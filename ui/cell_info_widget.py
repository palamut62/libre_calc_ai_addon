"""Hucre bilgi paneli - Secili hucrenin detaylarini gosterir."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGroupBox,
    QFormLayout,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QFrame,
)


class CellInfoWidget(QWidget):
    """Hucre analiz paneli.

    Secili hucrenin adresi, degeri, formulu, tipi ve
    oncul/ardil hucre agacini gosterir.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Arayuz elemanlarini olusturur."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 16)
        layout.setSpacing(12)

        # Hucre bilgi grubu
        info_group = QGroupBox("Hücre Detayları")
        info_form = QFormLayout()
        info_form.setSpacing(8)
        info_form.setLabelAlignment(Qt.AlignLeft)

        self._lbl_address = QLabel("-")
        self._lbl_address.setStyleSheet("font-weight: bold; color: #D97757;")
        self._lbl_address.setTextInteractionFlags(Qt.TextSelectableByMouse)
        info_form.addRow("Adres:", self._lbl_address)

        self._lbl_value = QLabel("-")
        self._lbl_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._lbl_value.setWordWrap(True)
        info_form.addRow("Değer:", self._lbl_value)

        self._lbl_formula = QLabel("-")
        self._lbl_formula.setStyleSheet("font-family: monospace; color: #9ca3af;")
        self._lbl_formula.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._lbl_formula.setWordWrap(True)
        info_form.addRow("Formül:", self._lbl_formula)

        self._lbl_type = QLabel("-")
        info_form.addRow("Tip:", self._lbl_type)

        info_group.setLayout(info_form)
        layout.addWidget(info_group)

        # Hata bolumu
        self._error_label = QLabel("")
        self._error_label.setObjectName("error_label")
        self._error_label.setWordWrap(True)
        self._error_label.setVisible(False)
        layout.addWidget(self._error_label)

        # Oncul/Ardil agaci
        tree_group = QGroupBox("İlişkili Hücreler")
        tree_layout = QVBoxLayout()
        tree_layout.setContentsMargins(8, 12, 8, 8)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Hücre", "İlişki"])
        self._tree.setAlternatingRowColors(True)
        self._tree.setColumnWidth(0, 100)
        self._tree.setFrameShape(QFrame.NoFrame)
        tree_layout.addWidget(self._tree)

        tree_group.setLayout(tree_layout)
        layout.addWidget(tree_group)

        layout.addStretch()

    def update_cell_info(self, info: dict):
        """Hucre bilgilerini gunceller.

        Args:
            info: Hucre bilgi sozlugu.
        """
        self._lbl_address.setText(str(info.get("address", "-")))

        value = info.get("value")
        self._lbl_value.setText(str(value) if value is not None else "(boş)")

        formula = info.get("formula")
        self._lbl_formula.setText(str(formula) if formula else "-")

        cell_type = info.get("type", "-")
        type_labels = {
            "empty": "Boş",
            "value": "Sayı",
            "text": "Metin",
            "formula": "Formül",
        }
        self._lbl_type.setText(type_labels.get(cell_type, cell_type))

        # Hata gosterimi
        error = info.get("error")
        if error:
            self._error_label.setText(f"Hata: {error}")
            self._error_label.setVisible(True)
        else:
            self._error_label.setVisible(False)

        # Oncul/ardil agaci
        self._tree.clear()

        precedents = info.get("precedents", [])
        if precedents:
            prec_item = QTreeWidgetItem(self._tree, ["Öncüller", f"({len(precedents)})"])
            prec_item.setExpanded(True)
            for addr in precedents:
                QTreeWidgetItem(prec_item, [addr, "Girdi"])

        dependents = info.get("dependents", [])
        if dependents:
            dep_item = QTreeWidgetItem(self._tree, ["Ardıllar", f"({len(dependents)})"])
            dep_item.setExpanded(True)
            for addr in dependents:
                QTreeWidgetItem(dep_item, [addr, "Çıktı"])

    def clear(self):
        """Tum hucre bilgilerini temizler."""
        self._lbl_address.setText("-")
        self._lbl_value.setText("-")
        self._lbl_formula.setText("-")
        self._lbl_formula_local.setText("-")
        self._lbl_type.setText("-")
        self._error_label.setVisible(False)
        self._tree.clear()
