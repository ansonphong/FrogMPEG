# 🐸 FrogMPEG

FrogMPEG is a **drop-in, frog-themed image sequence converter** built for fulldome and advanced visualization pipelines. Clone it into any project, configure once, and convert thousands of renders with hardware-accelerated FFmpeg — all while keeping your project repo clean.

## Features

- **GPU-accelerated** H.264 (NVENC) with automatic CPU fallback
- **btop-inspired CLI GUI** for folder selection and preset switching
- **Advanced configuration** via `config.json` with presets, encoder tuning, themes
- **Project-friendly layout** – keep FrogMPEG versioned while local config stays private
- **Frog branding** everywhere: ASCII art, emojis, and ribbiting logs

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
    "fps": 60
  },

  "presets": {
    "fulldome-2k": {
      "resolution": "2048x2048",
      "bitrate": "100M",
      "description": "Standard 2K fulldome"
    },
    "fulldome-4k": {
      "resolution": "4096x4096",
      "bitrate": "200M",
      "description": "High quality 4K fulldome"
    }
  }
}
```

## Commands

| Command                            | Description                           |
|------------------------------------|---------------------------------------|
| `python -m frogmpeg --gui`         | Launch GUI                             |
| `python -m frogmpeg convert`       | Convert with defaults                  |
| `python -m frogmpeg convert --folder FOLDER --preset fulldome-4k` | Targeted conversion |
| `python -m frogmpeg list-presets`  | Show available presets                 |
| `python -m frogmpeg init`          | Create config.json from example        |
| `python -m frogmpeg validate`      | Validate config and environment        |

Batch launchers (`frogmpeg-gui.bat`, `frogmpeg.bat`) call the same commands after auto-activating the local venv.

## Branding

Every run greets you with a frog:

```
     🐸 FrogMPEG 🐸
  The Ribbiting Way to
  Convert Image Sequences
```

- Console colors: neon greens & cyan gradients
- Messages like “Hopping through frames…” and “Ribbiting success!”

## Documentation

Detailed docs live in `docs/`:

- `INSTALLATION.md`
- `CONFIGURATION.md`
- `USAGE.md`

## License

MIT License. Ribbit responsibly. 🐸

