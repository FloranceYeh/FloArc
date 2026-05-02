import copy
import os
import textwrap

import yaml

DEFAULT_CONFIG_TEMPLATE = textwrap.dedent("""\
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
  # Exclude by window class name
  # Common transient UI: taskbar, tray popups, menus, combo dropdowns, tooltips
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
  # Exclude by window title (substring match)
  titles:
    - "Windhawk"
  # Exclude by executable name (wildcards allowed)
  executables:
    - "Pixpin.exe"
    - "Flow.Launcher.exe"
""")

DEFAULT_CONFIG = yaml.safe_load(DEFAULT_CONFIG_TEMPLATE)


def _merge_dicts(base, override):
    merged = dict(base)
    if not isinstance(override, dict):
        return merged

    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def _merge_default_exclusions(config):
    exclude = config.setdefault("exclude", {})
    defaults = DEFAULT_CONFIG.get("exclude", {})

    for key in ("classes", "titles", "executables"):
        merged = []
        for item in list(exclude.get(key, []) or []) + list(defaults.get(key, []) or []):
            if item not in merged:
                merged.append(item)
        exclude[key] = merged

    return config


def _normalize_config(config):
    windows_opacity = config.get("windows_opacity")
    if isinstance(windows_opacity, dict):
        windows_opacity.pop("enabled", None)
    return config


def load_config(path):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(DEFAULT_CONFIG_TEMPLATE)
        return copy.deepcopy(DEFAULT_CONFIG)

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return _normalize_config(
        _merge_default_exclusions(_merge_dicts(copy.deepcopy(DEFAULT_CONFIG), data))
    )
