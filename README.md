# 🐸 FrogMPEG

FrogMPEG is a **drop-in, frog-themed image sequence converter** built for fulldome and advanced visualization pipelines. Convert thousands of renders with hardware-accelerated FFmpeg supporting **H.264, HEVC, and Apple ProRes** codecs — all while keeping your project repo clean.

## Features

- **Multi-codec support**: H.264, HEVC/H.265, ProRes (all variants)
- **GPU-accelerated** encoding (NVENC) with automatic CPU fallback
- **Two-level hierarchical GUI** for intuitive container and codec selection
- **ProRes support**: All variants including 4444 with alpha channel
- **Advanced configuration** via `config.json` with presets, encoder tuning, themes
- **Project-friendly layout** – keep FrogMPEG versioned while local config stays private
- **Frog branding** everywhere: ASCII art, emojis, and ribbiting logs

## Supported Formats

### MP4 Container
- **H.264** (NVENC/CPU) - Universal playback
- **HEVC/H.265** (NVENC/CPU) - 50% smaller files, 4K optimized

### MOV Container
- **ProRes Proxy** - Offline editing
- **ProRes LT** - Standard editing
- **ProRes 422** - Broadcast quality (10-bit)
- **ProRes 422 HQ** - High-end production (10-bit)
- **ProRes 4444** - VFX with alpha channel (10-bit)
- **ProRes 4444 XQ** - Maximum quality (10-bit)

## Quick Start

```bash
cd YOUR_PROJECT
git clone https://github.com/yourname/FrogMPEG.git
cd FrogMPEG
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m frogmpeg init        # copies config.example.json to config.json
python -m frogmpeg validate
python -m frogmpeg --gui       # or: frogmpeg-gui.bat on Windows
```

## Configuration

1. Copy `config.example.json` to `config.json`
2. Set `renders_folder`, `output_folder`, `ffmpeg_path`, defaults, and presets
3. Git ignores `config.json`, so your secrets stay local

```jsonc
{
  "project_name": "COSMIC-HUMANITY",
  "renders_folder": "../_RENDERS",
  "output_folder": "../_RENDERS/_FrogOutputs",
  "ffmpeg_path": "C:/Tools/ffmpeg/bin/ffmpeg.exe",

  "defaults": {
    "resolution": "2048x2048",
    "bitrate": "100M",
    "file_extension": "jpeg",
    "fps": 60,
    "output_codec": "h264-nvenc-mp4"
  },

  "presets": [
    {
      "name": "fulldome-2k",
      "resolution": "2048x2048",
      "bitrate": "100M",
      "description": "Standard 2K fulldome",
      "fps": 60
    },
    {
      "name": "fulldome-prores",
      "resolution": "2048x2048",
      "bitrate": "100M",
      "description": "ProRes 422 for editing",
      "fps": 60,
      "output_codec": "prores-422-mov"
    }
  ]
}
```

## Commands

| Command                            | Description                           |
|------------------------------------|---------------------------------------|
| `python -m frogmpeg gui`           | Launch GUI with codec selection        |
| `python -m frogmpeg browse`        | Interactive browser with folder picker |
| `python -m frogmpeg convert FOLDER` | Convert with defaults                  |
| `python -m frogmpeg convert --browse` | Browse and convert in one command    |
| `python -m frogmpeg convert FOLDER --format prores-422-mov` | Convert to ProRes |
| `python -m frogmpeg list-formats`  | Show all available codecs              |
| `python -m frogmpeg list-presets`  | Show available presets                 |
| `python -m frogmpeg init`          | Create config.json from example        |
| `python -m frogmpeg validate`      | Validate config and environment        |

Batch launchers (`frogmpeg-gui.bat`, `frogmpeg.bat`) call the same commands after auto-activating the local venv.

### GUI Controls

- **B** - Browse for folder (opens native OS dialog)
- **Tab** - Move to next section
- **↑↓** - Navigate lists (folders, codecs)
- **←→** - Switch options (presets, extensions, containers)
- **S** - Start conversion
- **R** - Refresh folder list
- **Q** - Quit

### Format Selection Examples

```bash
# Interactive browse mode with dialogs
python -m frogmpeg browse

# Browse for folder, then convert
python -m frogmpeg convert --browse --format prores-422-mov
# ProRes 422 for editing
python -m frogmpeg convert my_folder --format prores-422-mov

# HEVC for smaller files
python -m frogmpeg convert my_folder --format hevc-nvenc-mp4

# ProRes 4444 with alpha
python -m frogmpeg convert vfx_renders --format prores-4444-mov

# Use MOV container with default codec
python -m frogmpeg convert my_folder --container mov
```

## Branding

Every run greets you with a frog:

```
     🐸 FrogMPEG 🐸
  Multi-Codec Video Converter
  with ProRes Support!
```

- Console colors: neon greens & cyan gradients
- Codec badges: 🟢 GPU / 🔵 CPU / 🟡 Alpha
- Messages like "Hopping through frames…" and "Ribbiting success!"

## Documentation

Detailed docs live in `docs/`:

- `INSTALLATION.md`
- `CONFIGURATION.md`
- `USAGE.md`

## License

MIT License. Ribbit responsibly. 🐸

