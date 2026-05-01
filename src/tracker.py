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
        self.opacity_initialized = False
        self.modified_window_states = {}

    def _get_blur_settings(self):
        return self.cfg.get("blur", {})

    def _get_window_opacity_settings(self):
        return self.cfg.get("windows_opacity", {})

    def _get_configured_window_opacity(self, key):
        settings = self._get_window_opacity_settings()
        if not settings.get("enabled", False):
            return None

        try:
            alpha = int(settings.get(key, -1))
        except (TypeError, ValueError):
            return None

        if alpha < 0:
            return None
        return max(0, min(255, alpha))

    def _window_opacity_enabled(self):
        settings = self._get_window_opacity_settings()
        if not settings.get("enabled", False):
            return False
        return (
            self._get_configured_window_opacity("focused") is not None
            or self._get_configured_window_opacity("unfocused") is not None
        )

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

    def _remember_window_state(self, hwnd):
        if hwnd in self.modified_window_states:
            return True

        state = winapi.capture_window_opacity_state(hwnd)
        if state["is_layered"] and state["alpha"] is None:
            return False

        self.modified_window_states[hwnd] = state
        return True

    def _apply_window_opacity(self, hwnd, alpha):
        if alpha is None or not hwnd or not winapi.user32.IsWindow(hwnd):
            return
        if self.should_exclude_window(hwnd):
            return
        if not self._remember_window_state(hwnd):
            return

        winapi.apply_window_opacity(hwnd, alpha)

    def _restore_window_opacity(self, hwnd):
        state = self.modified_window_states.pop(hwnd, None)
        if not state or not hwnd or not winapi.user32.IsWindow(hwnd):
            return

        winapi.restore_window_opacity(hwnd, state)

    def _iter_valid_windows(self):
        windows = []

        def collect(hwnd, _lparam):
            if self.is_valid_window(hwnd):
                windows.append(hwnd)
            return True

        winapi.enum_windows(collect)
        return windows

    def _sync_initial_window_opacity(self, focused_hwnd):
        if self.opacity_initialized or not self._window_opacity_enabled():
            return

        focused_alpha = self._get_configured_window_opacity("focused")
        unfocused_alpha = self._get_configured_window_opacity("unfocused")

        for hwnd in self._iter_valid_windows():
            if hwnd == focused_hwnd:
                if focused_alpha is not None:
                    self._apply_window_opacity(hwnd, focused_alpha)
            elif unfocused_alpha is not None:
                self._apply_window_opacity(hwnd, unfocused_alpha)

        self.opacity_initialized = True

    def _update_window_opacity(self, previous_hwnd, current_hwnd):
        if not self._window_opacity_enabled():
            return

        if not self.opacity_initialized:
            self._sync_initial_window_opacity(current_hwnd)

        focused_alpha = self._get_configured_window_opacity("focused")
        unfocused_alpha = self._get_configured_window_opacity("unfocused")

        if previous_hwnd and previous_hwnd != current_hwnd:
            if unfocused_alpha is None:
                self._restore_window_opacity(previous_hwnd)
            elif not self.should_exclude_window(previous_hwnd):
                self._apply_window_opacity(previous_hwnd, unfocused_alpha)

        if current_hwnd:
            if focused_alpha is None:
                self._restore_window_opacity(current_hwnd)
            else:
                self._apply_window_opacity(current_hwnd, focused_alpha)

    def tick(self):
        fg_hwnd = winapi.user32.GetForegroundWindow()
        next_target_hwnd = fg_hwnd if self.is_valid_window(fg_hwnd) else None

        self._sync_initial_window_opacity(next_target_hwnd)

        if next_target_hwnd != self.current_target_hwnd:
            previous_target_hwnd = self.current_target_hwnd

            if next_target_hwnd:
                self.current_target_hwnd = next_target_hwnd
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

            self._update_window_opacity(previous_target_hwnd, self.current_target_hwnd)

        self._fade_in_blur()
        self._update_blur_position()
        self.root.after(16, self.tick)

    def cleanup(self):
        for hwnd in list(self.modified_window_states):
            self._restore_window_opacity(hwnd)

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
