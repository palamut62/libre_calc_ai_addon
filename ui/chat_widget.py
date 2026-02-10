"""Sohbet arayuzu - Kullanici ve AI mesaj baloncuklari ile giris alani."""

import re

from PyQt5.QtCore import pyqtSignal, Qt, QTimer
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QLabel,
    QTextEdit,
    QPushButton,
    QSizePolicy,
    QPushButton,
    QSizePolicy,
    QFrame,
    QTextBrowser,
)


def _markdown_to_html(text: str) -> str:
    """Basit Markdown metnini HTML'e donusturur.

    Desteklenen formatlar: **kalin**, *italik*, `satir ici kod`, ```kod blogu```.

    Args:
        text: Markdown formatinda metin.

    Returns:
        HTML formatinda metin.
    """
    # Kod bloklari (``` ... ```)
    def _replace_code_block(m):
        code = m.group(1).strip()
        code = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return (
            '<pre style="background-color: rgba(0,0,0,0.2); padding: 8px; '
            'border-radius: 4px; font-family: monospace; white-space: pre-wrap;">'
            f"{code}</pre>"
        )

    text = re.sub(r"```(?:\w*\n)?(.*?)```", _replace_code_block, text, flags=re.DOTALL)

    # Satir ici kod (`...`)
    def _replace_inline_code(m):
        code = m.group(1)
        code = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return (
            '<code style="background-color: rgba(0,0,0,0.15); padding: 1px 4px; '
            f'border-radius: 3px; font-family: monospace;">{code}</code>'
        )

    text = re.sub(r"`([^`]+)`", _replace_inline_code, text)

    # Kalin (**...**)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)

    # Italik (*...*)
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<i>\1</i>", text)

    # Satir sonlari
    text = text.replace("\n", "<br>")

    return text


class ChatWidget(QWidget):
    """Sohbet arayuzu bileseni.

    Kullanici ve AI mesajlarini baloncuklar halinde gosterir,
    mesaj girisi ve gonderme islevi saglar.
    """

    message_sent = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loading_label = None
        self._loading_timer = None
        self._loading_dots = 0
        self._setup_ui()

    def _setup_ui(self):
        """Arayuz elemanlarini olusturur ve yerlestirir."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Mesaj alani
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setFrameShape(QFrame.NoFrame)

        self._messages_widget = QWidget()
        self._messages_layout = QVBoxLayout(self._messages_widget)
        self._messages_layout.setContentsMargins(0, 0, 0, 0)
        self._messages_layout.setSpacing(24)
        self._messages_layout.addStretch()

        self._scroll_area.setWidget(self._messages_widget)
        layout.addWidget(self._scroll_area, 1)

        # Yukleniyor gostergesi
        self._loading_label = QLabel("")
        self._loading_label.setObjectName("loading_label")
        self._loading_label.setVisible(False)
        layout.addWidget(self._loading_label)

        self._loading_timer = QTimer(self)
        self._loading_timer.setInterval(400)
        self._loading_timer.timeout.connect(self._animate_loading)

        # Prompt Box Container
        input_container = QFrame()
        input_container.setObjectName("input_container")
        input_container.setStyleSheet("""
            QFrame#input_container {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 8px;
                padding: 4px;
            }
        """)
        
        input_v_layout = QVBoxLayout(input_container)
        input_v_layout.setContentsMargins(12, 12, 12, 12)
        input_v_layout.setSpacing(8)

        self._input_edit = QTextEdit()
        self._input_edit.setPlaceholderText("Aras ile konuşun... (Ctrl+Enter)")
        self._input_edit.setFixedHeight(70)
        self._input_edit.setFrameShape(QFrame.NoFrame)
        self._input_edit.setStyleSheet("background-color: transparent; border: none; font-size: 14px; color: #000000;")
        self._input_edit.setAcceptRichText(False)
        input_v_layout.addWidget(self._input_edit)

        input_h_layout = QHBoxLayout()
        input_h_layout.addStretch()

        self._clear_btn = QPushButton("Temizle")
        self._clear_btn.setFlat(True)
        self._clear_btn.setCursor(Qt.PointingHandCursor)
        self._clear_btn.setStyleSheet("""
            QPushButton { 
                background-color: transparent; 
                color: #666666; 
                font-weight: 500;
                padding: 6px 12px;
            }
            QPushButton:hover { color: #000000; background-color: #eeeeee; border-radius: 4px; }
        """)
        self._clear_btn.clicked.connect(self.clear_chat)
        input_h_layout.addWidget(self._clear_btn)

        self._send_btn = QPushButton("Gönder")
        self._send_btn.setFixedWidth(100)
        self._send_btn.setCursor(Qt.PointingHandCursor)
        self._send_btn.clicked.connect(self._on_send)
        input_h_layout.addWidget(self._send_btn)

        input_v_layout.addLayout(input_h_layout)
        layout.addWidget(input_container)

    def keyPressEvent(self, event):
        """Ctrl+Enter ile mesaj gondermeyi yakalar."""
        if (
            event.key() in (Qt.Key_Return, Qt.Key_Enter)
            and event.modifiers() & Qt.ControlModifier
        ):
            self._on_send()
        else:
            super().keyPressEvent(event)

    def _on_send(self):
        """Kullanici mesajini gonderir."""
        text = self._input_edit.toPlainText().strip()
        if not text:
            return
        self._input_edit.clear()
        self.message_sent.emit(text)

    def add_message(self, role: str, content: str):
        """Sohbete yeni mesaj baloncugu ekler."""
        wrapper = QWidget()
        v_layout = QVBoxLayout(wrapper)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(6)

        header = QLabel()
        header.setStyleSheet("color: #64748b; font-weight: 700; font-size: 10px; letter-spacing: 0.5px;")
        
        bubble = QTextBrowser()
        bubble.setFrameShape(QFrame.NoFrame)
        bubble.setOpenExternalLinks(True)
        bubble.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        bubble.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # Word wrap ayarları
        bubble.setLineWrapMode(QTextBrowser.WidgetWidth)
        
        if role == "user":
            header.setText("SİZ")
            bubble.setObjectName("user_bubble")
            bubble.setHtml(f'<div style="line-height: 1.4;">{content.replace("\n", "<br>")}</div>')
            
            v_layout.addWidget(header, 0, Qt.AlignRight)
            v_layout.addWidget(bubble, 0, Qt.AlignRight)
            bubble.setFixedWidth(280)
        else:
            header.setText("ARAS")
            header.setStyleSheet("color: #18a303; font-weight: 700; font-size: 10px; letter-spacing: 0.5px;")
            bubble.setObjectName("ai_bubble")
            bubble.setHtml(f'<div style="line-height: 1.5;">{_markdown_to_html(content)}</div>')
            
            v_layout.addWidget(header, 0, Qt.AlignLeft)
            v_layout.addWidget(bubble, 0, Qt.AlignLeft)
            bubble.setFixedWidth(320)

        # Dinamik yükseklik hesaplama
        doc = bubble.document()
        doc.setTextWidth(bubble.width())
        # Yüksekliği içeriğe göre ayarla (biraz buffer ekle)
        height = doc.size().height() + 24
        bubble.setFixedHeight(int(height))

        count = self._messages_layout.count()
        self._messages_layout.insertWidget(count - 1, wrapper)

        QTimer.singleShot(100, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        """Mesaj alanini en alta kaydirir."""
        sb = self._scroll_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def show_loading(self):
        """Yukleniyor gostergesi mi baslatir."""
        self._loading_dots = 0
        self._loading_label.setText("Aras düşünüyor")
        self._loading_label.setVisible(True)
        self._loading_timer.start()

    def hide_loading(self):
        """Yukleniyor gostergesini gizler."""
        self._loading_timer.stop()
        self._loading_label.setVisible(False)

    def _animate_loading(self):
        """Yukleniyor animasyonunu gunceller."""
        self._loading_dots = (self._loading_dots + 1) % 4
        dots = "." * self._loading_dots
        self._loading_label.setText(f"Aras düşünüyor{dots}")

    def clear_chat(self):
        """Tum mesajlari temizler."""
        while self._messages_layout.count() > 1:
            item = self._messages_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def set_input_enabled(self, enabled: bool):
        """Giris alanini ve gonder butonunu etkinlestirir/devre disi birakir."""
        self._input_edit.setEnabled(enabled)
        self._send_btn.setEnabled(enabled)
        self._clear_btn.setEnabled(enabled)

    def update_theme(self, theme_name: str):
        """Chat bilesenlerinin temasini gunceller."""
        is_dark = theme_name == "dark"
        
        # Input container
        bg_color = "#1e293b" if is_dark else "#ffffff"
        border_color = "#334155" if is_dark else "#cccccc"
        text_color = "#f3f4f6" if is_dark else "#000000"
        placeholder_color = "#94a3b8" if is_dark else "#666666"
        btn_hover_bg = "#334155" if is_dark else "#eeeeee"
        
        self.findChild(QFrame, "input_container").setStyleSheet(f"""
            QFrame#input_container {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 4px;
            }}
        """)
        
        self._input_edit.setStyleSheet(f"background-color: transparent; border: none; font-size: 14px; color: {text_color};")
        
        self._clear_btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: transparent; 
                color: {placeholder_color}; 
                font-weight: 500;
                padding: 6px 12px;
            }}
            QPushButton:hover {{ color: {text_color}; background-color: {btn_hover_bg}; border-radius: 4px; }}
        """)

    def update_language(self, lang: str):
        """Chat bilesenlerinin dilini gunceller."""
        from .i18n import get_text
        
        self._input_edit.setPlaceholderText(get_text("chat_placeholder", lang))
        self._send_btn.setText(get_text("chat_send", lang))
        self._clear_btn.setText(get_text("chat_clear", lang))
        
        # Loading metni degiskenini guncelle (eger varsa)
        # Not: Loading animasyonu ozel oldugu icin anlik degismeyebilir ama sonraki sefer icin guncellenir
