"""
File dialog utilities for FrogMPEG.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import Optional


def browse_for_folder(title: str = "Select Folder with Image Sequence", initial_dir: Optional[Path] = None) -> Optional[Path]:
    """
    Open a native OS folder selection dialog.
    
    Args:
        title: Dialog window title
        initial_dir: Initial directory to open (optional)
    
    Returns:
        Path object if folder selected, None if cancelled
    """
    # Create hidden root window
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)  # Bring dialog to front
    
    # Determine initial directory
    if initial_dir and initial_dir.exists():
        start_dir = str(initial_dir)
    else:
        start_dir = str(Path.home())
    
    # Open folder selection dialog
    folder_path = filedialog.askdirectory(
        title=title,
        initialdir=start_dir,
        mustexist=True
    )
    
    # Clean up
    root.destroy()
    
    # Return Path or None
    if folder_path:
        return Path(folder_path)
    return None


def browse_for_renders_folder(config_renders_folder: Optional[Path] = None) -> Optional[Path]:
    """
    Browse for a renders folder, starting from config renders folder if available.
    
    Args:
        config_renders_folder: Renders folder from config (optional)
    
    Returns:
        Path to selected folder or None
    """
    return browse_for_folder(
        title="Select Renders Folder (containing image sequences)",
        initial_dir=config_renders_folder
    )


def browse_for_sequence_folder(renders_folder: Optional[Path] = None) -> Optional[Path]:
    """
    Browse for a specific image sequence folder.
    
    Args:
        renders_folder: Parent renders folder to start from (optional)
    
    Returns:
        Path to selected folder or None
    """
    return browse_for_folder(
        title="Select Image Sequence Folder",
        initial_dir=renders_folder
    )
