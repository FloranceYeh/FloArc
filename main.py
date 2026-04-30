import os
import tkinter as tk

from floarc.config import load_config
from floarc import winapi
from floarc.tracker import BlurTracker, reset_transparency_for_all_windows

CONFIG_FILE = "config.yaml"


def main():
    cfg = load_config(CONFIG_FILE)

    print("🌟 FloArc Started...")
    print(f"📄 Current Config: {os.path.abspath(CONFIG_FILE)}")

    if cfg.get("cleanup", {}).get("reset_on_start", True):
        reset_transparency_for_all_windows(cfg)

    root = tk.Tk()
    root.overrideredirect(True)
    root.config(bg="black")
    root.withdraw()

    root.update_idletasks()
    blur_hwnd = int(root.wm_frame(), 16)

    style = winapi.user32.GetWindowLongW(blur_hwnd, winapi.GWL_EXSTYLE)
    winapi.user32.SetWindowLongW(
        blur_hwnd,
        winapi.GWL_EXSTYLE,
        style
        | winapi.WS_EX_LAYERED
        | winapi.WS_EX_TRANSPARENT
        | winapi.WS_EX_NOACTIVATE
        | winapi.WS_EX_TOOLWINDOW,
    )

    winapi.apply_acrylic_blur(blur_hwnd, cfg["blur"]["color"], cfg["blur"]["intensity"])

    tracker = BlurTracker(cfg, root, blur_hwnd)
    tracker.tick()

    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        tracker.cleanup()


if __name__ == "__main__":
    main()
