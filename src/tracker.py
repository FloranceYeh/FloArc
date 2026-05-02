import fnmatch
import time

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
        self.window_opacity_transitions = {}

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

    def _get_window_opacity_transition_duration(self):
        settings = self._get_window_opacity_settings()
        try:
            duration = int(settings.get("transition_duration", 0))
        except (TypeError, ValueError):
            return 0
        return max(0, duration)

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

    def _get_current_window_opacity(self, hwnd):
        if not hwnd or not winapi.user32.IsWindow(hwnd):
            return None

        alpha = winapi.get_layered_window_alpha(hwnd)
        if alpha is None:
            return 255
        return max(0, min(255, int(alpha)))

    def _get_tracked_window_opacity(self, hwnd):
        transition = self.window_opacity_transitions.get(hwnd)
        if transition:
            return transition.get("current_alpha", transition.get("start_alpha"))
        return self._get_current_window_opacity(hwnd)

    def _restore_window_opacity_after_transition(self, hwnd):
        state = self.modified_window_states.pop(hwnd, None)
        if not state or not hwnd or not winapi.user32.IsWindow(hwnd):
            return

        winapi.restore_window_opacity(hwnd, state)

    def _schedule_restore_window_opacity(self, hwnd, duration_ms):
        state = self.modified_window_states.get(hwnd)
        if not state or not hwnd or not winapi.user32.IsWindow(hwnd):
            return

        target_alpha = state.get("alpha")
        if target_alpha is None:
            target_alpha = 255

        self._schedule_window_opacity_transition(hwnd, target_alpha, duration_ms, restore_after=True)

    def _schedule_window_opacity_transition(self, hwnd, alpha, duration_ms, restore_after=False):
        if alpha is None or not hwnd or not winapi.user32.IsWindow(hwnd):
            return
        if self.should_exclude_window(hwnd):
            return
        if not self._remember_window_state(hwnd):
            return

        target_alpha = max(0, min(255, int(alpha)))
        if restore_after:
            state = self.modified_window_states.get(hwnd)
            if state and state.get("alpha") is not None:
                target_alpha = max(0, min(255, int(state["alpha"])))
            else:
                target_alpha = 255

        duration_ms = max(0, int(duration_ms or 0))
        current_alpha = self._get_tracked_window_opacity(hwnd)
        if current_alpha is None:
            return

        existing = self.window_opacity_transitions.get(hwnd)
        if (
            existing
            and existing.get("target_alpha") == target_alpha
            and bool(existing.get("restore_after")) == bool(restore_after)
        ):
            return

        self.window_opacity_transitions.pop(hwnd, None)

        if duration_ms <= 0 or current_alpha == target_alpha:
            if restore_after:
                self._restore_window_opacity_after_transition(hwnd)
            else:
                winapi.apply_window_opacity(hwnd, target_alpha)
            return

        self.window_opacity_transitions[hwnd] = {
            "start_alpha": current_alpha,
            "target_alpha": target_alpha,
            "started_at": time.monotonic(),
            "duration_ms": duration_ms,
            "restore_after": restore_after,
            "current_alpha": current_alpha,
        }

    def _update_window_opacity_transitions(self):
        if not self.window_opacity_transitions:
            return

        now = time.monotonic()
        for hwnd, transition in list(self.window_opacity_transitions.items()):
            if not hwnd or not winapi.user32.IsWindow(hwnd):
                self.window_opacity_transitions.pop(hwnd, None)
                continue

            duration_ms = max(1, int(transition.get("duration_ms", 1)))
            progress = min(1.0, (now - transition["started_at"]) * 1000.0 / duration_ms)
            eased = 1.0 - pow(1.0 - progress, 3.0)
            alpha = int(
                round(
                    transition["start_alpha"]
                    + (transition["target_alpha"] - transition["start_alpha"]) * eased
                )
            )
            alpha = max(0, min(255, alpha))

            if alpha != transition.get("current_alpha"):
                winapi.apply_window_opacity(hwnd, alpha)
                transition["current_alpha"] = alpha

            if progress >= 1.0:
                if transition.get("restore_after"):
                    self._restore_window_opacity_after_transition(hwnd)
                self.window_opacity_transitions.pop(hwnd, None)

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

        duration = self._get_window_opacity_transition_duration()
        focused_alpha = self._get_configured_window_opacity("focused")
        unfocused_alpha = self._get_configured_window_opacity("unfocused")

        for hwnd in self._iter_valid_windows():
            if hwnd == focused_hwnd:
                if focused_alpha is not None:
                    if duration > 0:
                        self._schedule_window_opacity_transition(hwnd, focused_alpha, duration)
                    else:
                        self._apply_window_opacity(hwnd, focused_alpha)
            elif unfocused_alpha is not None:
                if duration > 0:
                    self._schedule_window_opacity_transition(hwnd, unfocused_alpha, duration)
                else:
                    self._apply_window_opacity(hwnd, unfocused_alpha)

        self.opacity_initialized = True

    def _update_window_opacity(self, previous_hwnd, current_hwnd):
        if not self._window_opacity_enabled():
            return

        if not self.opacity_initialized:
            self._sync_initial_window_opacity(current_hwnd)

        duration = self._get_window_opacity_transition_duration()
        focused_alpha = self._get_configured_window_opacity("focused")
        unfocused_alpha = self._get_configured_window_opacity("unfocused")

        if previous_hwnd and previous_hwnd != current_hwnd:
            if unfocused_alpha is None:
                self._schedule_restore_window_opacity(previous_hwnd, duration)
            elif not self.should_exclude_window(previous_hwnd):
                self._schedule_window_opacity_transition(previous_hwnd, unfocused_alpha, duration)

        if current_hwnd:
            if focused_alpha is None:
                self._schedule_restore_window_opacity(current_hwnd, duration)
            else:
                self._schedule_window_opacity_transition(current_hwnd, focused_alpha, duration)

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

        self._update_window_opacity_transitions()
        self._fade_in_blur()
        self._update_blur_position()
        self.root.after(16, self.tick)

    def cleanup(self):
        self.window_opacity_transitions.clear()
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
