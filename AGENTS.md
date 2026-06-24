# FloArc — Agent Guide

**Windows-only** Python app that tracks the foreground window and renders an acrylic blur overlay behind it. Built with tkinter + raw `ctypes` Win32 API.

## Quick start

```powershell
pip install -r requirements.txt  # only PyYAML
python main.py
```

First run auto-generates `config.yaml` next to the script. No other setup needed.

## Dev commands

| Action | Command |
|---|---|
| Run | `python main.py` |
| Build exe | `pip install pyinstaller && pyinstaller --noconfirm --clean FloArc.spec` |
| Test | — none exist (no test framework, no test files) |
| Lint | — none configured |
| Typecheck | — none configured |

## Architecture

- **`main.py`** — entrypoint. Creates hidden `tk.Tk()` window, applies acrylic blur via `SetWindowCompositionAttribute`, starts tracker and tray.
- **`src/winapi.py`** — raw ctypes bindings to user32/dwmapi/gdi32/kernel32.
- **`src/tracker.py`** (`BlurTracker`) — polling loop (~16-50ms `root.after`) that finds the foreground window, validates it, positions the blur overlay, and animates opacity transitions.
- **`src/config.py`** — loads `config.yaml`, merges user overrides onto defaults, always preserves default exclusion list.
- **`src/tray.py`** (`TrayController`) — system tray icon in a **daemon thread** with its own Windows message loop. Communicates actions back to main thread via `queue.Queue`.

## Key quirks

- Uses **undocumented** `SetWindowCompositionAttribute` with `AccentState=4` (acrylic blur). This is the standard approach for Windows customization tools but has no documented contract.
- Blur overlay is a hidden tkinter `Tk()` window (`overrideredirect`, black bg). Its HWND is obtained via `root.wm_frame()`.
- Tray runs in a **daemon thread** — it terminates abruptly if main thread exits uncleanly. The code does `PostMessageW(WM_CLOSE)` + `thread.join(timeout=5)` for graceful stop.
- Opacity transitions and blur fade-in both use cubic ease-out: `1 - (1 - t)^3`.
- Exclusion matching: class name exact match, title substring (case-insensitive), exe name `fnmatch` (case-insensitive). Window state (class, title, exe, visibility, iconic, cloaked) is cached with **200ms TTL**.
- `runtime_tmpdir='.'` in `FloArc.spec` — PyInstaller temp dir follows CWD. App changes CWD to exe directory on startup. Hard-kill may leave `_MEI*` temp dirs behind.
- Config on restart: `config.yaml` is read fresh each launch. Config changes take effect on restart.

## Project structure

```
main.py          ← entrypoint
src/
  config.py      ← config loading/merging
  winapi.py      ← Win32 API bindings
  tracker.py     ← background tracking loop
  tray.py        ← system tray (daemon thread)
FloArc.spec      ← PyInstaller spec
config.yaml      ← auto-generated runtime config
```

## CI / release

- **Only on tag push** (`v*`) — no CI on push/PR to main. Windows GitHub runner, Python 3.12.
- Builds `FloArc.exe` with PyInstaller, zips with `config.yaml`, publishes GitHub Release with SHA256.
- No test/lint step in CI.

## What's not here

- No test files, no pytest config.
- No linter, formatter, or typechecker config.
- No package.json (`.gitignore`d — not part of the project).
