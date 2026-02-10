#!/usr/bin/env python3
"""LibreCalc AI Asistanı - Ana giriş noktası.

LibreOffice Calc ile doğal dil komutlarıyla etkileşim kuran
PyQt5 tabanlı AI asistanını başlatır.

Kullanım:
    python main.py [--no-lo] [--theme dark|light] [--provider openrouter|ollama]

LibreOffice'i dinleme modunda başlatmak için:
    libreoffice --calc --accept="socket,host=localhost,port=2002;urp;"
"""

import sys
import argparse
import logging

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

from config.settings import Settings
from ui.main_window import MainWindow


def setup_logging(verbose: bool = False):
    """Loglama yapılandırmasını kurar."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def parse_args():
    """Komut satırı argümanlarını ayrıştırır."""
    parser = argparse.ArgumentParser(
        description="LibreCalc AI Asistanı - LibreOffice Calc için AI destekli yardımcı"
    )
    parser.add_argument(
        "--no-lo",
        action="store_true",
        help="LibreOffice bağlantısı olmadan başlat (test modu)",
    )
    parser.add_argument(
        "--theme",
        choices=["dark", "light"],
        default=None,
        help="Arayüz teması (varsayılan: ayarlardan okunur)",
    )
    parser.add_argument(
        "--provider",
        choices=["openrouter", "ollama"],
        default=None,
        help="LLM sağlayıcısı (varsayılan: ayarlardan okunur)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Ayrıntılı loglama",
    )
    return parser.parse_args()


def main():
    """Uygulamayı başlatır."""
    args = parse_args()
    setup_logging(args.verbose)

    logger = logging.getLogger(__name__)
    logger.info("LibreCalc AI Asistanı başlatılıyor...")

    # Ayarları yükle
    settings = Settings()

    # Komut satırı argümanlarını ayarlara uygula
    if args.theme:
        settings.theme = args.theme
    if args.provider:
        settings.provider = args.provider

    # High DPI desteği (QApplication oluşturulmadan önce ayarlanmalı)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # Qt uygulamasını oluştur
    app = QApplication(sys.argv)
    app.setApplicationName("LibreCalc AI Asistanı")
    app.setOrganizationName("LibreCalcAI")

    # Ana pencereyi oluştur ve göster
    window = MainWindow(skip_lo_connect=args.no_lo)
    window.show()

    logger.info("Uygulama hazır.")
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
