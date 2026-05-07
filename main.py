#!/usr/bin/env python3
"""LibreCalc AI Assistant - main entry point.

Starts the PyQt5-based AI assistant for LibreOffice Calc.
"""

import argparse
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config.settings import SUPPORTED_PROVIDERS
from config.settings import Settings


def create_startup_splash():
    """Create a short startup loading animation window."""
    from PyQt5.QtCore import Qt, QTimer
    from PyQt5.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

    splash = QWidget()
    splash.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
    splash.setAttribute(Qt.WA_TranslucentBackground, True)

    container = QWidget(splash)
    container.setObjectName("startup_container")
    container.setStyleSheet(
        "#startup_container {"
        "background: #0f172a; color: #e2e8f0; border: 1px solid #1e293b; "
        "border-radius: 14px;}"
        "QLabel { color: #e2e8f0; font-size: 13px; }"
        "QProgressBar { border: 1px solid #334155; border-radius: 6px; "
        "background: #0b1220; text-align: center; color: #cbd5e1; }"
        "QProgressBar::chunk { background: #22d3ee; border-radius: 5px; }"
    )

    root = QVBoxLayout(splash)
    root.setContentsMargins(0, 0, 0, 0)
    root.addWidget(container)

    layout = QVBoxLayout(container)
    layout.setContentsMargins(18, 16, 18, 16)
    layout.setSpacing(10)

    title = QLabel("ArasAI")
    title.setStyleSheet("font-size:16px; font-weight:700;")
    layout.addWidget(title)

    subtitle = QLabel("Asistan hazirlaniyor")
    layout.addWidget(subtitle)

    bar = QProgressBar()
    bar.setRange(0, 0)
    bar.setTextVisible(False)
    bar.setFixedHeight(12)
    layout.addWidget(bar)

    dots = {"value": 0}

    def tick():
        dots["value"] = (dots["value"] + 1) % 4
        subtitle.setText("Asistan hazirlaniyor" + "." * dots["value"])

    timer = QTimer(splash)
    timer.timeout.connect(tick)
    timer.start(250)

    splash.resize(280, 120)
    return splash, timer


def setup_logging(verbose: bool = False):
    """Setup logging."""
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%H:%M:%S"

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
    root.addHandler(console)

    log_dir = Path.home() / ".config" / "libre_calc_ai" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
    root.addHandler(file_handler)


def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="LibreCalc AI Assistant for LibreOffice Calc"
    )
    parser.add_argument(
        "--no-lo",
        action="store_true",
        help="Start without LibreOffice connection (test mode)",
    )
    parser.add_argument(
        "--theme",
        choices=["dark", "light"],
        default=None,
        help="UI theme (default: read from settings)",
    )
    parser.add_argument(
        "--provider",
        choices=list(SUPPORTED_PROVIDERS),
        default=None,
        help="LLM provider (default: read from settings)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose logging",
    )
    parser.add_argument(
        "--settings",
        action="store_true",
        help="Open settings dialog directly",
    )
    return parser.parse_args()


def setup_window_layout(window, addon_percent: int = 30):
    """Place assistant window right and LibreOffice left when possible."""
    import subprocess

    from PyQt5.QtCore import QTimer
    from PyQt5.QtWidgets import QDesktopWidget

    desktop = QDesktopWidget()
    screen = desktop.availableGeometry(desktop.primaryScreen())

    screen_x = screen.x()
    screen_y = screen.y()
    screen_width = screen.width()
    screen_height = screen.height()

    addon_width = int(screen_width * addon_percent / 100)
    addon_width = max(window.minimumWidth(), min(addon_width, 620))
    lo_width = screen_width - addon_width

    right_margin = 14
    top_margin = 6
    bottom_margin = 8
    x = screen_x + screen_width - addon_width - right_margin
    y = screen_y + top_margin
    height = max(window.minimumHeight(), screen_height - top_margin - bottom_margin)
    window.setGeometry(x, y, addon_width, height)

    def position_libreoffice():
        try:
            result = subprocess.run(["which", "wmctrl"], capture_output=True, text=True)
            if result.returncode != 0:
                return

            result = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if "calc" in line.lower() or "libreoffice" in line.lower():
                    wid = line.split()[0]
                    subprocess.run(
                        [
                            "wmctrl",
                            "-i",
                            "-r",
                            wid,
                            "-b",
                            "remove,maximized_vert,maximized_horz",
                        ],
                        capture_output=True,
                    )
                    subprocess.run(
                        [
                            "wmctrl",
                            "-i",
                            "-r",
                            wid,
                            "-e",
                            f"0,{screen_x},{screen_y},{max(200, lo_width-right_margin)},{height}",
                        ],
                        capture_output=True,
                    )
                    break
        except Exception:
            pass

    QTimer.singleShot(500, position_libreoffice)


def main():
    """Start the application."""
    args = parse_args()
    setup_logging(args.verbose)

    logger = logging.getLogger(__name__)
    logger.info("LibreCalc AI Assistant starting...")

    settings = Settings()
    if args.theme:
        settings.theme = args.theme
    if args.provider:
        settings.provider = args.provider

    if not settings.logging_enabled:
        logging.disable(logging.CRITICAL)

    # Some Windows LO builds can crash if PyQt5 loads before uno.
    try:
        import uno  # noqa: F401
    except Exception:
        pass

    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("ArasAI")
    app.setOrganizationName("ArasAI")

    splash = None
    splash_timer = None
    if not args.settings:
        splash, splash_timer = create_startup_splash()
        screen = app.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - splash.width()) // 2
            y = geo.y() + (geo.height() - splash.height()) // 2
            splash.move(x, y)
        splash.show()
        app.processEvents()

    if args.settings:
        from ui.settings_dialog import SettingsDialog

        dlg = SettingsDialog()
        sys.exit(dlg.exec_())

    from ui.main_window import MainWindow

    window = MainWindow(skip_lo_connect=args.no_lo)
    setup_window_layout(window, addon_percent=22)
    window.show()

    if splash is not None:
        app.processEvents()
        splash.close()
    if splash_timer is not None:
        splash_timer.stop()

    logger.info("Application ready.")
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
