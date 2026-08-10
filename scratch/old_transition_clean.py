import os
import win32gui
import win32con
import win32api
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QVariantAnimation, QTimer
from PySide6.QtGui import QPainter, QPixmap, QGuiApplication

class TransitionOverlay(QWidget):
    def __init__(self, old_path, new_path, duration_ms=500, parent=None):
        super().__init__(parent)
        self.old_path = old_path
        self.new_path = new_path
        self.duration_ms = duration_ms
        self.alpha = 0.0
        
        # Configure frameless widget
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SubWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Load wallpapers
        self.old_pixmap = QPixmap(old_path) if old_path and os.path.exists(old_path) else QPixmap()
        self.new_pixmap = QPixmap(new_path) if new_path and os.path.exists(new_path) else QPixmap()
        
        # Get virtual desktop geometry spanning all monitors
        self.virtual_geom = QGuiApplication.primaryScreen().virtualGeometry()
        self.setGeometry(self.virtual_geom)
        
        # Scale and crop pixmaps for each monitor screen to avoid runtime lag
        self.old_screen_pixmaps = {}
        self.new_screen_pixmaps = {}
        self.precompute_screen_pixmaps()
        
        # Parent the widget behind desktop icons
        self.attach_to_workerw()
        
        # Show widget immediately
        self.show()
        
        # Setup cross-fade animation (0.0 to 1.0)
        self.anim = QVariantAnimation(self)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setDuration(self.duration_ms)
        self.anim.valueChanged.connect(self.on_animation_value_changed)
        self.anim.finished.connect(self.on_animation_finished)
        self.anim.start()

    def get_scaled_pixmap(self, pixmap, target_size):
        """
        Scales and crops the image to fill the screen while preserving aspect ratio.
        """
        if pixmap.isNull():
            return pixmap
            
        pw, ph = pixmap.width(), pixmap.height()
        tw, th = target_size.width(), target_size.height()
        
        # Scale to fill
        scale_x = tw / pw
        scale_y = th / ph
        scale = max(scale_x, scale_y)
        
        new_w = int(pw * scale)
        new_h = int(ph * scale)
        
        scaled = pixmap.scaled(
            new_w, new_h, 
            Qt.AspectRatioMode.IgnoreAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        
        # Crop from the center
        x_offset = (new_w - tw) // 2
        y_offset = (new_h - th) // 2
        
        return scaled.copy(x_offset, y_offset, tw, th)

    def precompute_screen_pixmaps(self):
        """
        Precompute screen-sized wallpapers for all active monitors.
        """
        screens = QGuiApplication.screens()
        for screen in screens:
            size = screen.geometry().size()
            screen_name = screen.name()
            
            if not self.old_pixmap.isNull():
                self.old_screen_pixmaps[screen_name] = self.get_scaled_pixmap(self.old_pixmap, size)
            else:
                self.old_screen_pixmaps[screen_name] = QPixmap()
                
            if not self.new_pixmap.isNull():
                self.new_screen_pixmaps[screen_name] = self.get_scaled_pixmap(self.new_pixmap, size)
            else:
                self.new_screen_pixmaps[screen_name] = QPixmap()

    def attach_to_workerw(self):
        """
        Windows hack to parent this widget to the WorkerW window.
        Places it behind desktop icons and open application windows.
        """
        try:
            # 1. Get the Program Manager handle
            progman = win32gui.FindWindow("Progman", "Program Manager")
            
            # 2. Send 0x052C message to spawn the WorkerW sibling window
            win32gui.SendMessageTimeout(
                progman, 
                0x052C, 
                0, 
                0, 
                win32con.SMTO_NORMAL, 
                1000
            )
            
            # 3. Find the WorkerW sibling spawned behind SHELLDLL_DefView
            workerw = None
            def enum_callback(hwnd, extra):
                nonlocal workerw
                shell_dll = win32gui.FindWindowEx(hwnd, 0, "SHELLDLL_DefView", None)
                if shell_dll:
                    # Sibling is the next WorkerW top-level window
                    workerw = win32gui.FindWindowEx(0, hwnd, "WorkerW", None)
            
            win32gui.EnumWindows(enum_callback, None)
            
            if workerw:
                win_id = int(self.winId())
                win32gui.SetParent(win_id, workerw)
                print(f"Wallpaper overlay attached to WorkerW: {workerw}")
            else:
                print("WorkerW sibling not found. Running as standalone top-most overlay.")
                self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.SubWindow)
        except Exception as e:
            print(f"Error attaching to WorkerW: {e}. Running as standard overlay.")
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.SubWindow)

    def on_animation_value_changed(self, value):
        self.alpha = value
        self.update()  # Request repaint

    def paintEvent(self, event):
        painter = QPainter(self)
        screens = QGuiApplication.screens()
        virtual_origin = self.virtual_geom.topLeft()
        
        for screen in screens:
            screen_geom = screen.geometry()
            # Map global screen rect to widget rect (relative to top-left of virtual desktop)
            widget_rect = screen_geom.translated(-virtual_origin)
            screen_name = screen.name()
            
            # 1. Paint old wallpaper base layer
            old_pm = self.old_screen_pixmaps.get(screen_name)
            if old_pm and not old_pm.isNull():
                painter.drawPixmap(widget_rect, old_pm)
            else:
                # Black fallback
                painter.fillRect(widget_rect, Qt.GlobalColor.black)
                
            # 2. Paint new wallpaper with opacity alpha
            new_pm = self.new_screen_pixmaps.get(screen_name)
            if new_pm and not new_pm.isNull():
                painter.setOpacity(self.alpha)
                painter.drawPixmap(widget_rect, new_pm)
                painter.setOpacity(1.0)  # Reset painter opacity

    def on_animation_finished(self):
        """
        Permanently set the actual OS wallpaper when the fade finishes.
        Delays closing the widget slightly to let the system redraw the background.
        """
        from wallpaper_manager import set_wallpaper
        
        # Permanently change system wallpaper
        set_wallpaper(self.new_path)
        
        # Introduce a small 100ms delay before hiding/destroying this overlay.
        # This gives Windows enough time to update the actual desktop background
        # underneath, avoiding a sudden flicker or white flash.
        QTimer.singleShot(100, self.cleanup_and_destroy)

    def cleanup_and_destroy(self):
        self.close()
        self.deleteLater()
