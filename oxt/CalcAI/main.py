"""LibreCalc AI - Ana giris noktasi (OXT icin).

Bu modul LibreOffice tarafindan cagirilir ve AI asistani baslatir.
"""

import logging
import sys
import os

# Logging yapilandirmasi
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# pythonpath dizinini sys.path'e ekle (bundled dependencies icin)
_this_dir = os.path.dirname(os.path.abspath(__file__))
_pythonpath = os.path.join(_this_dir, "pythonpath")
if os.path.exists(_pythonpath) and _pythonpath not in sys.path:
    sys.path.insert(0, _pythonpath)

# UNO imports
try:
    import uno
    from com.sun.star.beans import PropertyValue
    UNO_AVAILABLE = True
except ImportError:
    UNO_AVAILABLE = False
    logger.warning("UNO modulu bulunamadi - LibreOffice disinda calisiliyor olabilir")

# Tkinter import
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, scrolledtext
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False
    logger.warning("Tkinter modulu bulunamadi")

# Global pencere referansi (tekil pencere icin)
_assistant_window = None
_root = None


def get_uno_context():
    """UNO component context'i dondurur."""
    if not UNO_AVAILABLE:
        return None
    try:
        return uno.getComponentContext()
    except Exception as e:
        logger.error("UNO context alinamadi: %s", e)
        return None


def get_desktop(ctx=None):
    """Desktop servisini dondurur."""
    if ctx is None:
        ctx = get_uno_context()
    if ctx is None:
        return None
    try:
        smgr = ctx.ServiceManager
        return smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    except Exception as e:
        logger.error("Desktop servisi alinamadi: %s", e)
        return None


def show_uno_message(title: str, message: str, msg_type: int = 0):
    """UNO ile mesaj kutusu gosterir.

    Args:
        title: Baslik
        message: Mesaj
        msg_type: 0=INFO, 1=WARNING, 2=ERROR
    """
    ctx = get_uno_context()
    if ctx is None:
        print(f"[{title}] {message}")
        return

    try:
        desktop = get_desktop(ctx)
        if desktop is None:
            return

        frame = desktop.getCurrentFrame()
        if frame is None:
            return

        window = frame.getContainerWindow()
        if window is None:
            return

        smgr = ctx.ServiceManager
        toolkit = smgr.createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)

        # MessageBoxType: 0=MESSAGEBOX, 1=INFOBOX, 2=WARNINGBOX, 3=ERRORBOX, 4=QUERYBOX
        box_type = 1  # INFOBOX
        if msg_type == 1:
            box_type = 2  # WARNINGBOX
        elif msg_type == 2:
            box_type = 3  # ERRORBOX

        msgbox = toolkit.createMessageBox(
            window,
            box_type,
            1,  # OK button
            title,
            message
        )
        msgbox.execute()
    except Exception as e:
        logger.error("Mesaj kutusu gosterilemedi: %s", e)
        print(f"[{title}] {message}")


# ============================================================
# TKINTER UI COMPONENTS
# ============================================================

class AssistantWindow(tk.Toplevel):
    """AI Asistan ana penceresi (Tkinter)."""

    def __init__(self, parent, uno_ctx=None):
        super().__init__(parent)

        self.uno_ctx = uno_ctx
        self._setup_window()
        self._create_widgets()
        self._setup_bindings()
        self._setup_styles()

        logger.info("AssistantWindow olusturuldu")

    def _setup_window(self):
        """Pencere ozelliklerini ayarlar."""
        self.title("LibreCalc AI Asistan")

        # Boyut ve konum
        width = 350
        height = 650
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = screen_width - width - 50
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

        # Her zaman ustte
        self.attributes('-topmost', True)

        # Minimum boyut
        self.minsize(300, 400)

        # Stil (Ana arka plan)
        self.configure(bg='#2b2b2b')

    def _setup_styles(self):
        """Ozel stilleri tanimlar."""
        style = ttk.Style()
        style.theme_use('default')  # Tutarlilik icin default tema

        # Frame stilleri
        style.configure('Main.TFrame', background='#2b2b2b')
        style.configure('Status.TFrame', background='#2b2b2b')
        style.configure('Input.TFrame', background='#3c3c3c')  # Input container rengi

        # Label stilleri
        style.configure('Header.TLabel',
            background='#2b2b2b',
            foreground='#ffffff',
            font=('Segoe UI', 12, 'bold')
        )
        style.configure('Status.TLabel',
            background='#2b2b2b',
            foreground='#cccccc',
            font=('Segoe UI', 9)
        )
        style.configure('Info.TLabel',
            background='#2b2b2b',
            foreground='#888888',
            font=('Segoe UI', 8)
        )

        # Button stili (Flat ve modern)
        style.configure('Send.TButton',
            background='#007acc',  # VSCode mavi vurgu (veya benzeri)
            foreground='white',
            borderwidth=0,
            focuscolor='none',
            font=('Segoe UI', 9, 'bold')
        )
        style.map('Send.TButton',
            background=[('active', '#0098ff'), ('pressed', '#005a9e')]
        )

    def _create_widgets(self):
        """UI widget'larini olusturur."""
        # Ana frame (Padding ile icerigi ortalar)
        main_frame = ttk.Frame(self, style='Main.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Baslik (Daha sade)
        header_frame = ttk.Frame(main_frame, style='Main.TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 10))

        title_label = ttk.Label(
            header_frame,
            text="AI ASSISTANT",
            style='Header.TLabel'
        )
        title_label.pack(side=tk.LEFT)

        # Durum gostergesi (Kucuk nokta veya metin)
        self.status_label = ttk.Label(
            header_frame,
            text="Hazır",
            style='Status.TLabel'
        )
        self.status_label.pack(side=tk.RIGHT, anchor='center')

        # Mesaj alani (Flat gorunum)
        self.messages_text = scrolledtext.ScrolledText(
            main_frame,
            wrap=tk.WORD,
            font=('Segoe UI', 10),
            bg='#1e1e1e',     # Icerik alani rengi
            fg='#e0e0e0',     # Metin rengi
            insertbackground='white',
            state=tk.DISABLED,
            bd=0,             # Cercevesiz
            highlightthickness=0,
            padx=10,
            pady=10
        )
        self.messages_text.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Tag yapilandirmasi (Zengin metin icin)
        self.messages_text.tag_config('user_header', foreground='#4ec9b0', font=('Segoe UI', 9, 'bold'), spacing3=2)
        self.messages_text.tag_config('ai_header', foreground='#569cd6', font=('Segoe UI', 9, 'bold'), spacing3=2)
        self.messages_text.tag_config('content', foreground='#d4d4d4', lmargin1=10, lmargin2=10, spacing1=2, spacing3=10)
        self.messages_text.tag_config('system', foreground='#808080', font=('Segoe UI', 9, 'italic'))

        # Giris alani kapsayicisi (Kapsul gorunumlu)
        # Tkinter'da tam yuvarlak kose zordur, ama renk ile butunluk saglayabiliriz.
        input_container = ttk.Frame(main_frame, style='Input.TFrame')
        input_container.pack(fill=tk.X, ipady=5)

        # Giris alani
        self.input_text = tk.Text(
            input_container,
            wrap=tk.WORD,
            font=('Segoe UI', 10),
            bg='#3c3c3c',     # Container ile ayni renk
            fg='#ffffff',
            insertbackground='white',
            height=3,
            bd=0,
            highlightthickness=0,
            padx=10,
            pady=5
        )
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(2, 0))

        # Gonder butonu (Ikon yerine metin simdilik, ama stilize)
        self.send_button = ttk.Button(
            input_container,
            text="GÖNDER",
            style='Send.TButton',
            command=self._on_send,
            cursor="hand2"
        )
        self.send_button.pack(side=tk.RIGHT, padx=5, pady=5, fill=tk.Y)

        # Alt bilgi
        info_label = ttk.Label(
            main_frame,
            text="Ctrl+Enter ile gönder | ESC: Kapat",
            style='Info.TLabel'
        )
        info_label.pack(pady=(5, 0), anchor='e')

    def _setup_bindings(self):
        """Klavye kisayollarini ayarlar."""
        self.input_text.bind('<Control-Return>', lambda e: self._on_send())
        self.bind('<Escape>', lambda e: self._on_close())
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Input focus efekti (istege bagli - basitce bg degisimi yapilabilir ama su an gerek yok)

    def _add_message(self, text: str, sender: str = "system"):
        """Mesaj alanina formatli mesaj ekler."""
        self.messages_text.configure(state=tk.NORMAL)

        if sender == "user":
            self.messages_text.insert(tk.END, "SEN\n", 'user_header')
            self.messages_text.insert(tk.END, f"{text}\n\n", 'content')
        elif sender == "assistant":
            self.messages_text.insert(tk.END, "AI\n", 'ai_header')
            self.messages_text.insert(tk.END, f"{text}\n\n", 'content')
        else:
            self.messages_text.insert(tk.END, f"[Sistem] {text}\n\n", 'system')

        self.messages_text.see(tk.END)
        self.messages_text.configure(state=tk.DISABLED)

    def _on_send(self):
        """Mesaj gonderme islemi."""
        text = self.input_text.get("1.0", tk.END).strip()
        if not text:
            return

        # Kullanici mesajini ekle
        self._add_message(text, "user")
        self.input_text.delete("1.0", tk.END)

        # Durumu guncelle
        self.status_label.configure(text="Düşünüyor...")
        self.update()

        # TODO: LLM cagrisini burada yap
        # Simdilik placeholder yanit
        response = self._get_placeholder_response(text)

        # Yaniti ekle
        # Kisa bir gecikme simulasyonu (UI donmamasi icin after kullanilir normalde)
        self.after(100, lambda: self._complete_response(response))

    def _complete_response(self, response):
        self._add_message(response, "assistant")
        self.status_label.configure(text="Hazır")

    def _get_placeholder_response(self, user_text: str) -> str:
        """Placeholder yanit dondurur (test icin)."""
        # UNO baglantisini test et
        if "test" in user_text.lower():
            ctx = self.uno_ctx or get_uno_context()
            if ctx:
                try:
                    desktop = get_desktop(ctx)
                    if desktop:
                        doc = desktop.getCurrentComponent()
                        if doc:
                            try:
                                title = doc.getTitle()
                            except:
                                title = "Adsız"
                            return f"LibreOffice bağlantısı başarılı!\nAktif Belge: {title}"
                except Exception as e:
                    return f"LibreOffice bağlantısı hatası: {e}"
            return "UNO context mevcut değil. (LibreOffice harici çalışıyor olabilir)"

        # Standart echo
        return f"Mesajını aldım: '{user_text}'\n\nBu henüz geliştirme aşamasındaki bir arayüzdür. Gerçek AI entegrasyonu eklenecektir."

    def _on_close(self):
        """Pencereyi kapatir."""
        global _assistant_window
        _assistant_window = None
        self.destroy()


# ============================================================
# LIBRE OFFICE ENTRY POINTS
# ============================================================

def show_assistant(*args):
    """AI Asistan penceresini gosterir.

    Bu fonksiyon LibreOffice menu/toolbar'dan cagirilir.
    """
    global _assistant_window, _root

    logger.info("show_assistant cagirildi")

    if not TKINTER_AVAILABLE:
        show_uno_message(
            "Hata",
            "Tkinter modulu bulunamadi. "
            "Lutfen Python Tkinter paketini kurun.",
            msg_type=2
        )
        return

    try:
        # Pencere zaten aciksa one getir
        if _assistant_window is not None:
            try:
                if _assistant_window.winfo_exists():
                    _assistant_window.lift()
                    _assistant_window.focus_force()
                    return
            except tk.TclError:
                _assistant_window = None

        # Root penceresi yoksa olustur
        if _root is None or not _root.winfo_exists():
            _root = tk.Tk()
            _root.withdraw()  # Ana pencereyi gizle

        # UNO context'i al
        uno_ctx = get_uno_context()

        # Asistan penceresini olustur
        _assistant_window = AssistantWindow(_root, uno_ctx)

        # Tkinter event loop'u baslat (non-blocking)
        _assistant_window.mainloop()

    except Exception as e:
        logger.exception("Asistan penceresi acilamadi")
        show_uno_message("Hata", f"Asistan acilamadi: {e}", msg_type=2)


def show_settings(*args):
    """Ayarlar dialogunu gosterir."""
    logger.info("show_settings cagirildi")
    show_uno_message(
        "Ayarlar",
        "Ayarlar penceresi henuz hazir degil.\n\nYakin zamanda eklenecek.",
        msg_type=0
    )


def show_about(*args):
    """Hakkinda dialogunu gosterir."""
    logger.info("show_about cagirildi")
    show_uno_message(
        "LibreCalc AI Asistan",
        "Surum: 1.0.0\n\n"
        "LibreOffice Calc icin AI destekli asistan.\n\n"
        "Gelistirici: Aras\n"
        "Lisans: MIT",
        msg_type=0
    )


# ============================================================
# UNO COMPONENT REGISTRATION (gerekirse)
# ============================================================

# LibreOffice Python script'leri icin g_exportedScripts gerekli
g_exportedScripts = (show_assistant, show_settings, show_about)


# Test icin dogrudan calistirma
if __name__ == "__main__":
    print("LibreCalc AI - Test modu")
    print("=" * 40)

    if not TKINTER_AVAILABLE:
        print("HATA: Tkinter bulunamadi!")
        sys.exit(1)

    # Test penceresi ac
    root = tk.Tk()
    root.withdraw()

    window = AssistantWindow(root, None)
    window._add_message("Test modunda calisiyorsunuz.", "system")

    window.mainloop()
