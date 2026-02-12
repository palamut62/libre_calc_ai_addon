"""Uygulama ikonları yönetimi."""

from pathlib import Path

from PyQt5.QtCore import QByteArray, Qt
from PyQt5.QtGui import QIcon, QPainter, QPixmap
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QStyle, QWidget

# İkon dosyalarının bulunduğu dizin
ICONS_DIR = Path(__file__).parent.parent / "assets" / "icons"

# İkon isimleri ve dosya eşleştirmesi
ICON_MAP = {
    "connect": "connect.svg",
    "analyze": "analyze.svg",
    "formula": "formula.svg",
    "profile": "profile.svg",
    "error": "error.svg",
    "history": "history.svg",
    "undo": "undo.svg",
    "save": "save.svg",
    "open": "open.svg",
    "export": "export.svg",
    "clear": "clear.svg",
    "send": "send.svg",
    "stop": "stop.svg",
    "menu": "menu.svg",
    "settings": "settings.svg",
    "info": "info.svg",
}

# Fallback ikonları (özel ikon bulunamazsa)
FALLBACK_ICONS = {
    "connect": QStyle.SP_DriveNetIcon,
    "analyze": QStyle.SP_FileDialogDetailedView,
    "formula": QStyle.SP_DialogApplyButton,
    "profile": QStyle.SP_FileDialogContentsView,
    "error": QStyle.SP_MessageBoxWarning,
    "history": QStyle.SP_FileDialogInfoView,
    "undo": QStyle.SP_ArrowBack,
    "save": QStyle.SP_DialogSaveButton,
    "open": QStyle.SP_DialogOpenButton,
    "export": QStyle.SP_FileDialogStart,
    "clear": QStyle.SP_TrashIcon,
    "send": QStyle.SP_ArrowRight,
    "stop": QStyle.SP_MediaStop,
    "menu": QStyle.SP_TitleBarMenuButton,
    "settings": QStyle.SP_ComputerIcon,
    "info": QStyle.SP_MessageBoxInformation,
}


def _build_colored_svg_icon(icon_path: Path, color: str) -> QIcon:
    """SVG dosyasını belirtilen renkte QIcon'a dönüştürür."""
    try:
        svg_text = icon_path.read_text(encoding="utf-8")
    except OSError:
        return QIcon(str(icon_path))

    svg_text = svg_text.replace("currentColor", color)
    renderer = QSvgRenderer(QByteArray(svg_text.encode("utf-8")))
    if not renderer.isValid():
        return QIcon(str(icon_path))

    icon = QIcon()
    for size in (14, 16, 20, 24, 28, 32):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        icon.addPixmap(pixmap)
    return icon


def get_icon(name: str, widget: QWidget = None, color: str = "") -> QIcon:
    """İkon adına göre QIcon döndürür.

    Args:
        name: İkon adı (örn: "connect", "save").
        widget: Fallback ikonu için widget (opsiyonel).

    Returns:
        QIcon nesnesi.
    """
    if name in ICON_MAP:
        icon_path = ICONS_DIR / ICON_MAP[name]
        if icon_path.exists():
            if color and icon_path.suffix.lower() == ".svg":
                return _build_colored_svg_icon(icon_path, color)
            return QIcon(str(icon_path))

    # Fallback: Qt standart ikonu
    if widget and name in FALLBACK_ICONS:
        return widget.style().standardIcon(FALLBACK_ICONS[name])

    return QIcon()


def get_icon_path(name: str) -> str:
    """İkon dosya yolunu döndürür.

    Args:
        name: İkon adı.

    Returns:
        Dosya yolu veya boş string.
    """
    if name in ICON_MAP:
        icon_path = ICONS_DIR / ICON_MAP[name]
        if icon_path.exists():
            return str(icon_path)
    return ""
