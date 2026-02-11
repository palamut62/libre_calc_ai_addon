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


def setup_window_layout(window, addon_percent: int = 30):
    """Pencereyi ekranın sağ tarafına konumlandırır ve LibreOffice'i sola yerleştirir.

    Args:
        window: QMainWindow nesnesi.
        addon_percent: Eklenti için ekran genişliğinin yüzdesi (varsayılan %30).
    """
    import subprocess
    from PyQt5.QtWidgets import QDesktopWidget
    from PyQt5.QtCore import QTimer

    desktop = QDesktopWidget()
    screen = desktop.availableGeometry(desktop.primaryScreen())

    screen_width = screen.width()
    screen_height = screen.height()

    # Eklenti genişliği (%30)
    addon_width = int(screen_width * addon_percent / 100)

    # LibreOffice genişliği (%70)
    lo_width = screen_width - addon_width

    # Eklenti penceresini sağa konumlandır
    window.setGeometry(lo_width, 0, addon_width, screen_height)

    # LibreOffice penceresini sola konumlandır (wmctrl ile)
    def position_libreoffice():
        try:
            # wmctrl var mı kontrol et
            result = subprocess.run(["which", "wmctrl"], capture_output=True, text=True)
            if result.returncode != 0:
                return

            # LibreOffice penceresini bul
            result = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if "calc" in line.lower() or "libreoffice" in line.lower():
                    wid = line.split()[0]
                    # Maximize'ı kaldır
                    subprocess.run([
                        "wmctrl", "-i", "-r", wid,
                        "-b", "remove,maximized_vert,maximized_horz"
                    ], capture_output=True)
                    # Konumlandır: x=0, y=0, genişlik=lo_width, yükseklik=screen_height
                    subprocess.run([
                        "wmctrl", "-i", "-r", wid,
                        "-e", f"0,0,0,{lo_width},{screen_height}"
                    ], capture_output=True)
                    break
        except Exception:
            pass

    # Biraz bekleyip LibreOffice'i konumlandır
    QTimer.singleShot(500, position_libreoffice)


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

    if not settings.logging_enabled:
        logging.disable(logging.CRITICAL)

    # High DPI desteği (QApplication oluşturulmadan önce ayarlanmalı)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # Qt uygulamasını oluştur
    app = QApplication(sys.argv)
    app.setApplicationName("ArasAI")
    app.setOrganizationName("ArasAI")

    # Ana pencereyi oluştur
    window = MainWindow(skip_lo_connect=args.no_lo)

    # Pencereleri yan yana konumlandır (LibreOffice %70 sol, ArasAI %30 sağ)
    setup_window_layout(window, addon_percent=20)

    window.show()

    logger.info("Uygulama hazır.")
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
