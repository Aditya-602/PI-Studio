from __future__ import annotations

import time

from PySide6.QtCore import QPoint, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QMenu,
    QVBoxLayout,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QWidget,
)

from .screens import (
    CompressToolScreen,
    ExtractToolScreen,
    HomeScreen,
    MergeToolScreen,
    ProtectToolScreen,
    PageNumbersToolScreen,
    FormFieldsToolScreen,
    RotateToolScreen,
    SplitToolScreen,
    ImagesToPdfToolScreen,
    PdfToImagesToolScreen,
    CompressImageToolScreen,
    ResizeImageToolScreen,
    RemoveBackgroundToolScreen,
    RemovePagesToolScreen,
    ReorderToolScreen,
    TransformImageToolScreen,
    CropImageToolScreen,
)
from .theme import app_stylesheet
from .components import CompactButton
from pdf_toolkit.preferences import Preferences


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("P — Offline PDF Studio")
        self.resize(1440, 920)
        self.setMinimumSize(1100, 720)
        self.setStyleSheet(app_stylesheet())
        self._operations: dict[str, dict[str, object]] = {}
        self._operations_menu_signature: tuple[object, ...] | None = None
        self.preferences = Preferences()
        geometry = self.preferences.get("window_geometry")
        if isinstance(geometry, dict):
            self.setGeometry(
                int(geometry.get("x", 100)),
                int(geometry.get("y", 100)),
                int(geometry.get("width", 1440)),
                int(geometry.get("height", 920)),
            )

        root = QWidget()
        self._app_root = root
        root.setObjectName("app-root")
        shell = QVBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        self.operations_button = CompactButton("JOBS  0")
        self.operations_button.setObjectName("operations-button")
        self.operations_button.setFixedSize(112, 36)
        self.operations_button.setAccessibleName("Active operations")
        self.operations_button.setAccessibleDescription(
            "Show progress and cancellation controls for running operations"
        )
        self.operations_button.setToolTip("Show active operations")
        self.operations_menu = QMenu(self.operations_button)
        self.operations_button.clicked.connect(self._show_operations_menu)
        self.operations_menu.aboutToShow.connect(self._refresh_operations_menu)
        self.operations_button.setParent(root)

        self.stacked = QStackedWidget()
        self.home = HomeScreen(on_open_tool=self.show_tool)
        self.stacked.addWidget(self.home)
        self.tool_screens: dict[str, QWidget] = {}
        self._tool_screen_classes = {
            "merge": MergeToolScreen,
            "split": SplitToolScreen,
            "extract": ExtractToolScreen,
            "remove-pages": RemovePagesToolScreen,
            "reorder": ReorderToolScreen,
            "compress": CompressToolScreen,
            "rotate": RotateToolScreen,
            "protect": ProtectToolScreen,
            "page-numbers": PageNumbersToolScreen,
            "form-fields": FormFieldsToolScreen,
            "images-to-pdf": ImagesToPdfToolScreen,
            "pdf-to-images": PdfToImagesToolScreen,
            "compress-image": CompressImageToolScreen,
            "resize-image": ResizeImageToolScreen,
            "remove-background": RemoveBackgroundToolScreen,
            "transform-image": TransformImageToolScreen,
            "crop-image": CropImageToolScreen,
        }
        shell.addWidget(self.stacked, 1)
        self.setCentralWidget(root)
        self._position_operations_button()
        self._menu_refresh_timer = QTimer(self)
        self._menu_refresh_timer.setInterval(1000)
        self._menu_refresh_timer.timeout.connect(self._refresh_operations_menu)
        self._menu_refresh_timer.start()

    def show_tool(self, tool_id: str):
        screen = self._ensure_tool_screen(tool_id)
        if screen is not None:
            self.home.record_tool(tool_id)
            self.stacked.setCurrentWidget(screen)
            self._fade_in(screen)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_operations_button()

    def _position_operations_button(self):
        if hasattr(self, "operations_button") and hasattr(self, "_app_root"):
            self.operations_button.move(
                self._app_root.width() - self.operations_button.width() - 56,
                16,
            )
            self.operations_button.raise_()

    def _ensure_tool_screen(self, tool_id: str) -> QWidget | None:
        screen = self.tool_screens.get(tool_id)
        if screen is not None:
            return screen
        screen_class = self._tool_screen_classes.get(tool_id)
        if screen_class is None:
            return None
        screen = screen_class()
        self.tool_screens[tool_id] = screen
        screen.back_button.clicked.connect(self.show_home)
        service = screen.operation_service
        service.progress.connect(
            lambda value, message, tool_id=tool_id: self._operation_progress(
                tool_id, value, message
            )
        )
        service.state_changed.connect(
            lambda state, tool_id=tool_id: self._operation_state(tool_id, state)
        )
        self.stacked.addWidget(screen)
        return screen

    def show_home(self):
        self.stacked.setCurrentWidget(self.home)
        self._fade_in(self.home)

    def _operation_progress(self, tool_id: str, value: float, message: str):
        operation = self._operations.setdefault(tool_id, {})
        operation["value"] = max(0, min(100, round(value)))
        operation["message"] = message
        self._refresh_operations_indicator()

    def _operation_state(self, tool_id: str, state: str):
        if state == "running":
            operation = self._operations.setdefault(tool_id, {})
            operation.setdefault("value", 0)
            operation.setdefault("message", "Starting")
            operation["started_at"] = time.monotonic()
            operation["state"] = state
        elif state in {"completed", "failed"}:
            self._operations.pop(tool_id, None)
        elif state == "cancelling" and tool_id in self._operations:
            self._operations[tool_id]["state"] = state
        self._refresh_operations_indicator()

    def _refresh_operations_indicator(self):
        active = len(self._operations)
        self.operations_button.setText(f"JOBS  {active}")
        self.operations_button.setToolTip(
            f"{active} active operation{'s' if active != 1 else ''}"
        )
        self._refresh_operations_menu()

    def _show_operations_menu(self):
        self._refresh_operations_menu()
        menu_size = self.operations_menu.sizeHint()
        anchor = self.operations_button.mapToGlobal(
            QPoint(self.operations_button.width(), self.operations_button.height())
        )
        root_top_left = self._app_root.mapToGlobal(QPoint(0, 0))
        root_rect = self._app_root.rect()
        frame_left = root_top_left.x() + 12
        frame_right = root_top_left.x() + root_rect.width() - 12
        frame_top = root_top_left.y() + 12
        frame_bottom = root_top_left.y() + root_rect.height() - 12

        x = min(anchor.x() - menu_size.width(), frame_right - menu_size.width())
        x = max(frame_left, x)
        y = anchor.y() + 8
        if y + menu_size.height() > frame_bottom:
            y = anchor.y() - menu_size.height() - 8
        y = max(frame_top, min(y, frame_bottom - menu_size.height()))
        self.operations_menu.popup(QPoint(x, y))

    def _refresh_operations_menu(self):
        signature: list[object] = [bool(self._operations)]
        if self._operations:
            for tool_id, operation in self._operations.items():
                started_at = float(operation.get("started_at", time.monotonic()))
                signature.extend(
                    (
                        tool_id,
                        int(operation.get("value", 0)),
                        str(operation.get("message", "Starting")),
                        str(operation.get("state", "running")),
                        int(time.monotonic() - started_at),
                    )
                )
        current_signature = tuple(signature)
        if current_signature == self._operations_menu_signature:
            return
        self._operations_menu_signature = current_signature
        self.operations_menu.clear()
        if not self._operations:
            action = self.operations_menu.addAction("No active operations")
            action.setEnabled(False)
            return
        header = self.operations_menu.addAction("ACTIVE OPERATIONS")
        header.setEnabled(False)
        cancel_all = self.operations_menu.addAction("Cancel All Active Operations")
        cancel_all.triggered.connect(self._cancel_all_operations)
        self.operations_menu.addSeparator()
        for tool_id, operation in self._operations.items():
            screen = self.tool_screens[tool_id]
            value = int(operation.get("value", 0))
            message = str(operation.get("message", "Starting")).upper()
            state = str(operation.get("state", "running")).upper()
            started_at = float(operation.get("started_at", time.monotonic()))
            elapsed = self._format_elapsed(time.monotonic() - started_at)
            action = self.operations_menu.addAction(
                f"{screen.tool['title']}  ·  {value}%  ·  {message}  ·  {elapsed}"
            )
            action.setToolTip(f"{state} — elapsed {elapsed} — click to open this tool")
            action.triggered.connect(lambda _checked=False, tool_id=tool_id: self.show_tool(tool_id))
            cancel_action = self.operations_menu.addAction(
                f"Cancel {screen.tool['title']}"
            )
            cancel_action.setEnabled(state != "CANCELLING")
            cancel_action.triggered.connect(
                lambda _checked=False, tool_id=tool_id: self._cancel_operation(tool_id)
            )
            self.operations_menu.addSeparator()

    @staticmethod
    def _format_elapsed(seconds: float) -> str:
        total_seconds = max(0, int(seconds))
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}h {minutes:02d}m"
        if minutes:
            return f"{minutes}m {seconds:02d}s"
        return f"{seconds}s"

    def _cancel_operation(self, tool_id: str):
        screen = self.tool_screens.get(tool_id)
        if screen is not None:
            screen.operation_service.cancel()

    def _cancel_all_operations(self):
        for tool_id in tuple(self._operations):
            self._cancel_operation(tool_id)

    def closeEvent(self, event):
        stopped = True
        for screen in self.tool_screens.values():
            stopped = screen.shutdown_operation() and stopped
        if not stopped:
            QMessageBox.warning(
                self,
                "Operation still running",
                "An operation is still running. Please wait for it to finish or cancel it before closing.",
            )
            event.ignore()
            return
        self.preferences.set(
            "window_geometry",
            {
                "x": self.x(),
                "y": self.y(),
                "width": self.width(),
                "height": self.height(),
            },
        )
        super().closeEvent(event)

    def _fade_in(self, widget: QWidget):
        # Screen widgets are reused by the stacked layout. Avoid applying a
        # graphics effect here because Qt may repaint the same widget while it
        # is being reparented, which produces invalid painter state.
        if widget.graphicsEffect() is not None:
            widget.setGraphicsEffect(None)
        widget.update()


def launch_app() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
