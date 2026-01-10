"""
Main launcher GUI for FrogMPEG - mode selection screen.
Uses shared theme for consistent colors and shortcuts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from rich import box
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

try:
    import msvcrt  # type: ignore
except ImportError:  # pragma: no cover
    msvcrt = None  # type: ignore

# Import shared theme
from ..theme import (
    COLORS,
    create_footer_text,
    fix_windows_encoding,
    resize_console_window,
)

console = Console()


@dataclass
class ModeOption:
    """A selectable mode in the launcher."""
    key: str
    title: str
    description: str
    icon: str


MODES: List[ModeOption] = [
    ModeOption(
        key="img2video",
        title="Image to Video",
        description="Convert image sequences (PNG, JPEG) into video files.\n"
                    "Supports H.264, HEVC, and ProRes codecs.",
        icon="🎬",
    ),
    ModeOption(
        key="video2img",
        title="Video to Images",
        description="Extract frames from video files into image sequences.\n"
                    "Supports PNG, JPEG, TIFF, and EXR output.",
        icon="🖼️",
    ),
]


class LauncherGui:
    """Main launcher for selecting conversion mode."""
    
    def __init__(self) -> None:
        self.modes = MODES
        self.selected_idx = 0
    
    def create_header(self) -> Panel:
        """Create the header panel with ASCII logo in frog theme."""
        logo = Text()
        logo.append("\n")
        logo.append("    ███████╗██████╗  ██████╗  ██████╗ ███╗   ███╗██████╗ ███████╗ ██████╗ \n", style=COLORS["success"])
        logo.append("    ██╔════╝██╔══██╗██╔═══██╗██╔════╝ ████╗ ████║██╔══██╗██╔════╝██╔════╝ \n", style=COLORS["bright"])
        logo.append("    █████╗  ██████╔╝██║   ██║██║  ███╗██╔████╔██║██████╔╝█████╗  ██║  ███╗\n", style=COLORS["bright"])
        logo.append("    ██╔══╝  ██╔══██╗██║   ██║██║   ██║██║╚██╔╝██║██╔═══╝ ██╔══╝  ██║   ██║\n", style=COLORS["primary"])
        logo.append("    ██║     ██║  ██║╚██████╔╝╚██████╔╝██║ ╚═╝ ██║██║     ███████╗╚██████╔╝\n", style=COLORS["primary"])
        logo.append("    ╚═╝     ╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝     ╚═╝╚═╝     ╚══════╝ ╚═════╝ \n", style=COLORS["muted"])
        logo.append("\n")
        logo.append("                     🐸 Multi-Format Video Converter 🐸", style=COLORS["emerald"])
        logo.append("\n")
        
        return Panel(logo, box=box.DOUBLE, style=COLORS["bright"])
    
    def create_mode_panel(self, mode: ModeOption, is_selected: bool) -> Panel:
        """Create a panel for a single mode option using theme colors."""
        content = Text()
        
        # Mode icon and title with click instruction
        content.append(f"{mode.icon}  ", style="")
        if is_selected:
            content.append(f"{mode.title}\n", style=COLORS["success"])
            content.append(mode.description, style=COLORS["emerald"])
        else:
            content.append(f"{mode.title}\n", style=COLORS["muted"])
            content.append(mode.description, style=COLORS["muted"])
        
        style = COLORS["active_border"] if is_selected else COLORS["inactive_border"]
        border = box.DOUBLE if is_selected else box.ROUNDED
        
        # Show number in title for "clicking"
        number = "1" if mode.key == "img2video" else "2"
        if is_selected:
            title = f"► Press [{number}] or [Enter] to select"
        else:
            title = f"  Press [{number}] to select"
        
        return Panel(
            content,
            title=title,
            box=border,
            style=style,
            padding=(0, 1),
        )
    
    def create_modes_layout(self) -> Layout:
        """Create the modes selection layout."""
        layout = Layout()
        
        panels = []
        for idx, mode in enumerate(self.modes):
            is_selected = idx == self.selected_idx
            panels.append(Layout(self.create_mode_panel(mode, is_selected)))
        
        layout.split_row(*panels)
        return layout
    
    def create_footer(self) -> Panel:
        """Create the footer with controls using theme colors."""
        shortcuts = [
            ("[1]", "Image→Video", "success"),
            ("[2]", "Video→Images", "success"),
            ("[←→]", "Navigate", "emerald"),
            ("[Enter]", "Confirm", "gold"),
            ("[Q]", "Quit", "muted"),
        ]
        return Panel(create_footer_text(shortcuts), box=box.ROUNDED, style=COLORS["inactive_border"])
    
    def render(self) -> Layout:
        """Render the full launcher UI."""
        layout = Layout()
        layout.split_column(
            Layout(self.create_header(), name="header"),
            Layout(self.create_modes_layout(), name="modes"),
            Layout(self.create_footer(), name="footer", size=3),
        )
        return layout
    
    def handle_key(self, key: str) -> Optional[str]:
        """Handle keyboard input. Returns mode key or 'quit'. Returns tuple (action, state_changed)."""
        if key.lower() == "q":
            return "quit"
        
        # Direct number selection
        if key == "1":
            return "img2video"
        if key == "2":
            return "video2img"
        
        # Arrow navigation (same key codes as other GUIs)
        old_idx = self.selected_idx
        if key == "K":  # left
            self.selected_idx = max(0, self.selected_idx - 1)
        elif key == "M":  # right
            self.selected_idx = min(len(self.modes) - 1, self.selected_idx + 1)
        
        # Enter to select
        if key == "\r":
            return self.modes[self.selected_idx].key
        
        # Return whether selection changed
        return ("continue", old_idx != self.selected_idx)
    
    def run(self) -> str:
        """Main loop. Returns selected mode key or 'quit'."""
        fix_windows_encoding()
        resize_console_window()
        
        # Clear screen and position at top
        console.clear()
        
        # Force initial render before starting Live context
        import time
        time.sleep(0.1)
        
        # Use very low refresh rate - Rich requires > 0
        # We only call live.update() on key press anyway
        with Live(self.render(), console=console, screen=True, refresh_per_second=0.1) as live:
            while True:
                if msvcrt:
                    key = msvcrt.getch()
                    if key in (b"\x00", b"\xe0"):
                        key = msvcrt.getch()
                    key = key.decode("utf-8", errors="ignore")
                else:  # pragma: no cover
                    import sys
                    key = sys.stdin.read(1)
                
                result = self.handle_key(key)
                
                # Check if it's a mode selection or quit
                if isinstance(result, str) and result != "continue":
                    return result
                
                # Only update if selection changed
                if isinstance(result, tuple) and result[1]:  # state_changed = True
                    live.update(self.render(), refresh=True)


def run_launcher() -> None:
    """
    Run the launcher and dispatch to selected mode.
    Handles the full application lifecycle with mode switching.
    """
    while True:
        # Clear before showing launcher
        console.clear()
        
        launcher = LauncherGui()
        mode = launcher.run()
        
        if mode == "quit":
            break
        elif mode == "img2video":
            console.clear()
            from ..img2video.gui import run_gui
            result = run_gui()
            if result == "quit":
                break
            # result == "launcher" continues loop
        elif mode == "video2img":
            console.clear()
            from ..video2img.gui import run_gui
            result = run_gui()
            if result == "quit":
                break
            # result == "launcher" continues loop
    
    console.clear()
    console.print(f"[{COLORS['success']}]Thanks for using FrogMPEG![/]")
