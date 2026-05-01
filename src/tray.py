import ctypes
import queue
import threading
from ctypes import byref, sizeof, Structure
from ctypes import wintypes

user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32
kernel32 = ctypes.windll.kernel32

HINSTANCE = getattr(wintypes, "HINSTANCE", wintypes.HANDLE)
HICON = getattr(wintypes, "HICON", wintypes.HANDLE)
HCURSOR = getattr(wintypes, "HCURSOR", wintypes.HANDLE)
HBRUSH = getattr(wintypes, "HBRUSH", wintypes.HANDLE)
HMENU = getattr(wintypes, "HMENU", wintypes.HANDLE)
HMODULE = getattr(wintypes, "HMODULE", wintypes.HANDLE)

WM_NULL = 0x0000
WM_CLOSE = 0x0010
WM_DESTROY = 0x0002
WM_CONTEXTMENU = 0x007B
WM_RBUTTONUP = 0x0205
WM_APP = 0x8000
WM_TRAYICON = WM_APP + 1

NIM_ADD = 0
NIM_MODIFY = 1
NIM_DELETE = 2
NIM_SETVERSION = 4

NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004

TPM_RIGHTBUTTON = 0x0002
TPM_RETURNCMD = 0x0100

MF_STRING = 0x0000
IDI_APPLICATION = 32512

ID_TRAY_RESTART = 1001
ID_TRAY_CLOSE = 1002


class POINT(Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class MSG(Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", POINT),
    ]


class NOTIFYICONDATAW(Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", HICON),
        ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256),
        ("uTimeoutOrVersion", wintypes.UINT),
        ("szInfoTitle", wintypes.WCHAR * 64),
        ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", ctypes.c_byte * 16),
        ("hBalloonIcon", HICON),
    ]


WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
)


class WNDCLASSW(Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", HINSTANCE),
        ("hIcon", HICON),
        ("hCursor", HCURSOR),
        ("hbrBackground", HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


def _make_int_resource(value):
    return ctypes.cast(ctypes.c_void_p(value), wintypes.LPCWSTR)


def _loword(value):
    return value & 0xFFFF


user32.DefWindowProcW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.DefWindowProcW.restype = ctypes.c_ssize_t
user32.AppendMenuW.argtypes = [HMENU, wintypes.UINT, wintypes.UINT, wintypes.LPCWSTR]
user32.AppendMenuW.restype = wintypes.BOOL
user32.CreatePopupMenu.restype = HMENU
user32.CreateWindowExW.argtypes = [
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    wintypes.HMENU,
    HINSTANCE,
    wintypes.LPVOID,
]
user32.CreateWindowExW.restype = wintypes.HWND
user32.DestroyMenu.argtypes = [HMENU]
user32.DestroyMenu.restype = wintypes.BOOL
user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.DestroyWindow.restype = wintypes.BOOL
user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.GetCursorPos.restype = wintypes.BOOL
user32.GetMessageW.argtypes = [
    ctypes.POINTER(MSG),
    wintypes.HWND,
    wintypes.UINT,
    wintypes.UINT,
]
user32.GetMessageW.restype = ctypes.c_int
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = HMODULE
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL
user32.LoadIconW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR]
user32.LoadIconW.restype = HICON
user32.PostMessageW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.PostMessageW.restype = wintypes.BOOL
user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
user32.RegisterClassW.restype = wintypes.ATOM
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.TrackPopupMenu.argtypes = [
    HMENU,
    wintypes.UINT,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    ctypes.POINTER(wintypes.RECT),
]
user32.TrackPopupMenu.restype = wintypes.UINT
user32.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
user32.TranslateMessage.restype = wintypes.BOOL
user32.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]
user32.DispatchMessageW.restype = ctypes.c_ssize_t
shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]
shell32.Shell_NotifyIconW.restype = wintypes.BOOL


class TrayController:
    def __init__(self, tooltip="FloArc"):
        self.tooltip = tooltip[:127]
        self._actions = queue.Queue()
        self._thread = None
        self._ready = threading.Event()
        self._hwnd = None
        self._nid = None
        self._wndproc = None
        self._class_name = f"FloArcTray_{id(self):x}"
        self._error = None

    def start(self):
        if self._thread is not None:
            return

        self._thread = threading.Thread(target=self._run, name="FloArcTray", daemon=True)
        self._thread.start()

        if not self._ready.wait(timeout=5):
            raise RuntimeError("Tray icon did not initialize in time.")
        if self._error is not None:
            raise RuntimeError("Tray icon failed to initialize.") from self._error

    def stop(self):
        hwnd = self._hwnd
        if hwnd:
            user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)

        thread = self._thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=5)

    def drain_actions(self):
        actions = []
        while True:
            try:
                actions.append(self._actions.get_nowait())
            except queue.Empty:
                break
        return actions

    def _run(self):
        try:
            hinstance = kernel32.GetModuleHandleW(None)
            self._wndproc = WNDPROC(self._window_proc)

            wndclass = WNDCLASSW()
            wndclass.lpfnWndProc = self._wndproc
            wndclass.hInstance = hinstance
            wndclass.hIcon = user32.LoadIconW(None, _make_int_resource(IDI_APPLICATION))
            wndclass.lpszClassName = self._class_name

            if not user32.RegisterClassW(byref(wndclass)):
                error = ctypes.get_last_error()
                if error not in (0, 1410):
                    raise ctypes.WinError(error)

            self._hwnd = user32.CreateWindowExW(
                0,
                self._class_name,
                self.tooltip,
                0,
                0,
                0,
                0,
                0,
                None,
                None,
                hinstance,
                None,
            )
            if not self._hwnd:
                raise ctypes.WinError(ctypes.get_last_error())

            self._add_icon()
            self._ready.set()

            msg = MSG()
            while user32.GetMessageW(byref(msg), None, 0, 0) > 0:
                user32.TranslateMessage(byref(msg))
                user32.DispatchMessageW(byref(msg))
        except Exception as exc:
            self._error = exc
            self._ready.set()
        finally:
            self._cleanup()
            self._ready.set()

    def _add_icon(self):
        self._nid = NOTIFYICONDATAW()
        self._nid.cbSize = sizeof(self._nid)
        self._nid.hWnd = self._hwnd
        self._nid.uID = 1
        self._nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        self._nid.uCallbackMessage = WM_TRAYICON
        self._nid.hIcon = user32.LoadIconW(None, _make_int_resource(IDI_APPLICATION))
        self._nid.szTip = self.tooltip

        if not shell32.Shell_NotifyIconW(NIM_ADD, byref(self._nid)):
            raise ctypes.WinError(ctypes.get_last_error())

        self._nid.uTimeoutOrVersion = 4
        shell32.Shell_NotifyIconW(NIM_SETVERSION, byref(self._nid))

    def _cleanup(self):
        if self._nid is not None:
            shell32.Shell_NotifyIconW(NIM_DELETE, byref(self._nid))
            self._nid = None

        hwnd = self._hwnd
        self._hwnd = None
        if hwnd and user32.IsWindow(hwnd):
            user32.DestroyWindow(hwnd)

    def _show_menu(self, hwnd):
        menu = user32.CreatePopupMenu()
        if not menu:
            return

        try:
            user32.AppendMenuW(menu, MF_STRING, ID_TRAY_RESTART, "Restart")
            user32.AppendMenuW(menu, MF_STRING, ID_TRAY_CLOSE, "Close")

            pt = POINT()
            user32.GetCursorPos(byref(pt))
            user32.SetForegroundWindow(hwnd)
            command = user32.TrackPopupMenu(
                menu,
                TPM_RIGHTBUTTON | TPM_RETURNCMD,
                pt.x,
                pt.y,
                0,
                hwnd,
                None,
            )
            if command == ID_TRAY_RESTART:
                self._actions.put("restart")
            elif command == ID_TRAY_CLOSE:
                self._actions.put("close")
        finally:
            user32.DestroyMenu(menu)
            user32.PostMessageW(hwnd, WM_NULL, 0, 0)

    def _window_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_TRAYICON:
            notification = _loword(lparam)
            if notification in (WM_RBUTTONUP, WM_CONTEXTMENU):
                self._show_menu(hwnd)
                return 0
        elif msg == WM_CLOSE:
            user32.DestroyWindow(hwnd)
            return 0
        elif msg == WM_DESTROY:
            if self._nid is not None:
                shell32.Shell_NotifyIconW(NIM_DELETE, byref(self._nid))
                self._nid = None
            user32.PostQuitMessage(0)
            return 0

        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)
