"""
Core conversion logic for FrogMPEG.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from ..config import Config, OutputCodec, Preset
from ..formats import CodecProfile


class ConversionError(RuntimeError):
    """Raised when FFmpeg conversion fails."""


SEQUENCE_PATTERN = re.compile(r"-?\d+")


@dataclass
class ConversionRequest:
    folder_name: str
    preset_name: str | None
    extension: str | None = None
    output_codec: str | None = None  # Override output codec
    source_folder: Optional[Path] = None  # If set, use this instead of config.renders_folder
    output_folder: Optional[Path] = None  # If set, output here instead of config.output_folder
    rotate: int = 0  # Clockwise degrees. 0, 90, -90, 180, 270.


def extract_sequence_numbers(filename: str) -> Tuple[int, ...]:
    """Return tuples of all integers in the filename for numeric sorting."""
    numbers = SEQUENCE_PATTERN.findall(filename)
    if not numbers:
        return (0,)
    return tuple(int(n) for n in numbers)


def list_images(folder: Path, extension: str) -> List[Path]:
    """Return sorted list of images within folder."""
    files = list(folder.glob(f"*.{extension.lower()}"))
    files.sort(key=lambda f: (extract_sequence_numbers(f.name), f.name))
    return files


def create_file_list(images: Sequence[Path]) -> Tuple[str, int]:
    """Create temporary concat file for FFmpeg."""
    if not images:
        raise ConversionError("No image files found for the requested extension.")

    temp_list = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")

    for image in images:
        image_path = str(image.resolve()).replace("\\", "/")
        temp_list.write(f"file '{image_path}'\n")

    temp_list.flush()
    temp_list.close()
    return temp_list.name, len(images)


# ============================================================================
# CODEC-SPECIFIC COMMAND BUILDERS
# ============================================================================

def build_h264_command(
    config: Config,
    preset: Preset,
    codec_profile: CodecProfile,
    use_gpu: bool,
) -> List[str]:
    """Build H.264 encoding parameters."""
    cmd: List[str] = []
    
    if use_gpu and codec_profile.supports_gpu:
        # NVENC GPU encoding
        cmd.extend([
            "-c:v", codec_profile.encoder_name,
            "-preset", config.encoding.gpu_preset,
            "-rc", "vbr",
            "-b:v", preset.bitrate,
            "-maxrate", preset.bitrate,
            "-bufsize", preset.bitrate,
            "-g", str(config.encoding.keyframe_interval),
            "-bf", str(config.encoding.b_frames),
            "-rc-lookahead", str(config.encoding.rc_lookahead),
            "-spatial-aq", str(config.encoding.spatial_aq),
            "-temporal-aq", str(config.encoding.temporal_aq),
            "-pix_fmt", codec_profile.pixel_format,
        ])
    else:
        # CPU encoding
        cmd.extend([
            "-c:v", "libx264",
            "-preset", config.encoding.cpu_preset,
            "-tune", config.encoding.tune,
            "-b:v", preset.bitrate,
            "-g", str(config.encoding.keyframe_interval),
            "-bf", str(config.encoding.b_frames),
            "-pix_fmt", codec_profile.pixel_format,
        ])
    
    return cmd


def build_hevc_command(
    config: Config,
    preset: Preset,
    codec_profile: CodecProfile,
    use_gpu: bool,
) -> List[str]:
    """Build HEVC/H.265 encoding parameters."""
    cmd: List[str] = []
    
    if use_gpu and codec_profile.supports_gpu:
        # NVENC GPU encoding
        cmd.extend([
            "-c:v", codec_profile.encoder_name,
            "-preset", config.encoding.gpu_preset,
            "-rc", "vbr",
            "-b:v", preset.bitrate,
            "-maxrate", preset.bitrate,
            "-bufsize", preset.bitrate,
            "-g", str(config.encoding.keyframe_interval),
            "-bf", str(config.encoding.b_frames),
            "-rc-lookahead", str(config.encoding.rc_lookahead),
            "-spatial-aq", str(config.encoding.spatial_aq),
            "-temporal-aq", str(config.encoding.temporal_aq),
            "-pix_fmt", codec_profile.pixel_format,
        ])
    else:
        # CPU encoding with x265
        cmd.extend([
            "-c:v", "libx265",
            "-preset", config.encoding.cpu_preset,
            "-b:v", preset.bitrate,
            "-g", str(config.encoding.keyframe_interval),
            "-pix_fmt", codec_profile.pixel_format,
        ])
    
    return cmd


def build_prores_command(
    config: Config,
    preset: Preset,
    codec_profile: CodecProfile,
    use_gpu: bool,
) -> List[str]:
    """Build ProRes encoding parameters."""
    cmd: List[str] = [
        "-c:v", codec_profile.encoder_name,
        "-profile:v", codec_profile.profile,
        "-pix_fmt", codec_profile.pixel_format,
    ]
    
    # ProRes uses quality scale instead of bitrate
    # Quality values: 9-13 for proxy, 0-32 for others (lower = better)
    if codec_profile.profile == "0":  # Proxy
        cmd.extend(["-qscale:v", "11"])
    elif codec_profile.profile == "1":  # LT
        cmd.extend(["-qscale:v", "9"])
    elif codec_profile.profile == "2":  # 422
        cmd.extend(["-qscale:v", "6"])
    elif codec_profile.profile == "3":  # 422 HQ
        cmd.extend(["-qscale:v", "4"])
    elif codec_profile.profile in ["4", "5"]:  # 4444 / 4444 XQ
        cmd.extend(["-qscale:v", "3"])
    
    # ProRes doesn't use GOP settings in the same way
    # But we can set vendor tag for compatibility
    cmd.extend(["-vendor", "apl0"])
    
    return cmd


def build_codec_command(
    config: Config,
    preset: Preset,
    codec_profile: CodecProfile,
    use_gpu: bool,
) -> List[str]:
    """Build codec-specific encoding parameters based on codec family."""
    
    if codec_profile.codec_name == "h264":
        return build_h264_command(config, preset, codec_profile, use_gpu)
    elif codec_profile.codec_name == "hevc":
        return build_hevc_command(config, preset, codec_profile, use_gpu)
    elif codec_profile.codec_name == "prores":
        return build_prores_command(config, preset, codec_profile, use_gpu)
    else:
        raise ConversionError(f"Unsupported codec: {codec_profile.codec_name}")


def build_scale_filter(preset: Preset) -> str:
    """Scale to the preset size.

    stretch fills the frame and ignores aspect ratio (dome presets).
    pad fits the whole frame and adds black bars.
    crop fills the frame and cuts the overflow.
    """
    width = preset.width
    height = preset.height
    if preset.fit == "pad":
        return (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"
        )
    if preset.fit == "crop":
        return (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height}"
        )
    return f"scale={width}:{height}"


def rotate_filter(degrees: int) -> Optional[str]:
    """FFmpeg filter for a clockwise quarter-turn, or None when degrees is 0.

    90 clockwise is transpose=1. -90 and 270 are transpose=2.
    180 is hflip,vflip. Other values raise ConversionError.
    """
    normalized = degrees % 360
    filters = {
        0: None,
        90: "transpose=1",
        180: "hflip,vflip",
        270: "transpose=2",
    }
    if normalized not in filters:
        raise ConversionError(
            f"Rotate must be a multiple of 90 degrees (0, 90, -90, 180, 270). Got {degrees}."
        )
    return filters[normalized]


def build_video_filter(preset: Preset, rotate: int = 0) -> str:
    """Rotate first, then scale into the preset frame."""
    parts: List[str] = []
    rotation = rotate_filter(rotate)
    if rotation:
        parts.append(rotation)
    parts.append(build_scale_filter(preset))
    return ",".join(parts)


def build_ffmpeg_command(
    config: Config,
    preset: Preset,
    output_codec: OutputCodec,
    file_list: str,
    output_path: Path,
    use_gpu: bool,
    rotate: int = 0,
) -> List[str]:
    """Build complete FFmpeg command for the requested conversion."""
    fps = preset.fps
    codec_profile = output_codec.codec_profile
    
    # Base command with input
    cmd: List[str] = [
        str(config.ffmpeg_path),
        "-f", "concat",
        "-safe", "0",
        "-r", str(fps),
        "-i", file_list,
        "-vf", build_video_filter(preset, rotate),
    ]
    
    # Add codec-specific encoding parameters
    codec_cmd = build_codec_command(config, preset, codec_profile, use_gpu)
    cmd.extend(codec_cmd)
    
    # Output settings
    if preset.faststart:
        cmd.extend(["-movflags", "+faststart"])
    cmd.extend([
        "-loglevel", "error",
        "-stats",
        str(output_path),
    ])
    
    return cmd


def build_output_path(
    config: Config,
    folder_name: str,
    preset: Preset,
    output_codec: OutputCodec,
    output_folder: Optional[Path] = None,
) -> Path:
    """Generate timestamped output path and avoid overwriting."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    codec_name = output_codec.codec_profile.key
    base_name = f"{folder_name}_{timestamp}_{preset.resolution}_{preset.fps}fps_{codec_name}"

    # Use custom output folder if provided, otherwise use config.output_folder
    target_folder = output_folder if output_folder else config.output_folder
    
    # Use correct extension from codec profile
    extension = output_codec.extension
    output_path = target_folder / f"{base_name}.{extension}"

    counter = 1
    while output_path.exists():
        output_path = target_folder / f"{base_name}_{counter}.{extension}"
        counter += 1

    return output_path


def run_ffmpeg(cmd: List[str]) -> None:
    """Execute FFmpeg command and raise on error."""
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        raise ConversionError("FFmpeg conversion failed.") from exc


def convert_folder(config: Config, request: ConversionRequest) -> Path:
    """Convert a folder according to the provided request."""
    preset = config.get_preset(request.preset_name)
    extension = (request.extension or config.defaults.file_extension).lower()

    # Determine output codec
    if request.output_codec:
        # Use codec from request
        output_codec = config.get_output_codec(request.output_codec)
    elif preset.output_codec:
        # Use codec from preset
        output_codec = preset.output_codec
    else:
        # Use default codec
        output_codec = config.get_output_codec()

    # Use custom source folder if provided, otherwise use config.renders_folder
    base_folder = request.source_folder if request.source_folder else config.renders_folder
    folder_path = base_folder if request.source_folder else base_folder / request.folder_name
    
    if not folder_path.exists():
        raise ConversionError(f"Folder '{request.folder_name}' not found.")

    images = list_images(folder_path, extension)
    file_list, frame_count = create_file_list(images)

    codec_profile = output_codec.codec_profile
    print(f"Found {frame_count} *.{extension} files in {folder_path.name}")
    print(f"Using preset: {preset.name} ({preset.resolution} @ {preset.fps}fps, {preset.bitrate})")
    print(f"Output codec: {codec_profile.display_name} ({codec_profile.container.upper()})")
    if request.rotate % 360:
        print(f"Rotate: {request.rotate} degrees clockwise")

    output_path = build_output_path(config, request.folder_name, preset, output_codec, request.output_folder)
    
    # Determine if we should try GPU encoding
    use_gpu = config.encoding.use_gpu and codec_profile.supports_gpu
    
    cmd = build_ffmpeg_command(
        config, preset, output_codec, file_list, output_path, use_gpu, request.rotate
    )

    try:
        run_ffmpeg(cmd)
    except ConversionError:
        # GPU fallback for codecs that support it
        if use_gpu:
            print(f"GPU encoding failed, retrying with CPU...")
            cmd = build_ffmpeg_command(
                config, preset, output_codec, file_list, output_path, False, request.rotate
            )
            run_ffmpeg(cmd)
        else:
            raise
    finally:
        try:
            os.unlink(file_list)
        except OSError:
            pass

    print(f"Ribbiting success! Output saved to {output_path}")
    return output_path
