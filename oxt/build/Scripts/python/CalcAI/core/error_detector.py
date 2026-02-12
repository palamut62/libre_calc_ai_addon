"""Hata tespit modülü - LibreOffice Calc hücrelerindeki formül hatalarını bulur ve açıklar."""

import logging
import re

from .address_utils import parse_address

try:
    from com.sun.star.table.CellContentType import EMPTY, VALUE, TEXT, FORMULA
    UNO_AVAILABLE = True
except ImportError:
    EMPTY, VALUE, TEXT, FORMULA = 0, 1, 2, 3
    UNO_AVAILABLE = False

logger = logging.getLogger(__name__)

# LibreOffice Calc hata türleri ve açıklamaları
ERROR_TYPES = {
    501: {
        "code": "#NULL!",
        "name": "Geçersiz karakter",
        "description": "Formülde geçersiz bir karakter bulundu.",
    },
    502: {
        "code": "#NULL!",
        "name": "Geçersiz argüman",
        "description": "Fonksiyon argümanı geçersiz.",
    },
    504: {
        "code": "#NAME?",
        "name": "Ad hatası",
        "description": "Tanınmayan bir fonksiyon veya alan adı kullanıldı. "
                       "Fonksiyon adının doğru yazıldığından emin olun.",
    },
    507: {
        "code": "#NULL!",
        "name": "Parantez eksik",
        "description": "Formülde kapanmamış bir parantez var.",
    },
    508: {
        "code": "#NULL!",
        "name": "Parantez hatası",
        "description": "Formülde fazladan veya eksik parantez bulundu.",
    },
    510: {
        "code": "#NULL!",
        "name": "Operatör eksik",
        "description": "Formülde beklenen bir operatör eksik.",
    },
    511: {
        "code": "#NULL!",
        "name": "Değişken eksik",
        "description": "Formülde beklenen bir değişken eksik.",
    },
    519: {
        "code": "#VALUE!",
        "name": "Değer hatası",
        "description": "Formüldeki bir değer beklenen türde değil. "
                       "Metin yerine sayı veya sayı yerine metin kullanılmış olabilir.",
    },
    521: {
        "code": "#NULL!",
        "name": "Iç hata",
        "description": "Dahili hesaplama hatası oluştu.",
    },
    522: {
        "code": "#REF!",
        "name": "Dairesel referans",
        "description": "Formül doğrudan veya dolaylı olarak kendisine referans veriyor.",
    },
    524: {
        "code": "#REF!",
        "name": "Referans hatası",
        "description": "Formüldeki bir hücre referansı geçersiz. "
                       "Silinen bir hücre veya sayfa referansı olabilir.",
    },
    525: {
        "code": "#NAME?",
        "name": "Ad hatası",
        "description": "Geçersiz bir ad veya tanımsız bir tanımlayıcı kullanıldı.",
    },
    532: {
        "code": "#DIV/0!",
        "name": "Sıfıra bölme",
        "description": "Bir sayı sıfıra bölünmeye çalışıldı. "
                       "Bölen hücrenin değerini kontrol edin.",
    },
    533: {
        "code": "#NULL!",
        "name": "Kesisim hatası",
        "description": "İki aralığın kesişimi boş.",
    },
}

# Hücre hata metin kalıpları
ERROR_PATTERNS = [
    "#REF!", "#NAME?", "#VALUE!", "#DIV/0!", "#NULL!",
    "#N/A", "#NUM!", "Err:502", "Err:504", "Err:519",
    "Err:522", "Err:524", "Err:525", "Err:532",
]


class ErrorDetector:
    """Çalışma sayfasındaki formül hatalarını tespit eden ve açıklayan sınıf."""

    def __init__(self, bridge, inspector):
        """
        ErrorDetector başlatıcı.

        Args:
            bridge: LibreOfficeBridge örneği.
            inspector: CellInspector örneği.
        """
        self.bridge = bridge
        self.inspector = inspector

    @staticmethod
    def get_error_type(cell) -> dict:
        """
        Hücrenin hata türünü belirler.

        Args:
            cell: LibreOffice hücre nesnesi.

        Returns:
            Hata bilgileri sozlugu veya bos sozluk (hata yoksa).
        """
        try:
            error_code = cell.getError()
            if error_code == 0:
                return {}

            if error_code in ERROR_TYPES:
                return ERROR_TYPES[error_code].copy()

            return {
                "code": f"Err:{error_code}",
                "name": "Bilinmeyen hata",
                "description": f"Bilinmeyen hata kodu: {error_code}",
            }

        except Exception:
            # getError desteklenmeyebilir, metin kontrolü yap
            try:
                text = cell.getString()
                for pattern in ERROR_PATTERNS:
                    if pattern in text:
                        return {
                            "code": pattern,
                            "name": "Formül hatası",
                            "description": f"Hücrede '{pattern}' hatası tespit edildi.",
                        }
            except Exception:
                pass
            return {}

    def detect_errors(self, range_str: str = None) -> list:
        """
        Belirtilen aralıkta veya tüm sayfada hataları tespit eder.

        Args:
            range_str: Hücre aralığı (ör. "A1:D10"). None ise tüm sayfa taranır.

        Returns:
            Hata bilgilerinin listesi. Her eleman bir sozluk:
            - address: Hücre adresi
            - formula: Hücredeki formül
            - error: Hata bilgileri sozlugu
        """
        try:
            sheet = self.bridge.get_active_sheet()

            if range_str:
                start, end = self.bridge.parse_range_string(range_str)
                start_col, start_row = start
                end_col, end_row = end
            else:
                cursor = sheet.createCursor()
                cursor.gotoStartOfUsedArea(False)
                cursor.gotoEndOfUsedArea(True)
                range_addr = cursor.getRangeAddress()
                start_col = range_addr.StartColumn
                start_row = range_addr.StartRow
                end_col = range_addr.EndColumn
                end_row = range_addr.EndRow

            errors = []

            for row in range(start_row, end_row + 1):
                for col in range(start_col, end_col + 1):
                    cell = sheet.getCellByPosition(col, row)

                    # Sadece formül hücrelerini kontrol et
                    if cell.getType() != FORMULA:
                        continue

                    error_info = self.get_error_type(cell)
                    if error_info:
                        col_str = self.bridge._index_to_column(col)
                        address = f"{col_str}{row + 1}"
                        errors.append({
                            "address": address,
                            "formula": cell.getFormula(),
                            "error": error_info,
                        })

            logger.info(
                "%d hata tespit edildi (aralık: %s).",
                len(errors), range_str or "tüm sayfa",
            )
            return errors

        except Exception as e:
            logger.error("Hata tespit hatası: %s", str(e))
            raise

    def explain_error(self, address: str) -> dict:
        """
        Belirtilen hücredeki hatayı detaylı olarak açıklar.

        Hata türünü, formülü, bağımlı hücreleri ve olası çözüm
        önerilerini içeren detaylı bir rapor döndürür.

        Args:
            address: Hücre adresi (ör. "A1").

        Returns:
            Detaylı hata açıklama sozlugu:
            - address: Hücre adresi
            - formula: Hücredeki formül
            - error: Hata bilgileri
            - precedents: Bağımlı olunan hücreler ve değerleri
            - suggestion: Çözüm önerisi
        """
        try:
            cell_details = self.inspector.get_cell_details(address)
            precedents = self.inspector.get_cell_precedents(address)

            # Hücreyi al ve hata türünü belirle
            col, row = parse_address(address)
            sheet = self.bridge.get_active_sheet()
            cell = sheet.getCellByPosition(col, row)
            error_info = self.get_error_type(cell)

            if not error_info:
                return {
                    "address": address.upper(),
                    "formula": cell_details.get("formula", ""),
                    "error": None,
                    "precedents": [],
                    "suggestion": "Bu hücrede herhangi bir hata tespit edilmedi.",
                }

            # Öncül hücrelerin değerlerini topla
            precedent_details = []
            for prec_addr in precedents:
                try:
                    prec_info = self.inspector.read_cell(prec_addr)
                    precedent_details.append(prec_info)
                except Exception:
                    precedent_details.append({
                        "address": prec_addr,
                        "value": "OKUNAMADI",
                        "type": "unknown",
                    })

            # Çözüm önerisi oluştur
            suggestion = self._generate_suggestion(error_info, precedent_details)

            return {
                "address": address.upper(),
                "formula": cell_details.get("formula", ""),
                "error": error_info,
                "precedents": precedent_details,
                "suggestion": suggestion,
            }

        except Exception as e:
            logger.error(
                "Hata açıklama hatası (%s): %s", address, str(e)
            )
            raise

    def detect_and_explain(self, range_str: str = None) -> dict:
        """Aralıktaki formül hatalarını tespit edip açıklamalarla döndürür."""
        errors = self.detect_errors(range_str)
        detailed = []

        for item in errors:
            address = item.get("address")
            if not address:
                continue
            try:
                detailed.append(self.explain_error(address))
            except Exception:
                # Tek bir hücrede açıklama alınamazsa temel bilgiyle devam et
                detailed.append(
                    {
                        "address": address,
                        "formula": item.get("formula", ""),
                        "error": item.get("error"),
                        "precedents": [],
                        "suggestion": "Hata açıklandıramadı; temel hata bilgisi gösterildi.",
                    }
                )

        return {
            "range": range_str or "used_area",
            "error_count": len(detailed),
            "errors": detailed,
        }

    @staticmethod
    def _generate_suggestion(error_info: dict, precedents: list) -> str:
        """
        Hata türüne ve bağımlı hücrelere göre çözüm önerisi oluşturur.

        Args:
            error_info: Hata bilgileri sozlugu.
            precedents: Öncül hücre bilgileri listesi.

        Returns:
            Çözüm önerisi metni.
        """
        code = error_info.get("code", "")

        if code == "#DIV/0!":
            # Sıfır değerli hücreleri bul
            zero_cells = [
                p["address"] for p in precedents
                if p.get("value") == 0 or p.get("value") is None
            ]
            if zero_cells:
                return (
                    f"Sıfıra bölme hatası. Şu hücreler sıfır veya boş: "
                    f"{', '.join(zero_cells)}. "
                    f"IF fonksiyonu ile sıfır kontrolü eklemeyi deneyin: "
                    f"=IF(bölen<>0, pay/bölen, 0)"
                )
            return (
                "Sıfıra bölme hatası. Bölen değerinin sıfır olmadığından "
                "emin olun veya IF fonksiyonu ile kontrol ekleyin."
            )

        if code == "#REF!":
            return (
                "Geçersiz hücre referansı. Silinen hücre, satır veya sütun "
                "nedeniyle referans bozulmuş olabilir. Formülü kontrol edip "
                "referansları güncelleyin."
            )

        if code == "#NAME?":
            return (
                "Tanınmayan ad hatası. Formüldeki fonksiyon adının doğru "
                "yazıldığından ve tanımlı alan adlarının mevcut olduğundan "
                "emin olun."
            )

        if code == "#VALUE!":
            text_cells = [
                p["address"] for p in precedents
                if p.get("type") == "text"
            ]
            if text_cells:
                return (
                    f"Değer türü hatası. Şu hücrelerde sayı yerine metin var: "
                    f"{', '.join(text_cells)}. "
                    f"VALUE() fonksiyonu ile metin-sayı dönüşümü yapabilirsiniz."
                )
            return (
                "Değer türü hatası. Formülde beklenen türde olmayan bir "
                "değer kullanılmış. Hücre değerlerinin türlerini kontrol edin."
            )

        if code == "#N/A":
            return (
                "Değer bulunamadı hatası. VLOOKUP veya benzeri arama "
                "fonksiyonunda aranan değer bulunamadı. IFERROR ile "
                "varsayılan değer belirleyebilirsiniz."
            )

        return error_info.get("description", "Bilinmeyen hata. Formülü kontrol edin.")
