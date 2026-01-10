"""
Centralized Frog Theme for FrogMPEG.

All GUIs import colors, shortcuts, and UI helpers from this module
to ensure visual consistency across the application.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Tuple

from rich import box
from rich.panel import Panel
from rich.text import Text


# =============================================================================
# FROG THEME COLOR PALETTE - All greens, emeralds, and yellows
# =============================================================================

COLORS: Dict[str, str] = {
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
    
    # Semantic colors - ACTIVE vs INACTIVE
    "active_selected": "bold white reverse",        # Currently active section's selection (WHITE)
    "inactive_selected": "bold bright_green reverse",  # Inactive section's selection (GREEN)
    "active_border": "bold bright_green",
    "inactive_border": "dark_green",
    "label": "spring_green2",        # Labels/titles
    "value": "yellow",               # Data values
    "description": "dark_sea_green", # Descriptions
    
    # Status colors
    "success": "bold bright_green",
    "warning": "gold3",
    "error": "red",
}


# =============================================================================
# KEYBOARD SHORTCUTS - Consistent across all GUIs
# =============================================================================

@dataclass(frozen=True)
class KeyBinding:
    """A keyboard shortcut definition."""
    key: str           # The key character/code
    display: str       # How to show in footer (e.g., "[S]")
    action: str        # Action identifier
    description: str   # Human-readable description


# Universal shortcuts (same in ALL GUIs)
SHORTCUTS_UNIVERSAL = [
    KeyBinding("s", "[S]", "start", "Start"),
    KeyBinding("b", "[B]", "browse", "Browse"),
    KeyBinding("q", "[Q]", "quit", "Quit"),
    KeyBinding("l", "[L]", "launcher", "Launcher"),
    KeyBinding("r", "[R]", "refresh", "Refresh"),
]

# Navigation shortcuts (consistent across GUIs)
SHORTCUTS_NAVIGATION = [
    KeyBinding("\t", "[Tab]", "next_section", "Next"),
    KeyBinding("\r", "[Enter]", "select", "Select"),
    KeyBinding("SHIFT_TAB", "[Shift+Tab]", "prev_section", "Previous"),
    KeyBinding("H", "[↑]", "up", "↑"),
    KeyBinding("P", "[↓]", "down", "↓"),
    KeyBinding("K", "[←]", "left", "←"),
    KeyBinding("M", "[→]", "right", "→"),
]

# Launcher-specific shortcuts
SHORTCUTS_LAUNCHER = [
    KeyBinding("1", "[1]", "img2video", "Image→Video"),
    KeyBinding("2", "[2]", "video2img", "Video→Images"),
]


# =============================================================================
# SHARED UI HELPERS
# =============================================================================

def create_header(title: str, subtitle: str = "") -> Panel:
    """Create a consistent header panel across all GUIs."""
    if subtitle:
        content = Text(title, style=COLORS["success"], justify="center")
        content.append(f"\n{subtitle}", style=COLORS["emerald"])
    else:
        content = Text(title, style=COLORS["success"], justify="center")
    return Panel(content, style=COLORS["bright"], box=box.ROUNDED, height=3)


def create_footer_text(shortcuts: List[Tuple[str, str, str]]) -> Text:
    """
    Create footer text from list of (display, description, style_key) tuples.
    
    Example: [("[S]", "Start", "success"), ("[Q]", "Quit", "muted")]
    """
    footer = Text()
    for display, desc, style_key in shortcuts:
        style = COLORS.get(style_key, style_key)
        footer.append(f"{display} {desc}  ", style=style)
    return footer


def style_selected(text: str, is_selected: bool, is_active: bool = True) -> str:
    """
    Return Rich markup for selected/unselected text.
    
    Args:
        text: The text to style
        is_selected: Whether this item is selected
        is_active: Whether the containing section is currently active
    """
    if is_selected:
        style = COLORS["active_selected"] if is_active else COLORS["inactive_selected"]
        return f"[{style}] {text} [/]"
    else:
        return f"[{COLORS['muted']}]{text}[/]"


def style_indicator(is_selected: bool, is_active: bool = True) -> Tuple[str, str]:
    """
    Return (indicator_char, style) for list selection.
    
    Args:
        is_selected: Whether this item is selected
        is_active: Whether the containing section is currently active
    """
    if is_selected:
        if is_active:
            return ("►", "bold white")
        else:
            return ("►", COLORS["bright"])
    else:
        return (" ", COLORS["muted"])


def get_panel_style(is_active: bool) -> str:
    """Get border style for active/inactive panels."""
    return COLORS["active_border"] if is_active else COLORS["inactive_border"]


# =============================================================================
# CONSOLE WINDOW SIZING
# =============================================================================

def resize_console_window(cols: int = 120, lines: int = 50) -> None:
    """Resize the console window to accommodate the GUI."""
    if sys.platform == "win32":
        try:
            os.system(f"mode con: cols={cols} lines={lines}")
        except Exception:
            pass  # If resizing fails, continue anyway


# =============================================================================
# WINDOWS CONSOLE ENCODING FIX
# =============================================================================

def fix_windows_encoding() -> None:
    """Fix Windows console encoding for emoji/unicode support."""
    if sys.platform == "win32":
        import codecs
        # Only fix if we're in a real terminal, not already wrapped
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
            sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, errors="replace")
        os.environ["PYTHONIOENCODING"] = "utf-8"
