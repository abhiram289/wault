import ctypes
import ctypes.wintypes

from PySide6.QtCore import QObject, Signal, QAbstractNativeEventFilter, QCoreApplication

WM_HOTKEY = 0x0312
MOD_NOREPEAT = 0x4000


class NativeHotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self, listener):
        super().__init__()
        self.listener = listener

    def nativeEventFilter(self, eventType, message):
        if eventType in (b"windows_generic_MSG", "windows_generic_MSG"):
            msg = ctypes.wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY and int(msg.wParam) == self.listener.hotkey_id:
                if self.listener.is_desktop_foreground():
                    self.listener.hotkey_triggered.emit()
                return True, 0
        return False, 0


class HotkeyListener(QObject):
    """Listens for global Windows RegisterHotKey events on the application thread."""

    hotkey_triggered = Signal()

    def __init__(self, modifiers, vk, parent=None):
        super().__init__(parent)
        self.modifiers = int(modifiers) | MOD_NOREPEAT
        self.vk = int(vk)
        self.hotkey_id = 0x574C  # "WL"
        self._registered = False

        self._register()
        
        self.native_filter = NativeHotkeyFilter(self)
        QCoreApplication.instance().installNativeEventFilter(self.native_filter)

    def _register(self):
        user32 = ctypes.windll.user32
        # Register thread-level hotkey (hWnd = None)
        if user32.RegisterHotKey(None, self.hotkey_id, self.modifiers, self.vk):
            self._registered = True
            print(f"[wallv] Thread-level global hotkey registered: modifiers=0x{self.modifiers:X}, vk=0x{self.vk:X}")
            return True

        error = ctypes.windll.kernel32.GetLastError()
        print(
            f"[wallv] FAILED to register thread-level global hotkey "
            f"(Windows error {error}). Another app may already own this shortcut."
        )
        return False

    def is_desktop_foreground(self):
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                return False

            allowed = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"}

            def get_class(h):
                buf = ctypes.create_unicode_buffer(256)
                ctypes.windll.user32.GetClassNameW(h, buf, 256)
                return buf.value

            cls = get_class(hwnd)
            if cls in allowed:
                return True

            parent = ctypes.windll.user32.GetParent(hwnd)
            if parent:
                if get_class(parent) in allowed:
                    return True
                gp = ctypes.windll.user32.GetParent(parent)
                if gp and get_class(gp) in allowed:
                    return True

            return False
        except Exception:
            return False

    def stop(self):
        self._unregister()
        QCoreApplication.instance().removeNativeEventFilter(self.native_filter)

    def _unregister(self):
        if self._registered:
            try:
                # Unregister thread-level hotkey (hWnd = None)
                ctypes.windll.user32.UnregisterHotKey(None, self.hotkey_id)
            finally:
                self._registered = False
