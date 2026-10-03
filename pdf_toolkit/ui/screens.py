from __future__ import annotations

from pathlib import Path

import fitz
from PySide6.QtCore import QMimeData, QPoint, Qt, Signal
from PySide6.QtGui import QDrag
from PySide6.QtGui import QFont, QIcon, QImage, QPixmap
from PIL import Image, ImageOps
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QButtonGroup,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QSpinBox,
    QProgressBar,
    QGraphicsBlurEffect,
    QPushButton,
    QScrollArea,
    QSplitter,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from pdf_toolkit.engine.compress import run as compress_run
from pdf_toolkit.engine.extract import run as extract_run
from pdf_toolkit.engine.merge import run as merge_run
from pdf_toolkit.engine.rotate import run as rotate_run
from pdf_toolkit.engine.protect import run as protect_run
from pdf_toolkit.engine.remove_pages import run as remove_pages_run
from pdf_toolkit.engine.reorder import run as reorder_run
from pdf_toolkit.engine.page_numbers import run as page_numbers_run
from pdf_toolkit.engine.form_fields import run as form_fields_run
from pdf_toolkit.engine.split import run as split_run
from pdf_toolkit.engine.image_tools import (
    compress_image,
    crop_to_content,
    images_to_pdf,
    pdf_to_images,
    remove_background,
    resize_image,
    transform_image,
)
from pdf_toolkit.workers.operation_service import OperationService
from pdf_toolkit.validation import IMAGE_EXTENSIONS, validate_inputs, validate_output_directory
from pdf_toolkit.preferences import Preferences

from .components import (
    AccentRule,
    CompactButton,
    NeoButton,
    OutputActions,
    SearchField,
    StatusStrip,
    ToolCard,
    label,
)
from .theme import THEME


TOOL_CATALOG = [
    {"id": "merge", "title": "Merge PDF", "subtitle": "Combine multiple files into one clean document.", "category": "Organize", "accent": THEME.red, "icon": "＋"},
    {"id": "split", "title": "Split PDF", "subtitle": "Break a document apart by pages or ranges.", "category": "Organize", "accent": THEME.yellow, "icon": "⌁"},
    {"id": "extract", "title": "Extract Pages", "subtitle": "Save one page or a selected range as a new PDF.", "category": "Organize", "accent": THEME.blue, "icon": "↳"},
    {"id": "remove-pages", "title": "Remove Pages", "subtitle": "Delete selected pages while keeping the rest.", "category": "Edit", "accent": THEME.red, "icon": "−"},
    {"id": "reorder", "title": "Reorder PDF", "subtitle": "Drag pages into a new order.", "category": "Edit", "accent": THEME.yellow, "icon": "↕"},
    {"id": "page-numbers", "title": "Page Numbers", "subtitle": "Add clean page numbers to every page.", "category": "Edit", "accent": THEME.blue, "icon": "#"},
    {"id": "form-fields", "title": "Inspect Form Fields", "subtitle": "List interactive fields before filling a PDF.", "category": "Forms", "accent": THEME.blue, "icon": "□"},
    {"id": "compress", "title": "Compress PDF", "subtitle": "Make heavy PDFs lighter, faster, and easier to share.", "category": "Optimize", "accent": THEME.green, "icon": "↓"},
    {"id": "rotate", "title": "Rotate PDF", "subtitle": "Correct page orientation in a single pass.", "category": "Edit", "accent": THEME.blue, "icon": "↻"},
    {"id": "protect", "title": "Protect PDF", "subtitle": "Add password protection and permissions.", "category": "Security", "accent": THEME.violet, "icon": "◇"},
    {"id": "images-to-pdf", "title": "Images to PDF", "subtitle": "Turn common image formats into a PDF.", "category": "Images", "accent": THEME.red, "icon": "▧", "kind": "image"},
    {"id": "pdf-to-images", "title": "PDF to Images", "subtitle": "Export PDF pages as high-quality PNG files.", "category": "Images", "accent": THEME.yellow, "icon": "▤", "kind": "pdf"},
    {"id": "compress-image", "title": "Compress Image", "subtitle": "Reduce image size while keeping it sharp.", "category": "Images", "accent": THEME.green, "icon": "↓", "kind": "image"},
    {"id": "resize-image", "title": "Resize Image", "subtitle": "Resize images for sharing, print, or upload.", "category": "Images", "accent": THEME.blue, "icon": "↔", "kind": "image"},
    {"id": "remove-background", "title": "Remove Background", "subtitle": "Make a clean transparent PNG from a simple backdrop.", "category": "Images", "accent": THEME.violet, "icon": "◌", "kind": "image"},
    {"id": "transform-image", "title": "Rotate & Flip", "subtitle": "Rotate, mirror, or turn images grayscale.", "category": "Images", "accent": THEME.red, "icon": "↻", "kind": "image"},
    {"id": "crop-image", "title": "Crop to Content", "subtitle": "Trim transparent or empty space around an image.", "category": "Images", "accent": THEME.yellow, "icon": "□", "kind": "image"},
]


class PageThumbnailButton(QPushButton):
    selection_requested = Signal(int, int)

    def __init__(self, page_index: int, pixmap: QPixmap, draggable: bool = False):
        super().__init__()
        self.page_index = page_index
        self.draggable = draggable
        self._drag_start: QPoint | None = None
        self.selection_modifiers = Qt.NoModifier
        self.setObjectName("pdf-page-thumbnail")
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setIcon(QIcon(pixmap))
        self.setIconSize(pixmap.size())
        self.setFixedSize(pixmap.width() + 16, pixmap.height() + 38)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start = event.position().toPoint()
            self.selection_modifiers = event.modifiers()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton and self._drag_start is not None:
            self.selection_requested.emit(
                self.page_index, self.selection_modifiers.value
            )
        self._drag_start = None

    def mouseMoveEvent(self, event):
        if (
            self.draggable
            and
            self._drag_start is not None
            and (event.position().toPoint() - self._drag_start).manhattanLength()
            >= 8
        ):
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(str(self.page_index))
            drag.setMimeData(mime)
            drag.setPixmap(self.icon().pixmap(self.iconSize()))
            drag.exec(Qt.MoveAction)
            self._drag_start = None
            return
        super().mouseMoveEvent(event)


class PageThumbnailGrid(QWidget):
    reorder_requested = Signal(int, int)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self._drop_target: QPushButton | None = None

    def _set_drop_target(self, button: QPushButton | None):
        if self._drop_target is button:
            return
        if self._drop_target is not None:
            self._drop_target.setProperty("dropTarget", False)
            self._drop_target.style().unpolish(self._drop_target)
            self._drop_target.style().polish(self._drop_target)
        self._drop_target = button
        if button is not None:
            button.setProperty("dropTarget", True)
            button.style().unpolish(button)
            button.style().polish(button)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        target = self._target_button(event.position().toPoint())
        self._set_drop_target(target)
        if target is not None:
            event.acceptProposedAction()

    def dropEvent(self, event):
        if not event.mimeData().hasText():
            return
        try:
            source = int(event.mimeData().text())
        except ValueError:
            return
        target_button = self._target_button(event.position().toPoint())
        if target_button is None:
            return
        self.reorder_requested.emit(source, target_button.page_index)
        self._set_drop_target(None)
        event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._set_drop_target(None)
        event.accept()

    def _target_button(self, position: QPoint) -> QPushButton | None:
        buttons = self.findChildren(QPushButton, "pdf-page-thumbnail")
        if not buttons:
            return None
        return min(
            buttons,
            key=lambda button: (
                button.mapTo(self, button.rect().center()) - position
            ).manhattanLength(),
        )


class ToolScreen(QWidget):
    def __init__(self, tool: dict):
        super().__init__()
        self.tool = tool
        self._paths: list[Path] = []
        self._output_dir: Path | None = None
        self._preferences = Preferences()
        saved_output = self._preferences.get("last_output_dir")
        if isinstance(saved_output, str) and saved_output:
            candidate = Path(saved_output).expanduser()
            if candidate.exists() and candidate.is_dir():
                self._output_dir = candidate
        self._operation_service = OperationService(self)
        self._operation_service.progress.connect(self._handle_progress)
        self._operation_service.completed.connect(self._handle_result)
        self._operation_service.failed.connect(self._handle_error_with_diagnostic)
        self._operation_service.state_changed.connect(self._handle_operation_state)
        self._diagnostic_id: str | None = None
        self.setStyleSheet(f"background: {THEME.bg};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setAlignment(Qt.AlignTop)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        content = QWidget()
        self._content_widget = content
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(56, 56, 56, 64)
        content_layout.setSpacing(32)
        scroll.setWidget(content)
        layout.addWidget(scroll)

        layout = content_layout

        top = QHBoxLayout()
        title_column = QVBoxLayout()
        title_column.setSpacing(9)
        title_column.addWidget(label(tool["category"].upper(), 10, tool["accent"], QFont.DemiBold))
        title_column.addWidget(label(tool["title"].upper(), 34, THEME.text, QFont.Bold))
        title_column.addWidget(label(tool["subtitle"], 14, THEME.muted))
        top.addLayout(title_column)
        top.addStretch()
        self.back_button = NeoButton("Back", style="secondary")
        top.addWidget(self.back_button, alignment=Qt.AlignTop)
        layout.addLayout(top)
        layout.addWidget(AccentRule(tool["accent"]))

        controls = QVBoxLayout()
        controls.setSpacing(18)
        preview_column = QVBoxLayout()
        preview_column.setSpacing(12)
        controls_panel = QWidget()
        controls_panel.setLayout(controls)
        controls_panel.setMinimumSize(0, 0)
        controls_panel.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        preview_panel = QWidget()
        preview_panel.setLayout(preview_column)
        preview_panel.setMinimumSize(0, 0)
        preview_panel.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        columns = QSplitter(Qt.Horizontal)
        columns.setChildrenCollapsible(False)
        columns.setHandleWidth(10)
        columns.addWidget(controls_panel)
        columns.addWidget(preview_panel)
        columns.setStretchFactor(0, 5)
        columns.setStretchFactor(1, 7)
        columns.setSizes([500, 700])
        columns.splitterMoved.connect(self._handle_splitter_resize)
        columns.setStyleSheet(
            f"QSplitter::handle {{ background: {THEME.line_soft}; margin: 8px 0; }}"
            f"QSplitter::handle:hover {{ background: {THEME.blue}; }}"
        )
        layout.addWidget(columns, 1)

        self.file_field = QLabel("NO FILES SELECTED")
        self.file_field.setMinimumHeight(58)
        self.file_field.setStyleSheet(
            f"background: {THEME.panel}; border: 1px solid {THEME.line_soft}; padding: 0 18px; color: {THEME.muted};"
        )
        controls.addWidget(self.file_field)
        preview_header_widget = QWidget()
        preview_header = QHBoxLayout(preview_header_widget)
        preview_header.setContentsMargins(0, 0, 0, 0)
        preview_header.addWidget(label("PREVIEW", 10, THEME.muted, QFont.DemiBold))
        preview_header.addStretch()
        preview_column.addWidget(preview_header_widget)

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(300)
        self.preview_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.preview_label.setStyleSheet(
            f"background: {THEME.panel}; border: 1px solid {THEME.line_soft}; color: {THEME.muted}; padding: 20px;"
        )
        self.preview_label.setText(
            "IMAGE PREVIEW WILL APPEAR HERE"
            if self.tool.get("kind") == "image"
            else "PDF PREVIEW WILL APPEAR HERE"
        )
        preview_column.addWidget(self.preview_label, 1)
        self._preview_pixmap = QPixmap()
        self._thumbnail_mode = self.tool.get("id") in {
            "extract",
            "remove-pages",
            "split",
            "page-numbers",
            "rotate",
            "reorder",
        }
        self.thumbnail_scroll = QScrollArea()
        self.thumbnail_scroll.setWidgetResizable(True)
        self.thumbnail_scroll.setFrameShape(QScrollArea.NoFrame)
        self.thumbnail_scroll.setStyleSheet(
            f"QScrollArea {{ background: {THEME.panel}; border: 1px solid {THEME.line_soft}; }}"
        )
        self.thumbnail_container = PageThumbnailGrid()
        self.thumbnail_container.reorder_requested.connect(self._reorder_pages)
        self.thumbnail_grid = QGridLayout(self.thumbnail_container)
        self.thumbnail_grid.setContentsMargins(16, 16, 16, 16)
        self.thumbnail_grid.setSpacing(14)
        self.thumbnail_scroll.setWidget(self.thumbnail_container)
        self.thumbnail_scroll.setMinimumHeight(300)
        self.thumbnail_scroll.setVisible(self._thumbnail_mode)
        preview_column.addWidget(self.thumbnail_scroll, 1)
        if self.tool.get("id") == "reorder":
            self.reorder_hint = label(
                "DRAG A PAGE CARD TO CHANGE ITS ORDER",
                10,
                THEME.muted,
                QFont.DemiBold,
            )
            self.reorder_hint.setAlignment(Qt.AlignCenter)
            preview_column.addWidget(self.reorder_hint)
        self.preview_label.setVisible(not self._thumbnail_mode)
        self._preview_page = 0
        self._preview_page_count = 0
        self._selected_pages: set[int] = set()
        self._page_order: list[int] = []
        self.preview_controls = QWidget()
        preview_controls_layout = QHBoxLayout(self.preview_controls)
        preview_controls_layout.setContentsMargins(0, 0, 0, 0)
        self.preview_previous = NeoButton("Previous", style="secondary")
        self.preview_previous.clicked.connect(self._previous_preview_page)
        self.preview_page_label = label("PAGE — OF —", 10, THEME.muted, QFont.DemiBold)
        self.preview_page_label.setAlignment(Qt.AlignCenter)
        self.preview_next = NeoButton("Next", style="secondary")
        self.preview_next.clicked.connect(self._next_preview_page)
        preview_controls_layout.addStretch()
        preview_controls_layout.addWidget(self.preview_previous)
        preview_controls_layout.addWidget(self.preview_page_label)
        preview_controls_layout.addWidget(self.preview_next)
        self.page_fullscreen_button = CompactButton("⛶")
        self.page_fullscreen_button.setFixedSize(34, 34)
        self.page_fullscreen_button.setToolTip("Open current page fullscreen")
        self.page_fullscreen_button.clicked.connect(self._open_preview_fullscreen)
        self.page_fullscreen_button.setVisible(self.tool.get("kind") != "image")
        preview_controls_layout.addWidget(self.page_fullscreen_button)
        preview_controls_layout.addStretch()
        self.preview_controls.setVisible(
            self.tool.get("kind") != "image" and not self._thumbnail_mode
        )
        preview_column.addWidget(self.preview_controls)

        self.options_panel = QWidget()
        self.options_layout = QFormLayout(self.options_panel)
        self.options_layout.setContentsMargins(0, 0, 0, 0)
        self.options_layout.setHorizontalSpacing(18)
        self.options_layout.setVerticalSpacing(12)
        self.options_panel.setStyleSheet(
            f"""
            QComboBox, QSpinBox {{
                min-height: 38px;
                min-width: 180px;
                background: {THEME.panel};
                border: 1px solid {THEME.line_soft};
                color: {THEME.text};
                padding: 0 10px;
            }}
            """
        )
        self._option_widgets: dict[str, QWidget] = {}
        self._build_options()
        controls.addWidget(self.options_panel)

        destination_row = QHBoxLayout()
        self.destination_field = QLabel("SAME FOLDER AS SOURCE")
        self.destination_field.setMinimumHeight(48)
        self.destination_field.setStyleSheet(
            f"background: {THEME.panel}; border: 1px solid {THEME.line_soft}; padding: 0 16px; color: {THEME.muted};"
        )
        if self._output_dir is not None:
            self.destination_field.setText(f"SAVE TO  /  {self._output_dir}")
            self.destination_field.setToolTip(str(self._output_dir))
        destination_button = NeoButton("Save to folder", style="secondary")
        destination_button.setMinimumWidth(148)
        destination_button.clicked.connect(self.choose_destination)
        destination_row.addWidget(self.destination_field, 1)
        destination_row.addWidget(destination_button)
        controls.addLayout(destination_row)

        actions = QHBoxLayout()
        browse = NeoButton("Choose files", style="secondary")
        browse.clicked.connect(self.browse_files)
        run_button = NeoButton("Run tool", accent=tool["accent"], style="accent")
        run_button.clicked.connect(self.run_action)
        self.cancel_button = NeoButton("Cancel", style="secondary")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_action)
        actions.addWidget(browse)
        actions.addWidget(run_button)
        actions.addWidget(self.cancel_button)
        actions.addStretch()
        controls.addLayout(actions)
        controls.addStretch(1)

        self.result_list = QListWidget()
        self.result_list.setStyleSheet(
            f"QListWidget {{ background: {THEME.panel}; border: 1px solid {THEME.line_soft}; color: {THEME.text}; padding: 8px; }}"
            f"QListWidget::item {{ padding: 12px; border-bottom: 1px solid {THEME.line_soft}; }}"
        )
        self.result_list.setVisible(False)
        self.output_actions_panel = QWidget()
        self.output_actions_layout = QVBoxLayout(self.output_actions_panel)
        self.output_actions_layout.setContentsMargins(0, 0, 0, 0)
        self.output_actions_layout.setSpacing(8)
        self.output_actions_panel.setVisible(False)
        preview_column.addWidget(self.output_actions_panel)
        self.output_summary = label("", 11, THEME.muted)
        self.output_summary.setWordWrap(True)
        self.output_summary.setVisible(False)
        preview_column.addWidget(self.output_summary)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(5)
        self.progress_bar.setStyleSheet(
            f"""
            QProgressBar {{
                background: {THEME.line_soft};
                border: none;
            }}
            QProgressBar::chunk {{
                background: {tool["accent"]};
            }}
            """
        )
        self.progress_status = label("READY", 10, THEME.dim, QFont.DemiBold)
        controls.addWidget(self.progress_bar)
        controls.addWidget(self.progress_status)
        controls.addWidget(StatusStrip())
        self._column_splitter = columns

    @property
    def operation_service(self) -> OperationService:
        return self._operation_service

    def browse_files(self):
        image_patterns = " ".join(f"*{extension}" for extension in sorted(IMAGE_EXTENSIONS))
        file_filter = (
            f"Image Files ({image_patterns})"
            if self.tool.get("kind") == "image"
            else "PDF Files (*.pdf)"
        )
        if self.tool.get("id") == "pdf-to-images":
            file_filter = "PDF Files (*.pdf)"
        paths, _ = QFileDialog.getOpenFileNames(self, "Choose files", str(Path.home()), file_filter)
        if paths:
            self._paths = [Path(path) for path in paths]
            self.file_field.setText("  •  ".join(path.name.upper() for path in self._paths))
            self._preview_page = 0
            self._selected_pages.clear()
            self._page_order.clear()
            pages_widget = self._option_widgets.get("pages")
            if isinstance(pages_widget, QLineEdit):
                pages_widget.clear()
            self._update_preview()

    def _update_preview(self):
        if not self._paths:
            return
        if self.tool.get("kind") == "image":
            self._update_image_preview()
            return
        if self._thumbnail_mode:
            self._update_page_thumbnails()
            return
        source = self._paths[0]
        try:
            document = fitz.open(source)
            try:
                if document.needs_pass:
                    self.preview_label.setPixmap(QPixmap())
                    self.preview_label.setText("PASSWORD-PROTECTED PDF  ·  PREVIEW UNAVAILABLE")
                    self._set_preview_navigation(0, 0)
                    return
                if not document.page_count:
                    self.preview_label.setText("PDF HAS NO PAGES")
                    self._set_preview_navigation(0, 0)
                    return
                self._preview_page_count = document.page_count
                self._preview_page = max(0, min(self._preview_page, document.page_count - 1))
                page = document[self._preview_page]
                preview = self._render_pdf_pixmap(page, 0.8).scaled(
                    max(420, self.preview_label.width() - 40),
                    max(360, self.preview_label.height() - 40),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                self.preview_label.setPixmap(preview)
                self.preview_label.setToolTip(
                    f"Page {self._preview_page + 1} of {document.page_count}"
                )
                self._set_preview_navigation(self._preview_page + 1, document.page_count)
            finally:
                document.close()
        except (OSError, ValueError, RuntimeError) as exc:
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText(f"PREVIEW UNAVAILABLE  ·  {type(exc).__name__.upper()}")
            self._set_preview_navigation(0, 0)

    def _update_page_thumbnails(self):
        source = self._paths[0]
        self._clear_thumbnails()
        try:
            document = fitz.open(source)
            try:
                if document.needs_pass:
                    self._add_thumbnail_message("PASSWORD-PROTECTED PDF  ·  PREVIEW UNAVAILABLE")
                    return
                if not document.page_count:
                    self._add_thumbnail_message("PDF HAS NO PAGES")
                    return
                self._preview_page_count = document.page_count
                if self.tool.get("id") == "reorder" and len(self._page_order) != document.page_count:
                    self._page_order = list(range(document.page_count))
                page_order = (
                    self._page_order if self.tool.get("id") == "reorder" else range(document.page_count)
                )
                for index, page_number in enumerate(page_order):
                    page = document[page_number]
                    pixmap = self._render_pdf_pixmap(page, 0.35)
                    thumbnail = PageThumbnailButton(
                        page_number,
                        pixmap,
                        draggable=self.tool.get("id") == "reorder",
                    )
                    thumbnail.setCursor(Qt.PointingHandCursor)
                    thumbnail.setFocusPolicy(Qt.StrongFocus)
                    thumbnail.setAccessibleName(f"Page {page_number + 1} preview")
                    thumbnail.setAccessibleDescription(
                        (
                            f"Drag page {page_number + 1} to reorder it"
                            if self.tool.get("id") == "reorder"
                            else f"Select page {page_number + 1} for this operation"
                        )
                    )
                    thumbnail.setCheckable(self.tool.get("id") in {"extract", "remove-pages"})
                    thumbnail.setChecked(page_number in self._selected_pages)
                    thumbnail.setToolTip(f"Page {page_number + 1}")
                    thumbnail.selection_requested.connect(self._select_thumbnail_page)
                    page_label = QLabel(f"PAGE {page_number + 1}")
                    page_label.setAlignment(Qt.AlignCenter)
                    page_label.setStyleSheet(f"color: {THEME.muted};")
                    cell = QWidget()
                    cell_layout = QVBoxLayout(cell)
                    cell_layout.setContentsMargins(0, 0, 0, 0)
                    cell_layout.setSpacing(4)
                    cell_layout.addWidget(thumbnail)
                    page_toolbar = QHBoxLayout()
                    page_toolbar.setContentsMargins(0, 0, 0, 0)
                    page_toolbar.addWidget(page_label, 1)
                    cell_layout.addLayout(page_toolbar)
                    if self._thumbnail_mode:
                        fullscreen_button = CompactButton("⛶")
                        fullscreen_button.setFixedSize(30, 30)
                        fullscreen_button.setToolTip(
                            f"Open page {page_number + 1} fullscreen"
                        )
                        fullscreen_button.setAccessibleName(
                            f"Open page {page_number + 1} fullscreen"
                        )
                        fullscreen_button.clicked.connect(
                            lambda _checked=False, page_index=page_number: (
                                self._open_page_fullscreen(page_index)
                            )
                        )
                        page_toolbar.addWidget(fullscreen_button)
                    columns = max(1, self.thumbnail_scroll.viewport().width() // 210)
                    self.thumbnail_grid.addWidget(cell, index // columns, index % columns)
            finally:
                document.close()
        except (OSError, ValueError, RuntimeError) as exc:
            self._add_thumbnail_message(
                f"PREVIEW UNAVAILABLE  ·  {type(exc).__name__.upper()}"
            )

    def _handle_splitter_resize(self, _position: int, _index: int):
        if self._thumbnail_mode:
            self._reflow_thumbnails()
        elif self._paths and self.tool.get("kind") != "image":
            self._update_preview()

    def _reflow_thumbnails(self):
        if not self.thumbnail_grid.count():
            return
        columns = max(1, self.thumbnail_scroll.viewport().width() // 210)
        widgets = [
            self.thumbnail_grid.itemAt(index).widget()
            for index in range(self.thumbnail_grid.count())
        ]
        for index, widget in enumerate(widgets):
            if widget is not None:
                self.thumbnail_grid.addWidget(widget, index // columns, index % columns)

    def _render_pdf_pixmap(self, page, scale: float) -> QPixmap:
        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        image = QImage(
            pixmap.samples,
            pixmap.width,
            pixmap.height,
            pixmap.stride,
            QImage.Format_RGB888,
        ).copy()
        return QPixmap.fromImage(image)

    def _clear_thumbnails(self):
        while self.thumbnail_grid.count():
            item = self.thumbnail_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _add_thumbnail_message(self, text: str):
        message = QLabel(text)
        message.setAlignment(Qt.AlignCenter)
        message.setStyleSheet(f"color: {THEME.muted}; padding: 40px;")
        self.thumbnail_grid.addWidget(message, 0, 0)

    def _select_thumbnail_page(self, page: int, modifiers: int = 0):
        if self.tool.get("id") in {"extract", "remove-pages"}:
            multi_select = bool(
                modifiers
                & (Qt.ControlModifier.value | Qt.MetaModifier.value)
            )
            if multi_select:
                if page in self._selected_pages:
                    self._selected_pages.remove(page)
                else:
                    self._selected_pages.add(page)
            else:
                self._selected_pages = {page}
            for thumbnail in self.thumbnail_container.findChildren(
                PageThumbnailButton, "pdf-page-thumbnail"
            ):
                thumbnail.setChecked(thumbnail.page_index in self._selected_pages)
            self._sync_selected_pages()
            return
        self._preview_page = page

    def _open_page_fullscreen(self, page: int):
        self._preview_page = page
        self._open_preview_fullscreen()

    def _reorder_pages(self, source_page: int, target_page: int):
        if self.tool.get("id") != "reorder":
            return
        source_position = self._page_order.index(source_page)
        target_position = self._page_order.index(target_page)
        if source_position == target_position:
            return
        page = self._page_order.pop(source_position)
        self._page_order.insert(target_position, page)
        self._update_page_thumbnails()

    def _sync_selected_pages(self):
        pages = sorted(self._selected_pages)
        page_text: list[str] = []
        start = previous = None
        for page in pages:
            if start is None:
                start = previous = page
            elif page == previous + 1:
                previous = page
            else:
                page_text.append(str(start + 1) if start == previous else f"{start + 1}-{previous + 1}")
                start = previous = page
        if start is not None and previous is not None:
            page_text.append(str(start + 1) if start == previous else f"{start + 1}-{previous + 1}")
        pages_widget = self._option_widgets.get("pages")
        if isinstance(pages_widget, QLineEdit):
            pages_widget.setText(", ".join(page_text))

    def _open_preview_fullscreen(self):
        if not self._paths or self.tool.get("kind") == "image":
            return
        try:
            document = fitz.open(self._paths[0])
            try:
                if document.needs_pass or not document.page_count:
                    return
                page_index = max(0, min(self._preview_page, document.page_count - 1))
                pixmap = self._render_pdf_pixmap(document[page_index], 1.8)
            finally:
                document.close()
        except (OSError, ValueError, RuntimeError):
            return
        if hasattr(self, "_preview_overlay") and self._preview_overlay is not None:
            return
        app_root = self.window().centralWidget()
        if app_root is None:
            return
        overlay = QWidget(app_root)
        overlay.setObjectName("preview-overlay")
        overlay.setGeometry(app_root.rect())
        overlay.setStyleSheet(
            "QWidget#preview-overlay { background: rgba(0, 0, 0, 220); }"
        )
        overlay_layout = QVBoxLayout(overlay)
        overlay_layout.setContentsMargins(48, 36, 48, 48)
        overlay_layout.setSpacing(14)
        toolbar = QHBoxLayout()
        title = label(
            f"{self.tool['title'].upper()}  ·  PAGE {page_index + 1}",
            11,
            THEME.muted,
            QFont.DemiBold,
        )
        toolbar.addWidget(title)
        toolbar.addStretch()
        close_button = CompactButton("CLOSE  ×")
        close_button.setObjectName("preview-overlay-close")
        close_button.setFixedHeight(36)
        close_button.clicked.connect(self._close_preview_fullscreen)
        toolbar.addWidget(close_button)
        overlay_layout.addLayout(toolbar)
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignCenter)
        image_label.setPixmap(pixmap)
        image_label.setScaledContents(False)
        image_scroll = QScrollArea()
        image_scroll.setWidgetResizable(True)
        image_scroll.setAlignment(Qt.AlignCenter)
        image_scroll.setFrameShape(QScrollArea.NoFrame)
        image_scroll.setWidget(image_label)
        overlay_layout.addWidget(image_scroll, 1)
        blur = QGraphicsBlurEffect(overlay)
        blur.setBlurRadius(8)
        self._content_widget.setGraphicsEffect(blur)
        self._preview_overlay = overlay
        overlay.show()
        overlay.raise_()
        close_button.setFocus()

    def _close_preview_fullscreen(self):
        overlay = getattr(self, "_preview_overlay", None)
        if overlay is not None:
            overlay.deleteLater()
            self._preview_overlay = None
        self._content_widget.setGraphicsEffect(None)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.tool.get("kind") == "image":
            self._render_image_preview()
        elif self._thumbnail_mode:
            self._reflow_thumbnails()
        elif self._paths:
            self._update_preview()
        overlay = getattr(self, "_preview_overlay", None)
        if overlay is not None:
            app_root = self.window().centralWidget()
            if app_root is not None:
                overlay.setGeometry(app_root.rect())

    def _update_image_preview(self):
        source = self._paths[0]
        try:
            with Image.open(source) as image:
                preview_image = ImageOps.exif_transpose(image)
                preview_image.thumbnail((2400, 2400), Image.Resampling.LANCZOS)
                if "A" in preview_image.getbands() or preview_image.mode == "P":
                    preview_image = preview_image.convert("RGBA")
                    image_format = QImage.Format_RGBA8888
                    bytes_per_pixel = 4
                else:
                    preview_image = preview_image.convert("RGB")
                    image_format = QImage.Format_RGB888
                    bytes_per_pixel = 3
                image_data = preview_image.tobytes()
                image = QImage(
                    image_data,
                    preview_image.width,
                    preview_image.height,
                    preview_image.width * bytes_per_pixel,
                    image_format,
                ).copy()
            self._preview_pixmap = QPixmap.fromImage(image)
            self._render_image_preview()
            self.preview_label.setToolTip(
                f"{source.name} · {image.width()} × {image.height()}"
            )
        except (OSError, ValueError, RuntimeError) as exc:
            self._preview_pixmap = QPixmap()
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText(f"PREVIEW UNAVAILABLE  · {type(exc).__name__.upper()}")

    def _render_image_preview(self):
        if self._preview_pixmap.isNull():
            return
        self.preview_label.setPixmap(
            self._preview_pixmap.scaled(
                max(1, self.preview_label.width() - 40),
                max(1, self.preview_label.height() - 40),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

    def _set_preview_navigation(self, page: int, page_count: int):
        self._preview_page_count = page_count
        self.preview_page_label.setText(
            f"PAGE {page} OF {page_count}" if page_count else "PAGE — OF —"
        )
        self.preview_previous.setEnabled(page > 1)
        self.preview_next.setEnabled(page > 0 and page < page_count)

    def _previous_preview_page(self):
        if self._preview_page > 0:
            self._preview_page -= 1
            self._update_preview()

    def _next_preview_page(self):
        if self._preview_page + 1 < self._preview_page_count:
            self._preview_page += 1
            self._update_preview()

    def choose_destination(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Choose output folder", str(self._output_dir or Path.home())
        )
        if directory:
            self._output_dir = Path(directory)
            self.destination_field.setText(f"SAVE TO  /  {self._output_dir}")
            self.destination_field.setToolTip(str(self._output_dir))
            self._preferences.set("last_output_dir", str(self._output_dir))

    def output_options(self, options: dict | None = None) -> dict:
        merged = dict(options or {})
        merged.update(self._read_options())
        if self._output_dir is not None:
            merged["output_dir"] = str(self._output_dir)
        return merged

    def _add_option(self, key: str, title: str, widget: QWidget):
        self._option_widgets[key] = widget
        self.options_layout.addRow(label(title.upper(), 10, THEME.muted, QFont.DemiBold), widget)

    def _build_options(self):
        tool_id = self.tool["id"]
        if tool_id == "compress":
            quality = QComboBox()
            quality.addItems(["Extreme", "Recommended", "Less"])
            self._add_option("level", "Compression level", quality)
        elif tool_id == "compress-image":
            quality = QSpinBox()
            quality.setRange(10, 100)
            quality.setValue(82)
            self._add_option("quality", "JPEG quality", quality)
        elif tool_id == "resize-image":
            width = QSpinBox()
            width.setRange(1, 12000)
            width.setValue(1600)
            height = QSpinBox()
            height.setRange(1, 12000)
            height.setValue(1600)
            self._add_option("width", "Maximum width", width)
            self._add_option("height", "Maximum height", height)
        elif tool_id == "pdf-to-images":
            dpi = QSpinBox()
            dpi.setRange(48, 600)
            dpi.setValue(150)
            self._add_option("dpi", "Render DPI", dpi)
        elif tool_id == "remove-background":
            tolerance = QSpinBox()
            tolerance.setRange(1, 100)
            tolerance.setValue(32)
            self._add_option("tolerance", "Background tolerance", tolerance)
        elif tool_id == "transform-image":
            operation = QComboBox()
            operation.addItem("Rotate right", "rotate-right")
            operation.addItem("Rotate left", "rotate-left")
            operation.addItem("Flip horizontal", "flip-horizontal")
            operation.addItem("Flip vertical", "flip-vertical")
            operation.addItem("Grayscale", "grayscale")
            self._add_option("operation", "Transform", operation)
        elif tool_id in {"extract", "remove-pages"}:
            pages = QLineEdit()
            pages.setPlaceholderText("Example: 1, 3-5, 8")
            pages.setMinimumHeight(38)
            self._add_option("pages", "Pages to extract" if tool_id == "extract" else "Pages to remove", pages)
        elif tool_id == "page-numbers":
            start_number = QSpinBox()
            start_number.setRange(1, 999999)
            start_number.setValue(1)
            self._add_option("start_number", "Start numbering at", start_number)
            position = QComboBox()
            position.addItem("Bottom left", "bottom-left")
            position.addItem("Bottom center", "bottom-center")
            position.addItem("Bottom right", "bottom-right")
            position.setCurrentIndex(1)
            self._add_option("position", "Position", position)

    def _read_options(self) -> dict:
        values: dict[str, object] = {}
        for key, widget in self._option_widgets.items():
            if isinstance(widget, QSpinBox):
                values[key] = widget.value()
            elif isinstance(widget, QComboBox):
                values[key] = widget.currentData() if widget.currentData() is not None else widget.currentText()
            elif isinstance(widget, QLineEdit):
                values[key] = widget.text()
        return values

    def _begin_worker(self, func, *args, **kwargs):
        if self._operation_service.running:
            self._handle_error("Another task is already running.")
            return
        try:
            kind = "image" if self.tool.get("kind") == "image" else "pdf"
            validate_inputs(self._paths, kind)
            input_bytes = sum(path.stat().st_size for path in self._paths)
            output_directory = self._output_dir or (
                self._paths[0].parent if self._paths else None
            )
            validate_output_directory(output_directory, required_bytes=input_bytes * 2)
        except ValueError as exc:
            self._handle_error(str(exc))
            return
        self._clear_output_actions()
        self.result_list.clear()
        self.result_list.addItem("PROCESSING LOCALLY…")
        self._diagnostic_id = None
        self.progress_bar.setValue(0)
        self.progress_status.setText("STARTING…")
        self.cancel_button.setEnabled(True)
        self._operation_service.start(func, *args, **kwargs)

    def cancel_action(self):
        if self._operation_service.running:
            self._operation_service.cancel()
            self.progress_status.setText("CANCELLING…")
            self.cancel_button.setEnabled(False)

    def shutdown_operation(self) -> bool:
        return self._operation_service.shutdown()

    def _set_diagnostic_id(self, operation_id: str):
        self._diagnostic_id = operation_id

    def _handle_operation_state(self, state: str):
        if state in {"completed", "failed"}:
            self.cancel_button.setEnabled(False)

    def _handle_error_with_diagnostic(self, message: str, operation_id: str):
        if operation_id:
            self._set_diagnostic_id(operation_id)
        if message:
            self._handle_error(message)

    def _handle_progress(self, value: float, message: str):
        self.progress_bar.setValue(max(0, min(100, round(value))))
        self.progress_status.setText(message.upper())

    def _handle_result(self, result):
        self.result_list.clear()
        self._clear_output_actions()
        self.output_summary.setVisible(False)
        items = result if isinstance(result, list) else [result]
        self.result_list.addItem("DONE — OUTPUT READY")
        output_paths = [Path(str(item)) for item in items]
        self.progress_bar.setValue(100)
        self.progress_status.setText("COMPLETE")
        for path in output_paths:
            self.result_list.addItem(str(path))
            if path.is_file():
                actions = OutputActions()
                actions.set_path(path)
                self.output_actions_layout.addWidget(actions)
        self.output_actions_panel.setVisible(bool(self.output_actions_layout.count()))
        if output_paths:
            self.output_summary.setText(self._output_summary(output_paths))
            self.output_summary.setVisible(True)

    def _clear_output_actions(self):
        while self.output_actions_layout.count():
            item = self.output_actions_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.output_actions_panel.setVisible(False)

    def _output_summary(self, paths: list[Path]) -> str:
        existing = [path for path in paths if path.exists()]
        total_bytes = sum(path.stat().st_size for path in existing)
        count = len(existing)
        if self.tool["id"] in {"compress", "compress-image"} and self._paths and existing:
            source_bytes = sum(path.stat().st_size for path in self._paths if path.exists())
            if source_bytes:
                delta = source_bytes - total_bytes
                percentage = (delta / source_bytes) * 100
                if delta >= 0:
                    return (
                        f"{count} output{'s' if count != 1 else ''}  ·  "
                        f"{source_bytes / 1024:.1f} KB → {total_bytes / 1024:.1f} KB  ·  "
                        f"{percentage:.1f}% smaller"
                    )
                return (
                    f"{count} output{'s' if count != 1 else ''}  ·  "
                    f"{source_bytes / 1024:.1f} KB → {total_bytes / 1024:.1f} KB  ·  "
                    f"{abs(percentage):.1f}% larger"
                )
        return f"{count} output{'s' if count != 1 else ''}  ·  {total_bytes / 1024:.1f} KB total"

    def _handle_error(self, message: str):
        self.result_list.clear()
        if message.lower() == "cancelled.":
            self.result_list.addItem("CANCELLED — NO OUTPUT WAS CREATED")
            self.progress_status.setText("CANCELLED")
        else:
            self.result_list.addItem(f"ERROR — {message}")
            if self._diagnostic_id:
                self.result_list.addItem(f"DIAGNOSTIC ID — {self._diagnostic_id}")
            self.progress_status.setText("FAILED")

    def run_action(self):
        self.result_list.clear()
        self.result_list.addItem(f"{self.tool['title'].upper()} IS READY.")


class HomeScreen(QWidget):
    def __init__(self, on_open_tool=None):
        super().__init__()
        self.on_open_tool = on_open_tool
        self.all_cards: list[ToolCard] = []
        self.search = SearchField()
        self._format_filter = "all"
        self.setStyleSheet(f"background: {THEME.bg};")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setAlignment(Qt.AlignTop)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        content = QWidget()
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(56, 56, 56, 64)
        content_layout.setSpacing(32)
        scroll.setWidget(content)
        outer.addWidget(scroll)
        outer = content_layout

        eyebrow = label("PDF + IMAGE TOOLKIT  /  LOCAL WORKSPACE", 10, THEME.muted, QFont.DemiBold)
        outer.addWidget(eyebrow)

        heading = label("Make files feel\nless complicated.", 54, THEME.text, QFont.Bold)
        heading.setObjectName("hero-heading")
        outer.addWidget(heading)
        subline = label("A focused, private workspace for PDFs and images.", 15, THEME.muted)
        outer.addWidget(subline)
        outer.addSpacing(18)

        self.format_filters = QButtonGroup(self)
        self.format_filters.setExclusive(True)
        search_row = QHBoxLayout()
        search_row.setSpacing(10)
        search_row.addWidget(label("SHOW", 10, THEME.muted, QFont.DemiBold))
        for key, text in (("all", "ALL"), ("pdf", "PDF"), ("image", "IMAGE")):
            button = QPushButton(text)
            button.setCheckable(True)
            button.setChecked(key == "all")
            button.setCursor(Qt.PointingHandCursor)
            button.setFocusPolicy(Qt.StrongFocus)
            button.setAccessibleName(f"Show {text.lower()} tools")
            button.setObjectName("home-format-filter")
            button.clicked.connect(lambda _checked=False, value=key: self._set_format_filter(value))
            self.format_filters.addButton(button)
            search_row.addWidget(button)
        search_row.addStretch()
        self.search.setMaximumWidth(360)
        search_row.addWidget(self.search)
        outer.addLayout(search_row)
        self.search.textChanged.connect(self.filter_cards)

        section_row = QHBoxLayout()
        section_row.addWidget(label("YOUR TOOLKIT", 11, THEME.text, QFont.DemiBold))
        section_row.addStretch()
        section_row.addWidget(label(f"{len(TOOL_CATALOG)} TOOLS  /  OFFLINE", 10, THEME.dim, QFont.DemiBold))
        outer.addLayout(section_row)

        self.card_grid = QGridLayout()
        self.card_grid.setHorizontalSpacing(44)
        self.card_grid.setVerticalSpacing(44)
        for tool in TOOL_CATALOG:
            card = ToolCard(tool)
            if self.on_open_tool:
                card.opened.connect(self.on_open_tool)
            self.all_cards.append(card)
        outer.addLayout(self.card_grid)
        self._rebuild_card_grid(self.all_cards)
        outer.addStretch(1)
        outer.addWidget(StatusStrip())

    def record_tool(self, tool_id: str):
        return None

    def filter_cards(self, query: str):
        text = query.strip().lower()
        visible_cards: list[ToolCard] = []
        for card in self.all_cards:
            tool = card.tool
            matches_text = not text or any(
                text in tool[key].lower() for key in ("title", "subtitle", "category")
            )
            is_image = tool.get("kind") == "image"
            matches_format = (
                self._format_filter == "all"
                or (self._format_filter == "image" and is_image)
                or (self._format_filter == "pdf" and not is_image)
            )
            visible = matches_text and matches_format
            card.setVisible(visible)
            if visible:
                visible_cards.append(card)
        self._rebuild_card_grid(visible_cards)

    def _rebuild_card_grid(self, visible_cards: list[ToolCard]):
        while self.card_grid.count():
            item = self.card_grid.takeAt(0)
            if item.widget() is not None:
                item.widget().setVisible(False)

        for index, card in enumerate(visible_cards):
            self.card_grid.addWidget(card, index // 3, index % 3)
            card.setVisible(True)

    def _set_format_filter(self, value: str):
        self._format_filter = value
        self.filter_cards(self.search.text())

    def filter_category(self, category: str):
        self.search.setText("" if category == "All" else category)


class MergeToolScreen(ToolScreen):
    def __init__(self):
        super().__init__(next(tool for tool in TOOL_CATALOG if tool["id"] == "merge"))

    def run_action(self):
        if not self._paths:
            self.result_list.clear()
            self.result_list.addItem("CHOOSE AT LEAST ONE PDF FIRST.")
            return
        self._begin_worker(merge_run, [str(path) for path in self._paths], self.output_options({"pages": []}))


class SplitToolScreen(ToolScreen):
    def __init__(self):
        super().__init__(next(tool for tool in TOOL_CATALOG if tool["id"] == "split"))

    def run_action(self):
        if not self._paths:
            self.result_list.clear()
            self.result_list.addItem("CHOOSE A PDF FIRST.")
            return
        self._begin_worker(
            split_run,
            [str(self._paths[0])],
            self.output_options({"mode": "chunks", "chunk_size": 2}),
        )


class ExtractToolScreen(ToolScreen):
    def __init__(self):
        super().__init__(next(tool for tool in TOOL_CATALOG if tool["id"] == "extract"))

    def run_action(self):
        if not self._paths:
            self.result_list.clear()
            self.result_list.addItem("CHOOSE A PDF FIRST.")
            return
        self._begin_worker(
            extract_run,
            [str(self._paths[0])],
            self.output_options(),
        )


class RemovePagesToolScreen(ToolScreen):
    def __init__(self):
        super().__init__(next(tool for tool in TOOL_CATALOG if tool["id"] == "remove-pages"))

    def run_action(self):
        if not self._paths:
            self.result_list.clear()
            self.result_list.addItem("CHOOSE A PDF FIRST.")
            return
        self._begin_worker(
            remove_pages_run,
            [str(self._paths[0])],
            self.output_options(),
        )


class ReorderToolScreen(ToolScreen):
    def __init__(self):
        super().__init__(next(tool for tool in TOOL_CATALOG if tool["id"] == "reorder"))

    def run_action(self):
        if not self._paths:
            self.result_list.clear()
            self.result_list.addItem("CHOOSE A PDF FIRST.")
            return
        self._begin_worker(
            reorder_run,
            [str(self._paths[0])],
            self.output_options({"order": self._page_order}),
        )


class PageNumbersToolScreen(ToolScreen):
    def __init__(self):
        super().__init__(next(tool for tool in TOOL_CATALOG if tool["id"] == "page-numbers"))

    def run_action(self):
        if not self._paths:
            self.result_list.clear()
            self.result_list.addItem("CHOOSE A PDF FIRST.")
            return
        self._begin_worker(
            page_numbers_run,
            [str(self._paths[0])],
            self.output_options(),
        )


class FormFieldsToolScreen(ToolScreen):
    def __init__(self):
        super().__init__(next(tool for tool in TOOL_CATALOG if tool["id"] == "form-fields"))

    def run_action(self):
        if not self._paths:
            self.result_list.clear()
            self.result_list.addItem("CHOOSE A PDF FIRST.")
            return
        self._begin_worker(form_fields_run, [str(self._paths[0])], self.output_options())


class CompressToolScreen(ToolScreen):
    def __init__(self):
        super().__init__(next(tool for tool in TOOL_CATALOG if tool["id"] == "compress"))

    def run_action(self):
        if not self._paths:
            self.result_list.clear()
            self.result_list.addItem("CHOOSE A PDF FIRST.")
            return
        self._begin_worker(
            compress_run,
            [str(self._paths[0])],
            self.output_options({"level": "Recommended"}),
        )


class RotateToolScreen(ToolScreen):
    def __init__(self):
        super().__init__(next(tool for tool in TOOL_CATALOG if tool["id"] == "rotate"))

    def run_action(self):
        if not self._paths:
            self.result_list.clear()
            self.result_list.addItem("CHOOSE A PDF FIRST.")
            return
        self._begin_worker(
            rotate_run,
            [str(self._paths[0])],
            self.output_options({"angle": 90}),
        )


class ProtectToolScreen(ToolScreen):
    def __init__(self):
        super().__init__(next(tool for tool in TOOL_CATALOG if tool["id"] == "protect"))
        for key in ("user_password", "confirm_password"):
            widget = QLineEdit()
            widget.setEchoMode(QLineEdit.Password)
            widget.setMinimumHeight(38)
            self._add_option(key, "Password" if key == "user_password" else "Confirm password", widget)

    def run_action(self):
        if not self._paths:
            self.result_list.clear()
            self.result_list.addItem("CHOOSE A PDF FIRST.")
            return
        user_password = str(self._option_widgets["user_password"].text())
        confirm_password = str(self._option_widgets["confirm_password"].text())
        if user_password != confirm_password:
            self._handle_error("Passwords do not match.")
            return
        if len(user_password) < 4:
            self._handle_error("Password must be at least 4 characters.")
            return
        self._begin_worker(
            protect_run,
            [str(self._paths[0])],
            self.output_options(
                {
                    "user_password": user_password,
                    "owner_password": user_password,
                }
            ),
        )


class ImagesToPdfToolScreen(ToolScreen):
    def __init__(self):
        super().__init__(next(tool for tool in TOOL_CATALOG if tool["id"] == "images-to-pdf"))

    def run_action(self):
        if not self._paths:
            self.result_list.addItem("CHOOSE AT LEAST ONE IMAGE FIRST.")
            return
        self._begin_worker(images_to_pdf, [str(path) for path in self._paths], self.output_options())


class PdfToImagesToolScreen(ToolScreen):
    def __init__(self):
        super().__init__(next(tool for tool in TOOL_CATALOG if tool["id"] == "pdf-to-images"))

    def run_action(self):
        if not self._paths:
            self.result_list.addItem("CHOOSE A PDF FIRST.")
            return
        self._begin_worker(pdf_to_images, [str(self._paths[0])], self.output_options())


class CompressImageToolScreen(ToolScreen):
    def __init__(self):
        super().__init__(next(tool for tool in TOOL_CATALOG if tool["id"] == "compress-image"))

    def run_action(self):
        if not self._paths:
            self.result_list.addItem("CHOOSE AT LEAST ONE IMAGE FIRST.")
            return
        self._begin_worker(compress_image, [str(path) for path in self._paths], self.output_options())


class ResizeImageToolScreen(ToolScreen):
    def __init__(self):
        super().__init__(next(tool for tool in TOOL_CATALOG if tool["id"] == "resize-image"))

    def run_action(self):
        if not self._paths:
            self.result_list.addItem("CHOOSE AT LEAST ONE IMAGE FIRST.")
            return
        self._begin_worker(resize_image, [str(path) for path in self._paths], self.output_options())


class RemoveBackgroundToolScreen(ToolScreen):
    def __init__(self):
        super().__init__(next(tool for tool in TOOL_CATALOG if tool["id"] == "remove-background"))

    def run_action(self):
        if not self._paths:
            self.result_list.addItem("CHOOSE AT LEAST ONE IMAGE FIRST.")
            return
        self._begin_worker(remove_background, [str(path) for path in self._paths], self.output_options())


class TransformImageToolScreen(ToolScreen):
    def __init__(self):
        super().__init__(next(tool for tool in TOOL_CATALOG if tool["id"] == "transform-image"))

    def run_action(self):
        if not self._paths:
            self.result_list.addItem("CHOOSE AT LEAST ONE IMAGE FIRST.")
            return
        self._begin_worker(
            transform_image,
            [str(path) for path in self._paths],
            self.output_options({"operation": "rotate-right"}),
        )


class CropImageToolScreen(ToolScreen):
    def __init__(self):
        super().__init__(next(tool for tool in TOOL_CATALOG if tool["id"] == "crop-image"))

    def run_action(self):
        if not self._paths:
            self.result_list.addItem("CHOOSE AT LEAST ONE IMAGE FIRST.")
            return
        self._begin_worker(crop_to_content, [str(path) for path in self._paths], self.output_options())
