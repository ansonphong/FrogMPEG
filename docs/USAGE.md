# Usage Guide

FrogMPEG now supports multiple output codecs including H.264, HEVC, and Apple ProRes in both MP4 and MOV containers.

## GUI Mode

Launch the interactive GUI:

```bash
frogmpeg-gui.bat
# or
python -m frogmpeg --gui
```

### Navigation

The GUI features a **5-step hierarchical workflow**:

1. **[1] Folders** - Select your image sequence folder (↑↓ arrows)
2. **[2] Preset** - Choose resolution/fps/bitrate preset (←→ arrows)
3. **[3] Extension** - Select input file type: jpeg/jpg/png (←→ arrows)
4. **[4] Container** - Choose output container: MP4 or MOV (←→ arrows)
5. **[5] Codec** - Select codec for the container (↑↓ arrows)

### GUI Controls

- **↑↓** - Navigate lists (folders, codecs)
- **←→** - Switch options (presets, extensions, containers)
- **Tab** - Move to next section
- **B** - **Browse** for folder (opens native OS file picker)
- **S** - Start conversion with current settings
- **R** - Refresh folder list
- **Q** - Quit

### Codec Badges

The GUI displays codec indicators:
- 🟢 **GPU** - Hardware accelerated (NVENC)
- 🔵 **CPU** - Software encoding
- 🟡 **Alpha** - Supports transparency (ProRes 4444 only)

## CLI Mode

### Basic Conversion

Convert with defaults:

```bash
python -m frogmpeg convert FOLDER_NAME
```

### Browse Mode (NEW!)

Open native OS folder picker and convert interactively:

```bash
# Full interactive mode with dialogs
python -m frogmpeg browse

# Browse for folder, use specific format
python -m frogmpeg convert --browse --format prores-422-mov

# Browse for folder, use preset
python -m frogmpeg convert --browse --preset fulldome-4k
```

The browse mode:
- Opens native Windows/Mac folder picker
- Works from anywhere (not limited to renders_folder)
- Interactively selects preset and format
- Perfect for one-off conversions

### With Preset

```bash
python -m frogmpeg convert FOLDER_NAME --preset fulldome-4k
```

### Output Codec Selection

#### Method 1: Specify Codec Key

Use a specific codec directly:

```bash
# ProRes 422
python -m frogmpeg convert FOLDER_NAME --format prores-422-mov

# HEVC with GPU
python -m frogmpeg convert FOLDER_NAME --format hevc-nvenc-mp4

# ProRes 4444 (with alpha)
python -m frogmpeg convert FOLDER_NAME --format prores-4444-mov
```

#### Method 2: Specify Container

Let FrogMPEG choose the default codec for a container:

```bash
# Use default MP4 codec (H.264 NVENC)
python -m frogmpeg convert FOLDER_NAME --container mp4

# Use default MOV codec (ProRes 422)
python -m frogmpeg convert FOLDER_NAME --container mov
```

### List Available Formats

See all supported codecs:

```bash
python -m frogmpeg list-formats
```

Output example:
```
🐸 Available Output Formats:

📦 MP4 Container:
  • h264-nvenc-mp4
    H.264 (GPU - NVENC) 🟢 GPU
    Hardware-accelerated H.264 encoding using NVIDIA GPU
    Use case: Fast encoding, universal playback

  • hevc-nvenc-mp4
    HEVC/H.265 (GPU - NVENC) 🟢 GPU
    Hardware-accelerated HEVC encoding, 50% smaller files
    Use case: 4K video, efficient storage, modern devices

📦 MOV Container:
  • prores-422-mov
    ProRes 422 🟣
    Standard ProRes for professional editing (10-bit)
    Use case: Broadcast, professional workflows

  • prores-4444-mov
    ProRes 4444 🟡 Alpha
    ProRes with alpha channel support for VFX (10-bit)
    Use case: VFX, compositing, transparency
```

### Other Commands

```bash
# List containers
python -m frogmpeg list-containers

# List codecs for a specific container
python -m frogmpeg list-codecs --container mov

# List presets
python -m frogmpeg list-presets

# Validate configuration
python -m frogmpeg validate
```

## Codec Reference

### MP4 Container

| Codec | Key | GPU | Use Case |
|-------|-----|-----|----------|
| H.264 (NVENC) | `h264-nvenc-mp4` | ✅ | Universal playback, fast |
| H.264 (CPU) | `h264-cpu-mp4` | ❌ | No GPU required |
| HEVC (NVENC) | `hevc-nvenc-mp4` | ✅ | 4K, 50% smaller files |
| HEVC (CPU) | `hevc-cpu-mp4` | ❌ | Best compression |

### MOV Container

| Codec | Key | Alpha | Use Case |
|-------|-----|-------|----------|
| H.264 | `h264-cpu-mov` | ❌ | MOV compatibility |
| ProRes Proxy | `prores-proxy-mov` | ❌ | Offline editing |
| ProRes LT | `prores-lt-mov` | ❌ | Standard editing |
| ProRes 422 | `prores-422-mov` | ❌ | Broadcast quality |
| ProRes 422 HQ | `prores-422-hq-mov` | ❌ | High-end production |
| ProRes 4444 | `prores-4444-mov` | ✅ | VFX with alpha |
| ProRes 4444 XQ | `prores-4444-xq-mov` | ✅ | Maximum quality |

## Usage Examples

### Standard Workflow

```bash
# H.264 MP4 (default)
python -m frogmpeg convert my_render --preset fulldome-4k

# ProRes for editing
python -m frogmpeg convert my_render --preset fulldome-4k --format prores-422-mov

# HEVC for smaller file size
python -m frogmpeg convert my_render --preset fulldome-4k --format hevc-nvenc-mp4
```

### Professional Workflows

```bash
# ProRes 422 HQ for mastering
python -m frogmpeg convert master_sequence --format prores-422-hq-mov

# ProRes 4444 with alpha for VFX
python -m frogmpeg convert vfx_plates --format prores-4444-mov

# HEVC for 4K archival
python -m frogmpeg convert 4k_sequence --format hevc-nvenc-mp4 --preset fulldome-4k
```

### Override File Extension

```bash
# Use PNG sequences instead of JPEG
python -m frogmpeg convert my_folder --extension png --format prores-422-mov
```

## Configuration

### Preset-Based Codec Selection

Define output codecs in your presets (`config.json`):

```json
{
  "presets": [
    {
      "name": "fulldome-prores",
      "description": "ProRes 422 for editing",
      "resolution": "2048x2048",
      "bitrate": "100M",
      "fps": 60,
      "output_codec": "prores-422-mov"
    },
    {
      "name": "fulldome-hevc",
      "description": "HEVC for smaller files",
      "resolution": "4096x4096",
      "bitrate": "150M",
      "fps": 60,
      "output_codec": "hevc-nvenc-mp4"
    }
  ]
}
```

### Default Output Codec

Set a default codec in your config:

```json
{
  "defaults": {
    "resolution": "2048x2048",
    "bitrate": "100M",
    "file_extension": "jpeg",
    "fps": 60,
    "output_codec": "h264-nvenc-mp4"
  }
}
```

## File Size Estimates

Relative to H.264 at the same bitrate:

- **H.264 / HEVC**: 1x (baseline)
- **ProRes Proxy**: ~2x
- **ProRes LT**: ~4x
- **ProRes 422**: ~8x
- **ProRes 422 HQ**: ~12x
- **ProRes 4444**: ~15x
- **ProRes 4444 XQ**: ~20x

**Note**: ProRes uses quality-based encoding, not bitrate. The multipliers are approximations.

## Important Notes

### GPU Acceleration

- **Available for**: H.264, HEVC (with NVIDIA GPU)
- **Not available for**: ProRes (CPU-only)
- FrogMPEG automatically falls back to CPU if GPU encoding fails

### ProRes Specifics

- ProRes encoding is **CPU-only** (no NVENC support)
- File sizes are significantly larger than H.264
- ProRes 4444 and 4444 XQ support **alpha channels**
- Best for **editing workflows**, not final delivery

### HEVC/H.265

- Better compression than H.264 (~50% smaller)
- Requires modern playback devices
- Slightly slower encoding than H.264

## Batch Launchers

Use the included batch files on Windows:

```bash
# GUI
frogmpeg-gui.bat

# CLI (forwards all arguments)
frogmpeg.bat convert my_folder --format prores-422-mov
```
