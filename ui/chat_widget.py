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
    QFrame,
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
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 12px;
                padding: 4px;
            }
        """)
        
        input_v_layout = QVBoxLayout(input_container)
        input_v_layout.setContentsMargins(8, 8, 8, 8)
        input_v_layout.setSpacing(8)

        self._input_edit = QTextEdit()
        self._input_edit.setPlaceholderText("Claude'a bir şunları sor... (Ctrl+Enter)")
        self._input_edit.setFixedHeight(80)
        self._input_edit.setFrameShape(QFrame.NoFrame)
        self._input_edit.setStyleSheet("background-color: transparent; border: none;")
        self._input_edit.setAcceptRichText(False)
        input_v_layout.addWidget(self._input_edit)

        input_h_layout = QHBoxLayout()
        input_h_layout.addStretch()

        self._clear_btn = QPushButton("Temizle")
        self._clear_btn.setFlat(True)
        self._clear_btn.setStyleSheet("""
            QPushButton { 
                background-color: transparent; 
                color: #9ca3af; 
                font-weight: normal;
                padding: 4px 8px;
            }
            QPushButton:hover { color: #e5e7eb; }
        """)
        self._clear_btn.clicked.connect(self.clear_chat)
        input_h_layout.addWidget(self._clear_btn)

        self._send_btn = QPushButton("Gönder")
        self._send_btn.setFixedWidth(80)
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
        """Sohbete yeni mesaj baloncugu ekler.

        Args:
            role: Mesaj rolu ("user" veya "assistant").
            content: Mesaj metni.
        """
        wrapper = QWidget()
        v_layout = QVBoxLayout(wrapper)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(4)

        # Header (Role Name)
        header = QLabel()
        header.setStyleSheet("color: #9ca3af; font-weight: bold; font-size: 11px; text-transform: uppercase;")
        
        bubble = QLabel()
        bubble.setWordWrap(True)
        bubble.setTextFormat(Qt.RichText)
        bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        if role == "user":
            header.setText("SİZ")
            bubble.setObjectName("user_bubble")
            bubble.setText(content.replace("\n", "<br>"))
            v_layout.addWidget(header, 0, Qt.AlignRight)
            v_layout.addWidget(bubble, 0, Qt.AlignRight)
            bubble.setMaximumWidth(320)
        else:
            header.setText("CLAUDE")
            header.setStyleSheet("color: #D97757; font-weight: bold; font-size: 11px; text-transform: uppercase;")
            bubble.setObjectName("ai_bubble")
            bubble.setText(_markdown_to_html(content))
            bubble.setOpenExternalLinks(True)
            v_layout.addWidget(header, 0, Qt.AlignLeft)
            v_layout.addWidget(bubble, 0, Qt.AlignLeft)
            bubble.setMinimumWidth(300)

        # Stretch'ten once ekle (stretch her zaman son eleman)
        count = self._messages_layout.count()
        self._messages_layout.insertWidget(count - 1, wrapper)

        # Otomatik en alta kaydir
        QTimer.singleShot(100, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        """Mesaj alanini en alta kaydirir."""
        sb = self._scroll_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def show_loading(self):
        """Yukleniyor gostergesi mi baslatir."""
        self._loading_dots = 0
        self._loading_label.setText("Claude düşünüyor")
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
        self._loading_label.setText(f"Claude düşünüyor{dots}")

    def clear_chat(self):
        """Tum mesajlari temizler."""
        while self._messages_layout.count() > 1:
            item = self._messages_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def set_input_enabled(self, enabled: bool):
        """Giris alanini ve gonder butonunu etkinlestirir/devre disi birakir.

        Args:
            enabled: True ise etkin, False ise devre disi.
        """
        self._input_edit.setEnabled(enabled)
        self._send_btn.setEnabled(enabled)
        self._clear_btn.setEnabled(enabled)
