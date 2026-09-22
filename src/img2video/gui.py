"""
btop-inspired CLI GUI for image-to-video conversion.
Uses shared theme for consistent colors and shortcuts.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from rich import box
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

try:
    import msvcrt  # type: ignore
except ImportError:  # pragma: no cover - non-Windows fallback
    msvcrt = None  # type: ignore

# Import shared theme
from ..theme import (
    COLORS,
    create_header,
    create_footer_text,
    style_selected,
    style_indicator,
    get_panel_style,
    fix_windows_encoding,
    resize_console_window,
)

from ..config import Config, load_config
from ..dialogs import browse_for_sequence_folder
from ..formats import (
    CodecProfile,
    get_available_containers,
    get_codecs_for_container,
)
from .converter import ConversionRequest, convert_folder, list_images

console = Console()


@dataclass
class FolderInfo:
    name: str
    path: Path
    file_count: int
    mod_time: datetime
    sample_names: List[str] = field(default_factory=list)


class Img2VideoGui:
    """GUI for converting image sequences to video."""
    
    def __init__(self, folder: Optional[Path] = None) -> None:
        self.config: Config = load_config()
        self.folders: List[FolderInfo] = []
        self.extensions = ["jpeg", "jpg", "png"]
        self.scan_root = folder.resolve() if folder else self.config.renders_folder
        
        # Navigation state
        self.selected_folder_idx = 0
        self.selected_extension_idx = 0
        self.preset_names = list(self.config.presets.keys()) or ["defaults"]
        self.selected_preset_idx = 0
        
        # Format selection state
        self.containers = get_available_containers()
        self.selected_container_idx = 0
        self.selected_codec_idx = 0
        
        # Navigation sections: folders -> presets -> extensions -> container -> codec
        self.sections = ["folders", "presets", "extensions", "container", "codec"]
        self.current_section = "folders"
        
        self.scan_folders()

    def _image_count(self, folder: Path) -> int:
        return sum(len(list(folder.glob(f"*.{ext}"))) for ext in self.extensions)

    def _sample_names(self, folder: Path) -> List[str]:
        best_ext = max(self.extensions, key=lambda ext: len(list(folder.glob(f"*.{ext}"))))
        files = list_images(folder, best_ext)
        if not files:
            return []
        shown = [path.name for path in files[:5]]
        if len(files) > 5:
            shown.append(f"… and {len(files) - 5} more")
        return shown

    def _folder_info(self, folder: Path) -> Optional[FolderInfo]:
        file_count = self._image_count(folder)
        if file_count == 0:
            return None
        mod_time = datetime.fromtimestamp(folder.stat().st_mtime)
        return FolderInfo(folder.name, folder, file_count, mod_time, self._sample_names(folder))

    def _prefer_extension(self, folder: Path) -> None:
        counts = {ext: len(list(folder.glob(f"*.{ext}"))) for ext in self.extensions}
        best = max(self.extensions, key=lambda ext: counts[ext])
        if counts[best] > 0:
            self.selected_extension_idx = self.extensions.index(best)

    def scan_folders(self) -> None:
        results: List[FolderInfo] = []
        root = self.scan_root
        opened_explicitly = root != self.config.renders_folder
        if root.is_dir():
            # A sequence folder contains the frames directly. A renders parent
            # contains one folder per sequence. Include the path itself only
            # when the user pointed the GUI at it.
            if opened_explicitly:
                own = self._folder_info(root)
                if own:
                    results.append(own)
            try:
                children = [entry for entry in root.iterdir() if entry.is_dir()]
            except OSError:
                children = []
            for entry in children:
                info = self._folder_info(entry)
                if info:
                    results.append(info)

        results.sort(key=lambda f: f.mod_time, reverse=True)
        self.folders = results
        if opened_explicitly and any(folder.path == root for folder in results):
            self.selected_folder_idx = next(i for i, folder in enumerate(results) if folder.path == root)
        elif self.config.ui.auto_select_latest and results:
            self.selected_folder_idx = 0
        elif self.folders:
            self.selected_folder_idx = min(self.selected_folder_idx, len(self.folders) - 1)
        if opened_explicitly and self.folders:
            self._prefer_extension(self.folders[self.selected_folder_idx].path)

    # UI helpers ---------------------------------------------------------
    def create_header_panel(self) -> Panel:
        """Use shared header with mode-specific subtitle."""
        return create_header("FrogMPEG", "Image to Video Converter")

    def create_folders_panel(self) -> Panel:
        table = Table(show_header=False, expand=True, box=None)
        table.add_column("", width=2)
        table.add_column("Folder", style=COLORS["emerald"])
        table.add_column("Files", justify="right", style=COLORS["gold"])
        table.add_column("Modified", justify="right", style=COLORS["amber"])

        is_active = self.current_section == "folders"
        
        if not self.folders:
            table.add_row("", "[dim]No image sequences in this folder[/]", "", "")
        else:
            show_files = len(self.folders) == 1 and bool(self.folders[0].sample_names)
            visible = self.folders if show_files else self.folders[:8]
            for idx, folder in enumerate(visible):
                is_selected = idx == self.selected_folder_idx
                indicator, ind_style = style_indicator(is_selected, is_active)
                
                if is_selected:
                    style = COLORS["active_selected"] if is_active else COLORS["inactive_selected"]
                else:
                    style = ""
                
                table.add_row(
                    Text(indicator, style=ind_style),
                    Text(folder.name, style=style),
                    Text(str(folder.file_count), style=style if is_selected else COLORS["gold"]),
                    Text(folder.mod_time.strftime("%Y-%m-%d %H:%M"), style=style if is_selected else COLORS["amber"]),
                )
                if show_files:
                    for name in folder.sample_names:
                        table.add_row("", Text(f"  {name}", style=COLORS["muted"]), "", "")

        if self.scan_root != self.config.renders_folder:
            label = f"[1] {self.scan_root.name}"
        else:
            label = "[1] Folders"
        title = f"{label} (↑↓)" if is_active else label
        return Panel(table, title=title, box=box.ROUNDED, style=get_panel_style(is_active))

    def create_settings_panel(self) -> Panel:
        table = Table(show_header=False, expand=True, box=None)
        table.add_column("Setting", width=14, style=COLORS["label"])
        table.add_column("Value")

        is_active_presets = self.current_section == "presets"
        is_active_extensions = self.current_section == "extensions"
        
        # Presets
        preset_display = "  ".join(
            style_selected(name, i == self.selected_preset_idx, is_active_presets)
            for i, name in enumerate(self.preset_names)
        )
        table.add_row("[2] Preset:", preset_display)

        # Extensions
        ext_display = "  ".join(
            style_selected(ext, i == self.selected_extension_idx, is_active_extensions)
            for i, ext in enumerate(self.extensions)
        )
        table.add_row("[3] Extension:", ext_display)

        is_active = self.current_section in ["presets", "extensions"]
        title = "Settings (Tab + ←→)" if is_active else "Settings"
        return Panel(table, title=title, box=box.ROUNDED, style=get_panel_style(is_active))

    def create_format_panel(self) -> Panel:
        """Two-level format selection panel with frog theme."""
        table = Table(show_header=False, expand=True, box=None)
        table.add_column("", width=2)
        table.add_column("Format")
        table.add_column("Details", style=COLORS["description"])

        is_active_container = self.current_section == "container"
        is_active_codec = self.current_section == "codec"
        is_active = is_active_container or is_active_codec
        
        # Container selection
        container_row = []
        for i, container in enumerate(self.containers):
            container_row.append(
                style_selected(container.upper(), i == self.selected_container_idx, is_active_container)
            )
        
        table.add_row("", f"[{COLORS['label']}][4] Container:[/]", "  ".join(container_row))
        
        # Codec selection for selected container
        selected_container = self.containers[self.selected_container_idx]
        codecs = get_codecs_for_container(selected_container)
        
        # Show first few codecs in compact form
        for idx, codec in enumerate(codecs[:6]):
            is_selected = idx == self.selected_codec_idx
            indicator, ind_style = style_indicator(is_selected, is_active_codec)
            
            # Build badges with green theme
            badges = []
            if codec.supports_gpu:
                badges.append(f"[{COLORS['lime']}][GPU][/]")
            else:
                badges.append(f"[{COLORS['muted']}][CPU][/]")
            if codec.supports_alpha:
                badges.append(f"[{COLORS['amber']}][Alpha][/]")
            
            badge_str = " ".join(badges)
            
            if is_selected:
                name_style = COLORS["active_selected"] if is_active_codec else COLORS["inactive_selected"]
                desc_style = "white" if is_active_codec else COLORS["lime"]
            else:
                name_style = COLORS["emerald"]
                desc_style = COLORS["muted"]
            
            table.add_row(
                Text(indicator, style=ind_style),
                f"[{COLORS['label']}][5][/] {badge_str} [{name_style}]{codec.display_name}[/]",
                f"[{desc_style}]{codec.use_case}[/]" if codec.use_case else ""
            )
        
        if len(codecs) > 6:
            table.add_row("", f"[{COLORS['muted']}]... and {len(codecs) - 6} more[/]", "")

        title = "Output Format (Tab + ←→ / ↑↓)" if is_active else "Output Format"
        return Panel(table, title=title, box=box.ROUNDED, style=get_panel_style(is_active))

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
            table.add_row("Folder:", str(folder.path))
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            table.add_row("Frames:", str(folder.file_count))
            table.add_row("Duration:", f"~{minutes}:{seconds:02d} @ {preset.fps}fps")
        
        table.add_row("Resolution:", preset.resolution)
        if preset.fit == "pad":
            table.add_row("Fit:", "pad (whole frame, bars)")
        elif preset.fit == "crop":
            table.add_row("Fit:", "crop (fill the frame)")
        table.add_row("Bitrate:", preset.bitrate)
        table.add_row("", "")
        table.add_row("Output:", f"{codec.display_name}")
        table.add_row("Container:", f".{codec.container}")
        
        # File size estimate
        if folder and folder.file_count > 0:
            bitrate_mbps = float(preset.bitrate.replace("M", ""))
            estimated_mb = (bitrate_mbps * duration / 8) * codec.file_size_multiplier
            if estimated_mb > 1024:
                size_str = f"~{estimated_mb/1024:.1f} GB"
            else:
                size_str = f"~{estimated_mb:.0f} MB"
            table.add_row("Est. Size:", size_str)

        return Panel(table, title="Preview", box=box.ROUNDED, style=COLORS["active_border"])

    def create_footer_panel(self) -> Panel:
        """Use consistent footer shortcuts."""
        shortcuts = [
            ("[S]", "Start", "success"),
            ("[B]", "Browse", "lime"),
            ("[Tab/Enter]", "Next", "emerald"),
            ("[Shift+Tab]", "Previous", "emerald"),
            ("[↑↓]", "Navigate", "muted"),
            ("[←→]", "Switch", "muted"),
            ("[R]", "Refresh", "amber"),
            ("[L]", "Launcher", "muted"),
            ("[Q]", "Quit", "muted"),
        ]
        return Panel(create_footer_text(shortcuts), box=box.ROUNDED, style=COLORS["inactive_border"])

    def render(self) -> Layout:
        """Render the UI with dynamic sizing."""
        layout = Layout()
        layout.split_column(
            Layout(self.create_header_panel(), name="header", size=3),
            Layout(self.create_folders_panel(), name="folders", size=11),
            Layout(self.create_settings_panel(), name="settings", size=5),
            Layout(self.create_format_panel(), name="formats", size=12),
            Layout(self.create_preview_panel(), name="preview", size=12),
            Layout(self.create_footer_panel(), name="footer", size=3),
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
    def handle_key(self, key: str) -> Optional[str]:
        # Universal shortcuts (consistent with other GUIs)
        if key.lower() == "q":
            return "quit"
        if key.lower() == "l":
            return "launcher"  # Return to launcher
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
            idx = self.sections.index(self.current_section)
            self.current_section = self.sections[(idx + 1) % len(self.sections)]
            return None
        if key == "SHIFT_TAB" or key == "\x0f":  # Shift+Tab to move to previous section
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
                f"[{COLORS['success']}]Opening folder browser...[/]\n"
                f"[{COLORS['emerald']}]Select a folder containing image sequences.[/]",
                box=box.ROUNDED,
                style=COLORS["bright"],
            )
        )
        
        selected_folder = browse_for_sequence_folder(self.scan_root)
        
        if selected_folder and selected_folder.exists():
            file_count = sum(
                len(list(selected_folder.glob(f"*.{ext}"))) for ext in self.extensions
            )
            
            if file_count > 0:
                folder_names = [f.name for f in self.folders]
                if selected_folder.name not in folder_names:
                    mod_time = datetime.fromtimestamp(selected_folder.stat().st_mtime)
                    new_folder = FolderInfo(selected_folder.name, selected_folder, file_count, mod_time)
                    self.folders.insert(0, new_folder)
                    self.selected_folder_idx = 0
                    console.print(f"[{COLORS['success']}]✓ Added: {selected_folder.name} ({file_count} files)[/]")
                else:
                    console.print(f"[{COLORS['warning']}]Folder already in list: {selected_folder.name}[/]")
                time.sleep(1)
            else:
                console.print(f"[{COLORS['warning']}]✗ No image files found in selected folder[/]")
                time.sleep(2)
        else:
            console.print(f"[{COLORS['warning']}]No folder selected[/]")
            time.sleep(1)

    def start_conversion(self) -> None:
        if not self.folders:
            console.print(f"[{COLORS['warning']}]No folders available[/]")
            time.sleep(1)
            return

        folder = self.get_selected_folder()
        preset = self.get_selected_preset()
        extension = self.extensions[self.selected_extension_idx]
        codec = self.get_selected_codec()

        console.clear()
        console.print(
            Panel(
                f"[{COLORS['success']}]🐸 Converting[/]\n"
                f"[{COLORS['label']}]Folder:[/] [{COLORS['gold']}]{folder.name}[/]\n"
                f"[{COLORS['label']}]Preset:[/] [{COLORS['gold']}]{preset.name}[/]\n"
                f"[{COLORS['label']}]Extension:[/] [{COLORS['gold']}]{extension}[/]\n"
                f"[{COLORS['label']}]Format:[/] [{COLORS['gold']}]{codec.display_name} (.{codec.container})[/]",
                box=box.ROUNDED,
                style=COLORS["bright"],
            )
        )

        # Output video to the parent folder of the source images
        source_folder_path = folder.path
        output_folder_path = source_folder_path.parent

        request = ConversionRequest(
            folder_name=folder.name,
            preset_name=preset.name if preset.name != "defaults" else None,
            extension=extension,
            output_codec=codec.key,
            source_folder=source_folder_path,
            output_folder=output_folder_path,
        )
        try:
            convert_folder(self.config, request)
        except Exception as exc:  # pragma: no cover
            console.print(f"[{COLORS['error']}]Conversion failed: {exc}[/]")
        console.print(f"\n[{COLORS['muted']}]Press any key to return...[/]")
        if msvcrt:
            msvcrt.getch()
        else:  # pragma: no cover
            input()

    def run(self) -> str:
        """Main GUI loop. Returns 'quit' or 'launcher'."""
        if not self.folders:
            console.print(
                f"[{COLORS['warning']}]No folders with images found in {self.scan_root}[/]"
            )
            return "quit"

        fix_windows_encoding()
        resize_console_window()
        console.clear()
        
        # Use lower refresh rate - only update on key press
        with Live(self.render(), console=console, screen=True, refresh_per_second=4) as live:
            while True:
                if msvcrt:
                    key = msvcrt.getch()
                    if key in (b"\x00", b"\xe0"):
                        next_key = msvcrt.getch()
                        if key == b"\x00" and next_key == b"\x0f":
                            key = b"SHIFT_TAB"
                        else:
                            key = next_key
                    key = key.decode("utf-8", errors="ignore")
                else:  # pragma: no cover
                    key = input()
                
                result = self.handle_key(key)
                if result in ("quit", "launcher"):
                    return result
                
                # Only update when key is pressed
                live.update(self.render(), refresh=True)


def run_gui(folder: Optional[Path] = None) -> str:
    """Run image-to-video GUI. Returns exit action.

    ``folder`` replaces ``renders_folder`` for this session. A sequence folder
    (frames directly inside) is shown with its files. A parent folder lists
    the sequence folders inside it.
    """
    return Img2VideoGui(folder).run()
