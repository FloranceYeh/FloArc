import os
import yaml

DEFAULT_CONFIG = {
    "windows_opacity": {
        "enabled": True,
        "focused": 220,
        "unfocused": 245
    },
    "blur": {
        "color": "333333",
        "opacity": 32,
        "alpha": 220,
        "animate_duration": 200
    },
    "exclude": {
        "classes": [
            "Progman",
            "WorkerW",
            "Shell_TrayWnd",
            "Windows.UI.Core.CoreWindow",
            "ConsoleWindowClass"
        ],
        "titles": [
            "任务管理器",
            "Task Manager"
        ],
        "executables": []
    }
}


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
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(DEFAULT_CONFIG, f, allow_unicode=True, default_flow_style=False)
        return DEFAULT_CONFIG

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return _merge_dicts(DEFAULT_CONFIG, data)
