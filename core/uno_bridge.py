"""LibreOffice UNO köprüsü - PyUNO üzerinden LibreOffice Calc ile iletişim sağlar."""

import logging
import os
import re
import time

try:
    import uno
    from com.sun.star.beans import PropertyValue
    from com.sun.star.connection import NoConnectException
    UNO_AVAILABLE = True
except ImportError:
    UNO_AVAILABLE = False

logger = logging.getLogger(__name__)


class LibreOfficeBridge:
    """LibreOffice Calc ile UNO protokolü üzerinden bağlantı kurar ve yönetir."""

    def __init__(self, host: str = "localhost", port: int = 2002):
        """
        LibreOfficeBridge başlatıcı.

        Args:
            host: LibreOffice dinleme adresi.
            port: LibreOffice dinleme portu.
        """
        self.host = host
        self.port = port
        self._local_context = None
        self._resolver = None
        self._context = None
        self._desktop = None
        self._connected = False
        self._max_retries = 5
        self._retry_delay = 3.0

        # Bağlantı tipini ortam değişkenlerinden oku
        self._connect_type = os.environ.get("LO_CONNECT_TYPE", "socket")
        self._pipe_name = os.environ.get("LO_PIPE_NAME", "librecalcai")

    @property
    def is_connected(self) -> bool:
        """Bağlantı durumunu döndürür."""
        return self._connected

    def connect(self) -> bool:
        """
        LibreOffice'e UNO soketi veya pipe üzerinden bağlanır.

        Returns:
            Bağlantı başarılıysa True, değilse False.

        Raises:
            RuntimeError: UNO modülü yüklü değilse.
        """
        if not UNO_AVAILABLE:
            raise RuntimeError(
                "UNO modülü bulunamadı. LibreOffice Python paketlerinin "
                "kurulu olduğundan emin olun."
            )

        # Bağlantı string'ini belirle
        if self._connect_type == "pipe":
            connection_str = (
                f"uno:pipe,name={self._pipe_name};"
                f"urp;StarOffice.ComponentContext"
            )
        else:
            connection_str = (
                f"uno:socket,host={self.host},port={self.port};"
                f"urp;StarOffice.ComponentContext"
            )

        for attempt in range(1, self._max_retries + 1):
            try:
                logger.info(
                    "LibreOffice'e bağlanılıyor: %s (deneme %d/%d)",
                    self._connect_type, attempt, self._max_retries,
                )

                self._local_context = uno.getComponentContext()
                self._resolver = self._local_context.ServiceManager.createInstanceWithContext(
                    "com.sun.star.bridge.UnoUrlResolver", self._local_context
                )

                self._context = self._resolver.resolve(connection_str)

                smgr = self._context.ServiceManager
                self._desktop = smgr.createInstanceWithContext(
                    "com.sun.star.frame.Desktop", self._context
                )

                self._connected = True
                logger.info("LibreOffice bağlantısı başarılı (%s).", self._connect_type)
                return True

            except Exception as e:
                logger.warning(
                    "Bağlantı denemesi %d başarısız: %s", attempt, str(e)
                )
                if attempt < self._max_retries:
                    time.sleep(self._retry_delay)

        self._connected = False
        logger.error(
            "%d deneme sonrası LibreOffice'e bağlanılamadı.", self._max_retries
        )
        return False

    def disconnect(self):
        """LibreOffice bağlantısını kapatır."""
        self._desktop = None
        self._context = None
        self._resolver = None
        self._local_context = None
        self._connected = False
        logger.info("LibreOffice bağlantısı kapatıldı.")

    def _ensure_connected(self):
        """Bağlantının aktif olduğunu doğrular, değilse yeniden bağlanır."""
        if not self._connected:
            if not self.connect():
                raise ConnectionError(
                    "LibreOffice'e bağlantı kurulamadı. "
                    "LibreOffice'in --accept parametresiyle başlatıldığından emin olun: "
                    f"soffice --calc --accept='socket,host={self.host},port={self.port};urp;'"
                )

    def get_active_document(self):
        """
        Aktif belgeyi döndürür.

        Returns:
            Aktif LibreOffice Calc belgesi.

        Raises:
            ConnectionError: Bağlantı yoksa.
            RuntimeError: Aktif belge bulunamazsa.
        """
        self._ensure_connected()
        doc = self._desktop.getCurrentComponent()
        if doc is None:
            raise RuntimeError("Aktif bir LibreOffice belgesi bulunamadı.")
        return doc

    def get_active_sheet(self):
        """
        Aktif çalışma sayfasını döndürür.

        Returns:
            Aktif spreadsheet sayfası.

        Raises:
            ConnectionError: Bağlantı yoksa.
            RuntimeError: Aktif sayfa bulunamazsa.
        """
        doc = self.get_active_document()
        sheet = doc.getCurrentController().getActiveSheet()
        if sheet is None:
            raise RuntimeError("Aktif bir çalışma sayfası bulunamadı.")
        return sheet

    def get_cell(self, sheet, col: int, row: int):
        """
        Belirtilen konumdaki hücreyi döndürür.

        Args:
            sheet: Çalışma sayfası nesnesi.
            col: Sütun indeksi (0 tabanlı).
            row: Satır indeksi (0 tabanlı).

        Returns:
            Hücre nesnesi.
        """
        return sheet.getCellByPosition(col, row)

    def get_cell_range(self, sheet, range_str: str):
        """
        Belirtilen aralıktaki hücreleri döndürür.

        Args:
            sheet: Çalışma sayfası nesnesi.
            range_str: Hücre aralığı (ör. "A1:D10").

        Returns:
            Hücre aralığı nesnesi.
        """
        start, end = self.parse_range_string(range_str)
        return sheet.getCellRangeByPosition(
            start[0], start[1], end[0], end[1]
        )

    @staticmethod
    def parse_range_string(range_str: str) -> tuple:
        """
        Hücre aralığı dizesini sütun/satır indekslerine dönüştürür.

        Args:
            range_str: "A1:D10" veya "A1" formatında aralık dizesi.

        Returns:
            ((başlangıç_sütun, başlangıç_satır), (bitiş_sütun, bitiş_satır)) tuple.
            Tek hücre için her iki tuple aynıdır.

        Raises:
            ValueError: Geçersiz aralık formatı.
        """
        range_str = range_str.strip().upper()

        pattern = r'^([A-Z]+)(\d+)(?::([A-Z]+)(\d+))?$'
        match = re.match(pattern, range_str)
        if not match:
            raise ValueError(f"Geçersiz hücre aralığı formatı: '{range_str}'")

        start_col = LibreOfficeBridge._column_to_index(match.group(1))
        start_row = int(match.group(2)) - 1

        if match.group(3) is not None:
            end_col = LibreOfficeBridge._column_to_index(match.group(3))
            end_row = int(match.group(4)) - 1
        else:
            end_col = start_col
            end_row = start_row

        return (start_col, start_row), (end_col, end_row)

    @staticmethod
    def _column_to_index(col_str: str) -> int:
        """
        Sütun harfini 0 tabanlı indekse dönüştürür.

        Args:
            col_str: Sütun harfi (ör. "A", "AB").

        Returns:
            0 tabanlı sütun indeksi.
        """
        result = 0
        for char in col_str.upper():
            result = result * 26 + (ord(char) - ord('A') + 1)
        return result - 1

    @staticmethod
    def _index_to_column(index: int) -> str:
        """
        0 tabanlı sütun indeksini harf karşılığına dönüştürür.

        Args:
            index: 0 tabanlı sütun indeksi.

        Returns:
            Sütun harfi (ör. "A", "AB").
        """
        result = ""
        index += 1
        while index > 0:
            index, remainder = divmod(index - 1, 26)
            result = chr(ord('A') + remainder) + result
        return result

    @classmethod
    def get_selection_address(cls, selection) -> str:
        """
        Seçimin (tek hücre, aralık veya çoklu aralık) adresini döndürür.

        Args:
            selection: LibreOffice seçim nesnesi.

        Returns:
            str: Adres (ör. "A1", "A1:B5", "A1, C5:D10").
        """
        if selection is None:
            return "-"

        try:
            # Tekil hücre veya aralık
            if hasattr(selection, "getCellAddress"):
                addr = selection.getCellAddress()
                col = cls._index_to_column(addr.Column)
                return f"{col}{addr.Row + 1}"

            if hasattr(selection, "getRangeAddress"):
                addr = selection.getRangeAddress()
                start_col = cls._index_to_column(addr.StartColumn)
                end_col = cls._index_to_column(addr.EndColumn)
                return f"{start_col}{addr.StartRow + 1}:{end_col}{addr.EndRow + 1}"

            # Çoklu seçim (SheetCellRanges)
            if hasattr(selection, "getRangeAddresses"):
                addrs = selection.getRangeAddresses()
                parts = []
                # Çok fazla alan seçilirse özet geç
                if len(addrs) > 3:
                     return f"Çoklu Seçim ({len(addrs)} alan)"

                for addr in addrs:
                    start_col = cls._index_to_column(addr.StartColumn)
                    end_col = cls._index_to_column(addr.EndColumn)
                    if addr.StartColumn == addr.EndColumn and addr.StartRow == addr.EndRow:
                         parts.append(f"{start_col}{addr.StartRow + 1}")
                    else:
                         parts.append(f"{start_col}{addr.StartRow + 1}:{end_col}{addr.EndRow + 1}")
                return ", ".join(parts)

            return "Bilinmeyen Seçim"

        except Exception as e:
            logger.error("Seçim adresi alınırken hata: %s", e)
            return "Hata"

    def __enter__(self):
        """Context manager girişi - bağlantıyı açar."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager çıkışı - bağlantıyı kapatır."""
        self.disconnect()
        return False
