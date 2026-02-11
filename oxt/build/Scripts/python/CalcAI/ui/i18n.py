"""Arayuz metinleri icin coklu dil destegi."""

import locale
import logging

logger = logging.getLogger(__name__)

TRANSLATIONS = {
    "tr": {
        "window_title": "ArasAI",
        # Menus
        "menu_file": "Dosya",
        "menu_save_chat": "Sohbeti Kaydet...",
        "menu_load_chat": "Sohbeti Yükle...",
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
        "toolbar_quick_actions": "Hızlı Eylemler",
        "toolbar_formula_check": "Formül Doğrula",
        "toolbar_data_profile": "Veri Profili",
        "toolbar_errors_scan": "Hata Taraması",
        "toolbar_changes": "Değişiklikler",
        "toolbar_undo": "Geri Al",
        "toolbar_save_chat": "Kaydet",
        "toolbar_load_chat": "Yükle",
        "toolbar_export_report": "Rapor",
        "ribbon_home": "Ana",
        "ribbon_history": "Geçmiş",
        "toolbar_connect_tooltip": "LibreOffice'e bağland",
        "toolbar_analyze_tooltip": "Seçili hücreyi analiz et",
        "toolbar_clear_tooltip": "Sohbet geçmişini temizle",
        "toolbar_quick_clear": "Seçiliyi Temizle",
        "toolbar_quick_fill": "Seçiliyi Doldur",
        "toolbar_quick_format": "Seçiliyi Formatla",
        "toolbar_quick_table": "Tablo Oluştur",
        "toolbar_quick_header": "Başlık Biçimlendir",
        "toolbar_quick_outliers": "Aykırıları Vurgula",
        "toolbar_clean_trim": "Boşlukları Temizle",
        "toolbar_clean_number": "Metni Sayıya Çevir",
        "toolbar_clean_date": "Metni Tarihe Çevir",
        "toolbar_formulaize": "Otomatik Formülleştir",
        "preview_title": "Seçim",
        "preview_empty": "Seçim yok",
        "preview_multi": "Çoklu seçim",
        "preview_no_lo": "LibreOffice bağlı değil",
        "preview_error": "Önizleme hatası",
        "preview_stats": "{rows}x{cols} ({total}) | boş {empty} | sayı {values} | metin {text} | formül {formula}",
        "preview_samples": "Örnek: {samples}",
        "preview_multi_stats": "{count} alan",
        # Status Bar
        "status_lo_connected": "LO: Bağlı",
        "status_lo_disconnected": "LO: Bağlı Değil",
        "status_llm_error": "(hata)",
        "status_selected": "Seçili",
        "status_tokens_est": "Token ~P:{prompt} ~C:{completion}",
        "status_cost_est": "Maliyet ~{cost}",
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
        "settings_gemini_api_key": "Gemini API Anahtarı:",
        "settings_model": "Model:",
        "settings_price_per_1k": "Fiyat ($/1k) P/C:",
        "settings_fetch_models": "Modelleri Getir",
        "settings_ollama_url": "Ollama URL:",
        "settings_api_key_required": "Modelleri getirmek için önce API anahtarını girin.",
        "settings_gemini_api_key_required": "Gemini modellerini getirmek için API anahtarını girin.",
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
        "msg_quick_clear_done": "Seçili alan temizlendi.",
        "msg_quick_fill_done": "Seçili alan dolduruldu.",
        "msg_quick_format_done": "Seçili alan formatlandı.",
        "msg_quick_action_error": "Hızlı eylem hatası: {}",
        "msg_table_need_range": "Tablo oluşturmak için bir aralık seçin.",
        "msg_table_done": "Tablo oluşturuldu.",
        "msg_header_done": "Başlık biçimlendirildi.",
        "msg_outlier_need_range": "Aykırıları vurgulamak için bir aralık seçin.",
        "msg_outlier_not_enough": "Aykırı değer analizi için yeterli sayısal veri yok.",
        "msg_outlier_done": "Aykırı değer sayısı: {0}",
        "msg_change_table": "Tablo oluşturuldu: {0}",
        "msg_change_header": "Başlık biçimlendirildi: {0}",
        "msg_change_outliers": "Aykırılar vurgulandı: {0}",
        "msg_clean_need_range": "Bu işlem için bir aralık seçin.",
        "msg_clean_done": "Temizlenen hücre sayısı: {0}",
        "msg_clean_number_done": "Sayıya çevrilen hücre sayısı: {0}",
        "msg_clean_date_done": "Tarihe çevrilen hücre sayısı: {0}",
        "msg_change_clean": "Temizleme uygulandı: {0}",
        "msg_formulaize_need_range": "Formülleştirmek için bir aralık seçin.",
        "msg_formulaize_multi": "Formülleştirme tek aralıkta çalışır. Lütfen tek bir aralık seçin.",
        "msg_formulaize_none": "Uygun formül ilişkisi bulunamadı.",
        "msg_formulaize_done": "Formülleştirilen hücre sayısı: {0}",
        "msg_formulaize_error": "Formülleştirme hatası: {}",
        "msg_change_formulaize": "Formülleştirildi: {0}",
        "msg_formulaize_preview": "Önerilen formüller:",
        "msg_formulaize_cancelled": "Formülleştirme iptal edildi.",
        "msg_formulaize_title": "Formülleştirme Onayı",
        "msg_change_clear": "Temizlendi: {0}",
        "msg_change_fill": "Dolduruldu: {0}",
        "msg_change_format": "Formatlandı: {0}",
        "msg_no_changes": "Değişiklik geçmişi boş.",
        "msg_undo_done": "Geri alındı: {0}",
        "msg_undo_none": "Geri alınacak değişiklik yok.",
        "msg_undo_error": "Geri alma hatası: {}",
        "msg_chat_saved": "Sohbet kaydedildi: {0}",
        "msg_chat_save_error": "Sohbet kaydedilemedi: {}",
        "msg_chat_loaded": "Sohbet yüklendi: {0}",
        "msg_chat_load_error": "Sohbet yüklenemedi: {}",
        "msg_report_saved": "Rapor kaydedildi: {0}",
        "msg_report_save_error": "Rapor kaydedilemedi: {}",
        "cmd_help_header": "**Kısayol Komutları**",
        "cmd_desc_analyze": "Seçili hücreyi analiz eder",
        "cmd_desc_connect": "LibreOffice'e bağlanır",
        "cmd_desc_profile": "Seçili/aktif alan için veri profili çıkarır",
        "cmd_desc_validate": "Seçili hücredeki formülü doğrular",
        "cmd_desc_changes": "Değişiklik geçmişini gösterir",
        "cmd_desc_undo": "Son değişikliği geri alır",
        "cmd_desc_clear": "Sohbet geçmişini temizler",
        "cmd_unknown": "Bilinmeyen komut: {0}. Yardım için `/help` yazın.",
        "chat_slash_hint": "Komutlar için / yazın (ör. /help)",
        "msg_formula_single_cell": "Lütfen tek bir hücre seçin.",
        "msg_formula_missing": "{0} hücresinde formül bulunamadı.",
        "msg_formula_ok": "Formül geçerli görünüyor.\n\nHücre: {0}\nFormül: `{1}`",
        "msg_formula_error": "Formül hatalı.\n\nHücre: {address}\nFormül: `{formula}`\nHata: {error}\n{description}",
        "msg_formula_suggestion": "Öneri: {0}",
        "msg_formula_check_error": "Formül doğrulama hatası: {}",
        "msg_profile_no_range": "Profil çıkarılacak aralık bulunamadı.",
        "msg_profile_empty": "Profil çıkarılacak veri bulunamadı.",
        "msg_profile_none": "Yok",
        "msg_profile_error": "Veri profili hatası: {}",
        "msg_errors_found": "{0} hata bulundu. İlk 10 gösteriliyor:",
        "msg_errors_none": "Formül hatası bulunamadı.",
        "msg_errors_scan_error": "Hata tarama hatası: {}",
        "msg_errors_suggestion": "Öneri ({0}): {1}",
        "msg_tool_call_title": "Araç Onayı",
        "msg_tool_call_confirm": "Aşağıdaki işlemler yapılacak, onaylıyor musunuz?",
        "msg_tool_call_cancelled": "Araç çağrısı iptal edildi.",
        "msg_tool_call_yes": "Evet",
        "msg_tool_call_no": "Hayır",
        "msg_tool_call_always": "Tümünü Kabul Et",
        # About
        "about_title": "Hakkında",
        "about_content": "<h3>ArasAI</h3><p>LibreOffice Calc için yapay zeka destekli asistan.</p><p>Formül analizi, hata tespiti ve tablo manipülasyonu işlemlerinde yardımcı olur.</p><p>Sürüm: 1.0.0</p>",
        # Help Dialog
        "help_title": "Yardım",
        "help_tab_start": "Başlangıç",
        "help_tab_features": "Özellikler",
        "help_tab_commands": "Komutlar",
        "help_tab_about": "Hakkında",
        "help_close": "Kapat",
        "menu_help_guide": "Kullanım Kılavuzu...",
        "help_content_start": """<h2>ArasAI'ye Hoş Geldiniz</h2>
<p>ArasAI, LibreOffice Calc için yapay zeka destekli akıllı bir asistan eklentisidir.</p>
<h3>Hızlı Başlangıç</h3>
<ol>
  <li><b>Bağlantı:</b> Araç çubuğundaki <em>Bağlan</em> butonuna tıklayın veya <code>./launch.sh</code> ile başlatın.</li>
  <li><b>Sohbet:</b> Alt kısımdaki metin kutusuna sorunuzu yazın ve <em>Gönder</em>'e basın.</li>
  <li><b>Hücre Analizi:</b> Bir hücre seçip <em>Hücre Analizi</em> butonuna tıklayın.</li>
  <li><b>Ayarlar:</b> <em>Dosya &gt; Ayarlar</em> menüsünden LLM sağlayıcınızı yapılandırın.</li>
</ol>
<h3>Desteklenen LLM Sağlayıcıları</h3>
<ul>
  <li><b>OpenRouter</b> — Claude, GPT, Gemini, Llama ve 100+ bulut modeli</li>
  <li><b>Ollama</b> — Yerel modeller (gizlilik ve çevrimdışı kullanım)</li>
  <li><b>Gemini</b> — Google Gemini modelleri</li>
</ul>""",
        "help_content_features": """<h2>Özellikler</h2>
<h3>Tablo İşlemleri</h3>
<ul>
  <li>Hücre değerlerini ve formülleri okuma/yazma</li>
  <li>Kalın, italik, renk, yazı boyutu stilleri uygulama</li>
  <li>Hücre birleştirme ve ayırma</li>
  <li>Gelişmiş kenarlıklar ve tablo tasarımı</li>
  <li>Metin hizalama ve kaydırma</li>
</ul>
<h3>Akıllı Araçlar</h3>
<ul>
  <li><b>Formül Doğrulama:</b> Formülleri kontrol eder ve öneriler sunar</li>
  <li><b>Veri Profili:</b> Seçili alanın istatistiksel özetini çıkarır</li>
  <li><b>Hata Taraması:</b> Tablodaki formül hatalarını tespit eder</li>
  <li><b>Otomatik Formülleştir:</b> Veri ilişkilerini algılayıp formül önerir</li>
</ul>
<h3>Hızlı Eylemler</h3>
<ul>
  <li>Seçili alanı temizle, doldur veya formatla</li>
  <li>Tablo ve başlık oluştur</li>
  <li>Aykırı değerleri vurgula</li>
  <li>Boşlukları temizle, metni sayıya/tarihe çevir</li>
</ul>""",
        "help_content_commands": """<h2>Kısayol Komutları</h2>
<p>Sohbet kutusuna <code>/</code> yazarak komutları kullanabilirsiniz:</p>
<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
  <tr><th>Komut</th><th>Açıklama</th></tr>
  <tr><td><code>/help</code></td><td>Komut listesini gösterir</td></tr>
  <tr><td><code>/analyze</code></td><td>Seçili hücreyi analiz eder</td></tr>
  <tr><td><code>/connect</code></td><td>LibreOffice'e bağlanır</td></tr>
  <tr><td><code>/profile</code></td><td>Seçili alan için veri profili çıkarır</td></tr>
  <tr><td><code>/validate</code></td><td>Seçili hücredeki formülü doğrular</td></tr>
  <tr><td><code>/changes</code></td><td>Değişiklik geçmişini gösterir</td></tr>
  <tr><td><code>/undo</code></td><td>Son değişikliği geri alır</td></tr>
  <tr><td><code>/clear</code></td><td>Sohbet geçmişini temizler</td></tr>
</table>
<h3>Klavye Kısayolları</h3>
<ul>
  <li><b>Ctrl+Enter</b> — Mesaj gönder</li>
</ul>""",
        "help_content_about": """<h2>ArasAI</h2>
<p>LibreOffice Calc için yapay zeka destekli asistan.</p>
<p><b>Sürüm:</b> 1.0.0</p>
<p><b>Lisans:</b> MIT</p>
<hr>
<h3>Geliştirici</h3>
<p>
  <b>GitHub:</b> <a href="https://github.com/palamut62">github.com/palamut62</a><br>
  <b>X (Twitter):</b> <a href="https://x.com/palamut62">x.com/palamut62</a>
</p>
<hr>
<p style="color:gray;font-size:small;">Formül analizi, hata tespiti ve tablo manipülasyonu işlemlerinde yardımcı olur.</p>""",
        # Chat Widget
        "chat_placeholder": "ArasAI ile konuşun... (Ctrl+Enter)",
        "chat_send": "Gönder",
        "chat_clear": "Temizle",
        "chat_stop": "Durdur",
        "chat_thinking": "ArasAI düşünüyor",
        "chat_you": "SİZ",
        "chat_aras": "ARASAI",
        "chat_provider_model": "LLM: {provider} · {model}",
        "msg_generation_cancelled": "Yanıt durduruldu.",
    },
    "en": {
        "window_title": "ArasAI",
        # Menus
        "menu_file": "File",
        "menu_save_chat": "Save Chat...",
        "menu_load_chat": "Load Chat...",
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
        "toolbar_quick_actions": "Quick Actions",
        "toolbar_formula_check": "Validate Formula",
        "toolbar_data_profile": "Data Profile",
        "toolbar_errors_scan": "Error Scan",
        "toolbar_changes": "Changes",
        "toolbar_undo": "Undo",
        "toolbar_save_chat": "Save",
        "toolbar_load_chat": "Load",
        "toolbar_export_report": "Report",
        "ribbon_home": "Home",
        "ribbon_history": "History",
        "toolbar_connect_tooltip": "Connect to LibreOffice",
        "toolbar_analyze_tooltip": "Analyze selected cell",
        "toolbar_clear_tooltip": "Clear chat history",
        "toolbar_quick_clear": "Clear Selection",
        "toolbar_quick_fill": "Fill Selection",
        "toolbar_quick_format": "Format Selection",
        "toolbar_quick_table": "Create Table",
        "toolbar_quick_header": "Format Header",
        "toolbar_quick_outliers": "Highlight Outliers",
        "toolbar_clean_trim": "Trim Whitespace",
        "toolbar_clean_number": "Text to Number",
        "toolbar_clean_date": "Text to Date",
        "toolbar_formulaize": "Auto Formula",
        "preview_title": "Selection",
        "preview_empty": "No selection",
        "preview_multi": "Multiple selection",
        "preview_no_lo": "LibreOffice not connected",
        "preview_error": "Preview error",
        "preview_stats": "{rows}x{cols} ({total}) | empty {empty} | value {values} | text {text} | formula {formula}",
        "preview_samples": "Samples: {samples}",
        "preview_multi_stats": "{count} ranges",
        # Status Bar
        "status_lo_connected": "LO: Connected",
        "status_lo_disconnected": "LO: Disconnected",
        "status_llm_error": "(error)",
        "status_selected": "Selected",
        "status_tokens_est": "Tokens ~P:{prompt} ~C:{completion}",
        "status_cost_est": "Cost ~{cost}",
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
        "settings_gemini_api_key": "Gemini API Key:",
        "settings_model": "Model:",
        "settings_price_per_1k": "Price ($/1k) P/C:",
        "settings_fetch_models": "Fetch Models",
        "settings_ollama_url": "Ollama URL:",
        "settings_api_key_required": "Please enter your API key to fetch models.",
        "settings_gemini_api_key_required": "Please enter your Gemini API key to fetch models.",
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
        "msg_quick_clear_done": "Selection cleared.",
        "msg_quick_fill_done": "Selection filled.",
        "msg_quick_format_done": "Selection formatted.",
        "msg_quick_action_error": "Quick action error: {}",
        "msg_table_need_range": "Select a range to create a table.",
        "msg_table_done": "Table created.",
        "msg_header_done": "Header formatted.",
        "msg_outlier_need_range": "Select a range to highlight outliers.",
        "msg_outlier_not_enough": "Not enough numeric data for outlier analysis.",
        "msg_outlier_done": "Outliers found: {0}",
        "msg_change_table": "Table created: {0}",
        "msg_change_header": "Header formatted: {0}",
        "msg_change_outliers": "Outliers highlighted: {0}",
        "msg_clean_need_range": "Select a range for this action.",
        "msg_clean_done": "Trimmed cells: {0}",
        "msg_clean_number_done": "Converted to number: {0}",
        "msg_clean_date_done": "Converted to date: {0}",
        "msg_change_clean": "Cleanup applied: {0}",
        "msg_formulaize_need_range": "Select a range to formulaize.",
        "msg_formulaize_multi": "Formulaize works on a single range. Please select one range.",
        "msg_formulaize_none": "No suitable formula relationship found.",
        "msg_formulaize_done": "Formulaized cells: {0}",
        "msg_formulaize_error": "Formulaize error: {}",
        "msg_change_formulaize": "Formulaized: {0}",
        "msg_formulaize_preview": "Suggested formulas:",
        "msg_formulaize_cancelled": "Formulaize cancelled.",
        "msg_formulaize_title": "Formulaize Confirmation",
        "msg_change_clear": "Cleared: {0}",
        "msg_change_fill": "Filled: {0}",
        "msg_change_format": "Formatted: {0}",
        "msg_no_changes": "Change history is empty.",
        "msg_undo_done": "Undone: {0}",
        "msg_undo_none": "No changes to undo.",
        "msg_undo_error": "Undo error: {}",
        "msg_chat_saved": "Chat saved: {0}",
        "msg_chat_save_error": "Failed to save chat: {}",
        "msg_chat_loaded": "Chat loaded: {0}",
        "msg_chat_load_error": "Failed to load chat: {}",
        "msg_report_saved": "Report saved: {0}",
        "msg_report_save_error": "Failed to save report: {}",
        "cmd_help_header": "**Shortcut Commands**",
        "cmd_desc_analyze": "Analyze selected cell",
        "cmd_desc_connect": "Connect to LibreOffice",
        "cmd_desc_profile": "Profile selected/active range",
        "cmd_desc_validate": "Validate formula in selected cell",
        "cmd_desc_changes": "Show change history",
        "cmd_desc_undo": "Undo last change",
        "cmd_desc_clear": "Clear chat history",
        "cmd_unknown": "Unknown command: {0}. Type `/help` for help.",
        "chat_slash_hint": "Type / for commands (e.g., /help)",
        "msg_formula_single_cell": "Please select a single cell.",
        "msg_formula_missing": "No formula found in cell {0}.",
        "msg_formula_ok": "Formula looks valid.\n\nCell: {0}\nFormula: `{1}`",
        "msg_formula_error": "Formula error.\n\nCell: {address}\nFormula: `{formula}`\nError: {error}\n{description}",
        "msg_formula_suggestion": "Suggestion: {0}",
        "msg_formula_check_error": "Formula validation error: {}",
        "msg_profile_no_range": "No range found for profiling.",
        "msg_profile_empty": "No data found to profile.",
        "msg_profile_none": "None",
        "msg_profile_error": "Data profile error: {}",
        "msg_errors_found": "{0} errors found. Showing first 10:",
        "msg_errors_none": "No formula errors found.",
        "msg_errors_scan_error": "Error scan failed: {}",
        "msg_errors_suggestion": "Suggestion ({0}): {1}",
        "msg_tool_call_title": "Tool Confirmation",
        "msg_tool_call_confirm": "The following actions will be performed. Continue?",
        "msg_tool_call_cancelled": "Tool call cancelled.",
        "msg_tool_call_yes": "Yes",
        "msg_tool_call_no": "No",
        "msg_tool_call_always": "Always Allow",
        # About
        "about_title": "About",
        "about_content": "<h3>ArasAI</h3><p>AI-powered assistant for LibreOffice Calc.</p><p>Helps with formula analysis, error detection, and spreadsheet manipulation.</p><p>Version: 1.0.0</p>",
        # Help Dialog
        "help_title": "Help",
        "help_tab_start": "Getting Started",
        "help_tab_features": "Features",
        "help_tab_commands": "Commands",
        "help_tab_about": "About",
        "help_close": "Close",
        "menu_help_guide": "User Guide...",
        "help_content_start": """<h2>Welcome to ArasAI</h2>
<p>ArasAI is an AI-powered smart assistant add-on for LibreOffice Calc.</p>
<h3>Quick Start</h3>
<ol>
  <li><b>Connect:</b> Click the <em>Connect</em> button in the toolbar or launch with <code>./launch.sh</code>.</li>
  <li><b>Chat:</b> Type your question in the text box at the bottom and press <em>Send</em>.</li>
  <li><b>Cell Analysis:</b> Select a cell and click <em>Cell Analysis</em>.</li>
  <li><b>Settings:</b> Configure your LLM provider via <em>File &gt; Settings</em>.</li>
</ol>
<h3>Supported LLM Providers</h3>
<ul>
  <li><b>OpenRouter</b> — Claude, GPT, Gemini, Llama and 100+ cloud models</li>
  <li><b>Ollama</b> — Local models (privacy and offline use)</li>
  <li><b>Gemini</b> — Google Gemini models</li>
</ul>""",
        "help_content_features": """<h2>Features</h2>
<h3>Spreadsheet Operations</h3>
<ul>
  <li>Read/write cell values and formulas</li>
  <li>Apply styles (bold, italic, color, font size)</li>
  <li>Cell merging and unmerging</li>
  <li>Advanced borders and table design</li>
  <li>Text alignment and wrapping</li>
</ul>
<h3>Smart Tools</h3>
<ul>
  <li><b>Formula Validation:</b> Checks formulas and provides suggestions</li>
  <li><b>Data Profile:</b> Extracts statistical summary of selected range</li>
  <li><b>Error Scan:</b> Detects formula errors in your spreadsheet</li>
  <li><b>Auto Formula:</b> Detects data relationships and suggests formulas</li>
</ul>
<h3>Quick Actions</h3>
<ul>
  <li>Clear, fill, or format selected area</li>
  <li>Create tables and headers</li>
  <li>Highlight outliers</li>
  <li>Trim whitespace, convert text to number/date</li>
</ul>""",
        "help_content_commands": """<h2>Shortcut Commands</h2>
<p>Type <code>/</code> in the chat box to use commands:</p>
<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
  <tr><th>Command</th><th>Description</th></tr>
  <tr><td><code>/help</code></td><td>Show command list</td></tr>
  <tr><td><code>/analyze</code></td><td>Analyze selected cell</td></tr>
  <tr><td><code>/connect</code></td><td>Connect to LibreOffice</td></tr>
  <tr><td><code>/profile</code></td><td>Profile selected range</td></tr>
  <tr><td><code>/validate</code></td><td>Validate formula in selected cell</td></tr>
  <tr><td><code>/changes</code></td><td>Show change history</td></tr>
  <tr><td><code>/undo</code></td><td>Undo last change</td></tr>
  <tr><td><code>/clear</code></td><td>Clear chat history</td></tr>
</table>
<h3>Keyboard Shortcuts</h3>
<ul>
  <li><b>Ctrl+Enter</b> — Send message</li>
</ul>""",
        "help_content_about": """<h2>ArasAI</h2>
<p>AI-powered assistant for LibreOffice Calc.</p>
<p><b>Version:</b> 1.0.0</p>
<p><b>License:</b> MIT</p>
<hr>
<h3>Developer</h3>
<p>
  <b>GitHub:</b> <a href="https://github.com/palamut62">github.com/palamut62</a><br>
  <b>X (Twitter):</b> <a href="https://x.com/palamut62">x.com/palamut62</a>
</p>
<hr>
<p style="color:gray;font-size:small;">Helps with formula analysis, error detection, and spreadsheet manipulation.</p>""",
        # Chat Widget
        "chat_placeholder": "Talk to ArasAI... (Ctrl+Enter)",
        "chat_send": "Send",
        "chat_clear": "Clear",
        "chat_stop": "Stop",
        "chat_thinking": "ArasAI is thinking",
        "chat_you": "YOU",
        "chat_aras": "ARASAI",
        "chat_provider_model": "LLM: {provider} · {model}",
        "msg_generation_cancelled": "Response stopped.",
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
