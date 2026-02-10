"""Tema tanımları - Koyu ve açık tema Qt stil şablonları."""


DARK_THEME = """
QMainWindow, QDialog, QWidget#main_container {
    background-color: #1e1e1e;
    color: #f3f4f6;
}

QWidget {
    background-color: #1e1e1e;
    color: #f3f4f6;
    font-family: "Segoe UI", "Tahoma", sans-serif;
    font-size: 13px;
}

/* Pencere Kenarlığı */
QWidget#main_container {
    border: 1px solid #333333;
}

QMenuBar {
    background-color: #1e1e1e;
    color: #d1d5db;
    border-bottom: 1px solid #333333;
    padding: 2px;
}

QMenuBar::item:selected {
    background-color: #333333;
    color: #ffffff;
}

QMenu {
    background-color: #262626;
    color: #f3f4f6;
    border: 1px solid #404040;
}

QMenu::item:selected {
    background-color: #18a303;
    color: #ffffff;
}

QToolBar {
    background-color: #1e1e1e;
    border-bottom: 1px solid #333333;
    spacing: 12px;
    padding: 4px;
}

QToolButton {
    background-color: transparent;
    color: #d1d5db;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 6px 14px;
}

QToolButton:hover {
    background-color: #333333;
    border: 1px solid #404040;
}

QPushButton {
    background-color: #18a303;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 6px 14px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #1eb904;
}

QLineEdit, QTextEdit, QPlainTextEdit, QTextBrowser {
    background-color: #262626;
    color: #f3f4f6;
    border: 1px solid #404040;
    border-radius: 4px;
    padding: 8px;
}

QLineEdit:focus {
    border: 1px solid #18a303;
}

/* Custom Title Bar */
QFrame#custom_title_bar {
    background-color: #18a303;
}

QLabel#title_label {
    background-color: transparent;
    color: #ffffff;
    font-weight: bold;
}

QPushButton#title_min_btn, QPushButton#title_close_btn {
    background-color: transparent;
    color: #ffffff;
    border: none;
    font-size: 16px;
    font-weight: bold;
}

QPushButton#title_min_btn:hover {
    background-color: rgba(255, 255, 255, 0.2);
}

QPushButton#title_close_btn:hover {
    background-color: #e81123;
}

QTextBrowser#user_bubble {
    background-color: #262626;
    color: #f3f4f6;
    border: 1px solid #404040;
    border-radius: 10px;
}

QTextBrowser#ai_bubble {
    background-color: #2c2c2c;
    color: #f3f4f6;
    border: 1px solid #18a303;
    border-radius: 10px;
}

QFrame#custom_status_bar {
    background-color: #2c2c2c;
    border-top: 1px solid #333333;
}
"""

LIGHT_THEME = """
QMainWindow, QDialog, QWidget#main_container {
    background-color: #f3f4f6;
    color: #111827;
}

QWidget {
    background-color: #f3f4f6;
    color: #111827;
    font-family: "Segoe UI", "Tahoma", sans-serif;
    font-size: 13px;
}

/* Pencere Kenarlığı */
QWidget#main_container {
    border: 1px solid #d1d5db;
}

QMenuBar {
    background-color: #f3f4f6;
    color: #111827;
    border-bottom: 1px solid #d1d5db;
    padding: 2px;
}

QMenuBar::item:selected {
    background-color: #e5e7eb;
    color: #111827;
}

QMenu {
    background-color: #ffffff;
    color: #111827;
    border: 1px solid #d1d5db;
}

QMenu::item:selected {
    background-color: #18a303;
    color: #ffffff;
}

QToolBar {
    background-color: #f3f4f6;
    border-bottom: 1px solid #d1d5db;
    spacing: 12px;
    padding: 4px;
}

QToolButton {
    background-color: transparent;
    color: #4b5563;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 6px 14px;
}

QToolButton:hover {
    background-color: #e5e7eb;
    border: 1px solid #d1d5db;
}

QPushButton {
    background-color: #18a303;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 6px 14px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #1eb904;
}

QLineEdit, QTextEdit, QPlainTextEdit, QTextBrowser {
    background-color: #ffffff;
    color: #111827;
    border: 1px solid #d1d5db;
    border-radius: 4px;
    padding: 8px;
}

QLineEdit:focus {
    border: 1px solid #18a303;
}

/* Custom Title Bar */
QFrame#custom_title_bar {
    background-color: #18a303;
}

QLabel#title_label {
    background-color: transparent;
    color: #ffffff;
    font-weight: bold;
}

QPushButton#title_min_btn, QPushButton#title_close_btn {
    background-color: transparent;
    color: #ffffff;
    border: none;
    font-size: 16px;
    font-weight: bold;
}

QPushButton#title_min_btn:hover {
    background-color: rgba(255, 255, 255, 0.2);
}

QPushButton#title_close_btn:hover {
    background-color: #e81123;
}

QTextBrowser#user_bubble {
    background-color: #e5e7eb;
    color: #111827;
    border: 1px solid #d1d5db;
    border-radius: 10px;
}

QTextBrowser#ai_bubble {
    background-color: #ffffff;
    color: #111827;
    border: 1px solid #18a303;
    border-radius: 10px;
}

QFrame#custom_status_bar {
    background-color: #f3f4f6;
    border-top: 1px solid #d1d5db;
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
