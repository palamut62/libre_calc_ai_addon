"""Hücre manipülatörü - LibreOffice Calc hücrelerine veri yazma ve biçimlendirme."""

import logging
import re

logger = logging.getLogger(__name__)


class CellManipulator:
    """Hücrelere veri yazma ve stil uygulama islemlerini yöneten sınıf."""

    def __init__(self, bridge):
        """
        CellManipulator başlatıcı.

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

    def write_value(self, address: str, value):
        """
        Hücreye değer yazar.

        Args:
            address: Hücre adresi (ör. "A1").
            value: Yazılacak değer (str veya sayısal).
        """
        try:
            cell = self._get_cell(address)

            if isinstance(value, (int, float)):
                cell.setValue(value)
            else:
                cell.setString(str(value))

            logger.info("Hücre %s <- %r yazıldı.", address.upper(), value)

        except Exception as e:
            logger.error("Hücre yazma hatası (%s): %s", address, str(e))
            raise

    def write_formula(self, address: str, formula: str):
        """
        Hücreye formül, metin veya sayı yazar.

        '=' ile başlıyorsa formül olarak, sayıya dönüşebiliyorsa sayı olarak,
        aksi halde metin olarak yazar.

        Args:
            address: Hücre adresi (ör. "A1").
            formula: Yazılacak içerik (ör. "=SUM(A1:A10)", "Başlık", "42").

        Returns:
            Yazılan değerin açıklaması.
        """
        try:
            cell = self._get_cell(address)

            if formula.startswith("="):
                # Formül olarak yaz
                cell.setFormula(formula)
                logger.info("Hücre %s <- formül '%s' yazıldı.", address.upper(), formula)
                return f"{address} hücresine formül yazıldı: {formula}"
            else:
                # Sayı mı metin mi kontrol et
                try:
                    num = float(formula)
                    cell.setValue(num)
                    logger.info("Hücre %s <- sayı %s yazıldı.", address.upper(), formula)
                    return f"{address} hücresine sayı yazıldı: {formula}"
                except ValueError:
                    cell.setString(formula)
                    logger.info("Hücre %s <- metin '%s' yazıldı.", address.upper(), formula)
                    return f"{address} hücresine metin yazıldı: {formula}"

        except Exception as e:
            logger.error(
                "Formül yazma hatası (%s): %s", address, str(e)
            )
            raise

    def set_cell_style(
        self,
        address: str,
        bold: bool = None,
        italic: bool = None,
        bg_color: int = None,
        font_color: int = None,
        font_size: float = None,
    ):
        """
        Hücreye stil uygular.

        Args:
            address: Hücre adresi (ör. "A1").
            bold: Kalın yazı (True/False/None).
            italic: Italik yazı (True/False/None).
            bg_color: Arka plan rengi (RGB int, ör. 0xFF0000 kırmızı).
            font_color: Yazı rengi (RGB int).
            font_size: Yazı boyutu (punto).
        """
        try:
            cell = self._get_cell(address)

            if bold is not None:
                from com.sun.star.awt.FontWeight import BOLD, NORMAL
                cell.setPropertyValue(
                    "CharWeight", BOLD if bold else NORMAL
                )

            if italic is not None:
                from com.sun.star.awt.FontSlant import ITALIC, NONE
                cell.setPropertyValue(
                    "CharPosture", ITALIC if italic else NONE
                )

            if bg_color is not None:
                cell.setPropertyValue("CellBackColor", bg_color)

            if font_color is not None:
                cell.setPropertyValue("CharColor", font_color)

            if font_size is not None:
                cell.setPropertyValue("CharHeight", font_size)

            logger.info("Hücre %s stili güncellendi.", address.upper())

        except Exception as e:
            logger.error("Stil uygulama hatası (%s): %s", address, str(e))
            raise

    def set_range_style(
        self,
        range_str: str,
        bold: bool = None,
        italic: bool = None,
        bg_color: int = None,
        font_color: int = None,
        font_size: float = None,
    ):
        """
        Hücre aralığına stil uygular.

        Args:
            range_str: Hücre aralığı (ör. "A1:D10").
            bold: Kalın yazı.
            italic: Italik yazı.
            bg_color: Arka plan rengi.
            font_color: Yazı rengi.
            font_size: Yazı boyutu.
        """
        try:
            sheet = self.bridge.get_active_sheet()
            cell_range = self.bridge.get_cell_range(sheet, range_str)

            if bold is not None:
                from com.sun.star.awt.FontWeight import BOLD, NORMAL
                cell_range.setPropertyValue(
                    "CharWeight", BOLD if bold else NORMAL
                )

            if italic is not None:
                from com.sun.star.awt.FontSlant import ITALIC, NONE
                cell_range.setPropertyValue(
                    "CharPosture", ITALIC if italic else NONE
                )

            if bg_color is not None:
                cell_range.setPropertyValue("CellBackColor", bg_color)

            if font_color is not None:
                cell_range.setPropertyValue("CharColor", font_color)

            if font_size is not None:
                cell_range.setPropertyValue("CharHeight", font_size)

            logger.info("Aralık %s stili güncellendi.", range_str.upper())

        except Exception as e:
            logger.error(
                "Aralık stil uygulama hatası (%s): %s", range_str, str(e)
            )
            raise

    def set_number_format(self, address: str, format_str: str):
        """
        Hücrenin sayı formatını ayarlar.

        Args:
            address: Hücre adresi (ör. "A1").
            format_str: Sayı format dizesi (ör. "#,##0.00", "0%", "dd.MM.yyyy").
        """
        try:
            cell = self._get_cell(address)
            doc = self.bridge.get_active_document()
            formats = doc.getNumberFormats()
            locale = doc.getPropertyValue("CharLocale")

            format_id = formats.queryKey(format_str, locale, False)
            if format_id == -1:
                format_id = formats.addNew(format_str, locale)

            cell.setPropertyValue("NumberFormat", format_id)
            logger.info(
                "Hücre %s sayı formatı '%s' olarak ayarlandı.",
                address.upper(), format_str,
            )

        except Exception as e:
            logger.error(
                "Sayı format ayarlama hatası (%s): %s", address, str(e)
            )
            raise

    def clear_cell(self, address: str):
        """
        Hücre içeriğini temizler.

        Args:
            address: Hücre adresi (ör. "A1").
        """
        try:
            cell = self._get_cell(address)
            cell.setString("")
            logger.info("Hücre %s temizlendi.", address.upper())

        except Exception as e:
            logger.error("Hücre temizleme hatası (%s): %s", address, str(e))
            raise

    def clear_range(self, range_str: str):
        """
        Hücre aralığındaki tüm içerikleri temizler.

        Args:
            range_str: Hücre aralığı (ör. "A1:D10").
        """
        try:
            sheet = self.bridge.get_active_sheet()
            cell_range = self.bridge.get_cell_range(sheet, range_str)
            # CellFlags: VALUE=1, DATETIME=2, STRING=4, ANNOTATION=8,
            # FORMULA=16, HARDATTR=32, STYLES=64
            # 1+2+4+16 = 23 -> değer, tarih, metin ve formülleri temizle
            cell_range.clearContents(23)
            logger.info("Aralık %s temizlendi.", range_str.upper())

        except Exception as e:
            logger.error(
                "Aralık temizleme hatası (%s): %s", range_str, str(e)
            )
            raise
