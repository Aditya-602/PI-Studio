from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    bg: str = "#0B0B0B"
    panel: str = "#101010"
    card: str = "#151515"
    card_hover: str = "#1B1B1B"
    line: str = "#292929"
    line_soft: str = "#202020"
    text: str = "#F5F5F2"
    muted: str = "#858583"
    dim: str = "#4E4E4C"
    white: str = "#FFFFFF"
    red: str = "#FF5A54"
    yellow: str = "#F7C948"
    green: str = "#5BE39A"
    blue: str = "#6878FF"
    violet: str = "#A078FF"
    max_width: int = 1440


THEME = Theme()


def app_stylesheet() -> str:
    return f"""
    QWidget {{
        color: {THEME.text};
        font-family: "Avenir Next", "Inter", sans-serif;
    }}
    QMainWindow, QWidget#app-root {{
        background: {THEME.bg};
    }}
    QPushButton#pdf-page-thumbnail {{
        background: {THEME.panel};
        border: 1px solid {THEME.line_soft};
        padding: 8px;
    }}
    QPushButton#pdf-page-thumbnail:hover {{
        border-color: {THEME.blue};
        background: {THEME.card_hover};
    }}
    QPushButton#pdf-page-thumbnail:checked {{
        border: 2px solid {THEME.green};
        background: {THEME.card_hover};
    }}
    QPushButton#pdf-page-thumbnail:pressed {{
        background: {THEME.line};
    }}
    QPushButton#pdf-page-thumbnail[dropTarget="true"] {{
        border: 2px dashed {THEME.yellow};
        background: {THEME.card_hover};
    }}
    QPushButton#home-format-filter {{
        background: transparent;
        border: 1px solid {THEME.line_soft};
        border-radius: 5px;
        color: {THEME.muted};
        min-height: 30px;
        padding: 0 12px;
        font-size: 9px;
        letter-spacing: 1px;
    }}
    QPushButton#home-format-filter:hover {{
        color: {THEME.text};
        border-color: {THEME.line};
    }}
    QPushButton#home-format-filter:checked {{
        background: {THEME.card};
        border-color: {THEME.text};
        color: {THEME.text};
    }}
    QMenu {{
        background: {THEME.panel};
        border: 1px solid {THEME.line};
        padding: 6px;
    }}
    QMenu::item {{
        padding: 10px 16px;
    }}
    QMenu::item:selected {{
        background: {THEME.card_hover};
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 8px 0;
    }}
    QScrollBar::handle:vertical {{
        background: {THEME.line};
        min-height: 36px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    """
