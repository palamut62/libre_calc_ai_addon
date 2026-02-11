"""Tema tanımları - Koyu ve açık tema Qt stil şablonları."""


DARK_THEME = """
QMainWindow, QDialog, QWidget#main_container {
    background-color: #0f172a;
    color: #e2e8f0;
}

QWidget {
    background-color: #0f172a;
    color: #e2e8f0;
    font-family: "Manrope", "Poppins", "Segoe UI", sans-serif;
    font-size: 13px;
}

/* Pencere Kenarlığı */
QWidget#main_container {
    border: 1px solid #1f2937;
}

QMenuBar {
    background-color: #0b1220;
    color: #cbd5e1;
    border-bottom: 1px solid #1f2937;
    padding: 4px;
}

QMenuBar::item:selected {
    background-color: #1f2937;
    color: #f8fafc;
}

QMenu {
    background-color: #0b1220;
    color: #e2e8f0;
    border: 1px solid #1f2937;
}

QMenu::item:selected {
    background-color: #22c55e;
    color: #0b1220;
}

QTabWidget#ribbon {
    background-color: #0b1220;
    border-bottom: 1px solid #1f2937;
}

QTabWidget#ribbon::pane {
    border: none;
}

QTabBar::tab {
    background-color: #0b1220;
    color: #cbd5e1;
    padding: 6px 12px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}

QTabBar::tab:selected {
    background-color: #111827;
    color: #ffffff;
}

QTabBar::tab:hover {
    background-color: #111827;
}

QToolButton {
    background-color: transparent;
    color: #cbd5e1;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 6px 10px;
}

QToolButton:hover {
    background-color: #111827;
    border: 1px solid #1f2937;
    color: #f8fafc;
}

QToolBar {
    background-color: #0b1220;
    border-bottom: 1px solid #1f2937;
    spacing: 10px;
    padding: 6px;
}

QPushButton {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #22c55e, stop:1 #16a34a);
    color: #0b1220;
    border: none;
    border-radius: 8px;
    padding: 6px 14px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #16a34a, stop:1 #15803d);
}

QLineEdit, QTextEdit, QPlainTextEdit, QTextBrowser {
    background-color: #0b1220;
    color: #e2e8f0;
    border: 1px solid #1f2937;
    border-radius: 8px;
    padding: 8px;
}

QLineEdit:focus {
    border: 1px solid #22c55e;
}

/* Custom Title Bar */
QFrame#custom_title_bar {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #22c55e, stop:1 #16a34a);
}

QLabel#title_label {
    background-color: transparent;
    color: #ffffff;
    font-weight: 700;
    letter-spacing: 0.4px;
}

QPushButton#title_min_btn, QPushButton#title_close_btn {
    background-color: transparent;
    color: #ffffff;
    border: none;
    font-size: 15px;
    font-weight: 700;
}

QPushButton#title_min_btn:hover {
    background-color: rgba(255, 255, 255, 0.18);
}

QPushButton#title_close_btn:hover {
    background-color: #e11d48;
}

QTextBrowser#user_bubble {
    background-color: #111827;
    color: #e2e8f0;
    border: 1px solid #1f2937;
    border-radius: 12px;
}

QTextBrowser#ai_bubble {
    background-color: #0b1220;
    color: #e2e8f0;
    border: 1px solid #22c55e;
    border-radius: 12px;
}

QFrame#custom_status_bar {
    background-color: #0b1220;
    border-top: 1px solid #1f2937;
}

QFrame#selection_preview {
    background-color: #0b1220;
    border-bottom: 1px solid #1f2937;
}

QLabel#selection_title {
    color: #22c55e;
    font-weight: 700;
}

QLabel#selection_stats, QLabel#selection_samples {
    color: #cbd5e1;
}
"""

LIGHT_THEME = """
QMainWindow, QDialog, QWidget#main_container {
    background-color: #f8fafc;
    color: #0f172a;
}

QWidget {
    background-color: #f8fafc;
    color: #0f172a;
    font-family: "Manrope", "Poppins", "Segoe UI", sans-serif;
    font-size: 13px;
}

/* Pencere Kenarlığı */
QWidget#main_container {
    border: 1px solid #e2e8f0;
}

QMenuBar {
    background-color: #f1f5f9;
    color: #0f172a;
    border-bottom: 1px solid #e2e8f0;
    padding: 4px;
}

QMenuBar::item:selected {
    background-color: #e2e8f0;
    color: #0f172a;
}

QMenu {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #e2e8f0;
}

QMenu::item:selected {
    background-color: #22c55e;
    color: #0f172a;
}

QTabWidget#ribbon {
    background-color: #f1f5f9;
    border-bottom: 1px solid #e2e8f0;
}

QTabWidget#ribbon::pane {
    border: none;
}

QTabBar::tab {
    background-color: #f1f5f9;
    color: #334155;
    padding: 6px 12px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}

QTabBar::tab:selected {
    background-color: #ffffff;
    color: #0f172a;
}

QTabBar::tab:hover {
    background-color: #ffffff;
}

QToolButton {
    background-color: transparent;
    color: #334155;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 6px 10px;
}

QToolButton:hover {
    background-color: #e2e8f0;
    border: 1px solid #cbd5e1;
}

QToolBar {
    background-color: #f1f5f9;
    border-bottom: 1px solid #e2e8f0;
    spacing: 10px;
    padding: 6px;
}

QPushButton {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #22c55e, stop:1 #16a34a);
    color: #0f172a;
    border: none;
    border-radius: 8px;
    padding: 6px 14px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #16a34a, stop:1 #15803d);
}

QLineEdit, QTextEdit, QPlainTextEdit, QTextBrowser {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 8px;
}

QLineEdit:focus {
    border: 1px solid #22c55e;
}

/* Custom Title Bar */
QFrame#custom_title_bar {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #22c55e, stop:1 #16a34a);
}

QLabel#title_label {
    background-color: transparent;
    color: #ffffff;
    font-weight: 700;
    letter-spacing: 0.4px;
}

QPushButton#title_min_btn, QPushButton#title_close_btn {
    background-color: transparent;
    color: #ffffff;
    border: none;
    font-size: 15px;
    font-weight: 700;
}

QPushButton#title_min_btn:hover {
    background-color: rgba(255, 255, 255, 0.18);
}

QPushButton#title_close_btn:hover {
    background-color: #e11d48;
}

QTextBrowser#user_bubble {
    background-color: #f1f5f9;
    color: #0f172a;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
}

QTextBrowser#ai_bubble {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #22c55e;
    border-radius: 12px;
}

QFrame#custom_status_bar {
    background-color: #f1f5f9;
    border-top: 1px solid #e2e8f0;
}

QFrame#selection_preview {
    background-color: #f1f5f9;
    border-bottom: 1px solid #e2e8f0;
}

QLabel#selection_title {
    color: #16a34a;
    font-weight: 700;
}

QLabel#selection_stats, QLabel#selection_samples {
    color: #334155;
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
