import fnmatch

from . import winapi


class BlurTracker:
    def __init__(self, cfg, root, blur_hwnd):
        self.cfg = cfg
        self.root = root
        self.blur_hwnd = blur_hwnd
        self.current_target_hwnd = None
        self.blur_last_rect = None
        self.touched_hwnds = set()

    def _get_blur_settings(self):
        return self.cfg.get("blur", {})

    def _get_opacity_settings(self):
        return self.cfg.get("opacity", {})

    def _is_transparency_enabled(self):
        return bool(self._get_opacity_settings().get("enabled", True))

    def _get_padding(self):
        padding = self._get_blur_settings().get("padding", {})
        return {
            "left": int(padding.get("left", 0)),
            "top": int(padding.get("top", 0)),
            "right": int(padding.get("right", 0)),
            "bottom": int(padding.get("bottom", 0)),
        }

    def _get_rounding_radius(self):
        rounded = self._get_blur_settings().get("rounded_corners", {})
        if isinstance(rounded, dict):
            if not rounded.get("enabled", True):
                return 0
            try:
                return max(0, int(rounded.get("radius", 0)))
            except (TypeError, ValueError):
                return 0
        try:
            return max(0, int(rounded))
        except (TypeError, ValueError):
            return 0

    def _get_rounding_mode(self):
        rounded = self._get_blur_settings().get("rounded_corners", {})
        if isinstance(rounded, dict):
            return str(rounded.get("mode", "region")).lower()
        return "region"

    def _log_transparency(self, hwnd, alpha, reason):
        handle_hex = f"0x{int(hwnd):X}"
        print(f"Transparency set: hwnd={handle_hex} alpha={alpha} reason={reason}")

    def _apply_transparency(self, hwnd, alpha, reason):
        if not self._is_transparency_enabled():
            return False
        winapi.set_window_transparency(hwnd, alpha)
        self._log_transparency(hwnd, alpha, reason)
        return True

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

    def reset_all_transparency(self):
        def callback(hwnd, lparam):
            if winapi.user32.IsWindow(hwnd) and not self.should_exclude_window(hwnd):
                winapi.reset_window_transparency(hwnd)
            return True

        winapi.enum_windows(callback)

    def reset_touched_transparency(self):
        for hwnd in list(self.touched_hwnds):
            if winapi.user32.IsWindow(hwnd):
                winapi.reset_window_transparency(hwnd)
        self.touched_hwnds.clear()
        self.current_target_hwnd = None

    def _apply_padding(self, rect):
        padding = self._get_padding()
        rect.left += padding["left"]
        rect.top += padding["top"]
        rect.right -= padding["right"]
        rect.bottom -= padding["bottom"]
        return rect

    def _get_target_rect(self, hwnd):
        mode = str(self._get_blur_settings().get("bounds_mode", "client")).lower()
        rect = winapi.get_window_rect(hwnd, mode)
        return self._apply_padding(rect)

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

        winapi.apply_rounding(
            self.blur_hwnd,
            w, h,
            self._get_rounding_radius(),
            self._get_rounding_mode(),
        )
        self.blur_last_rect = current_rect

    def tick(self):
        fg_hwnd = winapi.user32.GetForegroundWindow()

        if fg_hwnd != self.current_target_hwnd:
            if self.current_target_hwnd and winapi.user32.IsWindow(self.current_target_hwnd):
                unfocused_alpha = self._get_opacity_settings().get("unfocused", 245)
                if self._apply_transparency(self.current_target_hwnd, unfocused_alpha, "unfocused"):
                    self.touched_hwnds.add(self.current_target_hwnd)

            if self.is_valid_window(fg_hwnd):
                self.current_target_hwnd = fg_hwnd
                focused_alpha = self._get_opacity_settings().get("focused", 220)
                if self._apply_transparency(self.current_target_hwnd, focused_alpha, "focused"):
                    self.touched_hwnds.add(self.current_target_hwnd)
                self.blur_last_rect = None
            else:
                self.current_target_hwnd = None
                self.blur_last_rect = None
                winapi.user32.SetWindowPos(
                    self.blur_hwnd,
                    0, 0, 0, 0, 0,
                    winapi.SWP_NOMOVE
                    | winapi.SWP_NOSIZE
                    | winapi.SWP_NOACTIVATE
                    | winapi.SWP_HIDEWINDOW,
                )

        self._update_blur_position()
        self.root.after(16, self.tick)

    def cleanup(self):
        if self.cfg.get("cleanup", {}).get("reset_on_exit", True):
            if self.cfg.get("cleanup", {}).get("reset_all_on_exit", True):
                self.reset_all_transparency()
            else:
                self.reset_touched_transparency()

        if self.blur_hwnd and winapi.user32.IsWindow(self.blur_hwnd):
            winapi.user32.SetWindowPos(
                self.blur_hwnd,
                0, 0, 0, 0, 0,
                winapi.SWP_NOMOVE
                | winapi.SWP_NOSIZE
                | winapi.SWP_NOACTIVATE
                | winapi.SWP_HIDEWINDOW,
            )

        if self.root is not None:
            self.root.destroy()


def reset_transparency_for_all_windows(cfg, blur_hwnd=None):
    tracker = BlurTracker(cfg, None, blur_hwnd)
    tracker.reset_all_transparency()
