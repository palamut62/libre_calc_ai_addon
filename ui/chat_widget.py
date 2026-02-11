"""Sohbet arayuzu - Kullanici ve AI mesaj baloncuklari ile giris alani."""

import re

from PyQt5.QtCore import pyqtSignal, Qt, QTimer
from PyQt5.QtWidgets import QListWidget, QListWidgetItem
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
    QTextBrowser,
)

from .icons import get_icon


def _markdown_to_html(text: str) -> str:
    """Basit Markdown metnini HTML'e donusturur.

    Desteklenen formatlar: **kalin**, *italik*, `satir ici kod`, ```kod blogu```.

    Args:
        text: Markdown formatinda metin.

    Returns:
        HTML formatinda metin.
    """
    def _escape_html(value: str) -> str:
        return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _parse_markdown_table(lines: list[str]) -> tuple[str | None, int]:
        """Markdown tablo bloğunu yakalayıp HTML üretir."""
        if len(lines) < 2:
            return None, 0
        header = lines[0]
        sep = lines[1]
        if "|" not in header:
            return None, 0
        if not re.match(r'^\s*\|?(\s*:?-+:?\s*\|)+\s*$', sep):
            return None, 0

        def _split_row(row: str) -> list[str]:
            row = row.strip()
            if row.startswith("|"):
                row = row[1:]
            if row.endswith("|"):
                row = row[:-1]
            return [c.strip() for c in row.split("|")]

        headers = _split_row(header)
        aligns = []
        for part in _split_row(sep):
            left = part.startswith(":")
            right = part.endswith(":")
            if left and right:
                aligns.append("center")
            elif right:
                aligns.append("right")
            else:
                aligns.append("left")

        body_rows = []
        consumed = 2
        for line in lines[2:]:
            if "|" not in line:
                break
            body_rows.append(_split_row(line))
            consumed += 1

        # Normalize column count
        col_count = max(len(headers), *(len(r) for r in body_rows)) if body_rows else len(headers)
        headers += [""] * (col_count - len(headers))
        aligns += ["left"] * (col_count - len(aligns))
        for i, r in enumerate(body_rows):
            if len(r) < col_count:
                body_rows[i] = r + [""] * (col_count - len(r))

        table_parts = [
            "<table style=\"width:100%; border-collapse: collapse; margin: 6px 0;\">",
            "<thead><tr>",
        ]
        for i, h in enumerate(headers):
            table_parts.append(
                f"<th style=\"text-align:{aligns[i]}; border:1px solid rgba(0,0,0,0.15); padding:6px; "
                f"background: rgba(0,0,0,0.08);\">{_escape_html(h)}</th>"
            )
        table_parts.append("</tr></thead><tbody>")
        for row in body_rows:
            table_parts.append("<tr>")
            for i, cell in enumerate(row):
                table_parts.append(
                    f"<td style=\"text-align:{aligns[i]}; border:1px solid rgba(0,0,0,0.12); padding:6px;\">"
                    f"{_escape_html(cell)}</td>"
                )
            table_parts.append("</tr>")
        table_parts.append("</tbody></table>")
        return "".join(table_parts), consumed

    # Önce tabloları çıkar
    lines = text.splitlines()
    out_lines = []
    tables = []
    i = 0
    while i < len(lines):
        html_table, consumed = _parse_markdown_table(lines[i:])
        if html_table:
            token = f"__TABLE_{len(tables)}__"
            tables.append(html_table)
            out_lines.append(token)
            i += consumed
            continue
        out_lines.append(lines[i])
        i += 1
    text = "\n".join(out_lines)

    # Kod bloklari (``` ... ```)
    def _replace_code_block(m):
        code = m.group(1).strip()
        code = _escape_html(code)
        return (
            '<pre style="background-color: rgba(0,0,0,0.2); padding: 8px; '
            'border-radius: 4px; font-family: monospace; white-space: pre-wrap;">'
            f"{code}</pre>"
        )

    text = re.sub(r"```(?:\w*\n)?(.*?)```", _replace_code_block, text, flags=re.DOTALL)

    # Satir ici kod (`...`)
    def _replace_inline_code(m):
        code = m.group(1)
        code = _escape_html(code)
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

    # Tablo placeholderlarini geri koy
    for idx, table_html in enumerate(tables):
        text = text.replace(f"__TABLE_{idx}__", table_html)

    return text


class ChatWidget(QWidget):
    """Sohbet arayuzu bileseni.

    Kullanici ve AI mesajlarini baloncuklar halinde gosterir,
    mesaj girisi ve gonderme islevi saglar.
    """

    message_sent = pyqtSignal(str)
    cancel_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loading_label = None
        self._loading_timer = None
        self._loading_dots = 0
        self._provider_name = ""
        self._model_name = ""
        self._current_lang = "system"
        self._stream_bubble = None
        self._stream_role = None
        self._stream_wrapper = None
        self._is_generating = False
        self._slash_commands = []

        # Stream debounce için
        self._scroll_debounce_timer = QTimer(self)
        self._scroll_debounce_timer.setSingleShot(True)
        self._scroll_debounce_timer.setInterval(100)  # 100ms debounce
        self._scroll_debounce_timer.timeout.connect(self._scroll_to_bottom)
        self._pending_stream_content = None

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

        self._provider_model_label = QLabel("")
        self._provider_model_label.setObjectName("provider_model_label")
        self._provider_model_label.setStyleSheet("color: #64748b; font-size: 11px;")
        input_v_layout.addWidget(self._provider_model_label)

        self._slash_hint_label = QLabel("")
        self._slash_hint_label.setObjectName("slash_hint_label")
        self._slash_hint_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        input_v_layout.addWidget(self._slash_hint_label)

        self._input_edit = QTextEdit()
        self._input_edit.setPlaceholderText("ArasAI ile konuşun... (Ctrl+Enter)")
        self._input_edit.setFixedHeight(70)
        self._input_edit.setFrameShape(QFrame.NoFrame)
        self._input_edit.setStyleSheet("background-color: transparent; border: none; font-size: 14px; color: #000000;")
        self._input_edit.setAcceptRichText(False)
        self._input_edit.textChanged.connect(self._on_input_changed)
        input_v_layout.addWidget(self._input_edit)

        self._slash_list = QListWidget()
        self._slash_list.setObjectName("slash_list")
        self._slash_list.setVisible(False)
        self._slash_list.setFixedHeight(120)
        self._slash_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._slash_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._slash_list.itemClicked.connect(self._on_slash_item_clicked)
        input_v_layout.addWidget(self._slash_list)

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

        self._action_btn = QPushButton("")
        self._action_btn.setFixedSize(36, 32)
        self._action_btn.setCursor(Qt.PointingHandCursor)
        self._action_btn.setIcon(get_icon("send", self))
        self._action_btn.clicked.connect(self._on_action_clicked)
        input_h_layout.addWidget(self._action_btn)

        input_v_layout.addLayout(input_h_layout)
        layout.addWidget(input_container)

    def keyPressEvent(self, event):
        """Ctrl+Enter ile mesaj gondermeyi yakalar."""
        if self._slash_list.isVisible():
            if event.key() in (Qt.Key_Up, Qt.Key_Down):
                self._navigate_slash_list(event.key())
                return
            if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab):
                self._apply_slash_selection()
                return
            if event.key() == Qt.Key_Escape:
                self._slash_list.setVisible(False)
                return

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

    def _on_cancel(self):
        """Kullanici iptal istedi."""
        self.cancel_requested.emit()

    def add_message(self, role: str, content: str):
        """Sohbete yeni mesaj baloncugu ekler."""
        bubble, _wrapper = self._create_message_bubble(role, content)
        if bubble:
            QTimer.singleShot(100, self._scroll_to_bottom)
        return bubble

    def start_stream_message(self, role: str):
        """Stream mesajı için boş baloncuk başlatır."""
        self._stream_role = role
        bubble, wrapper = self._create_message_bubble(role, "")
        self._stream_bubble = bubble
        self._stream_wrapper = wrapper
        return self._stream_bubble

    def update_stream_message(self, content: str):
        """Stream mesaj baloncuğunu günceller (debounced scroll)."""
        if not self._stream_bubble or not self._stream_role:
            return
        self._set_bubble_content(self._stream_bubble, self._stream_role, content)
        # Debounce: Çok sık scroll yapmak yerine timer ile bekle
        if not self._scroll_debounce_timer.isActive():
            self._scroll_debounce_timer.start()

    def end_stream_message(self):
        """Stream mesajını sonlandırır."""
        self._stream_bubble = None
        self._stream_role = None
        self._stream_wrapper = None

    def discard_stream_message(self):
        """Stream baloncuğunu kaldırır."""
        if self._stream_wrapper:
            self._stream_wrapper.deleteLater()
        self._stream_bubble = None
        self._stream_role = None
        self._stream_wrapper = None

    def _create_message_bubble(self, role: str, content: str):
        """Mesaj baloncuğu oluşturur ve yerleştirir."""
        wrapper = QWidget()
        v_layout = QVBoxLayout(wrapper)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(6)

        from .i18n import get_text

        header = QLabel()
        header.setStyleSheet("color: #94a3b8; font-weight: 700; font-size: 10px; letter-spacing: 0.6px;")

        bubble = QTextBrowser()
        bubble.setFrameShape(QFrame.NoFrame)
        bubble.setOpenExternalLinks(True)
        bubble.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        bubble.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        bubble.setLineWrapMode(QTextBrowser.WidgetWidth)

        if role == "user":
            header.setText(get_text("chat_you", self._current_lang))
            bubble.setObjectName("user_bubble")
            v_layout.addWidget(header, 0, Qt.AlignRight)
            v_layout.addWidget(bubble, 0, Qt.AlignRight)
            bubble.setFixedWidth(280)
        else:
            header.setText(get_text("chat_aras", self._current_lang))
            header.setStyleSheet("color: #22c55e; font-weight: 700; font-size: 10px; letter-spacing: 0.6px;")
            bubble.setObjectName("ai_bubble")
            v_layout.addWidget(header, 0, Qt.AlignLeft)
            v_layout.addWidget(bubble, 0, Qt.AlignLeft)
            bubble.setFixedWidth(320)

        self._set_bubble_content(bubble, role, content)

        count = self._messages_layout.count()
        self._messages_layout.insertWidget(count - 1, wrapper)
        return bubble, wrapper

    def _set_bubble_content(self, bubble: QTextBrowser, role: str, content: str):
        """Baloncuk içeriğini ayarlar ve yüksekliği günceller."""
        if role == "user":
            safe = content.replace("\n", "<br>")
            bubble.setHtml(f'<div style="line-height: 1.4;">{safe}</div>')
        else:
            bubble.setHtml(f'<div style="line-height: 1.5;">{_markdown_to_html(content)}</div>')

        doc = bubble.document()
        doc.setTextWidth(bubble.width())
        height = doc.size().height() + 24
        bubble.setFixedHeight(int(height))

    def _scroll_to_bottom(self):
        """Mesaj alanini en alta kaydirir."""
        sb = self._scroll_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def show_loading(self):
        """Yukleniyor gostergesi mi baslatir."""
        from .i18n import get_text

        self._loading_dots = 0
        self._loading_label.setText(get_text("chat_thinking", self._current_lang))
        self._loading_label.setVisible(True)
        self._loading_timer.start()

    def hide_loading(self):
        """Yukleniyor gostergesini gizler."""
        self._loading_timer.stop()
        self._loading_label.setVisible(False)

    def _animate_loading(self):
        """Yukleniyor animasyonunu gunceller."""
        from .i18n import get_text

        self._loading_dots = (self._loading_dots + 1) % 4
        dots = "." * self._loading_dots
        base_text = get_text("chat_thinking", self._current_lang)
        self._loading_label.setText(f"{base_text}{dots}")

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
        if not self._is_generating:
            self._action_btn.setEnabled(enabled)
        self._clear_btn.setEnabled(enabled)

    def set_generating(self, generating: bool):
        """Stream durumuna göre durdur butonunu yönetir."""
        self._is_generating = generating
        if generating:
            self._action_btn.setIcon(get_icon("stop", self))
            self._action_btn.setToolTip(self._stop_tooltip)
            self._action_btn.setEnabled(True)
            if hasattr(self, "_action_stop_style"):
                self._action_btn.setStyleSheet(self._action_stop_style)
        else:
            self._action_btn.setIcon(get_icon("send", self))
            self._action_btn.setToolTip(self._send_tooltip)
            if hasattr(self, "_action_send_style"):
                self._action_btn.setStyleSheet(self._action_send_style)

    def update_theme(self, theme_name: str):
        """Chat bilesenlerinin temasini gunceller."""
        is_dark = theme_name == "dark"
        
        # Input container
        bg_color = "#0b1220" if is_dark else "#ffffff"
        border_color = "#1f2937" if is_dark else "#e2e8f0"
        text_color = "#e2e8f0" if is_dark else "#0f172a"
        placeholder_color = "#94a3b8" if is_dark else "#64748b"
        btn_hover_bg = "#111827" if is_dark else "#e2e8f0"
        provider_label_color = "#94a3b8" if is_dark else "#64748b"
        hint_color = "#94a3b8" if is_dark else "#64748b"
        list_bg = "#0b1220" if is_dark else "#ffffff"
        list_border = "#1f2937" if is_dark else "#e2e8f0"
        list_text = "#e2e8f0" if is_dark else "#0f172a"
        stop_bg = "#ef4444" if is_dark else "#ef4444"
        stop_hover = "#dc2626" if is_dark else "#dc2626"
        send_bg = "#22c55e" if is_dark else "#22c55e"
        send_hover = "#16a34a" if is_dark else "#16a34a"
        
        self.findChild(QFrame, "input_container").setStyleSheet(f"""
            QFrame#input_container {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 4px;
            }}
        """)
        
        self._input_edit.setStyleSheet(f"background-color: transparent; border: none; font-size: 14px; color: {text_color};")
        self._provider_model_label.setStyleSheet(f"color: {provider_label_color}; font-size: 11px;")
        self._slash_hint_label.setStyleSheet(f"color: {hint_color}; font-size: 11px;")
        
        self._clear_btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: transparent; 
                color: {placeholder_color}; 
                font-weight: 500;
                padding: 6px 12px;
            }}
            QPushButton:hover {{ color: {text_color}; background-color: {btn_hover_bg}; border-radius: 4px; }}
        """)

        self._action_send_style = f"""
            QPushButton {{
                background-color: {send_bg};
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 6px 10px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {send_hover}; }}
        """
        self._action_stop_style = f"""
            QPushButton {{
                background-color: {stop_bg};
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 6px 10px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {stop_hover}; }}
        """
        self._action_btn.setStyleSheet(
            self._action_stop_style if self._is_generating else self._action_send_style
        )

        self._slash_list.setStyleSheet(f"""
            QListWidget#slash_list {{
                background-color: {list_bg};
                color: {list_text};
                border: 1px solid {list_border};
                border-radius: 6px;
                padding: 4px;
            }}
            QListWidget#slash_list::item {{
                padding: 6px 8px;
                border-radius: 4px;
            }}
            QListWidget#slash_list::item:selected {{
                background-color: {btn_hover_bg};
            }}
        """)

    def update_language(self, lang: str):
        """Chat bilesenlerinin dilini gunceller."""
        from .i18n import get_text

        self._current_lang = lang
        self._input_edit.setPlaceholderText(get_text("chat_placeholder", lang))
        self._send_tooltip = get_text("chat_send", lang)
        self._clear_btn.setText(get_text("chat_clear", lang))
        self._stop_tooltip = get_text("chat_stop", lang)
        self._action_btn.setToolTip(self._stop_tooltip if self._is_generating else self._send_tooltip)
        self._slash_hint_label.setText(get_text("chat_slash_hint", lang))
        self._build_slash_commands()
        self._slash_list.setVisible(False)
        self._update_provider_model_label()

    def _on_action_clicked(self):
        """Gönder veya durdur aksiyonu."""
        if self._is_generating:
            self._on_cancel()
        else:
            self._on_send()

    def _build_slash_commands(self):
        from .i18n import get_text

        self._slash_commands = [
            ("/analiz", get_text("cmd_desc_analyze", self._current_lang)),
            ("/baglan", get_text("cmd_desc_connect", self._current_lang)),
            ("/profil", get_text("cmd_desc_profile", self._current_lang)),
            ("/dogrula", get_text("cmd_desc_validate", self._current_lang)),
            ("/gecmis", get_text("cmd_desc_changes", self._current_lang)),
            ("/geri", get_text("cmd_desc_undo", self._current_lang)),
            ("/temizle", get_text("cmd_desc_clear", self._current_lang)),
            ("/help", get_text("cmd_help_header", self._current_lang)),
        ]

    def _on_input_changed(self):
        text = self._input_edit.toPlainText()
        if not text.startswith("/"):
            self._slash_list.setVisible(False)
            return
        self._update_slash_list(text.strip())

    def _update_slash_list(self, query: str):
        self._slash_list.clear()
        prefix = query.split()[0] if query else ""
        matches = []
        for cmd, desc in self._slash_commands:
            if not prefix or cmd.startswith(prefix):
                matches.append((cmd, desc))

        if not matches:
            self._slash_list.setVisible(False)
            return

        for cmd, desc in matches:
            item = QListWidgetItem(f"{cmd} — {desc}")
            item.setData(Qt.UserRole, cmd)
            self._slash_list.addItem(item)

        self._slash_list.setCurrentRow(0)
        self._slash_list.setVisible(True)

    def _navigate_slash_list(self, key):
        row = self._slash_list.currentRow()
        if key == Qt.Key_Up:
            row = max(0, row - 1)
        else:
            row = min(self._slash_list.count() - 1, row + 1)
        self._slash_list.setCurrentRow(row)

    def _apply_slash_selection(self):
        item = self._slash_list.currentItem()
        if not item:
            return
        cmd = item.data(Qt.UserRole)
        self._input_edit.setPlainText(cmd + " ")
        cursor = self._input_edit.textCursor()
        cursor.movePosition(cursor.End)
        self._input_edit.setTextCursor(cursor)
        self._slash_list.setVisible(False)

    def _on_slash_item_clicked(self, item):
        self._apply_slash_selection()
        
        # Loading metni degiskenini guncelle (eger varsa)
        # Not: Loading animasyonu ozel oldugu icin anlik degismeyebilir ama sonraki sefer icin guncellenir

    def update_provider_model(self, provider_name: str, model_name: str):
        """Saglayici ve model bilgisini gunceller."""
        self._provider_name = provider_name
        self._model_name = model_name
        self._update_provider_model_label()

    def _update_provider_model_label(self):
        """Saglayici/model etiketini gunceller."""
        if not self._provider_name or not self._model_name:
            self._provider_model_label.setText("")
            return

        from .i18n import get_text
        text = get_text("chat_provider_model", self._current_lang).format(
            provider=self._provider_name,
            model=self._model_name,
        )
        self._provider_model_label.setText(text)
