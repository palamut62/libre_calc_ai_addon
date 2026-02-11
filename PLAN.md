# LibreCalc AI - OXT Extension Dönüşüm Planı

## Mevcut Durum Analizi

### Şu Anki Mimari
```
[Harici Python Uygulaması]
         ↓ (socket:2002)
[LibreOffice Calc - socket modunda]
```

**Sorunlar:**
1. LibreOffice'i `--accept="socket,..."` ile başlatmak gerekiyor
2. Harici pencere, native entegrasyon yok
3. Kullanıcı deneyimi zayıf

### Mevcut Bileşenler
| Bileşen | Dosya | Satır | Teknoloji |
|---------|-------|-------|-----------|
| UI - MainWindow | ui/main_window.py | 850+ | PyQt5 |
| UI - Chat | ui/chat_widget.py | 310+ | PyQt5 |
| UNO Bridge | core/uno_bridge.py | 280 | Socket-based |
| LLM Provider | llm/*.py | 500+ | httpx/requests |
| Tool Definitions | llm/tool_definitions.py | 650 | 18 araç |

---

## Hedef Mimari

### Seçenek A: Tkinter OXT (ÖNERİLEN)
```
[LibreOffice Calc]
    ↓ (native python)
[OXT Extension - Tkinter UI]
    ↓ (doğrudan UNO context)
[LLM API]
```

**Avantajlar:**
- Tkinter çoğu Python dağıtımında mevcut
- LibreOffice'in Python'u ile uyumlu
- Socket gerekmiyor, doğrudan UNO context
- Tek .oxt dosyası ile kurulum

**Dezavantajlar:**
- PyQt5 kadar modern görünüm yok
- UI yeniden yazılmalı

### Seçenek B: External Process + IPC
```
[LibreOffice Calc]
    ↓ (menü butonu)
[OXT Extension] → subprocess.Popen → [PyQt5 App]
    ↓ (pipe/socket IPC)
[LLM API]
```

**Avantajlar:**
- Mevcut PyQt5 UI korunur
- Modern görünüm

**Dezavantajlar:**
- Karmaşık IPC yönetimi
- İki ayrı süreç
- Bundling zorluğu

### Seçenek C: Web-based Sidebar
```
[LibreOffice Calc]
    ↓ (sidebar panel)
[OXT + Embedded Browser/HTML]
    ↓ (local HTTP)
[Python Flask Backend]
```

**Avantajlar:**
- Modern web UI
- LibreOffice sidebar entegrasyonu

**Dezavantajlar:**
- Flask dependency
- Port yönetimi
- Çok karmaşık

---

## Önerilen Yol: Seçenek A (Tkinter OXT)

### Faz 1: OXT İskeleti (1-2 gün)
```
libre_calc_ai.oxt/
├── META-INF/
│   └── manifest.xml
├── description.xml
├── Addons.xcu              # Menü tanımları
├── CalcAI/
│   ├── __init__.py
│   ├── main.py             # Entry point
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py  # Tkinter MainWindow
│   │   └── chat_widget.py  # Tkinter Chat
│   ├── core/
│   │   ├── __init__.py
│   │   ├── uno_bridge.py   # Direct context (socket yok)
│   │   └── ...
│   ├── llm/
│   │   ├── __init__.py
│   │   └── ...
│   └── pythonpath/         # Bundled dependencies
│       ├── httpx/
│       └── ...
└── icons/
    └── calc_ai.png
```

### Faz 2: UNO Bridge Refaktör (1 gün)
```python
# Mevcut (socket tabanlı):
def connect(self):
    self._local_context = uno.getComponentContext()
    self._resolver = ...
    self._context = self._resolver.resolve("uno:socket,...")

# Yeni (doğrudan context):
def connect(self):
    # OXT içinde zaten context mevcut
    self._context = uno.getComponentContext()
    smgr = self._context.ServiceManager
    self._desktop = smgr.createInstanceWithContext(
        "com.sun.star.frame.Desktop", self._context
    )
```

### Faz 3: UI Dönüşümü (3-5 gün)

#### MainWindow (PyQt5 → Tkinter)
```python
# Mevcut PyQt5:
class MainWindow(QMainWindow):
    def __init__(self):
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.chat_widget = ChatWidget()
        ...

# Yeni Tkinter:
class MainWindow(tk.Toplevel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.attributes('-topmost', True)
        self.overrideredirect(True)  # Frameless
        self.chat_widget = ChatWidget(self)
        ...
```

#### ChatWidget (PyQt5 → Tkinter)
```python
# Mevcut PyQt5:
class ChatWidget(QWidget):
    def __init__(self):
        self.messages = QScrollArea()
        self.input_field = QTextEdit()
        ...

# Yeni Tkinter:
class ChatWidget(ttk.Frame):
    def __init__(self, parent):
        self.messages = scrolledtext.ScrolledText(self)
        self.input_field = tk.Text(self, height=3)
        ...
```

### Faz 4: Dependency Bundling (1 gün)
```bash
# httpx ve bağımlılıkları OXT içine kopyala
pip install httpx --target=CalcAI/pythonpath/

# Gereksiz dosyaları temizle
find CalcAI/pythonpath -name "*.pyc" -delete
find CalcAI/pythonpath -name "__pycache__" -delete
```

### Faz 5: Build Script (1 gün)
```bash
#!/bin/bash
# build_oxt.sh

VERSION="1.0.0"
NAME="libre_calc_ai"

# Temizle
rm -rf build/
mkdir -p build/

# Dosyaları kopyala
cp -r CalcAI/ build/
cp -r META-INF/ build/
cp description.xml build/
cp Addons.xcu build/
cp -r icons/ build/

# OXT oluştur (zip formatı)
cd build
zip -r ../${NAME}-${VERSION}.oxt *
cd ..

echo "Created: ${NAME}-${VERSION}.oxt"
```

---

## Dosya Yapısı Detayları

### META-INF/manifest.xml
```xml
<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0">
    <manifest:file-entry
        manifest:full-path="CalcAI/"
        manifest:media-type="application/vnd.sun.star.uno-component;type=Python"/>
    <manifest:file-entry
        manifest:full-path="description.xml"
        manifest:media-type="application/vnd.sun.star.package-bundle-description"/>
</manifest:manifest>
```

### Addons.xcu
```xml
<?xml version="1.0" encoding="UTF-8"?>
<oor:component-data xmlns:oor="http://openoffice.org/2001/registry"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    oor:name="Addons" oor:package="org.openoffice.Office">

    <node oor:name="AddonUI">
        <node oor:name="OfficeMenuBar">
            <node oor:name="com.calcai.menu" oor:op="replace">
                <prop oor:name="Title" oor:type="xs:string">
                    <value>AI Assistant</value>
                </prop>
                <prop oor:name="Context" oor:type="xs:string">
                    <value>com.sun.star.sheet.SpreadsheetDocument</value>
                </prop>
                <node oor:name="Submenu">
                    <node oor:name="m1" oor:op="replace">
                        <prop oor:name="URL" oor:type="xs:string">
                            <value>vnd.sun.star.script:CalcAI.main.show_assistant?language=Python&amp;location=user:uno_packages</value>
                        </prop>
                        <prop oor:name="Title" oor:type="xs:string">
                            <value>Asistan Aç</value>
                        </prop>
                    </node>
                </node>
            </node>
        </node>

        <node oor:name="OfficeToolBar">
            <node oor:name="com.calcai.toolbar" oor:op="replace">
                <prop oor:name="Title" oor:type="xs:string">
                    <value>AI Assistant</value>
                </prop>
                <node oor:name="ToolBarItems">
                    <node oor:name="m1" oor:op="replace">
                        <prop oor:name="URL" oor:type="xs:string">
                            <value>vnd.sun.star.script:CalcAI.main.show_assistant?language=Python&amp;location=user:uno_packages</value>
                        </prop>
                        <prop oor:name="Title" oor:type="xs:string">
                            <value>AI Asistan</value>
                        </prop>
                        <prop oor:name="ImageIdentifier" oor:type="xs:string">
                            <value>%origin%/icons/calc_ai.png</value>
                        </prop>
                    </node>
                </node>
            </node>
        </node>
    </node>
</oor:component-data>
```

### description.xml
```xml
<?xml version="1.0" encoding="UTF-8"?>
<description xmlns="http://openoffice.org/extensions/description/2006"
    xmlns:xlink="http://www.w3.org/1999/xlink">

    <identifier value="com.aras.calcai"/>
    <version value="1.0.0"/>

    <display-name>
        <name lang="en">LibreCalc AI Assistant</name>
        <name lang="tr">LibreCalc AI Asistan</name>
    </display-name>

    <publisher>
        <name xlink:href="https://github.com/aras" lang="en">Aras</name>
    </publisher>

    <extension-description>
        <src xlink:href="description/description_en.txt" lang="en"/>
        <src xlink:href="description/description_tr.txt" lang="tr"/>
    </extension-description>

    <dependencies>
        <LibreOffice-minimal-version value="6.0"/>
    </dependencies>

    <platform value="all"/>
</description>
```

### CalcAI/main.py (Entry Point)
```python
"""LibreCalc AI - Ana giriş noktası (OXT için)."""

import uno
from com.sun.star.task import XJobExecutor

# Tkinter import (LibreOffice Python'unda mevcut olmalı)
try:
    import tkinter as tk
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False

# Global pencere referansı
_assistant_window = None


def show_assistant(*args):
    """AI Asistan penceresini gösterir."""
    global _assistant_window

    if not TKINTER_AVAILABLE:
        # Tkinter yoksa basit bir UNO dialog göster
        _show_error_dialog("Tkinter modülü bulunamadı.")
        return

    if _assistant_window is None or not _assistant_window.winfo_exists():
        from CalcAI.ui.main_window import MainWindow

        # UNO context'i al
        ctx = uno.getComponentContext()

        # Tkinter root oluştur (gizli)
        root = tk.Tk()
        root.withdraw()

        # Ana pencereyi oluştur
        _assistant_window = MainWindow(root, ctx)
    else:
        # Pencere varsa öne getir
        _assistant_window.lift()
        _assistant_window.focus_force()


def _show_error_dialog(message: str):
    """UNO ile basit hata dialogu gösterir."""
    ctx = uno.getComponentContext()
    smgr = ctx.ServiceManager
    desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    frame = desktop.getCurrentFrame()

    from com.sun.star.beans import PropertyValue
    msgbox = smgr.createInstanceWithContext(
        "com.sun.star.awt.Toolkit", ctx
    ).createMessageBox(
        frame.getContainerWindow(),
        1,  # ERRORBOX
        1,  # OK button
        "Hata",
        message
    )
    msgbox.execute()


# UNO component registration
g_ImplementationHelper = None

def createInstance(ctx):
    return None
```

---

## Geçiş Stratejisi

### Adım 1: Paralel Geliştirme
- Mevcut PyQt5 uygulamasını koruyarak OXT versiyonunu geliştir
- `/oxt` dizininde yeni yapıyı oluştur

### Adım 2: Core Modülleri Paylaş
```
libre_calc_ai_addon/
├── core/                    # Paylaşılan core modüller
├── llm/                     # Paylaşılan LLM modüller
├── ui/                      # PyQt5 UI (eski)
├── oxt/                     # OXT versiyonu
│   ├── CalcAI/
│   │   ├── ui/             # Tkinter UI (yeni)
│   │   ├── core/ → symlink → ../../core/
│   │   └── llm/ → symlink → ../../llm/
│   └── build_oxt.sh
└── main.py                  # Eski entry point
```

### Adım 3: Test Matrisi
| Test | PyQt5 | OXT |
|------|-------|-----|
| Bağlantı | ✓ Socket | ✓ Direct |
| Hücre okuma | ✓ | ✓ |
| Formül yazma | ✓ | ✓ |
| Stil uygulama | ✓ | ✓ |
| LLM çağrısı | ✓ | ✓ |
| Theme | ✓ | ✓ |
| i18n | ✓ | ✓ |

---

## Zaman Tahmini

| Faz | Süre | Açıklama |
|-----|------|----------|
| Faz 1: OXT İskeleti | 1-2 gün | Manifest, Addons.xcu, temel yapı |
| Faz 2: UNO Refaktör | 1 gün | Direct context kullanımı |
| Faz 3: UI Dönüşümü | 3-5 gün | Tkinter UI |
| Faz 4: Bundling | 1 gün | httpx, certifi vb. |
| Faz 5: Build/Test | 1-2 gün | Build script, test |
| **Toplam** | **7-11 gün** | |

---

## Riskler ve Çözümler

### Risk 1: LibreOffice Python'unda Tkinter yok
**Çözüm:**
- Linux: Genellikle mevcut
- Windows: LibreOffice ile gelen Python'da olmayabilir
- Alternatif: UNO native dialogs (sınırlı UI)

### Risk 2: httpx bundling sorunları
**Çözüm:**
- Pure Python alternatifi: `urllib.request` (stdlib)
- Veya `requests` (daha kolay bundling)

### Risk 3: Tkinter thread safety
**Çözüm:**
- LLM çağrıları için `threading.Thread`
- UI güncellemeleri için `after()` metodu

---

## Onay Bekleniyor

Bu planı onaylıyor musunuz? Onaylanırsa Faz 1 ile başlayacağım:
1. `/oxt` dizini oluştur
2. OXT iskelet dosyalarını oluştur
3. Basit "Hello World" OXT test et
