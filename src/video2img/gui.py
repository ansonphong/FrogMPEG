"""
btop-inspired CLI GUI for video-to-image extraction.
Uses shared theme for consistent colors and shortcuts.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
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
except ImportError:  # pragma: no cover
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
from ..dialogs import browse_for_video_file
from ..formats import IMAGE_OUTPUT_FORMATS, ImageOutputFormat
from .converter import (
    ExtractionRequest,
    VideoInfo,
    estimate_output_frames,
    estimate_output_size,
    extract_frames,
    probe_video,
)

console = Console()


@dataclass
class ExtractionMode:
    """Defines a frame extraction mode."""
    name: str
    fps: Optional[float]  # None = all frames
    description: str


# Predefined extraction modes
EXTRACTION_MODES: List[ExtractionMode] = [
    ExtractionMode("All Frames", None, "Extract every frame"),
    ExtractionMode("1 fps", 1.0, "1 frame per second"),
    ExtractionMode("5 fps", 5.0, "5 frames per second"),
    ExtractionMode("10 fps", 10.0, "10 frames per second"),
    ExtractionMode("24 fps", 24.0, "24 frames per second"),
    ExtractionMode("30 fps", 30.0, "30 frames per second"),
]


class Video2ImgGui:
    """GUI for extracting frames from video."""
    
    def __init__(self) -> None:
        self.config: Config = load_config()
        
        # Video state
        self.selected_video: Optional[Path] = None
        self.video_info: Optional[VideoInfo] = None
        
        # Output settings
        self.output_formats = IMAGE_OUTPUT_FORMATS
        self.selected_format_idx = 0
        
        self.extraction_modes = EXTRACTION_MODES
        self.selected_mode_idx = 0
        
        # Time range (None = full video)
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        
        # Quality settings
        self.jpeg_quality = 95
        self.png_compression = 6
        
        # Navigation (same pattern as img2video)
        self.sections = ["video", "format", "mode", "quality"]
        self.current_section = "video"
        
        # Scan for recent videos
        self.recent_videos: List[Path] = []
        self.selected_recent_idx = 0
        self.scan_recent_videos()
    
    def scan_recent_videos(self) -> None:
        """Scan output folder for recently created videos."""
        video_extensions = ["mp4", "mov", "mkv", "avi", "webm"]
        videos: List[tuple[Path, datetime]] = []
        
        for ext in video_extensions:
            for video in self.config.output_folder.glob(f"*.{ext}"):
                try:
                    mod_time = datetime.fromtimestamp(video.stat().st_mtime)
                    videos.append((video, mod_time))
                except:
                    pass
        
        videos.sort(key=lambda x: x[1], reverse=True)
        self.recent_videos = [v[0] for v in videos[:10]]
    
    # =========================================================================
    # UI Panel Builders (using shared theme)
    # =========================================================================
    
    def create_header_panel(self) -> Panel:
        """Use shared header with mode-specific subtitle."""
        return create_header("FrogMPEG", "Video to Image Extractor")
    
    def create_video_panel(self) -> Panel:
        """Panel showing selected video or recent videos list."""
        table = Table(show_header=False, expand=True, box=None)
        table.add_column("", width=2)
        table.add_column("Video", style=COLORS["emerald"])
        table.add_column("Size", justify="right", style=COLORS["gold"])
        table.add_column("Duration", justify="right", style=COLORS["amber"])
        
        is_active = self.current_section == "video"
        
        if self.video_info:
            table.add_row(
                "",
                Text(self.video_info.path.name, style=COLORS["active_selected"] if is_active else COLORS["inactive_selected"]),
                self.video_info.file_size_str,
                self.video_info.duration_str,
            )
            table.add_row("", "", "", "")
            table.add_row(
                "",
                f"[{COLORS['label']}]Resolution:[/] {self.video_info.resolution}",
                f"[{COLORS['label']}]FPS:[/] {self.video_info.fps:.2f}",
                f"[{COLORS['label']}]Frames:[/] {self.video_info.frame_count}",
            )
        elif self.recent_videos:
            for idx, video in enumerate(self.recent_videos[:6]):
                is_selected = idx == self.selected_recent_idx
                indicator, ind_style = style_indicator(is_selected, is_active)
                
                try:
                    size = video.stat().st_size / (1024 * 1024)
                    size_str = f"{size:.1f} MB"
                except:
                    size_str = "?"
                
                row_style = COLORS["active_selected"] if (is_selected and is_active) else COLORS["inactive_selected"] if is_selected else ""
                table.add_row(
                    Text(indicator, style=ind_style),
                    Text(video.name[:40], style=row_style),
                    Text(size_str, style=row_style if is_selected else COLORS["gold"]),
                    "",
                )
        else:
            table.add_row("", f"[{COLORS['muted']}]No videos found. Press [B] to browse.[/]", "", "")
        
        title = "[1] Video (↑↓, Enter=Select, B=Browse)" if is_active else "[1] Video"
        return Panel(table, title=title, box=box.ROUNDED, style=get_panel_style(is_active))
    
    def create_format_panel(self) -> Panel:
        """Panel for output format selection."""
        table = Table(show_header=False, expand=True, box=None)
        table.add_column("Setting", width=14, style=COLORS["label"])
        table.add_column("Value")
        
        is_active_format = self.current_section == "format"
        is_active_mode = self.current_section == "mode"
        is_active_quality = self.current_section == "quality"
        
        # Output format selection
        format_display = "  ".join(
            style_selected(fmt.display_name, i == self.selected_format_idx, is_active_format)
            for i, fmt in enumerate(self.output_formats)
        )
        table.add_row("[2] Format:", format_display)
        
        # Extraction mode selection
        mode_display = "  ".join(
            style_selected(mode.name, i == self.selected_mode_idx, is_active_mode)
            for i, mode in enumerate(self.extraction_modes[:4])
        )
        table.add_row("[3] Extract:", mode_display)
        
        # JPEG Quality (only show if JPEG is selected)
        current_format = self.output_formats[self.selected_format_idx]
        if current_format.key == "jpeg":
            quality_style = COLORS["active_selected"] if is_active_quality else COLORS["inactive_selected"] if True else COLORS["gold"]
            quality_bar = self._create_quality_bar()
            table.add_row("[4] Quality:", quality_bar)
        
        is_active = self.current_section in ["format", "mode", "quality"]
        title = "Output Settings (←→, ↑↓ for quality)" if is_active else "Output Settings"
        return Panel(table, title=title, box=box.ROUNDED, style=get_panel_style(is_active))
    
    def _create_quality_bar(self) -> str:
        """Create a visual quality bar for JPEG quality."""
        is_active = self.current_section == "quality"
        
        # Quality bar: 20 segments representing 5% each (from 0-100)
        segments = 20
        filled = int(self.jpeg_quality / 5)  # How many segments to fill
        
        bar_color = COLORS["active_selected"] if is_active else COLORS["success"]
        empty_color = COLORS["muted"]
        
        bar = ""
        for i in range(segments):
            if i < filled:
                bar += "█"
            else:
                bar += "░"
        
        quality_text = f"[{bar_color}]{bar}[/] [{COLORS['gold']}]{self.jpeg_quality}%[/]"
        return quality_text
    
    def create_preview_panel(self) -> Panel:
        """Panel showing extraction preview/estimates."""
        table = Table(show_header=False, expand=False, box=None, padding=(0, 2))
        table.add_column("Label", width=14, style=COLORS["label"], no_wrap=True)
        table.add_column("Value", style=COLORS["gold"], no_wrap=False)
        
        if self.video_info:
            output_format = self.output_formats[self.selected_format_idx]
            extraction_mode = self.extraction_modes[self.selected_mode_idx]
            
            request = ExtractionRequest(
                video_path=self.video_info.path,
                output_folder=self.config.output_folder / f"{self.video_info.path.stem}_frames",
                output_format=output_format.key,
                name_pattern=f"{self.video_info.path.stem}_%05d",
                frame_rate=extraction_mode.fps,
            )
            
            est_frames = estimate_output_frames(self.video_info, request)
            est_size = estimate_output_size(self.video_info, request, est_frames)
            
            table.add_row("Source:", self.video_info.path.name)
            table.add_row("Output:", output_format.display_name)
            table.add_row("Mode:", extraction_mode.name)
            table.add_row("", "")
            table.add_row("Est. Frames:", str(est_frames))
            
            size_str = f"~{est_size / (1024**3):.1f} GB" if est_size > 1024**3 else f"~{est_size / (1024**2):.0f} MB"
            table.add_row("Est. Size:", size_str)
            
            table.add_row("", "")
            table.add_row("Output Dir:", f"{self.video_info.path.stem}_frames")
        else:
            table.add_row("", f"[{COLORS['muted']}]Select a video to see preview[/]")
        
        return Panel(table, title="Preview", box=box.ROUNDED, style=COLORS["active_border"])
    
    def create_footer_panel(self) -> Panel:
        """Use consistent footer shortcuts (same as img2video)."""
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
        layout = Layout()
        layout.split_column(
            Layout(self.create_header_panel(), name="header", size=3),
            Layout(self.create_video_panel(), name="video", size=11),
            Layout(self.create_format_panel(), name="settings", size=5),
            Layout(self.create_preview_panel(), name="preview", size=12),
            Layout(self.create_footer_panel(), name="footer", size=3),
        )
        return layout
    
    # =========================================================================
    # Input Handling (consistent shortcuts with img2video)
    # =========================================================================
    
    def handle_key(self, key: str) -> Optional[str]:
        # Universal shortcuts (same as img2video)
        if key.lower() == "q":
            return "quit"
        if key.lower() == "l":
            return "launcher"
        if key.lower() == "r":
            self.scan_recent_videos()
            return None
        if key.lower() == "b":
            self.browse_for_video()
            return None
        if key.lower() == "s":
            self.start_extraction()
            return None
        if key == "\t" or key == "\r":
            idx = self.sections.index(self.current_section)
            self.current_section = self.sections[(idx + 1) % len(self.sections)]
            return None
        if key == "SHIFT_TAB" or key == "\x0f":
            idx = self.sections.index(self.current_section)
            self.current_section = self.sections[(idx - 1) % len(self.sections)]
            return None
        
        # Section-specific navigation (same key codes as img2video)
        if self.current_section == "video":
            if key == "H":  # up
                self.selected_recent_idx = max(0, self.selected_recent_idx - 1)
            elif key == "P":  # down
                self.selected_recent_idx = min(len(self.recent_videos) - 1, self.selected_recent_idx + 1)
            elif key == "\r" and self.recent_videos:  # enter - select from list
                self.load_video(self.recent_videos[self.selected_recent_idx])
        
        elif self.current_section == "format":
            if key == "K":  # left
                self.selected_format_idx = max(0, self.selected_format_idx - 1)
            elif key == "M":  # right
                self.selected_format_idx = min(len(self.output_formats) - 1, self.selected_format_idx + 1)
        
        elif self.current_section == "mode":
            if key == "K":
                self.selected_mode_idx = max(0, self.selected_mode_idx - 1)
            elif key == "M":
                self.selected_mode_idx = min(len(self.extraction_modes) - 1, self.selected_mode_idx + 1)
        
        elif self.current_section == "quality":
            # Adjust JPEG quality with arrow keys
            if key == "H":  # up - increase quality by 5
                self.jpeg_quality = min(100, self.jpeg_quality + 5)
            elif key == "P":  # down - decrease quality by 5
                self.jpeg_quality = max(50, self.jpeg_quality - 5)
            elif key == "K":  # left - decrease by 1
                self.jpeg_quality = max(50, self.jpeg_quality - 1)
            elif key == "M":  # right - increase by 1
                self.jpeg_quality = min(100, self.jpeg_quality + 1)
        
        return None
    
    def browse_for_video(self) -> None:
        """Open file browser to select video."""
        console.clear()
        console.print(
            Panel(
                f"[{COLORS['success']}]Opening file browser...[/]\n"
                f"[{COLORS['emerald']}]Select a video file to extract frames from.[/]",
                box=box.ROUNDED,
                style=COLORS["bright"],
            )
        )
        
        selected = browse_for_video_file(self.config.output_folder)
        if selected and selected.exists():
            self.load_video(selected)
        else:
            console.print(f"[{COLORS['warning']}]No file selected[/]")
            time.sleep(1)
    
    def load_video(self, video_path: Path) -> None:
        """Load video and probe metadata."""
        try:
            self.video_info = probe_video(self.config, video_path)
            self.selected_video = video_path
            console.print(f"[{COLORS['success']}]Loaded: {video_path.name}[/]")
            time.sleep(0.5)
        except Exception as e:
            console.print(f"[{COLORS['error']}]Failed to load video: {e}[/]")
            time.sleep(2)
    
    def start_extraction(self) -> None:
        """Start the frame extraction process."""
        if not self.video_info:
            console.print(f"[{COLORS['warning']}]No video selected[/]")
            time.sleep(1)
            return
        
        output_format = self.output_formats[self.selected_format_idx]
        extraction_mode = self.extraction_modes[self.selected_mode_idx]
        output_folder = self.config.output_folder / f"{self.video_info.path.stem}_frames"
        
        console.clear()
        console.print(
            Panel(
                f"[{COLORS['success']}]🐸 Extracting Frames[/]\n"
                f"[{COLORS['label']}]Video:[/] [{COLORS['gold']}]{self.video_info.path.name}[/]\n"
                f"[{COLORS['label']}]Format:[/] [{COLORS['gold']}]{output_format.display_name}[/]\n"
                f"[{COLORS['label']}]Mode:[/] [{COLORS['gold']}]{extraction_mode.name}[/]\n"
                f"[{COLORS['label']}]Output:[/] [{COLORS['gold']}]{output_folder}[/]",
                box=box.ROUNDED,
                style=COLORS["bright"],
            )
        )
        
        request = ExtractionRequest(
            video_path=self.video_info.path,
            output_folder=output_folder,
            output_format=output_format.key,
            name_pattern=f"{self.video_info.path.stem}_%05d",
            frame_rate=extraction_mode.fps,
            start_time=self.start_time,
            end_time=self.end_time,
            jpeg_quality=self.jpeg_quality,
            png_compression=self.png_compression,
        )
        
        try:
            extract_frames(self.config, request)
        except Exception as exc:
            console.print(f"[{COLORS['error']}]Extraction failed: {exc}[/]")
        
        console.print(f"\n[{COLORS['muted']}]Press any key to return...[/]")
        if msvcrt:
            msvcrt.getch()
        else:  # pragma: no cover
            input()
    
    def run(self) -> str:
        """Main GUI loop. Returns 'quit' or 'launcher'."""
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
                    import sys
                    key = sys.stdin.read(1)
                
                result = self.handle_key(key)
                if result in ("quit", "launcher"):
                    return result
                
                # Only update when key is pressed
                live.update(self.render(), refresh=True)


def run_gui() -> str:
    """Run video-to-image GUI. Returns exit action."""
    return Video2ImgGui().run()
