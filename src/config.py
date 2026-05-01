import copy
import os
import textwrap

import yaml

DEFAULT_CONFIG_TEMPLATE = textwrap.dedent("""\
windows_opacity:
  enabled: true  # enable focused/unfocused opacity switching
  focused: 220   # 0 - 255, -1 = skip
  unfocused: 245 # 0 - 255, -1 = skip

# Blur overlay settings
blur:
  color: "333333"
  opacity: 32    # 0 - 255
  alpha: 220     # 0 - 255
  animate_duration: 500

# Exclusion rules
exclude:
  # Exclude by window class name
  classes:
    - Progman
    - WorkerW
    - Shell_TrayWnd
    - Windows.UI.Core.CoreWindow
    - ConsoleWindowClass
  # Exclude by window title (substring match)
  titles:
    - "任务管理器"
    - "Task Manager"
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


def load_config(path):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(DEFAULT_CONFIG_TEMPLATE)
        return copy.deepcopy(DEFAULT_CONFIG)

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return _merge_dicts(copy.deepcopy(DEFAULT_CONFIG), data)
