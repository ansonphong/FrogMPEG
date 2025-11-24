"""
Typer-based CLI for FrogMPEG.
"""

from __future__ import annotations

import json
from typing import Optional

import typer

from . import __version__
from .config import (
    CONFIG_EXAMPLE_FILE,
    CONFIG_FILE,
    ConfigError,
    ensure_config_exists,
    load_config,
)
from .converter import ConversionRequest, ConversionError, convert_folder

app = typer.Typer(help="🐸 FrogMPEG - Convert image sequences to MP4 with style.")


@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", help="Show version and exit."),
) -> None:
    if version:
        typer.echo(f"FrogMPEG {__version__}")
        raise typer.Exit()


@app.command(help="Launch the btop-inspired GUI.")
def gui() -> None:
    from .gui import run_gui

    run_gui()


@app.command(help="Convert an image sequence folder to MP4.")
def convert(
    folder: str = typer.Argument(..., help="Folder name inside renders_folder."),
    preset: Optional[str] = typer.Option(None, "--preset", "-p", help="Preset name from config."),
    extension: Optional[str] = typer.Option(
        None, "--extension", "-e", help="Override file extension (jpeg/jpg/png)."
    ),
) -> None:
    config = load_config()
    request = ConversionRequest(folder_name=folder, preset_name=preset, extension=extension)
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
        typer.echo(
            f"- {preset.name}: {preset.description or 'No description'} "
            f"({preset.resolution}, {preset.bitrate}, {preset.fps}fps)"
        )


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


def run():
    app()


if __name__ == "__main__":
    run()

