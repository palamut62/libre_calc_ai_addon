"""Ana uygulama penceresi - Tum UI bilesenlerini bir araya getirir."""

import json
import logging
import re
import subprocess

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QMainWindow,
    QSplitter,
    QAction,
    QActionGroup,
    QToolBar,
    QToolButton,
    QLabel,
    QMessageBox,
    QApplication,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QFrame,
    QMenuBar,
    QMenu,
    QTabWidget,
    QFileDialog,
)
from PyQt5.QtGui import QTextDocument

from config.settings import Settings
from core import LibreOfficeBridge, CellInspector, CellManipulator, SheetAnalyzer, ErrorDetector, LibreOfficeEventListener
from llm import OpenRouterProvider, OllamaProvider, GeminiProvider
from llm.tool_definitions import TOOLS, ToolDispatcher
from llm.prompt_templates import SYSTEM_PROMPT

from .chat_widget import ChatWidget
from .settings_dialog import SettingsDialog
from .styles import get_theme
from .i18n import get_text
from .icons import get_icon


logger = logging.getLogger(__name__)

# Bellek yönetimi sabitleri
MAX_CONVERSATION_MESSAGES = 100  # Maksimum mesaj sayısı (aşılırsa özetleme tetiklenir)


class LLMWorker(QThread):
    """Arka plan is parcaciginda LLM isteklerini calistirir.

    Ana arayuzun donmasini onlemek icin LLM cagrilarini
    ayri bir QThread'de yurutur.
    """

    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, provider, messages, tools=None, parent=None):
        super().__init__(parent)
        self._provider = provider
        self._messages = messages
        self._tools = tools

    def run(self):
        """LLM sohbet tamamlama istegini calistirir."""
        try:
            result = self._provider.chat_completion(self._messages, self._tools)
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class LLMStreamWorker(QThread):
    """Arka plan is parcaciginda LLM stream isteklerini calistirir."""

    chunk = pyqtSignal(dict)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, provider, messages, tools=None, parent=None):
        super().__init__(parent)
        self._provider = provider
        self._messages = messages
        self._tools = tools

    def run(self):
        try:
            if self.isInterruptionRequested():
                self.finished.emit()
                return
            for part in self._provider.stream_completion(self._messages, self._tools):
                if self.isInterruptionRequested():
                    self.finished.emit()
                    return
                self.chunk.emit(part)
                if part.get("done"):
                    break
            self.finished.emit()
        except Exception as exc:
            self.error.emit(str(exc))


class MainWindow(QMainWindow):
    """Ana uygulama penceresi.

    Sohbet arayuzu, hucre bilgi paneli, menu cubugu, arac cubugu
    ve durum cubugunu icerir.
    """

    def __init__(self, skip_lo_connect: bool = False):
        super().__init__()
        self._settings = Settings()
        self._bridge = None
        self._provider = None
        self._dispatcher = None
        self._conversation = []
        self._worker = None
        self._stream_worker = None
        self._pending_tool_calls = []
        self._skip_lo_connect = skip_lo_connect
        self._stream_content = ""
        self._stream_tool_calls_indexed = {}
        self._stream_tool_calls_full = []
        self._stream_has_tool_calls = False
        self._stream_started = False
        self._last_prompt_tokens_est = 0
        self._conversation_summary = ""
        self._is_summarizing = False
        self._change_log = []
        self._is_undoing = False
        self._mask_sensitive = True
        self._tool_confirm_always = False
        
        # Dil ayarı
        self._current_lang = self._settings.language

        self._setup_window()
        self._init_actions()
        self._setup_ui()
        self._apply_theme()
        self._init_provider()
        
        # Metinleri guncelle
        self._update_ui_text()

        # Başlangıçta otomatik LO bağlantısı dene
        if not self._skip_lo_connect:
            if self._connect_lo_silent():
                self._chat_widget.add_message(
                    "assistant",
                    get_text("msg_lo_connected", self._current_lang)
                )
            else:
                self._chat_widget.add_message(
                    "assistant",
                    get_text("msg_lo_not_connected", self._current_lang)
                )
        else:
            self._chat_widget.add_message(
                "assistant",
                get_text("msg_test_mode", self._current_lang)
            )

        # LibreCalc penceresini ekranın sol tarafına yerleştir
        if not self._skip_lo_connect:
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(2000, self._position_libreoffice_window)

    def _update_ui_text(self):
        """Arayuz metinlerini secili dile gore gunceller."""
        lang = self._current_lang
        
        # Pencere basligi
        self.setWindowTitle(get_text("window_title", lang))
        self.findChild(QLabel, "title_label").setText(get_text("window_title", lang))
        
        # Menuler
        self._file_menu.setTitle(get_text("menu_file", lang))
        self._settings_action.setText(get_text("menu_settings", lang))
        self._quit_action.setText(get_text("menu_quit", lang))
        
        self._provider_menu.setTitle(get_text("menu_provider", lang))
        
        self._view_menu.setTitle(get_text("menu_view", lang))
        self._theme_menu.setTitle(get_text("menu_theme", lang))
        self._action_light.setText(get_text("theme_light", lang))
        self._action_dark.setText(get_text("theme_dark", lang))
        self._action_system_theme.setText(get_text("theme_system", lang))
        
        self._lang_menu.setTitle(get_text("menu_language", lang))
        self._action_lang_tr.setText(get_text("lang_tr", lang))
        self._action_lang_en.setText(get_text("lang_en", lang))
        self._action_lang_system.setText(get_text("lang_system", lang))
        
        self._always_on_top_action.setText(get_text("menu_always_on_top", lang))
        
        self._help_menu.setTitle(get_text("menu_help", lang))
        self._about_action.setText(get_text("menu_about", lang))
        
        # Ribbon
        self._connect_action.setText(get_text("toolbar_connect", lang))
        self._connect_action.setToolTip(get_text("toolbar_connect_tooltip", lang))
        self._analyze_action.setText(get_text("toolbar_analyze", lang))
        self._analyze_action.setToolTip(get_text("toolbar_analyze_tooltip", lang))
        self._quick_actions_btn.setText(get_text("toolbar_quick_actions", lang))
        self._quick_actions_btn.setToolTip(get_text("toolbar_quick_actions", lang))
        self._quick_actions_menu.setTitle(get_text("toolbar_quick_actions", lang))
        self._quick_clear_action.setText(get_text("toolbar_quick_clear", lang))
        self._quick_fill_action.setText(get_text("toolbar_quick_fill", lang))
        self._quick_format_action.setText(get_text("toolbar_quick_format", lang))
        self._quick_table_action.setText(get_text("toolbar_quick_table", lang))
        self._quick_header_action.setText(get_text("toolbar_quick_header", lang))
        self._quick_outlier_action.setText(get_text("toolbar_quick_outliers", lang))
        self._clean_trim_action.setText(get_text("toolbar_clean_trim", lang))
        self._clean_number_action.setText(get_text("toolbar_clean_number", lang))
        self._clean_date_action.setText(get_text("toolbar_clean_date", lang))
        self._quick_formulaize_action.setText(get_text("toolbar_formulaize", lang))
        self._formula_check_action.setText(get_text("toolbar_formula_check", lang))
        self._formula_check_action.setToolTip(get_text("toolbar_formula_check", lang))
        self._data_profile_action.setText(get_text("toolbar_data_profile", lang))
        self._data_profile_action.setToolTip(get_text("toolbar_data_profile", lang))
        self._errors_scan_action.setText(get_text("toolbar_errors_scan", lang))
        self._errors_scan_action.setToolTip(get_text("toolbar_errors_scan", lang))
        self._changes_action.setText(get_text("toolbar_changes", lang))
        self._changes_action.setToolTip(get_text("toolbar_changes", lang))
        self._undo_action.setText(get_text("toolbar_undo", lang))
        self._undo_action.setToolTip(get_text("toolbar_undo", lang))
        self._save_chat_action.setText(get_text("toolbar_save_chat", lang))
        self._save_chat_action.setToolTip(get_text("toolbar_save_chat", lang))
        self._load_chat_action.setText(get_text("toolbar_load_chat", lang))
        self._load_chat_action.setToolTip(get_text("toolbar_load_chat", lang))
        self._export_report_action.setText(get_text("toolbar_export_report", lang))
        self._export_report_action.setToolTip(get_text("toolbar_export_report", lang))
        self._clear_action.setText(get_text("toolbar_clear", lang))
        self._clear_action.setToolTip(get_text("toolbar_clear_tooltip", lang))

        self._ribbon.setTabText(0, get_text("ribbon_home", lang))
        self._ribbon.setTabText(1, get_text("ribbon_history", lang))

        # File menu
        self._file_menu.setTitle(get_text("menu_file", lang))
        self._save_chat_action.setText(get_text("menu_save_chat", lang))
        self._load_chat_action.setText(get_text("menu_load_chat", lang))

        # Selection preview
        self._selection_title.setText(get_text("preview_title", lang))
        self._selection_stats.setText(get_text("preview_empty", lang))
        self._selection_samples.setText("")
        
        # Chat Widget
        self._chat_widget.update_language(lang)
        self._update_provider_model_label()
        
        self._update_status_bar()

    def _setup_window(self):
        """Pencere ozelliklerini ayarlar."""
        self.setWindowTitle("ArasAI") # Placeholder, _update_ui_text will fix
        self.setMinimumWidth(380)

        # Frameless window - custom title bar
        self.setWindowFlags(
            Qt.Window
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
        )

        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            # Ekranın %30'u, 380-500px arası
            addon_width = int(geo.width() * 0.30)
            addon_width = max(380, min(addon_width, 500))
            height = geo.height()
            x = geo.x() + geo.width() - addon_width
            y = geo.y()
            self.setGeometry(x, y, addon_width, height)

    def _position_libreoffice_window(self):
        """LibreCalc penceresini ekranın sol tarafına yerleştirir (wmctrl ile)."""
        try:
            screen = QApplication.primaryScreen()
            if not screen:
                return
            geo = screen.availableGeometry()
            addon_width = self.width()
            lo_width = geo.width() - addon_width

            # wmctrl ile açık pencereleri listele
            result = subprocess.run(
                ["wmctrl", "-l"],
                capture_output=True, text=True, timeout=3
            )
            if result.returncode != 0:
                logger.debug("wmctrl çalıştırılamadı: %s", result.stderr)
                return

            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                # LibreOffice Calc penceresini bul
                lower_line = line.lower()
                if "calc" in lower_line or "libreoffice" in lower_line:
                    wid = line.split()[0]
                    subprocess.run(
                        ["wmctrl", "-i", "-r", wid, "-e",
                         f"0,{geo.x()},{geo.y()},{lo_width},{geo.height()}"],
                        timeout=3
                    )
                    logger.info(
                        "LibreCalc penceresi konumlandırıldı: x=%d, y=%d, w=%d, h=%d",
                        geo.x(), geo.y(), lo_width, geo.height()
                    )
                    break
        except FileNotFoundError:
            logger.debug("wmctrl bulunamadı. 'sudo apt install wmctrl' ile yükleyin.")
        except Exception as exc:
            logger.debug("LibreOffice penceresi konumlandırılamadı: %s", exc)

    def mousePressEvent(self, event):
        """Pencereyi suruklemek icin baslangic konumunu yakalar."""
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """Pencereyi surukler."""
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def _setup_ui(self):
        """Ana arayuz bilesenlerini olusturur."""
        main_widget = QWidget()
        main_widget.setObjectName("main_container")
        
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Custom Title Bar ---
        self._title_bar = QFrame()
        self._title_bar.setObjectName("custom_title_bar")
        self._title_bar.setFixedHeight(32)
        title_layout = QHBoxLayout(self._title_bar)
        title_layout.setContentsMargins(10, 0, 0, 0)
        title_layout.setSpacing(0)

        title_label = QLabel("ArasAI")
        title_label.setObjectName("title_label")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        # Minimize butonu
        min_btn = QPushButton("—")
        min_btn.setObjectName("title_min_btn")
        min_btn.setFixedSize(46, 32)
        min_btn.setCursor(Qt.PointingHandCursor)
        min_btn.clicked.connect(self.showMinimized)
        title_layout.addWidget(min_btn)

        # Close butonu
        close_btn = QPushButton("✕")
        close_btn.setObjectName("title_close_btn")
        close_btn.setFixedSize(46, 32)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.close)
        title_layout.addWidget(close_btn)

        main_layout.addWidget(self._title_bar)

        # Menu Bar (Manual)
        self._menubar = QMenuBar()
        self._setup_menus()
        main_layout.addWidget(self._menubar)

        # Ribbon
        self._ribbon = QTabWidget()
        self._ribbon.setObjectName("ribbon")
        self._ribbon.setDocumentMode(True)
        self._ribbon.setTabPosition(QTabWidget.North)
        main_layout.addWidget(self._ribbon)
        self._setup_ribbon()

        # Chat Widget
        self._selection_preview = QFrame()
        self._selection_preview.setObjectName("selection_preview")
        preview_layout = QHBoxLayout(self._selection_preview)
        preview_layout.setContentsMargins(10, 6, 10, 6)
        preview_layout.setSpacing(8)

        self._selection_title = QLabel()
        self._selection_stats = QLabel()
        self._selection_samples = QLabel()
        self._selection_title.setObjectName("selection_title")
        self._selection_stats.setObjectName("selection_stats")
        self._selection_samples.setObjectName("selection_samples")
        preview_layout.addWidget(self._selection_title)
        preview_layout.addWidget(self._selection_stats)
        preview_layout.addWidget(self._selection_samples)
        preview_layout.addStretch()

        main_layout.addWidget(self._selection_preview)

        self._chat_widget = ChatWidget()
        self._chat_widget.message_sent.connect(self._on_message_sent)
        self._chat_widget.cancel_requested.connect(self._on_cancel_requested)
        main_layout.addWidget(self._chat_widget, 1)

        # Status Bar
        self._status_bar = QFrame()
        self._status_bar.setObjectName("custom_status_bar")
        self._status_bar.setFixedHeight(25)
        status_layout = QHBoxLayout(self._status_bar)
        status_layout.setContentsMargins(10, 0, 10, 0)
        self._setup_statusbar(status_layout)
        main_layout.addWidget(self._status_bar)

        self.setCentralWidget(main_widget)

    def _init_actions(self):
        """Uygulama aksiyonlarını oluşturur."""
        self._connect_action = QAction("Bağlan", self)
        self._connect_action.setIcon(get_icon("connect", self))
        self._connect_action.triggered.connect(self._connect_lo)

        self._analyze_action = QAction("Hücre Analizi", self)
        self._analyze_action.setIcon(get_icon("analyze", self))
        self._analyze_action.triggered.connect(self._on_analyze_cell)

        # Hızlı Eylemler
        self._quick_clear_action = QAction("Seçiliyi Temizle", self)
        self._quick_clear_action.triggered.connect(self._quick_clear_selection)

        self._quick_fill_action = QAction("Seçiliyi Doldur", self)
        self._quick_fill_action.triggered.connect(self._quick_fill_selection)

        self._quick_format_action = QAction("Seçiliyi Formatla", self)
        self._quick_format_action.triggered.connect(self._quick_format_selection)

        self._quick_table_action = QAction("Tablo Oluştur", self)
        self._quick_table_action.triggered.connect(self._quick_make_table)

        self._quick_header_action = QAction("Başlık Biçimlendir", self)
        self._quick_header_action.triggered.connect(self._quick_header_format)

        self._quick_outlier_action = QAction("Aykırıları Vurgula", self)
        self._quick_outlier_action.triggered.connect(self._quick_highlight_outliers)

        self._clean_trim_action = QAction("Boşlukları Temizle", self)
        self._clean_trim_action.triggered.connect(lambda: self._clean_trim_whitespace())

        self._clean_number_action = QAction("Metni Sayıya Çevir", self)
        self._clean_number_action.triggered.connect(lambda: self._clean_text_to_number())

        self._clean_date_action = QAction("Metni Tarihe Çevir", self)
        self._clean_date_action.triggered.connect(lambda: self._clean_text_to_date())

        self._quick_formulaize_action = QAction("Otomatik Formülleştir", self)
        self._quick_formulaize_action.triggered.connect(self._quick_formulaize_selection)

        # Formül doğrulama
        self._formula_check_action = QAction("Formül Doğrula", self)
        self._formula_check_action.setIcon(get_icon("formula", self))
        self._formula_check_action.triggered.connect(self._on_validate_formula)

        # Veri profili
        self._data_profile_action = QAction("Veri Profili", self)
        self._data_profile_action.setIcon(get_icon("profile", self))
        self._data_profile_action.triggered.connect(self._on_data_profile)

        self._errors_scan_action = QAction("Hata Taraması", self)
        self._errors_scan_action.setIcon(get_icon("error", self))
        self._errors_scan_action.triggered.connect(self._on_scan_errors)

        # Değişiklikler ve geri al
        self._changes_action = QAction("Değişiklikler", self)
        self._changes_action.setIcon(get_icon("history", self))
        self._changes_action.triggered.connect(self._on_show_changes)

        self._undo_action = QAction("Geri Al", self)
        self._undo_action.setIcon(get_icon("undo", self))
        self._undo_action.triggered.connect(self._on_undo_last_change)

        # Sohbet kaydet/yükle/rapor
        self._save_chat_action = QAction("Sohbeti Kaydet...", self)
        self._save_chat_action.setIcon(get_icon("save", self))
        self._save_chat_action.triggered.connect(self._save_chat)

        self._load_chat_action = QAction("Sohbeti Yükle...", self)
        self._load_chat_action.setIcon(get_icon("open", self))
        self._load_chat_action.triggered.connect(self._load_chat)

        self._export_report_action = QAction("Rapor Oluştur", self)
        self._export_report_action.setIcon(get_icon("export", self))
        self._export_report_action.triggered.connect(self._export_report)

        self._clear_action = QAction("Geçmişi Sil", self)
        self._clear_action.setIcon(get_icon("clear", self))
        self._clear_action.triggered.connect(self._clear_conversation)

    def _setup_menus(self):
        """Menu cubuklarini olusturur."""
        menubar = self._menubar
        menubar.clear()

        # Dosya menusu
        self._file_menu = menubar.addMenu("Dosya")

        self._file_menu.addAction(self._save_chat_action)
        self._file_menu.addAction(self._load_chat_action)
        self._file_menu.addAction(self._export_report_action)
        self._file_menu.addSeparator()

        self._settings_action = QAction("Ayarlar...", self)
        self._settings_action.triggered.connect(self._open_settings)
        self._file_menu.addAction(self._settings_action)

        self._file_menu.addSeparator()

        self._quit_action = QAction("Çıkış", self)
        self._quit_action.setShortcut("Ctrl+Q")
        self._quit_action.triggered.connect(self.close)
        self._file_menu.addAction(self._quit_action)

        # Saglayici menusu
        self._provider_menu = menubar.addMenu("Sağlayıcı")
        provider_group = QActionGroup(self)
        provider_group.setExclusive(True)

        self._action_openrouter = QAction("OpenRouter", self, checkable=True)
        self._action_openrouter.setActionGroup(provider_group)
        self._provider_menu.addAction(self._action_openrouter)

        self._action_ollama = QAction("Ollama", self, checkable=True)
        self._action_ollama.setActionGroup(provider_group)
        self._provider_menu.addAction(self._action_ollama)
        
        self._action_gemini = QAction("Gemini", self, checkable=True)
        self._action_gemini.setActionGroup(provider_group)
        self._provider_menu.addAction(self._action_gemini)

        if self._settings.provider == "ollama":
            self._action_ollama.setChecked(True)
        elif self._settings.provider == "gemini":
            self._action_gemini.setChecked(True)
        else:
            self._action_openrouter.setChecked(True)

        provider_group.triggered.connect(self._on_provider_changed)

        # Gorunum menusu
        self._view_menu = menubar.addMenu("Görünüm")

        # Tema Alt Menüsü
        self._theme_menu = self._view_menu.addMenu("Tema")
        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)

        self._action_light = QAction("Açık", self, checkable=True)
        self._action_light.setData("light")
        self._action_light.setActionGroup(theme_group)
        self._theme_menu.addAction(self._action_light)

        self._action_dark = QAction("Koyu", self, checkable=True)
        self._action_dark.setData("dark")
        self._action_dark.setActionGroup(theme_group)
        self._theme_menu.addAction(self._action_dark)

        self._action_system_theme = QAction("Sistem", self, checkable=True)
        self._action_system_theme.setData("system")
        self._action_system_theme.setActionGroup(theme_group)
        self._theme_menu.addAction(self._action_system_theme)

        # Mevcut temayı işaretle
        current_theme = self._settings.theme
        if current_theme == "light":
            self._action_light.setChecked(True)
        elif current_theme == "dark":
            self._action_dark.setChecked(True)
        else:
            self._action_system_theme.setChecked(True)

        theme_group.triggered.connect(self._on_theme_changed)
        
        # Dil Alt Menusu
        self._lang_menu = self._view_menu.addMenu("Dil")
        lang_group = QActionGroup(self)
        lang_group.setExclusive(True)
        
        self._action_lang_tr = QAction("Türkçe", self, checkable=True)
        self._action_lang_tr.setData("tr")
        self._action_lang_tr.setActionGroup(lang_group)
        self._lang_menu.addAction(self._action_lang_tr)
        
        self._action_lang_en = QAction("English", self, checkable=True)
        self._action_lang_en.setData("en")
        self._action_lang_en.setActionGroup(lang_group)
        self._lang_menu.addAction(self._action_lang_en)
        
        self._action_lang_system = QAction("Sistem", self, checkable=True)
        self._action_lang_system.setData("system")
        self._action_lang_system.setActionGroup(lang_group)
        self._lang_menu.addAction(self._action_lang_system)
        
        current_lang = self._settings.language
        if current_lang == "tr":
            self._action_lang_tr.setChecked(True)
        elif current_lang == "en":
            self._action_lang_en.setChecked(True)
        else:
            self._action_lang_system.setChecked(True)
            
        lang_group.triggered.connect(self._on_language_changed)

        self._view_menu.addSeparator()

        self._always_on_top_action = QAction("Her Zaman Üstte", self, checkable=True)
        self._always_on_top_action.triggered.connect(self._toggle_always_on_top)
        self._view_menu.addAction(self._always_on_top_action)

        # Yardim menusu
        self._help_menu = menubar.addMenu("Yardım")

        self._about_action = QAction("Hakkında", self)
        self._about_action.triggered.connect(self._show_about)
        self._help_menu.addAction(self._about_action)

    def _setup_ribbon(self):
        """Ribbon tarzı üst şerit oluşturur."""
        icon_size = QSize(24, 24)

        def _button_for_action(action: QAction) -> QToolButton:
            btn = QToolButton()
            btn.setDefaultAction(action)
            btn.setToolButtonStyle(Qt.ToolButtonIconOnly)
            btn.setIconSize(icon_size)
            btn.setToolTip(action.text())
            return btn

        # Hızlı Eylemler (Seçili aralık)
        self._quick_actions_btn = QToolButton()
        self._quick_actions_btn.setPopupMode(QToolButton.InstantPopup)
        self._quick_actions_btn.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self._quick_actions_btn.setIconSize(icon_size)
        self._quick_actions_btn.setText("Hızlı Eylemler")
        self._quick_actions_btn.setIcon(get_icon("menu", self))
        self._quick_actions_menu = QMenu(self)
        self._quick_actions_btn.setMenu(self._quick_actions_menu)

        self._quick_actions_menu.addAction(self._quick_clear_action)
        self._quick_actions_menu.addAction(self._quick_fill_action)
        self._quick_actions_menu.addAction(self._quick_format_action)
        self._quick_actions_menu.addSeparator()
        self._quick_actions_menu.addAction(self._quick_table_action)
        self._quick_actions_menu.addAction(self._quick_header_action)
        self._quick_actions_menu.addAction(self._quick_outlier_action)
        self._quick_actions_menu.addSeparator()
        self._quick_actions_menu.addAction(self._clean_trim_action)
        self._quick_actions_menu.addAction(self._clean_number_action)
        self._quick_actions_menu.addAction(self._clean_date_action)
        self._quick_actions_menu.addSeparator()
        self._quick_actions_menu.addAction(self._quick_formulaize_action)

        # Home tab
        home_tab = QWidget()
        home_layout = QHBoxLayout(home_tab)
        home_layout.setContentsMargins(8, 6, 8, 6)
        home_layout.setSpacing(12)

        home_layout.addWidget(_button_for_action(self._connect_action))
        home_layout.addWidget(_button_for_action(self._analyze_action))
        home_layout.addWidget(self._quick_actions_btn)
        home_layout.addWidget(_button_for_action(self._formula_check_action))
        home_layout.addWidget(_button_for_action(self._data_profile_action))
        home_layout.addWidget(_button_for_action(self._errors_scan_action))
        home_layout.addStretch()

        # History tab
        history_tab = QWidget()
        history_layout = QHBoxLayout(history_tab)
        history_layout.setContentsMargins(8, 6, 8, 6)
        history_layout.setSpacing(12)

        history_layout.addWidget(_button_for_action(self._changes_action))
        history_layout.addWidget(_button_for_action(self._undo_action))
        history_layout.addWidget(_button_for_action(self._save_chat_action))
        history_layout.addWidget(_button_for_action(self._load_chat_action))
        history_layout.addWidget(_button_for_action(self._export_report_action))
        history_layout.addWidget(_button_for_action(self._clear_action))
        history_layout.addStretch()

        self._ribbon.addTab(home_tab, "Home")
        self._ribbon.addTab(history_tab, "History")

    def _setup_statusbar(self, layout):
        """Durum cubugunu olusturur."""
        self._lo_status_label = QLabel()
        self._llm_status_label = QLabel()
        self._cell_status_label = QLabel() # Secili hucre adresi
        self._usage_status_label = QLabel()

        # Modernleştirilmiş minimalist görünüm
        self._lo_status_label.setContentsMargins(0, 0, 8, 0)
        self._llm_status_label.setContentsMargins(8, 0, 0, 0)
        self._cell_status_label.setStyleSheet("font-weight: bold; color: #18a303;")
        self._usage_status_label.setStyleSheet("color: #94a3b8;")

        layout.addWidget(self._lo_status_label)
        layout.addWidget(self._cell_status_label)
        layout.addStretch()
        layout.addWidget(self._usage_status_label)
        layout.addWidget(self._llm_status_label)

        # Initial text set by _update_ui_text

    def _apply_theme(self):
        """Secili temayi ve sistem temasini dikkate alarak uygular."""
        theme_name = self._settings.theme
        
        # Sistem teması seçiliyse algıla
        if theme_name == "system":
            try:
                import darkdetect
                if darkdetect.isDark():
                    theme_name = "dark"
                else:
                    theme_name = "light"
            except ImportError:
                # darkdetect yoksa varsayılan olarak light
                theme_name = "light"

        stylesheet = get_theme(theme_name)
        self.setStyleSheet(stylesheet)
        
        # Chat widget temasını da güncelle
        if hasattr(self, '_chat_widget'):
            self._chat_widget.update_theme(theme_name)

    def _on_theme_changed(self, action: QAction):
        """Tema menüsünden seçim yapıldığında çağrılır."""
        theme = action.data()
        self._settings.theme = theme
        self._settings.save()
        self._apply_theme()
        
    def _on_language_changed(self, action: QAction):
        """Dil menusunden secim yapildiginda."""
        lang = action.data()
        self._settings.language = lang
        self._settings.save()
        self._current_lang = lang
        self._update_ui_text()

    def _init_provider(self):
        """Aktif LLM saglayicisini baslatir."""
        try:
            if self._settings.provider == "ollama":
                self._provider = OllamaProvider()
            elif self._settings.provider == "gemini":
                self._provider = GeminiProvider()
            else:
                self._provider = OpenRouterProvider()
            self._update_status_bar()
            self._update_provider_model_label()
        except Exception as exc:
            logger.error("LLM saglayici baslatilamadi: %s", exc)
            self._provider = None
            self._update_status_bar()
            self._update_provider_model_label()

    def _update_provider_model_label(self):
        """Saglayici ve model bilgisini sohbet giris alaninda gunceller."""
        if not hasattr(self, "_chat_widget"):
            return

        if self._settings.provider == "ollama":
            provider_name = "Ollama"
            model_name = self._settings.ollama_model
        elif self._settings.provider == "gemini":
            provider_name = "Gemini"
            model_name = self._settings.gemini_model
        else:
            provider_name = "OpenRouter"
            model_name = self._settings.openrouter_model

        self._chat_widget.update_provider_model(provider_name, model_name)

    def _update_status_bar(self):
        """Durum cubugu etiketlerini gunceller."""
        lang = self._current_lang
        
        # LO durumu
        if self._bridge and self._bridge.is_connected:
            self._lo_status_label.setText(f"  {get_text('status_lo_connected', lang)}")
            self._lo_status_label.setStyleSheet("color: #44bb44; font-weight: bold;")
        else:
            self._lo_status_label.setText(f"  {get_text('status_lo_disconnected', lang)}")
            self._lo_status_label.setStyleSheet("color: #bb4444; font-weight: bold;")

        # LLM durumu
        provider_name = self._settings.provider.capitalize()
        if self._provider:
            self._llm_status_label.setText(f"LLM: {provider_name}  ")
            self._llm_status_label.setStyleSheet("color: #44bb44;")
        else:
            error_text = get_text("status_llm_error", lang)
            self._llm_status_label.setText(f"LLM: {provider_name} {error_text}  ")
            self._llm_status_label.setStyleSheet("color: #bb4444;")

        self._update_usage_status()

    def _update_usage_status(self, prompt_tokens: int | None = None, completion_tokens: int | None = None):
        """Token kullanım tahminini durum çubuğunda gösterir."""
        lang = self._current_lang

        if prompt_tokens is None and completion_tokens is None:
            self._usage_status_label.setText("")
            return

        prompt_str = "-" if prompt_tokens is None else f"~{prompt_tokens}"
        completion_str = "-" if completion_tokens is None else f"~{completion_tokens}"
        text = get_text("status_tokens_est", lang).format(
            prompt=prompt_str,
            completion=completion_str,
        )
        prompt_price, completion_price = self._get_model_prices()
        if prompt_price or completion_price:
            cost = 0.0
            if prompt_tokens is not None and prompt_price:
                cost += (prompt_tokens / 1000.0) * prompt_price
            if completion_tokens is not None and completion_price:
                cost += (completion_tokens / 1000.0) * completion_price
            cost_text = get_text("status_cost_est", lang).format(cost=f"${cost:.4f}")
            text = f"{text} | {cost_text}"

        self._usage_status_label.setText(text)

    def _estimate_tokens(self, text: str) -> int:
        """Basit token tahmini (yaklaşık)."""
        if not text:
            return 0
        return max(1, int(len(text) / 4))

    def _get_model_prices(self) -> tuple[float, float]:
        """Seçili model için prompt/completion fiyatlarını döndürür."""
        if self._settings.provider == "ollama":
            model = self._settings.ollama_model
            prices = self._settings.ollama_model_prices.get(model, {})
        elif self._settings.provider == "gemini":
            return 0.0, 0.0
        else:
            model = self._settings.openrouter_model
            prices = self._settings.openrouter_model_prices.get(model, {})

        prompt_price = float(prices.get("prompt", 0.0) or 0.0)
        completion_price = float(prices.get("completion", 0.0) or 0.0)
        return prompt_price, completion_price

    def _masked_messages(self, messages: list[dict]) -> list[dict]:
        """Hassas verileri maskeleyerek mesajları döndürür."""
        if not self._mask_sensitive:
            return list(messages)

        masked = []
        for m in messages:
            if m.get("role") != "user":
                masked.append(m)
                continue
            content = m.get("content")
            if not isinstance(content, str):
                masked.append(m)
                continue
            masked.append({**m, "content": self._mask_sensitive_text(content)})
        return masked

    def _mask_sensitive_text(self, text: str) -> str:
        """E-posta, telefon ve kart benzeri kalıpları maskele."""
        # Email
        text = re.sub(r'([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})', "[EMAIL]", text)
        # Phone numbers (simple)
        text = re.sub(r'(\+?\d[\d\s().-]{7,}\d)', "[PHONE]", text)
        # Card-like numbers 13-19 digits
        text = re.sub(r'\b(?:\d[ -]*?){13,19}\b', "[CARD]", text)
        return text

    # --- Olay yoneticileri ---

    def _on_message_sent(self, text: str):
        """Kullanici mesaji gonderildiginde cagirilir.

        Args:
            text: Kullanici mesaji.
        """
        if text.strip().startswith("/"):
            self._chat_widget.add_message("user", text)
            handled = self._handle_command(text.strip())
            if not handled:
                self._chat_widget.add_message(
                    "assistant",
                    get_text("cmd_unknown", self._current_lang).format(text.strip()),
                )
            return

        self._chat_widget.add_message("user", text)
        self._chat_widget.set_input_enabled(False)
        self._chat_widget.set_generating(True)
        self._chat_widget.show_loading()

        # Sohbet gecmisine ekle
        self._conversation.append({"role": "user", "content": text})

        # LLM'ye gonder
        self._send_to_llm()

    def _handle_command(self, text: str) -> bool:
        """Slash komutlarını işler."""
        lang = self._current_lang
        cmd = text.split()[0].lower()

        if cmd in ("/help", "/yardim", "/yardım"):
            lines = [get_text("cmd_help_header", lang)]
            for c, key in [
                ("/analiz", "cmd_desc_analyze"),
                ("/baglan", "cmd_desc_connect"),
                ("/profil", "cmd_desc_profile"),
                ("/dogrula", "cmd_desc_validate"),
                ("/gecmis", "cmd_desc_changes"),
                ("/geri", "cmd_desc_undo"),
                ("/temizle", "cmd_desc_clear"),
            ]:
                lines.append(f"{c} - {get_text(key, lang)}")
            self._chat_widget.add_message("assistant", "\n".join(lines))
            # İlk hata için hızlı açıklama
            first = errors[0]
            addr = first.get("address")
            if addr:
                try:
                    detail = detector.explain_error(addr)
                    suggestion = detail.get("suggestion")
                    if suggestion:
                        self._chat_widget.add_message(
                            "assistant", get_text("msg_errors_suggestion", lang).format(addr, suggestion)
                        )
                except Exception:
                    pass
            return True

        if cmd in ("/analiz", "/analyze"):
            self._on_analyze_cell()
            return True

        if cmd in ("/baglan", "/connect"):
            self._connect_lo()
            return True

        if cmd in ("/profil", "/profile"):
            self._on_data_profile()
            return True

        if cmd in ("/dogrula", "/validate"):
            self._on_validate_formula()
            return True

        if cmd in ("/gecmis", "/changes", "/history"):
            self._on_show_changes()
            return True

        if cmd in ("/geri", "/undo"):
            self._on_undo_last_change()
            return True

        if cmd in ("/temizle", "/clear"):
            self._clear_conversation()
            return True

        return False

    def _send_to_llm(self):
        """Mevcut sohbet gecmisini LLM'ye gonderir."""
        if not self._provider:
            self._chat_widget.hide_loading()
            self._chat_widget.set_generating(False)
            self._chat_widget.set_input_enabled(True)
            self._chat_widget.add_message(
                "assistant", get_text("msg_llm_not_configured", self._current_lang)
            )
            return

        # Otomatik bağlam daraltma
        self._maybe_compact_context()

        # Dinamik bağlam oluştur
        dynamic_context = self._build_dynamic_context()
        summary_block = f"\n\n## SUMMARY\n{self._conversation_summary}" if self._conversation_summary else ""
        full_system_prompt = SYSTEM_PROMPT + summary_block + dynamic_context

        messages = [{"role": "system", "content": full_system_prompt}] + self._masked_messages(self._conversation)

        # Prompt token tahmini
        prompt_text = "\n".join([m.get("content") or "" for m in messages])
        self._last_prompt_tokens_est = self._estimate_tokens(prompt_text)
        self._update_usage_status(prompt_tokens=self._last_prompt_tokens_est, completion_tokens=None)

        # Araclari her zaman gonder - LO bagli degilse dispatcher hata mesaji dondurur
        tools = TOOLS

        self._start_stream(messages, tools)

    def _maybe_compact_context(self):
        """Sohbet geçmişini özetleyerek bağlamı daraltır."""
        if self._is_summarizing:
            return
        if not self._provider:
            return

        # Mesaj sayısı kontrolü - bellek yönetimi için
        if len(self._conversation) > MAX_CONVERSATION_MESSAGES:
            logger.info("Konuşma %d mesajı aştı, özetleme tetikleniyor", MAX_CONVERSATION_MESSAGES)

        # Basit eşik: max_tokens * 2 tahmini (prompt + completion)
        max_tokens = getattr(self._settings, "max_tokens", 4096)
        threshold = max(2000, int(max_tokens * 2))

        def _estimate_for_messages(msgs: list[dict]) -> int:
            text = "\n".join([m.get("content") or "" for m in msgs])
            return self._estimate_tokens(text)

        system_stub = {"role": "system", "content": SYSTEM_PROMPT}
        recent_keep = 8
        if len(self._conversation) <= recent_keep:
            return

        estimate = _estimate_for_messages([system_stub] + self._conversation)
        if estimate < threshold:
            return

        older = self._conversation[:-recent_keep]
        recent = self._conversation[-recent_keep:]
        if not older:
            return

        # Özet isteği
        summary_prompt = (
            "You are a summarizer. Summarize the conversation so far for future context.\n"
            "Keep it concise. Include user goals, constraints, decisions, and any important data.\n"
            "Use bullet points.\n"
        )
        transcript_lines = []
        if self._conversation_summary:
            transcript_lines.append("Existing summary:")
            transcript_lines.append(self._conversation_summary)
            transcript_lines.append("")
        transcript_lines.append("Conversation:")
        for m in self._masked_messages(older):
            role = m.get("role", "")
            content = m.get("content")
            if content is None:
                continue
            transcript_lines.append(f"{role}: {content}")

        self._is_summarizing = True
        try:
            result = self._provider.chat_completion(
                [
                    {"role": "system", "content": summary_prompt},
                    {"role": "user", "content": "\n".join(transcript_lines)},
                ],
                tools=None,
            )
            new_summary = (result.get("content") or "").strip()
            if new_summary:
                self._conversation_summary = new_summary
                self._conversation = list(recent)
        except Exception as exc:
            logger.warning("Ozetleme basarisiz: %s", exc)
        finally:
            self._is_summarizing = False

    def _start_stream(self, messages, tools):
        """LLM stream istegini baslatir."""
        # Stream state reset
        self._stream_content = ""
        self._stream_tool_calls_indexed = {}
        self._stream_tool_calls_full = []
        self._stream_has_tool_calls = False
        self._stream_started = False

        # Stream baloncuğu oluştur
        self._chat_widget.start_stream_message("assistant")

        self._stream_worker = LLMStreamWorker(self._provider, messages, tools, self)
        self._stream_worker.chunk.connect(self._on_llm_stream_chunk)
        self._stream_worker.finished.connect(self._on_llm_stream_finished)
        self._stream_worker.error.connect(self._on_llm_stream_error)
        self._stream_worker.start()

    def _on_llm_stream_chunk(self, part: dict):
        """Stream parçası geldiğinde çağrılır."""
        if not self._stream_started:
            self._stream_started = True
            self._chat_widget.hide_loading()

        content = part.get("content") or ""
        tool_calls = part.get("tool_calls")

        if tool_calls:
            self._stream_has_tool_calls = True
            self._accumulate_tool_calls(tool_calls)

        if content and not self._stream_has_tool_calls:
            self._stream_content += content
            self._chat_widget.update_stream_message(self._stream_content)

    def _on_llm_stream_finished(self):
        """Stream tamamlandığında çağrılır."""
        self._finalize_stream()

    def _on_llm_stream_error(self, error_msg: str):
        """Stream hatası alındığında çağrılır."""
        self._chat_widget.hide_loading()
        self._chat_widget.set_generating(False)
        self._chat_widget.set_input_enabled(True)
        self._chat_widget.discard_stream_message()
        self._chat_widget.add_message(
            "assistant", get_text("msg_llm_error", self._current_lang).format(error_msg)
        )

    def _accumulate_tool_calls(self, tool_calls: list):
        """Stream sırasında tool_call parçalarını birleştirir."""
        for tc in tool_calls:
            index = tc.get("index")
            if index is None:
                # Tam tool_call olarak gelmiş olabilir
                if "function" in tc:
                    self._stream_tool_calls_full.append(tc)
                continue

            existing = self._stream_tool_calls_indexed.setdefault(index, {
                "id": tc.get("id", ""),
                "type": tc.get("type", "function"),
                "function": {"name": "", "arguments": ""},
            })

            if "id" in tc and tc["id"]:
                existing["id"] = tc["id"]
            if "type" in tc and tc["type"]:
                existing["type"] = tc["type"]

            func = tc.get("function", {})
            if "name" in func and func["name"]:
                existing["function"]["name"] = func["name"]
            if "arguments" in func and func["arguments"]:
                existing["function"]["arguments"] += func["arguments"]

    def _finalize_stream(self):
        """Stream bitince sohbeti finalize eder."""
        self._chat_widget.hide_loading()
        self._chat_widget.set_generating(False)
        self._chat_widget.set_input_enabled(True)

        tool_calls = []
        if self._stream_tool_calls_indexed:
            for idx in sorted(self._stream_tool_calls_indexed.keys()):
                tool_calls.append(self._stream_tool_calls_indexed[idx])
        if self._stream_tool_calls_full:
            tool_calls.extend(self._stream_tool_calls_full)

        if tool_calls:
            self._chat_widget.discard_stream_message()
            # Tool çağrıları varsa içeriği sohbete ekleme
            self._handle_tool_calls(tool_calls)
            return

        if self._stream_content:
            self._conversation.append({"role": "assistant", "content": self._stream_content})
            self._chat_widget.end_stream_message()
            completion_est = self._estimate_tokens(self._stream_content)
            self._update_usage_status(
                prompt_tokens=self._last_prompt_tokens_est,
                completion_tokens=completion_est,
            )
        else:
            self._chat_widget.discard_stream_message()

    def _on_cancel_requested(self):
        """Kullanıcı üretimi iptal etmek istedi."""
        if self._stream_worker and self._stream_worker.isRunning():
            self._stream_worker.requestInterruption()
            self._stream_worker.quit()
            self._stream_worker.wait(300)

        self._chat_widget.hide_loading()
        self._chat_widget.set_generating(False)
        self._chat_widget.set_input_enabled(True)

        if self._stream_content:
            self._conversation.append({"role": "assistant", "content": self._stream_content})
            self._chat_widget.end_stream_message()
            completion_est = self._estimate_tokens(self._stream_content)
            self._update_usage_status(
                prompt_tokens=self._last_prompt_tokens_est,
                completion_tokens=completion_est,
            )
        else:
            self._chat_widget.discard_stream_message()
            self._chat_widget.add_message(
                "assistant", get_text("msg_generation_cancelled", self._current_lang)
            )

    def _build_dynamic_context(self) -> str:
        """LLM için dinamik bağlam bilgisi oluşturur.

        LibreOffice bağlıysa mevcut sayfa özeti ve seçili hücre bilgisini döndürür.

        Returns:
            Dinamik bağlam metni.
        """
        if not self._bridge or not self._bridge.is_connected:
            return "\n\n## MEVCUT DURUM\nLibreOffice bağlantısı yok."

        context_parts = ["\n\n## MEVCUT DURUM"]

        try:
            # Sayfa özeti
            analyzer = SheetAnalyzer(self._bridge)
            summary = analyzer.get_sheet_summary()

            context_parts.append(f"Sayfa: {summary.get('sheet_name', 'Bilinmiyor')}")
            context_parts.append(f"Kullanılan Aralık: {summary.get('used_range', '-')}")
            context_parts.append(f"Boyut: {summary.get('row_count', 0)} satır x {summary.get('col_count', 0)} sütun")

            headers = summary.get('headers', [])
            if headers and any(headers):
                header_str = ", ".join([h or "(boş)" for h in headers[:10]])
                if len(headers) > 10:
                    header_str += f"... (+{len(headers)-10} sütun)"
                context_parts.append(f"Başlıklar: {header_str}")

        except Exception as e:
            logger.debug("Sayfa özeti alınamadı: %s", e)
            context_parts.append("Sayfa bilgisi alınamadı.")

        try:
            # Seçili hücre
            doc = self._bridge.get_active_document()
            controller = doc.getCurrentController()
            selection = controller.getSelection()
            address = LibreOfficeBridge.get_selection_address(selection)
            context_parts.append(f"Seçili Hücre: {address}")

            # Seçili hücrenin içeriğini de ekle (tek hücre ise)
            if selection and hasattr(selection, 'getString'):
                value = selection.getString() or selection.getValue()
                formula = selection.getFormula()
                if formula:
                    context_parts.append(f"Seçili Formül: {formula}")
                elif value:
                    context_parts.append(f"Seçili Değer: {value}")

        except Exception as e:
            logger.debug("Seçili hücre bilgisi alınamadı: %s", e)

        return "\n".join(context_parts)

    def _on_llm_response(self, result: dict):
        """LLM yaniti alindiginda cagirilir.

        Args:
            result: LLM yanit sozlugu (content, tool_calls, usage).
        """
        tool_calls = result.get("tool_calls")

        if tool_calls:
            # LO bagli degilse otomatik baglanmayi dene
            if not self._dispatcher:
                self._connect_lo_silent()

            if self._dispatcher:
                self._handle_tool_calls(tool_calls)
                return
            else:
                # Baglanti basarisiz - kullaniciya bildir
                self._chat_widget.hide_loading()
                self._chat_widget.set_input_enabled(True)
                self._chat_widget.add_message(
                    "assistant",
                    get_text("msg_lo_connect_required_for_tool", self._current_lang)
                )
                return

        # Normal metin yaniti
        content = result.get("content", "")
        if content:
            self._conversation.append({"role": "assistant", "content": content})
            self._chat_widget.add_message("assistant", content)

        self._chat_widget.hide_loading()
        self._chat_widget.set_input_enabled(True)

    def _handle_tool_calls(self, tool_calls: list):
        """Arac cagrilarini isler ve sonuclari LLM'ye geri gonderir.

        Args:
            tool_calls: LLM'den gelen arac cagrisi listesi.
        """
        if not self._confirm_tool_calls(tool_calls):
            self._chat_widget.hide_loading()
            self._chat_widget.set_input_enabled(True)
            self._chat_widget.set_generating(False)
            self._chat_widget.add_message(
                "assistant", get_text("msg_tool_call_cancelled", self._current_lang)
            )
            return

        # Asistan mesajini sohbet gecmisine ekle
        self._conversation.append({
            "role": "assistant",
            "content": None,
            "tool_calls": tool_calls,
        })

        for tc in tool_calls:
            func = tc.get("function", {})
            tool_name = func.get("name", "")
            try:
                arguments = json.loads(func.get("arguments", "{}"))
            except json.JSONDecodeError:
                arguments = {}

            tool_result = self._dispatcher.dispatch(tool_name, arguments)

            self._conversation.append({
                "role": "tool",
                "tool_call_id": tc.get("id", ""),
                "content": tool_result,
            })

        # Arac sonuclariyla tekrar LLM'ye gonder
        self._send_to_llm()

    def _confirm_tool_calls(self, tool_calls: list) -> bool:
        """Araç çağrıları için kullanıcı onayı ister."""
        if self._tool_confirm_always:
            return True
        lang = self._current_lang
        lines = [get_text("msg_tool_call_confirm", lang)]
        for tc in tool_calls:
            func = tc.get("function", {})
            name = func.get("name", "")
            try:
                args = json.loads(func.get("arguments", "{}"))
            except json.JSONDecodeError:
                args = func.get("arguments", "")
            lines.append(f"- {name}: {args}")

        msg = "\n".join(lines)
        box = QMessageBox(self)
        box.setWindowTitle(get_text("msg_tool_call_title", lang))
        box.setText(msg)
        box.setIcon(QMessageBox.Question)

        yes_btn = box.addButton(get_text("msg_tool_call_yes", lang), QMessageBox.AcceptRole)
        always_btn = box.addButton(get_text("msg_tool_call_always", lang), QMessageBox.ActionRole)
        no_btn = box.addButton(get_text("msg_tool_call_no", lang), QMessageBox.RejectRole)
        box.setDefaultButton(no_btn)

        box.exec_()
        clicked = box.clickedButton()
        if clicked == always_btn:
            self._tool_confirm_always = True
            return True
        if clicked == yes_btn:
            return True
        return False

    def _on_llm_error(self, error_msg: str):
        """LLM hatasi alindiginda cagirilir.

        Args:
            error_msg: Hata mesaji.
        """
        self._chat_widget.hide_loading()
        self._chat_widget.set_input_enabled(True)
        self._chat_widget.add_message(
            "assistant", get_text("msg_llm_error", self._current_lang).format(error_msg)
        )

    def _connect_lo_silent(self) -> bool:
        """LibreOffice'e sessizce baglanir (UI mesaji gostermez).

        Returns:
            Baglanti basariliysa True.
        """
        try:
            self._bridge = LibreOfficeBridge(
                host=self._settings.lo_host,
                port=self._settings.lo_port,
            )
            success = self._bridge.connect()
            if success:
                inspector = CellInspector(self._bridge)
                manipulator = CellManipulator(self._bridge)
                analyzer = SheetAnalyzer(self._bridge)
                detector = ErrorDetector(self._bridge, inspector)
                self._dispatcher = ToolDispatcher(
                    inspector, manipulator, analyzer, detector, change_logger=self._record_change
                )

                # Listener baslat
                self._listener = LibreOfficeEventListener(self._bridge)
                self._listener.selection_changed.connect(self._on_selection_changed)
                self._listener.start()

                self._update_status_bar()
                return True
        except Exception as exc:
            logger.warning("Otomatik LO baglantisi basarisiz: %s", exc)
        self._update_status_bar()
        return False

    def _connect_lo(self):
        """LibreOffice'e baglanir ve sonucu kullaniciya bildirir."""
        success = self._connect_lo_silent()
        lang = self._current_lang
        if success:
            self._chat_widget.add_message(
                "assistant", get_text("msg_lo_connect_success", lang)
            )
        else:
            self._chat_widget.add_message(
                "assistant", get_text("msg_lo_connect_fail", lang)
            )

    def _on_analyze_cell(self):
        """Secili hucreyi analiz eder."""
        lang = self._current_lang
        if not self._bridge or not self._bridge.is_connected:
            self._chat_widget.add_message(
                "assistant", get_text("msg_need_lo", lang)
            )
            return

        try:
            inspector = CellInspector(self._bridge)
            doc = self._bridge.get_active_document()
            controller = doc.getCurrentController()
            selection = controller.getSelection()

            # Secili hucrenin adresini al
            cell_addr = selection.getCellAddress()
            col_str = LibreOfficeBridge._index_to_column(cell_addr.Column)
            address = f"{col_str}{cell_addr.Row + 1}"

            # Detayli bilgileri al
            details = inspector.get_cell_details(address)
            # Oncul ve ardillari al
            precedents = inspector.get_cell_precedents(address)
            dependents = inspector.get_cell_dependents(address)

            details["precedents"] = precedents
            details["dependents"] = dependents

            # Hata kontrolu
            value = details.get("value")
            if isinstance(value, str) and value.startswith("Err:"):
                details["error"] = value

            # Analiz sonucunu sohbete yaz
            # Note: Content generation is hard to localize perfectly without templates
            # but we can try basic formatting
            analysis_text = (
                f"**Hücre:** {details.get('address')}\n"
                f"**Değer:** {details.get('value')}\n"
                f"**Formül:** `{details.get('formula')}`"
            )
            self._chat_widget.add_message("assistant", analysis_text)

        except Exception as exc:
            logger.error("Hucre analiz hatasi: %s", exc)
            self._chat_widget.add_message(
                "assistant", get_text("msg_analysis_error", lang).format(exc)
            )

    def _on_validate_formula(self):
        """Seçili hücrenin formülünü doğrular."""
        lang = self._current_lang
        if not self._bridge or not self._bridge.is_connected:
            self._chat_widget.add_message("assistant", get_text("msg_need_lo", lang))
            return

        try:
            inspector = CellInspector(self._bridge)
            address = self._get_selection_address()
            if ":" in address:
                self._chat_widget.add_message(
                    "assistant", get_text("msg_formula_single_cell", lang)
                )
                return

            details = inspector.get_cell_details(address)
            formula = details.get("formula")
            value = details.get("value")

            if not formula:
                self._chat_widget.add_message(
                    "assistant", get_text("msg_formula_missing", lang).format(address)
                )
                return

            if isinstance(value, str) and value.startswith("Err:"):
                detector = ErrorDetector(self._bridge, inspector)
                error_info = detector.get_error_type(value)
                explanation = detector.explain_error(address)
                msg = get_text("msg_formula_error", lang).format(
                    address=address,
                    formula=formula,
                    error=error_info.get("type", value),
                    description=error_info.get("description", ""),
                )
                self._chat_widget.add_message("assistant", msg)
                if explanation and explanation.get("suggestion"):
                    self._chat_widget.add_message(
                        "assistant",
                        get_text("msg_formula_suggestion", lang).format(explanation.get("suggestion")),
                    )
            else:
                self._chat_widget.add_message(
                    "assistant",
                    get_text("msg_formula_ok", lang).format(address, formula),
                )

        except Exception as exc:
            logger.error("Formül doğrulama hatası: %s", exc)
            self._chat_widget.add_message(
                "assistant", get_text("msg_formula_check_error", lang).format(exc)
            )

    def _on_data_profile(self):
        """Seçili aralık için veri profili çıkarır."""
        lang = self._current_lang
        if not self._bridge or not self._bridge.is_connected:
            self._chat_widget.add_message("assistant", get_text("msg_need_lo", lang))
            return

        try:
            analyzer = SheetAnalyzer(self._bridge)
            inspector = CellInspector(self._bridge)
            selection = self._get_selection_address()

            if selection in ("-", "Bilinmeyen Seçim", "Hata") or "Çoklu Seçim" in selection or "," in selection:
                range_str = analyzer.get_sheet_summary().get("used_range")
            elif ":" in selection:
                range_str = selection
            else:
                range_str = analyzer.get_sheet_summary().get("used_range")

            if not range_str:
                self._chat_widget.add_message(
                    "assistant", get_text("msg_profile_no_range", lang)
                )
                return

            grid = inspector.read_range(range_str)
            if not grid:
                self._chat_widget.add_message(
                    "assistant", get_text("msg_profile_empty", lang)
                )
                return

            start, end = LibreOfficeBridge.parse_range_string(range_str)
            row_count = end[1] - start[1] + 1
            col_count = end[0] - start[0] + 1
            total_cells = row_count * col_count

            values = []
            numeric = []
            empties = 0
            for row in grid:
                for cell in row:
                    if cell.get("type") == "empty" or cell.get("value") is None:
                        empties += 1
                        continue
                    val = cell.get("value")
                    values.append((cell.get("address"), val))
                    if isinstance(val, (int, float)):
                        numeric.append((cell.get("address"), float(val)))

            # Duplicate analysis
            freq = {}
            for _addr, val in values:
                key = str(val).strip()
                if not key:
                    continue
                freq[key] = freq.get(key, 0) + 1
            duplicates = [(k, v) for k, v in freq.items() if v > 1]
            duplicates.sort(key=lambda x: x[1], reverse=True)
            top_dupes = duplicates[:3]

            # Outlier analysis (z-score)
            outliers = []
            if len(numeric) >= 8:
                nums = [v for _a, v in numeric]
                mean = sum(nums) / len(nums)
                variance = sum((x - mean) ** 2 for x in nums) / max(1, len(nums) - 1)
                std = variance ** 0.5
                if std > 0:
                    for addr, v in numeric:
                        z = abs(v - mean) / std
                        if z >= 3.0:
                            outliers.append((addr, v))
            outliers = outliers[:5]

            dup_summary = (
                ", ".join([f"`{k}` x{v}" for k, v in top_dupes]) if top_dupes else get_text("msg_profile_none", lang)
            )
            out_summary = (
                ", ".join([f"{addr}={val}" for addr, val in outliers]) if outliers else get_text("msg_profile_none", lang)
            )

            report = (
                f"**Veri Profili**\n"
                f"Aralık: `{range_str}`\n"
                f"Boyut: {row_count} satır x {col_count} sütun\n"
                f"Toplam Hücre: {total_cells}\n"
                f"Boş Hücre: {empties}\n"
                f"Tekrarlı Değerler: {len(duplicates)}\n"
                f"En Sık Tekrarlar: {dup_summary}\n"
                f"Aykırı Değerler (z≥3): {out_summary}"
            )

            self._chat_widget.add_message("assistant", report)

        except Exception as exc:
            logger.error("Veri profili hatası: %s", exc)
            self._chat_widget.add_message(
                "assistant", get_text("msg_profile_error", lang).format(exc)
            )

    def _on_scan_errors(self):
        """Tüm sayfada formül hatalarını tarar ve öneri verir."""
        lang = self._current_lang
        if not self._bridge or not self._bridge.is_connected:
            self._chat_widget.add_message("assistant", get_text("msg_need_lo", lang))
            return

        try:
            inspector = CellInspector(self._bridge)
            detector = ErrorDetector(self._bridge, inspector)

            errors = detector.detect_errors(range_str=None)
            if not errors:
                self._chat_widget.add_message(
                    "assistant", get_text("msg_errors_none", lang)
                )
                return

            lines = [get_text("msg_errors_found", lang).format(len(errors))]
            for err in errors[:10]:
                addr = err.get("address")
                err_info = err.get("error") or {}
                etype = err_info.get("name") or err_info.get("code") or "Error"
                desc = err_info.get("description", "")
                lines.append(f"- {addr}: {etype} {desc}".strip())

            self._chat_widget.add_message("assistant", "\n".join(lines))

        except Exception as exc:
            logger.error("Hata tarama hatası: %s", exc)
            self._chat_widget.add_message(
                "assistant", get_text("msg_errors_scan_error", lang).format(exc)
            )

    def _get_selection_address(self) -> str:
        """Mevcut seçim adresini döndürür."""
        doc = self._bridge.get_active_document()
        controller = doc.getCurrentController()
        selection = controller.getSelection()
        return LibreOfficeBridge.get_selection_address(selection)

    def _get_selection_ranges(self) -> list[str]:
        """Mevcut seçim aralıklarını döndürür."""
        doc = self._bridge.get_active_document()
        controller = doc.getCurrentController()
        selection = controller.getSelection()
        return LibreOfficeBridge.get_selection_ranges(selection)

    def _quick_clear_selection(self):
        """Seçili hücre/alanı temizler."""
        lang = self._current_lang
        if not self._bridge or not self._bridge.is_connected:
            self._chat_widget.add_message("assistant", get_text("msg_need_lo", lang))
            return

        try:
            manipulator = CellManipulator(self._bridge)
            ranges = self._get_selection_ranges()
            if not ranges:
                self._chat_widget.add_message("assistant", get_text("msg_clean_need_range", lang))
                return

            for address in ranges:
                range_str = address
                cells, too_large = self._capture_cells_for_range(range_str, max_cells=300)
                if ":" in address:
                    manipulator.clear_range(address)
                else:
                    manipulator.clear_cell(address)
                if too_large:
                    self._record_change(get_text("msg_change_clear", lang).format(address), cells=None, undoable=False)
                else:
                    self._record_change(get_text("msg_change_clear", lang).format(address), cells=cells, undoable=True)
            self._chat_widget.add_message(
                "assistant", get_text("msg_quick_clear_done", lang)
            )
        except Exception as exc:
            logger.error("Hızlı temizleme hatası: %s", exc)
            self._chat_widget.add_message(
                "assistant", get_text("msg_quick_action_error", lang).format(exc)
            )

    def _quick_fill_selection(self):
        """Seçili hücre/alanı arka plan rengiyle doldurur."""
        lang = self._current_lang
        if not self._bridge or not self._bridge.is_connected:
            self._chat_widget.add_message("assistant", get_text("msg_need_lo", lang))
            return

        try:
            manipulator = CellManipulator(self._bridge)
            fill_color = 0xD1FAE5  # açık yeşil
            ranges = self._get_selection_ranges()
            if not ranges:
                self._chat_widget.add_message("assistant", get_text("msg_clean_need_range", lang))
                return

            for address in ranges:
                range_str = address
                cells, too_large = self._capture_cells_for_range(range_str, max_cells=300)
                if ":" in address:
                    manipulator.set_range_style(address, bg_color=fill_color)
                else:
                    manipulator.set_cell_style(address, bg_color=fill_color)
                if too_large:
                    self._record_change(get_text("msg_change_fill", lang).format(address), cells=None, undoable=False, partial=True)
                else:
                    self._record_change(get_text("msg_change_fill", lang).format(address), cells=cells, undoable=True, partial=True)
            self._chat_widget.add_message(
                "assistant", get_text("msg_quick_fill_done", lang)
            )
        except Exception as exc:
            logger.error("Hızlı doldurma hatası: %s", exc)
            self._chat_widget.add_message(
                "assistant", get_text("msg_quick_action_error", lang).format(exc)
            )

    def _quick_format_selection(self):
        """Seçili hücre/alanı başlık formatında biçimlendirir."""
        lang = self._current_lang
        if not self._bridge or not self._bridge.is_connected:
            self._chat_widget.add_message("assistant", get_text("msg_need_lo", lang))
            return

        try:
            manipulator = CellManipulator(self._bridge)
            bg_color = 0xFEF3C7  # açık sarı
            ranges = self._get_selection_ranges()
            if not ranges:
                self._chat_widget.add_message("assistant", get_text("msg_clean_need_range", lang))
                return

            for address in ranges:
                range_str = address
                cells, too_large = self._capture_cells_for_range(range_str, max_cells=300)
                if ":" in address:
                    manipulator.set_range_style(
                        address, bold=True, bg_color=bg_color, h_align="center", wrap_text=True
                    )
                else:
                    manipulator.set_cell_style(
                        address, bold=True, bg_color=bg_color, h_align="center", wrap_text=True
                    )
                if too_large:
                    self._record_change(get_text("msg_change_format", lang).format(address), cells=None, undoable=False, partial=True)
                else:
                    self._record_change(get_text("msg_change_format", lang).format(address), cells=cells, undoable=True, partial=True)
            self._chat_widget.add_message(
                "assistant", get_text("msg_quick_format_done", lang)
            )
        except Exception as exc:
            logger.error("Hızlı format hatası: %s", exc)
            self._chat_widget.add_message(
                "assistant", get_text("msg_quick_action_error", lang).format(exc)
            )

    def _quick_make_table(self):
        """Seçili aralığı tablo görünümüne getirir (başlık + çizgiler)."""
        lang = self._current_lang
        if not self._bridge or not self._bridge.is_connected:
            self._chat_widget.add_message("assistant", get_text("msg_need_lo", lang))
            return

        try:
            manipulator = CellManipulator(self._bridge)
            ranges = self._get_selection_ranges()
            if not ranges:
                self._chat_widget.add_message("assistant", get_text("msg_table_need_range", lang))
                return

            for address in ranges:
                if ":" not in address:
                    continue
                cells, too_large = self._capture_cells_for_range(address, max_cells=300)

                # Başlık satırı
                start, end = LibreOfficeBridge.parse_range_string(address)
                header_range = f"{LibreOfficeBridge._index_to_column(start[0])}{start[1] + 1}:{LibreOfficeBridge._index_to_column(end[0])}{start[1] + 1}"
                manipulator.set_range_style(header_range, bold=True, bg_color=0xDCFCE7, h_align="center", wrap_text=True)

                # Tüm aralık için kenarlık
                manipulator.set_range_style(address, border_color=0x94A3B8)

                if too_large:
                    self._record_change(get_text("msg_change_table", lang).format(address), cells=None, undoable=False, partial=True)
                else:
                    self._record_change(get_text("msg_change_table", lang).format(address), cells=cells, undoable=True, partial=True)

            self._chat_widget.add_message("assistant", get_text("msg_table_done", lang))

        except Exception as exc:
            logger.error("Tablo oluşturma hatası: %s", exc)
            self._chat_widget.add_message(
                "assistant", get_text("msg_quick_action_error", lang).format(exc)
            )

    def _quick_header_format(self):
        """Seçili satırı başlık olarak biçimlendirir."""
        lang = self._current_lang
        if not self._bridge or not self._bridge.is_connected:
            self._chat_widget.add_message("assistant", get_text("msg_need_lo", lang))
            return

        try:
            manipulator = CellManipulator(self._bridge)
            ranges = self._get_selection_ranges()
            if not ranges:
                self._chat_widget.add_message("assistant", get_text("msg_table_need_range", lang))
                return

            for address in ranges:
                if ":" in address:
                    start, end = LibreOfficeBridge.parse_range_string(address)
                    header_range = f"{LibreOfficeBridge._index_to_column(start[0])}{start[1] + 1}:{LibreOfficeBridge._index_to_column(end[0])}{start[1] + 1}"
                else:
                    header_range = address

                cells, too_large = self._capture_cells_for_range(header_range, max_cells=300)

                manipulator.set_range_style(header_range, bold=True, bg_color=0xFEF3C7, h_align="center", wrap_text=True)

                if too_large:
                    self._record_change(get_text("msg_change_header", lang).format(header_range), cells=None, undoable=False, partial=True)
                else:
                    self._record_change(get_text("msg_change_header", lang).format(header_range), cells=cells, undoable=True, partial=True)

            self._chat_widget.add_message("assistant", get_text("msg_header_done", lang))

        except Exception as exc:
            logger.error("Başlık biçimlendirme hatası: %s", exc)
            self._chat_widget.add_message(
                "assistant", get_text("msg_quick_action_error", lang).format(exc)
            )

    def _quick_highlight_outliers(self):
        """Seçili aralıkta aykırı değerleri vurgular."""
        lang = self._current_lang
        if not self._bridge or not self._bridge.is_connected:
            self._chat_widget.add_message("assistant", get_text("msg_need_lo", lang))
            return

        try:
            inspector = CellInspector(self._bridge)
            manipulator = CellManipulator(self._bridge)
            ranges = self._get_selection_ranges()
            if not ranges:
                self._chat_widget.add_message("assistant", get_text("msg_outlier_need_range", lang))
                return

            applied_total = 0
            for address in ranges:
                if ":" not in address:
                    continue

                cells, too_large = self._capture_cells_for_range(address, max_cells=300)
                grid = inspector.read_range(address)

                numeric_cells = []
                for row in grid:
                    for cell in row:
                        val = cell.get("value")
                        if isinstance(val, (int, float)):
                            numeric_cells.append((cell.get("address"), float(val)))

                if len(numeric_cells) < 8:
                    continue

                nums = [v for _a, v in numeric_cells]
                mean = sum(nums) / len(nums)
                variance = sum((x - mean) ** 2 for x in nums) / max(1, len(nums) - 1)
                std = variance ** 0.5
                if std <= 0:
                    continue

                outliers = []
                for addr, v in numeric_cells:
                    z = abs(v - mean) / std
                    if z >= 3.0:
                        outliers.append(addr)

                for addr in outliers:
                    manipulator.set_cell_style(addr, bg_color=0xFECACA)

                if too_large:
                    self._record_change(get_text("msg_change_outliers", lang).format(address), cells=None, undoable=False, partial=True)
                else:
                    self._record_change(get_text("msg_change_outliers", lang).format(address), cells=cells, undoable=True, partial=True)

                applied_total += len(outliers)

            if applied_total == 0:
                self._chat_widget.add_message("assistant", get_text("msg_outlier_not_enough", lang))
            else:
                self._chat_widget.add_message(
                    "assistant", get_text("msg_outlier_done", lang).format(applied_total)
                )

        except Exception as exc:
            logger.error("Aykırı vurgulama hatası: %s", exc)
            self._chat_widget.add_message(
                "assistant", get_text("msg_quick_action_error", lang).format(exc)
            )

    def _clean_trim_whitespace(self):
        """Seçili aralıkta baştaki/sondaki boşlukları temizler."""
        lang = self._current_lang
        if not self._bridge or not self._bridge.is_connected:
            self._chat_widget.add_message("assistant", get_text("msg_need_lo", lang))
            return

        try:
            inspector = CellInspector(self._bridge)
            manipulator = CellManipulator(self._bridge)
            ranges = self._get_selection_ranges()
            if not ranges:
                self._chat_widget.add_message("assistant", get_text("msg_clean_need_range", lang))
                return

            changed = 0
            for address in ranges:
                cells, too_large = self._capture_cells_for_range(address, max_cells=300)
                grid = inspector.read_range(address)
                for row in grid:
                    for cell in row:
                        val = cell.get("value")
                        if isinstance(val, str):
                            trimmed = val.strip()
                            if trimmed != val:
                                manipulator.write_value(cell.get("address"), trimmed)
                                changed += 1

                if too_large:
                    self._record_change(get_text("msg_change_clean", lang).format(address), cells=None, undoable=False, partial=True)
                else:
                    self._record_change(get_text("msg_change_clean", lang).format(address), cells=cells, undoable=True, partial=True)

            self._chat_widget.add_message("assistant", get_text("msg_clean_done", lang).format(changed))
        except Exception as exc:
            logger.error("Boşluk temizleme hatası: %s", exc)
            self._chat_widget.add_message(
                "assistant", get_text("msg_quick_action_error", lang).format(exc)
            )

    def _clean_text_to_number(self):
        """Seçili aralıkta sayıya benzer metinleri sayıya çevirir."""
        lang = self._current_lang
        if not self._bridge or not self._bridge.is_connected:
            self._chat_widget.add_message("assistant", get_text("msg_need_lo", lang))
            return

        try:
            inspector = CellInspector(self._bridge)
            manipulator = CellManipulator(self._bridge)
            ranges = self._get_selection_ranges()
            if not ranges:
                self._chat_widget.add_message("assistant", get_text("msg_clean_need_range", lang))
                return

            changed = 0
            for address in ranges:
                cells, too_large = self._capture_cells_for_range(address, max_cells=300)
                grid = inspector.read_range(address)
                for row in grid:
                    for cell in row:
                        val = cell.get("value")
                        if isinstance(val, str):
                            raw = val.strip().replace(" ", "")
                            if not raw:
                                continue
                            # Binlik ayırıcıları temizle
                            raw = raw.replace(",", "").replace(".", ".")
                            try:
                                num = float(raw)
                                manipulator.write_value(cell.get("address"), num)
                                changed += 1
                            except ValueError:
                                continue

                if too_large:
                    self._record_change(get_text("msg_change_clean", lang).format(address), cells=None, undoable=False, partial=True)
                else:
                    self._record_change(get_text("msg_change_clean", lang).format(address), cells=cells, undoable=True, partial=True)

            self._chat_widget.add_message("assistant", get_text("msg_clean_number_done", lang).format(changed))
        except Exception as exc:
            logger.error("Sayıya çevirme hatası: %s", exc)
            self._chat_widget.add_message(
                "assistant", get_text("msg_quick_action_error", lang).format(exc)
            )

    def _clean_text_to_date(self):
        """Seçili aralıkta tarih benzeri metinleri tarih formatına çevirir."""
        lang = self._current_lang
        if not self._bridge or not self._bridge.is_connected:
            self._chat_widget.add_message("assistant", get_text("msg_need_lo", lang))
            return

        try:
            inspector = CellInspector(self._bridge)
            manipulator = CellManipulator(self._bridge)
            ranges = self._get_selection_ranges()
            if not ranges:
                self._chat_widget.add_message("assistant", get_text("msg_clean_need_range", lang))
                return

            changed = 0
            for address in ranges:
                cells, too_large = self._capture_cells_for_range(address, max_cells=300)
                grid = inspector.read_range(address)
                for row in grid:
                    for cell in row:
                        val = cell.get("value")
                        if isinstance(val, str):
                            raw = val.strip()
                            m = re.match(r'^(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})$', raw)
                            if not m:
                                continue
                            d, mth, y = m.groups()
                            if len(y) == 2:
                                y = "20" + y
                            try:
                                date_str = f"{y}-{int(mth):02d}-{int(d):02d}"
                                manipulator.write_value(cell.get("address"), date_str)
                                manipulator.set_number_format(cell.get("address"), "YYYY-MM-DD")
                                changed += 1
                            except Exception:
                                continue

                if too_large:
                    self._record_change(get_text("msg_change_clean", lang).format(address), cells=None, undoable=False, partial=True)
                else:
                    self._record_change(get_text("msg_change_clean", lang).format(address), cells=cells, undoable=True, partial=True)

            self._chat_widget.add_message("assistant", get_text("msg_clean_date_done", lang).format(changed))
        except Exception as exc:
            logger.error("Tarihe çevirme hatası: %s", exc)
            self._chat_widget.add_message(
                "assistant", get_text("msg_quick_action_error", lang).format(exc)
            )

    def _quick_formulaize_selection(self):
        """Seçili aralıkta otomatik formül önerir ve uygular."""
        lang = self._current_lang
        if not self._bridge or not self._bridge.is_connected:
            self._chat_widget.add_message("assistant", get_text("msg_need_lo", lang))
            return
        if not self._provider:
            self._chat_widget.add_message("assistant", get_text("msg_llm_not_configured", lang))
            return

        try:
            ranges = self._get_selection_ranges()
            if not ranges:
                self._chat_widget.add_message("assistant", get_text("msg_formulaize_need_range", lang))
                return
            if len(ranges) > 1:
                self._chat_widget.add_message("assistant", get_text("msg_formulaize_multi", lang))
                return

            address = ranges[0]
            inspector = CellInspector(self._bridge)
            grid = inspector.read_range(address)

            start, end = LibreOfficeBridge.parse_range_string(address)
            row_count = end[1] - start[1] + 1
            col_count = end[0] - start[0] + 1
            if row_count < 2 or col_count < 2:
                self._chat_widget.add_message("assistant", get_text("msg_formulaize_need_range", lang))
                return

            # Sample first 15 rows
            sample_rows = min(15, row_count)
            headers = []
            first_row = grid[0] if grid else []
            if all(isinstance(c.get("value"), str) and c.get("value") for c in first_row):
                headers = [str(c.get("value")) for c in first_row]
                data_start = 1
            else:
                data_start = 0

            sample = []
            for r in range(data_start, min(row_count, data_start + sample_rows)):
                row_vals = []
                for c in range(col_count):
                    row_vals.append(grid[r][c].get("value"))
                sample.append(row_vals)

            col_letters = [LibreOfficeBridge._index_to_column(start[0] + i) for i in range(col_count)]
            prompt = (
                "Analyze the table and infer row-wise arithmetic relationships.\n"
                "Return ONLY valid JSON like:\n"
                "{\"formulas\":[{\"target_col\":\"C\",\"op\":\"mul\",\"source_cols\":[\"A\",\"B\"],\"confidence\":0.9}]}.\n"
                "Allowed ops: add, sub, mul, div.\n"
                "Use column letters from this selection.\n"
            )
            payload = {
                "columns": col_letters,
                "headers": headers,
                "sample_rows": sample,
                "note": "Infer formulas where target column equals operation of source columns in the same row.",
            }

            result = self._provider.chat_completion(
                [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                tools=None,
            )
            content = (result.get("content") or "").strip()
            try:
                formulas = json.loads(content).get("formulas", [])
            except json.JSONDecodeError:
                # try extract JSON block
                m = re.search(r"\{.*\}", content, re.DOTALL)
                formulas = json.loads(m.group(0)).get("formulas", []) if m else []

            if not formulas:
                self._chat_widget.add_message("assistant", get_text("msg_formulaize_none", lang))
                return

            preview_lines = [get_text("msg_formulaize_preview", lang)]
            for f in formulas:
                target_col = f.get("target_col")
                op = f.get("op")
                sources = f.get("source_cols") or []
                if not target_col or len(sources) != 2:
                    continue
                preview_lines.append(f"- {target_col} = {sources[0]} {op} {sources[1]}")

            if not self._confirm_formulaize("\n".join(preview_lines)):
                self._chat_widget.add_message("assistant", get_text("msg_formulaize_cancelled", lang))
                return

            # Validate and apply
            cells_snapshot, too_large = self._capture_cells_for_range(address, max_cells=300)
            applied = 0

            def _to_num(v):
                if isinstance(v, (int, float)):
                    return float(v)
                if isinstance(v, str):
                    raw = v.strip().replace(" ", "").replace(",", "")
                    try:
                        return float(raw)
                    except ValueError:
                        return None
                return None

            for f in formulas:
                target_col = f.get("target_col")
                op = f.get("op")
                sources = f.get("source_cols") or []
                if not target_col or len(sources) != 2 or op not in ("add", "sub", "mul", "div"):
                    continue
                if target_col not in col_letters or sources[0] not in col_letters or sources[1] not in col_letters:
                    continue

                t_idx = col_letters.index(target_col)
                a_idx = col_letters.index(sources[0])
                b_idx = col_letters.index(sources[1])

                # validate on sample rows
                ok = 0
                total = 0
                for r in range(data_start, row_count):
                    a = _to_num(grid[r][a_idx].get("value"))
                    b = _to_num(grid[r][b_idx].get("value"))
                    t = _to_num(grid[r][t_idx].get("value"))
                    if a is None or b is None or t is None:
                        continue
                    if op == "add":
                        calc = a + b
                    elif op == "sub":
                        calc = a - b
                    elif op == "mul":
                        calc = a * b
                    else:
                        if b == 0:
                            continue
                        calc = a / b
                    total += 1
                    if abs(calc - t) <= max(1e-6, 0.01 * abs(calc)):
                        ok += 1

                if total == 0 or ok / total < 0.8:
                    continue

                # apply formulas only where target looks computed
                manipulator = CellManipulator(self._bridge)
                for r in range(data_start, row_count):
                    a = _to_num(grid[r][a_idx].get("value"))
                    b = _to_num(grid[r][b_idx].get("value"))
                    t = _to_num(grid[r][t_idx].get("value"))
                    if a is None or b is None or t is None:
                        continue
                    if op == "add":
                        calc = a + b
                        op_sym = "+"
                    elif op == "sub":
                        calc = a - b
                        op_sym = "-"
                    elif op == "mul":
                        calc = a * b
                        op_sym = "*"
                    else:
                        if b == 0:
                            continue
                        calc = a / b
                        op_sym = "/"
                    if abs(calc - t) <= max(1e-6, 0.01 * abs(calc)):
                        row_num = start[1] + r + 1
                        formula = f"={sources[0]}{row_num}{op_sym}{sources[1]}{row_num}"
                        manipulator.write_formula(f"{target_col}{row_num}", formula)
                        applied += 1

            if applied == 0:
                self._chat_widget.add_message("assistant", get_text("msg_formulaize_none", lang))
                return

            if too_large:
                self._record_change(get_text("msg_change_formulaize", lang).format(address), cells=None, undoable=False, partial=True)
            else:
                self._record_change(get_text("msg_change_formulaize", lang).format(address), cells=cells_snapshot, undoable=True, partial=True)

            self._chat_widget.add_message(
                "assistant", get_text("msg_formulaize_done", lang).format(applied)
            )

        except Exception as exc:
            logger.error("Formülleştirme hatası: %s", exc)
            self._chat_widget.add_message(
                "assistant", get_text("msg_formulaize_error", lang).format(exc)
            )

    def _confirm_formulaize(self, message: str) -> bool:
        lang = self._current_lang
        reply = QMessageBox.question(
            self,
            get_text("msg_formulaize_title", lang),
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return reply == QMessageBox.Yes

    def _clear_conversation(self):
        """Sohbet gecmisini temizler."""
        self._conversation.clear()
        self._conversation_summary = ""
        self._chat_widget.clear_chat()

    def _record_change(self, summary: str, cells: list | None = None, undoable: bool = True, partial: bool = False):
        """Değişiklik kaydı oluşturur."""
        if self._is_undoing:
            return
        entry = {
            "summary": summary,
            "undoable": undoable and bool(cells),
            "partial": partial,
            "cells": cells or [],
        }
        self._change_log.append(entry)
        if len(self._change_log) > 100:
            self._change_log.pop(0)

    def _capture_cells_for_range(self, range_str: str, max_cells: int = 500):
        """Aralıktaki hücreleri geri alma için snapshot alır."""
        start, end = LibreOfficeBridge.parse_range_string(range_str)
        row_count = end[1] - start[1] + 1
        col_count = end[0] - start[0] + 1
        total = row_count * col_count
        if total > max_cells:
            return None, True

        inspector = CellInspector(self._bridge)
        cells = []
        for row in range(start[1], end[1] + 1):
            for col in range(start[0], end[0] + 1):
                addr = f"{LibreOfficeBridge._index_to_column(col)}{row + 1}"
                details = inspector.get_cell_details(addr)
                cells.append({
                    "address": addr,
                    "type": details.get("type"),
                    "formula": details.get("formula"),
                    "value": details.get("value"),
                    "background_color": details.get("background_color"),
                    "number_format": details.get("number_format"),
                    "font_color": details.get("font_color"),
                    "font_size": details.get("font_size"),
                    "bold": details.get("bold"),
                    "italic": details.get("italic"),
                    "h_align": details.get("h_align"),
                    "v_align": details.get("v_align"),
                    "wrap_text": details.get("wrap_text"),
                })

        return cells, False

    def _restore_cells(self, cells: list):
        """Snapshot'tan hücreleri geri yükler."""
        manipulator = CellManipulator(self._bridge)
        for cell in cells:
            address = cell.get("address")
            ctype = cell.get("type")
            formula = cell.get("formula")
            value = cell.get("value")
            bg = cell.get("background_color")
            num_fmt = cell.get("number_format")
            font_color = cell.get("font_color")
            font_size = cell.get("font_size")
            bold = cell.get("bold")
            italic = cell.get("italic")
            h_align = cell.get("h_align")
            v_align = cell.get("v_align")
            wrap_text = cell.get("wrap_text")

            if ctype == "formula" and formula is not None:
                manipulator.write_formula(address, formula)
            elif ctype in ("value", "text"):
                manipulator.write_value(address, value)
            elif ctype == "empty":
                manipulator.clear_cell(address)
            else:
                manipulator.write_value(address, value)

            style_kwargs = {}
            if bg is not None:
                style_kwargs["bg_color"] = bg
            if font_color is not None:
                style_kwargs["font_color"] = font_color
            if font_size is not None:
                style_kwargs["font_size"] = font_size
            if bold is not None:
                if isinstance(bold, (int, float)):
                    style_kwargs["bold"] = bold >= 150
                else:
                    style_kwargs["bold"] = bool(bold)
            if italic is not None:
                if isinstance(italic, (int, float)):
                    style_kwargs["italic"] = italic != 0
                else:
                    style_kwargs["italic"] = bool(italic)
            if isinstance(h_align, str):
                style_kwargs["h_align"] = h_align
            if isinstance(v_align, str):
                style_kwargs["v_align"] = v_align
            if wrap_text is not None:
                style_kwargs["wrap_text"] = wrap_text

            if style_kwargs:
                try:
                    manipulator.set_cell_style(address, **style_kwargs)
                except Exception:
                    pass

            if isinstance(num_fmt, str) and num_fmt:
                try:
                    manipulator.set_number_format(address, num_fmt)
                except Exception:
                    pass

    def _on_show_changes(self):
        """Değişiklik geçmişini gösterir."""
        lang = self._current_lang
        if not self._change_log:
            self._chat_widget.add_message("assistant", get_text("msg_no_changes", lang))
            return

        lines = ["**Değişiklik Geçmişi (son 10)**"]
        for idx, entry in enumerate(self._change_log[-10:], start=1):
            flags = []
            if entry.get("undoable"):
                flags.append("undo")
            if entry.get("partial"):
                flags.append("partial")
            flag_text = f" [{' / '.join(flags)}]" if flags else ""
            lines.append(f"{idx}. {entry.get('summary')}{flag_text}")

        self._chat_widget.add_message("assistant", "\n".join(lines))

    def _on_undo_last_change(self):
        """Son geri alınabilir değişikliği geri alır."""
        lang = self._current_lang
        if not self._bridge or not self._bridge.is_connected:
            self._chat_widget.add_message("assistant", get_text("msg_need_lo", lang))
            return

        for i in range(len(self._change_log) - 1, -1, -1):
            entry = self._change_log[i]
            if entry.get("undoable") and entry.get("cells"):
                try:
                    self._is_undoing = True
                    self._restore_cells(entry["cells"])
                    self._change_log.pop(i)
                    self._record_change(
                        get_text("msg_undo_done", lang).format(entry.get("summary")),
                        cells=None,
                        undoable=False,
                    )
                    self._chat_widget.add_message(
                        "assistant", get_text("msg_undo_done", lang).format(entry.get("summary"))
                    )
                    return
                except Exception as exc:
                    logger.error("Geri alma hatası: %s", exc)
                    self._chat_widget.add_message(
                        "assistant", get_text("msg_undo_error", lang).format(exc)
                    )
                    return
                finally:
                    self._is_undoing = False

        self._chat_widget.add_message("assistant", get_text("msg_undo_none", lang))

    def _save_chat(self):
        """Sohbet geçmişini dosyaya kaydeder."""
        lang = self._current_lang
        path, _ = QFileDialog.getSaveFileName(
            self,
            get_text("menu_save_chat", lang),
            "conversation.json",
            "JSON Files (*.json)",
        )
        if not path:
            return
        payload = {
            "conversation": self._conversation,
            "summary": self._conversation_summary,
            "change_log": self._change_log,
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            self._chat_widget.add_message("assistant", get_text("msg_chat_saved", lang).format(path))
        except Exception as exc:
            self._chat_widget.add_message(
                "assistant", get_text("msg_chat_save_error", lang).format(exc)
            )

    def _load_chat(self):
        """Sohbet geçmişini dosyadan yükler."""
        lang = self._current_lang
        path, _ = QFileDialog.getOpenFileName(
            self,
            get_text("menu_load_chat", lang),
            "",
            "JSON Files (*.json)",
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            self._conversation = payload.get("conversation", [])
            self._conversation_summary = payload.get("summary", "")
            self._change_log = payload.get("change_log", [])
            self._chat_widget.clear_chat()
            for msg in self._conversation:
                role = msg.get("role")
                content = msg.get("content")
                if role in ("user", "assistant") and content:
                    self._chat_widget.add_message(role, content)
            self._chat_widget.add_message("assistant", get_text("msg_chat_loaded", lang).format(path))
        except Exception as exc:
            self._chat_widget.add_message(
                "assistant", get_text("msg_chat_load_error", lang).format(exc)
            )

    def _export_report(self):
        """Sohbet raporunu HTML olarak dışa aktarır."""
        lang = self._current_lang
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            get_text("toolbar_export_report", lang),
            "report.html",
            "HTML Files (*.html);;PDF Files (*.pdf)",
        )
        if not path:
            return

        try:
            html = self._build_report_html()
            is_pdf = path.lower().endswith(".pdf") or "PDF" in selected_filter
            if is_pdf:
                if not path.lower().endswith(".pdf"):
                    path += ".pdf"
                doc = QTextDocument()
                doc.setHtml(html)
                doc.printToPdf(path)
            else:
                if not path.lower().endswith(".html"):
                    path += ".html"
                with open(path, "w", encoding="utf-8") as f:
                    f.write(html)
            self._chat_widget.add_message(
                "assistant", get_text("msg_report_saved", lang).format(path)
            )
        except Exception as exc:
            self._chat_widget.add_message(
                "assistant", get_text("msg_report_save_error", lang).format(exc)
            )

    def _build_report_html(self) -> str:
        """Sohbet raporunu HTML olarak üretir."""
        from datetime import datetime
        from ui.chat_widget import _markdown_to_html

        title = "ArasAI Report"
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        parts = [
            "<html><head><meta charset='utf-8'>",
            "<style>",
            "body{font-family:Arial,sans-serif;background:#f8fafc;color:#0f172a;padding:24px;}",
            ".meta{color:#64748b;font-size:12px;margin-bottom:16px;}",
            ".msg{margin:12px 0;padding:12px;border-radius:8px;}",
            ".user{background:#e2e8f0;}",
            ".assistant{background:#ffffff;border:1px solid #e2e8f0;}",
            ".header{font-weight:bold;margin-bottom:6px;}",
            "</style></head><body>",
            f"<h2>{title}</h2>",
            f"<div class='meta'>{ts}</div>",
        ]

        for msg in self._conversation:
            role = msg.get("role")
            content = msg.get("content") or ""
            if role not in ("user", "assistant"):
                continue
            header = "User" if role == "user" else "Assistant"
            css = "user" if role == "user" else "assistant"
            if role == "assistant":
                body = _markdown_to_html(content)
            else:
                body = content.replace("\n", "<br>")
            parts.append(f"<div class='msg {css}'>")
            parts.append(f"<div class='header'>{header}</div>")
            parts.append(f"<div class='body'>{body}</div>")
            parts.append("</div>")

        parts.append("</body></html>")
        return "".join(parts)

    def _open_settings(self):
        """Ayarlar diyalogunu acar."""
        dialog = SettingsDialog(self)
        if dialog.exec_() == SettingsDialog.Accepted:
            self._apply_theme()
            self._init_provider()
            self._update_status_bar()

            # Saglayici menusunu guncelle
            if self._settings.provider == "ollama":
                self._action_ollama.setChecked(True)
            elif self._settings.provider == "gemini":
                self._action_gemini.setChecked(True)
            else:
                self._action_openrouter.setChecked(True)
            
            # Dil ayari degismis olabilir
            if self._current_lang != self._settings.language:
                self._current_lang = self._settings.language
                self._update_ui_text()
                # Dil menusunu guncelle
                if self._current_lang == "tr":
                    self._action_lang_tr.setChecked(True)
                elif self._current_lang == "en":
                    self._action_lang_en.setChecked(True)
                else:
                    self._action_lang_system.setChecked(True)


    def _on_provider_changed(self, action: QAction):
        """Saglayici menusunden degisiklik yapildiginda cagirilir.

        Args:
            action: Secilen menu eylemi.
        """
        if action == self._action_ollama:
            self._settings.provider = "ollama"
        elif action == self._action_gemini:
            self._settings.provider = "gemini"
        else:
            self._settings.provider = "openrouter"

        self._settings.save()
        self._init_provider()
        self._update_status_bar()

    def _toggle_always_on_top(self, checked: bool):
        """Pencereyi her zaman ustte tutar veya birakir.

        Args:
            checked: True ise her zaman ustte, False ise normal.
        """
        if checked:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()

    def _show_about(self):
        """Hakkinda diyalogunu gosterir."""
        QMessageBox.about(
            self,
            get_text("about_title", self._current_lang),
            get_text("about_content", self._current_lang),
        )

    def closeEvent(self, event):
        """Pencere kapatildiginda baglantilari ve bellegi temizler."""
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(2000)

        if self._bridge and self._bridge.is_connected:
            self._bridge.disconnect()

        # LLM provider'ı kapat
        if self._provider:
            self._provider.close()
            self._provider = None

        # Bellek temizligi
        self._conversation.clear()
        self._conversation_summary = ""
        self._change_log.clear()

        event.accept()

    def _on_selection_changed(self, source):
        """LibreOffice'te secim degistiginde cagirilir.
        
        Args:
            source: Olay kaynagi (Controller).
        """
        try:
            selection = source.getSelection()
            # Yeni çoklu seçim destekli metod
            address = LibreOfficeBridge.get_selection_address(selection)
            ranges = LibreOfficeBridge.get_selection_ranges(selection)
            
            prefix = get_text("status_selected", self._current_lang)
            self._cell_status_label.setText(f"{prefix}: {address}")
            self._update_selection_preview(ranges if ranges else [address])

        except Exception as e:
            logger.error("Seçim işleme hatası: %s", e)
            self._cell_status_label.setText("-")
            self._selection_stats.setText(get_text("preview_error", self._current_lang))

    def _update_selection_preview(self, ranges: list):
        """Seçim için mini özet panelini günceller."""
        lang = self._current_lang
        if not self._bridge or not self._bridge.is_connected:
            self._selection_stats.setText(get_text("preview_no_lo", lang))
            self._selection_samples.setText("")
            return

        if not ranges:
            self._selection_stats.setText(get_text("preview_empty", lang))
            self._selection_samples.setText("")
            return

        try:
            max_full = 500
            inspector = CellInspector(self._bridge)
            counts = {"empty": 0, "value": 0, "text": 0, "formula": 0, "unknown": 0}
            samples = []
            total_cells = 0
            rows_total = 0
            cols_total = 0

            for rng in ranges:
                if not rng or rng in ("-", "Bilinmeyen Seçim", "Hata"):
                    continue
                start, end = LibreOfficeBridge.parse_range_string(rng)
                row_count = end[1] - start[1] + 1
                col_count = end[0] - start[0] + 1
                total = row_count * col_count
                total_cells += total
                rows_total += row_count
                cols_total += col_count

                if total <= max_full:
                    grid = inspector.read_range(rng)
                else:
                    sample_rows = min(3, row_count)
                    sample_cols = min(3, col_count)
                    end_col = start[0] + sample_cols - 1
                    end_row = start[1] + sample_rows - 1
                    sample_range = f"{LibreOfficeBridge._index_to_column(start[0])}{start[1] + 1}:{LibreOfficeBridge._index_to_column(end_col)}{end_row + 1}"
                    grid = inspector.read_range(sample_range)

                for row in grid:
                    for cell in row:
                        counts[cell.get("type", "unknown")] = counts.get(cell.get("type", "unknown"), 0) + 1
                        if len(samples) < 3:
                            val = cell.get("value")
                            if val not in (None, ""):
                                samples.append(str(val))

            if total_cells == 0:
                self._selection_stats.setText(get_text("preview_empty", lang))
                self._selection_samples.setText("")
                return

            stats = get_text("preview_stats", lang).format(
                rows=rows_total,
                cols=cols_total,
                total=total_cells,
                empty=counts.get("empty", 0),
                values=counts.get("value", 0),
                text=counts.get("text", 0),
                formula=counts.get("formula", 0),
            )

            if len(ranges) > 1:
                stats = get_text("preview_multi_stats", lang).format(count=len(ranges)) + " | " + stats

            # örnek değerler (ilk 3)
            sample_text = get_text("preview_samples", lang).format(
                samples=", ".join(samples) if samples else "-"
            )

            self._selection_stats.setText(stats)
            self._selection_samples.setText(sample_text)

        except Exception as exc:
            logger.error("Önizleme hatası: %s", exc)
            self._selection_stats.setText(get_text("preview_error", lang))
            self._selection_samples.setText("")
