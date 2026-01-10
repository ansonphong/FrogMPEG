"""
btop-inspired CLI GUI for FrogMPEG with hierarchical format selection.
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List

# Fix Windows console encoding for emoji support
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, errors="replace")
    os.environ["PYTHONIOENCODING"] = "utf-8"

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
from .dialogs import browse_for_sequence_folder
from .formats import (
    CodecProfile,
    get_available_containers,
    get_codecs_for_container,
)


def resize_console_window() -> None:
    """Resize the console window to accommodate the full GUI."""
    if sys.platform == "win32":
        try:
            # Set console buffer and window size (cols=120, rows=50)
            # This ensures the GUI fits comfortably
            os.system("mode con: cols=120 lines=50")
        except Exception:  # pragma: no cover
            pass  # If resizing fails, continue anyway


console = Console()

# ═══════════════════════════════════════════════════════════════════════════════
# 🐸 FROG THEME COLOR PALETTE - All greens, emeralds, and yellows
# ═══════════════════════════════════════════════════════════════════════════════
COLORS = {
    # Primary greens (main UI elements)
    "primary": "green",              # Main accent color
    "bright": "bright_green",        # Highlights, selected items
    "emerald": "spring_green3",      # Emerald-like accent
    "lime": "chartreuse3",           # Lime/bright green accent
    
    # Secondary yellows (values, data)
    "gold": "yellow",                # Primary data color
    "amber": "gold3",                # Warm accent
    
    # Dimmed variants
    "muted": "dark_sea_green4",      # Muted green for inactive
    "dim_green": "dark_green",       # Dimmed borders/text
    "dim_yellow": "olive_drab1",     # Dimmed yellow
    
    # Semantic colors
    "selected": "bold bright_green reverse",
    "active_border": "bold bright_green",
    "inactive_border": "dark_green",
    "label": "spring_green2",        # Labels/titles
    "value": "yellow",               # Data values
    "description": "dark_sea_green", # Descriptions
}


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
        
        # Navigation state
        self.selected_folder_idx = 0
        self.selected_extension_idx = 0
        self.preset_names = list(self.config.presets.keys()) or ["defaults"]
        self.selected_preset_idx = 0
        
        # NEW: Format selection state
        self.containers = get_available_containers()
        self.selected_container_idx = 0
        self.selected_codec_idx = 0
        
        # Navigation sections: folders -> presets -> extensions -> container -> codec
        self.sections = ["folders", "presets", "extensions", "container", "codec"]
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
        """Compact header with frog branding."""
        title = Text("FrogMPEG", style="bold bright_green", justify="center")
        return Panel(title, style="bright_green", box=box.ROUNDED, height=3)

    def create_folders_panel(self) -> Panel:
        table = Table(show_header=False, expand=True, box=None)
        table.add_column("", width=2)
        table.add_column("Folder", style=COLORS["emerald"])
        table.add_column("Files", justify="right", style=COLORS["gold"])
        table.add_column("Modified", justify="right", style=COLORS["amber"])

        if not self.folders:
            table.add_row("", "[dim]No folders found[/]", "", "")
        else:
            for idx, folder in enumerate(self.folders[:8]):
                indicator = "►" if idx == self.selected_folder_idx else " "
                if idx == self.selected_folder_idx:
                    style = COLORS["selected"]
                    indicator_style = COLORS["bright"]
                else:
                    style = ""
                    indicator_style = COLORS["muted"]
                table.add_row(
                    Text(indicator, style=indicator_style),
                    Text(folder.name, style=style),
                    Text(str(folder.file_count), style=style if idx == self.selected_folder_idx else COLORS["gold"]),
                    Text(folder.mod_time.strftime("%Y-%m-%d %H:%M"), style=style if idx == self.selected_folder_idx else COLORS["amber"]),
                )

        title = "[1] Folders (↑↓)" if self.current_section == "folders" else "[1] Folders"
        style = COLORS["active_border"] if self.current_section == "folders" else COLORS["inactive_border"]
        return Panel(table, title=title, box=box.ROUNDED, style=style)

    def create_settings_panel(self) -> Panel:
        table = Table(show_header=False, expand=True, box=None)
        table.add_column("Setting", width=14, style=COLORS["label"])
        table.add_column("Value")

        # Presets
        preset_display = "  ".join(
            f"[{COLORS['selected']}] {name} [/]" if i == self.selected_preset_idx else f"[{COLORS['muted']}]{name}[/]"
            for i, name in enumerate(self.preset_names)
        )
        table.add_row("[2] Preset:", preset_display)

        # Extensions
        ext_display = "  ".join(
            f"[{COLORS['selected']}] {ext} [/]" if i == self.selected_extension_idx else f"[{COLORS['muted']}]{ext}[/]"
            for i, ext in enumerate(self.extensions)
        )
        table.add_row("[3] Extension:", ext_display)

        title = "Settings (Tab + ←→)" if self.current_section in ["presets", "extensions"] else "Settings"
        style = COLORS["active_border"] if self.current_section in ["presets", "extensions"] else COLORS["inactive_border"]
        return Panel(table, title=title, box=box.ROUNDED, style=style)

    def create_format_panel(self) -> Panel:
        """Two-level format selection panel with frog theme."""
        table = Table(show_header=False, expand=True, box=None)
        table.add_column("", width=2)
        table.add_column("Format")
        table.add_column("Details", style=COLORS["description"])

        # Container selection
        container_row = []
        for i, container in enumerate(self.containers):
            if i == self.selected_container_idx:
                container_row.append(f"[bold bright_green reverse] {container.upper()} [/]")
            else:
                container_row.append(f"[{COLORS['muted']}]{container.upper()}[/]")
        
        table.add_row("", f"[{COLORS['label']}][4] Container:[/]", "  ".join(container_row))
        
        # Codec selection for selected container
        selected_container = self.containers[self.selected_container_idx]
        codecs = get_codecs_for_container(selected_container)
        
        # Show first few codecs in compact form
        for idx, codec in enumerate(codecs[:6]):
            indicator = "►" if idx == self.selected_codec_idx else " "
            indicator_style = COLORS["bright"] if idx == self.selected_codec_idx else COLORS["muted"]
            
            # Build badges with green theme
            badges = []
            if codec.supports_gpu:
                badges.append(f"[{COLORS['lime']}][GPU][/]")
            else:
                badges.append(f"[{COLORS['muted']}][CPU][/]")
            if codec.supports_alpha:
                badges.append(f"[{COLORS['amber']}][Alpha][/]")
            
            badge_str = " ".join(badges)
            
            if idx == self.selected_codec_idx:
                name_style = "bold bright_green reverse"
                desc_style = COLORS["lime"]
            else:
                name_style = COLORS["emerald"]
                desc_style = COLORS["muted"]
            
            table.add_row(
                Text(indicator, style=indicator_style),
                f"[{COLORS['label']}][5][/] {badge_str} [{name_style}]{codec.display_name}[/]",
                f"[{desc_style}]{codec.use_case}[/]" if codec.use_case else ""
            )
        
        if len(codecs) > 6:
            table.add_row("", f"[{COLORS['muted']}]... and {len(codecs) - 6} more[/]", "")

        title = "Output Format (Tab + ←→ / ↑↓)" if self.current_section in ["container", "codec"] else "Output Format"
        style = COLORS["active_border"] if self.current_section in ["container", "codec"] else COLORS["inactive_border"]
        return Panel(table, title=title, box=box.ROUNDED, style=style)

    def create_preview_panel(self) -> Panel:
        table = Table(show_header=False, expand=False, box=None, padding=(0, 2))
        table.add_column("Label", width=16, style=COLORS["label"], no_wrap=True)
        table.add_column("Value", style=COLORS["gold"], no_wrap=False)

        folder = self.get_selected_folder()
        preset = self.get_selected_preset()
        codec = self.get_selected_codec()

        duration = 0.0
        if folder and folder.file_count > 0:
            duration = folder.file_count / preset.fps
            table.add_row("Folder:", folder.name)
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            table.add_row("Frames:", str(folder.file_count))
            table.add_row("Duration:", f"~{minutes}:{seconds:02d} @ {preset.fps}fps")
        
        table.add_row("Resolution:", preset.resolution)
        table.add_row("Bitrate:", preset.bitrate)
        table.add_row("", "")
        table.add_row("Output:", f"{codec.display_name}")
        table.add_row("Container:", f".{codec.container}")
        
        # File size estimate
        if folder and folder.file_count > 0:
            # Rough estimate: (bitrate in Mbps * duration in seconds) / 8 = MB
            bitrate_mbps = float(preset.bitrate.replace("M", ""))
            estimated_mb = (bitrate_mbps * duration / 8) * codec.file_size_multiplier
            if estimated_mb > 1024:
                size_str = f"~{estimated_mb/1024:.1f} GB"
            else:
                size_str = f"~{estimated_mb:.0f} MB"
            table.add_row("Est. Size:", size_str)

        return Panel(table, title="Preview", box=box.ROUNDED, style=COLORS["active_border"])

    def create_footer(self) -> Panel:
        controls = Text()
        controls.append("[S] Start  ", style="bold bright_green")
        controls.append("[B] Browse  ", style=COLORS["lime"])
        controls.append("[Tab/Enter] Next  ", style=COLORS["emerald"])
        controls.append("[Shift+Tab] Previous  ", style=COLORS["emerald"])
        controls.append("[↑↓] Navigate  ", style=COLORS["muted"])
        controls.append("[←→] Switch  ", style=COLORS["muted"])
        controls.append("[R] Refresh  ", style=COLORS["amber"])
        controls.append("[Q] Quit", style=COLORS["muted"])
        return Panel(controls, box=box.ROUNDED, style=COLORS["inactive_border"])

    def render(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(self.create_header(), size=3),
            Layout(self.create_folders_panel(), size=11),
            Layout(self.create_settings_panel(), size=5),
            Layout(self.create_format_panel(), size=12),
            Layout(self.create_preview_panel(), size=12),
            Layout(self.create_footer(), size=3),
        )
        return layout

    # Helpers -------------------------------------------------------------
    def get_selected_folder(self) -> FolderInfo:
        if not self.folders:
            return FolderInfo("", Path(), 0, datetime.now())
        return self.folders[self.selected_folder_idx]

    def get_selected_preset(self):
        name = self.preset_names[self.selected_preset_idx]
        return self.config.get_preset(name if name != "defaults" else None)
    
    def get_selected_codec(self) -> CodecProfile:
        """Get the currently selected codec profile."""
        container = self.containers[self.selected_container_idx]
        codecs = get_codecs_for_container(container)
        return codecs[self.selected_codec_idx]

    # Interaction ---------------------------------------------------------
    def handle_key(self, key: str) -> str | None:
        if key.lower() == "q":
            return "quit"
        if key.lower() == "r":
            self.scan_folders()
            return None
        if key.lower() == "b":
            self.browse_for_folder()
            return None
        if key.lower() == "s":
            self.start_conversion()
            return None
        if key == "\t" or key == "\r":  # Tab or Enter to move to next section
            # Cycle through sections forward
            idx = self.sections.index(self.current_section)
            self.current_section = self.sections[(idx + 1) % len(self.sections)]
            return None
        if key == "SHIFT_TAB":  # Shift+Tab to move to previous section
            # Cycle through sections backward
            idx = self.sections.index(self.current_section)
            self.current_section = self.sections[(idx - 1) % len(self.sections)]
            return None

        # Handle navigation based on current section
        if self.current_section == "folders":
            if key == "H":  # up arrow
                self.selected_folder_idx = max(0, self.selected_folder_idx - 1)
            elif key == "P":  # down arrow
                self.selected_folder_idx = min(len(self.folders) - 1, self.selected_folder_idx + 1)
        
        elif self.current_section == "presets":
            if key == "K":  # left arrow
                self.selected_preset_idx = max(0, self.selected_preset_idx - 1)
            elif key == "M":  # right arrow
                self.selected_preset_idx = min(len(self.preset_names) - 1, self.selected_preset_idx + 1)
        
        elif self.current_section == "extensions":
            if key == "K":  # left
                self.selected_extension_idx = max(0, self.selected_extension_idx - 1)
            elif key == "M":  # right
                self.selected_extension_idx = min(len(self.extensions) - 1, self.selected_extension_idx + 1)
        
        elif self.current_section == "container":
            # In container section: left/right for container, up/down for codec
            if key == "K":  # left
                self.selected_container_idx = max(0, self.selected_container_idx - 1)
                self.selected_codec_idx = 0  # Reset codec selection
            elif key == "M":  # right
                self.selected_container_idx = min(len(self.containers) - 1, self.selected_container_idx + 1)
                self.selected_codec_idx = 0  # Reset codec selection
            elif key == "H":  # up - also allow codec navigation in container section
                container = self.containers[self.selected_container_idx]
                codecs = get_codecs_for_container(container)
                self.selected_codec_idx = max(0, self.selected_codec_idx - 1)
            elif key == "P":  # down - also allow codec navigation in container section
                container = self.containers[self.selected_container_idx]
                codecs = get_codecs_for_container(container)
                self.selected_codec_idx = min(len(codecs) - 1, self.selected_codec_idx + 1)
        
        elif self.current_section == "codec":
            container = self.containers[self.selected_container_idx]
            codecs = get_codecs_for_container(container)
            if key == "H":  # up
                self.selected_codec_idx = max(0, self.selected_codec_idx - 1)
            elif key == "P":  # down
                self.selected_codec_idx = min(len(codecs) - 1, self.selected_codec_idx + 1)
            elif key == "K":  # left - also allow container navigation in codec section
                self.selected_container_idx = max(0, self.selected_container_idx - 1)
                self.selected_codec_idx = 0  # Reset codec selection
            elif key == "M":  # right - also allow container navigation in codec section
                self.selected_container_idx = min(len(self.containers) - 1, self.selected_container_idx + 1)
                self.selected_codec_idx = 0  # Reset codec selection
        
        return None

    def browse_for_folder(self) -> None:
        """Open native folder browser to add a folder to the list."""
        console.clear()
        console.print(
            Panel(
                "[bold bright_green]Opening folder browser...[/bold bright_green]\n"
                "[spring_green3]Select a folder containing image sequences.[/spring_green3]",
                box=box.ROUNDED,
                style="bright_green",
            )
        )
        
        # Open folder browser
        selected_folder = browse_for_sequence_folder(self.config.renders_folder)
        
        if selected_folder and selected_folder.exists():
            # Check if folder has images
            file_count = sum(
                len(list(selected_folder.glob(f"*.{ext}"))) for ext in self.extensions
            )
            
            if file_count > 0:
                # Add to folder list if not already there
                folder_names = [f.name for f in self.folders]
                if selected_folder.name not in folder_names:
                    mod_time = datetime.fromtimestamp(selected_folder.stat().st_mtime)
                    new_folder = FolderInfo(selected_folder.name, selected_folder, file_count, mod_time)
                    self.folders.insert(0, new_folder)
                    self.selected_folder_idx = 0
                    console.print(f"[bold bright_green]✓ Added: {selected_folder.name} ({file_count} files)[/bold bright_green]")
                else:
                    console.print(f"[yellow]Folder already in list: {selected_folder.name}[/yellow]")
                time.sleep(1)
            else:
                console.print(f"[gold3]✗ No image files found in selected folder[/gold3]")
                time.sleep(2)
        else:
            console.print("[yellow]No folder selected[/yellow]")
            time.sleep(1)

    def start_conversion(self) -> None:
        if not self.folders:
            console.print(f"[{COLORS['amber']}]No folders available[/]")
            time.sleep(1)
            return

        folder = self.get_selected_folder()
        preset = self.get_selected_preset()
        extension = self.extensions[self.selected_extension_idx]
        codec = self.get_selected_codec()

        console.clear()
        console.print(
            Panel(
                f"[bold bright_green]🐸 Converting[/bold bright_green]\n"
                f"[{COLORS['label']}]Folder:[/] [{COLORS['gold']}]{folder.name}[/]\n"
                f"[{COLORS['label']}]Preset:[/] [{COLORS['gold']}]{preset.name}[/]\n"
                f"[{COLORS['label']}]Extension:[/] [{COLORS['gold']}]{extension}[/]\n"
                f"[{COLORS['label']}]Format:[/] [{COLORS['gold']}]{codec.display_name} (.{codec.container})[/]",
                box=box.ROUNDED,
                style="bright_green",
            )
        )

        request = ConversionRequest(
            folder_name=folder.name,
            preset_name=preset.name if preset.name != "defaults" else None,
            extension=extension,
            output_codec=codec.key,
        )
        try:
            convert_folder(self.config, request)
        except Exception as exc:  # pragma: no cover - CLI feedback
            console.print(f"[{COLORS['amber']}]Conversion failed: {exc}[/]")
        console.print(f"\n[{COLORS['muted']}]Press any key to return...[/]")
        if msvcrt:
            msvcrt.getch()
        else:  # pragma: no cover
            input()

    def run(self) -> None:
        if not self.folders:
            console.print(f"[bold {COLORS['amber']}]No folders with images found in renders directory[/bold {COLORS['amber']}]")
            return

        # Resize console window to fit the GUI
        resize_console_window()

        with console.screen() as screen:
            while True:
                # Update screen content (Rich handles double buffering automatically)
                screen.update(self.render())
                
                if msvcrt:
                    key = msvcrt.getch()
                    # Handle special keys (arrows, function keys, etc.)
                    if key in (b"\x00", b"\xe0"):
                        key = msvcrt.getch()
                    # Shift+Tab sends "\x00\x0f"
                    elif key == b"\x00":
                        next_key = msvcrt.getch()
                        if next_key == b"\x0f":  # Shift+Tab
                            key = b"SHIFT_TAB"
                    key = key.decode("utf-8", errors="ignore")
                else:  # pragma: no cover
                    key = sys.stdin.read(1)
                
                result = self.handle_key(key)
                if result == "quit":
                    break


def run_gui() -> None:
    FrogMPEGGui().run()
