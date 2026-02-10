"""Ana uygulama penceresi - Tum UI bilesenlerini bir araya getirir."""

import json
import logging

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QMainWindow,
    QSplitter,
    QAction,
    QActionGroup,
    QToolBar,
    QLabel,
    QMessageBox,
    QApplication,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QFrame,
    QMenuBar,
)

from config.settings import Settings
from core import LibreOfficeBridge, CellInspector, CellManipulator, SheetAnalyzer, ErrorDetector, LibreOfficeEventListener
from llm import OpenRouterProvider, OllamaProvider
from llm.tool_definitions import TOOLS, ToolDispatcher
from llm.prompt_templates import SYSTEM_PROMPT

from .chat_widget import ChatWidget
from .settings_dialog import SettingsDialog
from .styles import get_theme
from .i18n import get_text


logger = logging.getLogger(__name__)


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
        self._pending_tool_calls = []
        self._skip_lo_connect = skip_lo_connect
        
        # Dil ayarı
        self._current_lang = self._settings.language

        self._setup_window()
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
        
        # Toolbar
        self._toolbar.setWindowTitle(get_text("toolbar_title", lang))
        self._connect_action.setText(get_text("toolbar_connect", lang))
        self._connect_action.setToolTip(get_text("toolbar_connect_tooltip", lang))
        self._analyze_action.setText(get_text("toolbar_analyze", lang))
        self._analyze_action.setToolTip(get_text("toolbar_analyze_tooltip", lang))
        self._clear_action.setText(get_text("toolbar_clear", lang))
        self._clear_action.setToolTip(get_text("toolbar_clear_tooltip", lang))
        
        # Chat Widget
        self._chat_widget.update_language(lang)
        
        self._update_status_bar()

    def _setup_window(self):
        """Pencere ozelliklerini ayarlar."""
        self.setWindowTitle("Aras") # Placeholder, _update_ui_text will fix
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
            width = 400
            height = geo.height()
            x = geo.x() + geo.width() - width
            y = geo.y()
            self.setGeometry(x, y, width, height)

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

        title_label = QLabel("Aras Asistan")
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

        # ToolBar
        self._toolbar = QToolBar("Ana Araç Çubuğu")
        self._toolbar.setMovable(False)
        self._toolbar.setFloatable(False)
        main_layout.addWidget(self._toolbar)
        self._setup_toolbar()

        # Chat Widget
        self._chat_widget = ChatWidget()
        self._chat_widget.message_sent.connect(self._on_message_sent)
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

    def _setup_menus(self):
        """Menu cubuklarini olusturur."""
        menubar = self._menubar
        menubar.clear()

        # Dosya menusu
        self._file_menu = menubar.addMenu("Dosya")

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

        if self._settings.provider == "ollama":
            self._action_ollama.setChecked(True)
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

    def _setup_toolbar(self):
        """Arac cubugunu olusturur."""
        self._toolbar.setIconSize(self._toolbar.iconSize()) # Force update

        self._connect_action = QAction("Bağlan", self)
        self._connect_action.triggered.connect(self._connect_lo)
        self._toolbar.addAction(self._connect_action)

        self._analyze_action = QAction("Hücre Analizi", self)
        self._analyze_action.triggered.connect(self._on_analyze_cell)
        self._toolbar.addAction(self._analyze_action)

        self._toolbar.addSeparator()

        self._clear_action = QAction("Geçmişi Sil", self)
        self._clear_action.triggered.connect(self._clear_conversation)
        self._toolbar.addAction(self._clear_action)

    def _setup_statusbar(self, layout):
        """Durum cubugunu olusturur."""
        self._lo_status_label = QLabel()
        self._llm_status_label = QLabel()
        self._cell_status_label = QLabel() # Secili hucre adresi

        # Modernleştirilmiş minimalist görünüm
        self._lo_status_label.setContentsMargins(0, 0, 8, 0)
        self._llm_status_label.setContentsMargins(8, 0, 0, 0)
        self._cell_status_label.setStyleSheet("font-weight: bold; color: #18a303;")

        layout.addWidget(self._lo_status_label)
        layout.addWidget(self._cell_status_label)
        layout.addStretch()
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
            else:
                self._provider = OpenRouterProvider()
            self._update_status_bar()
        except Exception as exc:
            logger.error("LLM saglayici baslatilamadi: %s", exc)
            self._provider = None
            self._update_status_bar()

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

    # --- Olay yoneticileri ---

    def _on_message_sent(self, text: str):
        """Kullanici mesaji gonderildiginde cagirilir.

        Args:
            text: Kullanici mesaji.
        """
        self._chat_widget.add_message("user", text)
        self._chat_widget.set_input_enabled(False)
        self._chat_widget.show_loading()

        # Sohbet gecmisine ekle
        self._conversation.append({"role": "user", "content": text})

        # LLM'ye gonder
        self._send_to_llm()

    def _send_to_llm(self):
        """Mevcut sohbet gecmisini LLM'ye gonderir."""
        if not self._provider:
            self._chat_widget.hide_loading()
            self._chat_widget.set_input_enabled(True)
            self._chat_widget.add_message(
                "assistant", get_text("msg_llm_not_configured", self._current_lang)
            )
            return

        # Dinamik bağlam oluştur
        dynamic_context = self._build_dynamic_context()
        full_system_prompt = SYSTEM_PROMPT + dynamic_context

        messages = [{"role": "system", "content": full_system_prompt}] + self._conversation

        # Araclari her zaman gonder - LO bagli degilse dispatcher hata mesaji dondurur
        tools = TOOLS

        self._worker = LLMWorker(self._provider, messages, tools, self)
        self._worker.finished.connect(self._on_llm_response)
        self._worker.error.connect(self._on_llm_error)
        self._worker.start()

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
                    inspector, manipulator, analyzer, detector
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

    def _clear_conversation(self):
        """Sohbet gecmisini temizler."""
        self._conversation.clear()
        self._chat_widget.clear_chat()

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
        """Pencere kapatildiginda baglantilari temizler."""
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(2000)

        if self._bridge and self._bridge.is_connected:
            self._bridge.disconnect()

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
            
            prefix = get_text("status_selected", self._current_lang)
            self._cell_status_label.setText(f"{prefix}: {address}")

        except Exception as e:
            logger.error("Seçim işleme hatası: %s", e)
            self._cell_status_label.setText("-")
