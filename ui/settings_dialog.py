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
)

from config.settings import Settings


class SettingsDialog(QDialog):
    """Uygulama ayarlari diyalogu.

    Uclu sekme yapisi ile LLM, baglanti ve arayuz ayarlarini yonetir.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = Settings()
        self.setWindowTitle("Ayarlar")
        self.setMinimumWidth(420)
        self.setMinimumHeight(400)
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        """Arayuz elemanlarini olusturur."""
        layout = QVBoxLayout(self)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        # --- LLM Ayarlari sekmesi ---
        llm_tab = QWidget()
        llm_layout = QVBoxLayout(llm_tab)

        # Saglayici secimi
        provider_group = QGroupBox("Saglayici")
        provider_layout = QVBoxLayout()

        self._provider_group = QButtonGroup(self)
        self._radio_openrouter = QRadioButton("OpenRouter (Bulut)")
        self._radio_ollama = QRadioButton("Ollama (Yerel)")
        self._provider_group.addButton(self._radio_openrouter, 0)
        self._provider_group.addButton(self._radio_ollama, 1)

        provider_layout.addWidget(self._radio_openrouter)
        provider_layout.addWidget(self._radio_ollama)
        provider_group.setLayout(provider_layout)
        llm_layout.addWidget(provider_group)

        # API ayarlari
        api_group = QGroupBox("API Ayarlari")
        api_form = QFormLayout()

        self._api_key_edit = QLineEdit()
        self._api_key_edit.setEchoMode(QLineEdit.Password)
        self._api_key_edit.setPlaceholderText("OpenRouter API anahtarinizi girin")
        api_form.addRow("API Anahtari:", self._api_key_edit)

        self._model_combo = QComboBox()
        self._model_combo.setEditable(True)
        self._model_combo.addItems([
            "anthropic/claude-3.5-sonnet",
            "anthropic/claude-3-haiku",
            "google/gemini-pro",
            "meta-llama/llama-3.1-70b-instruct",
            "mistralai/mistral-large-latest",
        ])
        api_form.addRow("Model:", self._model_combo)

        api_group.setLayout(api_form)
        llm_layout.addWidget(api_group)

        # Parametre ayarlari
        param_group = QGroupBox("Parametreler")
        param_form = QFormLayout()

        self._temperature_spin = QDoubleSpinBox()
        self._temperature_spin.setRange(0.0, 2.0)
        self._temperature_spin.setSingleStep(0.1)
        self._temperature_spin.setDecimals(1)
        param_form.addRow("Sicaklik:", self._temperature_spin)

        self._max_tokens_spin = QSpinBox()
        self._max_tokens_spin.setRange(100, 32000)
        self._max_tokens_spin.setSingleStep(256)
        param_form.addRow("Maks. Token:", self._max_tokens_spin)

        param_group.setLayout(param_form)
        llm_layout.addWidget(param_group)

        llm_layout.addStretch()
        self._tabs.addTab(llm_tab, "LLM Ayarlari")

        # --- Baglanti sekmesi ---
        conn_tab = QWidget()
        conn_layout = QVBoxLayout(conn_tab)

        lo_group = QGroupBox("LibreOffice Baglantisi")
        lo_form = QFormLayout()

        self._lo_host_edit = QLineEdit()
        lo_form.addRow("Sunucu:", self._lo_host_edit)

        self._lo_port_spin = QSpinBox()
        self._lo_port_spin.setRange(1, 65535)
        lo_form.addRow("Port:", self._lo_port_spin)

        lo_group.setLayout(lo_form)
        conn_layout.addWidget(lo_group)

        ollama_group = QGroupBox("Ollama Baglantisi")
        ollama_form = QFormLayout()

        self._ollama_url_edit = QLineEdit()
        self._ollama_url_edit.setPlaceholderText("http://localhost:11434")
        ollama_form.addRow("URL:", self._ollama_url_edit)

        ollama_group.setLayout(ollama_form)
        conn_layout.addWidget(ollama_group)

        conn_layout.addStretch()
        self._tabs.addTab(conn_tab, "Baglanti")

        # --- Arayuz sekmesi ---
        ui_tab = QWidget()
        ui_layout = QVBoxLayout(ui_tab)

        appearance_group = QGroupBox("Gorunum")
        appearance_form = QFormLayout()

        self._theme_combo = QComboBox()
        self._theme_combo.addItem("Koyu", "dark")
        self._theme_combo.addItem("Acik", "light")
        appearance_form.addRow("Tema:", self._theme_combo)

        self._lang_combo = QComboBox()
        self._lang_combo.addItem("Turkce", "tr")
        self._lang_combo.addItem("English", "en")
        appearance_form.addRow("Dil:", self._lang_combo)

        appearance_group.setLayout(appearance_form)
        ui_layout.addWidget(appearance_group)

        ui_layout.addStretch()
        self._tabs.addTab(ui_tab, "Arayuz")

        # --- OK/Cancel butonlari ---
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Iptal")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        ok_btn = QPushButton("Tamam")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._save_and_accept)
        btn_layout.addWidget(ok_btn)

        layout.addLayout(btn_layout)

    def _load_settings(self):
        """Mevcut ayarlari form alanlarina yukler."""
        s = self._settings

        # Saglayici
        if s.provider == "ollama":
            self._radio_ollama.setChecked(True)
        else:
            self._radio_openrouter.setChecked(True)

        # API
        self._api_key_edit.setText(s.openrouter_api_key)

        # Model combo'da mevcut modeli sec veya yaz
        model = s.openrouter_model if s.provider == "openrouter" else s.ollama_model
        idx = self._model_combo.findText(model)
        if idx >= 0:
            self._model_combo.setCurrentIndex(idx)
        else:
            self._model_combo.setCurrentText(model)

        # Parametreler
        self._temperature_spin.setValue(s.temperature)
        self._max_tokens_spin.setValue(s.max_tokens)

        # Baglanti
        self._lo_host_edit.setText(s.lo_host)
        self._lo_port_spin.setValue(s.lo_port)
        self._ollama_url_edit.setText(s.ollama_base_url)

        # Arayuz
        theme_idx = self._theme_combo.findData(s.theme)
        if theme_idx >= 0:
            self._theme_combo.setCurrentIndex(theme_idx)

        lang_idx = self._lang_combo.findData(s.get("ui_language", "tr"))
        if lang_idx >= 0:
            self._lang_combo.setCurrentIndex(lang_idx)

    def _save_and_accept(self):
        """Ayarlari kaydedip diyalogu kapatir."""
        s = self._settings

        # Saglayici
        if self._radio_ollama.isChecked():
            s.provider = "ollama"
        else:
            s.provider = "openrouter"

        # API
        s.set("openrouter_api_key", self._api_key_edit.text().strip())
        if s.provider == "openrouter":
            s.set("openrouter_default_model", self._model_combo.currentText().strip())
        else:
            s.set("ollama_default_model", self._model_combo.currentText().strip())

        # Parametreler
        s.set("llm_temperature", self._temperature_spin.value())
        s.set("llm_max_tokens", self._max_tokens_spin.value())

        # Baglanti
        s.set("libreoffice_host", self._lo_host_edit.text().strip())
        s.set("libreoffice_port", self._lo_port_spin.value())
        s.set("ollama_base_url", self._ollama_url_edit.text().strip())

        # Arayuz
        s.theme = self._theme_combo.currentData()
        s.set("ui_language", self._lang_combo.currentData())

        s.save()
        self.accept()
