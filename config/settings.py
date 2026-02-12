"""Konfigürasyon yönetimi - .env dosyasından ayarları okur ve yönetir."""

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class Settings:
    """Uygulama ayarlarını yöneten singleton sınıf."""

    _instance = None
    _config_dir = Path.home() / ".config" / "libre_calc_ai"
    _config_file = _config_dir / "settings.json"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # .env dosyasını yükle
        env_path = Path(__file__).parent.parent / ".env"
        load_dotenv(env_path)

        # Varsayılan değerler
        self._defaults = {
            # OpenRouter
            "openrouter_api_key": "",
            "openrouter_base_url": "https://openrouter.ai/api/v1",
            "openrouter_default_model": "anthropic/claude-3.5-sonnet",
            # Gemini
            "gemini_api_key": "",
            "gemini_base_url": "https://generativelanguage.googleapis.com/v1beta",
            "gemini_default_model": "gemini-1.5-flash",
            # Ollama
            "ollama_base_url": "http://localhost:11434",
            "ollama_default_model": "llama3.1",
            # LLM Parametreleri
            "llm_temperature": 0.7,
            "llm_max_tokens": 4096,
            "llm_provider": "openrouter",  # "openrouter", "ollama", "gemini"
            # LibreOffice
            "libreoffice_host": "localhost",
            "libreoffice_port": 2002,
            # UI
            "ui_theme": "dark",
            "ui_language": "tr",
            "openrouter_models": [],
            "ollama_models": [],
            "gemini_models": [],
            "openrouter_model_prices": {},
            "ollama_model_prices": {},
            "openrouter_free_only": False,
            "logging_enabled": True,
        }

        # Ayarları yükle
        self._settings = dict(self._defaults)
        self._load_from_env()
        self._load_from_file()

    def _load_from_env(self):
        """Ortam değişkenlerinden ayarları yükle."""
        env_mapping = {
            "OPENROUTER_API_KEY": "openrouter_api_key",
            "OPENROUTER_BASE_URL": "openrouter_base_url",
            "OPENROUTER_DEFAULT_MODEL": "openrouter_default_model",
            "GEMINI_API_KEY": "gemini_api_key",
            "GEMINI_BASE_URL": "gemini_base_url",
            "GEMINI_DEFAULT_MODEL": "gemini_default_model",
            "OLLAMA_BASE_URL": "ollama_base_url",
            "OLLAMA_DEFAULT_MODEL": "ollama_default_model",
            "LLM_TEMPERATURE": "llm_temperature",
            "LLM_MAX_TOKENS": "llm_max_tokens",
            "LIBREOFFICE_HOST": "libreoffice_host",
            "LIBREOFFICE_PORT": "libreoffice_port",
            "UI_THEME": "ui_theme",
            "UI_LANGUAGE": "ui_language",
        }

        for env_key, setting_key in env_mapping.items():
            value = os.getenv(env_key)
            if value is not None:
                # Tip dönüşümü
                default = self._defaults[setting_key]
                if isinstance(default, int):
                    value = int(value)
                elif isinstance(default, float):
                    value = float(value)
                self._settings[setting_key] = value

    def _load_from_file(self):
        """Kaydedilmiş ayarları dosyadan yükle (env üzerine yazar)."""
        if self._config_file.exists():
            try:
                with open(self._config_file, "r") as f:
                    saved = json.load(f)
                self._settings.update(saved)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("Ayarlar dosyası okunamadı: %s", e)

    def save(self):
        """Mevcut ayarları dosyaya kaydet."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        # Sadece varsayılandan farklı olanları kaydet
        diff = {}
        for key, value in self._settings.items():
            if value != self._defaults.get(key):
                diff[key] = value
        with open(self._config_file, "w") as f:
            json.dump(diff, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default=None):
        """Ayar değerini al."""
        return self._settings.get(key, default)

    def set(self, key: str, value):
        """Ayar değerini güncelle."""
        self._settings[key] = value

    def reset(self):
        """Tüm ayarları varsayılana döndür."""
        self._settings = dict(self._defaults)

    # Kısayol property'ler
    @property
    def openrouter_api_key(self) -> str:
        return self._settings["openrouter_api_key"]

    @property
    def openrouter_base_url(self) -> str:
        return self._settings["openrouter_base_url"]

    @property
    def openrouter_model(self) -> str:
        return self._settings["openrouter_default_model"]

    @property
    def gemini_api_key(self) -> str:
        return self._settings["gemini_api_key"]

    @property
    def gemini_base_url(self) -> str:
        return self._settings["gemini_base_url"]

    @property
    def gemini_model(self) -> str:
        return self._settings["gemini_default_model"]

    @property
    def ollama_base_url(self) -> str:
        return self._settings["ollama_base_url"]

    @property
    def ollama_model(self) -> str:
        return self._settings["ollama_default_model"]

    @property
    def temperature(self) -> float:
        return self._settings["llm_temperature"]

    @property
    def max_tokens(self) -> int:
        return self._settings["llm_max_tokens"]

    @property
    def provider(self) -> str:
        return self._settings["llm_provider"]

    @provider.setter
    def provider(self, value: str):
        if value not in ("openrouter", "ollama", "gemini"):
            raise ValueError("Provider 'openrouter', 'ollama' veya 'gemini' olmalıdır")
        self._settings["llm_provider"] = value

    @property
    def lo_host(self) -> str:
        return self._settings["libreoffice_host"]

    @property
    def lo_port(self) -> int:
        return self._settings["libreoffice_port"]

    @property
    def theme(self) -> str:
        return self._settings["ui_theme"]

    @theme.setter
    def theme(self, value: str):
        if value not in ("dark", "light", "system"):
            raise ValueError("Tema 'dark', 'light' veya 'system' olmalıdır")
        self._settings["ui_theme"] = value

    @property
    def language(self) -> str:
        return self._settings.get("ui_language", "system")

    @language.setter
    def language(self, value: str):
        if value not in ("tr", "en", "system"):
            raise ValueError("Dil 'tr', 'en' veya 'system' olmalıdır")
        self._settings["ui_language"] = value

    @property
    def openrouter_models(self) -> list:
        return self._settings.get("openrouter_models", [])

    @openrouter_models.setter
    def openrouter_models(self, value: list):
        self._settings["openrouter_models"] = value

    @property
    def ollama_models(self) -> list:
        return self._settings.get("ollama_models", [])

    @ollama_models.setter
    def ollama_models(self, value: list):
        self._settings["ollama_models"] = value

    @property
    def gemini_models(self) -> list:
        return self._settings.get("gemini_models", [])

    @gemini_models.setter
    def gemini_models(self, value: list):
        self._settings["gemini_models"] = value

    @property
    def openrouter_model_prices(self) -> dict:
        return self._settings.get("openrouter_model_prices", {})

    @openrouter_model_prices.setter
    def openrouter_model_prices(self, value: dict):
        self._settings["openrouter_model_prices"] = value

    @property
    def ollama_model_prices(self) -> dict:
        return self._settings.get("ollama_model_prices", {})

    @ollama_model_prices.setter
    def ollama_model_prices(self, value: dict):
        self._settings["ollama_model_prices"] = value

    @property
    def logging_enabled(self) -> bool:
        return bool(self._settings.get("logging_enabled", True))

    @logging_enabled.setter
    def logging_enabled(self, value: bool):
        self._settings["logging_enabled"] = bool(value)
