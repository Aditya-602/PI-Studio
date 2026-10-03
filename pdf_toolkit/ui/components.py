from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QProcess, QUrl, Qt, Signal
from PySide6.QtGui import QColor, QDesktopServices, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .theme import THEME


def label(text: str, size: int, color: str = THEME.text, weight: int = QFont.Normal) -> QLabel:
    item = QLabel(text)
    font = QFont("Avenir Next", size)
    font.setWeight(weight)
    item.setFont(font)
    item.setStyleSheet(f"color: {color};")
    return item


class NeoButton(QPushButton):
    def __init__(self, text: str = "", accent: str = THEME.white, style: str = "primary"):
        super().__init__(text.upper())
        self.setAccessibleName(text)
        self.setAccessibleDescription(f"{text} action")
        self._accent = accent
        self._style = style
        self._hover = False
        self._pressed = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumHeight(44)
        self.setMinimumWidth(128)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setStyleSheet("border: none; background: transparent;")

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(1, 1, -6, -6)
        edge = self._accent if self._style == "accent" else THEME.line
        if self._style == "primary":
            face, text_color = THEME.white, THEME.bg
        elif self._style == "accent":
            face, text_color = self._accent, THEME.bg
        else:
            face, text_color = THEME.card, THEME.text
        if not self.isEnabled():
            face, edge, text_color = THEME.line_soft, THEME.line, THEME.dim
        if self._pressed:
            painter.fillRect(rect, face)
        else:
            painter.fillRect(rect.translated(0, 4), edge)
            painter.fillRect(rect, face)
        if self._style == "secondary":
            painter.setPen(QPen(QColor(THEME.line), 1))
            painter.drawRect(rect)
        painter.setPen(QPen(QColor(text_color), 1))
        painter.drawText(self.rect(), Qt.AlignCenter, self.text())

    def enterEvent(self, event) -> None:
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        self._pressed = True
        self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(event)


class CompactButton(QPushButton):
    def __init__(self, text: str = "", accent: str = THEME.blue):
        super().__init__(text)
        self._accent = accent
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAccessibleName(text)
        self.setAccessibleDescription(f"{text} action")
        self.setStyleSheet(
            f"""
            QPushButton {{
                background: {THEME.card};
                border: 1px solid {THEME.line_soft};
                border-radius: 5px;
                color: {THEME.text};
                padding: 0 12px;
                font-size: 10px;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: {THEME.card_hover};
                border-color: {THEME.line};
            }}
            QPushButton:pressed {{
                background: {THEME.line};
            }}
            QPushButton:focus {{
                border: 1px solid {THEME.line};
            }}
            QPushButton:disabled {{
                color: {THEME.dim};
                background: {THEME.line_soft};
                border-color: {THEME.line_soft};
            }}
            """
        )


class AccentRule(QFrame):
    def __init__(self, color: str = THEME.red, width: int = 44):
        super().__init__()
        self.setFixedSize(width, 3)
        self.setStyleSheet(f"background: {color};")


class ToolCard(QFrame):
    opened = Signal(str)

    def __init__(self, tool: dict):
        super().__init__()
        self.tool = tool
        self.setAccessibleName(tool["title"])
        self.setAccessibleDescription(tool["subtitle"])
        self.setObjectName("tool-card")
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(280)
        self.setAttribute(Qt.WA_Hover, True)
        self._hovered = False
        self._accent = tool["accent"]
        self._apply_style()

        body = QVBoxLayout(self)
        body.setContentsMargins(22, 20, 20, 18)
        body.setSpacing(5)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 20)
        top.setSpacing(10)
        index = label(f"{tool['id'].upper()[:2]}", 10, THEME.dim, QFont.DemiBold)
        top.addWidget(index)
        top.addStretch()
        category = label(tool["category"].upper(), 9, THEME.muted, QFont.DemiBold)
        top.addWidget(category)
        body.addLayout(top)

        title = label(tool["title"], 22, THEME.text, QFont.Bold)
        title.setContentsMargins(2, 2, 2, 0)
        body.addWidget(title)
        body.addSpacing(8)
        description = label(tool["subtitle"], 12, THEME.muted)
        description.setWordWrap(True)
        description.setContentsMargins(2, 0, 2, 2)
        body.addWidget(description)
        body.addStretch()

        footer = QHBoxLayout()
        footer.setContentsMargins(2, 18, 2, 0)
        footer.setSpacing(10)
        footer.addWidget(AccentRule(tool["accent"], 28))
        footer.addStretch()
        footer.addWidget(label("OPEN  ↗", 9, THEME.text, QFont.DemiBold))
        body.addLayout(footer)

    def _apply_style(self):
        background = THEME.card_hover if self._hovered else THEME.card
        border = self._accent if self._hovered else THEME.line_soft
        self.setStyleSheet(
            f"""
            QFrame#tool-card {{
                background: {background};
                border: 1px solid {border};
            }}
            """
        )

    def enterEvent(self, event) -> None:
        self._hovered = True
        self._apply_style()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self._apply_style()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.opened.emit(self.tool["id"])
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.opened.emit(self.tool["id"])
            event.accept()
            return
        super().keyPressEvent(event)


class SearchField(QLineEdit):
    def __init__(self, placeholder: str = "SEARCH TOOLS"):
        super().__init__()
        self.setAccessibleName("Search tools")
        self.setAccessibleDescription("Filter the available PDF and image tools")
        self.setPlaceholderText(placeholder)
        self.setMinimumHeight(52)
        self.setClearButtonEnabled(True)
        self.setStyleSheet(
            f"""
            QLineEdit {{
                background: {THEME.panel};
                border: 1px solid {THEME.line_soft};
                color: {THEME.text};
                padding: 0 18px;
                font-size: 12px;
                letter-spacing: 1.5px;
            }}
            QLineEdit:focus {{ border: 1px solid {THEME.muted}; }}
            """
        )


class Sidebar(QWidget):
    category_selected = Signal(str)

    def __init__(self, categories: list[str]):
        super().__init__()
        self.setFixedWidth(104)
        self.setStyleSheet(f"background: {THEME.panel}; border-right: 1px solid {THEME.line_soft};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 28, 18, 24)
        layout.setSpacing(10)
        brand = label("P", 30, THEME.text, QFont.Black)
        brand.setAlignment(Qt.AlignCenter)
        layout.addWidget(brand)
        layout.addSpacing(36)
        for index, category in enumerate(["Home", *categories]):
            item = QPushButton(category.upper())
            item.setCursor(Qt.PointingHandCursor)
            item.setMinimumHeight(56)
            item.setToolTip(category)
            item.setStyleSheet(
                f"""
                QPushButton {{
                    color: {THEME.muted};
                    background: transparent;
                    border: none;
                    font-size: 9px;
                    letter-spacing: 1.2px;
                    padding: 8px 2px;
                }}
                QPushButton:hover {{ color: {THEME.text}; }}
                QPushButton:focus {{
                    color: {THEME.text};
                    border: 1px solid {THEME.line};
                }}
                """
            )
            if category == "Home":
                self.home_button = item
            item.clicked.connect(lambda checked=False, value=category: self.category_selected.emit(value))
            layout.addWidget(item)
        layout.addStretch()
        layout.addWidget(label("OFFLINE", 9, THEME.green, QFont.DemiBold), alignment=Qt.AlignCenter)


class StatusStrip(QFrame):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(
            f"background: {THEME.panel}; border: 1px solid {THEME.line_soft};"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.addWidget(label("LOCAL MODE", 9, THEME.green, QFont.DemiBold))
        layout.addStretch()
        layout.addWidget(label("By Aditya Srivastava. IG: adiizxx ", 9, THEME.muted, QFont.Normal))


class OutputActions(QFrame):
    def __init__(self):
        super().__init__()
        self._path: Path | None = None
        self.setStyleSheet(f"background: {THEME.card}; border: 1px solid {THEME.line_soft};")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        self.path_label = label("NO OUTPUT SELECTED", 10, THEME.muted)
        layout.addWidget(self.path_label, 1)
        self.copy_button = NeoButton("Copy path", style="secondary")
        self.copy_button.clicked.connect(self.copy_path)
        self.open_button = NeoButton("Open", style="secondary")
        self.open_button.clicked.connect(self.open_file)
        self.reveal_button = NeoButton("Reveal", style="secondary")
        self.reveal_button.clicked.connect(self.reveal)
        layout.addWidget(self.copy_button)
        layout.addWidget(self.open_button)
        layout.addWidget(self.reveal_button)
        self.setVisible(False)

    def set_path(self, path: Path):
        self._path = path
        self.path_label.setText(f"{path.name}  ·  {path.stat().st_size / 1024:.1f} KB")
        self.setVisible(True)

    def clear(self):
        self._path = None
        self.path_label.setText("NO OUTPUT SELECTED")
        self.setVisible(False)

    def _has_existing_path(self) -> bool:
        return self._path is not None and self._path.is_file()

    def copy_path(self):
        if self._has_existing_path():
            QApplication.clipboard().setText(str(self._path))

    def open_file(self):
        if self._has_existing_path():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._path)))

    def reveal(self):
        if not self._has_existing_path():
            return
        path = self._path
        if sys.platform == "darwin":
            QProcess.startDetached("open", ["-R", str(path)])
        elif sys.platform == "win32":
            QProcess.startDetached("explorer", [f"/select,{path}"])
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))
