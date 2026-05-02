# FloArc

FloArc is a lightweight Windows utility that generates Acrylic blur overlays for all valid top-level windows and dynamically adjusts window opacity based on its focus state.

[Chinese README](README_zh-cn.md)

## Features

- Tracks the position and size of the client area of each valid top-level window.
- Keeps Acrylic blur overlays on both focused and unfocused windows.
- Sets separate opacity levels for focused and unfocused windows.
- Configurable transition durations for opacity changes between focus states.
- Automatically excludes temporary windows by default (e.g., Desktop, Taskbar, System Tray popups, Menus, Dropdowns, Tooltips).
- Runs quietly in the System Tray with `Restart` and `Close` options.

## Requirements

- Windows 10 / 11
- Python 3
- `PyYAML`

## Installation

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run directly:

```powershell
python main.py
```

On first launch, a default `config.yaml` will be generated automatically if it does not exist in the program directory.

## Configuration

The default template generated on first startup is as follows:

```yaml
windows_opacity:
  focused: 200   # 0 - 255, -1 = disable
  unfocused: 220 # 0 - 255, -1 = disable
  transition_duration:
    focus: 500    # milliseconds, -1 = instant
    unfocus: 500  # milliseconds, -1 = instant

# Blur overlay settings
blur:
  color: "333333"
  opacity: 32    # 0 - 255
  alpha: 220     # 0 - 255
  animate_duration: 500

# Exclusion rules
exclude:
  classes:
    - Progman
    - WorkerW
    - Shell_TrayWnd
    - Shell_SecondaryTrayWnd
    - NotifyIconOverflowWindow
    - "#32768"
    - ComboLBox
    - tooltips_class32
    - Xaml_WindowedPopupClass
    - Windows.UI.Core.CoreWindow
    - ConsoleWindowClass
  titles:
    - "Windhawk"
  executables:
    - "Pixpin.exe"
    - "Flow.Launcher.exe"
```

**Configuration Details:**

- `windows_opacity.focused`: Opacity of the focused window (0-255). Set to `-1` to disable management.
- `windows_opacity.unfocused`: Opacity of unfocused windows (0-255). Set to `-1` to disable management.
- `windows_opacity.transition_duration.focus`: Transition duration when gaining focus (ms). Set to `-1` or `0` for instant change.
- `windows_opacity.transition_duration.unfocus`: Transition duration when losing focus (ms). Set to `-1` or `0` for instant change.
- `blur.color`: Color of the blur overlay (Hex RGB string without `#`).
- `blur.opacity`: Intensity of the overlay color (0-255).
- `blur.alpha`: Transparency of the overlay window itself (0-255).
- `blur.animate_duration`: Fade-in duration of the blur overlay (ms).
- `exclude.classes`: Exclude windows by exact class name.
- `exclude.titles`: Exclude windows whose titles contain these substrings.
- `exclude.executables`: Exclude processes by executable name (wildcards supported, case-insensitive).

**Notes:**
- If both `focused` and `unfocused` are set to `-1`, FloArc will only display the blur overlays without modifying window opacity.
- Default exclusion items are merged at runtime; manual addition of common system windows (Taskbar, Tray, Menus, etc.) is not required.
- Exclusion rules only affect window selection and opacity management; they do not modify the excluded windows themselves.

**Common Usage Example:**

```yaml
windows_opacity:
  focused: 235
  unfocused: 210
  transition_duration:
    focus: 180
    unfocus: 320

blur:
  color: "2B2B2B"
  opacity: 28
  alpha: 215
  animate_duration: 350

exclude:
  classes:
    - Progman
    - WorkerW
  titles: []
  executables:
    - "msedge.exe"
```

## Tray

The application runs in the System Tray upon launch.

- Right-click the tray icon to access `Restart` and `Close`.
- `Restart` relaunches the app with current parameters and reloads `config.yaml`.
- `Close` stops tracking, restores original opacity for managed windows, and exits the program.

## Build

Install PyInstaller:

```powershell
pip install pyinstaller
```

Execute build:

```powershell
pyinstaller FloArc.spec
```

Output location:

```text
dist/FloArc.exe
```

**Deployment Notes:**
- `FloArc.spec` sets `runtime_tmpdir='.'`, so the PyInstaller `_MEIxxxxxx` temp directory follows the current working directory.
- The working directory is switched to the executable's location on startup, and `config.yaml` is always read from there.

## Notes

- Under normal exit conditions, PyInstaller attempts to auto-delete the `_MEIxxxxxx` temporary directory.
- If the process is forcibly terminated or handles remain open, you may see `Failed to remove temporary directory: ...`. Manual deletion after the process fully exits is usually safe.
- Certain custom-drawn or special layered windows may not handle opacity changes well; add them to the exclusion list if necessary.
- The current logic only processes visible, non-minimized, top-level windows that are not cloaked by the system.
