"""Application visual theme: dark/light stylesheets, icons, branding colors."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPalette, QPixmap, QPolygon
from PySide6.QtWidgets import QApplication, QPushButton, QSizePolicy, QStyle, QWidget

from batch_stlink_flasher.assets_util import asset_path

# Cached painted chevrons for QComboBox::down-arrow (Fusion loses its arrow when
# ::drop-down is restyled without an explicit image).
_COMBO_ARROW_CACHE: dict[str, str] = {}

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


def combo_down_arrow_url(color: str) -> str:
    """Paint a small chevron PNG and return a POSIX path for stylesheet ``url()``."""
    key = color.strip().lower().lstrip("#")
    cached = _COMBO_ARROW_CACHE.get(key)
    if cached and Path(cached).is_file():
        return Path(cached).as_posix()

    pix = QPixmap(12, 12)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(color))
    painter.drawPolygon(QPolygon([QPoint(2, 4), QPoint(10, 4), QPoint(6, 9)]))
    painter.end()

    cache_dir = Path(tempfile.gettempdir()) / "batch_stlink_flasher"
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"combo_down_{key}.png"
    pix.save(str(path), "PNG")
    _COMBO_ARROW_CACHE[key] = str(path)
    return path.as_posix()


def app_stylesheet(palette: ThemePalette | None = None) -> str:
    p = palette or active_palette()
    arrow = combo_down_arrow_url(p.text_muted)
    return f"""
    QWidget {{
        color: {p.text};
        background-color: {p.bg};
        font-size: 13px;
    }}
    QMainWindow, QDialog {{
        background-color: {p.bg};
        color: {p.text};
    }}
    QLabel {{
        background-color: transparent;
        color: {p.text};
    }}
    QLabel#mutedLabel {{
        color: {p.text_muted};
        font-size: 12px;
    }}
    QMenuBar {{
        background-color: {p.bg_elevated};
        color: {p.text};
        border-bottom: 1px solid {p.border};
        padding: 2px 4px;
    }}
    QMenuBar::item {{
        background: transparent;
        color: {p.text};
    }}
    QMenuBar::item:selected {{
        background-color: {p.bg_hover};
        border-radius: 4px;
    }}
    QMenu {{
        background-color: {p.bg_elevated};
        color: {p.text};
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
    QTabWidget::pane {{
        border: 1px solid {p.border};
        background-color: {p.bg};
        border-radius: 6px;
        top: -1px;
        padding: 8px;
    }}
    QTabBar::tab {{
        background-color: {p.bg_elevated};
        color: {p.text_muted};
        border: 1px solid {p.border};
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        padding: 6px 14px;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        background-color: {p.bg};
        color: {p.text};
        font-weight: 600;
    }}
    QTabBar::tab:hover:!selected {{
        color: {p.text};
        background-color: {p.bg_hover};
    }}
    QComboBox {{
        background-color: {p.bg_input};
        border: 1px solid {p.border};
        border-radius: 5px;
        padding: 3px 28px 3px 8px;
        min-height: 24px;
        color: {p.text};
    }}
    QComboBox:hover {{
        border-color: {p.accent};
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 22px;
        border: none;
        border-left: 1px solid {p.border};
        background: transparent;
    }}
    QComboBox::down-arrow {{
        image: url({arrow});
        width: 10px;
        height: 10px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {p.bg_elevated};
        color: {p.text};
        border: 1px solid {p.border};
        selection-background-color: {p.accent};
        selection-color: {p.text_on_accent};
        outline: 0;
    }}
    QDialogButtonBox {{
        background-color: transparent;
    }}
    QDialogButtonBox QPushButton {{
        min-width: 80px;
        padding: 5px 16px;
    }}
    QSplitter::handle {{
        background-color: {p.border};
        margin: 1px 4px;
    }}
    QSplitter::handle:horizontal {{
        width: 5px;
    }}
    QSplitter::handle:vertical {{
        height: 5px;
    }}
    QPushButton {{
        background-color: {p.bg_elevated};
        border: 1px solid {p.border};
        border-radius: 6px;
        padding: 4px 10px;
        min-height: 24px;
        color: {p.text};
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
    /* Path-row ellipsis — same chrome as other buttons, fixed square hit target */
    QPushButton#browseButton {{
        background-color: {p.bg_elevated};
        border: 1px solid {p.border};
        border-radius: 6px;
        padding: 0px;
        margin: 0px;
        min-width: 26px;
        max-width: 26px;
        min-height: 26px;
        max-height: 26px;
        font-size: 14px;
        font-weight: 600;
        color: {p.text};
    }}
    QPushButton#browseButton:hover {{
        border-color: {p.accent};
        background-color: {p.bg_hover};
    }}
    QPushButton#browseButton:pressed {{
        background-color: {p.bg_pressed};
    }}
    QPushButton#browseButton:disabled {{
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
        padding: 3px 6px;
        color: {p.text};
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
        color: {p.text};
    }}
    QHeaderView::section {{
        background-color: {p.bg_elevated};
        color: {p.text_muted};
        border: none;
        border-right: 1px solid {p.border};
        border-bottom: 1px solid {p.border};
        padding: 4px 6px;
        font-weight: 600;
    }}
    QTableWidget::item:selected {{
        background-color: {p.selection_bg};
        color: {p.text};
    }}
    QLabel#summaryLabel {{
        color: {p.text};
        font-weight: 700;
        font-size: 12px;
        padding: 0 8px;
    }}
    QLabel#toolsSummary {{
        color: {p.text_muted};
        font-size: 12px;
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


def build_qpalette(palette: ThemePalette | None = None) -> QPalette:
    """Fusion QPalette so dialogs / tabs match even where stylesheets skip a role."""
    p = palette or active_palette()
    qp = QPalette()
    window = QColor(p.bg)
    text = QColor(p.text)
    base = QColor(p.bg_input)
    button = QColor(p.bg_elevated)
    muted = QColor(p.text_muted)
    disabled = QColor(p.text_disabled)
    highlight = QColor(p.selection_bg)
    accent = QColor(p.accent)

    qp.setColor(QPalette.ColorRole.Window, window)
    qp.setColor(QPalette.ColorRole.WindowText, text)
    qp.setColor(QPalette.ColorRole.Base, base)
    qp.setColor(QPalette.ColorRole.AlternateBase, QColor(p.table_alt))
    qp.setColor(QPalette.ColorRole.ToolTipBase, button)
    qp.setColor(QPalette.ColorRole.ToolTipText, text)
    qp.setColor(QPalette.ColorRole.Text, text)
    qp.setColor(QPalette.ColorRole.Button, button)
    qp.setColor(QPalette.ColorRole.ButtonText, text)
    qp.setColor(QPalette.ColorRole.BrightText, QColor("#ffffff"))
    qp.setColor(QPalette.ColorRole.Link, accent)
    qp.setColor(QPalette.ColorRole.Highlight, highlight)
    qp.setColor(QPalette.ColorRole.HighlightedText, text)
    qp.setColor(QPalette.ColorRole.PlaceholderText, muted)

    for group in (QPalette.ColorGroup.Disabled, QPalette.ColorGroup.Inactive):
        qp.setColor(group, QPalette.ColorRole.WindowText, disabled)
        qp.setColor(group, QPalette.ColorRole.Text, disabled)
        qp.setColor(group, QPalette.ColorRole.ButtonText, disabled)
        qp.setColor(group, QPalette.ColorRole.Highlight, QColor(p.border))
        qp.setColor(group, QPalette.ColorRole.HighlightedText, muted)
    return qp


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
    """Apply Fusion style + palette + stylesheet for the resolved mode; return active palette."""
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
    app.setPalette(build_qpalette(palette))
    app.setStyleSheet(app_stylesheet(palette))
    icon = load_app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    clear_icon_cache()
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
    """Brand logo for splash / About (charcoal tile + chip)."""
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


def style_standard_icon_widget(widget: QWidget, standard: QStyle.StandardPixmap) -> QIcon:
    """Alias used when building QAction icons (same behaviour as style_standard_icon)."""
    return style_standard_icon(widget, standard)


# ---------------------------------------------------------------------------
# Theme-aware icon system using Papirus icon theme
# ---------------------------------------------------------------------------
# Icons live in assets/papirus/ (24x24 actions from Papirus).
# Each SVG uses CSS classes with a primary text color (#444444).
# themed_icon() replaces that color with the active palette's text color,
# renders the SVG in-memory via QSvgRenderer → QPixmap, and caches the QIcon.
# No temp files, no Qt SVG file-cache issues.
_ICON_CACHE: dict[str, QIcon] = {}

# Papirus SVGs use these color tokens; we only replace the text color.
_PAPIRUS_PRIMARY = "#444444"

# Map action names → Papirus SVG filenames (relative to assets/papirus/).
_PAPIRUS_ICONS: dict[str, str] = {
    "icon_refresh.svg": "view-refresh.svg",
    "icon_check_all.svg": "edit-select-all.svg",
    "icon_uncheck_all.svg": "edit-select-none.svg",
    "icon_identify.svg": "dialog-information.svg",
    "icon_settings.svg": "configure.svg",
    "icon_export.svg": "edit-download.svg",
    "icon_clear.svg": "edit-clear.svg",
    "icon_cancel.svg": "window-close.svg",
    "icon_flash.svg": "system-run.svg",
}


def _papirus_path(filename: str) -> Path:
    return Path(__file__).resolve().parent.parent / "assets" / "papirus" / filename


def themed_icon(name: str) -> QIcon:
    """Return a theme-aware QIcon from the Papirus icon set."""
    p = active_palette()
    cache_key = f"{name}|{p.text}"
    cached = _ICON_CACHE.get(cache_key)
    if cached is not None:
        return cached

    papirus_name = _PAPIRUS_ICONS.get(name)
    if papirus_name is None:
        return QIcon()

    src = _papirus_path(papirus_name)
    if not src.is_file():
        return QIcon()

    raw = src.read_text(encoding="utf-8")
    # Replace the primary text color with the active palette color.
    recolored = raw.replace(_PAPIRUS_PRIMARY, p.text)

    # Render to QPixmap via QSvgRenderer — no temp files, no caching bugs.
    from PySide6.QtSvg import QSvgRenderer
    from PySide6.QtCore import QByteArray

    renderer = QSvgRenderer(QByteArray(recolored.encode("utf-8")))
    size = 24
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    renderer.render(painter)
    painter.end()

    icon = QIcon(pix)
    _ICON_CACHE[cache_key] = icon
    return icon


def clear_icon_cache() -> None:
    """Drop cached themed icons (call when the palette changes)."""
    _ICON_CACHE.clear()


def create_browse_button(
    parent: QWidget | None = None,
    *,
    height: int = 26,
) -> QPushButton:
    """
    Path-row browse control labeled ``…``.

    Same fixed square size and objectName everywhere (main window + dialogs)
    so app stylesheet ``QPushButton#browseButton`` applies identically.
    """
    side = max(24, int(height))
    btn = QPushButton("…", parent)
    btn.setObjectName("browseButton")
    btn.setToolTip("Browse…")
    btn.setAccessibleName("Browse")
    btn.setAutoDefault(False)
    btn.setDefault(False)
    btn.setFlat(False)
    btn.setFixedSize(side, side)
    btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
    return btn


def decorate_button(
    button: QPushButton,
    *,
    standard: QStyle.StandardPixmap | None = None,
    role: str | None = None,
    icon_size: int = 16,
) -> None:
    """Attach a standard icon and optional objectName role (primary/danger)."""
    if standard is not None:
        # Never use SP_DirOpenIcon here — callers should use create_browse_button().
        button.setIcon(style_standard_icon(button, standard))
        button.setIconSize(QSize(icon_size, icon_size))
    if role == "primary":
        button.setObjectName("primaryButton")
    elif role == "danger":
        button.setObjectName("dangerButton")


def style_dialog_buttons(box) -> None:
    """Style a QDialogButtonBox: accept → primary, others → secondary."""
    from PySide6.QtWidgets import QDialogButtonBox as Dbb

    # Mark the accept button as primary so the stylesheet picks it up.
    accept = box.button(Dbb.StandardButton.Ok)
    if accept is not None:
        accept.setObjectName("primaryButton")
    # Save buttons also get primary treatment.
    save = box.button(Dbb.StandardButton.Save)
    if save is not None:
        save.setObjectName("primaryButton")
