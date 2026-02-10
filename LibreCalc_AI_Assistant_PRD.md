

# PRD: LibreCalc AI Assistant (Claude-Style)

## 1. Proje Vizyonu

LibreOffice Calc kullanıcılarına, tıpkı **Claude Code** terminal aracında olduğu gibi, doğrudan tablo içeriğine müdahale edebilen, formülleri analiz eden ve doğal dil komutlarıyla karmaşık mühendislik hesaplamalarını otomatize eden bir yapay zeka ekosistemi sunmak.

## 2. Temel Mimari ve Teknoloji Yığını

* **İşletim Sistemi:** Linux (Öncelikli Ubuntu)
* **Dil:** Python 3.10+
* **Bağlantı Köprüsü:** PyUNO (LibreOffice Universal Network Objects)
* **LLM Sağlayıcıları:** * **OpenRouter:** (Claude 3.5 Sonnet, GPT-4o gibi üst düzey modeller)
* **Ollama:** (Yerel kullanım için Llama 3, Mistral, Phi-3)


* **Arayüz:** PyQt5 veya PySide6 (Yan panel asistanı)

---

## 3. Fonksiyonel Gereksinimler

### 3.1. Çoklu LLM ve Sağlayıcı Yönetimi

* **Dinamik Seçim:** Kullanıcı, arayüz üzerinden tek tıkla **Ollama** (ücretsiz/yerel) ve **OpenRouter** (ücretli/bulut) arasında geçiş yapabilmelidir.
* **API Anahtar Yönetimi:** OpenRouter API anahtarları yerel bir `.env` veya şifreli konfigürasyon dosyasında saklanmalıdır.
* **Model Parametreleri:** Sıcaklık (temperature), sistem promptu ve maksimum token sınırı kullanıcı tarafından ayarlanabilmelidir.

### 3.2. Bağlamsal Analiz ve Denetim (Contextual Audit)

* **Hücre İnceleme (Cell Inspection):** AI, seçili hücrenin sadece değerini değil, `Formula` (formül), `FormulaLocal` (yerel dildeki formül) ve `CellBackColor` (biçim) özelliklerini okuyabilmelidir.
* **Sayfa Tarama:** Aktif sayfanın yapısını (başlıklar, veri aralıkları, boş hücreler) analiz ederek genel bir özet çıkarabilmelidir.
* **Hata Ayıklama:** `#REF!`, `#NAME?`, `#VALUE!` gibi hataların nedenini, hücre referanslarını takip ederek (Precedents) kullanıcıya doğal dille açıklayabilmelidir.

### 3.3. Aksiyon ve Manipülasyon Yetenekleri

* **Formül Yazımı:** AI, karmaşık mühendislik formüllerini (örn: metraj cetveli çarpımları, KDV hesapları, lojistik maliyet analizleri) istenen hücreye otomatik yazabilmelidir.
* **Tablo Oluşturma:** "Bana 10 satırlık, Poz No, Tanım, Miktar, Birim Fiyat ve Toplam sütunlarından oluşan bir tablo yap" dendiğinde tabloyu sıfırdan inşa edebilmelidir.
* **Otomatik Biçimlendirme:** Veri setindeki aykırı değerleri (outliers) renklendirme, başlıkları kalınlaştırma ve hücre kenarlıkları oluşturma.

---

## 4. Teknik Gereksinimler (Technical Requirements)

### 4.1. Veri İletişim Protokolü

* LibreOffice, Python scriptlerinin bağlanabilmesi için soket dinleme modunda başlatılmalıdır:
`libreoffice --calc --accept="socket,host=localhost,port=2002;urp;"`
* Python scripti, `uno.getComponentContext()` üzerinden bu sokete bağlanarak canlı müdahale gerçekleştirmelidir.

### 4.2. Function Calling (Fonksiyon Çağırma) Yapısı

AI modeline (özellikle Claude 3.5'e) aşağıdaki gibi fonksiyon şemaları (Tools) tanımlanmalıdır:

* `read_cell_range(range_name)`
* `write_formula(cell_address, formula)`
* `set_cell_style(range_name, color, bold_status)`
* `get_sheet_summary()`

---

## 5. Kullanıcı Arayüzü (UI) Tasarımı

* **Kompakt Yan Panel:** Calc penceresinin sağ tarafına sabitlenebilir veya üzerinde yüzebilir (floating).
* **Chat Geçmişi:** Yapılan işlemlerin ve verilen komutların geçmişi.
* **Analiz Penceresi:** AI bir hücreyi incelediğinde, hücrenin "röntgenini" (formül yapısı, bağımlılıklar) gösteren özel bir bilgi alanı.

---

## 6. Güvenlik ve Gizlilik

* **Yerel Öncelik:** Hassas mühendislik verileriyle çalışırken (örn: gizli ihale fiyatları) sistemin tamamen Ollama (yerel) üzerinden çalışabilmesi garantilenmelidir.
* **Veri Filtreleme:** AI'ya sadece seçili hücrelerin verisi gönderilmeli, tüm dosya rıza dışı buluta yüklenmemelidir.

---

## 7. Gelecek Yol Haritası (Roadmap)

* **Faz 1:** Temel bağlantı ve Ollama/OpenRouter üzerinden basit hücre yazma işlemi.
* **Faz 2:** Hücre/Formül analiz modülü ve hata ayıklama asistanı.
* **Faz 3:** PyQt5 tabanlı tam kapsamlı kullanıcı paneli ve Ubuntu paketleme (.deb).
* **Faz 4:** Sesli komut desteği (Örn: "Tüm toplamları kontrol et").


