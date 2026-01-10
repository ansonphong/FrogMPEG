"""
Format registry and codec definitions for FrogMPEG.

This module defines all supported output formats, codecs, and their configurations
for FFmpeg encoding.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class CodecProfile:
    """Defines a specific codec configuration."""
    
    key: str  # Unique identifier (e.g., "h264-gpu", "prores-422")
    display_name: str
    codec_name: str  # FFmpeg codec name
    encoder_name: str  # FFmpeg encoder (e.g., "h264_nvenc", "prores_ks")
    container: str  # File extension: mp4, mov
    
    # Encoding settings
    supports_gpu: bool = False
    supports_alpha: bool = False
    pixel_format: str = "yuv420p"
    
    # Codec-specific settings
    profile: Optional[str] = None  # For ProRes, HEVC profiles
    quality_mode: str = "bitrate"  # "bitrate" or "qscale"
    
    # UI display
    description: str = ""
    use_case: str = ""
    badge: str = ""  # Emoji/symbol for UI
    file_size_multiplier: float = 1.0  # Relative to H.264
    
    # Advanced settings
    extra_flags: Dict[str, str] = field(default_factory=dict)


# ============================================================================
# FORMAT REGISTRY - All supported codecs
# ============================================================================

# H.264 Formats
H264_NVENC_MP4 = CodecProfile(
    key="h264-nvenc-mp4",
    display_name="H.264 (GPU - NVENC)",
    codec_name="h264",
    encoder_name="h264_nvenc",
    container="mp4",
    supports_gpu=True,
    pixel_format="yuv420p",
    quality_mode="bitrate",
    description="Hardware-accelerated H.264 encoding using NVIDIA GPU",
    use_case="Fast encoding, universal playback",
    badge="🟢",
    file_size_multiplier=1.0,
)

H264_CPU_MP4 = CodecProfile(
    key="h264-cpu-mp4",
    display_name="H.264 (CPU - x264)",
    codec_name="h264",
    encoder_name="libx264",
    container="mp4",
    supports_gpu=False,
    pixel_format="yuv420p",
    quality_mode="bitrate",
    description="Software H.264 encoding with maximum compatibility",
    use_case="Universal playback, no GPU required",
    badge="🔵",
    file_size_multiplier=1.0,
)

H264_CPU_MOV = CodecProfile(
    key="h264-cpu-mov",
    display_name="H.264 (CPU - x264)",
    codec_name="h264",
    encoder_name="libx264",
    container="mov",
    supports_gpu=False,
    pixel_format="yuv420p",
    quality_mode="bitrate",
    description="H.264 in MOV container for professional workflows",
    use_case="Editing compatibility, MOV preference",
    badge="🔵",
    file_size_multiplier=1.0,
)

# HEVC/H.265 Formats
HEVC_NVENC_MP4 = CodecProfile(
    key="hevc-nvenc-mp4",
    display_name="HEVC/H.265 (GPU - NVENC)",
    codec_name="hevc",
    encoder_name="hevc_nvenc",
    container="mp4",
    supports_gpu=True,
    pixel_format="yuv420p",
    quality_mode="bitrate",
    description="Hardware-accelerated HEVC encoding, 50% smaller files",
    use_case="4K video, efficient storage, modern devices",
    badge="🟢",
    file_size_multiplier=0.5,
)

HEVC_CPU_MP4 = CodecProfile(
    key="hevc-cpu-mp4",
    display_name="HEVC/H.265 (CPU - x265)",
    codec_name="hevc",
    encoder_name="libx265",
    container="mp4",
    supports_gpu=False,
    pixel_format="yuv420p",
    quality_mode="bitrate",
    description="Software HEVC encoding with best compression",
    use_case="Maximum quality/size ratio, slower encoding",
    badge="🔵",
    file_size_multiplier=0.5,
)

# Apple ProRes Formats
PRORES_PROXY = CodecProfile(
    key="prores-proxy-mov",
    display_name="ProRes Proxy",
    codec_name="prores",
    encoder_name="prores_ks",
    container="mov",
    supports_gpu=False,
    pixel_format="yuv422p10le",
    profile="0",
    quality_mode="qscale",
    description="Lowest quality ProRes for offline editing",
    use_case="Rough cuts, proxy workflows",
    badge="🟣",
    file_size_multiplier=2.0,
)

PRORES_LT = CodecProfile(
    key="prores-lt-mov",
    display_name="ProRes LT",
    codec_name="prores",
    encoder_name="prores_ks",
    container="mov",
    supports_gpu=False,
    pixel_format="yuv422p10le",
    profile="1",
    quality_mode="qscale",
    description="Light ProRes for everyday editing",
    use_case="Standard editing, web delivery",
    badge="🟣",
    file_size_multiplier=4.0,
)

PRORES_422 = CodecProfile(
    key="prores-422-mov",
    display_name="ProRes 422",
    codec_name="prores",
    encoder_name="prores_ks",
    container="mov",
    supports_gpu=False,
    pixel_format="yuv422p10le",
    profile="2",
    quality_mode="qscale",
    description="Standard ProRes for professional editing (10-bit)",
    use_case="Broadcast, professional workflows",
    badge="🟣",
    file_size_multiplier=8.0,
)

PRORES_422_HQ = CodecProfile(
    key="prores-422-hq-mov",
    display_name="ProRes 422 HQ",
    codec_name="prores",
    encoder_name="prores_ks",
    container="mov",
    supports_gpu=False,
    pixel_format="yuv422p10le",
    profile="3",
    quality_mode="qscale",
    description="High quality ProRes for demanding work (10-bit)",
    use_case="High-end production, mastering",
    badge="🟣",
    file_size_multiplier=12.0,
)

PRORES_4444 = CodecProfile(
    key="prores-4444-mov",
    display_name="ProRes 4444",
    codec_name="prores",
    encoder_name="prores_ks",
    container="mov",
    supports_gpu=False,
    supports_alpha=True,
    pixel_format="yuva444p10le",
    profile="4",
    quality_mode="qscale",
    description="ProRes with alpha channel support for VFX (10-bit)",
    use_case="VFX, compositing, transparency",
    badge="🟡",
    file_size_multiplier=15.0,
)

PRORES_4444_XQ = CodecProfile(
    key="prores-4444-xq-mov",
    display_name="ProRes 4444 XQ",
    codec_name="prores",
    encoder_name="prores_ks",
    container="mov",
    supports_gpu=False,
    supports_alpha=True,
    pixel_format="yuva444p10le",
    profile="5",
    quality_mode="qscale",
    description="Highest quality ProRes with alpha (10-bit)",
    use_case="Maximum quality, color grading, archival",
    badge="🟡",
    file_size_multiplier=20.0,
)

# ============================================================================
# REGISTRY ORGANIZATION
# ============================================================================

ALL_CODECS: List[CodecProfile] = [
    # H.264
    H264_NVENC_MP4,
    H264_CPU_MP4,
    H264_CPU_MOV,
    # HEVC
    HEVC_NVENC_MP4,
    HEVC_CPU_MP4,
    # ProRes
    PRORES_PROXY,
    PRORES_LT,
    PRORES_422,
    PRORES_422_HQ,
    PRORES_4444,
    PRORES_4444_XQ,
]

# Container mappings
CODECS_BY_CONTAINER: Dict[str, List[CodecProfile]] = {
    "mp4": [
        H264_NVENC_MP4,
        H264_CPU_MP4,
        HEVC_NVENC_MP4,
        HEVC_CPU_MP4,
    ],
    "mov": [
        H264_CPU_MOV,
        PRORES_PROXY,
        PRORES_LT,
        PRORES_422,
        PRORES_422_HQ,
        PRORES_4444,
        PRORES_4444_XQ,
    ],
}

# Codec family groupings
CODEC_FAMILIES: Dict[str, List[CodecProfile]] = {
    "h264": [H264_NVENC_MP4, H264_CPU_MP4, H264_CPU_MOV],
    "hevc": [HEVC_NVENC_MP4, HEVC_CPU_MP4],
    "prores": [
        PRORES_PROXY,
        PRORES_LT,
        PRORES_422,
        PRORES_422_HQ,
        PRORES_4444,
        PRORES_4444_XQ,
    ],
}

# Quick lookup by key
CODECS_BY_KEY: Dict[str, CodecProfile] = {codec.key: codec for codec in ALL_CODECS}

# Default codec per container
DEFAULT_CODEC: Dict[str, str] = {
    "mp4": "h264-nvenc-mp4",
    "mov": "prores-422-mov",
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_codec(key: str) -> Optional[CodecProfile]:
    """Get codec profile by key."""
    return CODECS_BY_KEY.get(key)


def get_codecs_for_container(container: str) -> List[CodecProfile]:
    """Get all codec profiles available for a container."""
    return CODECS_BY_CONTAINER.get(container.lower(), [])


def get_default_codec_for_container(container: str) -> Optional[CodecProfile]:
    """Get the default codec for a container."""
    default_key = DEFAULT_CODEC.get(container.lower())
    if default_key:
        return get_codec(default_key)
    return None


def get_available_containers() -> List[str]:
    """Get list of supported container formats."""
    return list(CODECS_BY_CONTAINER.keys())


def get_codec_family(family: str) -> List[CodecProfile]:
    """Get all codecs in a family (h264, hevc, prores)."""
    return CODEC_FAMILIES.get(family.lower(), [])


def validate_codec_key(key: str) -> bool:
    """Check if a codec key is valid."""
    return key in CODECS_BY_KEY


def get_gpu_codecs() -> List[CodecProfile]:
    """Get all GPU-accelerated codecs."""
    return [codec for codec in ALL_CODECS if codec.supports_gpu]


def get_alpha_codecs() -> List[CodecProfile]:
    """Get all codecs that support alpha channel."""
    return [codec for codec in ALL_CODECS if codec.supports_alpha]
