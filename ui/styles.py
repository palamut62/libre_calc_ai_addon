"""Tema tanımları - Koyu ve açık tema Qt stil şablonları."""


DARK_THEME = """
QMainWindow, QDialog {
    background-color: #1a1a1a;
    color: #e5e7eb;
}

QWidget {
    background-color: #1a1a1a;
    color: #e5e7eb;
    font-family: "Inter", "Segoe UI", "Noto Sans", sans-serif;
    font-size: 13px;
}

QMenuBar {
    background-color: #1a1a1a;
    color: #e5e7eb;
    border-bottom: 1px solid #333333;
}

QMenuBar::item:selected {
    background-color: #2d2d2d;
}

QMenu {
    background-color: #1a1a1a;
    color: #e5e7eb;
    border: 1px solid #333333;
}

QMenu::item:selected {
    background-color: #D97757;
    color: #ffffff;
}

QToolBar {
    background-color: #1a1a1a;
    border-bottom: 1px solid #333333;
    spacing: 8px;
    padding: 6px;
}

QToolButton {
    background-color: transparent;
    color: #e5e7eb;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 6px 10px;
}

QToolButton:hover {
    background-color: #2d2d2d;
}

QPushButton {
    background-color: #D97757;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #e68a6d;
}

QPushButton:pressed {
    background-color: #c4664a;
}

QPushButton:disabled {
    background-color: #333333;
    color: #6b7280;
}

QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #2d2d2d;
    color: #e5e7eb;
    border: 1px solid #404040;
    border-radius: 8px;
    padding: 8px;
    selection-background-color: #D97757;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #D97757;
}

QGroupBox {
    border: 1px solid #333333;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #D97757;
}

QTabWidget::pane {
    border: 1px solid #333333;
    background-color: #1a1a1a;
}

QTabBar::tab {
    background-color: #1a1a1a;
    color: #9ca3af;
    border: none;
    padding: 8px 16px;
    margin-right: 4px;
}

QTabBar::tab:selected {
    color: #D97757;
    border-bottom: 2px solid #D97757;
}

QScrollBar:vertical {
    background-color: #1a1a1a;
    width: 8px;
}

QScrollBar::handle:vertical {
    background-color: #404040;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background-color: #525252;
}

QSplitter::handle {
    background-color: #333333;
    height: 1px;
}

QLabel#user_bubble {
    background-color: #2d2d2d;
    color: #e5e7eb;
    border-radius: 12px;
    padding: 10px 14px;
    border: 1px solid #404040;
}

QLabel#ai_bubble {
    background-color: transparent;
    color: #e5e7eb;
    padding: 10px 0px;
}

QLabel#loading_label {
    color: #9ca3af;
    font-style: italic;
    padding: 4px;
}

QLabel#error_label {
    background-color: rgba(220, 38, 38, 0.1);
    color: #ef4444;
    border: 1px solid rgba(220, 38, 38, 0.2);
    border-radius: 8px;
    padding: 10px;
}
"""


LIGHT_THEME = """
QMainWindow, QDialog {
    background-color: #ffffff;
    color: #1f2937;
}

QWidget {
    background-color: #ffffff;
    color: #1f2937;
    font-family: "Inter", "Segoe UI", "Noto Sans", sans-serif;
    font-size: 13px;
}

QMenuBar {
    background-color: #ffffff;
    color: #1f2937;
    border-bottom: 1px solid #e5e7eb;
}

QPushButton {
    background-color: #D97757;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
}

QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #f9fafb;
    color: #1f2937;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 8px;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #D97757;
}

QLabel#user_bubble {
    background-color: #f3f4f6;
    color: #1f2937;
    border-radius: 12px;
    padding: 10px 14px;
    border: 1px solid #e5e7eb;
}

QLabel#ai_bubble {
    background-color: transparent;
    color: #1f2937;
    padding: 10px 0px;
}
"""


_THEMES = {
    "dark": DARK_THEME,
    "light": LIGHT_THEME,
}


def get_theme(name: str) -> str:
    """Belirtilen tema adina gore stil sablonunu dondurur.

    Args:
        name: Tema adi ("dark" veya "light").

    Returns:
        Qt stylesheet dizesi.
    """
    return _THEMES.get(name, DARK_THEME)
