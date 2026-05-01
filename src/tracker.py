import fnmatch

from . import winapi


class BlurTracker:
    def __init__(self, cfg, root, blur_hwnd):
        self.cfg = cfg
        self.root = root
        self.blur_hwnd = blur_hwnd
        self.current_target_hwnd = None
        self.blur_last_rect = None
        self.blur_fade_restart = False

    def _get_blur_settings(self):
        return self.cfg.get("blur", {})

    def should_exclude_window(self, hwnd):
        if not hwnd or hwnd == self.blur_hwnd:
            return True

        class_name = winapi.get_window_class_name(hwnd)
        if class_name in self.cfg.get("exclude", {}).get("classes", []):
            return True

        title = winapi.get_window_text(hwnd)
        for excluded_title in self.cfg.get("exclude", {}).get("titles", []):
            if excluded_title in title:
                return True

        exe_name = winapi.get_window_exe_name(hwnd)
        for excluded_exe in self.cfg.get("exclude", {}).get("executables", []):
            if exe_name and fnmatch.fnmatch(exe_name, excluded_exe.lower()):
                return True

        return False

    def is_valid_window(self, hwnd):
        if self.should_exclude_window(hwnd):
            return False
        if winapi.is_window_iconic(hwnd) or not winapi.is_window_visible(hwnd):
            return False
        if winapi.is_window_cloaked(hwnd):
            return False
        return True

    def _get_target_rect(self, hwnd):
        return winapi.get_window_rect(hwnd, "client")

    def _update_blur_position(self):
        if not self.current_target_hwnd or not winapi.user32.IsWindow(self.current_target_hwnd):
            return

        rect = self._get_target_rect(self.current_target_hwnd)
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        if w <= 0 or h <= 0:
            return

        current_rect = (rect.left, rect.top, w, h)
        if current_rect == self.blur_last_rect:
            return

        winapi.user32.SetWindowPos(
            self.blur_hwnd,
            self.current_target_hwnd,
            rect.left,
            rect.top,
            w,
            h,
            winapi.SWP_NOACTIVATE | winapi.SWP_SHOWWINDOW,
        )

        self.blur_last_rect = current_rect
    
    def _fade_in_blur(self):
        settings = self._get_blur_settings()
        target_alpha = settings.get("alpha", 255)
        duration = settings.get("animate_duration", 200)
        winapi.blur_fade_in(
            self.blur_hwnd,
            target_alpha,
            duration,
            restart=self.blur_fade_restart,
        )
        self.blur_fade_restart = False

    def tick(self):
        fg_hwnd = winapi.user32.GetForegroundWindow()

        if fg_hwnd != self.current_target_hwnd:
            if self.is_valid_window(fg_hwnd):
                self.current_target_hwnd = fg_hwnd
                self.blur_last_rect = None
                self.blur_fade_restart = True
            else:
                self.current_target_hwnd = None
                self.blur_last_rect = None
                self.blur_fade_restart = False
                winapi.reset_blur_fade(self.blur_hwnd)
                winapi.user32.SetWindowPos(
                    self.blur_hwnd,
                    0, 0, 0, 0, 0,
                    winapi.SWP_NOMOVE
                    | winapi.SWP_NOSIZE
                    | winapi.SWP_NOACTIVATE
                    | winapi.SWP_HIDEWINDOW,
                )

        self._fade_in_blur()
        self._update_blur_position()
        self.root.after(16, self.tick)

    def cleanup(self):
        if self.blur_hwnd and winapi.user32.IsWindow(self.blur_hwnd):
            winapi.reset_blur_fade(self.blur_hwnd)
            winapi.user32.SetWindowPos(
                self.blur_hwnd,
                0, 0, 0, 0, 0,
                winapi.SWP_NOMOVE
                | winapi.SWP_NOSIZE
                | winapi.SWP_NOACTIVATE
                | winapi.SWP_HIDEWINDOW,
            )
