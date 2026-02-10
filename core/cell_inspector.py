"""Hücre denetleyici - LibreOffice Calc hücrelerinin detaylı bilgilerini okur."""

import logging
import re

try:
    from com.sun.star.table.CellContentType import EMPTY, VALUE, TEXT, FORMULA
    UNO_AVAILABLE = True
except ImportError:
    EMPTY, VALUE, TEXT, FORMULA = 0, 1, 2, 3
    UNO_AVAILABLE = False

logger = logging.getLogger(__name__)


class CellInspector:
    """Hücre içeriklerini ve özelliklerini inceleyen sınıf."""

    def __init__(self, bridge):
        """
        CellInspector başlatıcı.

        Args:
            bridge: LibreOfficeBridge örneği.
        """
        self.bridge = bridge

    @staticmethod
    def _parse_address(address: str) -> tuple:
        """
        Hücre adresini sütun ve satır indekslerine dönüştürür.

        Args:
            address: Hücre adresi (ör. "A1", "AB10").

        Returns:
            (sütun_indeksi, satır_indeksi) tuple (0 tabanlı).

        Raises:
            ValueError: Geçersiz hücre adresi.
        """
        address = address.strip().upper()
        match = re.match(r'^([A-Z]+)(\d+)$', address)
        if not match:
            raise ValueError(f"Geçersiz hücre adresi: '{address}'")

        col_str = match.group(1)
        row_num = int(match.group(2))

        col_index = 0
        for char in col_str:
            col_index = col_index * 26 + (ord(char) - ord('A') + 1)
        col_index -= 1

        row_index = row_num - 1
        return col_index, row_index

    def _get_cell(self, address: str):
        """
        Adrese göre hücre nesnesini döndürür.

        Args:
            address: Hücre adresi (ör. "A1").

        Returns:
            Hücre nesnesi.
        """
        col, row = self._parse_address(address)
        sheet = self.bridge.get_active_sheet()
        return self.bridge.get_cell(sheet, col, row)

    def read_cell(self, address: str) -> dict:
        """
        Hücrenin temel bilgilerini okur.

        Args:
            address: Hücre adresi (ör. "A1").

        Returns:
            Hücre bilgilerini iceren sozluk:
            - address: Hücre adresi
            - value: Hücre değeri
            - formula: Formül (varsa)
            - type: Hücre tipi (empty, value, text, formula)
        """
        try:
            cell = self._get_cell(address)
            cell_type = cell.getType()

            type_map = {
                EMPTY: "empty",
                VALUE: "value",
                TEXT: "text",
                FORMULA: "formula",
            }

            if cell_type == EMPTY:
                value = None
            elif cell_type == VALUE:
                value = cell.getValue()
            elif cell_type == TEXT:
                value = cell.getString()
            elif cell_type == FORMULA:
                value = cell.getValue() if cell.getValue() != 0 else cell.getString()
            else:
                value = cell.getString()

            formula = cell.getFormula() if cell_type == FORMULA else None

            return {
                "address": address.upper(),
                "value": value,
                "formula": formula,
                "type": type_map.get(cell_type, "unknown"),
            }

        except Exception as e:
            logger.error("Hücre okuma hatası (%s): %s", address, str(e))
            raise

    def get_cell_details(self, address: str) -> dict:
        """
        Hücrenin tüm detaylı bilgilerini döndürür.

        Args:
            address: Hücre adresi (ör. "A1").

        Returns:
            Detaylı hücre bilgileri sozlugu:
            - address: Hücre adresi
            - value: Hücre değeri
            - formula: Formül
            - formula_local: Yerel formül
            - type: Hücre tipi
            - background_color: Arka plan rengi (int)
            - number_format: Sayı formatı
        """
        try:
            cell = self._get_cell(address)
            cell_type = cell.getType()

            type_map = {
                EMPTY: "empty",
                VALUE: "value",
                TEXT: "text",
                FORMULA: "formula",
            }

            if cell_type == EMPTY:
                value = None
            elif cell_type == VALUE:
                value = cell.getValue()
            elif cell_type == TEXT:
                value = cell.getString()
            elif cell_type == FORMULA:
                value = cell.getValue() if cell.getValue() != 0 else cell.getString()
            else:
                value = cell.getString()

            return {
                "address": address.upper(),
                "value": value,
                "formula": cell.getFormula(),
                "formula_local": cell.getPropertyValue("FormulaLocal"),
                "type": type_map.get(cell_type, "unknown"),
                "background_color": cell.getPropertyValue("CellBackColor"),
                "number_format": cell.getPropertyValue("NumberFormat"),
            }

        except Exception as e:
            logger.error("Hücre detay okuma hatası (%s): %s", address, str(e))
            raise

    def get_cell_precedents(self, address: str) -> list:
        """
        Hücrenin bağımlı olduğu hücreleri (öncülleri) döndürür.

        Bir hücrenin formülünde referans verilen diğer hücreleri bulur.

        Args:
            address: Hücre adresi (ör. "B2").

        Returns:
            Öncül hücre adreslerinin listesi.
        """
        try:
            cell = self._get_cell(address)
            formula = cell.getFormula()

            if not formula:
                return []

            # Formüldeki hücre referanslarını bul
            references = re.findall(
                r'\$?([A-Z]+)\$?(\d+)', formula.upper()
            )

            precedents = []
            for col_str, row_str in references:
                ref_address = f"{col_str}{row_str}"
                if ref_address not in precedents:
                    precedents.append(ref_address)

            return precedents

        except Exception as e:
            logger.error(
                "Öncül hücre tespit hatası (%s): %s", address, str(e)
            )
            raise

    def get_cell_dependents(self, address: str) -> list:
        """
        Bu hücreye bağımlı olan hücreleri (ardılları) döndürür.

        Aktif sayfadaki kullanılan aralıktaki formülleri tarayarak
        bu hücreye referans veren hücreleri bulur.

        Args:
            address: Hücre adresi (ör. "A1").

        Returns:
            Ardıl hücre adreslerinin listesi.
        """
        try:
            sheet = self.bridge.get_active_sheet()
            target = address.strip().upper()

            # Sayfanın kullanılan alanını belirle
            cursor = sheet.createCursor()
            cursor.gotoStartOfUsedArea(False)
            cursor.gotoEndOfUsedArea(True)

            end_col = cursor.getRangeAddress().EndColumn
            end_row = cursor.getRangeAddress().EndRow

            dependents = []

            for row in range(end_row + 1):
                for col in range(end_col + 1):
                    cell = sheet.getCellByPosition(col, row)
                    if cell.getType() == FORMULA:
                        formula = cell.getFormula().upper()
                        # Hedef hücreye referans var mi kontrol et
                        # Dolar isareti olabilir: $A$1, A$1, $A1, A1
                        col_str = re.match(r'^([A-Z]+)', target).group(1)
                        row_str = re.match(r'^[A-Z]+(\d+)$', target).group(1)
                        pattern = rf'\$?{re.escape(col_str)}\$?{re.escape(row_str)}(?![0-9A-Z])'
                        if re.search(pattern, formula):
                            dep_col = self.bridge._index_to_column(col)
                            dep_address = f"{dep_col}{row + 1}"
                            dependents.append(dep_address)

            return dependents

        except Exception as e:
            logger.error(
                "Ardıl hücre tespit hatası (%s): %s", address, str(e)
            )
            raise
