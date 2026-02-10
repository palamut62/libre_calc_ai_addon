"""Hucre bilgi paneli - Secili hucrenin detaylarini gosterir."""

from PyQt5.QtCore import Qt, QParallelAnimationGroup, QPropertyAnimation, QAbstractAnimation, QSize
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGroupBox,
    QFormLayout,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QFrame,
    QToolButton,
    QScrollArea,
    QSizePolicy,
)


class CollapsibleBox(QWidget):
    """
    Acilir kapanir bir baslik ve icerik alanina sahip widget.
    Basliga tiklandiginda icerik gizlenir/gosterilir.
    """
    def __init__(self, title="", parent=None):
        super(CollapsibleBox, self).__init__(parent)

        self.toggle_button = QToolButton(text=title, checkable=True, checked=False)
        self.toggle_button.setStyleSheet("QToolButton { border: none; font-weight: bold; color: #D97757; }")
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.RightArrow)
        self.toggle_button.pressed.connect(self.on_pressed)

        self.toggle_animation = QParallelAnimationGroup(self)
        self.content_area = QScrollArea(maximumHeight=0, minimumHeight=0)
        self.content_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.content_area.setFrameShape(QFrame.NoFrame)

        lay = QVBoxLayout(self)
        lay.setSpacing(0)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.toggle_button)
        lay.addWidget(self.content_area)

        self.toggle_animation.addAnimation(QPropertyAnimation(self, b"minimumHeight"))
        self.toggle_animation.addAnimation(QPropertyAnimation(self, b"maximumHeight"))
        self.toggle_animation.addAnimation(QPropertyAnimation(self.content_area, b"maximumHeight"))

    def on_pressed(self):
        checked = self.toggle_button.isChecked()
        self.toggle_button.setArrowType(Qt.DownArrow if not checked else Qt.RightArrow)
        self.toggle_animation.setDirection(
            QAbstractAnimation.Forward if not checked else QAbstractAnimation.Backward
        )
        self.toggle_animation.start()

    def setContentLayout(self, layout):
        lay = self.content_area.layout()
        del lay
        self.content_area.setLayout(layout)
        collapsed_height = self.sizeHint().height() - self.content_area.maximumHeight()
        content_height = layout.sizeHint().height()
        for i in range(self.toggle_animation.animationCount()):
            animation = self.toggle_animation.animationAt(i)
            animation.setDuration(300)
            animation.setStartValue(collapsed_height)
            animation.setEndValue(collapsed_height + content_height)

        content_animation = self.toggle_animation.animationAt(self.toggle_animation.animationCount() - 1)
        content_animation.setDuration(300)
        content_animation.setStartValue(0)
        content_animation.setEndValue(content_height)


class CellInfoWidget(QWidget):
    """
    Secili hucre hakkinda detayli bilgi gosteren panel.
    Acilir/kapanir bolumler halinde duzenlenmistir.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Arayuz elemanlarini olusturur."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 16)
        layout.setSpacing(12)

        # Hucre Detaylari (Collapsible)
        self._details_box = CollapsibleBox("Hücre Detayları (Tıkla)")
        
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

        self._details_box.setContentLayout(info_form)
        layout.addWidget(self._details_box)

        # Hata bolumu
        self._error_label = QLabel("")
        self._error_label.setObjectName("error_label")
        self._error_label.setWordWrap(True)
        self._error_label.setVisible(False)
        layout.addWidget(self._error_label)

        # Iliskili Hucreler (Collapsible)
        self._relations_box = CollapsibleBox("İlişkili Hücreler (Tıkla)")
        
        tree_layout = QVBoxLayout()
        tree_layout.setContentsMargins(8, 12, 8, 8)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Hücre", "İlişki"])
        self._tree.setAlternatingRowColors(True)
        self._tree.setColumnWidth(0, 100)
        self._tree.setFrameShape(QFrame.NoFrame)
        self._tree.setMinimumHeight(150)
        tree_layout.addWidget(self._tree)

        self._relations_box.setContentLayout(tree_layout)
        layout.addWidget(self._relations_box)

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
    
    def is_details_expanded(self):
        """Detay paneli acik mi?"""
        return self._details_box.toggle_button.isChecked()

    def clear(self):
        """Tum hucre bilgilerini temizler."""
        self._lbl_address.setText("-")
        self._lbl_value.setText("-")
        self._lbl_formula.setText("-")
        self._lbl_type.setText("-")
        self._error_label.setVisible(False)
        self._tree.clear()
