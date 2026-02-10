"""LibreOffice olay dinleyicisi - Secim degisikliklerini takip eder."""

import logging
import threading
import uno
import unohelper
from com.sun.star.view import XSelectionChangeListener
from com.sun.star.lang import EventObject
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class SelectionChangeHandler(unohelper.Base, XSelectionChangeListener):
    """LibreOffice secim degisikliklerini dinleyen UNO sinifi."""

    def __init__(self, callback):
        """
        Handler baslatici.

        Args:
            callback: Secim degistiginde cagrilacak fonksiyon.
        """
        self.callback = callback

    def selectionChanged(self, event: EventObject):
        """
        Secim degistiginde LibreOffice tarafindan cagrilir.
        
        Args:
            event: Olay nesnesi.
        """
        try:
            # Callback'i cagir (genellikle Bridge sinyalini tetikler)
            self.callback(event)
        except Exception as e:
            logger.error("Selection change hatasi: %s", e)

    def disposing(self, event: EventObject):
        """Dinlenen nesne yok oldugunda cagrilir."""
        pass


class LibreOfficeEventListener(QObject):
    """
    LibreOffice olaylarini dinler ve PyQt sinyallerine cevirir.
    UI thread'i ile güvenli iletisim saglar.
    """
    
    # Secim degistiginde tetiklenir (controller nesnesi gonderilir)
    selection_changed = pyqtSignal(object)

    def __init__(self, bridge):
        """
        EventListener baslatici.

        Args:
            bridge: LibreOfficeBridge ornegi.
        """
        super().__init__()
        self._bridge = bridge
        self._handler = None
        self._controller = None
        self._listening = False

    def start(self):
        """Dinlemeyi baslatir."""
        if self._listening:
            return

        try:
            doc = self._bridge.get_active_document()
            self._controller = doc.getCurrentController()
            
            # Handler olustur
            self._handler = SelectionChangeHandler(self._on_selection_changed_uno)
            
            # Listener'i kaydet
            self._controller.addSelectionChangeListener(self._handler)
            self._listening = True
            logger.info("Selection listener baslatildi.")
            
        except Exception as e:
            logger.error("Listener baslatma hatasi: %s", e)

    def stop(self):
        """Dinlemeyi durdurur."""
        if not self._listening or not self._controller:
            return

        try:
            self._controller.removeSelectionChangeListener(self._handler)
            self._handler = None
            self._controller = None
            self._listening = False
            logger.info("Selection listener durduruldu.")
        except Exception as e:
            logger.error("Listener durdurma hatasi: %s", e)

    def _on_selection_changed_uno(self, event):
        """
        UNO thread'inden gelen olayi karsilar ve PyQt sinyali yayar.
        Not: Bu metod UNO thread'inde calisir!
        """
        try:
            # Kaynak controller'i al
            source = event.Source
            # PyQt sinyali thread-safe'tir, dogrudan emit edilebilir
            self.selection_changed.emit(source)
        except Exception as e:
            logger.error("UNO event isleme hatasi: %s", e)
