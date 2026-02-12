"""LLM araç tanımları ve araç yönlendirici (dispatcher).

OpenAI function calling şemasına uygun araç tanımları ve
gelen araç çağrılarını ilgili core modül metodlarına yönlendiren sınıf.
"""

import json
import logging

logger = logging.getLogger(__name__)


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_cell_range",
            "description": "Belirtilen hücre aralığındaki değerleri okur",
            "parameters": {
                "type": "object",
                "properties": {
                    "range_name": {
                        "type": "string",
                        "description": "Hücre aralığı (ör: A1:D10, B2, Sheet1.A1:C5)",
                    }
                },
                "required": ["range_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_formula",
            "description": "Belirtilen hücreye metin, sayı veya formül yazar. Düz metin için direkt yaz (ör: 'Toplam'), sayı için sayı yaz (ör: '42'), formül için = ile başlat (ör: '=SUM(A1:A10)'). Tablo oluştururken tüm başlıkları ve verileri mümkünse tek seferde yaz.",

            "parameters": {
                "type": "object",
                "properties": {
                    "cell": {
                        "type": "string",
                        "description": "Hedef hücre adresi (ör: A1, B5)",
                    },
                    "formula": {
                        "type": "string",
                        "description": "Yazılacak içerik: metin (ör: 'Başlık'), sayı (ör: '100'), veya formül (ör: '=A1+B1')",
                    },
                },
                "required": ["cell", "formula"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_cell_style",
            "description": "Belirtilen hücre veya aralığa stil ve biçimlendirme uygular. Genellikle write_formula veya merge_cells işleminden sonra görselleştirme için kullanılır.",

            "parameters": {
                "type": "object",
                "properties": {
                    "range_name": {
                        "type": "string",
                        "description": "Hedef hücre veya aralık (ör: A1, A1:D10)",
                    },
                    "bold": {
                        "type": "boolean",
                        "description": "Kalın yazı tipi",
                    },
                    "italic": {
                        "type": "boolean",
                        "description": "İtalik yazı tipi",
                    },
                    "font_size": {
                        "type": "number",
                        "description": "Yazı tipi boyutu (punto)",
                    },
                    "bg_color": {
                        "type": "string",
                        "description": "Arka plan rengi (hex: #FF0000 veya isim: yellow)",
                    },
                    "font_color": {
                        "type": "string",
                        "description": "Yazı rengi (hex: #000000 veya isim: red)",
                    },
                    "h_align": {
                        "type": "string",
                        "enum": ["left", "center", "right", "justify"],
                        "description": "Yatay hizalama",
                    },
                    "v_align": {
                        "type": "string",
                        "enum": ["top", "center", "bottom"],
                        "description": "Dikey hizalama",
                    },
                    "wrap_text": {
                        "type": "boolean",
                        "description": "Metni kaydır",
                    },
                    "border_color": {
                        "type": "string",
                        "description": "Kenarlık rengi (hex veya isim). Hücre/aralık çevresine çerçeve çizer.",
                    },
                    "number_format": {
                        "type": "string",
                        "description": "Sayı biçimi (ör: #,##0.00, 0%, dd.mm.yyyy)",
                    },
                },
                "required": ["range_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_sheet_summary",
            "description": "Aktif sayfanın veya belirtilen sayfanın özetini döndürür (boyut, dolu hücre sayısı, sütun başlıkları vb.)",
            "parameters": {
                "type": "object",
                "properties": {
                    "sheet_name": {
                        "type": "string",
                        "description": "Sayfa adı (boş bırakılırsa aktif sayfa kullanılır)",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "detect_and_explain_errors",
            "description": "Belirtilen aralıktaki formül hatalarını tespit eder ve Türkçe açıklama ile çözüm önerisi sunar",
            "parameters": {
                "type": "object",
                "properties": {
                    "range_name": {
                        "type": "string",
                        "description": "Kontrol edilecek hücre aralığı (ör: A1:Z100). Boş bırakılırsa tüm sayfa taranır.",
                    }
                },
                "required": [],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "merge_cells",
            "description": "Belirtilen hücre aralığını birleştirir (merge). Genellikle ana başlıklar için kullanılır. Bu işlemden sonra write_formula ile başlık metnini yazmayı ve set_cell_style ile stil vermeyi unutma.",

            "parameters": {
                "type": "object",
                "properties": {
                    "range_name": {
                        "type": "string",
                        "description": "Birleştirilecek aralık (ör: A1:D1)",
                    },
                    "center": {
                        "type": "boolean",
                        "description": "İçeriği ortala (varsayılan: true)",
                    }
                },
                "required": ["range_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_column_width",
            "description": "Sütun genişliğini ayarlar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "col_letter": {
                        "type": "string",
                        "description": "Sütun harfi (ör: A, B, AB)",
                    },
                    "width_mm": {
                        "type": "number",
                        "description": "Genişlik (milimetre cinsinden, ör: 30)",
                    },
                },
                "required": ["col_letter", "width_mm"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_row_height",
            "description": "Satır yüksekliğini ayarlar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "row_num": {
                        "type": "integer",
                        "description": "Satır numarası (1 tabanlı)",
                    },
                    "height_mm": {
                        "type": "number",
                        "description": "Yükseklik (milimetre cinsinden, ör: 8)",
                    },
                },
                "required": ["row_num", "height_mm"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "insert_rows",
            "description": "Belirtilen konuma yeni satırlar ekler. Mevcut satırları aşağı kaydırır.",
            "parameters": {
                "type": "object",
                "properties": {
                    "row_num": {
                        "type": "integer",
                        "description": "Ekleme yapılacak satır numarası (1 tabanlı)",
                    },
                    "count": {
                        "type": "integer",
                        "description": "Eklenecek satır sayısı (varsayılan: 1)",
                    },
                },
                "required": ["row_num"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "insert_columns",
            "description": "Belirtilen konuma yeni sütunlar ekler. Mevcut sütunları sağa kaydırır.",
            "parameters": {
                "type": "object",
                "properties": {
                    "col_letter": {
                        "type": "string",
                        "description": "Ekleme yapılacak sütun harfi",
                    },
                    "count": {
                        "type": "integer",
                        "description": "Eklenecek sütun sayısı (varsayılan: 1)",
                    },
                },
                "required": ["col_letter"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_rows",
            "description": "Belirtilen satırları siler. DİKKAT: Bu işlem geri alınamaz!",
            "parameters": {
                "type": "object",
                "properties": {
                    "row_num": {
                        "type": "integer",
                        "description": "Silinecek ilk satır numarası (1 tabanlı)",
                    },
                    "count": {
                        "type": "integer",
                        "description": "Silinecek satır sayısı (varsayılan: 1)",
                    },
                },
                "required": ["row_num"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_columns",
            "description": "Belirtilen sütunları siler. DİKKAT: Bu işlem geri alınamaz!",
            "parameters": {
                "type": "object",
                "properties": {
                    "col_letter": {
                        "type": "string",
                        "description": "Silinecek ilk sütun harfi",
                    },
                    "count": {
                        "type": "integer",
                        "description": "Silinecek sütun sayısı (varsayılan: 1)",
                    },
                },
                "required": ["col_letter"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "auto_fit_column",
            "description": "Sütun genişliğini içeriğe göre otomatik ayarlar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "col_letter": {
                        "type": "string",
                        "description": "Sütun harfi (ör: A, B)",
                    },
                },
                "required": ["col_letter"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_all_formulas",
            "description": "Sayfadaki tüm formülleri listeler. Her formülün adresi, içeriği, hesaplanan değeri ve bağımlı olduğu hücreleri gösterir.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sheet_name": {
                        "type": "string",
                        "description": "Sayfa adı (boş bırakılırsa aktif sayfa)",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_spreadsheet_structure",
            "description": "Tablonun formül yapısını ve veri akışını analiz eder. Giriş hücrelerini (veri), ara hesaplama hücrelerini ve çıkış hücrelerini (sonuç) tespit eder. Tablonun mantığını anlamak için kullanılır.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sheet_name": {
                        "type": "string",
                        "description": "Sayfa adı (boş bırakılırsa aktif sayfa)",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_cell_details",
            "description": "Bir hücrenin detaylı bilgilerini döndürür: değer, formül, yerel formül, tip, arka plan rengi, sayı formatı.",
            "parameters": {
                "type": "object",
                "properties": {
                    "address": {
                        "type": "string",
                        "description": "Hücre adresi (ör: A1, B5)",
                    }
                },
                "required": ["address"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_cell_precedents",
            "description": "Bir hücrenin formülünde referans verilen (bağımlı olduğu) hücreleri listeler.",
            "parameters": {
                "type": "object",
                "properties": {
                    "address": {
                        "type": "string",
                        "description": "Hücre adresi (ör: B5)",
                    }
                },
                "required": ["address"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_cell_dependents",
            "description": "Bu hücreye bağımlı olan (bu hücreyi kullanan) formül hücrelerini listeler.",
            "parameters": {
                "type": "object",
                "properties": {
                    "address": {
                        "type": "string",
                        "description": "Hücre adresi (ör: A1)",
                    }
                },
                "required": ["address"],
            },
        },
    },
    # === YENİ CLAUDE EXCEL ÖZELLİKLERİ ===
    {
        "type": "function",
        "function": {
            "name": "sort_range",
            "description": "Belirtilen veri aralığını sıralar. Başlık satırı varsa has_header=true olarak belirtin.",
            "parameters": {
                "type": "object",
                "properties": {
                    "range_name": {
                        "type": "string",
                        "description": "Sıralanacak aralık (ör: A1:D10)",
                    },
                    "sort_column": {
                        "type": "integer",
                        "description": "Sıralama yapılacak sütun numarası (0 tabanlı, aralık içindeki pozisyon)",
                    },
                    "ascending": {
                        "type": "boolean",
                        "description": "Artan sıralama (true) veya azalan (false). Varsayılan: true",
                    },
                    "has_header": {
                        "type": "boolean",
                        "description": "İlk satır başlık mı? Varsayılan: true",
                    },
                },
                "required": ["range_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_auto_filter",
            "description": "Veri aralığına otomatik filtre uygular veya kaldırır.",
            "parameters": {
                "type": "object",
                "properties": {
                    "range_name": {
                        "type": "string",
                        "description": "Filtre uygulanacak aralık (ör: A1:D10)",
                    },
                    "enable": {
                        "type": "boolean",
                        "description": "Filtreyi aç (true) veya kapat (false). Varsayılan: true",
                    },
                },
                "required": ["range_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_conditional_format",
            "description": "Hücre aralığına koşullu biçimlendirme uygular. Renk skalası, veri çubukları veya değer bazlı renklendirme yapabilir.",
            "parameters": {
                "type": "object",
                "properties": {
                    "range_name": {
                        "type": "string",
                        "description": "Biçimlendirilecek aralık (ör: A1:A20)",
                    },
                    "format_type": {
                        "type": "string",
                        "enum": ["color_scale", "data_bar", "value_condition"],
                        "description": "Biçim tipi: color_scale (renk skalası), data_bar (veri çubuğu), value_condition (değer koşulu)",
                    },
                    "condition": {
                        "type": "string",
                        "enum": ["greater_than", "less_than", "equal", "between", "contains"],
                        "description": "Koşul tipi (sadece value_condition için)",
                    },
                    "value1": {
                        "type": "string",
                        "description": "Birinci değer (karşılaştırma veya between için alt sınır)",
                    },
                    "value2": {
                        "type": "string",
                        "description": "İkinci değer (sadece between için üst sınır)",
                    },
                    "color": {
                        "type": "string",
                        "description": "Koşul sağlandığında uygulanacak arka plan rengi (ör: #FF0000 veya red)",
                    },
                },
                "required": ["range_name", "format_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_data_validation",
            "description": "Hücreye veri doğrulama kuralı ekler (dropdown liste, sayı aralığı vb.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "range_name": {
                        "type": "string",
                        "description": "Doğrulama uygulanacak aralık (ör: A1:A10)",
                    },
                    "validation_type": {
                        "type": "string",
                        "enum": ["list", "whole_number", "decimal", "date", "text_length"],
                        "description": "Doğrulama tipi",
                    },
                    "values": {
                        "type": "string",
                        "description": "Liste için virgülle ayrılmış değerler (ör: 'Evet,Hayır,Belki') veya sayı aralığı için 'min;max' formatında",
                    },
                    "error_message": {
                        "type": "string",
                        "description": "Geçersiz giriş durumunda gösterilecek hata mesajı",
                    },
                },
                "required": ["range_name", "validation_type", "values"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_sheets",
            "description": "Çalışma kitabındaki tüm sayfa isimlerini listeler.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "switch_sheet",
            "description": "Belirtilen sayfaya geçiş yapar (aktif sayfa yapar).",
            "parameters": {
                "type": "object",
                "properties": {
                    "sheet_name": {
                        "type": "string",
                        "description": "Geçiş yapılacak sayfa adı",
                    },
                },
                "required": ["sheet_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_sheet",
            "description": "Yeni bir sayfa oluşturur.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sheet_name": {
                        "type": "string",
                        "description": "Yeni sayfa adı",
                    },
                    "position": {
                        "type": "integer",
                        "description": "Sayfa pozisyonu (0 tabanlı). Belirtilmezse sona eklenir.",
                    },
                },
                "required": ["sheet_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rename_sheet",
            "description": "Sayfanın adını değiştirir.",
            "parameters": {
                "type": "object",
                "properties": {
                    "old_name": {
                        "type": "string",
                        "description": "Mevcut sayfa adı",
                    },
                    "new_name": {
                        "type": "string",
                        "description": "Yeni sayfa adı",
                    },
                },
                "required": ["old_name", "new_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "copy_range",
            "description": "Bir hücre aralığını başka bir konuma kopyalar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_range": {
                        "type": "string",
                        "description": "Kaynak aralık (ör: A1:C10)",
                    },
                    "target_cell": {
                        "type": "string",
                        "description": "Hedef başlangıç hücresi (ör: E1)",
                    },
                },
                "required": ["source_range", "target_cell"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_chart",
            "description": "Verilerden grafik oluşturur. Çubuk, çizgi, pasta veya dağılım grafiği desteklenir.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data_range": {
                        "type": "string",
                        "description": "Grafik verileri için aralık (ör: A1:B10)",
                    },
                    "chart_type": {
                        "type": "string",
                        "enum": ["bar", "line", "pie", "scatter", "column"],
                        "description": "Grafik tipi: bar (yatay çubuk), column (dikey çubuk), line (çizgi), pie (pasta), scatter (dağılım)",
                    },
                    "title": {
                        "type": "string",
                        "description": "Grafik başlığı",
                    },
                    "position": {
                        "type": "string",
                        "description": "Grafiğin yerleştirileceği hücre (ör: E1)",
                    },
                    "has_header": {
                        "type": "boolean",
                        "description": "İlk satır/sütun etiket mi? Varsayılan: true",
                    },
                },
                "required": ["data_range", "chart_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "clear_range",
            "description": "Belirtilen aralıktaki tüm içerikleri temizler (değerler, formüller).",
            "parameters": {
                "type": "object",
                "properties": {
                    "range_name": {
                        "type": "string",
                        "description": "Temizlenecek aralık (ör: A1:D10)",
                    },
                },
                "required": ["range_name"],
            },
        },
    },
]


from core.uno_bridge import LibreOfficeBridge


class ToolDispatcher:
    """Araç çağrılarını ilgili core modül metodlarına yönlendirir.

    LLM'den gelen tool_call yanıtlarını alır, araç adına göre
    uygun core modül metodunu çağırır ve sonucu döndürür.
    """

    def __init__(self, cell_inspector, cell_manipulator, sheet_analyzer, error_detector, change_logger=None):
        """Dispatcher'ı core modül nesneleriyle başlatır.

        Args:
            cell_inspector: Hücre okuma işlemleri için CellInspector nesnesi.
            cell_manipulator: Hücre yazma/stil işlemleri için CellManipulator nesnesi.
            sheet_analyzer: Sayfa analizi için SheetAnalyzer nesnesi.
            error_detector: Hata tespiti için ErrorDetector nesnesi.
        """
        self._cell_inspector = cell_inspector
        self._cell_manipulator = cell_manipulator
        self._sheet_analyzer = sheet_analyzer
        self._error_detector = error_detector
        self._change_logger = change_logger

        self._dispatch_map = {
            "read_cell_range": self._read_cell_range,
            "write_formula": self._write_formula,
            "set_cell_style": self._set_cell_style,
            "get_sheet_summary": self._get_sheet_summary,
            "detect_and_explain_errors": self._detect_and_explain_errors,
            "merge_cells": self._merge_cells,
            "set_column_width": self._set_column_width,
            "set_row_height": self._set_row_height,
            "insert_rows": self._insert_rows,
            "insert_columns": self._insert_columns,
            "delete_rows": self._delete_rows,
            "delete_columns": self._delete_columns,
            "auto_fit_column": self._auto_fit_column,
            "get_all_formulas": self._get_all_formulas,
            "analyze_spreadsheet_structure": self._analyze_spreadsheet_structure,
            "get_cell_details": self._get_cell_details,
            "get_cell_precedents": self._get_cell_precedents,
            "get_cell_dependents": self._get_cell_dependents,
            # Yeni Claude Excel özellikleri
            "sort_range": self._sort_range,
            "set_auto_filter": self._set_auto_filter,
            "set_conditional_format": self._set_conditional_format,
            "set_data_validation": self._set_data_validation,
            "list_sheets": self._list_sheets,
            "switch_sheet": self._switch_sheet,
            "create_sheet": self._create_sheet,
            "rename_sheet": self._rename_sheet,
            "copy_range": self._copy_range,
            "create_chart": self._create_chart,
            "clear_range": self._clear_range,
        }

    def _log_change(self, summary: str, cells: list | None = None, undoable: bool = True, partial: bool = False):
        if self._change_logger:
            self._change_logger(summary, cells=cells, undoable=undoable, partial=partial)

    def _snapshot_range(self, range_name: str, max_cells: int = 500) -> tuple[list | None, bool]:
        """Range için hücre snapshot alır."""
        if ":" in range_name:
            start, end = LibreOfficeBridge.parse_range_string(range_name)
        else:
            start = end = LibreOfficeBridge.parse_range_string(range_name)[0]

        row_count = end[1] - start[1] + 1
        col_count = end[0] - start[0] + 1
        total = row_count * col_count
        if total > max_cells:
            return None, True

        cells = []
        for row in range(start[1], end[1] + 1):
            for col in range(start[0], end[0] + 1):
                addr = f"{LibreOfficeBridge._index_to_column(col)}{row + 1}"
                details = self._cell_inspector.get_cell_details(addr)
                cells.append({
                    "address": addr,
                    "type": details.get("type"),
                    "formula": details.get("formula"),
                    "value": details.get("value"),
                    "background_color": details.get("background_color"),
                    "number_format": details.get("number_format"),
                    "font_color": details.get("font_color"),
                    "font_size": details.get("font_size"),
                    "bold": details.get("bold"),
                    "italic": details.get("italic"),
                    "h_align": details.get("h_align"),
                    "v_align": details.get("v_align"),
                    "wrap_text": details.get("wrap_text"),
                })

        return cells, False

    def dispatch(self, tool_name: str, arguments: dict) -> str:
        """Araç çağrısını ilgili metoda yönlendirir ve sonucu string olarak döndürür.

        Args:
            tool_name: Çağrılacak araç adı.
            arguments: Araç parametreleri sözlüğü.

        Returns:
            Araç çalışma sonucu (JSON string).
        """
        handler = self._dispatch_map.get(tool_name)
        if handler is None:
            return json.dumps({"error": f"Bilinmeyen araç: {tool_name}"}, ensure_ascii=False)

        try:
            result = handler(arguments)
            return json.dumps({"result": result}, ensure_ascii=False, default=str)
        except Exception as exc:
            logger.exception("Araç çalıştırma hatası (%s): %s", tool_name, exc)
            return json.dumps(
                {
                    "tool": tool_name,
                    "arguments": arguments,
                    "error": f"Araç çalıştırma hatası: {exc}",
                },
                ensure_ascii=False,
            )

    def _read_cell_range(self, args: dict):
        """Hücre aralığını okur."""
        return self._cell_inspector.read_range(args["range_name"])

    def _write_formula(self, args: dict):
        """Hücreye formül veya değer yazar."""
        cell = args["cell"]
        cells, _too_large = self._snapshot_range(cell, max_cells=1)
        result = self._cell_manipulator.write_formula(cell, args["formula"])
        self._log_change(f"Hücre yazıldı: {cell}", cells=cells, undoable=True, partial=False)
        return result

    def _set_cell_style(self, args: dict):
        """Hücre stilini ayarlar."""
        args = dict(args)  # orijinali değiştirme
        range_name = args.pop("range_name")
        number_format = args.pop("number_format", None)

        cells, too_large = self._snapshot_range(range_name, max_cells=300)

        # Renk dönüşümü (hex string -> int)
        for color_key in ("bg_color", "font_color", "border_color"):
            if color_key in args and isinstance(args[color_key], str):
                args[color_key] = self._parse_color(args[color_key])

        # Aralık mı tekil hücre mi?
        if ":" in range_name:
            result = self._cell_manipulator.set_range_style(range_name, **args)
        else:
            result = self._cell_manipulator.set_cell_style(range_name, **args)

        # number_format stil API'sinin değil, ayrı format API'sinin parçası
        if number_format:
            if ":" in range_name:
                start, end = LibreOfficeBridge.parse_range_string(range_name)
                for row in range(start[1], end[1] + 1):
                    for col in range(start[0], end[0] + 1):
                        addr = f"{LibreOfficeBridge._index_to_column(col)}{row + 1}"
                        self._cell_manipulator.set_number_format(addr, number_format)
            else:
                self._cell_manipulator.set_number_format(range_name, number_format)

        if too_large:
            self._log_change(f"Stil uygulandı: {range_name}", cells=None, undoable=False, partial=True)
        else:
            self._log_change(f"Stil uygulandı: {range_name}", cells=cells, undoable=True, partial=True)
        return result

    @staticmethod
    def _parse_color(color_str: str) -> int:
        """Renk string'ini RGB int'e dönüştürür."""
        color_str = color_str.strip().lower()
        color_names = {
            "red": 0xFF0000, "green": 0x00FF00, "blue": 0x0000FF,
            "yellow": 0xFFFF00, "white": 0xFFFFFF, "black": 0x000000,
            "orange": 0xFF8C00, "purple": 0x800080, "gray": 0x808080,
            "grey": 0x808080, "cyan": 0x00FFFF, "pink": 0xFFC0CB,
        }
        if color_str in color_names:
            return color_names[color_str]
        if color_str.startswith("#"):
            return int(color_str[1:], 16)
        return int(color_str, 16)

    def _get_sheet_summary(self, args: dict):
        """Sayfa özetini döndürür."""
        # SheetAnalyzer şu an sadece aktif sayfa özetini döndürüyor.
        return self._sheet_analyzer.get_sheet_summary()

    def _detect_and_explain_errors(self, args: dict):
        """Hataları tespit eder ve açıklar."""
        range_name = args.get("range_name")
        return self._error_detector.detect_and_explain(range_name)

    def _merge_cells(self, args: dict):
        """Hücreleri birleştirir."""
        range_name = args.get("range_name")
        center = args.get("center", True)
        self._cell_manipulator.merge_cells(range_name, center)
        self._log_change(f"Hücreler birleştirildi: {range_name}", cells=None, undoable=False)
        return f"{range_name} aralığı birleştirildi."

    def _set_column_width(self, args: dict):
        """Sütun genişliğini ayarlar."""
        result = self._cell_manipulator.set_column_width(
            args["col_letter"], args["width_mm"]
        )
        self._log_change(f"Sütun genişliği ayarlandı: {args['col_letter']}", cells=None, undoable=False)
        return result

    def _set_row_height(self, args: dict):
        """Satır yüksekliğini ayarlar."""
        result = self._cell_manipulator.set_row_height(
            args["row_num"], args["height_mm"]
        )
        self._log_change(f"Satır yüksekliği ayarlandı: {args['row_num']}", cells=None, undoable=False)
        return result

    def _insert_rows(self, args: dict):
        """Satır ekler."""
        result = self._cell_manipulator.insert_rows(
            args["row_num"], args.get("count", 1)
        )
        self._log_change(f"Satır eklendi: {args['row_num']} (+{args.get('count', 1)})", cells=None, undoable=False)
        return result

    def _insert_columns(self, args: dict):
        """Sütun ekler."""
        result = self._cell_manipulator.insert_columns(
            args["col_letter"], args.get("count", 1)
        )
        self._log_change(f"Sütun eklendi: {args['col_letter']} (+{args.get('count', 1)})", cells=None, undoable=False)
        return result

    def _delete_rows(self, args: dict):
        """Satır siler."""
        result = self._cell_manipulator.delete_rows(
            args["row_num"], args.get("count", 1)
        )
        self._log_change(f"Satır silindi: {args['row_num']} (-{args.get('count', 1)})", cells=None, undoable=False)
        return result

    def _delete_columns(self, args: dict):
        """Sütun siler."""
        result = self._cell_manipulator.delete_columns(
            args["col_letter"], args.get("count", 1)
        )
        self._log_change(f"Sütun silindi: {args['col_letter']} (-{args.get('count', 1)})", cells=None, undoable=False)
        return result

    def _auto_fit_column(self, args: dict):
        """Sütun genişliğini otomatik ayarlar."""
        result = self._cell_manipulator.auto_fit_column(args["col_letter"])
        self._log_change(f"Otomatik sütun genişliği: {args['col_letter']}", cells=None, undoable=False)
        return result

    def _get_all_formulas(self, args: dict):
        """Sayfadaki tüm formülleri listeler."""
        sheet_name = args.get("sheet_name")
        return self._cell_inspector.get_all_formulas(sheet_name)

    def _analyze_spreadsheet_structure(self, args: dict):
        """Tablonun yapısını analiz eder."""
        sheet_name = args.get("sheet_name")
        return self._cell_inspector.analyze_spreadsheet_structure(sheet_name)

    def _get_cell_details(self, args: dict):
        """Hücre detaylarını döndürür."""
        return self._cell_inspector.get_cell_details(args["address"])

    def _get_cell_precedents(self, args: dict):
        """Hücrenin bağımlı olduğu hücreleri listeler."""
        return self._cell_inspector.get_cell_precedents(args["address"])

    def _get_cell_dependents(self, args: dict):
        """Bu hücreye bağımlı olan hücreleri listeler."""
        return self._cell_inspector.get_cell_dependents(args["address"])

    # === YENİ CLAUDE EXCEL ÖZELLİKLERİ ===

    def _sort_range(self, args: dict):
        """Aralığı sıralar."""
        result = self._cell_manipulator.sort_range(
            args["range_name"],
            args.get("sort_column", 0),
            args.get("ascending", True),
            args.get("has_header", True),
        )
        self._log_change(f"Aralık sıralandı: {args['range_name']}", cells=None, undoable=False)
        return result

    def _set_auto_filter(self, args: dict):
        """Otomatik filtre uygular."""
        result = self._cell_manipulator.set_auto_filter(
            args["range_name"],
            args.get("enable", True),
        )
        self._log_change(f"AutoFilter: {args['range_name']}", cells=None, undoable=False)
        return result

    def _set_conditional_format(self, args: dict):
        """Koşullu biçimlendirme uygular."""
        result = self._cell_manipulator.set_conditional_format(
            args["range_name"],
            args["format_type"],
            args.get("condition"),
            args.get("value1"),
            args.get("value2"),
            args.get("color"),
        )
        self._log_change(f"Koşullu biçim: {args['range_name']}", cells=None, undoable=False)
        return result

    def _set_data_validation(self, args: dict):
        """Veri doğrulama uygular."""
        result = self._cell_manipulator.set_data_validation(
            args["range_name"],
            args["validation_type"],
            args["values"],
            args.get("error_message"),
        )
        self._log_change(f"Veri doğrulama: {args['range_name']}", cells=None, undoable=False)
        return result

    def _list_sheets(self, args: dict):
        """Sayfa isimlerini listeler."""
        return self._cell_manipulator.list_sheets()

    def _switch_sheet(self, args: dict):
        """Sayfaya geçiş yapar."""
        result = self._cell_manipulator.switch_sheet(args["sheet_name"])
        self._log_change(f"Sayfa değişti: {args['sheet_name']}", cells=None, undoable=False)
        return result

    def _create_sheet(self, args: dict):
        """Yeni sayfa oluşturur."""
        result = self._cell_manipulator.create_sheet(
            args["sheet_name"],
            args.get("position"),
        )
        self._log_change(f"Sayfa oluşturuldu: {args['sheet_name']}", cells=None, undoable=False)
        return result

    def _rename_sheet(self, args: dict):
        """Sayfayı yeniden adlandırır."""
        result = self._cell_manipulator.rename_sheet(
            args["old_name"],
            args["new_name"],
        )
        self._log_change(f"Sayfa yeniden adlandırıldı: {args['old_name']} -> {args['new_name']}", cells=None, undoable=False)
        return result

    def _copy_range(self, args: dict):
        """Aralığı kopyalar."""
        result = self._cell_manipulator.copy_range(
            args["source_range"],
            args["target_cell"],
        )
        self._log_change(f"Kopyalandı: {args['source_range']} -> {args['target_cell']}", cells=None, undoable=False)
        return result

    def _create_chart(self, args: dict):
        """Grafik oluşturur."""
        result = self._cell_manipulator.create_chart(
            args["data_range"],
            args["chart_type"],
            args.get("title"),
            args.get("position"),
            args.get("has_header", True),
        )
        self._log_change(f"Grafik oluşturuldu: {args['chart_type']}", cells=None, undoable=False)
        return result

    def _clear_range(self, args: dict):
        """Aralığı temizler."""
        self._cell_manipulator.clear_range(args["range_name"])
        self._log_change(f"Temizlendi: {args['range_name']}", cells=None, undoable=False)
        return f"{args['range_name']} aralığı temizlendi."
