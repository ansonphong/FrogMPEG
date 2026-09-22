# FrogMPEG 2.2.0

FrogMPEG builds FFmpeg commands for fulldome and visualization work. It converts a folder of stills into a video, or a video back into a frame sequence. Encoding is always FFmpeg. This repo does not decode or encode pixels itself.

Version `2.2.0` is in `src/__version__.py` and `pyproject.toml`. `python -m src --version` prints it.

It is aimed at square dome masters: presets are 1:1, the default rate is 60 fps, and the encoder tune is `animation`. Output is always scaled to the preset size.

## Headless operation

Use this section to run FrogMPEG without a person at the keyboard. The terminal GUIs, the browse command, and the folder picker all wait for input and will hang an agent.

Run every command from the repository root:

```bash
python -m src <command>
```

After `pip install -e .`, `frogmpeg <command>` is the same app. Do not pass `--gui`. That flag does not exist. The GUI command is `gui`, and agents should not run it.

### Do not run

| Command | Why it is not headless |
|---|---|
| `python -m src gui` | Full-screen launcher. Waits for a key. |
| `python -m src img2video` | Image-to-video TUI. `img2video FOLDER` still opens the TUI, scoped to that folder. |
| `python -m src video2img` | Video-to-frames TUI. `video2img PATH` still opens the TUI. |
| `python -m src browse` | Folder picker, then numbered prompts. |
| `python -m src convert --browse` | Opens a native folder dialog. |
| `python -m src convert` | No folder argument also opens that dialog. |
| `frogmpeg-gui.bat` | Starts the launcher TUI. |

Arrow keys in those TUIs only work on Windows (`msvcrt`). That is another reason to stay on the commands below.

### Check the machine first

```bash
python -m src validate
python -m src list-presets
python -m src list-formats
python -m src list-containers
python -m src list-codecs --container mov
```

`validate` checks that `ffmpeg_path` exists and that `renders_folder` and `output_folder` exist. It exits `0` on success and `1` on failure. `list-formats` reads the codec registry and does not need a valid FFmpeg path. `list-presets` reads `config.json`.

`ffmpeg_path` must be a binary this process can execute. FFprobe is expected beside it (`ffprobe` or `ffprobe.exe`). A Windows path in `config.json` will not run under a Linux Python.

If `config.json` is missing, the first command that loads config copies `config.example.json`. `python -m src init` does that copy on purpose. `init --force` overwrites an existing file.

### Image sequence to video

The folder argument is the **name of a child of `renders_folder`**, not a full path. `MyShot` is correct when the files live in `<renders_folder>/MyShot/`. A path outside that parent is not accepted by `convert`.

```bash
python -m src convert MyShot --preset fulldome-2k --extension jpeg --format h264-nvenc-mp4
```

| Flag | Meaning |
|---|---|
| `FOLDER` | Required. Child folder name under `renders_folder`. |
| `--preset`, `-p` | Preset name from `config.json`. Omit to use `defaults.preset_name`, or a preset built from `defaults`. |
| `--extension`, `-e` | `jpeg`, `jpg`, or `png`. Omit to use `defaults.file_extension`. |
| `--format`, `-f` | Codec key from `list-formats`, such as `prores-422-mov`. |
| `--container`, `-c` | `mp4` or `mov`. Uses the first codec registered for that container (`h264-nvenc-mp4` or `h264-cpu-mov`). Prefer `--format`. |
| `--rotate`, `-r` | Clockwise degrees applied to every frame before scaling. `0` (default), `90`, `-90`, `180`, or `270`. |

There is no `--output` on `convert`. The file is written to `output_folder` in `config.json`. To change the destination, edit that key. Relative paths in config resolve against the FrogMPEG repo root, not the shell's current directory.

Codec choice, in order:

1. `--format` or `--container` on the command
2. `output_codec` on the selected preset
3. `defaults.output_codec`
4. `h264-nvenc-mp4`

Only one extension is read. `*.jpeg` does not include `*.jpg`. Files are sorted by the integers in the filename, then by name. They are passed to FFmpeg as a concat list with `-r` set to the preset fps, then scaled to the preset resolution. `fit` controls that scale: `stretch` (the default, used by dome presets), `pad` (whole frame, black bars), or `crop` (fill the frame and cut the overflow).

`convert` has no start time, end time, or duration. Every still in the folder becomes one frame. Length is frame count divided by the preset fps. A 60 fps preset plays each frame for 1/60 of a second: 300 frames become 5 seconds, 1800 frames become 30 seconds. Choosing 30 fps plays those same frames for twice as long. It does not drop frames, and it does not trim the sequence to 30 or 60 seconds. A shorter reel means a folder that contains only the frames you want.

#### Rotate

`--rotate` turns every frame clockwise before the preset scale. The preset resolution is the size of the finished file. `extract` and the GUIs do not rotate.

| Value | Direction | FFmpeg filter |
|---|---|---|
| `0` | none | no rotate filter |
| `90` | clockwise | `transpose=1` |
| `-90` or `270` | counter-clockwise | `transpose=2` |
| `180` | half turn | `hflip,vflip` |

Other numbers fail. `360` and `-180` are accepted and normalized (`-180` is the same turn as `180`).

```bash
python -m src convert MyShot --preset social-reel --rotate 90
python -m src convert MyShot --preset social-reel --rotate -90
python -m src convert MyShot --preset fulldome-2k --rotate 180
```

A square frame stays square after a quarter turn, then `pad` or `crop` fits that turned picture into the preset. A 90 degree turn of a 1080×1920 picture swaps it to 1920×1080 before scaling.

#### Speed

`--speed` changes how fast the frames play. It is passed through to FFmpeg as `setpts`. Every still stays in the file. `extract` and the GUIs do not change speed.

| `--speed` | Result | Filter |
|---|---|---|
| `1` | preset timing | no `setpts` |
| `2` | half as long, twice as fast | `setpts=PTS/2` |
| `0.5` | twice as long, half speed | `setpts=PTS/0.5` |

`0` and negative values fail. There is no audio track to speed up with them.

A 60 fps folder that runs 2 minutes is 7,200 frames. `--speed 2` keeps all 7,200 frames and finishes in 1 minute, so the file is about 120 fps. The preset fps is the rate before speeding up. Instagram accepts up to 60 fps, so a sped-up 60 fps reel can come out above that limit.

```bash
python -m src convert MyShot --preset social-reel --speed 2
python -m src convert MyShot --preset fulldome-2k --speed 0.5
```

Output name:

```text
{folder}_{YYYY-MM-DD_HH-MM-SS}_{width}x{height}_{fps}fps_{codec-key}.{mp4|mov}
```

If that file already exists, `_1`, `_2`, … is appended. The command prints the frame count, preset, codec, and finishes when FFmpeg exits. Failure exits `1`.

GPU codecs (`h264_nvenc`, `hevc_nvenc`) retry the same job with `libx264` or `libx265` if the GPU encode fails. ProRes stays on `prores_ks`. Set `encoding.use_gpu` to `false` to skip the GPU attempt.

### Video to frames

`extract` takes a real video path. It does not look inside `renders_folder`.

```bash
python -m src extract /path/to/show.mp4 --format png -o /path/to/show_frames
python -m src extract /path/to/show.mp4 --fps 24 --format jpeg --quality 95
python -m src extract /path/to/show.mp4 --start 10 --end 60 --format tiff
```

| Flag | Meaning |
|---|---|
| `VIDEO` | Required path to the file. |
| `--output`, `-o` | Output directory. Default: `{output_folder}/{stem}_frames`. |
| `--format`, `-f` | `png` (default), `jpeg`, `tiff`, or `exr`. |
| `--fps` | Sample at this frame rate. Omit to keep every frame. |
| `--start`, `-s` | Start on the source clock, in seconds. |
| `--end`, `-e` | End on the source clock, in seconds. This is a timestamp, so `--end 25` means "stop at 25s," which is a length only when you also start at 0. |
| `--quality`, `-q` | JPEG quality, 1–100. Default 95. Ignored for other formats. |

`--start` and `--end` apply only to `extract`. `convert` ignores time and encodes the whole image folder.

```bash
python -m src extract show.mp4 --start 10 --end 25   # from 10s to 25s, so 15 seconds of frames
python -m src extract show.mp4 --start 10            # from 10s through the end of the file
python -m src extract show.mp4 --end 25              # the first 25 seconds
```

There is no flag for "start here and take N seconds." To keep 15 seconds starting at 10s, pass `--end 25` (10 + 15). The video-to-frames GUI cannot set either time. Use `extract`.

Frames are named `{stem}_%05d.{ext}` (`show_00001.png`). JPEG is written as `.jpg`. PNG uses compression level 6. TIFF uses LZW. EXR is passed through with no extra codec flags, so bit depth is whatever FFmpeg's default EXR encoder writes. The `extraction` block in `config.json` is not read by this command.

The CLI does not probe-and-print metadata before extracting. Metadata (codec, resolution, fps, frame count, duration, size) is shown in the video-to-image GUI.

### Presets an agent can pass to `--preset`

Shipped in `config.example.json`. A local `config.json` may differ. Trust `python -m src list-presets`.

| Name | Resolution | FPS | Bitrate | `output_codec` if set |
|---|---|---|---|---|
| `fulldome-2k` | 2048×2048 | 60 | 100M | none (falls through to the default) |
| `fulldome-4k` | 4096×4096 | 60 | 200M | none |
| `fulldome-4k-hevc` | 4096×4096 | 60 | 150M | `hevc-nvenc-mp4` |
| `fulldome-prores` | 2048×2048 | 60 | 100M | `prores-422-mov` |
| `fulldome-prores-hq` | 4096×4096 | 60 | 200M | `prores-422-hq-mov` |
| `vfx-prores-4444` | 4096×4096 | 60 | 200M | `prores-4444-mov` |
| `preview` | 1024×1024 | 30 | 25M | none |
| `social-reel` | 1080×1920 | 60 | 24M | `h264-nvenc-mp4`, `fit: pad`, faststart |
| `social-reel-30` | 1080×1920 | 30 | 24M | `h264-nvenc-mp4`, `fit: pad`, faststart |
| `social-reel-fill` | 1080×1920 | 60 | 24M | `h264-nvenc-mp4`, `fit: crop`, faststart |
| `social-feed` | 1080×1350 | 60 | 24M | `h264-nvenc-mp4`, `fit: pad`, faststart |
| `social-square` | 1080×1080 | 60 | 24M | `h264-nvenc-mp4`, faststart |

`social-reel` is the file for Instagram Reels, Stories, TikTok, and YouTube Shorts: 9:16 H.264, `yuv420p`. Every social preset targets **24 Mbps**, and the encoder also caps the peak at that rate. That is the room fine particle detail needs while staying under the 25 Mbps ceiling those apps publish. A lower rate bakes blur into sparks and grit before the platform re-encodes the upload. About 100 seconds at 24 Mbps is 300 MB, which is the usual upload-size limit, so keep a particle reel shorter than that if the app rejects the file. `pad` keeps a square dome master round and centered. `social-reel-fill` crops the sides so the phone frame is full. `social-feed` is the 4:5 feed portrait. `social-square` is an even scale of a square master. Social presets set `-movflags +faststart`. Dome presets do not, and their bitrates stay at 100M–200M.

A preset is resolution, fps, bitrate, and optional `output_codec`, `fit`, and `faststart`. Add one by appending an object to `presets` in `config.json`. `output_codec` must be a key from `list-formats`. `fit` is `stretch`, `pad`, or `crop`. Bitrate is ignored for ProRes, which uses a fixed quality scale.

Default when no `--preset` is passed: `defaults.preset_name` (`fulldome-2k` in the example).

## What the two pipelines do

### Image sequence → video

- Input extensions: `jpeg`, `jpg`, `png`. One extension per job.
- Containers: MP4 and MOV.
- Codecs: H.264, HEVC, and ProRes Proxy through 4444 XQ.
- The GUI writes the video in the **parent of the image folder**. The CLI writes to `output_folder`.
- The GUI can browse to a folder anywhere and set that folder as the source. The CLI cannot. Headless jobs stay under `renders_folder`.

### Video → image sequence

- Reads any file FFprobe can open.
- Writes PNG, JPEG, TIFF, or OpenEXR.
- Can keep every frame, or sample with `--fps`.
- Can cut a source time range with `extract --start` and `--end`. `--end` is a clock time. There is no duration flag. See [Video to frames](#video-to-frames).
- The GUI writes `{video_parent}/{stem}_frames/`. The CLI writes `{output_folder}/{stem}_frames/` unless `-o` is set.
- The GUI lists the ten newest `mp4`, `mov`, `mkv`, `avi`, and `webm` files in `output_folder`.

## Codec registry

Keys are exact. Do not invent names like `h264` or `prores`. Confirm with `python -m src list-formats`.

### MP4

| Key | Encoder | Notes |
|---|---|---|
| `h264-nvenc-mp4` | `h264_nvenc` | Default. GPU, `yuv420p`, bitrate. |
| `h264-cpu-mp4` | `libx264` | CPU. Also the fallback if NVENC fails. |
| `hevc-nvenc-mp4` | `hevc_nvenc` | GPU. Better compression than H.264 at the same bitrate setting. |
| `hevc-cpu-mp4` | `libx265` | CPU. Fallback if HEVC NVENC fails. |

### MOV

| Key | Encoder | Alpha | Notes |
|---|---|---|---|
| `h264-cpu-mov` | `libx264` | no | First MOV codec, so `--container mov` selects this. |
| `prores-proxy-mov` | `prores_ks` profile 0 | no | `-qscale:v 11`, `yuv422p10le` |
| `prores-lt-mov` | profile 1 | no | `-qscale:v 9` |
| `prores-422-mov` | profile 2 | no | `-qscale:v 6`. `formats.py` names this the default MOV codec, but nothing calls that helper. `--container mov` still picks `h264-cpu-mov`. |
| `prores-422-hq-mov` | profile 3 | no | `-qscale:v 4` |
| `prores-4444-mov` | profile 4 | yes | `-qscale:v 3`, `yuva444p10le` |
| `prores-4444-xq-mov` | profile 5 | yes | `-qscale:v 3`, `yuva444p10le` |

ProRes is CPU-only. The preset bitrate is not sent to FFmpeg for these keys. The GUI's size estimate multiplies the H.264 bitrate guess by about 2× (Proxy), 4× (LT), 8× (422), 12× (422 HQ), 15× (4444), and 20× (4444 XQ).

H.264 and HEVC use the preset bitrate as `-b:v`, with NVENC also setting `maxrate` and `bufsize` to that same value (`-rc vbr`).

### Image outputs

| Key | Extension | What FFmpeg actually gets |
|---|---|---|
| `png` | `.png` | `-compression_level 6` |
| `jpeg` | `.jpg` | `-q:v` mapped from `--quality` (95 → a mid-high FFmpeg qscale) |
| `tiff` | `.tiff` | `-compression_algo lzw` |
| `exr` | `.exr` | No extra flags |

The format objects mention 16-bit PNG/TIFF and 16/32-bit EXR. The extract command does not set a pixel format or bit depth, so those are not guaranteed.

## Encoder settings

From the `encoding` object in `config.json`. They apply to every image-to-video job.

| Key | Example | Effect |
|---|---|---|
| `use_gpu` | `true` | Try NVENC when the codec supports it. |
| `gpu_preset` | `p7` | NVENC preset. |
| `cpu_preset` | `veryslow` | x264 / x265 preset. |
| `tune` | `animation` | x264 only. |
| `pixel_format` | `yuv420p` | Stored on the config. The command uses the codec profile's pixel format (`yuv420p`, `yuv422p10le`, or `yuva444p10le`). |
| `keyframe_interval` | `60` | `-g` for H.264 and HEVC. |
| `b_frames` | `3` | `-bf` for H.264 and HEVC. |
| `rc_lookahead` | `32` | NVENC only. |
| `spatial_aq`, `temporal_aq` | `1` | NVENC only. |

## Configuration

`config.json` is gitignored and per machine. `config.example.json` is the schema.

```json
{
  "project_name": "COSMIC-HUMANITY",
  "renders_folder": "../_RENDERS",
  "output_folder": "../_RENDERS",
  "ffmpeg_path": "C:/Tools/ffmpeg/bin/ffmpeg.exe",
  "auto_create_output": true,
  "defaults": {
    "resolution": "2048x2048",
    "bitrate": "100M",
    "file_extension": "jpeg",
    "fps": 60,
    "preset_name": "fulldome-2k",
    "output_codec": "h264-nvenc-mp4"
  },
  "presets": [],
  "encoding": {},
  "extraction": {
    "output_format": "png",
    "jpeg_quality": 95,
    "png_compression": 6,
    "name_pattern": "{video_name}_%05d"
  },
  "ui": {
    "theme": "frog_splash",
    "show_file_count": true,
    "auto_select_latest": true
  }
}
```

| Key | Used by |
|---|---|
| `renders_folder` | CLI `convert` looks for `renders_folder/FOLDER`. The image-to-video GUI scans its immediate subfolders for jpeg/jpg/png. |
| `output_folder` | CLI `convert` destination. CLI `extract` default parent. Video-to-image GUI "recent videos" scan. Created when missing if `auto_create_output` is true. |
| `ffmpeg_path` | Every encode and probe. |
| `defaults` | Fallback preset fields, input extension, and codec. |
| `presets` | `--preset` and the GUI preset list. |
| `encoding` | H.264 / HEVC flags above. |
| `extraction` | Loaded into config. The `extract` CLI and the current GUI do not apply this block. Pass `--format` and `--quality` instead. |
| `ui` | TUI only. |

The image-to-video GUI quits immediately if `renders_folder` has no subfolder containing images. Browse never runs in that case. Headless `convert` does not have that problem: name the folder directly.

## Interactive GUI

For a person on Windows. Agents should stay in [Headless operation](#headless-operation).

```bash
python -m src gui            # launcher: 1 = image→video, 2 = video→frames
python -m src img2video
python -m src video2img
frogmpeg-gui.bat             # creates venv if needed, then the launcher
```

With no path, image-to-video lists sequence folders inside `renders_folder`, and video-to-frames lists videos inside `output_folder`.

Pass a path to open the GUI on that folder instead:

```bash
python -m src img2video /path/to/shot          # frames live directly in shot
python -m src img2video /path/to/renders       # lists sequence folders inside renders
python -m src img2video .                      # the current directory
python -m src video2img /path/to/videos        # lists mp4/mov/mkv/avi/webm in that folder
python -m src video2img /path/to/show.mp4      # opens that file
python -m src gui /path/to/shot                # launcher, then the mode you pick uses this folder
python -m src gui /path/to/show.mp4            # skips the launcher and opens video-to-frames
```

A sequence folder (jpeg, jpg, or png files in the folder itself) is selected immediately. The list shows the first frames, and the input extension switches to whichever of those three is most common. A parent folder lists each child folder that contains frames; `[S]` still converts the highlighted folder, not a single file. The video is written next to that sequence folder, same as an unscoped GUI session.

`video2img` on a folder shows the videos in it. Enter loads the highlighted file. `video2img` on a file probes it immediately. `[R]` rescans the same folder. A missing path exits with an error and does not open the screen.

Shared keys: `[S]` start, `[B]` browse, `[R]` refresh, `[L]` back to the launcher, `[Q]` quit, Tab / Shift+Tab to change section, arrows to move. Active selection is white reverse; inactive selection is green reverse.

Image-to-video sections: folders, preset, extension (`jpeg` / `jpg` / `png`), container, codec. The preview shows duration, resolution, bitrate, codec, and a rough file size.

Video-to-image sections: video, format, sample rate (all frames, 1, 5, 10, 24, 30 fps), JPEG quality (50–100). `[B]` opens a file dialog. The GUI extracts the whole file. A start or end time is `extract --start` and `--end` only.

`python -m src browse` is a third interactive path: folder dialog, then a preset number, then a format menu limited to H.264 NVENC, HEVC NVENC, ProRes 422, ProRes 422 HQ, and ProRes 4444.

## Setup

```bash
python -m venv venv
# Windows: venv\Scripts\activate
# POSIX:   source venv/bin/activate
pip install -r requirements.txt
python -m src init
python -m src validate
```

Windows launchers `frogmpeg.bat` and `frogmpeg-gui.bat` create `venv` and install the package if needed. `frogmpeg.bat convert MyShot --preset fulldome-2k` is headless. `frogmpeg-gui.bat` is not.

Browse dialogs need tkinter. Headless `convert` and `extract` do not.

`python -m src --version` prints the version.

## Other docs

`docs/INSTALLATION.md`, `docs/CONFIGURATION.md`, and `docs/USAGE.md` are shorter notes. Where they disagree with this file (including `python -m frogmpeg --gui`), follow this README.
