"""LibreOffice UNO köprüsü - PyUNO üzerinden LibreOffice Calc ile iletişim sağlar."""

import logging
import os
import time

from .address_utils import index_to_column, parse_range_string

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
        start, end = parse_range_string(range_str)
        return sheet.getCellRangeByPosition(
            start[0], start[1], end[0], end[1]
        )

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
                col = index_to_column(addr.Column)
                return f"{col}{addr.Row + 1}"

            if hasattr(selection, "getRangeAddress"):
                addr = selection.getRangeAddress()
                start_col = index_to_column(addr.StartColumn)
                end_col = index_to_column(addr.EndColumn)
                return f"{start_col}{addr.StartRow + 1}:{end_col}{addr.EndRow + 1}"

            # Çoklu seçim (SheetCellRanges)
            if hasattr(selection, "getRangeAddresses"):
                ranges = cls.get_selection_ranges(selection)
                if not ranges:
                    return "Çoklu Seçim"
                if len(ranges) > 3:
                    return f"Çoklu Seçim ({len(ranges)} alan)"
                return ", ".join(ranges)

            return "Bilinmeyen Seçim"

        except Exception as e:
            logger.error("Seçim adresi alınırken hata: %s", e)
            return "Hata"

    @classmethod
    def get_selection_ranges(cls, selection) -> list:
        """Seçimi aralık listesine dönüştürür."""
        if selection is None:
            return []
        try:
            if hasattr(selection, "getCellAddress"):
                addr = selection.getCellAddress()
                col = index_to_column(addr.Column)
                return [f"{col}{addr.Row + 1}"]

            if hasattr(selection, "getRangeAddress"):
                addr = selection.getRangeAddress()
                start_col = index_to_column(addr.StartColumn)
                end_col = index_to_column(addr.EndColumn)
                if addr.StartColumn == addr.EndColumn and addr.StartRow == addr.EndRow:
                    return [f"{start_col}{addr.StartRow + 1}"]
                return [f"{start_col}{addr.StartRow + 1}:{end_col}{addr.EndRow + 1}"]

            if hasattr(selection, "getRangeAddresses"):
                addrs = selection.getRangeAddresses()
                parts = []
                for addr in addrs:
                    start_col = index_to_column(addr.StartColumn)
                    end_col = index_to_column(addr.EndColumn)
                    if addr.StartColumn == addr.EndColumn and addr.StartRow == addr.EndRow:
                        parts.append(f"{start_col}{addr.StartRow + 1}")
                    else:
                        parts.append(f"{start_col}{addr.StartRow + 1}:{end_col}{addr.EndRow + 1}")
                return parts
        except Exception:
            return []
        return []

    def __enter__(self):
        """Context manager girişi - bağlantıyı açar."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager çıkışı - bağlantıyı kapatır."""
        self.disconnect()
        return False
