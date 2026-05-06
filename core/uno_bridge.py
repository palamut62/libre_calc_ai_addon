"""LibreOffice UNO köprüsü - PyUNO üzerinden LibreOffice Calc ile iletişim sağlar."""

import logging
import os
import sys
import time
from pathlib import Path

from .address_utils import (
    column_to_index,
    index_to_column,
    parse_address,
    parse_range_string,
)

logger = logging.getLogger(__name__)
_DLL_DIR_HANDLES = []
uno = None
PropertyValue = None
NoConnectException = Exception
UNO_AVAILABLE = False
_UNO_IMPORT_ERROR = None


def _add_sys_path_if_dir(path: str):
    if path and os.path.isdir(path) and path not in sys.path:
        sys.path.insert(0, path)


def _windows_add_dll_dir(path: str):
    if sys.platform != "win32" or not path:
        return
    if not hasattr(os, "add_dll_directory"):
        return
    try:
        _DLL_DIR_HANDLES.append(os.add_dll_directory(path))
    except OSError:
        pass


def _lo_program_candidates() -> list[str]:
    candidates = []

    for key in ("UNO_PATH", "LIBREOFFICE_PROGRAM_PATH"):
        value = os.environ.get(key, "")
        if value:
            candidates.append(value)

    ure_bootstrap = os.environ.get("URE_BOOTSTRAP", "")
    marker = "vnd.sun.star.pathname:"
    if ure_bootstrap.startswith(marker):
        # Example:
        # vnd.sun.star.pathname:C:\Program Files\LibreOffice\program\fundamental.ini
        ini_path = ure_bootstrap[len(marker):]
        if ini_path:
            candidates.append(str(Path(ini_path).parent))

    if sys.platform == "win32":
        pf = os.environ.get("PROGRAMFILES", r"C:\Program Files")
        pf86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
        candidates.extend(
            [
                os.path.join(pf, "LibreOffice", "program"),
                os.path.join(pf86, "LibreOffice", "program"),
            ]
        )
    else:
        candidates.extend(
            [
                "/usr/lib/libreoffice/program",
                "/usr/lib64/libreoffice/program",
                "/opt/libreoffice/program",
                "/Applications/LibreOffice.app/Contents/Resources",
            ]
        )

    # Preserve order, remove duplicates
    seen = set()
    uniq = []
    for c in candidates:
        c_norm = os.path.normpath(c)
        if c_norm in seen:
            continue
        seen.add(c_norm)
        uniq.append(c_norm)
    return uniq


def _try_import_uno(enable_bootstrap: bool = False):
    """Try importing UNO safely.

    Note:
    On Windows, loading pyuno from a mismatched external Python can crash
    the process (access violation). Therefore path bootstrap is opt-in.
    """
    try:
        import uno as _uno
        from com.sun.star.beans import PropertyValue as _PropertyValue
        from com.sun.star.connection import NoConnectException as _NoConnectException
        return _uno, _PropertyValue, _NoConnectException, True, None
    except Exception as exc:
        first_error = exc

    if not enable_bootstrap:
        return None, None, None, False, first_error

    for program_dir in _lo_program_candidates():
        if not os.path.isdir(program_dir):
            continue

        _add_sys_path_if_dir(program_dir)
        _windows_add_dll_dir(program_dir)

        # If URE_BOOTSTRAP is missing, set it from fundamental.ini
        fundamental_ini = Path(program_dir) / "fundamental.ini"
        if fundamental_ini.exists() and not os.environ.get("URE_BOOTSTRAP"):
            os.environ["URE_BOOTSTRAP"] = f"vnd.sun.star.pathname:{fundamental_ini}"

        try:
            import uno as _uno
            from com.sun.star.beans import PropertyValue as _PropertyValue
            from com.sun.star.connection import NoConnectException as _NoConnectException
            logger.info("UNO import bootstrap successful from: %s", program_dir)
            return _uno, _PropertyValue, _NoConnectException, True, None
        except Exception:
            continue

    return None, None, None, False, first_error


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
        self._max_retries = 3
        self._retry_delay = 1.0

        # Bağlantı tipini ortam değişkenlerinden oku
        self._connect_type = os.environ.get("LO_CONNECT_TYPE", "socket")
        self._pipe_name = os.environ.get("LO_PIPE_NAME", "librecalcai")

    @property
    def is_connected(self) -> bool:
        """Bağlantı durumunu döndürür."""
        return self._connected

    # Geriye uyumluluk: eski kodda bridge/_class üstünden çağrılan yardımcılar.
    @staticmethod
    def _index_to_column(index: int) -> str:
        return index_to_column(index)

    @staticmethod
    def _column_to_index(col_str: str) -> int:
        return column_to_index(col_str)

    @staticmethod
    def parse_address(address: str) -> tuple[int, int]:
        return parse_address(address)

    @staticmethod
    def parse_range_string(range_str: str) -> tuple[tuple[int, int], tuple[int, int]]:
        return parse_range_string(range_str)

    def connect(self) -> bool:
        """
        LibreOffice'e UNO soketi veya pipe üzerinden bağlanır.

        Returns:
            Bağlantı başarılıysa True, değilse False.

        Raises:
            RuntimeError: UNO modülü yüklü değilse.
        """
        global uno, PropertyValue, NoConnectException, UNO_AVAILABLE, _UNO_IMPORT_ERROR
        if not UNO_AVAILABLE:
            bootstrap = os.environ.get("CALCAI_UNO_BOOTSTRAP", "0") == "1"
            uno, PropertyValue, NoConnectException, UNO_AVAILABLE, _UNO_IMPORT_ERROR = _try_import_uno(
                enable_bootstrap=bootstrap
            )
        if not UNO_AVAILABLE:
            raise RuntimeError(
                "UNO modülü bulunamadı. "
                "Windows'ta uyumsuz pyuno yüklemesi süreç çökmesine neden olabildiği için "
                "otomatik bootstrap varsayılan olarak kapalıdır. "
                "Gerekirse CALCAI_UNO_BOOTSTRAP=1 ile tekrar deneyin."
            )

        # Öncelik: LibreOffice'in resmi bootstrap yolu.
        # Eklenti senaryosunda çalışan LO oturumuna en stabil bağlantı budur.
        if self._connect_via_officehelper():
            return True

        # Bağlantı string'lerini belirle
        connection_candidates = []
        if self._connect_type == "pipe":
            connection_candidates.append(
                f"uno:pipe,name={self._pipe_name};"
                f"urp;StarOffice.ComponentContext"
            )
        else:
            hosts = [self.host, "127.0.0.1", "localhost"]
            seen = set()
            for host in hosts:
                if host in seen:
                    continue
                seen.add(host)
                connection_candidates.append(
                    f"uno:socket,host={host},port={self.port};"
                    f"urp;StarOffice.ComponentContext"
                )

        for connection_str in connection_candidates:
            for attempt in range(1, self._max_retries + 1):
                try:
                    logger.info(
                        "LibreOffice'e bağlanılıyor: %s (deneme %d/%d)",
                        connection_str, attempt, self._max_retries,
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
                    logger.info("LibreOffice bağlantısı başarılı.")
                    return True

                except Exception as e:
                    logger.warning(
                        "Bağlantı denemesi başarısız (%s, %d/%d): %s",
                        connection_str, attempt, self._max_retries, str(e)
                    )
                    if attempt < self._max_retries:
                        time.sleep(self._retry_delay)

        self._connected = False
        logger.error(
            "%d deneme sonrası LibreOffice'e bağlanılamadı.", self._max_retries
        )
        return False

    def _connect_via_officehelper(self) -> bool:
        """LibreOffice runtime bootstrap ile masaüstüne bağlanmayı dener."""
        try:
            import officehelper

            logger.info("officehelper.bootstrap() ile LibreOffice bağlantısı deneniyor.")
            self._context = officehelper.bootstrap()
            smgr = self._context.ServiceManager
            self._desktop = smgr.createInstanceWithContext(
                "com.sun.star.frame.Desktop", self._context
            )
            self._connected = True
            logger.info("LibreOffice bağlantısı başarılı (officehelper bootstrap).")
            return True
        except Exception as e:
            logger.warning("officehelper bootstrap bağlantısı başarısız: %s", e)
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
                    "Calc belgesinin açık olduğundan emin olun. "
                    "Harici otomasyon için gerekirse --accept ile de başlatabilirsiniz: "
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
            # Headless/remote sessions can have no "current" component even when
            # documents are open. Fallback to first spreadsheet component.
            try:
                components = self._desktop.getComponents()
                enum = components.createEnumeration()
                while enum.hasMoreElements():
                    comp = enum.nextElement()
                    if comp and comp.supportsService("com.sun.star.sheet.SpreadsheetDocument"):
                        doc = comp
                        break
            except Exception:
                doc = None

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
