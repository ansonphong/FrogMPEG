# Configuration

Configuration lives in `config.json` (gitignored). Copy from `config.example.json` and customize.

Key sections:

- `project_name` – label used in UI/logs
- `renders_folder` – relative/absolute path to the folder containing sequence folders
- `output_folder` – where MP4 files are written
- `ffmpeg_path` – absolute path to ffmpeg executable
- `defaults` – fallback resolution/bitrate/fps/extension
- `presets` – array of objects:
  ```json
  {
    "name": "fulldome-4k",
    "description": "High quality",
    "resolution": "4096x4096",
    "bitrate": "200M",
    "fps": 60
  }
  ```
- `encoding` – NVENC/libx264 tuning values
- `ui` – GUI preferences (theme, auto-select latest folder)

You can create multiple preset objects, each with its own fps.

