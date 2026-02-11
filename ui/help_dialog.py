"""Yardim diyalogu - Uygulama ozellikleri, kullanim kilavuzu ve gelistirici bilgileri."""

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QWidget,
    QTextBrowser,
    QPushButton,
)

from config.settings import Settings
from .i18n import get_text


class HelpDialog(QDialog):
    """Yardim ve kullanim kilavuzu diyalogu."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = Settings()
        self._current_lang = self._settings.language

        self._setup_ui()
        self._update_ui_text()

    def _setup_ui(self):
        """Arayuz elemanlarini olusturur."""
        self.setMinimumSize(520, 480)
        layout = QVBoxLayout(self)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        # --- Baslangic sekmesi ---
        self._start_browser = self._make_browser()
        self._tabs.addTab(self._start_browser, "")

        # --- Ozellikler sekmesi ---
        self._features_browser = self._make_browser()
        self._tabs.addTab(self._features_browser, "")

        # --- Komutlar sekmesi ---
        self._commands_browser = self._make_browser()
        self._tabs.addTab(self._commands_browser, "")

        # --- Hakkinda sekmesi ---
        self._about_browser = self._make_browser()
        self._tabs.addTab(self._about_browser, "")

        # Kapat butonu
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._close_btn = QPushButton()
        self._close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self._close_btn)
        layout.addLayout(btn_layout)

    @staticmethod
    def _make_browser() -> QTextBrowser:
        """Ortak QTextBrowser olusturur."""
        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        browser.setOpenLinks(False)
        browser.anchorClicked.connect(lambda url: QDesktopServices.openUrl(url))
        return browser

    def _update_ui_text(self):
        """Arayuz metinlerini secili dile gore gunceller."""
        lang = self._current_lang

        self.setWindowTitle(get_text("help_title", lang))
        self._tabs.setTabText(0, get_text("help_tab_start", lang))
        self._tabs.setTabText(1, get_text("help_tab_features", lang))
        self._tabs.setTabText(2, get_text("help_tab_commands", lang))
        self._tabs.setTabText(3, get_text("help_tab_about", lang))

        self._start_browser.setHtml(get_text("help_content_start", lang))
        self._features_browser.setHtml(get_text("help_content_features", lang))
        self._commands_browser.setHtml(get_text("help_content_commands", lang))
        self._about_browser.setHtml(get_text("help_content_about", lang))

        self._close_btn.setText(get_text("help_close", lang))
