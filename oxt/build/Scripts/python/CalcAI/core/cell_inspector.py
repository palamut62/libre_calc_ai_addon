"""Hücre denetleyici - LibreOffice Calc hücrelerinin detaylı bilgilerini okur."""

import logging

from .address_utils import parse_address

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
    def _cell_type_name(cell_type) -> str:
        """UNO Enum uyumlu hücre tipi ismi döndürür."""
        if cell_type == EMPTY:
            return "empty"
        if cell_type == VALUE:
            return "value"
        if cell_type == TEXT:
            return "text"
        if cell_type == FORMULA:
            return "formula"
        return "unknown"

    @staticmethod
    def _safe_prop(cell, name, default=None):
        try:
            return cell.getPropertyValue(name)
        except Exception:
            return default

    def _get_cell(self, address: str):
        """
        Adrese göre hücre nesnesini döndürür.

        Args:
            address: Hücre adresi (ör. "A1").

        Returns:
            Hücre nesnesi.
        """
        col, row = parse_address(address)
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
                "type": self._cell_type_name(cell_type),
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
                "formula_local": self._safe_prop(cell, "FormulaLocal"),
                "type": self._cell_type_name(cell_type),
                "background_color": self._safe_prop(cell, "CellBackColor"),
                "number_format": self._safe_prop(cell, "NumberFormat"),
                "font_color": self._safe_prop(cell, "CharColor"),
                "font_size": self._safe_prop(cell, "CharHeight"),
                "bold": self._safe_prop(cell, "CharWeight"),
                "italic": self._safe_prop(cell, "CharPosture"),
                "h_align": self._safe_prop(cell, "HoriJustify"),
                "v_align": self._safe_prop(cell, "VertJustify"),
                "wrap_text": self._safe_prop(cell, "IsTextWrapped"),
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

    def read_range(self, range_name: str) -> list[list[dict]]:
        """
        Hücre aralığındaki değerleri ve formülleri okur.

        Args:
            range_name: Hücre aralığı (ör. "A1:D10", "B2").

        Returns:
            2D liste: Her hücre için {address, value, formula, type} içeren dict.
        """
        try:
            sheet = self.bridge.get_active_sheet()

            # Tek hücre mi kontrol et
            if ":" not in range_name:
                cell_info = self.read_cell(range_name)
                return [[cell_info]]

            cell_range = self.bridge.get_cell_range(sheet, range_name)
            addr = cell_range.getRangeAddress()

            result = []
            for row in range(addr.StartRow, addr.EndRow + 1):
                row_data = []
                for col in range(addr.StartColumn, addr.EndColumn + 1):
                    cell = sheet.getCellByPosition(col, row)
                    cell_type = cell.getType()

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

                    col_letter = self.bridge._index_to_column(col)
                    address = f"{col_letter}{row + 1}"
                    formula = cell.getFormula() if cell_type == FORMULA else None

                    row_data.append({
                        "address": address,
                        "value": value,
                        "formula": formula,
                        "type": self._cell_type_name(cell_type),
                    })
                result.append(row_data)

            return result

        except Exception as e:
            logger.error("Aralık okuma hatası (%s): %s", range_name, str(e))
            raise

    def get_all_formulas(self, sheet_name: str = None) -> list[dict]:
        """
        Sayfadaki tüm formülleri listeler.

        Args:
            sheet_name: Sayfa adı (None ise aktif sayfa).

        Returns:
            Formül listesi: [{address, formula, value, precedents}, ...]
        """
        try:
            if sheet_name:
                doc = self.bridge.get_active_document()
                sheets = doc.getSheets()
                sheet = sheets.getByName(sheet_name)
            else:
                sheet = self.bridge.get_active_sheet()

            # Kullanılan alanı bul
            cursor = sheet.createCursor()
            cursor.gotoStartOfUsedArea(False)
            cursor.gotoEndOfUsedArea(True)

            addr = cursor.getRangeAddress()
            formulas = []

            for row in range(addr.StartRow, addr.EndRow + 1):
                for col in range(addr.StartColumn, addr.EndColumn + 1):
                    cell = sheet.getCellByPosition(col, row)
                    if cell.getType() == FORMULA:
                        col_letter = self.bridge._index_to_column(col)
                        address = f"{col_letter}{row + 1}"
                        formula = cell.getFormula()
                        value = cell.getValue() if cell.getValue() != 0 else cell.getString()

                        # Referans edilen hücreleri bul
                        refs = re.findall(r'\$?([A-Z]+)\$?(\d+)', formula.upper())
                        precedents = [f"{c}{r}" for c, r in refs]

                        formulas.append({
                            "address": address,
                            "formula": formula,
                            "value": value,
                            "precedents": precedents,
                        })

            return formulas

        except Exception as e:
            logger.error("Formül listeleme hatası: %s", str(e))
            raise

    def analyze_spreadsheet_structure(self, sheet_name: str = None) -> dict:
        """
        Tablonun yapısını ve formül ağını analiz eder.

        Args:
            sheet_name: Sayfa adı (None ise aktif sayfa).

        Returns:
            Yapı analizi: {
                input_cells: Veri girişi yapılan hücreler (formülsüz),
                output_cells: Sonuç hücreleri (formüllü ama başka formül tarafından kullanılmayan),
                intermediate_cells: Ara hesaplama hücreleri,
                formula_chain: Formül zinciri (bağımlılık sırası),
                data_ranges: Veri aralıkları (başlık + veri grupları),
            }
        """
        try:
            formulas = self.get_all_formulas(sheet_name)

            if not formulas:
                return {
                    "input_cells": [],
                    "output_cells": [],
                    "intermediate_cells": [],
                    "formula_chain": [],
                    "summary": "Bu sayfada formül bulunamadı."
                }

            # Tüm formül hücrelerini ve referanslarını topla
            formula_cells = {f["address"] for f in formulas}
            all_precedents = set()
            for f in formulas:
                all_precedents.update(f["precedents"])

            # Giriş hücreleri: Formül tarafından referans edilen ama formül içermeyen
            input_cells = list(all_precedents - formula_cells)

            # Çıkış hücreleri: Formül içeren ama başka formül tarafından referans edilmeyen
            referenced_formulas = set()
            for f in formulas:
                for p in f["precedents"]:
                    if p in formula_cells:
                        referenced_formulas.add(p)

            output_cells = [f["address"] for f in formulas if f["address"] not in referenced_formulas]

            # Ara hesaplama hücreleri
            intermediate_cells = list(formula_cells - set(output_cells))

            # Formül zincirini oluştur (basit topolojik sıralama)
            formula_chain = []
            for f in formulas:
                formula_chain.append({
                    "cell": f["address"],
                    "formula": f["formula"],
                    "depends_on": f["precedents"],
                })

            return {
                "input_cells": sorted(input_cells),
                "output_cells": sorted(output_cells),
                "intermediate_cells": sorted(intermediate_cells),
                "formula_chain": formula_chain,
                "summary": f"Analiz: {len(input_cells)} giriş, {len(intermediate_cells)} ara hesap, {len(output_cells)} çıkış hücresi."
            }

        except Exception as e:
            logger.error("Yapı analizi hatası: %s", str(e))
            raise
