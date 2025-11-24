"""
btop-inspired CLI GUI for FrogMPEG.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List

from rich import box
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

try:
    import msvcrt  # type: ignore
except ImportError:  # pragma: no cover - non-Windows fallback
    msvcrt = None  # type: ignore

from .config import Config, load_config
from .converter import ConversionRequest, convert_folder

console = Console()


@dataclass
class FolderInfo:
    name: str
    path: Path
    file_count: int
    mod_time: datetime


class FrogMPEGGui:
    def __init__(self) -> None:
        self.config: Config = load_config()
        self.folders: List[FolderInfo] = []
        self.extensions = ["jpeg", "jpg", "png"]
        self.selected_folder_idx = 0
        self.selected_extension_idx = 0
        self.preset_names = list(self.config.presets.keys()) or ["defaults"]
        self.selected_preset_idx = 0
        self.current_section = "folders"
        self.scan_folders()

    def scan_folders(self) -> None:
        results: List[FolderInfo] = []
        for entry in self.config.renders_folder.iterdir():
            if not entry.is_dir():
                continue
            file_count = sum(
                len(list(entry.glob(f"*.{ext}"))) for ext in self.extensions
            )
            if file_count == 0:
                continue
            mod_time = datetime.fromtimestamp(entry.stat().st_mtime)
            results.append(FolderInfo(entry.name, entry, file_count, mod_time))

        results.sort(key=lambda f: f.mod_time, reverse=True)
        self.folders = results
        if self.config.ui.auto_select_latest and results:
            self.selected_folder_idx = 0
        elif self.folders:
            self.selected_folder_idx = min(self.selected_folder_idx, len(self.folders) - 1)

    # UI helpers ---------------------------------------------------------
    def create_header(self) -> Panel:
        frog = Text("\n     🐸 FrogMPEG 🐸\n  The Ribbiting Way to\n  Convert Image Sequences\n", justify="center")
        return Panel(frog, style="bold green", box=box.ROUNDED)

    def create_folders_panel(self) -> Panel:
        table = Table(show_header=False, expand=True, box=None)
        table.add_column("", width=2)
        table.add_column("Folder", style="cyan")
        table.add_column("Files", justify="right", style="yellow")
        table.add_column("Modified", justify="right", style="magenta")

        if not self.folders:
            table.add_row("", "No folders found", "", "")
        else:
            for idx, folder in enumerate(self.folders[:12]):
                indicator = "►" if idx == self.selected_folder_idx else " "
                style = "reverse bold" if idx == self.selected_folder_idx else ""
                table.add_row(
                    indicator,
                    Text(folder.name, style=style),
                    Text(str(folder.file_count), style=style),
                    Text(folder.mod_time.strftime("%Y-%m-%d %H:%M"), style=style),
                )

        title = "Folders (↑↓)" if self.current_section == "folders" else "Folders"
        style = "bold cyan" if self.current_section == "folders" else "dim"
        return Panel(table, title=title, box=box.ROUNDED, style=style)

    def create_settings_panel(self) -> Panel:
        table = Table(show_header=False, expand=True, box=None)
        table.add_column("Setting", width=14, style="cyan")
        table.add_column("Value", style="yellow")

        preset_display = "  ".join(
            f"[{'bold green' if i == self.selected_preset_idx else 'dim'}]{name}[/]"
            for i, name in enumerate(self.preset_names)
        )
        table.add_row("Preset:", preset_display)

        ext_display = "  ".join(
            f"[{'bold green' if i == self.selected_extension_idx else 'dim'}]{ext}[/]"
            for i, ext in enumerate(self.extensions)
        )
        table.add_row("Extension:", ext_display)

        gpu_status = "⚡ NVENC Enabled" if self.config.encoding.use_gpu else "CPU Encoding"
        gpu_style = "bold green" if self.config.encoding.use_gpu else "yellow"
        table.add_row("GPU:", Text(gpu_status, style=gpu_style))

        title = "Settings (Tab + ←→)" if self.current_section != "folders" else "Settings"
        style = "bold magenta" if self.current_section != "folders" else "dim"
        return Panel(table, title=title, box=box.ROUNDED, style=style)

    def create_preview_panel(self) -> Panel:
        table = Table(show_header=False, expand=True, box=None)
        table.add_column("Metric", width=14, style="cyan")
        table.add_column("Value", style="yellow")

        folder = self.get_selected_folder()
        preset = self.get_selected_preset()

        if folder:
            table.add_row("Folder:", folder.name)
            duration = folder.file_count / preset.fps
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            table.add_row("Frames:", str(folder.file_count))
            table.add_row("Duration:", f"~{minutes}:{seconds:02d} ({preset.fps} fps)")
        table.add_row("Resolution:", preset.resolution)
        table.add_row("Bitrate:", preset.bitrate)

        return Panel(table, title="Preview", box=box.ROUNDED, style="bold green")

    def create_footer(self) -> Panel:
        controls = Text()
        controls.append("[S] Start  ")
        controls.append("[Tab] Switch  ")
        controls.append("[↑↓←→] Navigate  ")
        controls.append("[R] Refresh  ")
        controls.append("[Q] Quit")
        return Panel(controls, box=box.ROUNDED, style="dim")

    def render(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(self.create_header(), size=7),
            Layout(self.create_folders_panel(), size=15),
            Layout(self.create_settings_panel(), size=6),
            Layout(self.create_preview_panel(), size=6),
            Layout(self.create_footer(), size=3),
        )
        return layout

    # Helpers -------------------------------------------------------------
    def get_selected_folder(self) -> FolderInfo:
        return self.folders[self.selected_folder_idx]

    def get_selected_preset(self):
        name = self.preset_names[self.selected_preset_idx]
        return self.config.get_preset(name if name != "defaults" else None)

    # Interaction ---------------------------------------------------------
    def handle_key(self, key: str) -> str | None:
        if key.lower() == "q":
            return "quit"
        if key.lower() == "r":
            self.scan_folders()
            return None
        if key.lower() == "s":
            self.start_conversion()
            return None
        if key == "\t":
            sections = ["folders", "presets", "extensions"]
            idx = sections.index(self.current_section)
            self.current_section = sections[(idx + 1) % len(sections)]
            return None

        if self.current_section == "folders":
            if key == "H":  # up
                self.selected_folder_idx = max(0, self.selected_folder_idx - 1)
            elif key == "P":  # down
                self.selected_folder_idx = min(len(self.folders) - 1, self.selected_folder_idx + 1)
        elif self.current_section == "presets":
            if key == "K":  # left
                self.selected_preset_idx = max(0, self.selected_preset_idx - 1)
            elif key == "M":  # right
                self.selected_preset_idx = min(len(self.preset_names) - 1, self.selected_preset_idx + 1)
        elif self.current_section == "extensions":
            if key == "K":
                self.selected_extension_idx = max(0, self.selected_extension_idx - 1)
            elif key == "M":
                self.selected_extension_idx = min(len(self.extensions) - 1, self.selected_extension_idx + 1)
        return None

    def start_conversion(self) -> None:
        if not self.folders:
            console.print("[red]No folders available[/red]")
            time.sleep(1)
            return

        folder = self.get_selected_folder()
        preset = self.get_selected_preset()
        extension = self.extensions[self.selected_extension_idx]

        console.clear()
        console.print(
            Panel(
                f"[bold cyan]Converting[/bold cyan]\nFolder: {folder.name}\nPreset: {preset.name}\nExtension: {extension}",
                box=box.ROUNDED,
                style="green",
            )
        )

        request = ConversionRequest(
            folder_name=folder.name,
            preset_name=preset.name if preset.name != "defaults" else None,
            extension=extension,
        )
        try:
            convert_folder(self.config, request)
        except Exception as exc:  # pragma: no cover - CLI feedback
            console.print(f"[red]Conversion failed: {exc}[/red]")
        console.print("\nPress any key to return...")
        if msvcrt:
            msvcrt.getch()
        else:  # pragma: no cover
            input()

    def run(self) -> None:
        console.clear()
        if not self.folders:
            console.print("[bold red]No folders with images found in renders directory[/bold red]")
            return

        with console.screen():
            while True:
                console.print(self.render(), justify="center")
                if msvcrt:
                    key = msvcrt.getch()
                    if key in (b"\x00", b"\xe0"):
                        key = msvcrt.getch()
                    key = key.decode("utf-8", errors="ignore")
                else:  # pragma: no cover
                    key = sys.stdin.read(1)
                result = self.handle_key(key)
                if result == "quit":
                    break
                console.clear()


def run_gui() -> None:
    FrogMPEGGui().run()

