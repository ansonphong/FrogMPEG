# 🐸 FrogMPEG V2.0.0

FrogMPEG is a **dual-mode, frog-themed video converter** built for fulldome and advanced visualization pipelines. Convert image sequences to video OR extract frames from video — all with hardware-accelerated FFmpeg supporting **H.264, HEVC, and Apple ProRes** codecs.

## ✨ What's New in V2.0.0

- **🎬 Image to Video**: Convert image sequences (PNG, JPEG) to video (H.264, HEVC, ProRes)
- **🖼️ Video to Images**: Extract frames from video files to image sequences (PNG, JPEG, TIFF, EXR)
- **🚀 Launcher GUI**: Choose your mode from a beautiful main menu
- **🎨 Centralized Theme**: Consistent frog-themed colors across all GUIs
- **📦 Modular Architecture**: Separate pipelines with clean separation of concerns

## Features

### Image-to-Video Pipeline
- Multi-codec support: H.264, HEVC/H.265, ProRes (all variants)
- GPU-accelerated encoding (NVENC) with automatic CPU fallback
- Two-level hierarchical GUI for intuitive container and codec selection
- ProRes support: All variants including 4444 with alpha channel
- Advanced configuration via `config.json` with presets and encoder tuning

### Video-to-Image Pipeline (NEW!)
- Extract all frames or at specific frame rates (1fps, 5fps, 24fps, 30fps, etc.)
- Output formats: PNG, JPEG, TIFF, OpenEXR
- Video metadata display: codec, resolution, fps, frame count
- Size estimation before extraction
- Quality control for JPEG and PNG compression

### Unified Experience
- Consistent keyboard shortcuts across all GUIs
- Frog branding everywhere: ASCII art, emojis, and ribbiting logs
- Project-friendly layout – keep FrogMPEG versioned while local config stays private

## Supported Formats

### Video Output (Image-to-Video)

**MP4 Container**
- **H.264** (NVENC/CPU) - Universal playback
- **HEVC/H.265** (NVENC/CPU) - 50% smaller files, 4K optimized

**MOV Container**
- **ProRes Proxy** - Offline editing
- **ProRes LT** - Standard editing
- **ProRes 422** - Broadcast quality (10-bit)
- **ProRes 422 HQ** - High-end production (10-bit)
- **ProRes 4444** - VFX with alpha channel (10-bit)
- **ProRes 4444 XQ** - Maximum quality (10-bit)

### Image Output (Video-to-Image)
- **PNG** - Lossless, supports alpha, 16-bit support
- **JPEG** - Lossy compression, smallest files, quality control
- **TIFF** - Lossless, professional workflows, 16-bit support
- **OpenEXR** - HDR, VFX workflows, 16/32-bit float

## Quick Start

```bash
cd YOUR_PROJECT
git clone https://github.com/yourname/FrogMPEG.git
cd FrogMPEG
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m src init           # copies config.example.json to config.json
python -m src validate
python -m src gui            # or: frogmpeg-gui.bat on Windows
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
  
  "extraction": {
    "output_format": "png",
    "jpeg_quality": 95,
    "png_compression": 6,
    "name_pattern": "{video_name}_%05d"
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

### Main Commands

| Command | Description |
|---------|-------------|
| `python -m src gui` | Launch launcher - choose image→video or video→image |
| `python -m src img2video` | Launch image-to-video GUI directly |
| `python -m src video2img` | Launch video-to-image GUI directly |

### Image-to-Video Commands

| Command | Description |
|---------|-------------|
| `python -m src browse` | Interactive browser with folder picker |
| `python -m src convert FOLDER` | Convert with defaults |
| `python -m src convert --browse` | Browse and convert in one command |
| `python -m src convert FOLDER --format prores-422-mov` | Convert to ProRes |
| `python -m src list-formats` | Show all available video codecs |
| `python -m src list-presets` | Show available presets |

### Video-to-Image Commands (NEW!)

| Command | Description |
|---------|-------------|
| `python -m src extract VIDEO.mp4` | Extract all frames to PNG |
| `python -m src extract VIDEO.mp4 --fps 24` | Extract at 24fps |
| `python -m src extract VIDEO.mp4 --format jpeg --quality 95` | Extract as high-quality JPEG |
| `python -m src extract VIDEO.mp4 --start 10 --end 60` | Extract frames from 10s to 60s |
| `python -m src extract VIDEO.mp4 -o custom_folder` | Specify output folder |

### Configuration Commands

| Command | Description |
|---------|-------------|
| `python -m src init` | Create config.json from example |
| `python -m src validate` | Validate config and environment |

Batch launchers (`frogmpeg-gui.bat`, `frogmpeg.bat`) call the same commands after auto-activating the local venv.

### GUI Controls (All GUIs)

Universal shortcuts across launcher, image-to-video, and video-to-image GUIs:

- **[S]** - Start conversion/extraction
- **[B]** - Browse for folder/file
- **[L]** - Return to launcher (from sub-GUIs)
- **[R]** - Refresh folder/video list
- **[Q]** - Quit application
- **[Tab]** / **[Enter]** - Move to next section
- **[Shift+Tab]** - Move to previous section
- **[↑↓]** - Navigate lists (folders, videos, codecs)
- **[←→]** - Switch options (presets, formats, modes)

### Format Selection Examples

**Image to Video:**
```bash
# Interactive browse mode with dialogs
python -m src browse

# Browse for folder, then convert
python -m src convert --browse --format prores-422-mov

# ProRes 422 for editing
python -m src convert my_folder --format prores-422-mov

# HEVC for smaller files
python -m src convert my_folder --format hevc-nvenc-mp4

# ProRes 4444 with alpha
python -m src convert vfx_renders --format prores-4444-mov

# Use MOV container with default codec
python -m src convert my_folder --container mov
```

**Video to Images:**
```bash
# Extract all frames as PNG
python -m src extract my_video.mp4

# Extract at 24fps as JPEG
python -m src extract my_video.mp4 --fps 24 --format jpeg

# Extract time range (10s to 60s)
python -m src extract my_video.mp4 --start 10 --end 60

# High-quality JPEG extraction
python -m src extract my_video.mp4 --format jpeg --quality 98

# Extract to specific folder
python -m src extract my_video.mp4 --output ./my_frames
```

## Branding

The launcher greets you with ASCII art:

```
  ______                __  ___ ____  ________ 
 / ____/________  ____ /  |/  // __ \/ ____/ / 
/ /_  / ___/ __ \/ __ `/ /|_/ // /_/ / __/ / /  
/ __/ / /  / /_/ / /_/ / /  / // ____/ /___/ /___
/_/   /_/   \____/\__, /_/  /_//_/   /_____/_____/
                /____/                            

        Multi-Format Video Converter
```

**Frog Theme Colors:**
- Primary: Bright greens, emeralds, and spring greens
- Secondary: Yellows, golds, and ambers
- Selection: Active sections = WHITE, Inactive = GREEN
- Badges: [GPU] lime green, [CPU] muted, [Alpha] amber

Messages like "🐸 Converting..." and "Ribbiting success!"

## Documentation

Detailed docs live in `docs/`:

- `INSTALLATION.md`
- `CONFIGURATION.md`
- `USAGE.md`

## License

MIT License. Ribbit responsibly. 🐸

