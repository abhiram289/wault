import os
import hashlib

from PIL import Image

from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QScrollArea, QFileDialog, QGraphicsDropShadowEffect, QPushButton,
    QSizePolicy, QGridLayout
)
from PySide6.QtCore import (
    Qt, Signal, Slot, QRunnable, QThreadPool, QObject, QSize, QEvent, QCoreApplication
)
from PySide6.QtGui import (
    QPixmap, QImage, QMouseEvent, QKeyEvent, QColor, QPainter, QPainterPath
)

from wallpaper_manager import get_current_wallpaper


class ThumbnailSignals(QObject):
    loaded = Signal(str, QImage)


class ThumbnailWorker(QRunnable):
    def __init__(self, filepath, cache_dir, size=(104, 58)):
        super().__init__()
        self.filepath = filepath
        self.cache_dir = cache_dir
        self.size = size
        self.signals = ThumbnailSignals()

    def run(self):
        try:
            mtime = os.path.getmtime(self.filepath)
            key = hashlib.md5(
                f"{os.path.normcase(self.filepath)}_{mtime}_{self.size}".encode()
            ).hexdigest()
            cache_path = os.path.join(self.cache_dir, f"{key}.png")

            if os.path.exists(cache_path):
                image = QImage(cache_path)
            else:
                with Image.open(self.filepath) as img:
                    img = img.convert("RGB")
                    img.thumbnail(self.size, Image.Resampling.LANCZOS)
                    canvas = Image.new("RGB", self.size, (20, 20, 24))
                    offset = (
                        (self.size[0] - img.width) // 2,
                        (self.size[1] - img.height) // 2,
                    )
                    canvas.paste(img, offset)
                    canvas.save(cache_path, "PNG", optimize=True)
                image = QImage(cache_path)

            if not image.isNull():
                self.signals.loaded.emit(self.filepath, image)
        except Exception as exc:
            print(f"[wallv] thumbnail error: {self.filepath}: {exc}")


class WallpaperRow(QFrame):
    clicked = Signal(str)

    def __init__(self, filepath, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.setObjectName("WallpaperRow")
        self.setFixedHeight(66)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 5, 10, 5)
        layout.setSpacing(11)

        self.thumbnail = QLabel()
        self.thumbnail.setFixedSize(104, 56)
        self.thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail.setText("…")
        self.thumbnail.setObjectName("RowThumb")
        layout.addWidget(self.thumbnail)

        text = QVBoxLayout()
        text.setContentsMargins(0, 2, 0, 0)
        text.setSpacing(1)

        self.title = QLabel(os.path.splitext(os.path.basename(filepath))[0])
        self.title.setObjectName("RowTitle")
        self.title.setToolTip(os.path.basename(filepath))
        text.addWidget(self.title)

        self.subtitle = QLabel(self._subtitle())
        self.subtitle.setObjectName("RowSubtitle")
        text.addWidget(self.subtitle)
        layout.addLayout(text, 1)

        self.active = QLabel("✓")
        self.active.setObjectName("CurrentPill")
        self.active.hide()
        layout.addWidget(self.active)

    def _subtitle(self):
        try:
            size = os.path.getsize(self.filepath) / 1024
            return f"{os.path.splitext(self.filepath)[1][1:].upper()}  ·  {size:.0f} KB"
        except OSError:
            return "WALLPAPER"

    def set_thumbnail(self, image):
        target_w, target_h = 208, 112
        rounded = QPixmap(target_w, target_h)
        rounded.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        path_clip = QPainterPath()
        path_clip.addRoundedRect(0, 0, target_w, target_h, 12, 12)
        painter.setClipPath(path_clip)
        
        painter.drawImage(0, 0, image)
        
        painter.setClipping(False)
        painter.setPen(QColor(255, 255, 255, 15))  # rgba(255, 255, 255, 0.06)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(0.5, 0.5, target_w - 1, target_h - 1, 12, 12)
        
        painter.end()
        rounded.setDevicePixelRatio(2.0)
        self.thumbnail.setPixmap(rounded)

    def set_selected(self, selected):
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def set_current(self, current):
        self.active.setVisible(current)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.filepath)
            event.accept()
            return
        super().mousePressEvent(event)


class WallpaperCard(QFrame):
    clicked = Signal(str)

    def __init__(self, filepath, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.setObjectName("WallpaperCard")
        self.setFixedSize(142, 108)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        self.thumbnail = QLabel()
        self.thumbnail.setFixedSize(130, 74)
        self.thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail.setText("…")
        self.thumbnail.setObjectName("CardThumb")
        layout.addWidget(self.thumbnail)

        # Place the current badge directly on top of the thumbnail
        self.active = QLabel("✓", self.thumbnail)
        self.active.setObjectName("CardCurrentBadge")
        self.active.setFixedSize(16, 16)
        self.active.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.active.move(130 - 16 - 3, 3)
        self.active.hide()

        self.title = QLabel(os.path.splitext(os.path.basename(filepath))[0])
        self.title.setObjectName("CardTitle")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setToolTip(os.path.basename(filepath))
        layout.addWidget(self.title)

    def set_thumbnail(self, image):
        target_w, target_h = 260, 148
        rounded = QPixmap(target_w, target_h)
        rounded.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        path_clip = QPainterPath()
        path_clip.addRoundedRect(0, 0, target_w, target_h, 12, 12)
        painter.setClipPath(path_clip)
        
        painter.drawImage(0, 0, image)
        
        painter.setClipping(False)
        painter.setPen(QColor(255, 255, 255, 15))  # rgba(255, 255, 255, 0.06)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(0.5, 0.5, target_w - 1, target_h - 1, 12, 12)
        
        painter.end()
        rounded.setDevicePixelRatio(2.0)
        self.thumbnail.setPixmap(rounded)

    def set_selected(self, selected):
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def set_current(self, current):
        self.active.setVisible(current)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.filepath)
            event.accept()
            return
        super().mousePressEvent(event)


class SelectorWindow(QWidget):
    wallpaper_selected = Signal(str, object)

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(max(2, min(6, self.thread_pool.maxThreadCount())))

        self.all_files = []
        self.visible_files = []
        self.rows = {}
        self.highlighted_index = -1
        self.is_picking_folder = False

        self.setWindowFlags(
            Qt.WindowType.Tool |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setFixedSize(860, 540)

        self.view_mode = "grid"
        self.results_layout = None

        self._build_ui()
        self.load_wallpapers()
        QCoreApplication.instance().installEventFilter(self)

    def _build_ui(self):
        self.setStyleSheet("""
            QWidget {
                color: #f5f5f7;
                font-family: "PPRightSerifMono-Regular-BF660e236c35bea", "PP Right Serif Mono", "Right Serif", "PP Right Serif", "Inter", "Segoe UI", sans-serif;
                font-size: 12px;
            }

            QFrame#Shell {
                background: rgba(18, 18, 21, 0.985);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 16px;
            }

            QLineEdit#Search {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 0 14px;
                color: #ffffff;
                font-size: 14px;
                height: 38px;
            }
            QLineEdit#Search:focus {
                border: 1px solid rgba(139, 141, 255, 0.50);
                background: rgba(255, 255, 255, 0.07);
            }

            QLabel#SearchIcon {
                color: rgba(255, 255, 255, 0.50);
                font-size: 16px;
            }
            QLabel#Shortcut {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 5px;
                color: rgba(255, 255, 255, 0.52);
                padding: 3px 6px;
                font-size: 10px;
                font-weight: 600;
            }

            QFrame#ResultsPane {
                background: rgba(255, 255, 255, 0.025);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }

            QFrame#WallpaperRow {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 9px;
            }
            QFrame#WallpaperRow[selected="true"] {
                background: rgba(122, 125, 255, 0.13);
                border: 1px solid rgba(145, 148, 255, 0.28);
            }
            QFrame#WallpaperRow:hover {
                background: rgba(255, 255, 255, 0.055);
            }

            QLabel#RowThumb {
                background: #151519;
                border: none;
                border-radius: 6px;
                color: rgba(255, 255, 255, 0.25);
                font-size: 14px;
            }
            QLabel#RowTitle {
                color: #f4f4f5;
                font-size: 12px;
                font-weight: 600;
            }
            QLabel#RowSubtitle {
                color: rgba(255, 255, 255, 0.34);
                font-size: 10px;
            }
            QLabel#CurrentPill {
                background: rgba(139, 141, 255, 0.14);
                border: 1px solid rgba(139, 141, 255, 0.30);
                border-radius: 9px;
                color: #8b8dff;
                padding: 1px 4px;
                font-size: 10px;
                font-weight: bold;
            }

            QFrame#ResultsWidget {
                background: transparent;
                border: none;
            }

            QFrame#WallpaperCard {
                background: rgba(255, 255, 255, 0.025);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
            }
            QFrame#WallpaperCard[selected="true"] {
                background: rgba(122, 125, 255, 0.13);
                border: 1px solid rgba(145, 148, 255, 0.28);
            }
            QFrame#WallpaperCard:hover {
                background: rgba(255, 255, 255, 0.055);
            }
            QLabel#CardThumb {
                background: #151519;
                border: none;
                border-radius: 6px;
                color: rgba(255, 255, 255, 0.25);
            }
            QLabel#CardTitle {
                color: #e4e4e7;
                font-size: 10px;
                font-weight: 500;
            }
            QLabel#CardCurrentBadge {
                background: #8b8dff;
                border: none;
                border-radius: 8px;
                color: #ffffff;
                font-size: 9px;
                font-weight: bold;
                margin-top: 3px;
                margin-right: 3px;
            }
            QPushButton#ViewToggle {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 5px;
                color: rgba(255, 255, 255, 0.60);
                padding: 2px 8px;
                font-size: 10px;
                font-weight: 600;
            }
            QPushButton#ViewToggle:hover {
                background: rgba(255, 255, 255, 0.10);
                color: #ffffff;
            }

            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                width: 4px;
                background: transparent;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.12);
                border-radius: 2px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.25);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none;
                border: none;
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
                border: none;
            }

            QFrame#PreviewPane {
                background: rgba(255, 255, 255, 0.025);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }
            QLabel#PreviewImage {
                background: #111114;
                border: none;
                border-radius: 8px;
            }
            QLabel#PreviewTitle {
                color: #ffffff;
                font-size: 13px;
                font-weight: 650;
            }
            QLabel#Muted {
                color: rgba(255, 255, 255, 0.38);
                font-size: 10px;
            }
            QPushButton#Ghost {
                background: rgba(255, 255, 255, 0.055);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                color: rgba(255, 255, 255, 0.80);
                padding: 7px 10px;
            }
            QPushButton#Ghost:hover {
                background: rgba(255, 255, 255, 0.10);
            }
            QPushButton#Apply {
                background: #f5f5f7;
                border: none;
                border-radius: 8px;
                color: #171719;
                font-weight: 700;
                padding: 8px 10px;
            }
            QPushButton#Apply:hover {
                background: #ffffff;
            }
            QLabel#KeyHint {
                background: rgba(255, 255, 255, 0.07);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 5px;
                padding: 2px 5px;
                color: rgba(255, 255, 255, 0.50);
                font-size: 9px;
                font-weight: 600;
            }
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(30, 30, 30, 30)

        self.shell = QFrame()
        self.shell.setObjectName("Shell")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(36)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 110))
        self.shell.setGraphicsEffect(shadow)
        outer.addWidget(self.shell)

        root = QVBoxLayout(self.shell)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        top = QHBoxLayout()
        top.setSpacing(10)

        icon = QLabel("⌕")
        icon.setObjectName("SearchIcon")
        icon.setFixedWidth(20)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top.addWidget(icon)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("Search")
        self.search_input.setPlaceholderText("Search wallpapers…")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.installEventFilter(self)
        top.addWidget(self.search_input, 1)

        self.shortcut = QLabel("ESC")
        self.shortcut.setObjectName("Shortcut")
        top.addWidget(self.shortcut)

        root.addLayout(top)

        body = QHBoxLayout()
        body.setSpacing(12)

        results_frame = QFrame()
        results_frame.setObjectName("ResultsPane")
        results_layout = QVBoxLayout(results_frame)
        results_layout.setContentsMargins(8, 8, 8, 8)
        results_layout.setSpacing(8)

        header = QHBoxLayout()
        self.count_label = QLabel("0 wallpapers")
        header.addWidget(self.count_label)
        header.addStretch()

        self.view_toggle = QPushButton("☰ List")
        self.view_toggle.setObjectName("ViewToggle")
        self.view_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.view_toggle.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.view_toggle.clicked.connect(self.toggle_view_mode)
        header.addWidget(self.view_toggle)

        hint = QLabel("↑ ↓ navigate   ·   ↵ apply")
        hint.setObjectName("Muted")
        header.addWidget(hint)
        results_layout.addLayout(header)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.results_widget = QFrame()
        self.results_widget.setObjectName("ResultsWidget")
        self.results_layout = QVBoxLayout(self.results_widget)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(4)
        self.results_layout.addStretch()
        self.scroll_area.setWidget(self.results_widget)
        results_layout.addWidget(self.scroll_area, 1)
        body.addWidget(results_frame, 1)

        self.preview = QFrame()
        self.preview.setObjectName("PreviewPane")
        self.preview.setFixedWidth(288)
        preview_layout = QVBoxLayout(self.preview)
        preview_layout.setContentsMargins(12, 12, 12, 12)
        preview_layout.setSpacing(10)

        self.preview_img = QLabel()
        self.preview_img.setObjectName("PreviewImage")
        self.preview_img.setFixedSize(264, 148)
        self.preview_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_img.setText("Select a wallpaper")
        preview_layout.addWidget(self.preview_img)

        self.preview_title = QLabel("Select a wallpaper")
        self.preview_title.setObjectName("PreviewTitle")
        self.preview_title.setWordWrap(True)
        preview_layout.addWidget(self.preview_title)

        self.preview_info = QLabel("Your current wallpaper")
        self.preview_info.setObjectName("Muted")
        self.preview_info.setWordWrap(True)
        preview_layout.addWidget(self.preview_info)

        preview_layout.addStretch()

        actions = QHBoxLayout()
        self.folder_button = QPushButton("Folder")
        self.folder_button.setObjectName("Ghost")
        self.folder_button.clicked.connect(self.select_folder)
        actions.addWidget(self.folder_button)

        self.random_button = QPushButton("Random")
        self.random_button.setObjectName("Ghost")
        self.random_button.clicked.connect(self.select_random)
        actions.addWidget(self.random_button)
        preview_layout.addLayout(actions)

        self.apply_button = QPushButton("Apply")
        self.apply_button.setObjectName("Apply")
        self.apply_button.clicked.connect(self.on_set_btn_clicked)
        preview_layout.addWidget(self.apply_button)

        body.addWidget(self.preview)
        root.addLayout(body, 1)

        footer = QHBoxLayout()
        self.status_label = QLabel("wallv")
        self.status_label.setObjectName("Muted")
        footer.addWidget(self.status_label)
        footer.addStretch()
        for key, text in [("↵", "apply"), ("esc", "close")]:
            k = QLabel(key)
            k.setObjectName("KeyHint")
            footer.addWidget(k)
            t = QLabel(text)
            t.setObjectName("Muted")
            footer.addWidget(t)
        root.addLayout(footer)

        self.search_input.textChanged.connect(self.on_search_changed)
        self.installEventFilter(self)

    def load_wallpapers(self):
        folder = self.config.wallpaper_dir
        self.all_files = []
        valid = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}

        if os.path.isdir(folder):
            try:
                for root, dirs, files in os.walk(folder):
                    dirs[:] = [d for d in dirs if not d.startswith(".")]
                    for filename in files:
                        if os.path.splitext(filename)[1].lower() in valid:
                            self.all_files.append(os.path.join(root, filename))
            except OSError as exc:
                print(f"[wallv] scan error: {exc}")

        self.all_files.sort(key=lambda p: os.path.basename(p).lower())
        self.filter_and_rebuild()

    def filter_and_rebuild(self):
        query = self.search_input.text().strip().lower()
        self.visible_files = [
            p for p in self.all_files
            if not query or query in os.path.basename(p).lower()
            or query in os.path.dirname(p).lower()
        ]

        # Take and delete the old scroll widget containing the old layout and widgets safely
        old_widget = self.scroll_area.takeWidget()
        if old_widget:
            old_widget.deleteLater()
        self.rows.clear()

        self.count_label.setText(
            f"{len(self.visible_files)} wallpaper" + ("" if len(self.visible_files) == 1 else "s")
        )

        self.results_widget = QFrame()
        self.results_widget.setObjectName("ResultsWidget")
        
        if self.view_mode == "list":
            self.results_layout = QVBoxLayout(self.results_widget)
            self.results_layout.setContentsMargins(0, 0, 0, 0)
            self.results_layout.setSpacing(4)
        else:
            self.results_layout = QGridLayout(self.results_widget)
            self.results_layout.setContentsMargins(0, 0, 0, 0)
            self.results_layout.setSpacing(8)

        if not self.visible_files:
            empty = QLabel("No wallpapers found\nTry a different search or choose another folder.")
            empty.setObjectName("Muted")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if self.view_mode == "list":
                self.results_layout.addWidget(empty, 1)
            else:
                self.results_layout.addWidget(empty, 0, 0, 1, 3, Qt.AlignmentFlag.AlignCenter)
            
            self.scroll_area.setWidget(self.results_widget)
            self.results_widget.show()
            self.highlighted_index = -1
            self.preview_title.setText("Nothing selected")
            self.preview_info.setText("No matching wallpapers")
            self.preview_img.clear()
            return

        for i, path in enumerate(self.visible_files):
            if self.view_mode == "list":
                row = WallpaperRow(path)
                row.clicked.connect(self.on_row_clicked)
                self.results_layout.addWidget(row)
                self.rows[path] = row
                thumb_size = (208, 112)
            else:
                card = WallpaperCard(path)
                card.clicked.connect(self.on_row_clicked)
                grid_row = i // 3
                grid_col = i % 3
                self.results_layout.addWidget(card, grid_row, grid_col)
                self.rows[path] = card
                thumb_size = (260, 148)

            worker = ThumbnailWorker(path, self.config.thumbnail_cache_dir, size=thumb_size)
            worker.signals.loaded.connect(self.on_thumbnail_loaded)
            self.thread_pool.start(worker)

        if self.view_mode == "list":
            self.results_layout.addStretch()
        else:
            self.results_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.scroll_area.setWidget(self.results_widget)
        self.results_widget.show()

        current = get_current_wallpaper()
        current_norm = os.path.normcase(os.path.normpath(current)) if current else None
        selected = next(
            (i for i, p in enumerate(self.visible_files)
             if current_norm and os.path.normcase(os.path.normpath(p)) == current_norm),
            0
        )
        self.highlight_index(selected)

    def toggle_view_mode(self):
        if self.view_mode == "list":
            self.view_mode = "grid"
            self.view_toggle.setText("☰ List")
        else:
            self.view_mode = "list"
            self.view_toggle.setText("⊞ Grid")
        self.filter_and_rebuild()

    @Slot(str, QImage)
    def on_thumbnail_loaded(self, filepath, image):
        row = self.rows.get(filepath)
        if row:
            row.set_thumbnail(image)

    def scroll_to_widget(self, widget):
        scrollbar = self.scroll_area.verticalScrollBar()
        if not scrollbar or not widget:
            return

        viewport_h = self.scroll_area.viewport().height()
        widget_y = widget.y()
        widget_h = widget.height()
        current_scroll = scrollbar.value()

        margin = 8
        target_scroll = current_scroll

        if widget_y < current_scroll + margin:
            target_scroll = max(0, widget_y - margin)
        elif widget_y + widget_h > current_scroll + viewport_h - margin:
            target_scroll = min(
                scrollbar.maximum(),
                widget_y + widget_h - viewport_h + margin
            )

        if target_scroll != current_scroll:
            from PySide6.QtCore import QPropertyAnimation, QEasingCurve
            if not hasattr(self, "_scroll_anim"):
                self._scroll_anim = QPropertyAnimation(scrollbar, b"value", self)
                self._scroll_anim.setDuration(120)
                self._scroll_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

            self._scroll_anim.stop()
            self._scroll_anim.setStartValue(current_scroll)
            self._scroll_anim.setEndValue(target_scroll)
            self._scroll_anim.start()

    def highlight_index(self, index):
        if not self.visible_files:
            self.highlighted_index = -1
            return

        index = index % len(self.visible_files)

        if 0 <= self.highlighted_index < len(self.visible_files):
            old = self.rows.get(self.visible_files[self.highlighted_index])
            if old:
                old.set_selected(False)

        self.highlighted_index = index
        path = self.visible_files[index]
        row = self.rows.get(path)
        if row:
            row.set_selected(True)
            self.results_layout.activate()
            self.scroll_to_widget(row)

        current = get_current_wallpaper()
        is_current = bool(
            current and os.path.normcase(os.path.normpath(current))
            == os.path.normcase(os.path.normpath(path))
        )
        if row:
            row.set_current(is_current)
        self._update_preview(path)

    def _update_preview(self, path):
        title = os.path.splitext(os.path.basename(path))[0]
        self.preview_title.setText(title)

        try:
            with Image.open(path) as img:
                w, h = img.size
                size = os.path.getsize(path) / (1024 * 1024)
                self.preview_info.setText(f"{w} × {h}  ·  {size:.2f} MB")
        except OSError:
            self.preview_info.setText("Image details unavailable")

        pixmap = QPixmap(path)
        if not pixmap.isNull():
            ratio = self.devicePixelRatioF()
            logical_w = self.preview_img.width()
            logical_h = self.preview_img.height()
            
            target_w = int(logical_w * ratio)
            target_h = int(logical_h * ratio)
            
            scaled = pixmap.scaled(
                target_w, target_h,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            
            x = (scaled.width() - target_w) // 2
            y = (scaled.height() - target_h) // 2
            cropped = scaled.copy(x, y, target_w, target_h)
            
            rounded = QPixmap(target_w, target_h)
            rounded.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            
            path_clip = QPainterPath()
            path_clip.addRoundedRect(0, 0, target_w, target_h, 8 * ratio, 8 * ratio)
            painter.setClipPath(path_clip)
            
            painter.drawPixmap(0, 0, cropped)
            
            # Disable clipping and draw a perfect, anti-aliased 1px border on the pixmap
            painter.setClipping(False)
            painter.setPen(QColor(255, 255, 255, 20))  # rgba(255, 255, 255, 0.08)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(0.5, 0.5, target_w - 1, target_h - 1, 8 * ratio, 8 * ratio)
            
            painter.end()
            rounded.setDevicePixelRatio(ratio)
            self.preview_img.setPixmap(rounded)

    def on_row_clicked(self, path):
        try:
            self.highlight_index(self.visible_files.index(path))
        except ValueError:
            return

    def on_set_btn_clicked(self):
        if 0 <= self.highlighted_index < len(self.visible_files):
            path = self.visible_files[self.highlighted_index]
            row = self.rows.get(path)
            self.hide()
            self.wallpaper_selected.emit(path, row.geometry() if row else None)

    def select_random(self):
        import random
        if self.visible_files:
            self.highlight_index(random.randrange(len(self.visible_files)))
            self.on_set_btn_clicked()

    def select_folder(self):
        self.is_picking_folder = True
        try:
            folder = QFileDialog.getExistingDirectory(
                self, "Select Wallpapers Folder", self.config.wallpaper_dir
            )
        finally:
            self.is_picking_folder = False

        if folder:
            self.config.wallpaper_dir = folder
            self.load_wallpapers()
            self.activateWindow()
            self.search_input.setFocus()

    def on_search_changed(self, _text):
        self.filter_and_rebuild()

    def eventFilter(self, obj, event):
        if not self.isVisible() or not self.isActiveWindow():
            return super().eventFilter(obj, event)

        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Escape:
                self.hide()
                return True
            if key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
                if self.visible_files:
                    delta = 3 if self.view_mode == "grid" else 1
                    if key == Qt.Key.Key_Up:
                        delta = -delta
                    self.highlight_index(self.highlighted_index + delta)
                return True
            if key in (Qt.Key.Key_Left, Qt.Key.Key_Right):
                if self.visible_files and self.view_mode == "grid":
                    delta = -1 if key == Qt.Key.Key_Left else 1
                    self.highlight_index(self.highlighted_index + delta)
                    return True
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.on_set_btn_clicked()
                return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            event.accept()
            return
        super().keyPressEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self.center_on_screen()
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self.search_input.setFocus()
        self.search_input.selectAll()

    def center_on_screen(self):
        screen = self.screen() or self.windowHandle().screen() if self.windowHandle() else None
        if screen is None:
            screen = self.windowHandle().screen() if self.windowHandle() else None
        if screen is None:
            from PySide6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen()

        if screen:
            geo = screen.availableGeometry()
            self.move(
                geo.x() + (geo.width() - self.width()) // 2,
                geo.y() + (geo.height() - self.height()) // 2,
            )

    def changeEvent(self, event):
        if event.type() == QEvent.Type.ActivationChange and not self.isActiveWindow():
            if not self.is_picking_folder:
                self.hide()
        super().changeEvent(event)
