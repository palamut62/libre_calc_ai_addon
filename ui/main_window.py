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
)

from config.settings import Settings
from core import LibreOfficeBridge, CellInspector, CellManipulator, SheetAnalyzer, ErrorDetector
from llm import OpenRouterProvider, OllamaProvider
from llm.tool_definitions import TOOLS, ToolDispatcher
from llm.prompt_templates import SYSTEM_PROMPT

from .chat_widget import ChatWidget
from .cell_info_widget import CellInfoWidget
from .settings_dialog import SettingsDialog
from .styles import get_theme

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

        self._setup_window()
        self._setup_ui()
        self._setup_menus()
        self._setup_toolbar()
        self._setup_statusbar()
        self._apply_theme()
        self._init_provider()

        # Başlangıçta otomatik LO bağlantısı dene
        if not self._skip_lo_connect:
            if self._connect_lo_silent():
                self._chat_widget.add_message(
                    "assistant",
                    "Merhaba! LibreOffice'e bağlandım. Tablonuzdaki verileri analiz etmeye veya formüllerinizi düzenlemeye hazırım."
                )
            else:
                self._chat_widget.add_message(
                    "assistant",
                    "Selam! LibreOffice bağlantısı henüz kurulmadı.\n\n"
                    "Başlamak için araç çubuğundaki **Bağlan** butonuna basabilir veya terminalden `./launch.sh` komutunu kullanabilirsiniz."
                )
        else:
            self._chat_widget.add_message(
                "assistant",
                "Şu an test modundayım. LibreOffice olmadan arayüzü kontrol edebilirsiniz."
            )

    def _setup_window(self):
        """Pencere ozelliklerini ayarlar."""
        self.setWindowTitle("Claude for LibreCalc")
        self.setMinimumWidth(380)

        # Her zaman üstte kal — LibreOffice'a tıklanınca arkaya düşmesin
        self.setWindowFlags(
            Qt.Window
            | Qt.WindowStaysOnTopHint
            | Qt.WindowCloseButtonHint
            | Qt.WindowMinimizeButtonHint
        )

        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            width = 400
            height = geo.height()
            x = geo.x() + geo.width() - width
            y = geo.y()
            self.setGeometry(x, y, width, height)

    def _setup_ui(self):
        """Ana arayuz bilesenlerini olusturur."""
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(1)

        self._chat_widget = ChatWidget()
        self._chat_widget.message_sent.connect(self._on_message_sent)
        splitter.addWidget(self._chat_widget)

        self._cell_info_widget = CellInfoWidget()
        splitter.addWidget(self._cell_info_widget)

        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)

        self.setCentralWidget(splitter)

    def _setup_menus(self):
        """Menu cubuklarini olusturur."""
        menubar = self.menuBar()

        # Dosya menusu
        file_menu = menubar.addMenu("Dosya")

        settings_action = QAction("Ayarlar...", self)
        settings_action.triggered.connect(self._open_settings)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        quit_action = QAction("Çıkış", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # Saglayici menusu
        provider_menu = menubar.addMenu("Sağlayıcı")
        provider_group = QActionGroup(self)
        provider_group.setExclusive(True)

        self._action_openrouter = QAction("OpenRouter", self, checkable=True)
        self._action_openrouter.setActionGroup(provider_group)
        provider_menu.addAction(self._action_openrouter)

        self._action_ollama = QAction("Ollama", self, checkable=True)
        self._action_ollama.setActionGroup(provider_group)
        provider_menu.addAction(self._action_ollama)

        if self._settings.provider == "ollama":
            self._action_ollama.setChecked(True)
        else:
            self._action_openrouter.setChecked(True)

        provider_group.triggered.connect(self._on_provider_changed)

        # Gorunum menusu
        view_menu = menubar.addMenu("Görünüm")

        self._always_on_top_action = QAction("Her Zaman Üstte", self, checkable=True)
        self._always_on_top_action.triggered.connect(self._toggle_always_on_top)
        view_menu.addAction(self._always_on_top_action)

        # Yardim menusu
        help_menu = menubar.addMenu("Yardım")

        about_action = QAction("Hakkında", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_toolbar(self):
        """Arac cubugunu olusturur."""
        toolbar = QToolBar("Ana Araç Çubuğu")
        toolbar.setMovable(False)
        toolbar.setIconSize(toolbar.iconSize()) # Force update
        self.addToolBar(toolbar)

        connect_action = QAction("Bağlan", self)
        connect_action.setToolTip("LibreOffice'e bağlan")
        connect_action.triggered.connect(self._connect_lo)
        toolbar.addAction(connect_action)

        analyze_action = QAction("Hücre Analizi", self)
        analyze_action.setToolTip("Seçili hücreyi analiz et")
        analyze_action.triggered.connect(self._on_analyze_cell)
        toolbar.addAction(analyze_action)

        toolbar.addSeparator()

        clear_action = QAction("Geçmişi Sil", self)
        clear_action.setToolTip("Sohbet geçmişini temizle")
        clear_action.triggered.connect(self._clear_conversation)
        toolbar.addAction(clear_action)

    def _setup_statusbar(self):
        """Durum cubugunu olusturur."""
        self._lo_status_label = QLabel()
        self._llm_status_label = QLabel()
        
        # Modernleştirilmiş minimalist görünüm
        self._lo_status_label.setContentsMargins(8, 0, 8, 0)
        self._llm_status_label.setContentsMargins(8, 0, 8, 0)

        self.statusBar().addWidget(self._lo_status_label)
        self.statusBar().addPermanentWidget(self._llm_status_label)

        self._update_status_bar()

    def _apply_theme(self):
        """Secili temayi uygular."""
        stylesheet = get_theme(self._settings.theme)
        self.setStyleSheet(stylesheet)

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
        # LO durumu
        if self._bridge and self._bridge.is_connected:
            self._lo_status_label.setText("  LO: Bagli")
            self._lo_status_label.setStyleSheet("color: #44bb44; font-weight: bold;")
        else:
            self._lo_status_label.setText("  LO: Bagli Degil")
            self._lo_status_label.setStyleSheet("color: #bb4444; font-weight: bold;")

        # LLM durumu
        provider_name = self._settings.provider.capitalize()
        if self._provider:
            self._llm_status_label.setText(f"LLM: {provider_name}  ")
            self._llm_status_label.setStyleSheet("color: #44bb44;")
        else:
            self._llm_status_label.setText(f"LLM: {provider_name} (hata)  ")
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
                "assistant", "LLM saglayicisi yapilandirilmamis. Lutfen Ayarlar'i kontrol edin."
            )
            return

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self._conversation

        # Araclari her zaman gonder - LO bagli degilse dispatcher hata mesaji dondurur
        tools = TOOLS

        self._worker = LLMWorker(self._provider, messages, tools, self)
        self._worker.finished.connect(self._on_llm_response)
        self._worker.error.connect(self._on_llm_error)
        self._worker.start()

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
                    "Bu islemi gerceklestirmek icin LibreOffice'e baglanmam gerekiyor "
                    "ama baglanti kurulamadi.\n\n"
                    "LibreOffice'i su komutla baslatin:\n"
                    "`libreoffice --calc --accept=\"socket,host=localhost,port=2002;urp;\"`\n\n"
                    "Sonra arac cubugundaki 'LO Baglan' butonuna basin."
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
            "assistant", f"Hata olustu: {error_msg}"
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
                self._update_status_bar()
                return True
        except Exception as exc:
            logger.warning("Otomatik LO baglantisi basarisiz: %s", exc)
        self._update_status_bar()
        return False

    def _connect_lo(self):
        """LibreOffice'e baglanir ve sonucu kullaniciya bildirir."""
        success = self._connect_lo_silent()
        if success:
            self._chat_widget.add_message(
                "assistant", "LibreOffice'e basariyla baglandi! Artik tablonuza dogrudan mudahale edebilirim."
            )
        else:
            self._chat_widget.add_message(
                "assistant",
                "LibreOffice'e baglanilamadi.\n\n"
                "LibreOffice'i su komutla baslatin:\n"
                "`libreoffice --calc --accept=\"socket,host=localhost,port=2002;urp;\"`",
            )

    def _on_analyze_cell(self):
        """Secili hucreyi analiz eder."""
        if not self._bridge or not self._bridge.is_connected:
            self._chat_widget.add_message(
                "assistant", "Once LibreOffice'e baglanmaniz gerekiyor."
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

            self._cell_info_widget.update_cell_info(details)

        except Exception as exc:
            logger.error("Hucre analiz hatasi: %s", exc)
            self._chat_widget.add_message(
                "assistant", f"Hucre analiz hatasi: {exc}"
            )

    def _clear_conversation(self):
        """Sohbet gecmisini temizler."""
        self._conversation.clear()
        self._chat_widget.clear_chat()
        self._cell_info_widget.clear()

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
            "Hakkinda",
            "<h3>LibreCalc AI Asistani</h3>"
            "<p>LibreOffice Calc icin yapay zeka destekli asistan.</p>"
            "<p>Formul analizi, hata tespiti ve tablo manipulasyonu "
            "islemlerinde yardimci olur.</p>"
            "<p>Surum: 1.0.0</p>",
        )

    def closeEvent(self, event):
        """Pencere kapatildiginda baglantilari temizler."""
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(2000)

        if self._bridge and self._bridge.is_connected:
            self._bridge.disconnect()

        event.accept()
