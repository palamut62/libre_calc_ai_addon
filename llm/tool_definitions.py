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
            "description": "Belirtilen hücreye metin, sayı veya formül yazar. Düz metin için direkt yaz (ör: 'Toplam'), sayı için sayı yaz (ör: '42'), formül için = ile başlat (ör: '=SUM(A1:A10)'). Birden fazla hücreye yazmak için bu aracı tekrar tekrar çağır.",
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
            "description": "Belirtilen hücre veya aralığa stil ve biçimlendirme uygular",
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
            "description": "Belirtilen hücre aralığını birleştirir (merge). Genellikle ana başlıklar için kullanılır.",
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
]


class ToolDispatcher:
    """Araç çağrılarını ilgili core modül metodlarına yönlendirir.

    LLM'den gelen tool_call yanıtlarını alır, araç adına göre
    uygun core modül metodunu çağırır ve sonucu döndürür.
    """

    def __init__(self, cell_inspector, cell_manipulator, sheet_analyzer, error_detector):
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
        }

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
            logger.error("Araç çalıştırma hatası (%s): %s", tool_name, exc)
            return json.dumps(
                {"error": f"Araç çalıştırma hatası: {exc}"}, ensure_ascii=False
            )

    def _read_cell_range(self, args: dict):
        """Hücre aralığını okur."""
        return self._cell_inspector.read_range(args["range_name"])

    def _write_formula(self, args: dict):
        """Hücreye formül veya değer yazar."""
        return self._cell_manipulator.write_formula(args["cell"], args["formula"])

    def _set_cell_style(self, args: dict):
        """Hücre stilini ayarlar."""
        args = dict(args)  # orijinali değiştirme
        range_name = args.pop("range_name")

        # Renk dönüşümü (hex string -> int)
        for color_key in ("bg_color", "font_color", "border_color"):
            if color_key in args and isinstance(args[color_key], str):
                args[color_key] = self._parse_color(args[color_key])

        # Aralık mı tekil hücre mi?
        if ":" in range_name:
            return self._cell_manipulator.set_range_style(range_name, **args)
        else:
            return self._cell_manipulator.set_cell_style(range_name, **args)

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
        sheet_name = args.get("sheet_name")
        return self._sheet_analyzer.get_summary(sheet_name)

    def _detect_and_explain_errors(self, args: dict):
        """Hataları tespit eder ve açıklar."""
        range_name = args.get("range_name")
        return self._error_detector.detect_and_explain(range_name)

    def _merge_cells(self, args: dict):
        """Hücreleri birleştirir."""
        range_name = args.get("range_name")
        center = args.get("center", True)
        self._cell_manipulator.merge_cells(range_name, center)
        return f"{range_name} aralığı birleştirildi."

    def _set_column_width(self, args: dict):
        """Sütun genişliğini ayarlar."""
        return self._cell_manipulator.set_column_width(
            args["col_letter"], args["width_mm"]
        )

    def _set_row_height(self, args: dict):
        """Satır yüksekliğini ayarlar."""
        return self._cell_manipulator.set_row_height(
            args["row_num"], args["height_mm"]
        )

    def _insert_rows(self, args: dict):
        """Satır ekler."""
        return self._cell_manipulator.insert_rows(
            args["row_num"], args.get("count", 1)
        )

    def _insert_columns(self, args: dict):
        """Sütun ekler."""
        return self._cell_manipulator.insert_columns(
            args["col_letter"], args.get("count", 1)
        )

    def _delete_rows(self, args: dict):
        """Satır siler."""
        return self._cell_manipulator.delete_rows(
            args["row_num"], args.get("count", 1)
        )

    def _delete_columns(self, args: dict):
        """Sütun siler."""
        return self._cell_manipulator.delete_columns(
            args["col_letter"], args.get("count", 1)
        )

    def _auto_fit_column(self, args: dict):
        """Sütun genişliğini otomatik ayarlar."""
        return self._cell_manipulator.auto_fit_column(args["col_letter"])

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

