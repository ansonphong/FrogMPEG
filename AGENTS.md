# FrogMPEG

Frog-themed FFmpeg wrapper for fulldome / visualization pipelines. Dual-mode: **image sequence → video** and **video → image sequence**. Terminal GUIs (Rich) plus a Typer CLI. Encoding is always FFmpeg; this repo only builds commands, probes metadata, and presents a TUI.

Runtime version: `src/__version__.py` (`2.1.0`). Keep the same number in `pyproject.toml`. `python -m src --version` reads `__version__.py`.

This file is agent context. The headless runbook and full capability guide live in `README.md` (section **Headless operation**). Do not copy that guide here. `docs/USAGE.md` still shows `python -m frogmpeg --gui`, which is not a command — ignore it.

## Headless (required unless the user asked for the TUI)

Run from the repo root. Do not launch a GUI, a folder picker, or any command that prompts.

Never run these in an agent session. They block on a keyboard, a Rich screen, or a tkinter dialog:

- `python -m src gui`
- `python -m src img2video`
- `python -m src video2img`
- `python -m src browse`
- `python -m src convert --browse`
- `python -m src convert` with no folder argument (same picker)
- `frogmpeg-gui.bat`

Headless sequence:

```bash
python -m src validate
python -m src list-presets
python -m src list-formats
python -m src convert FOLDER_NAME --preset PRESET --extension jpeg --format CODEC_KEY
python -m src extract /path/to/video.mp4 --format png -o /path/to/out
```

`FOLDER_NAME` is a child of `renders_folder`, not a filesystem path. `convert` has no `--output`; the file is written to `output_folder`. Codec keys come from `list-formats`. Details, output names, and flag tables are in `README.md`.

## Commands

Prefer `python -m src`. After `pip install -e .`, `frogmpeg` and `python -m frogmpeg` also work.

| Command | What it does |
|---|---|
| `python -m src validate` | Check ffmpeg path, folders, config |
| `python -m src list-presets` | Presets from `config.json` |
| `python -m src list-formats` | Codec registry dump |
| `python -m src list-containers` | `mp4` and `mov` |
| `python -m src list-codecs --container mp4` | Codecs for one container |
| `python -m src convert FOLDER --preset NAME --format KEY --extension EXT` | Headless image sequence → video |
| `python -m src extract VIDEO --format FMT -o DIR` | Headless video → frames |
| `python -m src init` | Copy `config.example.json` → `config.json` (`--force` overwrites) |
| `python -m src gui` | Launcher TUI. Not headless. `gui FOLDER` scopes the chosen mode to that folder |
| `python -m src img2video` | Image-sequence GUI. Not headless. `img2video FOLDER` lists that folder |
| `python -m src video2img` | Frame-extract GUI. Not headless. `video2img FILE_OR_FOLDER` lists that path |
| `python -m src browse` | Picker plus prompts. Not headless |
| `frogmpeg.bat` | Windows: create venv if missing, then `python -m src` plus args |
| `frogmpeg-gui.bat` | Windows GUI launcher. Not headless |

No test suite, no linter config. Do not invent `pytest` / `ruff` commands.

Windows venv: `venv\Scripts\python.exe`. POSIX: `venv/bin/python`.

## Architecture

```
FrogMPEG/
  src/                    # Python package (also importable as `frogmpeg` via package-dir)
    __main__.py           # python -m src → cli.run()
    cli.py                # Typer app: all commands
    config.py             # config.json → dataclasses
    formats.py            # Codec + image-format registry (single source of truth)
    theme.py              # Shared TUI colors, shortcuts, console helpers
    dialogs.py            # tkinter native folder/file pickers
    launcher/gui.py       # Mode picker
    img2video/            # Sequence → video (converter + GUI)
    video2img/            # Video → frames (converter + GUI)
  config.example.json     # Checked in
  config.json             # Local only (gitignored)
  docs/                   # INSTALLATION, CONFIGURATION, USAGE
  frogmpeg.bat            # CLI wrapper
  frogmpeg-gui.bat        # GUI wrapper
```

V1 had `src/converter.py` and `src/gui.py`. Those are gone. Do not resurrect them. `__pycache__` may still contain the old names.

### Data flow

```
config.json ──► load_config() ──► Config
                                      │
launcher ──► img2video GUI ──► ConversionRequest ──► convert_folder()
         └──► video2img GUI ──► ExtractionRequest ──► extract_frames()
cli convert / extract ──────────┘                          │
                                                           ▼
                                              FFmpeg / FFprobe subprocess
```

- **img2video:** glob `*.{ext}` in a folder, numeric-sort filenames, write an FFmpeg concat list, `-vf scale=WxH`, encode.
- **video2img:** `ffprobe` JSON for metadata, then `ffmpeg` to image sequence (`name_%05d.ext`).
- GPU codecs (`*_nvenc`): if FFmpeg fails, retry the same job with the CPU encoder. ProRes is CPU-only (`prores_ks`).

## Key files

| File | Role |
|---|---|
| `src/cli.py` | Command surface. Wire new commands here. |
| `src/config.py` | Required keys, path resolution (relative paths are vs repo root), presets, encoding, extraction defaults. |
| `src/formats.py` | `CodecProfile` list, `CODECS_BY_CONTAINER`, `IMAGE_OUTPUT_FORMATS`. Add formats here first. |
| `src/img2video/converter.py` | `build_*_command`, concat list, GPU fallback, output naming. |
| `src/video2img/converter.py` | `probe_video`, extract command, size/frame estimates. |
| `src/theme.py` | `COLORS`, `SHORTCUTS_*`, panel helpers. All GUIs import this. |
| `src/dialogs.py` | `browse_for_sequence_folder`, `browse_for_video_file`. |

## Conventions

**New video codec**

1. Add a `CodecProfile` in `src/formats.py` and register it in `ALL_CODECS` + `CODECS_BY_CONTAINER` (+ family/default maps if needed).
2. Add or extend a `build_*_command` in `src/img2video/converter.py` and branch in `build_codec_command`.
3. GUI/CLI pickers read the registry — do not hardcode codec lists in the GUI.

**New image output format**

1. Add `ImageOutputFormat` to `IMAGE_OUTPUT_FORMATS`.
2. Handle quality/flags in `build_extraction_command` and extension maps.

**GUI**

- Three screens: `launcher` → `img2video` | `video2img`. Sub-GUIs return `"quit"` or `"launcher"`.
- Colors and footer shortcuts come from `theme.py`. Do not invent a second palette.
- Universal keys: `[S]` start, `[B]` browse, `[R]` refresh, `[L]` launcher, `[Q]` quit, Tab / Shift+Tab cycle sections.
- Arrow keys on Windows `msvcrt` decode as `H` up, `P` down, `K` left, `M` right. Keep those codes if you touch `handle_key`.
- Active section = white reverse; inactive selection = green reverse (`theme.style_selected`).
- Keep frog branding (ASCII header, greens/golds, “Ribbiting success!”). It is intentional.

**Style**

- Python 3.10+, `from __future__ import annotations`.
- Dataclasses for requests/config; `RuntimeError` subclasses for domain errors (`ConversionError`, `ExtractionError`, `ConfigError`).
- Relative imports inside the package (`from ..theme import ...`).
- Match surrounding code. Do not add type-checking tooling or reformat the whole tree.

## Config and paths

`config.json` is per-machine and gitignored. Schema lives in `config.example.json` and `src/config.py`.

Typical layout: FrogMPEG is cloned next to a `_RENDERS` folder.

| Key | Meaning |
|---|---|
| `renders_folder` | Default image-sequence parent. GUI scans immediate subfolders that contain jpeg/jpg/png. |
| `output_folder` | CLI default destination; also where video2img GUI scans for “recent” videos. |
| `ffmpeg_path` | Full path to `ffmpeg` (`ffmpeg.exe` on Windows). FFprobe is assumed to sit next to it (`ffprobe` / `ffprobe.exe`). |
| `defaults` | Resolution, bitrate, fps, input extension, optional `preset_name` / `output_codec`. |
| `presets[]` | Named resolution/fps/bitrate (+ optional `output_codec` key). |
| `encoding` | NVENC vs x264/x265 knobs (`use_gpu`, presets, GOP, AQ). |
| `extraction` | video2img defaults (format, jpeg quality, png compression, name pattern). GUI currently uses its own defaults more than this block. |

Relative paths in config resolve against the FrogMPEG repo root, not the cwd.

**Output location (easy to get wrong)**

- GUI img2video: video written to **parent of the source image folder**.
- GUI video2img: frames written to **`{video_parent}/{stem}_frames/`**.
- CLI `convert`: `config.output_folder` unless `ConversionRequest.output_folder` is set.
- CLI `extract`: `config.output_folder / "{stem}_frames"` unless `-o` is passed.

CLI `convert --browse` stores only `folder_name`, not `source_folder`. Folders outside `renders_folder` can fail even though the picker accepted them. GUI sets `source_folder` explicitly.

## Gotchas

- **Windows-first TUI.** Arrow keys and Shift+Tab need `msvcrt`. POSIX fallbacks (`sys.stdin.read(1)` / `input()`) do not handle arrows. Do not claim Linux TUI parity unless you add a real input layer.
- **Invoke as `src`, not only `frogmpeg`.** `pyproject.toml` maps package name `frogmpeg` → `src/`, but batch files and day-to-day use are `python -m src`. Docs still mix `python -m frogmpeg` and even `python -m frogmpeg --gui` (wrong; the command is `gui`).
- **Always scales** to the preset resolution, even when frames already match.
- **Concat + `-r` on input** is the img2video pattern. Do not switch to glob input without a reason.
- **EXR extract** has no extra FFmpeg codec flags yet.
- **`pyyaml` is in `requirements.txt` and unused.** Do not build YAML config on that leftover.
- **No tests.** If you add some, put them in a new `tests/` and keep them off the FFmpeg binary unless a fixture exists.
- **Do not commit `config.json`, `venv/`, or rendered `.mp4`.** `.gitignore` already covers these. `FrogMPEG.lnk` is a local shortcut — leave it untracked.
- **Mixed line endings** (CRLF on several `src/` files). Do not mass-convert the tree in an unrelated PR; the current uncommitted diffs are mostly CRLF noise.
- **tkinter** must be available for browse dialogs. Headless environments will fail those paths.
- img2video GUI **exits with `"quit"`** if `renders_folder` has no image-sequence subfolders (browse never gets a chance).
- Codec keys look like `h264-nvenc-mp4`, `prores-422-mov`. Validate with `get_codec()`; do not parse the string.

## Do not

- Put conversion logic in GUI modules. GUIs build a `*Request` and call the converter.
- Hardcode codec/format lists in CLI or GUI when the registry already has them.
- Change FFmpeg invocation to shell strings (`shell=True`). Keep argv lists.
- “Clean up” frog theming, emoji logs, or ASCII art unless asked.
- Expand into a web UI, job queue, or extra media libraries without an explicit request. This is an FFmpeg command builder with a TUI.
