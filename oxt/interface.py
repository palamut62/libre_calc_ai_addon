"""LibreOffice Script Provider entry point.

This module bridges LibreOffice's Script Framework to the real CalcAI application.
It sets up Python paths, imports the actual modules, and launches the PyQt5 UI.
"""

import sys
import os
import logging

logger = logging.getLogger("CalcAI.interface")

# --- Path Setup ---
# __file__ is not available during exec() in LO Script Provider (pythonscript.py:495)
# The compile filename is set at pythonscript.py:492 and available via frame code object
_this_file = globals().get('__file__') or sys._getframe().f_code.co_filename
_script_dir = os.path.dirname(os.path.abspath(_this_file))
_calcai_dir = os.path.join(_script_dir, "CalcAI")

# Add CalcAI directory to sys.path (contains ui/, core/, llm/, config/)
if _calcai_dir not in sys.path:
    sys.path.insert(0, _calcai_dir)

# Add Python site-packages for third-party dependencies (PyQt5, requests, etc.)
def _setup_site_packages():
    """Find and add Python site-packages directories to sys.path."""
    import glob

    # Candidate site-packages paths
    candidates = []

    # 1. Bundled pythonpath inside the extension
    pythonpath_dir = os.path.join(_calcai_dir, "pythonpath")
    if os.path.isdir(pythonpath_dir):
        candidates.append(pythonpath_dir)

    # 2. Project venv (development convenience)
    # Walk up from script_dir to find the project root with a venv/
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(_calcai_dir)  # up from Scripts/python/CalcAI
    )))
    venv_patterns = [
        os.path.join(project_root, "venv", "lib", "python*", "site-packages"),
        os.path.join(os.path.expanduser("~"), "Masaüstü", "UYGULAMALARIM",
                     "libre_clac_ai_addon", "venv", "lib", "python*", "site-packages"),
    ]
    for pattern in venv_patterns:
        candidates.extend(glob.glob(pattern))

    # 3. System site-packages
    try:
        import site
        candidates.extend(site.getsitepackages())
    except Exception:
        pass

    # 4. User site-packages
    try:
        import site
        user_site = site.getusersitepackages()
        if user_site:
            candidates.append(user_site)
    except Exception:
        pass

    # 5. Common system paths
    candidates.extend([
        "/usr/lib/python3/dist-packages",
        "/usr/local/lib/python3/dist-packages",
    ])

    for path in candidates:
        if os.path.isdir(path) and path not in sys.path:
            sys.path.insert(1, path)

_setup_site_packages()


# --- Global state ---
_qapp = None
_main_window = None


def _get_desktop_from_context():
    """Get LibreOffice Desktop from the script execution context."""
    try:
        ctx = XSCRIPTCONTEXT.getComponentContext()
        smgr = ctx.ServiceManager
        desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
        return ctx, desktop
    except Exception:
        return None, None


def _ensure_qapp():
    """Create QApplication if it doesn't exist yet."""
    global _qapp
    try:
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import Qt

        _qapp = QApplication.instance()
        if _qapp is None:
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
            _qapp = QApplication(sys.argv)
            _qapp.setApplicationName("ArasAI")
            _qapp.setOrganizationName("ArasAI")
        return True
    except ImportError as e:
        logger.error("PyQt5 not available: %s", e)
        return False


def _inject_uno_context(window):
    """Create bridge with injected UNO context and set up all components on MainWindow."""
    try:
        ctx, desktop = _get_desktop_from_context()
        if not ctx or not desktop:
            logger.warning("Could not get UNO context from XSCRIPTCONTEXT")
            return False

        from core import LibreOfficeBridge, CellInspector, CellManipulator, SheetAnalyzer, ErrorDetector
        from llm.tool_definitions import ToolDispatcher

        # Create bridge and inject UNO context directly (no socket needed)
        bridge = LibreOfficeBridge()
        bridge._local_context = ctx
        bridge._context = ctx
        bridge._desktop = desktop
        bridge._connected = True

        # Assign bridge to window
        window._bridge = bridge

        # Set up all tool components (same as _connect_lo_silent)
        inspector = CellInspector(bridge)
        manipulator = CellManipulator(bridge)
        analyzer = SheetAnalyzer(bridge)
        detector = ErrorDetector(bridge, inspector)
        window._dispatcher = ToolDispatcher(
            inspector, manipulator, analyzer, detector,
            change_logger=window._record_change
        )

        # Update status bar to show connected
        window._update_status_bar()

        logger.info("UNO context injected directly (no socket needed)")
        return True

    except Exception as e:
        logger.warning("Could not inject UNO context: %s", e, exc_info=True)
        return False


def show_assistant(*args):
    """Open the AI Assistant main window."""
    global _main_window

    try:
        if not _ensure_qapp():
            _show_error("PyQt5 bulunamadi. Lutfen 'pip install PyQt5' ile kurun.")
            return

        from ui.main_window import MainWindow

        if _main_window is None or not _main_window.isVisible():
            # Create window without socket connection attempt
            _main_window = MainWindow(skip_lo_connect=True)

            # Inject UNO context directly from LibreOffice
            if _inject_uno_context(_main_window):
                from ui.i18n import get_text
                lang = _main_window._current_lang
                _main_window._chat_widget.add_message(
                    "assistant", get_text("msg_lo_connected", lang)
                )

            _main_window.show()
        else:
            _main_window.raise_()
            _main_window.activateWindow()

        # Run the Qt event loop (blocks until window is closed)
        _qapp.exec_()

    except Exception as e:
        logger.error("show_assistant error: %s", e, exc_info=True)
        _show_error(f"AI Asistan acilamadi:\n{e}")


def show_settings(*args):
    """Open the settings dialog."""
    try:
        if not _ensure_qapp():
            _show_error("PyQt5 bulunamadi.")
            return

        from ui.settings_dialog import SettingsDialog

        dialog = SettingsDialog()
        dialog.exec_()

    except Exception as e:
        logger.error("show_settings error: %s", e, exc_info=True)
        _show_error(f"Ayarlar acilamadi:\n{e}")


def show_about(*args):
    """Show the help/about dialog."""
    try:
        if not _ensure_qapp():
            _show_error("PyQt5 bulunamadi.")
            return

        from ui.help_dialog import HelpDialog

        dlg = HelpDialog()
        dlg.exec_()

    except Exception as e:
        logger.error("show_about error: %s", e, exc_info=True)
        _show_error(f"Hakkinda gosterilemedi:\n{e}")


def _show_error(message):
    """Show error using LibreOffice UNO message box as fallback."""
    try:
        import uno
        ctx = XSCRIPTCONTEXT.getComponentContext()
        smgr = ctx.ServiceManager
        desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
        frame = desktop.getCurrentFrame()
        window = frame.getContainerWindow()
        toolkit = window.getToolkit()

        from com.sun.star.awt.MessageBoxType import ERRORBOX
        box = toolkit.createMessageBox(window, ERRORBOX, 1, "CalcAI Hata", message)
        box.execute()
    except Exception:
        print(f"CalcAI ERROR: {message}", file=sys.stderr)


# Export scripts for the Script Provider
g_exportedScripts = (show_assistant, show_settings, show_about)
