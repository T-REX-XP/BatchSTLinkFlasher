"""Application visual theme: stylesheet, icons, branding colors."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QPushButton, QStyle, QWidget

from batch_stlink_flasher.assets_util import asset_path

# Industrial charcoal + teal accent (avoid purple / neon defaults).
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


def app_stylesheet() -> str:
    return f"""
    QWidget {{
        color: {TEXT};
        font-size: 13px;
    }}
    QMainWindow, QDialog {{
        background-color: {BG};
    }}
    QMenuBar {{
        background-color: {BG_ELEVATED};
        color: {TEXT};
        border-bottom: 1px solid {BORDER};
        padding: 2px 4px;
    }}
    QMenuBar::item:selected {{
        background-color: {BORDER};
        border-radius: 4px;
    }}
    QMenu {{
        background-color: {BG_ELEVATED};
        border: 1px solid {BORDER};
        padding: 4px;
    }}
    QMenu::item:selected {{
        background-color: {ACCENT};
        color: #0b1210;
    }}
    QStatusBar {{
        background-color: {BG_ELEVATED};
        color: {TEXT_MUTED};
        border-top: 1px solid {BORDER};
    }}
    QSplitter::handle {{
        background-color: {BORDER};
        height: 2px;
    }}
    QPushButton {{
        background-color: {BG_ELEVATED};
        border: 1px solid {BORDER};
        border-radius: 6px;
        padding: 6px 12px;
        min-height: 28px;
    }}
    QPushButton:hover {{
        border-color: {ACCENT};
        background-color: #2a3342;
    }}
    QPushButton:pressed {{
        background-color: #1f2632;
    }}
    QPushButton:disabled {{
        color: #6b7685;
        border-color: #2e3644;
        background-color: #1a1f28;
    }}
    QPushButton#primaryButton {{
        background-color: {ACCENT};
        color: #06201a;
        border: 1px solid {ACCENT_PRESSED};
        font-weight: 700;
    }}
    QPushButton#primaryButton:hover {{
        background-color: {ACCENT_HOVER};
    }}
    QPushButton#primaryButton:pressed {{
        background-color: {ACCENT_PRESSED};
    }}
    QPushButton#dangerButton {{
        background-color: #3a2426;
        border: 1px solid {DANGER};
        color: #f0d0d0;
    }}
    QPushButton#dangerButton:hover {{
        background-color: #4a2e31;
        border-color: {DANGER_HOVER};
    }}
    QLineEdit, QPlainTextEdit, QSpinBox {{
        background-color: {BG_INPUT};
        border: 1px solid {BORDER};
        border-radius: 5px;
        padding: 5px 8px;
        selection-background-color: {ACCENT};
        selection-color: #06201a;
    }}
    QLineEdit:focus, QPlainTextEdit:focus {{
        border-color: {ACCENT};
    }}
    QTableWidget {{
        background-color: {BG_INPUT};
        alternate-background-color: #161b24;
        gridline-color: #2a3340;
        border: 1px solid {BORDER};
        border-radius: 6px;
    }}
    QHeaderView::section {{
        background-color: {BG_ELEVATED};
        color: {TEXT_MUTED};
        border: none;
        border-right: 1px solid {BORDER};
        border-bottom: 1px solid {BORDER};
        padding: 6px 8px;
        font-weight: 600;
    }}
    QTableWidget::item:selected {{
        background-color: #1e4a42;
        color: {TEXT};
    }}
    QLabel#summaryLabel {{
        color: {TEXT};
        font-weight: 700;
        font-size: 13px;
        padding: 6px 2px;
    }}
    QScrollBar:vertical {{
        background: {BG};
        width: 10px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {BORDER};
        border-radius: 4px;
        min-height: 24px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    """


def apply_app_theme(app: QApplication) -> None:
    """Apply global stylesheet and application icon."""
    app.setStyle("Fusion")
    app.setStyleSheet(app_stylesheet())
    icon = load_app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)


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
    pix = QPixmap(size, size)
    pix.fill(QColor(BG))
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(ACCENT))
    painter.setPen(Qt.PenStyle.NoPen)
    margin = size // 5
    painter.drawRoundedRect(margin, margin, size - 2 * margin, size - 2 * margin, 12, 12)
    painter.setBrush(QColor(BG))
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
