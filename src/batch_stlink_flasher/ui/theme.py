"""Application visual theme: dark/light stylesheets, icons, branding colors."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QPushButton, QStyle, QWidget

from batch_stlink_flasher.assets_util import asset_path

# Kept for splash/back-compat imports (resolve to active dark palette tokens).
ACCENT = "#2f9e88"
ACCENT_HOVER = "#3cb89f"
ACCENT_PRESSED = "#248070"
DANGER = "#c45c5c"
DANGER_HOVER = "#d47070"
BG = "#1b212c"
BG_ELEVATED = "#242b38"
BG_INPUT = "#12161e"
BORDER = "#3a4556"
TEXT = "#e8eef5"
TEXT_MUTED = "#9aa7b8"


class ThemeMode(str, Enum):
    """User preference for appearance."""

    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


@dataclass(frozen=True)
class ThemePalette:
    name: str
    accent: str
    accent_hover: str
    accent_pressed: str
    danger: str
    danger_hover: str
    danger_bg: str
    danger_text: str
    bg: str
    bg_elevated: str
    bg_input: str
    bg_hover: str
    bg_pressed: str
    bg_disabled: str
    border: str
    border_disabled: str
    text: str
    text_muted: str
    text_disabled: str
    text_on_accent: str
    table_alt: str
    table_grid: str
    selection_bg: str
    menu_selected_text: str


DARK = ThemePalette(
    name="dark",
    accent="#2f9e88",
    accent_hover="#3cb89f",
    accent_pressed="#248070",
    danger="#c45c5c",
    danger_hover="#d47070",
    danger_bg="#3a2426",
    danger_text="#f0d0d0",
    bg="#1b212c",
    bg_elevated="#242b38",
    bg_input="#12161e",
    bg_hover="#2a3342",
    bg_pressed="#1f2632",
    bg_disabled="#1a1f28",
    border="#3a4556",
    border_disabled="#2e3644",
    text="#e8eef5",
    text_muted="#9aa7b8",
    text_disabled="#6b7685",
    text_on_accent="#06201a",
    table_alt="#161b24",
    table_grid="#2a3340",
    selection_bg="#1e4a42",
    menu_selected_text="#0b1210",
)

LIGHT = ThemePalette(
    name="light",
    accent="#1f8a75",
    accent_hover="#2aa08a",
    accent_pressed="#187261",
    danger="#c0392b",
    danger_hover="#d35448",
    danger_bg="#fdecea",
    danger_text="#7a1f18",
    bg="#f4f6f8",
    bg_elevated="#ffffff",
    bg_input="#ffffff",
    bg_hover="#e8eef3",
    bg_pressed="#dce4ec",
    bg_disabled="#eef1f4",
    border="#c5ced8",
    border_disabled="#d7dee5",
    text="#1a2330",
    text_muted="#5b6b7c",
    text_disabled="#93a0ae",
    text_on_accent="#ffffff",
    table_alt="#eef2f6",
    table_grid="#d7dee5",
    selection_bg="#d5f0e9",
    menu_selected_text="#ffffff",
)

_ACTIVE: ThemePalette = DARK


def active_palette() -> ThemePalette:
    return _ACTIVE


def normalize_theme_mode(value: str | ThemeMode | None) -> ThemeMode:
    if isinstance(value, ThemeMode):
        return value
    text = str(value if value is not None else ThemeMode.SYSTEM.value).strip().lower()
    # Accept either "light" or accidental "thememode.light" forms.
    if "." in text:
        text = text.rsplit(".", 1)[-1]
    try:
        return ThemeMode(text)
    except ValueError:
        return ThemeMode.SYSTEM


def system_prefers_dark() -> bool:
    """True when the OS color scheme is dark (fallback: dark)."""
    app = QGuiApplication.instance()
    if app is None:
        return True
    hints = app.styleHints()
    scheme = hints.colorScheme()
    if scheme == Qt.ColorScheme.Light:
        return False
    if scheme == Qt.ColorScheme.Dark:
        return True
    # Unknown / NoPreference: prefer dark for this tool's industrial look.
    return True


def resolve_palette(mode: ThemeMode | str | None) -> ThemePalette:
    resolved = normalize_theme_mode(mode)
    if resolved == ThemeMode.LIGHT:
        return LIGHT
    if resolved == ThemeMode.DARK:
        return DARK
    return DARK if system_prefers_dark() else LIGHT


def app_stylesheet(palette: ThemePalette | None = None) -> str:
    p = palette or active_palette()
    return f"""
    QWidget {{
        color: {p.text};
        font-size: 13px;
    }}
    QMainWindow, QDialog {{
        background-color: {p.bg};
    }}
    QMenuBar {{
        background-color: {p.bg_elevated};
        color: {p.text};
        border-bottom: 1px solid {p.border};
        padding: 2px 4px;
    }}
    QMenuBar::item:selected {{
        background-color: {p.bg_hover};
        border-radius: 4px;
    }}
    QMenu {{
        background-color: {p.bg_elevated};
        border: 1px solid {p.border};
        padding: 4px;
    }}
    QMenu::item:selected {{
        background-color: {p.accent};
        color: {p.menu_selected_text};
    }}
    QStatusBar {{
        background-color: {p.bg_elevated};
        color: {p.text_muted};
        border-top: 1px solid {p.border};
    }}
    QSplitter::handle {{
        background-color: {p.border};
        height: 2px;
    }}
    QPushButton {{
        background-color: {p.bg_elevated};
        border: 1px solid {p.border};
        border-radius: 6px;
        padding: 6px 12px;
        min-height: 28px;
    }}
    QPushButton:hover {{
        border-color: {p.accent};
        background-color: {p.bg_hover};
    }}
    QPushButton:pressed {{
        background-color: {p.bg_pressed};
    }}
    QPushButton:disabled {{
        color: {p.text_disabled};
        border-color: {p.border_disabled};
        background-color: {p.bg_disabled};
    }}
    QPushButton#primaryButton {{
        background-color: {p.accent};
        color: {p.text_on_accent};
        border: 1px solid {p.accent_pressed};
        font-weight: 700;
    }}
    QPushButton#primaryButton:hover {{
        background-color: {p.accent_hover};
    }}
    QPushButton#primaryButton:pressed {{
        background-color: {p.accent_pressed};
    }}
    QPushButton#dangerButton {{
        background-color: {p.danger_bg};
        border: 1px solid {p.danger};
        color: {p.danger_text};
    }}
    QPushButton#dangerButton:hover {{
        border-color: {p.danger_hover};
    }}
    QLineEdit, QPlainTextEdit, QSpinBox {{
        background-color: {p.bg_input};
        border: 1px solid {p.border};
        border-radius: 5px;
        padding: 5px 8px;
        selection-background-color: {p.accent};
        selection-color: {p.text_on_accent};
    }}
    QLineEdit:focus, QPlainTextEdit:focus {{
        border-color: {p.accent};
    }}
    QTableWidget {{
        background-color: {p.bg_input};
        alternate-background-color: {p.table_alt};
        gridline-color: {p.table_grid};
        border: 1px solid {p.border};
        border-radius: 6px;
    }}
    QHeaderView::section {{
        background-color: {p.bg_elevated};
        color: {p.text_muted};
        border: none;
        border-right: 1px solid {p.border};
        border-bottom: 1px solid {p.border};
        padding: 6px 8px;
        font-weight: 600;
    }}
    QTableWidget::item:selected {{
        background-color: {p.selection_bg};
        color: {p.text};
    }}
    QLabel#summaryLabel {{
        color: {p.text};
        font-weight: 700;
        font-size: 13px;
        padding: 6px 2px;
    }}
    QScrollBar:vertical {{
        background: {p.bg};
        width: 10px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {p.border};
        border-radius: 4px;
        min-height: 24px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    """


def splash_stylesheet(palette: ThemePalette | None = None) -> str:
    p = palette or active_palette()
    return f"""
    QWidget#splashRoot {{
        background-color: {p.bg};
        border: 1px solid {p.border};
        border-radius: 12px;
    }}
    QLabel#title {{
        color: {p.text};
        font-size: 20px;
        font-weight: 700;
    }}
    QLabel#subtitle {{
        color: {p.text_muted};
        font-size: 12px;
    }}
    QLabel#status {{
        color: {p.text};
        font-size: 13px;
    }}
    QProgressBar {{
        border: 1px solid {p.border};
        border-radius: 4px;
        background: {p.bg_input};
        text-align: center;
        color: {p.text};
        min-height: 16px;
    }}
    QProgressBar::chunk {{
        background-color: {p.accent};
        border-radius: 3px;
    }}
    """


def apply_app_theme(app: QApplication, mode: ThemeMode | str | None = ThemeMode.SYSTEM) -> ThemePalette:
    """Apply Fusion style + stylesheet for the resolved mode; return active palette."""
    global _ACTIVE, ACCENT, ACCENT_HOVER, ACCENT_PRESSED, DANGER, DANGER_HOVER
    global BG, BG_ELEVATED, BG_INPUT, BORDER, TEXT, TEXT_MUTED

    palette = resolve_palette(mode)
    _ACTIVE = palette
    ACCENT = palette.accent
    ACCENT_HOVER = palette.accent_hover
    ACCENT_PRESSED = palette.accent_pressed
    DANGER = palette.danger
    DANGER_HOVER = palette.danger_hover
    BG = palette.bg
    BG_ELEVATED = palette.bg_elevated
    BG_INPUT = palette.bg_input
    BORDER = palette.border
    TEXT = palette.text
    TEXT_MUTED = palette.text_muted

    app.setStyle("Fusion")
    app.setStyleSheet(app_stylesheet(palette))
    icon = load_app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    return palette


def load_app_icon() -> QIcon:
    """Prefer multi-size ``.ico`` on Windows; fall back to PNG."""
    for name in ("app_icon.ico", "app_icon.png", "logo.png"):
        path = asset_path(name)
        if path is None:
            continue
        icon = QIcon(str(path))
        if not icon.isNull():
            return icon
    return QIcon()


def load_logo_pixmap(*, max_width: int = 160) -> QPixmap:
    """Brand logo for splash / About (flat chip glyph)."""
    for name in ("logo.png", "app_icon.png"):
        path = asset_path(name)
        if path is None:
            continue
        pix = QPixmap(str(path))
        if pix.isNull():
            continue
        return pix.scaled(
            max_width,
            max_width,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    return _fallback_splash_pixmap(max_width)


def load_splash_pixmap(*, max_width: int = 160) -> QPixmap:
    """Splash artwork; falls back to the brand logo."""
    path = asset_path("splash.png")
    if path is not None:
        pix = QPixmap(str(path))
        if not pix.isNull():
            return pix.scaled(
                max_width,
                max_width,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
    return load_logo_pixmap(max_width=max_width)


def _fallback_splash_pixmap(size: int) -> QPixmap:
    p = active_palette()
    pix = QPixmap(size, size)
    pix.fill(QColor(p.bg))
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(p.accent))
    painter.setPen(Qt.PenStyle.NoPen)
    margin = size // 5
    painter.drawRoundedRect(margin, margin, size - 2 * margin, size - 2 * margin, 12, 12)
    painter.setBrush(QColor(p.bg))
    painter.drawRect(size // 3, size // 3, size // 3, size // 3)
    painter.end()
    return pix


def style_standard_icon(widget: QWidget, standard: QStyle.StandardPixmap) -> QIcon:
    style = widget.style()
    if style is None:
        style = QApplication.style()
    if style is None:
        return QIcon()
    return style.standardIcon(standard)


def decorate_button(
    button: QPushButton,
    *,
    standard: QStyle.StandardPixmap | None = None,
    role: str | None = None,
    icon_size: int = 16,
) -> None:
    """Attach a standard icon and optional objectName role (primary/danger)."""
    if standard is not None:
        button.setIcon(style_standard_icon(button, standard))
        button.setIconSize(QSize(icon_size, icon_size))
    if role == "primary":
        button.setObjectName("primaryButton")
    elif role == "danger":
        button.setObjectName("dangerButton")
