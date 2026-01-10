"""
Core extraction logic for video to image frames.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from ..config import Config


class ExtractionError(RuntimeError):
    """Raised when FFmpeg extraction fails."""


@dataclass
class VideoInfo:
    """Metadata about a video file."""
    path: Path
    duration: float          # seconds
    width: int
    height: int
    fps: float
    frame_count: int
    codec: str
    container: str
    file_size: int           # bytes
    
    @property
    def resolution(self) -> str:
        return f"{self.width}x{self.height}"
    
    @property
    def duration_str(self) -> str:
        minutes = int(self.duration // 60)
        seconds = int(self.duration % 60)
        return f"{minutes}:{seconds:02d}"
    
    @property
    def file_size_str(self) -> str:
        if self.file_size > 1024 * 1024 * 1024:
            return f"{self.file_size / (1024**3):.1f} GB"
        elif self.file_size > 1024 * 1024:
            return f"{self.file_size / (1024**2):.1f} MB"
        else:
            return f"{self.file_size / 1024:.1f} KB"


@dataclass
class ExtractionRequest:
    """Parameters for frame extraction."""
    video_path: Path
    output_folder: Path
    output_format: str       # "png", "jpeg", "tiff", "exr"
    name_pattern: str        # e.g., "frame_%05d"
    
    # Optional extraction filters
    frame_rate: Optional[float] = None  # None = all frames, or specific fps
    start_time: Optional[float] = None  # seconds
    end_time: Optional[float] = None    # seconds
    
    # Quality settings
    jpeg_quality: int = 95              # 1-100 for JPEG
    png_compression: int = 6            # 0-9 for PNG
    
    def get_output_extension(self) -> str:
        """Get file extension for output format."""
        format_extensions = {
            "png": "png",
            "jpeg": "jpg",
            "tiff": "tiff",
            "exr": "exr",
        }
        return format_extensions.get(self.output_format, "png")


def probe_video(config: Config, video_path: Path) -> VideoInfo:
    """
    Use FFprobe to extract video metadata.
    
    Returns VideoInfo with duration, resolution, fps, codec, etc.
    """
    if not video_path.exists():
        raise ExtractionError(f"Video file not found: {video_path}")
    
    # FFprobe command for JSON output
    ffprobe_path = config.ffmpeg_path.parent / "ffprobe.exe"
    if not ffprobe_path.exists():
        ffprobe_path = config.ffmpeg_path.parent / "ffprobe"
    
    cmd = [
        str(ffprobe_path),
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(video_path),
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
    except subprocess.CalledProcessError as exc:
        raise ExtractionError(f"FFprobe failed: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ExtractionError(f"Failed to parse FFprobe output: {exc}") from exc
    
    # Find video stream
    video_stream = None
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            video_stream = stream
            break
    
    if not video_stream:
        raise ExtractionError("No video stream found in file")
    
    # Parse frame rate (can be "30/1" or "29.97")
    fps_str = video_stream.get("r_frame_rate", "30/1")
    if "/" in fps_str:
        num, den = fps_str.split("/")
        fps = float(num) / float(den)
    else:
        fps = float(fps_str)
    
    # Get duration from format or stream
    format_info = data.get("format", {})
    duration = float(format_info.get("duration", video_stream.get("duration", 0)))
    
    # Calculate frame count
    frame_count = int(video_stream.get("nb_frames", 0))
    if frame_count == 0:
        frame_count = int(duration * fps)
    
    return VideoInfo(
        path=video_path,
        duration=duration,
        width=int(video_stream.get("width", 0)),
        height=int(video_stream.get("height", 0)),
        fps=fps,
        frame_count=frame_count,
        codec=video_stream.get("codec_name", "unknown"),
        container=video_path.suffix.lstrip("."),
        file_size=video_path.stat().st_size,
    )


def build_extraction_command(
    config: Config,
    request: ExtractionRequest,
) -> List[str]:
    """
    Build FFmpeg command for frame extraction.
    
    Handles:
    - Time range filtering (start/end)
    - Frame rate filtering (extract every Nth frame)
    - Output format and quality settings
    """
    cmd: List[str] = [str(config.ffmpeg_path)]
    
    # Input time range (before -i for faster seeking)
    if request.start_time is not None:
        cmd.extend(["-ss", str(request.start_time)])
    
    # Input file
    cmd.extend(["-i", str(request.video_path)])
    
    # Output time range (after -i for precise cutting)
    if request.end_time is not None:
        if request.start_time is not None:
            # Duration from start
            duration = request.end_time - request.start_time
            cmd.extend(["-t", str(duration)])
        else:
            cmd.extend(["-to", str(request.end_time)])
    
    # Build video filter chain
    vf_filters: List[str] = []
    
    # Frame rate filter (extract at specific fps)
    if request.frame_rate is not None:
        vf_filters.append(f"fps={request.frame_rate}")
    
    # Apply filters if any
    if vf_filters:
        cmd.extend(["-vf", ",".join(vf_filters)])
    
    # Format-specific quality settings
    if request.output_format == "jpeg":
        cmd.extend(["-q:v", str(int((100 - request.jpeg_quality) / 3.2))])  # FFmpeg uses 2-31
    elif request.output_format == "png":
        cmd.extend(["-compression_level", str(request.png_compression)])
    elif request.output_format == "tiff":
        cmd.extend(["-compression_algo", "lzw"])
    
    # Ensure output folder exists
    request.output_folder.mkdir(parents=True, exist_ok=True)
    
    # Output path with pattern
    extension = request.get_output_extension()
    output_path = request.output_folder / f"{request.name_pattern}.{extension}"
    
    cmd.extend([
        "-start_number", "0",
        "-loglevel", "error",
        "-stats",
        str(output_path),
    ])
    
    return cmd


def estimate_output_frames(
    video_info: VideoInfo,
    request: ExtractionRequest,
) -> int:
    """Estimate number of frames that will be extracted."""
    # Calculate effective duration
    start = request.start_time or 0
    end = request.end_time or video_info.duration
    duration = end - start
    
    # Calculate frame count based on extraction rate
    if request.frame_rate is not None:
        return int(duration * request.frame_rate)
    else:
        return int(duration * video_info.fps)


def estimate_output_size(
    video_info: VideoInfo,
    request: ExtractionRequest,
    frame_count: int,
) -> int:
    """Estimate total output size in bytes based on format and resolution."""
    # Approximate bytes per pixel for each format
    bytes_per_pixel = {
        "png": 2.0,      # Compressed, varies
        "jpeg": 0.3,     # Highly compressed
        "tiff": 3.0,     # Less compression
        "exr": 6.0,      # 16-bit float
    }
    
    pixels = video_info.width * video_info.height
    bpp = bytes_per_pixel.get(request.output_format, 2.0)
    
    # Adjust for JPEG quality
    if request.output_format == "jpeg":
        bpp *= (request.jpeg_quality / 100)
    
    return int(pixels * bpp * frame_count)


def run_extraction(cmd: List[str]) -> None:
    """Execute FFmpeg extraction command."""
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        raise ExtractionError("FFmpeg extraction failed.") from exc


def extract_frames(config: Config, request: ExtractionRequest) -> Tuple[Path, int]:
    """
    Main entry point for frame extraction.
    
    Returns:
        Tuple of (output_folder, extracted_frame_count)
    """
    # Probe video first
    video_info = probe_video(config, request.video_path)
    
    # Log info
    print(f"Video: {video_info.path.name}")
    print(f"Duration: {video_info.duration_str} ({video_info.frame_count} frames)")
    print(f"Resolution: {video_info.resolution} @ {video_info.fps:.2f}fps")
    print(f"Codec: {video_info.codec.upper()} ({video_info.container.upper()})")
    print()
    
    # Estimate output
    estimated_frames = estimate_output_frames(video_info, request)
    estimated_size = estimate_output_size(video_info, request, estimated_frames)
    
    print(f"Extracting ~{estimated_frames} frames as {request.output_format.upper()}")
    print(f"Output folder: {request.output_folder}")
    print(f"Estimated size: {estimated_size / (1024**2):.1f} MB")
    print()
    
    # Build and run command
    cmd = build_extraction_command(config, request)
    run_extraction(cmd)
    
    # Count actual extracted frames
    extension = request.get_output_extension()
    actual_frames = len(list(request.output_folder.glob(f"*.{extension}")))
    
    print(f"Ribbiting success! Extracted {actual_frames} frames to {request.output_folder}")
    return request.output_folder, actual_frames
