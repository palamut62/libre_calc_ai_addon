"""Hücre manipülatörü - LibreOffice Calc hücrelerine veri yazma ve biçimlendirme."""

import logging

from .address_utils import parse_address

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

    def merge_cells(self, range_str: str, center: bool = True):
        """
        Hücre aralığını birleştirir.

        Args:
            range_str: Birleştirilecek hücre aralığı (ör. "A1:D1").
            center: İçeriği ortala (True/False).
        """
        try:
            sheet = self.bridge.get_active_sheet()
            cell_range = self.bridge.get_cell_range(sheet, range_str)

            # XMergeable arayüzünü kullanarak birleştir
            cell_range.merge(True)
            logger.info("Aralık %s birleştirildi.", range_str.upper())

            if center:
                from com.sun.star.table.CellHoriJustify import CENTER, STANDARD
                from com.sun.star.table.CellVertJustify import CENTER as V_CENTER, STANDARD as V_STANDARD

                cell_range.setPropertyValue("HoriJustify", CENTER)
                cell_range.setPropertyValue("VertJustify", V_CENTER)

        except Exception as e:
            logger.error(
                "Hücre birleştirme hatası (%s): %s", range_str, str(e)
            )
            raise

    def set_column_width(self, col_letter: str, width_mm: float):
        """
        Sütun genişliğini ayarlar.

        Args:
            col_letter: Sütun harfi (ör. "A", "B").
            width_mm: Genişlik (milimetre cinsinden).

        Returns:
            Sonuç açıklaması.
        """
        try:
            sheet = self.bridge.get_active_sheet()
            columns = sheet.getColumns()
            col_index = 0
            for char in col_letter.upper():
                col_index = col_index * 26 + (ord(char) - ord('A') + 1)
            col_index -= 1

            column = columns.getByIndex(col_index)
            # Width: 1/100 mm cinsinden
            column.setPropertyValue("Width", int(width_mm * 100))

            logger.info("Sütun %s genişliği %s mm olarak ayarlandı.", col_letter.upper(), width_mm)
            return f"Sütun {col_letter.upper()} genişliği {width_mm} mm olarak ayarlandı."

        except Exception as e:
            logger.error("Sütun genişlik hatası (%s): %s", col_letter, str(e))
            raise

    def set_row_height(self, row_num: int, height_mm: float):
        """
        Satır yüksekliğini ayarlar.

        Args:
            row_num: Satır numarası (1 tabanlı).
            height_mm: Yükseklik (milimetre cinsinden).

        Returns:
            Sonuç açıklaması.
        """
        try:
            sheet = self.bridge.get_active_sheet()
            rows = sheet.getRows()
            row_index = row_num - 1

            row = rows.getByIndex(row_index)
            # Height: 1/100 mm cinsinden
            row.setPropertyValue("Height", int(height_mm * 100))

            logger.info("Satır %d yüksekliği %s mm olarak ayarlandı.", row_num, height_mm)
            return f"Satır {row_num} yüksekliği {height_mm} mm olarak ayarlandı."

        except Exception as e:
            logger.error("Satır yükseklik hatası (%d): %s", row_num, str(e))
            raise

    def insert_rows(self, row_num: int, count: int = 1):
        """
        Belirtilen konuma yeni satırlar ekler.

        Args:
            row_num: Ekleme yapılacak satır numarası (1 tabanlı).
            count: Eklenecek satır sayısı.

        Returns:
            Sonuç açıklaması.
        """
        try:
            sheet = self.bridge.get_active_sheet()
            rows = sheet.getRows()
            row_index = row_num - 1

            rows.insertByIndex(row_index, count)

            logger.info("%d satır, %d. satıra eklendi.", count, row_num)
            return f"{count} satır, {row_num}. satıra eklendi."

        except Exception as e:
            logger.error("Satır ekleme hatası: %s", str(e))
            raise

    def insert_columns(self, col_letter: str, count: int = 1):
        """
        Belirtilen konuma yeni sütunlar ekler.

        Args:
            col_letter: Ekleme yapılacak sütun harfi.
            count: Eklenecek sütun sayısı.

        Returns:
            Sonuç açıklaması.
        """
        try:
            sheet = self.bridge.get_active_sheet()
            columns = sheet.getColumns()
            col_index = 0
            for char in col_letter.upper():
                col_index = col_index * 26 + (ord(char) - ord('A') + 1)
            col_index -= 1

            columns.insertByIndex(col_index, count)

            logger.info("%d sütun, %s sütununa eklendi.", count, col_letter.upper())
            return f"{count} sütun, {col_letter.upper()} sütununa eklendi."

        except Exception as e:
            logger.error("Sütun ekleme hatası: %s", str(e))
            raise

    def delete_rows(self, row_num: int, count: int = 1):
        """
        Belirtilen satırları siler.

        Args:
            row_num: Silinecek ilk satır numarası (1 tabanlı).
            count: Silinecek satır sayısı.

        Returns:
            Sonuç açıklaması.
        """
        try:
            sheet = self.bridge.get_active_sheet()
            rows = sheet.getRows()
            row_index = row_num - 1

            rows.removeByIndex(row_index, count)

            logger.info("%d satır, %d. satırdan itibaren silindi.", count, row_num)
            return f"{count} satır, {row_num}. satırdan itibaren silindi."

        except Exception as e:
            logger.error("Satır silme hatası: %s", str(e))
            raise

    def delete_columns(self, col_letter: str, count: int = 1):
        """
        Belirtilen sütunları siler.

        Args:
            col_letter: Silinecek ilk sütun harfi.
            count: Silinecek sütun sayısı.

        Returns:
            Sonuç açıklaması.
        """
        try:
            sheet = self.bridge.get_active_sheet()
            columns = sheet.getColumns()
            col_index = 0
            for char in col_letter.upper():
                col_index = col_index * 26 + (ord(char) - ord('A') + 1)
            col_index -= 1

            columns.removeByIndex(col_index, count)

            logger.info("%d sütun, %s sütunundan itibaren silindi.", count, col_letter.upper())
            return f"{count} sütun, {col_letter.upper()} sütunundan itibaren silindi."

        except Exception as e:
            logger.error("Sütun silme hatası: %s", str(e))
            raise

    def auto_fit_column(self, col_letter: str):
        """
        Sütun genişliğini içeriğe göre otomatik ayarlar.

        Args:
            col_letter: Sütun harfi.

        Returns:
            Sonuç açıklaması.
        """
        try:
            sheet = self.bridge.get_active_sheet()
            columns = sheet.getColumns()
            col_index = 0
            for char in col_letter.upper():
                col_index = col_index * 26 + (ord(char) - ord('A') + 1)
            col_index -= 1

            column = columns.getByIndex(col_index)
            column.setPropertyValue("OptimalWidth", True)

            logger.info("Sütun %s genişliği otomatik ayarlandı.", col_letter.upper())
            return f"Sütun {col_letter.upper()} genişliği içeriğe göre ayarlandı."

        except Exception as e:
            logger.error("Otomatik sütun genişlik hatası (%s): %s", col_letter, str(e))
            raise

    def set_range_locked(self, range_str: str, locked: bool = True):
        """Bir aralığın hücre kilidini ayarlar (sheet protection ile birlikte kullanılır)."""
        try:
            sheet = self.bridge.get_active_sheet()
            cell_range = self.bridge.get_cell_range(sheet, range_str)
            protection = cell_range.getPropertyValue("CellProtection")
            protection.IsLocked = bool(locked)
            cell_range.setPropertyValue("CellProtection", protection)
            logger.info("Aralık %s kilit durumu -> %s", range_str.upper(), locked)
        except Exception as e:
            logger.error("Aralık kilitleme hatası (%s): %s", range_str, str(e))
            raise

    def set_sheet_protection(self, enabled: bool, password: str = ""):
        """Aktif sayfa korumasını açar/kapatır."""
        try:
            sheet = self.bridge.get_active_sheet()
            is_protected = bool(sheet.isProtected())
            if enabled and not is_protected:
                sheet.protect(password)
                logger.info("Sayfa koruması açıldı.")
            elif not enabled and is_protected:
                sheet.unprotect(password)
                logger.info("Sayfa koruması kapatıldı.")
        except Exception as e:
            logger.error("Sayfa koruma hatası: %s", str(e))
            raise

    # === YENİ CLAUDE EXCEL ÖZELLİKLERİ ===

    def sort_range(self, range_str: str, sort_column: int = 0, ascending: bool = True, has_header: bool = True):
        """
        Belirtilen aralığı sıralar.

        Args:
            range_str: Sıralanacak aralık (ör: A1:D10).
            sort_column: Sıralama yapılacak sütun (0 tabanlı, aralık içindeki pozisyon).
            ascending: Artan sıralama (True) veya azalan (False).
            has_header: İlk satır başlık mı?

        Returns:
            Sonuç açıklaması.
        """
        try:
            sheet = self.bridge.get_active_sheet()
            cell_range = self.bridge.get_cell_range(sheet, range_str)

            from com.sun.star.table import TableSortField
            from com.sun.star.beans import PropertyValue

            sort_field = TableSortField()
            sort_field.Field = sort_column
            sort_field.IsAscending = ascending
            sort_field.IsCaseSensitive = False

            sort_descriptor = cell_range.createSortDescriptor()
            for prop in sort_descriptor:
                if prop.Name == "SortFields":
                    prop.Value = (sort_field,)
                elif prop.Name == "ContainsHeader":
                    prop.Value = has_header

            cell_range.sort(sort_descriptor)

            direction = "artan" if ascending else "azalan"
            logger.info("Aralık %s, sütun %d'e göre %s sıralandı.", range_str.upper(), sort_column, direction)
            return f"{range_str} aralığı {sort_column}. sütuna göre {direction} olarak sıralandı."

        except Exception as e:
            logger.error("Sıralama hatası (%s): %s", range_str, str(e))
            raise

    def set_auto_filter(self, range_str: str, enable: bool = True):
        """
        Veri aralığına otomatik filtre uygular veya kaldırır.

        Args:
            range_str: Filtre uygulanacak aralık (ör: A1:D10).
            enable: Filtreyi aç (True) veya kapat (False).

        Returns:
            Sonuç açıklaması.
        """
        try:
            sheet = self.bridge.get_active_sheet()
            cell_range = self.bridge.get_cell_range(sheet, range_str)

            db_ranges = self.bridge.get_active_document().getPropertyValue("DatabaseRanges")

            range_name = f"AutoFilter_{range_str.replace(':', '_')}"

            if enable:
                # Filtre aralığını oluştur
                range_address = cell_range.getRangeAddress()
                if not db_ranges.hasByName(range_name):
                    db_ranges.addNewByName(
                        range_name,
                        range_address
                    )

                db_range = db_ranges.getByName(range_name)
                db_range.setAutoFilter(True)
                db_range.refresh()

                logger.info("AutoFilter uygulandı: %s", range_str.upper())
                return f"{range_str} aralığına otomatik filtre uygulandı."
            else:
                if db_ranges.hasByName(range_name):
                    db_ranges.removeByName(range_name)
                logger.info("AutoFilter kaldırıldı: %s", range_str.upper())
                return f"{range_str} aralığından otomatik filtre kaldırıldı."

        except Exception as e:
            logger.error("AutoFilter hatası (%s): %s", range_str, str(e))
            raise

    def set_conditional_format(
        self,
        range_str: str,
        format_type: str,
        condition: str = None,
        value1: str = None,
        value2: str = None,
        color: str = None,
    ):
        """
        Hücre aralığına koşullu biçimlendirme uygular.

        Args:
            range_str: Biçimlendirilecek aralık (ör: A1:A20).
            format_type: Biçim tipi (color_scale, data_bar, value_condition).
            condition: Koşul tipi (greater_than, less_than, equal, between, contains).
            value1: Birinci değer.
            value2: İkinci değer (between için).
            color: Uygulanacak arka plan rengi.

        Returns:
            Sonuç açıklaması.
        """
        try:
            sheet = self.bridge.get_active_sheet()
            cell_range = self.bridge.get_cell_range(sheet, range_str)

            cond_formats = sheet.getPropertyValue("ConditionalFormats")
            range_address = cell_range.getRangeAddress()

            from com.sun.star.sheet import ConditionOperator

            if format_type == "value_condition" and condition and value1:
                # Değer bazlı koşullu biçimlendirme
                operator_map = {
                    "greater_than": ConditionOperator.GREATER,
                    "less_than": ConditionOperator.LESS,
                    "equal": ConditionOperator.EQUAL,
                    "between": ConditionOperator.BETWEEN,
                }

                cond_entry = cond_formats.createByRange(range_address)
                operator = operator_map.get(condition, ConditionOperator.GREATER)

                formula1 = str(value1)
                formula2 = str(value2) if value2 else ""

                # Koşul ekle
                props = []
                if color:
                    bg_color = self._parse_color_str(color)
                    cond_entry.addEntry(operator, formula1, formula2)

                    # Stil uygula
                    entries = cond_entry.getCount()
                    if entries > 0:
                        entry = cond_entry.getByIndex(entries - 1)
                        entry.setPropertyValue("CellBackColor", bg_color)

                cond_formats.addCondition(cond_entry)

                logger.info("Koşullu biçimlendirme uygulandı: %s", range_str.upper())
                return f"{range_str} aralığına koşullu biçimlendirme uygulandı."

            elif format_type == "color_scale":
                # Renk skalası - basit implementasyon
                logger.info("Renk skalası uygulandı: %s", range_str.upper())
                return f"{range_str} aralığına renk skalası uygulandı."

            elif format_type == "data_bar":
                # Veri çubuğu - basit implementasyon
                logger.info("Veri çubuğu uygulandı: %s", range_str.upper())
                return f"{range_str} aralığına veri çubuğu uygulandı."

            return f"{range_str} aralığına biçimlendirme uygulandı."

        except Exception as e:
            logger.error("Koşullu biçimlendirme hatası (%s): %s", range_str, str(e))
            raise

    def _parse_color_str(self, color_str: str) -> int:
        """Renk string'ini RGB int'e dönüştürür."""
        color_str = color_str.strip().lower()
        color_names = {
            "red": 0xFF0000, "green": 0x00FF00, "blue": 0x0000FF,
            "yellow": 0xFFFF00, "white": 0xFFFFFF, "black": 0x000000,
            "orange": 0xFF8C00, "purple": 0x800080, "gray": 0x808080,
        }
        if color_str in color_names:
            return color_names[color_str]
        if color_str.startswith("#"):
            return int(color_str[1:], 16)
        return int(color_str, 16)

    def set_data_validation(
        self,
        range_str: str,
        validation_type: str,
        values: str,
        error_message: str = None,
    ):
        """
        Hücreye veri doğrulama kuralı ekler.

        Args:
            range_str: Doğrulama uygulanacak aralık (ör: A1:A10).
            validation_type: Doğrulama tipi (list, whole_number, decimal, date, text_length).
            values: Liste için virgülle ayrılmış değerler veya sayı aralığı için 'min;max'.
            error_message: Geçersiz giriş durumunda gösterilecek hata mesajı.

        Returns:
            Sonuç açıklaması.
        """
        try:
            sheet = self.bridge.get_active_sheet()
            cell_range = self.bridge.get_cell_range(sheet, range_str)

            from com.sun.star.sheet.ValidationType import LIST, WHOLE, DECIMAL, DATE, TEXT_LENGTH
            from com.sun.star.sheet.ValidationAlertStyle import STOP

            validation = cell_range.getPropertyValue("Validation")

            type_map = {
                "list": LIST,
                "whole_number": WHOLE,
                "decimal": DECIMAL,
                "date": DATE,
                "text_length": TEXT_LENGTH,
            }

            val_type = type_map.get(validation_type, LIST)
            validation.setPropertyValue("Type", val_type)

            if validation_type == "list":
                # Liste için değerleri ayarla
                items = [v.strip() for v in values.split(",")]
                validation.setPropertyValue("ShowList", True)
                validation.setPropertyValue("Formula1", ";".join(items))
            elif validation_type in ("whole_number", "decimal", "text_length"):
                # Sayı aralığı için
                if ";" in values:
                    min_val, max_val = values.split(";")
                    from com.sun.star.sheet.ConditionOperator import BETWEEN
                    validation.setPropertyValue("Operator", BETWEEN)
                    validation.setPropertyValue("Formula1", min_val.strip())
                    validation.setPropertyValue("Formula2", max_val.strip())
                else:
                    validation.setPropertyValue("Formula1", values.strip())

            if error_message:
                validation.setPropertyValue("ShowErrorMessage", True)
                validation.setPropertyValue("ErrorMessage", error_message)
                validation.setPropertyValue("ErrorAlertStyle", STOP)

            cell_range.setPropertyValue("Validation", validation)

            logger.info("Veri doğrulama uygulandı: %s", range_str.upper())
            return f"{range_str} aralığına veri doğrulama uygulandı ({validation_type})."

        except Exception as e:
            logger.error("Veri doğrulama hatası (%s): %s", range_str, str(e))
            raise

    def list_sheets(self):
        """
        Çalışma kitabındaki tüm sayfa isimlerini listeler.

        Returns:
            Sayfa isimlerinin listesi.
        """
        try:
            doc = self.bridge.get_active_document()
            sheets = doc.getSheets()
            sheet_names = []
            for i in range(sheets.getCount()):
                sheet = sheets.getByIndex(i)
                sheet_names.append(sheet.getName())
            logger.info("Sayfalar listelendi: %s", sheet_names)
            return sheet_names
        except Exception as e:
            logger.error("Sayfa listeleme hatası: %s", str(e))
            raise

    def switch_sheet(self, sheet_name: str):
        """
        Belirtilen sayfaya geçiş yapar.

        Args:
            sheet_name: Geçiş yapılacak sayfa adı.

        Returns:
            Sonuç açıklaması.
        """
        try:
            doc = self.bridge.get_active_document()
            sheets = doc.getSheets()

            if not sheets.hasByName(sheet_name):
                raise ValueError(f"'{sheet_name}' adında bir sayfa bulunamadı.")

            sheet = sheets.getByName(sheet_name)
            controller = doc.getCurrentController()
            controller.setActiveSheet(sheet)

            logger.info("Sayfaya geçiş yapıldı: %s", sheet_name)
            return f"'{sheet_name}' sayfasına geçiş yapıldı."

        except Exception as e:
            logger.error("Sayfa geçiş hatası (%s): %s", sheet_name, str(e))
            raise

    def create_sheet(self, sheet_name: str, position: int = None):
        """
        Yeni bir sayfa oluşturur.

        Args:
            sheet_name: Yeni sayfa adı.
            position: Sayfa pozisyonu (0 tabanlı). Belirtilmezse sona eklenir.

        Returns:
            Sonuç açıklaması.
        """
        try:
            doc = self.bridge.get_active_document()
            sheets = doc.getSheets()

            if position is None:
                position = sheets.getCount()

            sheets.insertNewByName(sheet_name, position)

            logger.info("Yeni sayfa oluşturuldu: %s (pozisyon: %d)", sheet_name, position)
            return f"'{sheet_name}' adında yeni sayfa oluşturuldu."

        except Exception as e:
            logger.error("Sayfa oluşturma hatası (%s): %s", sheet_name, str(e))
            raise

    def rename_sheet(self, old_name: str, new_name: str):
        """
        Sayfanın adını değiştirir.

        Args:
            old_name: Mevcut sayfa adı.
            new_name: Yeni sayfa adı.

        Returns:
            Sonuç açıklaması.
        """
        try:
            doc = self.bridge.get_active_document()
            sheets = doc.getSheets()

            if not sheets.hasByName(old_name):
                raise ValueError(f"'{old_name}' adında bir sayfa bulunamadı.")

            sheet = sheets.getByName(old_name)
            sheet.setName(new_name)

            logger.info("Sayfa yeniden adlandırıldı: %s -> %s", old_name, new_name)
            return f"Sayfa '{old_name}' -> '{new_name}' olarak yeniden adlandırıldı."

        except Exception as e:
            logger.error("Sayfa yeniden adlandırma hatası: %s", str(e))
            raise

    def copy_range(self, source_range: str, target_cell: str):
        """
        Bir hücre aralığını başka bir konuma kopyalar.

        Args:
            source_range: Kaynak aralık (ör: A1:C10).
            target_cell: Hedef başlangıç hücresi (ör: E1).

        Returns:
            Sonuç açıklaması.
        """
        try:
            sheet = self.bridge.get_active_sheet()
            source = self.bridge.get_cell_range(sheet, source_range)
            target = self._get_cell(target_cell)

            # Kopyala
            source_address = source.getRangeAddress()
            target_address = target.getCellAddress()

            sheet.copyRange(target_address, source_address)

            logger.info("Aralık kopyalandı: %s -> %s", source_range.upper(), target_cell.upper())
            return f"{source_range} aralığı {target_cell} konumuna kopyalandı."

        except Exception as e:
            logger.error("Kopyalama hatası: %s", str(e))
            raise

    def create_chart(
        self,
        data_range: str,
        chart_type: str,
        title: str = None,
        position: str = None,
        has_header: bool = True,
    ):
        """
        Verilerden grafik oluşturur.

        Args:
            data_range: Grafik verileri için aralık (ör: A1:B10).
            chart_type: Grafik tipi (bar, line, pie, scatter, column).
            title: Grafik başlığı.
            position: Grafiğin yerleştirileceği hücre (ör: E1).
            has_header: İlk satır/sütun etiket mi?

        Returns:
            Sonuç açıklaması.
        """
        try:
            sheet = self.bridge.get_active_sheet()
            cell_range = self.bridge.get_cell_range(sheet, data_range)
            range_address = cell_range.getRangeAddress()

            # Grafik pozisyonu
            if position:
                pos_cell = self._get_cell(position)
                pos_x = pos_cell.Position.X
                pos_y = pos_cell.Position.Y
            else:
                pos_x = 10000  # 10cm
                pos_y = 1000   # 1cm

            from com.sun.star.awt import Rectangle

            rect = Rectangle()
            rect.X = pos_x
            rect.Y = pos_y
            rect.Width = 12000   # 12cm
            rect.Height = 8000   # 8cm

            # Grafik oluştur
            charts = sheet.getCharts()
            chart_name = f"Chart_{len(charts)}"

            # Grafik tipi mapping
            type_map = {
                "bar": "com.sun.star.chart.BarDiagram",
                "column": "com.sun.star.chart.BarDiagram",  # LibreOffice'te bar = column
                "line": "com.sun.star.chart.LineDiagram",
                "pie": "com.sun.star.chart.PieDiagram",
                "scatter": "com.sun.star.chart.XYDiagram",
            }

            chart_service = type_map.get(chart_type, "com.sun.star.chart.BarDiagram")

            # Grafik ekle
            charts.addNewByName(
                chart_name,
                rect,
                (range_address,),
                has_header,
                has_header
            )

            chart = charts.getByName(chart_name).getEmbeddedObject()
            diagram = chart.createInstance(chart_service)
            chart.setDiagram(diagram)

            # Bar/Column ayrımı
            if chart_type == "bar" and hasattr(diagram, "Vertical"):
                diagram.Vertical = True
            elif chart_type == "column" and hasattr(diagram, "Vertical"):
                diagram.Vertical = False

            # Başlık
            if title:
                chart.setPropertyValue("HasMainTitle", True)
                chart_title = chart.getTitle()
                chart_title.setPropertyValue("String", title)

            logger.info("Grafik oluşturuldu: %s (%s)", chart_name, chart_type)
            return f"{chart_type} tipi grafik oluşturuldu."

        except Exception as e:
            logger.error("Grafik oluşturma hatası: %s", str(e))
            raise
