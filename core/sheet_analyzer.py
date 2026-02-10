"""Sayfa analizci - LibreOffice Calc sayfalarının yapısını ve istatistiklerini analiz eder."""

import logging
import math
import re

try:
    from com.sun.star.table.CellContentType import EMPTY, VALUE, TEXT, FORMULA
    UNO_AVAILABLE = True
except ImportError:
    EMPTY, VALUE, TEXT, FORMULA = 0, 1, 2, 3
    UNO_AVAILABLE = False

logger = logging.getLogger(__name__)


class SheetAnalyzer:
    """Çalışma sayfasının yapısını ve verilerini analiz eden sınıf."""

    def __init__(self, bridge):
        """
        SheetAnalyzer başlatıcı.

        Args:
            bridge: LibreOfficeBridge örneği.
        """
        self.bridge = bridge

    def get_sheet_summary(self) -> dict:
        """
        Aktif sayfanın genel özetini döndürür.

        Returns:
            Sayfa özet bilgileri sozlugu:
            - sheet_name: Sayfa adı
            - used_range: Kullanılan aralık (ör. "A1:F100")
            - row_count: Kullanılan satır sayısı
            - col_count: Kullanılan sütun sayısı
            - headers: İlk satırdaki başlıklar listesi
        """
        try:
            sheet = self.bridge.get_active_sheet()
            cursor = sheet.createCursor()
            cursor.gotoStartOfUsedArea(False)
            cursor.gotoEndOfUsedArea(True)

            range_addr = cursor.getRangeAddress()
            start_col = range_addr.StartColumn
            start_row = range_addr.StartRow
            end_col = range_addr.EndColumn
            end_row = range_addr.EndRow

            row_count = end_row - start_row + 1
            col_count = end_col - start_col + 1

            start_col_str = self.bridge._index_to_column(start_col)
            end_col_str = self.bridge._index_to_column(end_col)
            used_range = f"{start_col_str}{start_row + 1}:{end_col_str}{end_row + 1}"

            # İlk satırdaki başlıkları oku
            headers = []
            for col in range(start_col, end_col + 1):
                cell = sheet.getCellByPosition(col, start_row)
                cell_value = cell.getString()
                headers.append(cell_value if cell_value else None)

            return {
                "sheet_name": sheet.getName(),
                "used_range": used_range,
                "row_count": row_count,
                "col_count": col_count,
                "headers": headers,
            }

        except Exception as e:
            logger.error("Sayfa özeti oluşturma hatası: %s", str(e))
            raise

    def detect_data_regions(self) -> list:
        """
        Sayfadaki veri bölgelerini tespit eder.

        Birbirinden bos satır veya sütunlarla ayrılan veri bloklarını bulur.

        Returns:
            Veri bölgelerinin listesi. Her bölge bir sozluk:
            - range: Bölge aralığı (ör. "A1:D10")
            - row_count: Satır sayısı
            - col_count: Sütun sayısı
        """
        try:
            sheet = self.bridge.get_active_sheet()
            cursor = sheet.createCursor()
            cursor.gotoStartOfUsedArea(False)
            cursor.gotoEndOfUsedArea(True)

            range_addr = cursor.getRangeAddress()
            end_col = range_addr.EndColumn
            end_row = range_addr.EndRow

            # Satır bazında doluluğu kontrol et
            row_empty = []
            for row in range(end_row + 1):
                is_empty = True
                for col in range(end_col + 1):
                    cell = sheet.getCellByPosition(col, row)
                    if cell.getType() != EMPTY:
                        is_empty = False
                        break
                row_empty.append(is_empty)

            # Boş satırlara göre bölgeleri ayır
            regions = []
            region_start = None

            for row in range(len(row_empty)):
                if not row_empty[row]:
                    if region_start is None:
                        region_start = row
                elif region_start is not None:
                    # Bölge sonu - bu bölgenin sütun sınırlarını bul
                    region = self._find_region_bounds(
                        sheet, region_start, row - 1, end_col
                    )
                    if region:
                        regions.append(region)
                    region_start = None

            # Son bölge
            if region_start is not None:
                region = self._find_region_bounds(
                    sheet, region_start, end_row, end_col
                )
                if region:
                    regions.append(region)

            return regions

        except Exception as e:
            logger.error("Veri bölgesi tespit hatası: %s", str(e))
            raise

    def _find_region_bounds(
        self, sheet, start_row: int, end_row: int, max_col: int
    ) -> dict:
        """
        Bir veri bölgesinin sütun sınırlarını belirler.

        Args:
            sheet: Çalışma sayfası.
            start_row: Başlangıç satırı.
            end_row: Bitiş satırı.
            max_col: Maksimum sütun indeksi.

        Returns:
            Bölge bilgileri sozlugu veya None.
        """
        min_col = max_col
        actual_max_col = 0

        for row in range(start_row, end_row + 1):
            for col in range(max_col + 1):
                cell = sheet.getCellByPosition(col, row)
                if cell.getType() != EMPTY:
                    min_col = min(min_col, col)
                    actual_max_col = max(actual_max_col, col)

        if actual_max_col < min_col:
            return None

        start_col_str = self.bridge._index_to_column(min_col)
        end_col_str = self.bridge._index_to_column(actual_max_col)

        return {
            "range": f"{start_col_str}{start_row + 1}:{end_col_str}{end_row + 1}",
            "row_count": end_row - start_row + 1,
            "col_count": actual_max_col - min_col + 1,
        }

    def find_empty_cells(self, range_str: str) -> list:
        """
        Belirtilen aralıktaki boş hücreleri bulur.

        Args:
            range_str: Hücre aralığı (ör. "A1:D10").

        Returns:
            Bos hücre adreslerinin listesi.
        """
        try:
            sheet = self.bridge.get_active_sheet()
            start, end = self.bridge.parse_range_string(range_str)

            empty_cells = []
            for row in range(start[1], end[1] + 1):
                for col in range(start[0], end[0] + 1):
                    cell = sheet.getCellByPosition(col, row)
                    if cell.getType() == EMPTY:
                        col_str = self.bridge._index_to_column(col)
                        empty_cells.append(f"{col_str}{row + 1}")

            return empty_cells

        except Exception as e:
            logger.error(
                "Boş hücre arama hatası (%s): %s", range_str, str(e)
            )
            raise

    def get_column_statistics(self, col_letter: str) -> dict:
        """
        Bir sütundaki sayısal verilerin istatistiklerini hesaplar.

        Args:
            col_letter: Sütun harfi (ör. "A", "B").

        Returns:
            Istatistik sozlugu:
            - column: Sütun harfi
            - count: Sayısal değer sayısı
            - sum: Toplam
            - mean: Ortalama
            - min: Minimum
            - max: Maksimum
            - std: Standart sapma
        """
        try:
            sheet = self.bridge.get_active_sheet()
            col_index = self.bridge._column_to_index(col_letter.upper())

            cursor = sheet.createCursor()
            cursor.gotoStartOfUsedArea(False)
            cursor.gotoEndOfUsedArea(True)
            end_row = cursor.getRangeAddress().EndRow

            values = []
            for row in range(end_row + 1):
                cell = sheet.getCellByPosition(col_index, row)
                cell_type = cell.getType()
                if cell_type == VALUE or (
                    cell_type == FORMULA and cell.getValue() != 0
                ):
                    values.append(cell.getValue())
                elif cell_type == FORMULA:
                    # Formül sonucu 0 olabilir, kontrol et
                    try:
                        val = cell.getValue()
                        values.append(val)
                    except Exception:
                        pass

            if not values:
                return {
                    "column": col_letter.upper(),
                    "count": 0,
                    "sum": 0,
                    "mean": 0,
                    "min": None,
                    "max": None,
                    "std": 0,
                }

            count = len(values)
            total = sum(values)
            mean = total / count
            min_val = min(values)
            max_val = max(values)

            # Standart sapma hesaplama
            if count > 1:
                variance = sum((x - mean) ** 2 for x in values) / (count - 1)
                std = math.sqrt(variance)
            else:
                std = 0.0

            return {
                "column": col_letter.upper(),
                "count": count,
                "sum": round(total, 6),
                "mean": round(mean, 6),
                "min": min_val,
                "max": max_val,
                "std": round(std, 6),
            }

        except Exception as e:
            logger.error(
                "Sütun istatistik hatası (%s): %s", col_letter, str(e)
            )
            raise
