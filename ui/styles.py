"""Tema tanımları - Koyu ve açık tema Qt stil şablonları."""


DARK_THEME = """
QMainWindow, QDialog, QWidget#main_container {
    background-color: #0f1115;
    color: #e6edf3;
}

QWidget {
    background-color: #0f1115;
    color: #e6edf3;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}

QWidget#main_container {
    border: 1px solid #252b36;
}

QLabel#dialog_title {
    color: #e6edf3;
    font-size: 17px;
    font-weight: 700;
    padding: 6px 2px 0 2px;
}

QLabel#dialog_subtitle {
    color: #8b98aa;
    padding: 0 2px 8px 2px;
}

QLabel#help_section_title {
    color: #d7e2f0;
}

QLabel#help_section_content {
    color: #c2ccda;
}

QDialog QTabWidget::pane {
    border: 1px solid #2a303b;
    border-radius: 8px;
    background: #121821;
    top: -1px;
}

QDialog QTabBar::tab {
    background: #171d27;
    color: #bcc6d4;
    border: 1px solid #2a303b;
    padding: 7px 12px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}

QDialog QTabBar::tab:selected {
    background: #202a38;
    color: #e6edf3;
}

QDialog QGroupBox {
    border: 1px solid #2a303b;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
    background: #111722;
}

QDialog QGroupBox::title {
    color: #d3deeb;
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}

QDialog QComboBox {
    background: #111722;
    color: #e6edf3;
    border: 1px solid #2e3644;
    border-radius: 6px;
    padding: 4px 8px;
}

QDialog QComboBox::drop-down {
    border: none;
    width: 18px;
}

QDialog QComboBox QAbstractItemView {
    background: #171b22;
    color: #e6edf3;
    border: 1px solid #2a303b;
    selection-background-color: #2f81f7;
    selection-color: #ffffff;
}

QDialog QSpinBox, QDialog QDoubleSpinBox {
    background: #111722;
    color: #e6edf3;
    border: 1px solid #2e3644;
    border-radius: 6px;
    padding: 4px 8px;
}

QDialog QSpinBox::up-button, QDialog QSpinBox::down-button,
QDialog QDoubleSpinBox::up-button, QDialog QDoubleSpinBox::down-button {
    width: 16px;
    border: none;
    background: #1a2230;
}

QDialog QCheckBox, QDialog QRadioButton {
    color: #d0d8e4;
}

QDialog QCheckBox::indicator, QDialog QRadioButton::indicator {
    width: 14px;
    height: 14px;
}

QDialog QCheckBox::indicator {
    border: 1px solid #3a4658;
    border-radius: 3px;
    background: #111722;
}

QDialog QCheckBox::indicator:checked {
    background: #2f81f7;
    border-color: #2f81f7;
}

QDialog QRadioButton::indicator {
    border: 1px solid #3a4658;
    border-radius: 7px;
    background: #111722;
}

QDialog QRadioButton::indicator:checked {
    background: #2f81f7;
    border-color: #2f81f7;
}

QMessageBox {
    background-color: #0f1115;
    color: #e6edf3;
}

QLabel#tool_warning_label {
    color: #f0ad4e;
    padding: 8px;
    background: rgba(240, 173, 78, 0.14);
    border-radius: 6px;
    border: 1px solid rgba(240, 173, 78, 0.32);
}

QMenuBar {
    background-color: #171b22;
    color: #e6edf3;
    border-bottom: 1px solid #2a303b;
    padding: 4px;
}

QMenuBar::item:selected {
    background-color: #232a35;
    border-radius: 4px;
}

QMenu {
    background-color: #171b22;
    color: #e6edf3;
    border: 1px solid #2a303b;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #2f81f7;
    color: #ffffff;
}

QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #323a46;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #465062;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QToolBar {
    background-color: #10141a;
    border-bottom: 1px solid #2a303b;
    spacing: 8px;
    padding: 8px;
}

QPushButton {
    background-color: #202632;
    color: #c9d1d9;
    border: 1px solid #2e3644;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #2b3442;
    border-color: #3a4658;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #1a202a;
}

QLineEdit, QTextEdit, QPlainTextEdit, QTextBrowser {
    background-color: #111722;
    color: #e6edf3;
    border: 1px solid #2e3644;
    border-radius: 10px;
    padding: 8px;
}

QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #2f81f7;
}

QFrame#custom_title_bar {
    background-color: #0f1115;
    border-bottom: 1px solid #252b36;
}

QLabel#title_label {
    background-color: transparent;
    color: #d8dee9;
    font-weight: 600;
    font-size: 14px;
}

QPushButton#top_min_btn, QPushButton#top_close_btn {
    background-color: transparent;
    color: #c3ccd8;
    border: none;
    border-radius: 6px;
    padding: 0;
    font-size: 14px;
    font-weight: 500;
}

QPushButton#top_min_btn:hover, QPushButton#top_close_btn:hover {
    background-color: #202632;
    color: #e6edf3;
}

QPushButton#top_close_btn:hover {
    background-color: #d73a49;
    color: #ffffff;
}

QFrame#top_toolbar {
    background-color: transparent;
    border: none;
}

QPushButton#toolbar_btn {
    background-color: transparent;
    color: #c3ccd8;
    border: none;
    border-radius: 6px;
    padding: 0;
    font-size: 14px;
}

QPushButton#toolbar_btn:hover {
    background-color: #202632;
    color: #e6edf3;
}

QTextBrowser#user_bubble {
    background-color: #1f2a3a;
    color: #e6edf3;
    border: 1px solid #3a4c68;
    border-top-left-radius: 12px;
    border-top-right-radius: 4px;
    border-bottom-left-radius: 12px;
    border-bottom-right-radius: 12px;
    padding: 10px 12px;
}

QTextBrowser#ai_bubble {
    background-color: #171d2a;
    color: #e6edf3;
    border: 1px solid #323b4c;
    border-top-left-radius: 4px;
    border-top-right-radius: 12px;
    border-bottom-left-radius: 12px;
    border-bottom-right-radius: 12px;
    padding: 10px 12px;
}

QLabel#loading_label {
    color: #7f8b99;
    font-size: 12px;
    padding: 2px 2px;
    background: transparent;
}

QFrame#input_container {
    background-color: #161b24;
    border: 1px solid #2a303b;
    border-radius: 14px;
}

QFrame#input_container QTextEdit {
    background-color: transparent;
    border: none;
    border-radius: 0;
    padding: 0;
}

QPushButton#action_btn {
    background-color: transparent;
    color: #c5dcff;
    border: 1px solid transparent;
    border-radius: 16px;
    padding: 0;
}

QPushButton#action_btn:hover {
    background-color: #202632;
    color: #d7e7ff;
}

QPushButton#input_icon_btn {
    background-color: transparent;
    color: #bcc6d4;
    border: none;
    border-radius: 6px;
    padding: 0;
    font-size: 13px;
}

QPushButton#input_icon_btn:hover {
    background-color: #202632;
    color: #e2e8f0;
}

QLabel#model_chip {
    background-color: #1b2432;
    color: #d2d9e4;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
    border: 1px solid #2d3644;
}

QLabel#recent_title {
    color: #cbd5e1;
    font-size: 13px;
    font-weight: 600;
}

QLabel#recent_action_item {
    color: #d7e2f0;
    background-color: #111722;
    border: 1px solid #2a303b;
    border-radius: 10px;
    padding: 10px 12px;
}

QFrame#custom_status_bar {
    background-color: #0f1115;
    border-top: 1px solid #252b36;
    color: #8b949e;
}

QLabel#lo_status_label[state="ok"], QLabel#llm_status_label[state="ok"] {
    color: #3fb950;
    font-weight: 600;
}

QLabel#lo_status_label[state="error"], QLabel#llm_status_label[state="error"] {
    color: #f85149;
    font-weight: 600;
}
"""

LIGHT_THEME = """
QMainWindow, QDialog, QWidget#main_container {
    background-color: #f3f3f3;
    color: #1f2328;
}

QWidget {
    background-color: #f3f3f3;
    color: #1f2328;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}

QWidget#main_container {
    border: 1px solid #d0d7de;
}

QLabel#dialog_title {
    color: #1f2328;
    font-size: 17px;
    font-weight: 700;
    padding: 6px 2px 0 2px;
}

QLabel#dialog_subtitle {
    color: #6e7781;
    padding: 0 2px 8px 2px;
}

QLabel#help_section_title {
    color: #24292f;
}

QLabel#help_section_content {
    color: #3f4852;
}

QDialog QTabWidget::pane {
    border: 1px solid #d0d7de;
    border-radius: 8px;
    background: #ffffff;
    top: -1px;
}

QDialog QTabBar::tab {
    background: #f6f8fa;
    color: #57606a;
    border: 1px solid #d0d7de;
    padding: 7px 12px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}

QDialog QTabBar::tab:selected {
    background: #eaf2ff;
    color: #1f2328;
}

QDialog QGroupBox {
    border: 1px solid #d0d7de;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
    background: #ffffff;
}

QDialog QGroupBox::title {
    color: #24292f;
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}

QDialog QComboBox {
    background: #ffffff;
    color: #24292f;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 4px 8px;
}

QDialog QComboBox::drop-down {
    border: none;
    width: 18px;
}

QDialog QComboBox QAbstractItemView {
    background: #ffffff;
    color: #24292f;
    border: 1px solid #d0d7de;
    selection-background-color: #dbeafe;
    selection-color: #1f2328;
}

QDialog QSpinBox, QDialog QDoubleSpinBox {
    background: #ffffff;
    color: #24292f;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 4px 8px;
}

QDialog QSpinBox::up-button, QDialog QSpinBox::down-button,
QDialog QDoubleSpinBox::up-button, QDialog QDoubleSpinBox::down-button {
    width: 16px;
    border: none;
    background: #f6f8fa;
}

QDialog QCheckBox, QDialog QRadioButton {
    color: #24292f;
}

QDialog QCheckBox::indicator, QDialog QRadioButton::indicator {
    width: 14px;
    height: 14px;
}

QDialog QCheckBox::indicator {
    border: 1px solid #8c959f;
    border-radius: 3px;
    background: #ffffff;
}

QDialog QCheckBox::indicator:checked {
    background: #0969da;
    border-color: #0969da;
}

QDialog QRadioButton::indicator {
    border: 1px solid #8c959f;
    border-radius: 7px;
    background: #ffffff;
}

QDialog QRadioButton::indicator:checked {
    background: #0969da;
    border-color: #0969da;
}

QMessageBox {
    background-color: #f3f3f3;
    color: #1f2328;
}

QLabel#tool_warning_label {
    color: #9a6700;
    padding: 8px;
    background: rgba(154, 103, 0, 0.10);
    border-radius: 6px;
    border: 1px solid rgba(154, 103, 0, 0.24);
}

QMenuBar {
    background-color: #f3f3f3;
    color: #24292f;
    border-bottom: 1px solid #d0d7de;
    padding: 4px;
}

QMenuBar::item:selected {
    background-color: #eaeef2;
    border-radius: 4px;
}

QMenu {
    background-color: #ffffff;
    color: #24292f;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #dbeafe;
    color: #1f2328;
}

QLineEdit, QTextEdit, QPlainTextEdit, QTextBrowser {
    background-color: #ffffff;
    color: #1f2328;
    border: 1px solid #d0d7de;
    border-radius: 10px;
    padding: 8px;
}

QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #0969da;
}

QFrame#custom_title_bar {
    background-color: #f3f3f3;
    border-bottom: 1px solid #d0d7de;
}

QLabel#title_label {
    background-color: transparent;
    color: #24292f;
    font-weight: 600;
    font-size: 14px;
}

QPushButton#top_min_btn, QPushButton#top_close_btn {
    background-color: transparent;
    color: #57606a;
    border: none;
    border-radius: 6px;
    padding: 0;
    font-size: 14px;
    font-weight: 500;
}

QPushButton#top_min_btn:hover, QPushButton#top_close_btn:hover {
    background-color: #eaeef2;
    color: #24292f;
}

QPushButton#top_close_btn:hover {
    background-color: #cf222e;
    color: #ffffff;
}

QFrame#top_toolbar {
    background-color: transparent;
    border: none;
}

QPushButton#toolbar_btn {
    background-color: transparent;
    color: #57606a;
    border: none;
    border-radius: 6px;
    padding: 0;
    font-size: 14px;
}

QPushButton#toolbar_btn:hover {
    background-color: #eaeef2;
    color: #24292f;
}

QTextBrowser#user_bubble {
    background-color: #dcecff;
    color: #1f2328;
    border: 1px solid #b7d0f8;
    border-top-left-radius: 12px;
    border-top-right-radius: 4px;
    border-bottom-left-radius: 12px;
    border-bottom-right-radius: 12px;
    padding: 10px 12px;
}

QTextBrowser#ai_bubble {
    background-color: #f2f5f9;
    color: #1f2328;
    border: 1px solid #d6dde5;
    border-top-left-radius: 4px;
    border-top-right-radius: 12px;
    border-bottom-left-radius: 12px;
    border-bottom-right-radius: 12px;
    padding: 10px 12px;
}

QLabel#loading_label {
    color: #6e7781;
    font-size: 12px;
    padding: 2px 2px;
    background: transparent;
}

QFrame#input_container {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 14px;
}

QFrame#input_container QTextEdit {
    background-color: transparent;
    border: none;
    border-radius: 0;
    padding: 0;
}

QPushButton#action_btn {
    background-color: transparent;
    color: #0969da;
    border: 1px solid transparent;
    border-radius: 16px;
    padding: 0;
}

QPushButton#action_btn:hover {
    background-color: #eaf2ff;
    color: #0550ae;
}

QPushButton#input_icon_btn {
    background-color: transparent;
    color: #6e7781;
    border: none;
    border-radius: 6px;
    padding: 0;
}

QPushButton#input_icon_btn:hover {
    background-color: #eaeef2;
    color: #24292f;
}

QLabel#model_chip {
    background-color: #f6f8fa;
    color: #57606a;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
    border: 1px solid #d0d7de;
}

QLabel#recent_title {
    color: #57606a;
    font-size: 13px;
    font-weight: 600;
}

QLabel#recent_action_item {
    color: #24292f;
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 10px;
    padding: 10px 12px;
}

QFrame#custom_status_bar {
    background-color: #f3f3f3;
    border-top: 1px solid #d0d7de;
    color: #57606a;
}

QLabel#lo_status_label[state="ok"], QLabel#llm_status_label[state="ok"] {
    color: #1a7f37;
    font-weight: 600;
}

QLabel#lo_status_label[state="error"], QLabel#llm_status_label[state="error"] {
    color: #cf222e;
    font-weight: 600;
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
