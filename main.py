import sys
import os
import socket
import ctypes

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtCore import QObject, Slot, Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush

from config_manager import ConfigManager
from hotkey_listener import HotkeyListener
from wallpaper_manager import get_current_wallpaper
from selector_window import SelectorWindow
from transition_overlay import TransitionOverlay


def create_tray_icon_pixmap():
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    painter.setBrush(QBrush(QColor("#8b8dff")))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(3, 3, 26, 26, 8, 8)

    painter.setBrush(QBrush(QColor(255, 255, 255, 230)))
    painter.drawRoundedRect(8, 9, 16, 11, 2, 2)
    painter.drawRect(14, 21, 4, 2)
    painter.drawRoundedRect(11, 23, 10, 2, 1, 1)
    painter.end()
    return pixmap


class WallvApplication(QObject):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.selector = SelectorWindow(self.config)
        self.selector.wallpaper_selected.connect(self.on_wallpaper_selected)
        self.active_transition = None
        self.hotkey_listener = None
        self.setup_tray()
        self.setup_hotkey()
        self.setup_startup_shortcut()

    def setup_startup_shortcut(self):
        import threading
        def worker():
            try:
                import pythoncom
                pythoncom.CoInitialize()
                try:
                    import win32com.client
                    startup_dir = os.path.join(os.environ["APPDATA"], r"Microsoft\Windows\Start Menu\Programs\Startup")
                    shortcut_path = os.path.join(startup_dir, "wallv.lnk")
                    
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    pythonw_path = os.path.join(base_dir, r".venv\Scripts\pythonw.exe")
                    main_py_path = os.path.join(base_dir, "main.py")
                    
                    shell = win32com.client.Dispatch("WScript.Shell")
                    shortcut = shell.CreateShortCut(shortcut_path)
                    shortcut.Targetpath = pythonw_path
                    shortcut.Arguments = f'"{main_py_path}"'
                    shortcut.WorkingDirectory = base_dir
                    shortcut.Description = "Starts wault wallpaper switcher on login"
                    shortcut.save()
                    print("[wallv] Startup shortcut verified successfully.")
                finally:
                    pythoncom.CoUninitialize()
            except Exception as e:
                print(f"[wallv] Could not setup startup shortcut: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(QIcon(create_tray_icon_pixmap()))
        self.tray.setToolTip(f"wault · {self.config.get_hotkey_string()}")

        menu = QMenu()

        show = menu.addAction(f"Open wault  ·  {self.config.get_hotkey_string()}")
        show.triggered.connect(self.show_selector)

        reload_action = menu.addAction("Reload wallpapers")
        reload_action.triggered.connect(self.selector.load_wallpapers)

        folder = menu.addAction("Change wallpaper folder…")
        folder.triggered.connect(self.selector.select_folder)

        menu.addSeparator()
        quit_action = menu.addAction("Quit wault")
        quit_action.triggered.connect(self.quit_app)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()

    def setup_hotkey(self):
        modifiers, vk = self.config.get_hotkey_params()
        self.hotkey_listener = HotkeyListener(modifiers, vk)
        self.hotkey_listener.hotkey_triggered.connect(self.toggle_selector)

        if not self.hotkey_listener._registered:
            self.tray.showMessage(
                "wault hotkey unavailable",
                f"{self.config.get_hotkey_string()} is already in use by Windows or another app.",
                QSystemTrayIcon.MessageIcon.Warning,
                5000,
            )

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_selector()

    @Slot()
    def toggle_selector(self):
        if self.selector.isVisible():
            self.selector.hide()
            return
        self.show_selector()

    @Slot()
    def show_selector(self):
        self.selector.load_wallpapers()
        self.selector.show()
        self.selector.raise_()
        self.selector.activateWindow()

        # Windows can refuse SetForegroundWindow when the caller was launched
        # from a background/global-hotkey context. Temporarily make the launcher
        # topmost, then restore its normal top-level state.
        try:
            user32 = ctypes.windll.user32
            hwnd = int(self.selector.winId())
            HWND_TOPMOST = -1
            HWND_NOTOPMOST = -2
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_SHOWWINDOW = 0x0040

            user32.SetWindowPos(
                hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
            )
            user32.SetForegroundWindow(hwnd)
            user32.SetWindowPos(
                hwnd, HWND_NOTOPMOST, 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
            )
        except Exception as exc:
            print(f"[wallv] could not force foreground: {exc}")

    @Slot(str, object)
    def on_wallpaper_selected(self, new_path, _start_rect=None):
        old_path = get_current_wallpaper()

        if old_path and os.path.normcase(os.path.normpath(old_path)) == os.path.normcase(
            os.path.normpath(new_path)
        ):
            return

        self.active_transition = TransitionOverlay(
            old_path,
            new_path,
            duration_ms=self.config.transition_ms,
        )

    def quit_app(self):
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        self.tray.hide()
        QApplication.quit()


def main():
    # Force Per-Monitor DPI Awareness on Windows to prevent blurry rendering/text
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    # Local TCP bind is a lightweight single-instance lock on Windows.
    lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        lock_socket.bind(("127.0.0.1", 56214))
    except OSError:
        print("[wallv] another instance is already running.")
        return 0

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Load and set all fonts in the fonts folder
    from PySide6.QtGui import QFontDatabase, QFont
    fonts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
    loaded_families = []
    
    if os.path.isdir(fonts_dir):
        for filename in os.listdir(fonts_dir):
            if filename.lower().endswith((".ttf", ".otf")):
                font_path = os.path.join(fonts_dir, filename)
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id != -1:
                    families = QFontDatabase.applicationFontFamilies(font_id)
                    if families:
                        loaded_families.extend(families)
                        print(f"[wallv] Registered font family: {families[0]}")

    # Prioritize Right Serif (or PP Right Serif), fallback to Inter, then system default
    chosen_family = "Inter"
    for fam in loaded_families:
        if "right serif" in fam.lower() or "rightserif" in fam.lower():
            chosen_family = fam
            break
            
    app.setFont(QFont(chosen_family, 9))

    wallv = WallvApplication()
    app.aboutToQuit.connect(lock_socket.close)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
