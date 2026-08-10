import os
import win32gui
import win32con
import win32api
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QVariantAnimation, QTimer, QRect
from PySide6.QtGui import QPainter, QPixmap, QGuiApplication, QImage, QRadialGradient, QColor, QBrush

class TransitionOverlay(QWidget):
    def __init__(self, old_path, new_path, duration_ms=500, start_rect=None, parent=None):
        super().__init__(parent)
        self.old_path = old_path
        self.new_path = new_path
        self.duration_ms = duration_ms
        self.alpha = 0.0
        
        # Configure frameless widget
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SubWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Load wallpapers (only the new wallpaper is needed for overlay)
        self.new_pixmap = QPixmap(new_path) if new_path and os.path.exists(new_path) else QPixmap()
        
        # Get virtual desktop geometry spanning all monitors
        self.virtual_geom = QGuiApplication.primaryScreen().virtualGeometry()
        self.setGeometry(self.virtual_geom)
        
        # Scale and crop pixmaps for each monitor screen to avoid runtime lag
        self.new_screen_pixmaps = {}
        self.precompute_screen_pixmaps()
        
        # Parent the widget behind desktop icons (WorkerW or Progman fallback)
        self.attach_to_workerw()
        
        # Show widget immediately
        self.show()
        
        # Setup simple cross-fade animation (0.0 to 1.0)
        self.anim = QVariantAnimation(self)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setDuration(self.duration_ms)
        self.anim.valueChanged.connect(self.on_animation_value_changed)
        self.anim.finished.connect(self.on_animation_finished)
        self.anim.start()

    def get_scaled_pixmap(self, pixmap, target_size):
        """Scale to cover the monitor, preserving aspect ratio, then center-crop."""
        if pixmap.isNull():
            return pixmap

        tw, th = target_size.width(), target_size.height()
        pw, ph = pixmap.width(), pixmap.height()
        scale = max(tw / pw, th / ph)

        scaled = pixmap.scaled(
            max(1, int(pw * scale)),
            max(1, int(ph * scale)),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )

        x = max(0, (scaled.width() - tw) // 2)
        y = max(0, (scaled.height() - th) // 2)
        return scaled.copy(x, y, tw, th)

    def precompute_screen_pixmaps(self):
        """
        Precompute screen-sized wallpapers and mask buffers for all active monitors.
        """
        screens = QGuiApplication.screens()
        self.mask_images = {}
        for screen in screens:
            size = screen.geometry().size()
            screen_name = screen.name()
            
            if not self.new_pixmap.isNull():
                self.new_screen_pixmaps[screen_name] = self.get_scaled_pixmap(self.new_pixmap, size)
            else:
                self.new_screen_pixmaps[screen_name] = QPixmap()
                
            self.mask_images[screen_name] = QImage(size, QImage.Format.Format_ARGB32_Premultiplied)

    def attach_to_workerw(self):
        """
        Windows hack to parent this widget behind desktop icons and open windows.
        Tries to locate the WorkerW window, falling back to Progman itself if WorkerW
        is unavailable in the session.
        """
        try:
            # 1. Get the Program Manager handle
            progman = win32gui.FindWindow("Progman", "Program Manager")
            
            # 2. Trigger WorkerW creation
            win32gui.SendMessageTimeout(
                progman, 
                0x052C, 
                0, 
                0, 
                win32con.SMTO_NORMAL, 
                1000
            )
            
            # 3. Search for WorkerW sibling window
            workerw = None
            def enum_callback(hwnd, extra):
                nonlocal workerw
                shell_dll = win32gui.FindWindowEx(hwnd, 0, "SHELLDLL_DefView", None)
                if shell_dll:
                    workerw = win32gui.FindWindowEx(0, hwnd, "WorkerW", None)
            
            win32gui.EnumWindows(enum_callback, None)
            
            win_id = int(self.winId())
            if workerw:
                win32gui.SetParent(win_id, workerw)
                print(f"Wallpaper overlay attached to WorkerW: {workerw}")
            elif progman:
                # Robust fallback: Parent to Progman directly if WorkerW sibling isn't active
                win32gui.SetParent(win_id, progman)
                print(f"Wallpaper overlay attached to Progman fallback: {progman}")
            else:
                print("WorkerW and Progman not found. Running as standard overlay.")
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
            widget_rect = screen_geom.translated(-virtual_origin)
            screen_name = screen.name()
            
            # Paint new wallpaper with radial mask (expanding from center)
            new_pm = self.new_screen_pixmaps.get(screen_name)
            mask_img = self.mask_images.get(screen_name)
            
            if new_pm and not new_pm.isNull() and mask_img:
                w = widget_rect.width()
                h = widget_rect.height()
                
                # Reset and clear the pre-allocated mask image
                mask_img.fill(Qt.GlobalColor.transparent)
                
                mask_painter = QPainter(mask_img)
                mask_painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                
                # Draw new wallpaper onto the mask buffer
                mask_painter.drawPixmap(0, 0, new_pm)
                
                # Apply composition mode to mask the image (keeps the destination but clips to mask)
                mask_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
                
                center = QRect(0, 0, w, h).center()
                max_radius = ((w / 2) ** 2 + (h / 2) ** 2) ** 0.5
                
                # Multiply by 1.15 to ensure the screen corners are fully covered before alpha reaches 1.0
                current_radius = max_radius * (self.alpha * 1.15)
                
                # Create radial mask gradient with a broad, soft feathered edge (40% width)
                radial_grad = QRadialGradient(center, max(1.0, current_radius))
                radial_grad.setColorAt(0.0, QColor(0, 0, 0, 255))
                radial_grad.setColorAt(max(0.0, 1.0 - 0.40), QColor(0, 0, 0, 255))
                radial_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
                
                mask_painter.setBrush(radial_grad)
                mask_painter.setPen(Qt.PenStyle.NoPen)
                mask_painter.drawRect(0, 0, w, h)
                
                mask_painter.end()
                
                # Draw the prepared mask image onto the screen overlay
                painter.drawImage(widget_rect.topLeft(), mask_img)

    def on_animation_finished(self):
        """
        Permanently set the actual OS wallpaper when the fade finishes.
        """
        from wallpaper_manager import set_wallpaper, set_lockscreen_wallpaper
        import threading
        
        # Run wallpaper application in a background thread to prevent GUI lockup
        def apply_wallpapers():
            set_wallpaper(self.new_path)
            set_lockscreen_wallpaper(self.new_path)
            
        threading.Thread(target=apply_wallpapers, daemon=True).start()
        
        # Introduce a small 150ms delay before hiding/destroying this overlay.
        # This gives Windows enough time to start updating the actual desktop background.
        QTimer.singleShot(150, self.cleanup_and_destroy)

    def cleanup_and_destroy(self):
        self.close()
        self.deleteLater()
