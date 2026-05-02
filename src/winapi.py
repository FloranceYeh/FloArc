import os
import ctypes
from ctypes import wintypes, c_int, Structure, POINTER, byref, sizeof
import time

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
gdi32 = ctypes.windll.gdi32
dwmapi = ctypes.windll.dwmapi


class ACCENT_POLICY(Structure):
    _fields_ = [
        ("AccentState", c_int),
        ("AccentFlags", c_int),
        ("GradientColor", c_int),
        ("AnimationId", c_int),
    ]


class WINDOWCOMPOSITIONATTRIBDATA(Structure):
    _fields_ = [
        ("Attribute", c_int),
        ("Data", POINTER(ACCENT_POLICY)),
        ("SizeOfData", c_int),
    ]


class POINT(Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


GWL_EXSTYLE = -20
GWLP_HWNDPARENT = -8
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
LWA_COLORKEY = 0x00000001
LWA_ALPHA = 0x00000002

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SWP_HIDEWINDOW = 0x0080

DWMWA_EXTENDED_FRAME_BOUNDS = 9
DWMWA_CLOAKED = 14
DWMWA_WINDOW_CORNER_PREFERENCE = 33

DWMWCP_DEFAULT = 0
DWMWCP_DONOTROUND = 1
DWMWCP_ROUND = 2

AW_ACTIVATE = 0x00020000
AW_BLEND = 0x00080000
AW_HIDE = 0x00010000

_BLUR_FADE_STATE = {}


def _clamp_byte(value, default=255):
    try:
        return max(0, min(255, int(value)))
    except (TypeError, ValueError):
        return default


def get_gradient_color(hex_color, opacity):
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
    except (TypeError, ValueError):
        r, g, b = 255, 255, 255
    alpha = _clamp_byte(opacity, default=64)
    return (alpha << 24) | (b << 16) | (g << 8) | r


def apply_acrylic_blur(hwnd, hex_color, blur_opacity, blur_alpha):
    accent = ACCENT_POLICY()
    accent.AccentState = 4
    accent.GradientColor = get_gradient_color(hex_color, blur_opacity)

    data = WINDOWCOMPOSITIONATTRIBDATA()
    data.Attribute = 19
    data.SizeOfData = sizeof(accent)
    data.Data = ctypes.cast(byref(accent), POINTER(ACCENT_POLICY))
    user32.SetWindowCompositionAttribute(hwnd, byref(data))
    set_window_alpha(hwnd, blur_alpha)


def get_window_exstyle(hwnd):
    return user32.GetWindowLongW(hwnd, GWL_EXSTYLE)


def set_window_exstyle(hwnd, exstyle):
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, exstyle)


def set_window_owner(hwnd, owner_hwnd):
    try:
        user32.SetWindowLongPtrW(hwnd, GWLP_HWNDPARENT, owner_hwnd)
    except AttributeError:
        user32.SetWindowLongW(hwnd, GWLP_HWNDPARENT, owner_hwnd)


def set_window_alpha(hwnd, alpha):
    user32.SetLayeredWindowAttributes(hwnd, 0, _clamp_byte(alpha), LWA_ALPHA)


def get_layered_window_alpha(hwnd):
    color_key = wintypes.DWORD()
    alpha = wintypes.BYTE()
    flags = wintypes.DWORD()
    if not user32.GetLayeredWindowAttributes(hwnd, byref(color_key), byref(alpha), byref(flags)):
        return None
    if not (flags.value & LWA_ALPHA):
        return None
    return int(alpha.value)


def capture_window_opacity_state(hwnd):
    exstyle = get_window_exstyle(hwnd)
    is_layered = bool(exstyle & WS_EX_LAYERED)
    return {
        "exstyle": exstyle,
        "is_layered": is_layered,
        "alpha": get_layered_window_alpha(hwnd) if is_layered else 255,
    }


def apply_window_opacity(hwnd, alpha):
    exstyle = get_window_exstyle(hwnd)
    if not (exstyle & WS_EX_LAYERED):
        set_window_exstyle(hwnd, exstyle | WS_EX_LAYERED)
    return bool(user32.SetLayeredWindowAttributes(hwnd, 0, _clamp_byte(alpha), LWA_ALPHA))


def restore_window_opacity(hwnd, state):
    if not state:
        return

    exstyle = state.get("exstyle")
    if exstyle is not None:
        set_window_exstyle(hwnd, exstyle)

    if state.get("is_layered") and state.get("alpha") is not None:
        user32.SetLayeredWindowAttributes(hwnd, 0, _clamp_byte(state["alpha"]), LWA_ALPHA)


def reset_blur_fade(hwnd):
    _BLUR_FADE_STATE.pop(hwnd, None)


def blur_fade_in(hwnd, target_alpha, duration_ms=200, restart=False):
    target_alpha = _clamp_byte(target_alpha)
    duration_ms = max(1, int(duration_ms or 0))
    now = time.monotonic()

    state = _BLUR_FADE_STATE.get(hwnd)
    if restart or state is None or state["target_alpha"] != target_alpha or state["duration_ms"] != duration_ms:
        state = {
            "started_at": now,
            "duration_ms": duration_ms,
            "target_alpha": target_alpha,
            "current_alpha": 0,
            "done": False,
        }
        _BLUR_FADE_STATE[hwnd] = state
        set_window_alpha(hwnd, 0)
        return 0

    if state["done"]:
        return state["current_alpha"]

    progress = min(1.0, (now - state["started_at"]) * 1000.0 / state["duration_ms"])
    eased = 1.0 - pow(1.0 - progress, 3.0)
    alpha = int(round(state["target_alpha"] * eased))
    if progress >= 1.0:
        alpha = state["target_alpha"]
        state["done"] = True

    if alpha != state["current_alpha"]:
        state["current_alpha"] = alpha
        set_window_alpha(hwnd, alpha)

    return alpha


def get_window_text(hwnd):
    length = user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def get_window_class_name(hwnd):
    buffer = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buffer, 256)
    return buffer.value


def get_window_exe_name(hwnd):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, byref(pid))
    if not pid.value:
        return None

    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not handle:
        return None
    try:
        buf_len = wintypes.DWORD(1024)
        buffer = ctypes.create_unicode_buffer(buf_len.value)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, byref(buf_len)):
            return os.path.basename(buffer.value).lower()
    finally:
        kernel32.CloseHandle(handle)
    return None


def is_window_visible(hwnd):
    return bool(user32.IsWindowVisible(hwnd))


def is_window_iconic(hwnd):
    return bool(user32.IsIconic(hwnd))


def is_window_cloaked(hwnd):
    cloaked = wintypes.DWORD()
    hr = dwmapi.DwmGetWindowAttribute(
        hwnd, DWMWA_CLOAKED, byref(cloaked), sizeof(cloaked)
    )
    return hr == 0 and cloaked.value != 0


def get_window_rect_fallback(hwnd):
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, byref(rect))
    return rect


def get_window_rect_extended(hwnd):
    rect = wintypes.RECT()
    hr = dwmapi.DwmGetWindowAttribute(
        hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, byref(rect), sizeof(rect)
    )
    if hr != 0:
        return get_window_rect_fallback(hwnd)
    return rect


def get_window_rect_client(hwnd):
    rect = wintypes.RECT()
    if not user32.GetClientRect(hwnd, byref(rect)):
        return get_window_rect_fallback(hwnd)

    points = (POINT * 2)(POINT(rect.left, rect.top), POINT(rect.right, rect.bottom))
    user32.MapWindowPoints(hwnd, 0, points, 2)
    return wintypes.RECT(points[0].x, points[0].y, points[1].x, points[1].y)


def get_window_rect(hwnd, mode):
    if mode == "client":
        return get_window_rect_client(hwnd)
    if mode == "extended":
        return get_window_rect_extended(hwnd)
    return get_window_rect_fallback(hwnd)


def apply_rounding(hwnd, width, height, radius, mode):
    if str(mode).lower() == "dwm":
        preference = DWMWCP_ROUND if radius > 0 else DWMWCP_DONOTROUND
        value = ctypes.c_int(preference)
        dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_WINDOW_CORNER_PREFERENCE,
            byref(value),
            sizeof(value),
        )
        return

    if radius <= 0:
        user32.SetWindowRgn(hwnd, 0, True)
        return

    ellipse = max(2, radius * 2)
    region = gdi32.CreateRoundRectRgn(0, 0, width + 1, height + 1, ellipse, ellipse)
    if region:
        user32.SetWindowRgn(hwnd, region, True)


def enum_windows(callback):
    enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(enum_proc(callback), 0)
