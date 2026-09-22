"""
Configuration loading and validation for FrogMPEG.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .formats import CodecProfile, get_codec


class ConfigError(RuntimeError):
    """Raised when the configuration file is invalid."""


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / "config.json"
CONFIG_EXAMPLE_FILE = PROJECT_ROOT / "config.example.json"


@dataclass(frozen=True)
class OutputCodec:
    """Output codec configuration for a preset or conversion request."""
    
    codec_profile: CodecProfile
    
    @property
    def container(self) -> str:
        return self.codec_profile.container
    
    @property
    def codec_key(self) -> str:
        return self.codec_profile.key
    
    @property
    def extension(self) -> str:
        return self.codec_profile.container


FIT_MODES = ("stretch", "pad", "crop")


@dataclass(frozen=True)
class Preset:
    name: str
    resolution: str
    bitrate: str
    fps: int
    description: str = ""
    output_codec: Optional[OutputCodec] = None  # If None, uses defaults
    fit: str = "stretch"  # stretch | pad | crop
    faststart: bool = False

    @property
    def width(self) -> int:
        return int(self.resolution.split("x")[0])

    @property
    def height(self) -> int:
        return int(self.resolution.split("x")[1])


@dataclass(frozen=True)
class Defaults:
    resolution: str
    bitrate: str
    file_extension: str
    fps: int
    preset_name: Optional[str] = None
    output_codec: Optional[str] = None  # Default codec key (e.g., "h264-nvenc-mp4")


@dataclass(frozen=True)
class EncodingSettings:
    use_gpu: bool
    gpu_preset: str
    cpu_preset: str
    tune: str
    pixel_format: str
    keyframe_interval: int
    b_frames: int
    rc_lookahead: int
    spatial_aq: int
    temporal_aq: int


@dataclass(frozen=True)
class UISettings:
    theme: str
    show_file_count: bool
    auto_select_latest: bool


@dataclass(frozen=True)
class ExtractionDefaults:
    """Default settings for video-to-image extraction."""
    output_format: str = "png"
    jpeg_quality: int = 95
    png_compression: int = 6
    name_pattern: str = "{video_name}_%05d"


@dataclass(frozen=True)
class Config:
    project_name: str
    renders_folder: Path
    output_folder: Path
    ffmpeg_path: Path
    auto_create_output: bool
    defaults: Defaults
    presets: Dict[str, Preset]
    encoding: EncodingSettings
    ui: UISettings
    extraction: ExtractionDefaults  # NEW: Extraction defaults

    def get_preset(self, name: Optional[str]) -> Preset:
        if name:
            if name not in self.presets:
                raise ConfigError(f"Preset '{name}' not found in config.json")
            return self.presets[name]
        if self.defaults.preset_name:
            if self.defaults.preset_name not in self.presets:
                raise ConfigError(
                    f"Default preset '{self.defaults.preset_name}' defined in defaults.preset_name "
                    "was not found in presets array."
                )
            return self.presets[self.defaults.preset_name]

        # Build preset from defaults on the fly
        return Preset(
            name="defaults",
            resolution=self.defaults.resolution,
            bitrate=self.defaults.bitrate,
            fps=self.defaults.fps,
            description="Default configuration"
        )
    
    def get_output_codec(self, codec_key: Optional[str] = None) -> OutputCodec:
        """Get output codec from codec key, falling back to defaults."""
        # Use provided key
        if codec_key:
            codec = get_codec(codec_key)
            if not codec:
                raise ConfigError(f"Unknown codec key: {codec_key}")
            return OutputCodec(codec_profile=codec)
        
        # Use default from config
        if self.defaults.output_codec:
            codec = get_codec(self.defaults.output_codec)
            if not codec:
                raise ConfigError(
                    f"Default output codec '{self.defaults.output_codec}' is invalid"
                )
            return OutputCodec(codec_profile=codec)
        
        # Fall back to H.264 NVENC MP4 (original behavior)
        codec = get_codec("h264-nvenc-mp4")
        if not codec:
            raise ConfigError("Default H.264 codec not found in registry")
        return OutputCodec(codec_profile=codec)


def ensure_config_exists() -> Path:
    """
    Ensure config.json exists. If missing, copy from config.example.json.
    Returns the path to the config file.
    """
    if CONFIG_FILE.exists():
        return CONFIG_FILE

    if not CONFIG_EXAMPLE_FILE.exists():
        raise ConfigError(
            "config.example.json is missing. Please restore it from the repository."
        )

    CONFIG_FILE.write_text(CONFIG_EXAMPLE_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    return CONFIG_FILE


def _load_raw_config() -> Dict[str, Any]:
    config_path = CONFIG_FILE if CONFIG_FILE.exists() else ensure_config_exists()
    with config_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _validate_required(data: Dict[str, Any], key: str) -> Any:
    if key not in data:
        raise ConfigError(f"Missing required key '{key}' in config.json")
    return data[key]


def _load_presets(presets_data: List[Dict[str, Any]]) -> Dict[str, Preset]:
    presets: Dict[str, Preset] = {}
    for preset in presets_data:
        name = _validate_required(preset, "name")
        resolution = _validate_required(preset, "resolution")
        bitrate = _validate_required(preset, "bitrate")
        fps = int(_validate_required(preset, "fps"))
        description = preset.get("description", "")
        fit = preset.get("fit", "stretch")
        if fit not in FIT_MODES:
            raise ConfigError(
                f"Preset '{name}' has unknown fit '{fit}'. Use stretch, pad, or crop."
            )
        faststart = bool(preset.get("faststart", False))
        
        # Load output codec if specified
        output_codec = None
        output_codec_key = preset.get("output_codec")
        if output_codec_key:
            codec = get_codec(output_codec_key)
            if not codec:
                raise ConfigError(
                    f"Preset '{name}' references unknown output codec: {output_codec_key}"
                )
            output_codec = OutputCodec(codec_profile=codec)

        presets[name] = Preset(
            name=name,
            resolution=resolution,
            bitrate=bitrate,
            fps=fps,
            description=description,
            output_codec=output_codec,
            fit=fit,
            faststart=faststart,
        )
    return presets


def load_config() -> Config:
    """
    Load and validate configuration data.
    """
    raw = _load_raw_config()

    project_name = _validate_required(raw, "project_name")

    def resolve_path(value: str) -> Path:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = (PROJECT_ROOT / path).resolve()
        return path

    renders_folder = resolve_path(_validate_required(raw, "renders_folder"))
    output_folder = resolve_path(_validate_required(raw, "output_folder"))
    ffmpeg_path = resolve_path(_validate_required(raw, "ffmpeg_path"))
    auto_create_output = bool(raw.get("auto_create_output", True))

    defaults_data = _validate_required(raw, "defaults")
    defaults = Defaults(
        resolution=_validate_required(defaults_data, "resolution"),
        bitrate=_validate_required(defaults_data, "bitrate"),
        file_extension=_validate_required(defaults_data, "file_extension"),
        fps=int(_validate_required(defaults_data, "fps")),
        preset_name=defaults_data.get("preset_name"),
        output_codec=defaults_data.get("output_codec")
    )

    presets_data = raw.get("presets", [])
    presets = _load_presets(presets_data)

    encoding_data = raw.get("encoding", {})
    encoding = EncodingSettings(
        use_gpu=bool(encoding_data.get("use_gpu", True)),
        gpu_preset=encoding_data.get("gpu_preset", "p7"),
        cpu_preset=encoding_data.get("cpu_preset", "veryslow"),
        tune=encoding_data.get("tune", "animation"),
        pixel_format=encoding_data.get("pixel_format", "yuv420p"),
        keyframe_interval=int(encoding_data.get("keyframe_interval", 60)),
        b_frames=int(encoding_data.get("b_frames", 3)),
        rc_lookahead=int(encoding_data.get("rc_lookahead", 32)),
        spatial_aq=int(encoding_data.get("spatial_aq", 1)),
        temporal_aq=int(encoding_data.get("temporal_aq", 1)),
    )

    ui_data = raw.get("ui", {})
    ui = UISettings(
        theme=ui_data.get("theme", "frog_splash"),
        show_file_count=bool(ui_data.get("show_file_count", True)),
        auto_select_latest=bool(ui_data.get("auto_select_latest", True))
    )
    
    # NEW: Extraction defaults (optional)
    extraction_data = raw.get("extraction", {})
    extraction = ExtractionDefaults(
        output_format=extraction_data.get("output_format", "png"),
        jpeg_quality=int(extraction_data.get("jpeg_quality", 95)),
        png_compression=int(extraction_data.get("png_compression", 6)),
        name_pattern=extraction_data.get("name_pattern", "{video_name}_%05d")
    )

    if auto_create_output and not output_folder.exists():
        output_folder.mkdir(parents=True, exist_ok=True)

    return Config(
        project_name=project_name,
        renders_folder=renders_folder.resolve(),
        output_folder=output_folder.resolve(),
        ffmpeg_path=ffmpeg_path.resolve(),
        auto_create_output=auto_create_output,
        defaults=defaults,
        presets=presets,
        encoding=encoding,
        ui=ui,
        extraction=extraction,  # NEW
    )

