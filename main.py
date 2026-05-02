import os
import subprocess
import sys
import tkinter as tk

from src.config import load_config
from src.tracker import BlurTracker
from src.tray import TrayController


def _get_app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


APP_DIR = _get_app_dir()
CONFIG_FILE = os.path.join(APP_DIR, "config.yaml")


def _build_restart_command():
    if getattr(sys, "frozen", False):
        return [sys.executable, *sys.argv[1:]]
    return [sys.executable, os.path.abspath(__file__), *sys.argv[1:]]


def main():
    os.chdir(APP_DIR)
    cfg = load_config(CONFIG_FILE)

    print("FloArc started...")
    print(f"Current config: {CONFIG_FILE}")

    root = tk.Tk()
    root.overrideredirect(True)
    root.config(bg="black")
    root.withdraw()

    tracker = BlurTracker(cfg, root)
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
            subprocess.Popen(_build_restart_command(), cwd=APP_DIR)


if __name__ == "__main__":
    main()
