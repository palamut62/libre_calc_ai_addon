"""Arayuz metinleri icin coklu dil destegi."""

import locale

TRANSLATIONS = {
    "tr": {
        "window_title": "Aras Asistan",
        # Menus
        "menu_file": "Dosya",
        "menu_settings": "Ayarlar...",
        "menu_quit": "Çıkış",
        "menu_provider": "Sağlayıcı",
        "menu_view": "Görünüm",
        "menu_theme": "Tema",
        "menu_always_on_top": "Her Zaman Üstte",
        "menu_language": "Dil",
        "menu_help": "Yardım",
        "menu_about": "Hakkında",
        # Toolbar
        "toolbar_title": "Ana Araç Çubuğu",
        "toolbar_connect": "Bağlan",
        "toolbar_analyze": "Hücre Analizi",
        "toolbar_clear": "Geçmişi Sil",
        "toolbar_connect_tooltip": "LibreOffice'e bağland",
        "toolbar_analyze_tooltip": "Seçili hücreyi analiz et",
        "toolbar_clear_tooltip": "Sohbet geçmişini temizle",
        # Status Bar
        "status_lo_connected": "LO: Bağlı",
        "status_lo_disconnected": "LO: Bağlı Değil",
        "status_llm_error": "(hata)",
        "status_selected": "Seçili",
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
        "settings_provider": "LLM Sağlayıcı:",
        "settings_api_key": "API Anahtarı:",
        "settings_model": "Model:",
        "settings_fetch_models": "Modelleri Getir",
        "settings_ollama_url": "Ollama URL:",
        "settings_api_key_required": "Modelleri getirmek için önce API anahtarını girin.",
        "settings_models_empty": "Model listesi boş döndü.",
        "settings_no_tool_support": "⚠️ Bu model araç (tool) desteği sağlamıyor. Hücre düzenleme, formül yazma gibi işlemler yapılamaz. Sadece sohbet edebilirsiniz. Tool destekli modeller: llama3.1, llama3.2, qwen2.5, mistral",
        "settings_host": "Host:",
        "settings_port": "Port:",
        "settings_save": "Kaydet",
        "settings_cancel": "İptal",
        "settings_models_fetched": "Modeller başarıyla getirildi!",
        "settings_fetch_error": "Modeller getirilemedi: {}",
        # Assistant Messages
        "msg_lo_connected": "Merhaba! LibreOffice'e bağlandım. Tablonuzdaki verileri analiz etmeye veya formüllerinizi düzenlemeye hazırım.",
        "msg_lo_not_connected": "Selam! LibreOffice bağlantısı henüz kurulmadı.\n\nBaşlamak için araç çubuğundaki **Bağlan** butonuna basabilir veya terminalden `./launch.sh` komutunu kullanabilirsiniz.",
        "msg_test_mode": "Şu an test modundayım. LibreOffice olmadan arayüzü kontrol edebilirsiniz.",
        "msg_lo_connect_success": "LibreOffice'e başarıyla bağlandı! Artık tablonuza doğrudan müdahale edebilirim.",
        "msg_lo_connect_fail": "LibreOffice'e bağlanılamadı.\n\nLibreOffice'i şu komutla başlatın:\n`libreoffice --calc --accept=\"socket,host=localhost,port=2002;urp;\"`",
        "msg_need_lo": "Önce LibreOffice'e bağlanmanız gerekiyor.",
        "msg_analysis_error": "Hücre analizi sırasında hata oluştu: {}",
        "msg_llm_no_provider": "LLM sağlayıcısı yapılandırılmamış. Lütfen Ayarlar'ı kontrol edin.",
        "msg_llm_not_configured": "LLM sağlayıcısı yapılandırılmamış. Lütfen Ayarlar'ı kontrol edin.",
        "msg_lo_connect_required_for_tool": "Bu işlemi gerçekleştirmek için LibreOffice'e bağlanmam gerekiyor ama bağlantı kurulamadı.\n\nLibreOffice'i şu komutla başlatın:\n`libreoffice --calc --accept=\"socket,host=localhost,port=2002;urp;\"`",
        "msg_llm_error": "Hata oluştu: {}",
        "msg_lo_tool_fail": "Bu işlemi gerçekleştirmek için LibreOffice'e bağlanmam gerekiyor ama bağlantı kurulamadı.\n\nLibreOffice'i şu komutla başlatın:\n`libreoffice --calc --accept=\"socket,host=localhost,port=2002;urp;\"`\n\nSonra araç çubuğundaki 'Bağlan' butonuna basın.",
        # About
        "about_title": "Hakkında",
        "about_content": "<h3>LibreCalc AI Asistanı</h3><p>LibreOffice Calc için yapay zeka destekli asistan.</p><p>Formül analizi, hata tespiti ve tablo manipülasyonu işlemlerinde yardımcı olur.</p><p>Sürüm: 1.0.0</p>",
        # Chat Widget
        "chat_placeholder": "Aras ile konuşun... (Ctrl+Enter)",
        "chat_send": "Gönder",
        "chat_clear": "Temizle",
        "chat_thinking": "Aras düşünüyor",
        "chat_you": "SİZ",
        "chat_aras": "ARAS",
    },
    "en": {
        "window_title": "Aras Assistant",
        # Menus
        "menu_file": "File",
        "menu_settings": "Settings...",
        "menu_quit": "Quit",
        "menu_provider": "Provider",
        "menu_view": "View",
        "menu_theme": "Theme",
        "menu_always_on_top": "Always on Top",
        "menu_language": "Language",
        "menu_help": "Help",
        "menu_about": "About",
        # Toolbar
        "toolbar_title": "Main Toolbar",
        "toolbar_connect": "Connect",
        "toolbar_analyze": "Cell Analysis",
        "toolbar_clear": "Clear History",
        "toolbar_connect_tooltip": "Connect to LibreOffice",
        "toolbar_analyze_tooltip": "Analyze selected cell",
        "toolbar_clear_tooltip": "Clear chat history",
        # Status Bar
        "status_lo_connected": "LO: Connected",
        "status_lo_disconnected": "LO: Disconnected",
        "status_llm_error": "(error)",
        "status_selected": "Selected",
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
        "settings_provider": "LLM Provider:",
        "settings_api_key": "API Key:",
        "settings_model": "Model:",
        "settings_fetch_models": "Fetch Models",
        "settings_ollama_url": "Ollama URL:",
        "settings_api_key_required": "Please enter your API key to fetch models.",
        "settings_models_empty": "Model list returned empty.",
        "settings_no_tool_support": "⚠️ This model does not support tools. Cell editing, formula writing, etc. will not work. Chat only. Tool-supported models: llama3.1, llama3.2, qwen2.5, mistral",
        "settings_host": "Host:",
        "settings_port": "Port:",
        "settings_save": "Save",
        "settings_cancel": "Cancel",
        "settings_models_fetched": "Models fetched successfully!",
        "settings_fetch_error": "Failed to fetch models: {}",
        # Assistant Messages
        "msg_lo_connected": "Hello! I'm connected to LibreOffice. Ready to analyze your data or edit formulas.",
        "msg_lo_not_connected": "Hi! LibreOffice connection is not established yet.\n\nYou can click the **Connect** button in the toolbar or run `./launch.sh` in the terminal to start.",
        "msg_test_mode": "I'm in test mode. You can check the interface without LibreOffice.",
        "msg_lo_connect_success": "Successfully connected to LibreOffice! I can now interact with your spreadsheet directly.",
        "msg_lo_connect_fail": "Could not connect to LibreOffice.\n\nPlease start LibreOffice with:\n`libreoffice --calc --accept=\"socket,host=localhost,port=2002;urp;\"`",
        "msg_need_lo": "You need to connect to LibreOffice first.",
        "msg_analysis_error": "Error during cell analysis: {}",
        "msg_llm_no_provider": "LLM provider not configured. Please check Settings.",
        "msg_llm_not_configured": "LLM provider not configured. Please check Settings.",
        "msg_lo_connect_required_for_tool": "I need to connect to LibreOffice to perform this action but the connection failed.\n\nPlease start LibreOffice with:\n`libreoffice --calc --accept=\"socket,host=localhost,port=2002;urp;\"`",
        "msg_llm_error": "An error occurred: {}",
        "msg_lo_tool_fail": "I need to connect to LibreOffice to perform this action but the connection failed.\n\nPlease start LibreOffice with:\n`libreoffice --calc --accept=\"socket,host=localhost,port=2002;urp;\"`\n\nThen click the 'Connect' button in the toolbar.",
        # About
        "about_title": "About",
        "about_content": "<h3>LibreCalc AI Assistant</h3><p>AI-powered assistant for LibreOffice Calc.</p><p>Helps with formula analysis, error detection, and spreadsheet manipulation.</p><p>Version: 1.0.0</p>",
        # Chat Widget
        "chat_placeholder": "Talk to Aras... (Ctrl+Enter)",
        "chat_send": "Send",
        "chat_clear": "Clear",
        "chat_thinking": "Aras is thinking",
        "chat_you": "YOU",
        "chat_aras": "ARAS",
    }
}


def get_system_lang() -> str:
    """Sistem dilini dondurur (tr veya en)."""
    try:
        lang_code = locale.getdefaultlocale()[0]
        if lang_code and lang_code.startswith("tr"):
            return "tr"
    except:
        pass
    return "en"


def get_text(key: str, lang: str = "system") -> str:
    """Belirtilen dildeki metni dondurur.
    
    Args:
        key: Metin anahtari.
        lang: Dil kodu ('tr', 'en' veya 'system').
        
    Returns:
        Cevrilmis metin.
    """
    if lang == "system":
        lang = get_system_lang()
        
    # Desteklenmeyen dil ise ingilizceye dus
    if lang not in TRANSLATIONS:
        lang = "en"
        
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    return texts.get(key, key)
