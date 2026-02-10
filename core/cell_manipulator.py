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
        h_align: str = None,
        v_align: str = None,
        wrap_text: bool = None,
        border_color: int = None,
    ):
        """
        Hücreye stil uygular.

        Args:
            address: Hücre adresi (ör. "A1").
            bold: Kalın yazı (True/False/None).
            italic: Italik yazı (True/False/None).
            bg_color: Arka plan rengi (RGB int).
            font_color: Yazı rengi (RGB int).
            font_size: Yazı boyutu (punto).
            h_align: Yatay hizalama ("left", "center", "right", "justify").
            v_align: Dikey hizalama ("top", "center", "bottom").
            wrap_text: Metni kaydır (True/False).
            border_color: Kenarlık rengi (RGB int).
        """
        try:
            cell = self._get_cell(address)
            self._apply_style_properties(
                cell, bold, italic, bg_color, font_color, font_size,
                h_align, v_align, wrap_text, border_color
            )
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
        h_align: str = None,
        v_align: str = None,
        wrap_text: bool = None,
        border_color: int = None,
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
            h_align: Yatay hizalama ("left", "center", "right", "justify").
            v_align: Dikey hizalama ("top", "center", "bottom").
            wrap_text: Metni kaydır (True/False).
            border_color: Kenarlık rengi (RGB int).
        """
        try:
            sheet = self.bridge.get_active_sheet()
            cell_range = self.bridge.get_cell_range(sheet, range_str)
            self._apply_style_properties(
                cell_range, bold, italic, bg_color, font_color, font_size,
                h_align, v_align, wrap_text, border_color
            )
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

    def _apply_style_properties(
        self, obj, bold, italic, bg_color, font_color, font_size,
        h_align, v_align, wrap_text, border_color
    ):
        """Ortak stil özelliklerini uygular (hücre veya aralık için)."""
        if bold is not None:
            from com.sun.star.awt.FontWeight import BOLD, NORMAL
            obj.setPropertyValue("CharWeight", BOLD if bold else NORMAL)

        if italic is not None:
            from com.sun.star.awt.FontSlant import ITALIC, NONE
            obj.setPropertyValue("CharPosture", ITALIC if italic else NONE)

        if bg_color is not None:
            obj.setPropertyValue("CellBackColor", bg_color)

        if font_color is not None:
            obj.setPropertyValue("CharColor", font_color)

        if font_size is not None:
            obj.setPropertyValue("CharHeight", font_size)

        if h_align is not None:
            from com.sun.star.table.CellHoriJustify import (
                LEFT, CENTER, RIGHT, BLOCK, STANDARD
            )
            align_map = {
                "left": LEFT, "center": CENTER, "right": RIGHT,
                "justify": BLOCK, "standard": STANDARD
            }
            if h_align.lower() in align_map:
                obj.setPropertyValue("HoriJustify", align_map[h_align.lower()])

        if v_align is not None:
            from com.sun.star.table.CellVertJustify import (
                TOP, CENTER, BOTTOM, STANDARD
            )
            align_map = {
                "top": TOP, "center": CENTER, "bottom": BOTTOM,
                "standard": STANDARD
            }
            if v_align.lower() in align_map:
                obj.setPropertyValue("VertJustify", align_map[v_align.lower()])

        if wrap_text is not None:
            obj.setPropertyValue("IsTextWrapped", wrap_text)

        if border_color is not None:
             self._apply_borders(obj, border_color)

    def _apply_borders(self, obj, color: int):
        """Kenarlıkları uygular."""
        from com.sun.star.table import BorderLine
        
        line = BorderLine()
        line.Color = color
        line.OuterLineWidth = 50 # 0.05pt ~ 2, biraz daha kalin yapalim 50 (~1.25mm degil, 1/100mm cinsinden olabilir, hayir BorderLine structinda OuterLineWidth in 1/100mm. 2 cok ince, 25 veya 50 iyi)
        # LibreOffice API: OuterLineWidth is in 1/100 mm. So 50 is 0.5 mm.

        # Tum kenarlara uygula
        obj.setPropertyValue("TopBorder", line)
        obj.setPropertyValue("BottomBorder", line)
        obj.setPropertyValue("LeftBorder", line)
        obj.setPropertyValue("RightBorder", line)
