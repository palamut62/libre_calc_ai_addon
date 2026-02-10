
import sys
import os
from PyQt5.QtWidgets import QApplication

# Add current directory to path
sys.path.append(os.getcwd())

# Mock Settings if needed, or rely on actual settings
# Trying to import SettingsDialog directly
try:
    from ui.settings_dialog import SettingsDialog
    
    app = QApplication(sys.argv)
    dialog = SettingsDialog()
    print("SettingsDialog initialized successfully")
except Exception as e:
    print(f"Error initializing SettingsDialog: {e}")
    import traceback
    traceback.print_exc()
