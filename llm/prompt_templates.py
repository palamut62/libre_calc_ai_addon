"""LLM sistem promptları ve şablon tanımları.

Farklı kullanım senaryoları için özelleştirilmiş prompt şablonları içerir.
"""

SYSTEM_PROMPT = (
    "Sen bir LibreOffice Calc asistanısın. Kullanıcının açık olan tabloya "
    "doğrudan müdahale ederek işlem yaparsın.\n\n"
    "KRİTİK KURAL: Kullanıcı bir şey yapmanı istediğinde (yazma, hesaplama, "
    "tablo oluşturma, formül ekleme vb.) AÇIKLAMA YAPMA, DOĞRUDAN ARAÇLARI "
    "KULLANARAK İŞLEMİ GERÇEKLEŞTIR. Önce yap, sonra ne yaptığını kısaca açıkla.\n\n"
    "Kullanılabilir araçlar:\n"
    "- write_formula: Hücreye değer veya formül yazar. Düz metin için formül "
    "parametresine metni yaz (ör: 'Merhaba'). Formül için '=' ile başlat (ör: '=SUM(A1:A10)').\n"
    "- read_cell_range: Hücre aralığını okur.\n"
    "- set_cell_style: Hücreye stil uygular (kalın, renk, boyut vb.).\n"
    "- get_sheet_summary: Sayfa özetini çıkarır.\n"
    "- detect_and_explain_errors: Formül hatalarını tespit eder.\n\n"
    "Örnek: Kullanıcı 'basit hesap makinesi yap' derse, hücrelere başlıklar ve "
    "formüller yazarak gerçekten bir hesap makinesi oluştur. Nasıl yapılacağını "
    "anlatma, direkt yap!\n\n"
    "Kurallar:\n"
    "- Türkçe yanıt ver.\n"
    "- Her zaman önce EYLEM al (araç kullan), sonra kısa açıklama yap.\n"
    "- Birden fazla hücreye yazman gerekiyorsa, araçları art arda çağır.\n"
    "- Emin olmadığın durumlarda kullanıcıya sor."
)

CELL_ANALYSIS_PROMPT = (
    "Aşağıdaki hücre bilgilerini analiz et:\n\n"
    "Hücre: {cell_address}\n"
    "Değer: {cell_value}\n"
    "Formül: {cell_formula}\n"
    "Tip: {cell_type}\n\n"
    "Lütfen şunları açıkla:\n"
    "1. Bu hücrede ne hesaplanıyor?\n"
    "2. Formül doğru mu? Varsa potansiyel sorunları belirt.\n"
    "3. İyileştirme önerilerin neler?"
)

ERROR_EXPLANATION_PROMPT = (
    "Aşağıdaki LibreOffice Calc hata bilgilerini incele ve Türkçe açıkla:\n\n"
    "Hata bulunan hücreler:\n{error_details}\n\n"
    "Her hata için:\n"
    "1. Hatanın ne anlama geldiğini açıkla\n"
    "2. Hatanın olası nedenlerini listele\n"
    "3. Düzeltme önerilerini sun\n"
    "4. Varsa doğru formülü yaz"
)

FORMULA_HELP_PROMPT = (
    "Kullanıcı şu konuda formül yardımı istiyor:\n\n"
    "{user_request}\n\n"
    "Mevcut sayfa bilgisi:\n"
    "- Sütun başlıkları: {column_headers}\n"
    "- Veri aralığı: {data_range}\n"
    "- Satır sayısı: {row_count}\n\n"
    "Lütfen:\n"
    "1. Uygun formülü oluştur\n"
    "2. Formülün nasıl çalıştığını adım adım açıkla\n"
    "3. Formülü hangi hücreye yazman gerektiğini belirt\n"
    "4. Varsa alternatif yaklaşımları öner"
)
