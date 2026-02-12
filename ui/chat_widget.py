"""Sohbet arayuzu - Minimal chat widget (Claude Excel benzeri)."""

import html
import re

from PyQt5.QtCore import pyqtSignal, Qt, QTimer, QSize
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QLabel,
    QTextEdit,
    QPushButton,
    QFrame,
    QTextBrowser,
)

from .icons import get_icon


def _markdown_to_html(text: str, theme_name: str = "dark") -> str:
    """Basit Markdown metnini HTML'e donusturur."""
    is_dark = theme_name == "dark"
    table_header_bg = "rgba(255,255,255,0.08)" if is_dark else "rgba(0,0,0,0.08)"
    table_border = "rgba(255,255,255,0.18)" if is_dark else "rgba(0,0,0,0.14)"
    code_bg = "rgba(255,255,255,0.10)" if is_dark else "rgba(0,0,0,0.20)"
    inline_code_bg = "rgba(255,255,255,0.14)" if is_dark else "rgba(0,0,0,0.15)"

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
                f"<th style=\"text-align:{aligns[i]}; border:1px solid {table_border}; padding:6px; "
                f"background: {table_header_bg};\">{_escape_html(h)}</th>"
            )
        table_parts.append("</tr></thead><tbody>")
        for row in body_rows:
            table_parts.append("<tr>")
            for i, cell in enumerate(row):
                table_parts.append(
                    f"<td style=\"text-align:{aligns[i]}; border:1px solid {table_border}; padding:6px;\">"
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
            f'<pre style="background-color: {code_bg}; padding: 8px; '
            f'border-radius: 4px; font-family: monospace; white-space: pre-wrap; '
            f'border: 1px solid {table_border};">'
            f"{code}</pre>"
        )

    text = re.sub(r"```(?:\w*\n)?(.*?)```", _replace_code_block, text, flags=re.DOTALL)

    # Satir ici kod (`...`)
    def _replace_inline_code(m):
        code = m.group(1)
        code = _escape_html(code)
        return (
            f'<code style="background-color: {inline_code_bg}; padding: 1px 4px; '
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
    """Minimal sohbet arayuzu bileseni."""

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
        self._stream_thinking_active = False
        self._is_generating = False
        self._theme_name = "dark"

        # Stream debounce için
        self._scroll_debounce_timer = QTimer(self)
        self._scroll_debounce_timer.setSingleShot(True)
        self._scroll_debounce_timer.setInterval(100)
        self._scroll_debounce_timer.timeout.connect(self._scroll_to_bottom)

        self._setup_ui()

    def _setup_ui(self):
        """Arayuz elemanlarini olusturur."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Recent actions section
        recent_frame = QFrame()
        recent_frame.setObjectName("recent_section")
        recent_layout = QVBoxLayout(recent_frame)
        recent_layout.setContentsMargins(0, 0, 0, 0)
        recent_layout.setSpacing(8)

        recent_title = QLabel("Recent actions")
        recent_title.setObjectName("recent_title")
        recent_layout.addWidget(recent_title)

        self._recent_action_item = QLabel("Henüz bir işlem yok.")
        self._recent_action_item.setWordWrap(True)
        self._recent_action_item.setObjectName("recent_action_item")
        recent_layout.addWidget(self._recent_action_item)
        layout.addWidget(recent_frame)

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

        # Modern Flat Input Container
        input_container = QFrame()
        input_container.setObjectName("input_container")

        input_v_layout = QVBoxLayout(input_container)
        input_v_layout.setContentsMargins(16, 12, 16, 12)
        input_v_layout.setSpacing(10)

        # Input text area
        self._input_edit = QTextEdit()
        self._input_edit.setPlaceholderText("ArasAI ile konuşun... (Ctrl+Enter)")
        self._input_edit.setFixedHeight(74)
        self._input_edit.setFrameShape(QFrame.NoFrame)
        self._input_edit.setAcceptRichText(False)
        input_v_layout.addWidget(self._input_edit)

        # Bottom bar with chips and buttons
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(8)

        self._plus_btn = QPushButton("+")
        self._plus_btn.setObjectName("input_icon_btn")
        self._plus_btn.setFixedSize(24, 24)
        self._plus_btn.setCursor(Qt.PointingHandCursor)
        self._plus_btn.setToolTip("Yeni sohbet")
        self._plus_btn.clicked.connect(self.clear_chat)
        bottom_bar.addWidget(self._plus_btn)

        # Clear button - icon in input bar
        self._clear_btn = QPushButton("")
        self._clear_btn.setObjectName("input_icon_btn")
        self._clear_btn.setFlat(True)
        self._clear_btn.setFixedSize(24, 24)
        self._clear_btn.setCursor(Qt.PointingHandCursor)
        self._clear_btn.setIcon(get_icon("clear", self))
        self._clear_btn.setIconSize(QSize(14, 14))
        self._clear_btn.setToolTip("Temizle")
        self._clear_btn.clicked.connect(self.clear_chat)
        bottom_bar.addWidget(self._clear_btn)

        # Model/Provider chip
        self._provider_model_label = QLabel("")
        self._provider_model_label.setObjectName("model_chip")
        self._provider_model_label.setMinimumHeight(24)
        self._provider_model_label.setAlignment(Qt.AlignCenter)
        bottom_bar.addWidget(self._provider_model_label)
        bottom_bar.addStretch()

        # Send button - accent color
        self._action_btn = QPushButton("")
        self._action_btn.setObjectName("action_btn")
        self._action_btn.setFixedSize(32, 32)
        self._action_btn.setCursor(Qt.PointingHandCursor)
        self._action_btn.setIconSize(QSize(16, 16))
        self._action_send_style = ""
        self._action_stop_style = ""
        self._action_btn.clicked.connect(self._on_action_clicked)
        bottom_bar.addWidget(self._action_btn)

        input_v_layout.addLayout(bottom_bar)
        layout.addWidget(input_container)
        self._apply_icon_theme()

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
        self._set_recent_action_text(text)
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
        if role == "assistant":
            self._start_stream_thinking()
        return self._stream_bubble

    def update_stream_message(self, content: str):
        """Stream mesaj baloncuğunu günceller."""
        if not self._stream_bubble or not self._stream_role:
            return
        if content and content.strip():
            self._stop_stream_thinking()
        self._set_bubble_content(self._stream_bubble, self._stream_role, content)
        if not self._scroll_debounce_timer.isActive():
            self._scroll_debounce_timer.start()

    def end_stream_message(self):
        """Stream mesajını sonlandırır."""
        self._stop_stream_thinking()
        self._stream_bubble = None
        self._stream_role = None
        self._stream_wrapper = None

    def discard_stream_message(self):
        """Stream baloncuğunu kaldırır."""
        self._stop_stream_thinking()
        if self._stream_wrapper:
            self._stream_wrapper.deleteLater()
        self._stream_bubble = None
        self._stream_role = None
        self._stream_wrapper = None

    def _create_message_bubble(self, role: str, content: str):
        """Mesaj baloncuğu oluşturur - Flat Cursor/VSCode tarzı."""
        wrapper = QWidget()
        v_layout = QVBoxLayout(wrapper)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(0)

        bubble = QTextBrowser()
        bubble.setFrameShape(QFrame.NoFrame)
        bubble.setOpenExternalLinks(True)
        bubble.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        bubble.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        bubble.setLineWrapMode(QTextBrowser.WidgetWidth)

        if role == "user":
            bubble.setObjectName("user_bubble")
        else:
            bubble.setObjectName("ai_bubble")

        v_layout.addWidget(bubble)

        self._set_bubble_content(bubble, role, content)

        count = self._messages_layout.count()
        self._messages_layout.insertWidget(count - 1, wrapper)
        return bubble, wrapper

    def _set_bubble_content(self, bubble: QTextBrowser, role: str, content: str):
        """Baloncuk içeriğini ayarlar - flat style."""
        if role == "user":
            safe = html.escape(content).replace("\n", "<br>")
            bubble.setHtml(f'<div style="line-height: 1.5;">{safe}</div>')
        else:
            bubble.setHtml(
                f'<div style="line-height: 1.6;">'
                f'{_markdown_to_html(content, self._theme_name)}'
                f"</div>"
            )

        doc = bubble.document()
        doc.setTextWidth(bubble.viewport().width() if bubble.viewport().width() > 0 else 400)
        height = doc.size().height() + 16
        bubble.setFixedHeight(max(int(height), 32))

    def _scroll_to_bottom(self):
        """Mesaj alanini en alta kaydirir."""
        sb = self._scroll_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def show_loading(self):
        """AI balonundaki düşünme animasyonunu başlatır."""
        if self._stream_bubble and self._stream_role == "assistant":
            self._start_stream_thinking()

    def hide_loading(self):
        """Düşünme animasyonunu durdurur."""
        self._stop_stream_thinking()
        self._loading_label.setVisible(False)

    def _animate_loading(self):
        """Düşünme animasyonunu günceller."""
        from .i18n import get_text

        self._loading_dots = (self._loading_dots + 1) % 4
        if self._stream_thinking_active and self._stream_bubble and self._stream_role == "assistant":
            dots = "." * self._loading_dots
            base_text = get_text("chat_thinking", self._current_lang)
            self._set_bubble_content(self._stream_bubble, "assistant", f"{base_text}{dots}")
            if not self._scroll_debounce_timer.isActive():
                self._scroll_debounce_timer.start()

    def clear_chat(self):
        """Tum mesajlari temizler."""
        while self._messages_layout.count() > 1:
            item = self._messages_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def set_input_enabled(self, enabled: bool):
        """Giris alanini etkinlestirir/devre disi birakir."""
        self._input_edit.setEnabled(enabled)
        if not self._is_generating:
            self._action_btn.setEnabled(enabled)
        self._clear_btn.setEnabled(enabled)

    def set_generating(self, generating: bool):
        """Stream durumuna göre durdur butonunu yönetir."""
        self._is_generating = generating
        if generating:
            self._action_btn.setToolTip(self._stop_tooltip if hasattr(self, '_stop_tooltip') else "Durdur")
            self._action_btn.setEnabled(True)
            if hasattr(self, "_action_stop_style"):
                self._action_btn.setStyleSheet(self._action_stop_style)
        else:
            self._action_btn.setToolTip(self._send_tooltip if hasattr(self, '_send_tooltip') else "Gönder")
            if hasattr(self, "_action_send_style"):
                self._action_btn.setStyleSheet(self._action_send_style)
        self._apply_icon_theme()

    def update_theme(self, theme_name: str):
        """Chat bilesenlerinin temasini gunceller."""
        self._theme_name = theme_name
        self._apply_icon_theme()

    def update_language(self, lang: str):
        """Chat bilesenlerinin dilini gunceller."""
        from .i18n import get_text

        self._current_lang = lang
        self._input_edit.setPlaceholderText(get_text("chat_placeholder", lang))
        self._send_tooltip = get_text("chat_send", lang)
        self._clear_btn.setToolTip(get_text("chat_clear", lang))
        self._plus_btn.setToolTip("Yeni sohbet")
        self._stop_tooltip = get_text("chat_stop", lang)
        self._action_btn.setToolTip(self._stop_tooltip if self._is_generating else self._send_tooltip)
        self._update_provider_model_label()

    def _on_action_clicked(self):
        """Gönder veya durdur aksiyonu."""
        if self._is_generating:
            self._on_cancel()
        else:
            self._on_send()

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

    def _set_recent_action_text(self, text: str):
        """Recent actions kartındaki son kullanıcı girdisini günceller."""
        compact = " ".join(text.split())
        if len(compact) > 110:
            compact = compact[:107] + "..."
        self._recent_action_item.setText(compact)

    def _apply_icon_theme(self):
        """Tema uyumlu giriş ikonu renklerini uygular."""
        icon_neutral = "#d2dae6" if self._theme_name == "dark" else "#57606a"
        icon_send = "#9dc2ff" if self._theme_name == "dark" else "#0969da"
        icon_stop = "#ff938f" if self._theme_name == "dark" else "#cf222e"

        self._clear_btn.setIcon(get_icon("clear", self, color=icon_neutral))
        if self._is_generating:
            self._action_btn.setIcon(get_icon("stop", self, color=icon_stop))
        else:
            self._action_btn.setIcon(get_icon("send", self, color=icon_send))

    def _start_stream_thinking(self):
        """AI stream balonunda düşünme animasyonunu başlatır."""
        if not self._stream_bubble or self._stream_role != "assistant":
            return
        self._stream_thinking_active = True
        self._loading_dots = 0
        self._loading_timer.start()
        self._animate_loading()

    def _stop_stream_thinking(self):
        """AI stream balonundaki düşünme animasyonunu durdurur."""
        self._stream_thinking_active = False
        self._loading_timer.stop()
