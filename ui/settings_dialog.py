"""Ayarlar diyalogu - Uygulama yapilandirmasi icin sekme tabanli dialog."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QWidget,
    QFormLayout,
    QGroupBox,
    QRadioButton,
    QButtonGroup,
    QLineEdit,
    QComboBox,
    QDoubleSpinBox,
    QSpinBox,
    QPushButton,
    QLabel,
    QMessageBox,
    QApplication,
)

from config.settings import Settings
from llm.openrouter_provider import OpenRouterProvider
from llm.ollama_provider import OllamaProvider
from .i18n import get_text

class SettingsDialog(QDialog):
    """Uygulama ayarlari diyalogu."""

    # Tool destekleyen Ollama modelleri (kısmi eşleşme)
    TOOL_SUPPORTED_MODELS = [
        "llama3.1", "llama3.2", "llama3.3",
        "qwen2.5", "qwen2",
        "mistral",
        "command-r",
        "hermes",
        "functionary",
        "firefunction",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = Settings()
        
        # O anki dili al
        self._current_lang = self._settings.language
        
        self._setup_ui()
        self._load_settings()
        self._update_ui_text()

    def _setup_ui(self):
        """Arayuz elemanlarini olusturur."""
        layout = QVBoxLayout(self)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        # --- LLM Ayarlari sekmesi ---
        llm_tab = QWidget()
        llm_layout = QVBoxLayout(llm_tab)

        # Saglayici secimi
        self._provider_group = QGroupBox()
        provider_layout = QVBoxLayout()

        self._provider_bg = QButtonGroup(self)
        self._radio_openrouter = QRadioButton("OpenRouter (Bulut)")
        self._radio_ollama = QRadioButton("Ollama (Yerel)")
        self._provider_bg.addButton(self._radio_openrouter, 0)
        self._provider_bg.addButton(self._radio_ollama, 1)

        provider_layout.addWidget(self._radio_openrouter)
        provider_layout.addWidget(self._radio_ollama)
        self._provider_group.setLayout(provider_layout)
        llm_layout.addWidget(self._provider_group)

        # API ayarlari
        self._api_group = QGroupBox()
        api_form = QFormLayout()

        # OpenRouter API Key
        self._api_key_edit = QLineEdit()
        self._api_key_edit.setEchoMode(QLineEdit.Password)
        self._api_key_label = QLabel()
        api_form.addRow(self._api_key_label, self._api_key_edit)

        # Ollama Base URL
        self._ollama_url_edit = QLineEdit()
        self._ollama_url_label = QLabel()
        api_form.addRow(self._ollama_url_label, self._ollama_url_edit)

        # Model secimi
        model_layout = QHBoxLayout()
        self._model_combo = QComboBox()
        self._model_combo.setEditable(True)
        self._model_combo.setMinimumWidth(250)
        # ... (items unchanged)
        self._model_combo.addItems([
            "anthropic/claude-3.5-sonnet",
            "anthropic/claude-3-haiku",
            "google/gemini-pro",
            "meta-llama/llama-3.1-70b-instruct",
            "mistralai/mistral-large-latest",
        ])
        model_layout.addWidget(self._model_combo)

        self._fetch_models_btn = QPushButton()
        self._fetch_models_btn.clicked.connect(self._fetch_models)
        model_layout.addWidget(self._fetch_models_btn)

        self._model_label = QLabel()
        api_form.addRow(self._model_label, model_layout)

        # Tool desteği uyarı label'ı
        self._tool_warning_label = QLabel()
        self._tool_warning_label.setWordWrap(True)
        self._tool_warning_label.setStyleSheet(
            "QLabel { color: #f0ad4e; padding: 8px; background: rgba(240, 173, 78, 0.1); "
            "border-radius: 4px; }"
        )
        self._tool_warning_label.setVisible(False)
        api_form.addRow("", self._tool_warning_label)

        # Model değişikliğini dinle
        self._model_combo.currentTextChanged.connect(self._on_model_changed)

        self._api_group.setLayout(api_form)
        llm_layout.addWidget(self._api_group)

        llm_layout.addStretch()
        self._tabs.addTab(llm_tab, "") # Text set in _update_ui_text

        # --- Baglanti sekmesi ---
        conn_tab = QWidget()
        conn_layout = QVBoxLayout(conn_tab)

        self._lo_group = QGroupBox()
        lo_form = QFormLayout()

        self._lo_host_edit = QLineEdit()
        self._lo_host_label = QLabel()
        lo_form.addRow(self._lo_host_label, self._lo_host_edit)

        self._lo_port_spin = QSpinBox()
        self._lo_port_spin.setRange(1, 65535)
        self._lo_port_label = QLabel()
        lo_form.addRow(self._lo_port_label, self._lo_port_spin)

        self._lo_group.setLayout(lo_form)
        conn_layout.addWidget(self._lo_group)

        conn_layout.addStretch()
        self._tabs.addTab(conn_tab, "")

        # --- Arayuz sekmesi ---
        ui_tab = QWidget()
        ui_layout = QVBoxLayout(ui_tab)

        self._appearance_group = QGroupBox()
        appearance_form = QFormLayout()

        self._theme_combo = QComboBox()
        self._theme_combo.addItem("", "light") # Text set loop
        self._theme_combo.addItem("", "dark") 
        self._theme_combo.addItem("", "system")
        self._theme_label = QLabel()
        appearance_form.addRow(self._theme_label, self._theme_combo)

        self._lang_combo = QComboBox()
        self._lang_combo.addItem("", "tr")
        self._lang_combo.addItem("", "en")
        self._lang_combo.addItem("", "system")
        self._lang_combo.currentIndexChanged.connect(self._on_language_changed)
        self._lang_label = QLabel()
        appearance_form.addRow(self._lang_label, self._lang_combo)

        self._appearance_group.setLayout(appearance_form)
        ui_layout.addWidget(self._appearance_group)

        ui_layout.addStretch()
        self._tabs.addTab(ui_tab, "")

        # --- OK/Cancel butonlari ---
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._cancel_btn = QPushButton()
        self._cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._cancel_btn)

        self._ok_btn = QPushButton()
        self._ok_btn.setDefault(True)
        self._ok_btn.clicked.connect(self._save_and_accept)
        btn_layout.addWidget(self._ok_btn)

        layout.addLayout(btn_layout)

    def _update_ui_text(self):
        """Arayuz metinlerini secili dile gore gunceller."""
        lang = self._current_lang
        
        self.setWindowTitle(get_text("settings_title", lang))
        
        self._tabs.setTabText(0, get_text("settings_tab_llm", lang))
        self._tabs.setTabText(1, get_text("settings_tab_lo", lang))
        self._tabs.setTabText(2, get_text("settings_tab_general", lang)) # Arayuz -> General/Gorunum
        
        self._provider_group.setTitle(get_text("settings_provider", lang))
        self._api_group.setTitle("API") # Universal
        self._api_key_label.setText(get_text("settings_api_key", lang))
        self._ollama_url_label.setText(get_text("settings_ollama_url", lang))
        self._model_label.setText(get_text("settings_model", lang))
        self._fetch_models_btn.setText(get_text("settings_fetch_models", lang))
        
        self._lo_group.setTitle(get_text("settings_tab_lo", lang))
        self._lo_host_label.setText(get_text("settings_host", lang))
        self._lo_port_label.setText(get_text("settings_port", lang))
        
        self._appearance_group.setTitle(get_text("menu_view", lang))
        self._theme_label.setText(get_text("settings_ui_theme", lang))
        self._lang_label.setText(get_text("settings_ui_lang", lang))
        
        self._theme_combo.setItemText(0, get_text("theme_light", lang))
        self._theme_combo.setItemText(1, get_text("theme_dark", lang))
        self._theme_combo.setItemText(2, get_text("theme_system", lang))
        
        self._lang_combo.setItemText(0, get_text("lang_tr", lang))
        self._lang_combo.setItemText(1, get_text("lang_en", lang))
        self._lang_combo.setItemText(2, get_text("lang_system", lang))
        
        self._save_btn_text = get_text("settings_save", lang)
        self._ok_btn.setText(self._save_btn_text)
        self._cancel_btn.setText(get_text("settings_cancel", lang))

        # Tool uyarısını güncelle
        self._check_tool_support()

    def _on_language_changed(self, index):
        """Dil secimi degistiginde anlik olarak arayuzu gunceller."""
        code = self._lang_combo.itemData(index)
        self._current_lang = code
        self._update_ui_text()

    def _on_provider_changed(self):
        """Provider degistiginde UI elemanlarini gunceller."""
        is_ollama = self._radio_ollama.isChecked()

        # OpenRouter için API key göster, Ollama için gizle
        self._api_key_label.setVisible(not is_ollama)
        self._api_key_edit.setVisible(not is_ollama)

        # Ollama için URL göster, OpenRouter için gizle
        self._ollama_url_label.setVisible(is_ollama)
        self._ollama_url_edit.setVisible(is_ollama)

        # Modelleri getir butonu her zaman aktif
        self._fetch_models_btn.setEnabled(True)

        # Model listesini güncelle
        self._update_model_list()

        # Tool uyarısını güncelle
        self._check_tool_support()

    def _on_model_changed(self, _model_name: str):
        """Model degistiginde tool destegini kontrol eder."""
        self._check_tool_support()

    def _check_tool_support(self):
        """Secili modelin tool destegini kontrol eder ve uyari gosterir."""
        # Sadece Ollama için kontrol et
        if not self._radio_ollama.isChecked():
            self._tool_warning_label.setVisible(False)
            return

        model_name = self._model_combo.currentText().lower()
        if not model_name:
            self._tool_warning_label.setVisible(False)
            return

        # Tool destekli model mi kontrol et
        has_tool_support = any(
            supported in model_name
            for supported in self.TOOL_SUPPORTED_MODELS
        )

        if not has_tool_support:
            self._tool_warning_label.setText(
                get_text("settings_no_tool_support", self._current_lang)
            )
            self._tool_warning_label.setVisible(True)
        else:
            self._tool_warning_label.setVisible(False)

    def _update_model_list(self):
        """Secili provider'a gore model listesini gunceller."""
        self._model_combo.clear()
        s = self._settings

        if self._radio_ollama.isChecked():
            # Ollama modelleri
            cached = s.ollama_models
            if cached:
                self._model_combo.addItems(sorted(cached))
            else:
                # Varsayılan Ollama modelleri
                self._model_combo.addItems([
                    "llama3.1",
                    "llama3.2",
                    "codellama",
                    "mistral",
                    "phi3",
                ])
        else:
            # OpenRouter modelleri
            cached = s.openrouter_models
            if cached:
                self._model_combo.addItems(sorted(cached))
            else:
                self._model_combo.addItems([
                    "anthropic/claude-3.5-sonnet",
                    "anthropic/claude-3-haiku",
                    "google/gemini-pro",
                    "meta-llama/llama-3.1-70b-instruct",
                    "mistralai/mistral-large-latest",
                ])

    def _load_settings(self):
        s = self._settings

        if s.provider == "ollama":
            self._radio_ollama.setChecked(True)
        else:
            self._radio_openrouter.setChecked(True)

        # Provider değişikliğinde UI'yi güncelle
        self._radio_openrouter.toggled.connect(self._on_provider_changed)
        self._radio_ollama.toggled.connect(self._on_provider_changed)

        self._api_key_edit.setText(s.openrouter_api_key)
        self._ollama_url_edit.setText(s.ollama_base_url)

        # İlk yüklemede doğru modelleri göster
        self._update_model_list()

        model = s.openrouter_model if s.provider == "openrouter" else s.ollama_model
        idx = self._model_combo.findText(model)
        if idx >= 0:
            self._model_combo.setCurrentIndex(idx)
        else:
            self._model_combo.setCurrentText(model)

        # İlk yüklemede UI durumunu ayarla
        self._on_provider_changed()

        self._lo_host_edit.setText(s.lo_host)
        self._lo_port_spin.setValue(s.lo_port)

        theme_idx = self._theme_combo.findData(s.theme)
        if theme_idx >= 0:
            self._theme_combo.setCurrentIndex(theme_idx)

        lang_idx = self._lang_combo.findData(s.language)
        if lang_idx >= 0:
            self._lang_combo.setCurrentIndex(lang_idx)

    def _save_and_accept(self):
        """Ayarlari kaydedip diyalogu kapatir."""
        s = self._settings

        if self._radio_ollama.isChecked():
            s.provider = "ollama"
            s.set("ollama_base_url", self._ollama_url_edit.text().strip())
            s.set("ollama_default_model", self._model_combo.currentText().strip())
        else:
            s.provider = "openrouter"
            s.set("openrouter_api_key", self._api_key_edit.text().strip())
            s.set("openrouter_default_model", self._model_combo.currentText().strip())

        s.set("libreoffice_host", self._lo_host_edit.text().strip())
        s.set("libreoffice_port", self._lo_port_spin.value())

        s.theme = self._theme_combo.currentData()
        s.language = self._lang_combo.currentData()

        s.save()
        self.accept()

    def _fetch_models(self):
        """Secili provider'dan mevcut modelleri getirir."""
        is_ollama = self._radio_ollama.isChecked()

        if not is_ollama:
            # OpenRouter için API key gerekli
            api_key = self._api_key_edit.text().strip()
            if not api_key:
                QMessageBox.warning(
                    self,
                    get_text("settings_title", self._current_lang),
                    get_text("settings_api_key_required", self._current_lang)
                )
                return

        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)

            if is_ollama:
                # Ollama URL'sini geçici olarak kaydet
                self._settings.set("ollama_base_url", self._ollama_url_edit.text().strip())

                provider = OllamaProvider()
                models = provider.get_available_models()
                cache_key = "ollama_models"
            else:
                # OpenRouter API anahtarını geçici olarak kaydet
                self._settings.set("openrouter_api_key", self._api_key_edit.text().strip())

                provider = OpenRouterProvider()
                models = provider.get_available_models()
                cache_key = "openrouter_models"

            if models:
                self._model_combo.clear()
                self._model_combo.addItems(sorted(models))

                # Modelleri önbelleğe kaydet
                self._settings.set(cache_key, models)
                self._settings.save()

                QMessageBox.information(
                    self,
                    get_text("settings_title", self._current_lang),
                    get_text("settings_models_fetched", self._current_lang)
                )
            else:
                QMessageBox.warning(
                    self,
                    get_text("settings_title", self._current_lang),
                    get_text("settings_models_empty", self._current_lang)
                )

        except Exception as e:
            QMessageBox.critical(
                self,
                get_text("settings_title", self._current_lang),
                get_text("settings_fetch_error", self._current_lang).format(str(e))
            )
        finally:
            QApplication.restoreOverrideCursor()
