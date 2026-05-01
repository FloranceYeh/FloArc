import os
import subprocess
import sys
import tkinter as tk

from src import winapi
from src.config import load_config
from src.tracker import BlurTracker
from src.tray import TrayController

CONFIG_FILE = "config.yaml"


def _build_restart_command():
    if getattr(sys, "frozen", False):
        return [sys.executable, *sys.argv[1:]]
    return [sys.executable, os.path.abspath(__file__), *sys.argv[1:]]


def main():
    cfg = load_config(CONFIG_FILE)

    print("FloArc started...")
    print(f"Current config: {os.path.abspath(CONFIG_FILE)}")

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

    winapi.apply_acrylic_blur(
        blur_hwnd,
        cfg["blur"]["color"],
        cfg["blur"]["opacity"],
        cfg["blur"]["alpha"],
    )

    tracker = BlurTracker(cfg, root, blur_hwnd)
    tracker.tick()

    tray = TrayController("FloArc")
    shutdown_requested = False
    restart_requested = False

    def request_shutdown(restart=False):
        nonlocal shutdown_requested, restart_requested
        if shutdown_requested:
            return
        shutdown_requested = True
        restart_requested = restart
        try:
            root.quit()
        except tk.TclError:
            pass

    def poll_tray_actions():
        if shutdown_requested:
            return

        for action in tray.drain_actions():
            if action == "restart":
                request_shutdown(restart=True)
                return
            if action == "close":
                request_shutdown(restart=False)
                return

        root.after(100, poll_tray_actions)

    try:
        tray.start()
        root.after(100, poll_tray_actions)
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        tray.stop()
        tracker.cleanup()
        try:
            if root.winfo_exists():
                root.destroy()
        except tk.TclError:
            pass

        if restart_requested:
            subprocess.Popen(_build_restart_command(), cwd=os.getcwd())


if __name__ == "__main__":
    main()
