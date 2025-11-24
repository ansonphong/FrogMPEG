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
from typing import List, Sequence, Tuple

from .config import Config, Preset


class ConversionError(RuntimeError):
    """Raised when FFmpeg conversion fails."""


SEQUENCE_PATTERN = re.compile(r"-?\d+")


@dataclass
class ConversionRequest:
    folder_name: str
    preset_name: str | None
    extension: str | None = None


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


def build_ffmpeg_command(
    config: Config,
    preset: Preset,
    file_list: str,
    output_path: Path,
    use_gpu: bool,
) -> List[str]:
    """Build FFmpeg command for the requested conversion."""
    fps = preset.fps
    cmd: List[str] = [
        str(config.ffmpeg_path),
        "-f",
        "concat",
        "-safe",
        "0",
        "-r",
        str(fps),
        "-i",
        file_list,
        "-vf",
        f"scale={preset.width}:{preset.height}",
    ]

    if use_gpu:
        cmd.extend(
            [
                "-c:v",
                "h264_nvenc",
                "-preset",
                config.encoding.gpu_preset,
                "-rc",
                "vbr",
                "-b:v",
                preset.bitrate,
                "-maxrate",
                preset.bitrate,
                "-bufsize",
                preset.bitrate,
                "-g",
                str(config.encoding.keyframe_interval),
                "-bf",
                str(config.encoding.b_frames),
                "-rc-lookahead",
                str(config.encoding.rc_lookahead),
                "-spatial-aq",
                str(config.encoding.spatial_aq),
                "-temporal-aq",
                str(config.encoding.temporal_aq),
                "-pix_fmt",
                config.encoding.pixel_format,
            ]
        )
    else:
        cmd.extend(
            [
                "-c:v",
                "libx264",
                "-preset",
                config.encoding.cpu_preset,
                "-tune",
                config.encoding.tune,
                "-b:v",
                preset.bitrate,
                "-g",
                str(config.encoding.keyframe_interval),
                "-bf",
                str(config.encoding.b_frames),
                "-pix_fmt",
                config.encoding.pixel_format,
            ]
        )

    cmd.extend(
        [
            "-loglevel",
            "error",
            "-stats",
            str(output_path),
        ]
    )

    return cmd


def build_output_path(config: Config, folder_name: str, preset: Preset) -> Path:
    """Generate timestamped output path and avoid overwriting."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base_name = f"{folder_name}_{timestamp}_{preset.resolution}_{preset.fps}fps"
    output_path = config.output_folder / f"{base_name}.mp4"

    counter = 1
    while output_path.exists():
        output_path = config.output_folder / f"{base_name}_{counter}.mp4"
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

    folder_path = config.renders_folder / request.folder_name
    if not folder_path.exists():
        raise ConversionError(f"Folder '{request.folder_name}' not found inside renders folder.")

    images = list_images(folder_path, extension)
    file_list, frame_count = create_file_list(images)

    print(f"Found {frame_count} *.{extension} files in {folder_path.name}")
    print(f"Using preset: {preset.name} ({preset.resolution} @ {preset.fps}fps, {preset.bitrate})")

    output_path = build_output_path(config, request.folder_name, preset)
    cmd = build_ffmpeg_command(config, preset, file_list, output_path, config.encoding.use_gpu)

    try:
        run_ffmpeg(cmd)
    except ConversionError:
        # NVENC fallback
        if config.encoding.use_gpu:
            print("NVENC failed, retrying with CPU encoding...")
            cmd = build_ffmpeg_command(config, preset, file_list, output_path, use_gpu=False)
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

