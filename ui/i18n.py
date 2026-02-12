"""Arayuz metinleri icin coklu dil destegi - Minimal."""

import locale
import logging

logger = logging.getLogger(__name__)

TRANSLATIONS = {
    "tr": {
        "window_title": "ArasAI",
        # Menus
        "menu_file": "Dosya",
        "menu_settings": "Ayarlar...",
        "menu_quit": "Çıkış",
        "menu_provider": "Sağlayıcı",
        "menu_view": "Görünüm",
        "menu_theme": "Tema",
        "menu_language": "Dil",
        "menu_help": "Yardım",
        "menu_help_about": "Yardım...",
        # Status Bar
        "status_lo_connected": "LO: Bağlı",
        "status_lo_disconnected": "LO: Bağlı Değil",
        "status_llm_error": "(hata)",
        # Themes
        "theme_light": "Açık",
        "theme_dark": "Koyu",
        "theme_system": "Sistem",
        # Languages
        "lang_system": "Sistem",
        "lang_tr": "Türkçe",
        "lang_en": "English",
        # Settings Dialog
        "settings_title": "Ayarlar",
        "settings_tab_general": "Genel",
        "settings_tab_llm": "Yapay Zeka (LLM)",
        "settings_tab_lo": "LibreOffice",
        "settings_ui_theme": "Arayüz Teması:",
        "settings_ui_lang": "Arayüz Dili:",
        "settings_logging": "Yerel loglar açık",
        "settings_provider": "LLM Sağlayıcı:",
        "settings_api_key": "API Anahtarı:",
        "settings_groq_api_key": "Groq API Anahtarı:",
        "settings_gemini_api_key": "Gemini API Anahtarı:",
        "settings_model": "Model:",
        "settings_openrouter_free_only": "Sadece ücretsiz modelleri göster",
        "settings_price_per_1k": "Fiyat ($/1k) P/C:",
        "settings_fetch_models": "Modelleri Getir",
        "settings_ollama_url": "Ollama URL:",
        "settings_api_key_required": "Modelleri getirmek için önce API anahtarını girin.",
        "settings_groq_api_key_required": "Groq modellerini getirmek için API anahtarını girin.",
        "settings_gemini_api_key_required": "Gemini modellerini getirmek için API anahtarını girin.",
        "settings_models_empty": "Model listesi boş döndü.",
        "settings_no_tool_support": "Bu model araç desteği sağlamıyor.",
        "settings_host": "Host:",
        "settings_port": "Port:",
        "settings_save": "Kaydet",
        "settings_cancel": "İptal",
        "settings_models_fetched": "Modeller başarıyla getirildi!",
        "settings_fetch_error": "Modeller getirilemedi: {}",
        # Assistant Messages
        "msg_lo_connected": "Merhaba! LibreOffice'e bağlandım. Tablonuzdaki verileri analiz etmeye veya formüllerinizi düzenlemeye hazırım. Ne yapmamı istersiniz?",
        "msg_lo_not_connected": "Selam! LibreOffice bağlantısı henüz kurulmadı.\n\nBaşlamak için terminalden `./launch.sh` komutunu kullanabilirsiniz.",
        "msg_test_mode": "Şu an test modundayım.",
        "msg_llm_not_configured": "LLM sağlayıcısı yapılandırılmamış. Lütfen Ayarlar'ı kontrol edin.",
        "msg_lo_connect_required_for_tool": "Bu işlemi gerçekleştirmek için LibreOffice'e bağlanmam gerekiyor ama bağlantı kurulamadı.\n\nLibreOffice'i şu komutla başlatın:\n`libreoffice --calc --accept=\"socket,host=localhost,port=2002;urp;\"`",
        "msg_llm_error": "Hata oluştu: {}",
        "msg_generation_cancelled": "Yanıt durduruldu.",
        # Chat Widget
        "chat_placeholder": "ArasAI ile konuşun... (Ctrl+Enter)",
        "chat_send": "Gönder",
        "chat_clear": "Temizle",
        "chat_stop": "Durdur",
        "chat_thinking": "ArasAI düşünüyor",
        "chat_you": "SİZ",
        "chat_aras": "CALC AI",
        "chat_provider_model": "LLM: {provider} · {model}",
    },
    "en": {
        "window_title": "ArasAI",
        # Menus
        "menu_file": "File",
        "menu_settings": "Settings...",
        "menu_quit": "Quit",
        "menu_provider": "Provider",
        "menu_view": "View",
        "menu_theme": "Theme",
        "menu_language": "Language",
        "menu_help": "Help",
        "menu_help_about": "Help...",
        # Status Bar
        "status_lo_connected": "LO: Connected",
        "status_lo_disconnected": "LO: Disconnected",
        "status_llm_error": "(error)",
        # Themes
        "theme_light": "Light",
        "theme_dark": "Dark",
        "theme_system": "System",
        # Languages
        "lang_system": "System",
        "lang_tr": "Türkçe",
        "lang_en": "English",
        # Settings Dialog
        "settings_title": "Settings",
        "settings_tab_general": "General",
        "settings_tab_llm": "AI (LLM)",
        "settings_tab_lo": "LibreOffice",
        "settings_ui_theme": "Interface Theme:",
        "settings_ui_lang": "Interface Language:",
        "settings_logging": "Enable local logs",
        "settings_provider": "LLM Provider:",
        "settings_api_key": "API Key:",
        "settings_groq_api_key": "Groq API Key:",
        "settings_gemini_api_key": "Gemini API Key:",
        "settings_model": "Model:",
        "settings_openrouter_free_only": "Show free models only",
        "settings_price_per_1k": "Price ($/1k) P/C:",
        "settings_fetch_models": "Fetch Models",
        "settings_ollama_url": "Ollama URL:",
        "settings_api_key_required": "Please enter your API key to fetch models.",
        "settings_groq_api_key_required": "Please enter your Groq API key to fetch models.",
        "settings_gemini_api_key_required": "Please enter your Gemini API key to fetch models.",
        "settings_models_empty": "Model list returned empty.",
        "settings_no_tool_support": "This model does not support tools.",
        "settings_host": "Host:",
        "settings_port": "Port:",
        "settings_save": "Save",
        "settings_cancel": "Cancel",
        "settings_models_fetched": "Models fetched successfully!",
        "settings_fetch_error": "Failed to fetch models: {}",
        # Assistant Messages
        "msg_lo_connected": "Hello! I'm connected to LibreOffice. Ready to analyze your data or edit formulas. What would you like me to do?",
        "msg_lo_not_connected": "Hi! LibreOffice connection is not established yet.\n\nRun `./launch.sh` in the terminal to start.",
        "msg_test_mode": "I'm in test mode.",
        "msg_llm_not_configured": "LLM provider not configured. Please check Settings.",
        "msg_lo_connect_required_for_tool": "I need to connect to LibreOffice to perform this action but the connection failed.\n\nPlease start LibreOffice with:\n`libreoffice --calc --accept=\"socket,host=localhost,port=2002;urp;\"`",
        "msg_llm_error": "An error occurred: {}",
        "msg_generation_cancelled": "Response stopped.",
        # Chat Widget
        "chat_placeholder": "Talk to ArasAI... (Ctrl+Enter)",
        "chat_send": "Send",
        "chat_clear": "Clear",
        "chat_stop": "Stop",
        "chat_thinking": "ArasAI is thinking",
        "chat_you": "YOU",
        "chat_aras": "CALC AI",
        "chat_provider_model": "LLM: {provider} · {model}",
    }
}


def get_system_lang() -> str:
    """Sistem dilini dondurur (tr veya en)."""
    try:
        lang_code = locale.getdefaultlocale()[0]
        if lang_code and lang_code.startswith("tr"):
            return "tr"
    except Exception as e:
        logger.warning("Sistem dili belirlenemedi: %s", e)
    return "en"


def get_text(key: str, lang: str = "system") -> str:
    """Belirtilen dildeki metni dondurur."""
    if lang == "system":
        lang = get_system_lang()

    if lang not in TRANSLATIONS:
        lang = "en"

    texts = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    return texts.get(key, key)
