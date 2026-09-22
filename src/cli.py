"""
Typer-based CLI for FrogMPEG.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

# Fix Windows console encoding for emoji support
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"

import typer

from . import __version__
from .config import (
    CONFIG_EXAMPLE_FILE,
    CONFIG_FILE,
    ConfigError,
    ensure_config_exists,
    load_config,
)
from .img2video.converter import ConversionRequest, ConversionError, convert_folder
from .video2img.converter import ExtractionRequest, ExtractionError, extract_frames
from .dialogs import browse_for_sequence_folder, browse_for_video_file
from .formats import (
    ALL_CODECS,
    CODECS_BY_CONTAINER,
    get_available_containers,
    get_codec,
    get_codecs_for_container,
)

app = typer.Typer(help="FrogMPEG - Multi-codec video converter with ProRes support.")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", help="Show version and exit."),
) -> None:
    if version:
        typer.echo(f"FrogMPEG {__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


def _existing_path(path: Optional[Path]) -> Optional[Path]:
    """Resolve a GUI path argument, or exit if it does not exist."""
    if path is None:
        return None
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        typer.secho(f"Path not found: {resolved}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    return resolved


@app.command(help="Launch the launcher - choose between image-to-video or video-to-image.")
def gui(
    folder: Optional[Path] = typer.Argument(
        None,
        help="Folder to open in the mode you pick. A video file opens video-to-image on that file.",
    ),
) -> None:
    folder = _existing_path(folder)
    if folder is not None and folder.is_file():
        from .video2img.gui import run_gui
        run_gui(folder)
        return
    from .launcher.gui import run_launcher
    run_launcher(folder)


@app.command(help="Launch image-to-video GUI directly.")
def img2video(
    folder: Optional[Path] = typer.Argument(
        None,
        help="Sequence folder, or a parent of sequence folders. Defaults to renders_folder.",
    ),
) -> None:
    folder = _existing_path(folder)
    if folder is not None and not folder.is_dir():
        typer.secho(f"Not a folder: {folder}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    from .img2video.gui import run_gui
    run_gui(folder)


@app.command(help="Launch video-to-image GUI directly.")
def video2img(
    path: Optional[Path] = typer.Argument(
        None,
        help="Video file to open, or a folder of videos. Defaults to output_folder.",
    ),
) -> None:
    path = _existing_path(path)
    from .video2img.gui import run_gui
    run_gui(path)


@app.command(help="Convert an image sequence folder to video.")
def convert(
    folder: str = typer.Argument(None, help="Folder name inside renders_folder (or use --browse)."),
    preset: Optional[str] = typer.Option(None, "--preset", "-p", help="Preset name from config."),
    extension: Optional[str] = typer.Option(
        None, "--extension", "-e", help="Override file extension (jpeg/jpg/png)."
    ),
    format: Optional[str] = typer.Option(
        None, "--format", "-f", help="Output format key (e.g., prores-422-mov, hevc-nvenc-mp4)."
    ),
    container: Optional[str] = typer.Option(
        None, "--container", "-c", help="Output container: mp4, mov (will use default codec)."
    ),
    browse: bool = typer.Option(
        False, "--browse", "-b", help="Open folder browser to select image sequence."
    ),
    rotate: int = typer.Option(
        0,
        "--rotate",
        "-r",
        help="Rotate clockwise before scaling: 0, 90, -90, 180, or 270.",
    ),
) -> None:
    config = load_config()
    
    # Handle folder selection
    folder_name = folder
    if browse or not folder:
        typer.secho("Opening folder browser...", fg=typer.colors.CYAN)
        selected_folder = browse_for_sequence_folder(config.renders_folder)
        
        if not selected_folder:
            typer.secho("No folder selected. Cancelled.", fg=typer.colors.YELLOW)
            raise typer.Exit()
        
        # Check if selected folder is inside renders_folder
        try:
            relative = selected_folder.relative_to(config.renders_folder)
            folder_name = str(relative).replace("\\", "/").split("/")[0]
        except ValueError:
            # Folder is outside renders_folder, use its name
            folder_name = selected_folder.name
            typer.secho(
                f"Warning: Selected folder is outside configured renders_folder.", 
                fg=typer.colors.YELLOW
            )
        
        typer.secho(f"Selected: {folder_name}", fg=typer.colors.GREEN)
    
    if not folder_name:
        typer.secho("Error: No folder specified. Use folder name or --browse flag.", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    
    # Resolve output format
    output_format_key = None
    if format:
        # Explicit format key provided
        if not get_codec(format):
            typer.secho(f"Error: Unknown format key '{format}'", fg=typer.colors.RED)
            typer.secho("Run 'frogmpeg list-formats' to see available formats.", fg=typer.colors.YELLOW)
            raise typer.Exit(code=1)
        output_format_key = format
    elif container:
        # Container provided, use default codec for that container
        codecs = get_codecs_for_container(container)
        if not codecs:
            typer.secho(f"Error: Unknown container '{container}'", fg=typer.colors.RED)
            typer.secho("Run 'frogmpeg list-containers' to see available containers.", fg=typer.colors.YELLOW)
            raise typer.Exit(code=1)
        # Use the first codec (typically the best/default one)
        output_format_key = codecs[0].key
        typer.secho(f"Using default codec for {container}: {codecs[0].display_name}", fg=typer.colors.CYAN)
    
    request = ConversionRequest(
        folder_name=folder_name,
        preset_name=preset,
        extension=extension,
        output_codec=output_format_key,
        rotate=rotate,
    )
    
    try:
        convert_folder(config, request)
    except (ConversionError, ConfigError) as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command(help="Browse for folder and start conversion with interactive prompts.")
def browse() -> None:
    """Open folder browser, then interactively configure and convert."""
    config = load_config()
    
    typer.secho("FrogMPEG Browse Mode", fg=typer.colors.GREEN, bold=True)
    typer.echo()
    
    # Browse for folder
    typer.secho("Opening folder browser...", fg=typer.colors.CYAN)
    selected_folder = browse_for_sequence_folder(config.renders_folder)
    
    if not selected_folder:
        typer.secho("No folder selected. Cancelled.", fg=typer.colors.YELLOW)
        raise typer.Exit()
    
    # Determine folder name
    try:
        relative = selected_folder.relative_to(config.renders_folder)
        folder_name = str(relative).replace("\\", "/").split("/")[0]
    except ValueError:
        folder_name = selected_folder.name
    
    typer.secho(f"Selected: {selected_folder}", fg=typer.colors.GREEN)
    typer.echo()
    
    # Show available presets
    if config.presets:
        typer.secho("Available presets:", fg=typer.colors.CYAN)
        for i, (name, preset) in enumerate(config.presets.items(), 1):
            typer.echo(f"  {i}. {name} - {preset.description}")
        typer.echo()
        
        preset_input = typer.prompt("Select preset number (or press Enter for default)", default="", show_default=False)
        if preset_input:
            try:
                preset_idx = int(preset_input) - 1
                preset_name = list(config.presets.keys())[preset_idx]
            except (ValueError, IndexError):
                typer.secho("Invalid preset, using default", fg=typer.colors.YELLOW)
                preset_name = None
        else:
            preset_name = None
    else:
        preset_name = None
    
    # Show format options
    typer.echo()
    typer.secho("Output format:", fg=typer.colors.CYAN)
    typer.echo("  1. H.264 MP4 (default - fast, universal)")
    typer.echo("  2. HEVC MP4 (smaller files)")
    typer.echo("  3. ProRes 422 MOV (editing)")
    typer.echo("  4. ProRes 422 HQ MOV (high quality)")
    typer.echo("  5. ProRes 4444 MOV (with alpha)")
    typer.echo()
    
    format_map = {
        "1": "h264-nvenc-mp4",
        "2": "hevc-nvenc-mp4",
        "3": "prores-422-mov",
        "4": "prores-422-hq-mov",
        "5": "prores-4444-mov",
    }
    
    format_input = typer.prompt("Select format (1-5)", default="1")
    output_codec = format_map.get(format_input, "h264-nvenc-mp4")
    
    # Create request
    request = ConversionRequest(
        folder_name=folder_name,
        preset_name=preset_name,
        output_codec=output_codec
    )
    
    typer.echo()
    typer.secho("Starting conversion...", fg=typer.colors.GREEN, bold=True)
    typer.echo()
    
    try:
        convert_folder(config, request)
    except (ConversionError, ConfigError) as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command(help="List available presets.")
def list_presets() -> None:
    config = load_config()
    if not config.presets:
        typer.secho("No presets defined in config.json", fg=typer.colors.YELLOW)
        raise typer.Exit()

    typer.secho("Available presets:", fg=typer.colors.GREEN, bold=True)
    for preset in config.presets.values():
        codec_info = ""
        if preset.output_codec:
            codec = preset.output_codec.codec_profile
            codec_info = f" [{codec.display_name}]"
        fit_info = f", {preset.fit}" if preset.fit != "stretch" else ""
        
        typer.echo(
            f"- {preset.name}: {preset.description or 'No description'} "
            f"({preset.resolution}, {preset.bitrate}, {preset.fps}fps{fit_info}){codec_info}"
        )


@app.command(help="List all available output formats and codecs.")
def list_formats() -> None:
    typer.secho("Available Output Formats:", fg=typer.colors.GREEN, bold=True)
    typer.echo()
    
    # Group by container
    for container in sorted(CODECS_BY_CONTAINER.keys()):
        codecs = CODECS_BY_CONTAINER[container]
        typer.secho(f"{container.upper()} Container:", fg=typer.colors.CYAN, bold=True)
        
        for codec in codecs:
            # Build badge string
            badges = []
            if codec.supports_gpu:
                badges.append("[GPU]")
            else:
                badges.append("[CPU]")
            if codec.supports_alpha:
                badges.append("[Alpha]")
            
            badge_str = " ".join(badges)
            
            typer.echo(f"  • {codec.key}")
            typer.echo(f"    {codec.display_name} {badge_str}")
            typer.echo(f"    {codec.description}")
            if codec.use_case:
                typer.secho(f"    Use case: {codec.use_case}", fg=typer.colors.YELLOW)
            typer.echo()


@app.command(help="List available containers.")
def list_containers() -> None:
    typer.secho("Available containers:", fg=typer.colors.GREEN, bold=True)
    containers = get_available_containers()
    for container in sorted(containers):
        codec_count = len(get_codecs_for_container(container))
        typer.echo(f"  • {container.upper()} ({codec_count} codecs available)")
    typer.echo()
    typer.secho("Run 'frogmpeg list-codecs --container <name>' to see codecs for a specific container.", 
                fg=typer.colors.CYAN)


@app.command(help="List codecs available for a specific container.")
def list_codecs(
    container: str = typer.Option(..., "--container", "-c", help="Container: mp4, mov")
) -> None:
    codecs = get_codecs_for_container(container)
    
    if not codecs:
        typer.secho(f"Unknown container: {container}", fg=typer.colors.RED)
        typer.secho("Run 'frogmpeg list-containers' to see available containers.", fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)
    
    typer.secho(f"Codecs for {container.upper()}:", fg=typer.colors.GREEN, bold=True)
    for codec in codecs:
        gpu_marker = "[GPU]" if codec.supports_gpu else "[CPU]"
        alpha_marker = " [Alpha]" if codec.supports_alpha else ""
        typer.echo(f"  {gpu_marker}{alpha_marker} {codec.key}: {codec.display_name}")
        typer.echo(f"      {codec.description}")
    typer.echo()
    typer.secho(f"Use --format <key> to select a specific codec", fg=typer.colors.CYAN)


@app.command(help="Create config.json from config.example.json.")
def init(force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing config.")) -> None:
    if CONFIG_FILE.exists() and not force:
        typer.secho("config.json already exists. Use --force to overwrite.", fg=typer.colors.YELLOW)
        raise typer.Exit()

    ensure_config_exists()
    typer.secho("config.json is ready. Customize it for your project.", fg=typer.colors.GREEN)


@app.command(help="Validate configuration and environment.")
def validate() -> None:
    try:
        config = load_config()
    except ConfigError as exc:
        typer.secho(f"Config error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    ok = True

    if not config.ffmpeg_path.exists():
        typer.secho(f"FFmpeg not found at {config.ffmpeg_path}", fg=typer.colors.RED)
        ok = False

    if not config.renders_folder.exists():
        typer.secho(f"Renders folder missing: {config.renders_folder}", fg=typer.colors.RED)
        ok = False

    if not config.output_folder.exists():
        typer.secho(f"Output folder missing: {config.output_folder}", fg=typer.colors.RED)
        ok = False

    if config.presets:
        typer.secho(f"{len(config.presets)} presets loaded.", fg=typer.colors.GREEN)

    if ok:
        typer.secho("Configuration validated successfully!", fg=typer.colors.GREEN, bold=True)
    else:
        raise typer.Exit(code=1)


@app.command(help="Extract frames from a video file.")
def extract(
    video: Path = typer.Argument(..., help="Path to video file"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output folder"),
    format: str = typer.Option("png", "--format", "-f", help="Output format: png, jpeg, tiff, exr"),
    fps: Optional[float] = typer.Option(None, "--fps", help="Extract at specific frame rate (e.g., 24, 30)"),
    start: Optional[float] = typer.Option(None, "--start", "-s", help="Start time in seconds"),
    end: Optional[float] = typer.Option(None, "--end", "-e", help="End time in seconds"),
    quality: int = typer.Option(95, "--quality", "-q", help="JPEG quality (1-100)"),
) -> None:
    """Extract frames from video (CLI mode)."""
    config = load_config()
    
    # Default output folder
    if output is None:
        output = config.output_folder / f"{video.stem}_frames"
    
    request = ExtractionRequest(
        video_path=video,
        output_folder=output,
        output_format=format,
        name_pattern=f"{video.stem}_%05d",
        frame_rate=fps,
        start_time=start,
        end_time=end,
        jpeg_quality=quality,
    )
    
    try:
        extract_frames(config, request)
    except (ExtractionError, ConfigError) as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


def run():
    app()


if __name__ == "__main__":
    run()

