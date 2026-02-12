"""Ana uygulama penceresi - Minimal chat arayuzu (Claude Excel benzeri)."""

import json
import logging

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QMainWindow,
    QAction,
    QActionGroup,
    QLabel,
    QApplication,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QFrame,
    QMenuBar,
    QMenu,
)

from config.settings import Settings
from core import LibreOfficeBridge, CellInspector, CellManipulator, SheetAnalyzer, ErrorDetector
from llm import OpenRouterProvider, OllamaProvider, GeminiProvider
from llm.tool_definitions import TOOLS, ToolDispatcher
from llm.prompt_templates import SYSTEM_PROMPT

from .chat_widget import ChatWidget
from .settings_dialog import SettingsDialog
from .help_dialog import HelpDialog
from .styles import get_theme
from .i18n import get_text


logger = logging.getLogger(__name__)


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
    """Minimal ana uygulama penceresi - Sadece chat arayuzu."""

    def __init__(self, skip_lo_connect: bool = False):
        super().__init__()
        self._settings = Settings()
        self._bridge = None
        self._provider = None
        self._dispatcher = None
        self._conversation = []
        self._stream_worker = None
        self._skip_lo_connect = skip_lo_connect
        self._stream_content = ""
        self._stream_tool_calls_indexed = {}
        self._stream_tool_calls_full = []
        self._stream_has_tool_calls = False
        self._stream_started = False
        self._stop_requested = False

        self._current_lang = self._settings.language

        self._setup_window()
        self._setup_ui()
        self._apply_theme()
        self._init_provider()
        self._update_ui_text()

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

        self._help_menu.setTitle(get_text("menu_help", lang))
        self._help_action.setText(get_text("menu_help_about", lang))

        self._chat_widget.update_language(lang)
        self._update_provider_model_label()
        self._update_status_bar()

    def _setup_window(self):
        """Pencere ozelliklerini ayarlar."""
        self.setWindowTitle("Calc AI")
        self.setMinimumWidth(380)

        self.setWindowFlags(
            Qt.Window
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
        )

        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            addon_width = int(geo.width() * 0.28)
            addon_width = max(380, min(addon_width, 450))
            height = geo.height()
            x = geo.x() + geo.width() - addon_width
            y = geo.y()
            self.setGeometry(x, y, addon_width, height)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def _setup_ui(self):
        """Minimal arayuz bilesenlerini olusturur."""
        main_widget = QWidget()
        main_widget.setObjectName("main_container")

        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Custom Title Bar
        self._title_bar = QFrame()
        self._title_bar.setObjectName("custom_title_bar")
        self._title_bar.setFixedHeight(32)
        title_layout = QHBoxLayout(self._title_bar)
        title_layout.setContentsMargins(10, 0, 0, 0)
        title_layout.setSpacing(0)

        title_label = QLabel("Calc AI")
        title_label.setObjectName("title_label")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        min_btn = QPushButton("—")
        min_btn.setObjectName("title_min_btn")
        min_btn.setFixedSize(46, 32)
        min_btn.setCursor(Qt.PointingHandCursor)
        min_btn.clicked.connect(self.showMinimized)
        title_layout.addWidget(min_btn)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("title_close_btn")
        close_btn.setFixedSize(46, 32)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.close)
        title_layout.addWidget(close_btn)

        main_layout.addWidget(self._title_bar)

        # Menu Bar
        self._menubar = QMenuBar()
        self._setup_menus()
        main_layout.addWidget(self._menubar)

        # Chat Widget - Ana bileşen
        self._chat_widget = ChatWidget()
        self._chat_widget.message_sent.connect(self._on_message_sent)
        self._chat_widget.cancel_requested.connect(self._on_cancel_requested)
        main_layout.addWidget(self._chat_widget, 1)

        # Minimal Status Bar
        self._status_bar = QFrame()
        self._status_bar.setObjectName("custom_status_bar")
        self._status_bar.setFixedHeight(25)
        status_layout = QHBoxLayout(self._status_bar)
        status_layout.setContentsMargins(10, 0, 10, 0)
        self._setup_statusbar(status_layout)
        main_layout.addWidget(self._status_bar)

        self.setCentralWidget(main_widget)

    def _setup_menus(self):
        """Minimal menu cubugunu olusturur."""
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

        # Yardim menusu
        self._help_menu = menubar.addMenu("Yardım")
        self._help_action = QAction("Yardım...", self)
        self._help_action.setShortcut("F1")
        self._help_action.triggered.connect(self._open_help)
        self._help_menu.addAction(self._help_action)

    def _setup_statusbar(self, layout):
        """Minimal durum cubugunu olusturur."""
        self._lo_status_label = QLabel()
        self._llm_status_label = QLabel()

        self._lo_status_label.setContentsMargins(0, 0, 8, 0)
        self._llm_status_label.setContentsMargins(8, 0, 0, 0)

        layout.addWidget(self._lo_status_label)
        layout.addStretch()
        layout.addWidget(self._llm_status_label)

    def _apply_theme(self):
        """Secili temayi uygular."""
        theme_name = self._settings.theme

        if theme_name == "system":
            try:
                import darkdetect
                if darkdetect.isDark():
                    theme_name = "dark"
                else:
                    theme_name = "light"
            except ImportError:
                theme_name = "light"

        stylesheet = get_theme(theme_name)
        self.setStyleSheet(stylesheet)

        if hasattr(self, '_chat_widget'):
            self._chat_widget.update_theme(theme_name)

    def _on_theme_changed(self, action: QAction):
        theme = action.data()
        self._settings.theme = theme
        self._settings.save()
        self._apply_theme()

    def _on_language_changed(self, action: QAction):
        lang = action.data()
        self._settings.language = lang
        self._settings.save()
        self._current_lang = lang
        self._update_ui_text()

    def _on_provider_changed(self, action: QAction):
        """Saglayici degistiginde cagirilir."""
        text = action.text().lower()
        if text == "ollama":
            self._settings.provider = "ollama"
        elif text == "gemini":
            self._settings.provider = "gemini"
        else:
            self._settings.provider = "openrouter"
        self._settings.save()
        self._init_provider()
        self._update_status_bar()
        self._update_provider_model_label()

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

        if self._bridge and self._bridge.is_connected:
            self._lo_status_label.setText(f"  {get_text('status_lo_connected', lang)}")
            self._lo_status_label.setStyleSheet("color: #44bb44; font-weight: bold;")
        else:
            self._lo_status_label.setText(f"  {get_text('status_lo_disconnected', lang)}")
            self._lo_status_label.setStyleSheet("color: #bb4444; font-weight: bold;")

        provider_name = self._settings.provider.capitalize()
        if self._provider:
            self._llm_status_label.setText(f"LLM: {provider_name}  ")
            self._llm_status_label.setStyleSheet("color: #44bb44;")
        else:
            error_text = get_text("status_llm_error", lang)
            self._llm_status_label.setText(f"LLM: {provider_name} {error_text}  ")
            self._llm_status_label.setStyleSheet("color: #bb4444;")

    def _open_settings(self):
        """Ayarlar dialogunu acar."""
        dialog = SettingsDialog(self)
        if dialog.exec_():
            self._init_provider()
            self._apply_theme()
            self._current_lang = self._settings.language
            self._update_ui_text()

    def _open_help(self):
        """Yardim dialogunu acar."""
        dialog = HelpDialog(self, self._current_lang)
        dialog.exec_()

    def _on_message_sent(self, text: str):
        """Kullanici mesaji gonderildiginde cagirilir."""
        self._chat_widget.add_message("user", text)
        self._conversation.append({"role": "user", "content": text})

        self._chat_widget.set_input_enabled(False)
        self._chat_widget.set_generating(True)
        self._chat_widget.show_loading()
        self._stop_requested = False

        self._send_to_llm()

    def _send_to_llm(self):
        """Mevcut sohbet gecmisini LLM'ye gonderir."""
        if self._stop_requested:
            self._chat_widget.hide_loading()
            self._chat_widget.set_generating(False)
            self._chat_widget.set_input_enabled(True)
            return

        if not self._provider:
            self._chat_widget.hide_loading()
            self._chat_widget.set_generating(False)
            self._chat_widget.set_input_enabled(True)
            self._chat_widget.add_message(
                "assistant", get_text("msg_llm_not_configured", self._current_lang)
            )
            return

        dynamic_context = self._build_dynamic_context()
        full_system_prompt = SYSTEM_PROMPT + dynamic_context

        messages = [{"role": "system", "content": full_system_prompt}] + self._conversation

        tools = TOOLS
        self._start_stream(messages, tools)

    def _build_dynamic_context(self) -> str:
        """LLM için dinamik bağlam bilgisi oluşturur."""
        if not self._bridge or not self._bridge.is_connected:
            return "\n\n## MEVCUT DURUM\nLibreOffice bağlantısı yok."

        context_parts = ["\n\n## MEVCUT DURUM"]

        try:
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
            doc = self._bridge.get_active_document()
            controller = doc.getCurrentController()
            selection = controller.getSelection()
            address = LibreOfficeBridge.get_selection_address(selection)
            context_parts.append(f"Seçili Hücre: {address}")

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

    def _start_stream(self, messages, tools):
        """LLM stream istegini baslatir."""
        self._stream_content = ""
        self._stream_tool_calls_indexed = {}
        self._stream_tool_calls_full = []
        self._stream_has_tool_calls = False
        self._stream_started = False

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
            names = []
            for tc in tool_calls:
                name = (tc.get("function") or {}).get("name")
                if name:
                    names.append(name)
            if names:
                preview = ", ".join(names[:3])
                if len(names) > 3:
                    preview += ", ..."
                self._stream_content = f"Araçlar çalışıyor: `{preview}`"
            elif not self._stream_content:
                self._stream_content = "Araçlar çalışıyor..."
            self._chat_widget.update_stream_message(self._stream_content)

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
        tool_calls = []
        if self._stream_tool_calls_indexed:
            for idx in sorted(self._stream_tool_calls_indexed.keys()):
                tool_calls.append(self._stream_tool_calls_indexed[idx])
        if self._stream_tool_calls_full:
            tool_calls.extend(self._stream_tool_calls_full)

        if tool_calls:
            if self._stop_requested:
                self._chat_widget.hide_loading()
                self._chat_widget.set_generating(False)
                self._chat_widget.set_input_enabled(True)
                self._chat_widget.add_message(
                    "assistant", get_text("msg_generation_cancelled", self._current_lang)
                )
                return

            if self._stream_content:
                self._chat_widget.end_stream_message()
            else:
                self._chat_widget.discard_stream_message()

            self._chat_widget.set_generating(True)
            self._chat_widget.set_input_enabled(False)

            if not self._dispatcher:
                self._connect_lo_silent()
            if not self._dispatcher:
                self._chat_widget.hide_loading()
                self._chat_widget.set_input_enabled(True)
                self._chat_widget.add_message(
                    "assistant",
                    get_text("msg_lo_connect_required_for_tool", self._current_lang)
                )
                return
            try:
                self._handle_tool_calls(tool_calls)
            except Exception as exc:
                logger.error("Tool çağrıları işlenemedi: %s", exc)
                self._chat_widget.hide_loading()
                self._chat_widget.set_input_enabled(True)
                self._chat_widget.add_message(
                    "assistant", get_text("msg_llm_error", self._current_lang).format(str(exc))
                )
            return

        if self._stream_content:
            self._conversation.append({"role": "assistant", "content": self._stream_content})
            self._chat_widget.end_stream_message()
            self._chat_widget.hide_loading()
            self._chat_widget.set_generating(False)
            self._chat_widget.set_input_enabled(True)
        else:
            self._chat_widget.discard_stream_message()
            self._chat_widget.hide_loading()
            self._chat_widget.set_generating(False)
            self._chat_widget.set_input_enabled(True)

    def _on_cancel_requested(self):
        """Kullanıcı üretimi iptal etmek istedi."""
        self._stop_requested = True
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
        else:
            self._chat_widget.discard_stream_message()
            self._chat_widget.add_message(
                "assistant", get_text("msg_generation_cancelled", self._current_lang)
            )

    def _handle_tool_calls(self, tool_calls: list):
        """Arac cagrilarini isler ve sonuclari LLM'ye geri gonderir."""
        self._conversation.append({
            "role": "assistant",
            "content": None,
            "tool_calls": tool_calls,
        })

        for tc in tool_calls:
            if self._stop_requested:
                self._chat_widget.hide_loading()
                self._chat_widget.set_generating(False)
                self._chat_widget.set_input_enabled(True)
                self._chat_widget.add_message(
                    "assistant", get_text("msg_generation_cancelled", self._current_lang)
                )
                return

            func = tc.get("function", {})
            tool_name = func.get("name", "")
            try:
                arguments = json.loads(func.get("arguments", "{}"))
            except json.JSONDecodeError:
                arguments = {}

            tool_result = self._dispatcher.dispatch(tool_name, arguments)

            try:
                tool_payload = json.loads(tool_result)
            except json.JSONDecodeError:
                tool_payload = {}
            if "error" in tool_payload:
                err_msg = tool_payload.get("error", "Bilinmeyen tool hatası")
                logger.error("Tool hatası (%s): %s", tool_name, err_msg)

            self._conversation.append({
                "role": "tool",
                "tool_call_id": tc.get("id", ""),
                "content": tool_result,
            })

        if self._stop_requested:
            self._chat_widget.hide_loading()
            self._chat_widget.set_generating(False)
            self._chat_widget.set_input_enabled(True)
            return
        self._send_to_llm()

    def _connect_lo_silent(self) -> bool:
        """LibreOffice'e sessizce baglanir."""
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
