"""
FrogMPEG package initializer.
"""

from .__version__ import __version__

# Re-export main modules for convenience
from . import img2video
from . import video2img
from . import launcher

__all__ = [
    "__version__",
    "img2video",
    "video2img",
    "launcher",
]


