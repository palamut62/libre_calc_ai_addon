"""Yardim diyalogu - Uygulama ozellikleri ve kullanim bilgileri."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QWidget,
    QFrame,
)
from PyQt5.QtGui import QFont

from .i18n import get_text


class HelpDialog(QDialog):
    """Yardim ve ozellikler diyalogu."""

    def __init__(self, parent=None, lang: str = "tr"):
        super().__init__(parent)
        self._lang = lang
        self._setup_ui()

    def _setup_ui(self):
        """Arayuz elemanlarini olusturur."""
        self.setWindowTitle("Calc AI - Yardım" if self._lang == "tr" else "Calc AI - Help")
        self.setMinimumSize(500, 600)
        self.setMaximumSize(700, 800)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Başlık
        title = QLabel("Calc AI")
        title.setFont(QFont("", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("LibreOffice Calc için AI Asistanı" if self._lang == "tr" else "AI Assistant for LibreOffice Calc")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #888; margin-bottom: 10px;")
        layout.addWidget(subtitle)

        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(20)

        # Özellikler
        self._add_section(content_layout,
            "Özellikler" if self._lang == "tr" else "Features",
            self._get_features_text()
        )

        # Kullanım
        self._add_section(content_layout,
            "Nasıl Kullanılır?" if self._lang == "tr" else "How to Use?",
            self._get_usage_text()
        )

        # Araçlar
        self._add_section(content_layout,
            "Mevcut Araçlar" if self._lang == "tr" else "Available Tools",
            self._get_tools_text()
        )

        # İpuçları
        self._add_section(content_layout,
            "İpuçları" if self._lang == "tr" else "Tips",
            self._get_tips_text()
        )

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        # Kapat butonu
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Kapat" if self._lang == "tr" else "Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setMinimumWidth(100)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _add_section(self, layout, title: str, content: str):
        """Bölüm başlığı ve içeriği ekler."""
        title_label = QLabel(title)
        title_label.setFont(QFont("", 12, QFont.Bold))
        title_label.setStyleSheet("margin-top: 10px;")
        layout.addWidget(title_label)

        content_label = QLabel(content)
        content_label.setWordWrap(True)
        content_label.setTextFormat(Qt.RichText)
        content_label.setStyleSheet("padding-left: 10px; line-height: 1.5;")
        layout.addWidget(content_label)

    def _get_features_text(self) -> str:
        if self._lang == "tr":
            return """
            <ul>
            <li><b>Doğal Dil ile Tablo Düzenleme:</b> Türkçe veya İngilizce komutlarla tablonuzu düzenleyin</li>
            <li><b>Formül Oluşturma:</b> Karmaşık formülleri doğal dille oluşturun</li>
            <li><b>Veri Analizi:</b> Tablonuzdaki verileri analiz edin ve özetleyin</li>
            <li><b>Hata Tespiti:</b> Formül hatalarını otomatik tespit edin</li>
            <li><b>Grafik Oluşturma:</b> Verilerinizden grafikler oluşturun</li>
            <li><b>Biçimlendirme:</b> Hücre stilleri, koşullu biçimlendirme uygulayın</li>
            <li><b>Çoklu Sayfa Yönetimi:</b> Sayfalar arası geçiş ve yönetim</li>
            </ul>
            """
        else:
            return """
            <ul>
            <li><b>Natural Language Editing:</b> Edit your spreadsheet with Turkish or English commands</li>
            <li><b>Formula Creation:</b> Create complex formulas with natural language</li>
            <li><b>Data Analysis:</b> Analyze and summarize your data</li>
            <li><b>Error Detection:</b> Automatically detect formula errors</li>
            <li><b>Chart Creation:</b> Create charts from your data</li>
            <li><b>Formatting:</b> Apply cell styles, conditional formatting</li>
            <li><b>Multi-Sheet Management:</b> Navigate and manage multiple sheets</li>
            </ul>
            """

    def _get_usage_text(self) -> str:
        if self._lang == "tr":
            return """
            <ol>
            <li>LibreOffice Calc'ı <code>./launch.sh</code> ile başlatın</li>
            <li>Chat alanına komutunuzu yazın (ör: "A sütununu topla")</li>
            <li>Ctrl+Enter veya Gönder butonuyla gönderin</li>
            <li>AI asistanı tablonuzda işlemi gerçekleştirir</li>
            </ol>
            """
        else:
            return """
            <ol>
            <li>Start LibreOffice Calc with <code>./launch.sh</code></li>
            <li>Type your command in the chat area (e.g., "Sum column A")</li>
            <li>Send with Ctrl+Enter or the Send button</li>
            <li>AI assistant performs the operation on your spreadsheet</li>
            </ol>
            """

    def _get_tools_text(self) -> str:
        if self._lang == "tr":
            return """
            <b>Okuma:</b> read_cell_range, get_sheet_summary, get_all_formulas, analyze_spreadsheet_structure<br><br>
            <b>Yazma:</b> write_formula, set_cell_style, merge_cells, clear_range<br><br>
            <b>Satır/Sütun:</b> insert_rows, insert_columns, delete_rows, delete_columns, set_column_width, set_row_height<br><br>
            <b>Veri:</b> sort_range, set_auto_filter, set_data_validation, copy_range<br><br>
            <b>Biçim:</b> set_conditional_format<br><br>
            <b>Grafik:</b> create_chart<br><br>
            <b>Sayfa:</b> list_sheets, switch_sheet, create_sheet, rename_sheet<br><br>
            <b>Hata:</b> detect_and_explain_errors, get_cell_precedents, get_cell_dependents
            """
        else:
            return """
            <b>Reading:</b> read_cell_range, get_sheet_summary, get_all_formulas, analyze_spreadsheet_structure<br><br>
            <b>Writing:</b> write_formula, set_cell_style, merge_cells, clear_range<br><br>
            <b>Row/Column:</b> insert_rows, insert_columns, delete_rows, delete_columns, set_column_width, set_row_height<br><br>
            <b>Data:</b> sort_range, set_auto_filter, set_data_validation, copy_range<br><br>
            <b>Formatting:</b> set_conditional_format<br><br>
            <b>Charts:</b> create_chart<br><br>
            <b>Sheets:</b> list_sheets, switch_sheet, create_sheet, rename_sheet<br><br>
            <b>Errors:</b> detect_and_explain_errors, get_cell_precedents, get_cell_dependents
            """

    def _get_tips_text(self) -> str:
        if self._lang == "tr":
            return """
            <ul>
            <li>Spesifik hücre adresleri kullanın: "A1:D10 aralığını sırala"</li>
            <li>Türkçe formül isimleri: TOPLA, EĞER, DÜŞEYARA vb.</li>
            <li>Karmaşık işlemler için adım adım talimat verin</li>
            <li>Hata aldığınızda "hataları tespit et" diyebilirsiniz</li>
            </ul>
            """
        else:
            return """
            <ul>
            <li>Use specific cell addresses: "Sort range A1:D10"</li>
            <li>LibreOffice formula names: SUM, IF, VLOOKUP etc.</li>
            <li>For complex operations, give step-by-step instructions</li>
            <li>When you get errors, you can say "detect errors"</li>
            </ul>
            """
