# python internals
from __future__ import annotations
# external packages
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIntValidator
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFrame, QGraphicsDropShadowEffect

class Row(QWidget):
    removeBtnClickOccurred: pyqtSignal = pyqtSignal()
    def __init__(self, parent_layout: QVBoxLayout) -> None:
        super().__init__()
        self.layout_ref: QVBoxLayout = parent_layout

        self.__card_frame: QFrame = QFrame()
        self.__card_frame.setObjectName("StateCard")

        shadow: QGraphicsDropShadowEffect = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        self.__card_frame.setGraphicsEffect(shadow)

        card_layout: QHBoxLayout = QHBoxLayout()
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.setSpacing(10)
        self.__card_frame.setLayout(card_layout)

        main_layout: QVBoxLayout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.addWidget(self.__card_frame)
        self.setLayout(main_layout)

        self.__inp_n: QLineEdit = QLineEdit("1")
        self.__inp_n.setValidator(QIntValidator(1, 100))
        self.__inp_l: QLineEdit = QLineEdit("0")
        self.__inp_l.setValidator(QIntValidator(0, 100))
        self.__inp_m: QLineEdit = QLineEdit("0")
        self.__inp_m.setValidator(QIntValidator(-100, 100))

        for inp in [self.__inp_n, self.__inp_l, self.__inp_m]:
            inp.setFixedWidth(50)
            inp.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.__btn_remove: QPushButton = QPushButton("X")
        self.__btn_remove.setObjectName("DestructiveButton")
        self.__btn_remove.setFixedWidth(36)
        self.__btn_remove.setCursor(Qt.CursorShape.PointingHandCursor)
        self.__btn_remove.clicked.connect(self.removeBtnClickOccurred.emit)

        self.__lbl_title: QLabel = QLabel("")
        self.__lbl_title.setStyleSheet("color: #00BCff; font-weight: bold;")

        card_layout.addWidget(self.__lbl_title)
        card_layout.addStretch()

        def make_lbl(html_text: str) -> QLabel:
            l: QLabel = QLabel(html_text)
            l.setStyleSheet("font-family: 'Times New Roman', serif; font-size: 19px; color: #ffffff;")
            return l

        card_layout.addWidget(make_lbl("<i>n</i> :"))
        card_layout.addWidget(self.__inp_n)
        card_layout.addWidget(make_lbl("ℓ :"))
        card_layout.addWidget(self.__inp_l)
        card_layout.addWidget(make_lbl("<i>m<sub>ℓ</sub></i> :"))
        card_layout.addWidget(self.__inp_m)
        card_layout.addSpacing(10)
        card_layout.addWidget(self.__btn_remove)
    def set_index(self, index: int) -> None:
        self.__lbl_title.setText(f"Orbital {index + 1}")
    @property
    def n(self) -> int:
        try:
            return int(self.__inp_n.text())
        except ValueError:
            raise ValueError("Pincipal quantum number must be an integer")
    @n.setter
    def n(self, value: int) -> None:
        self.__inp_n.setText(str(value))
    @property
    def l(self) -> int:
        try:
            return int(self.__inp_l.text())
        except ValueError:
            raise ValueError("Azimuthal quantum number must be an integer")
    @l.setter
    def l(self, value: int) -> None:
        self.__inp_l.setText(str(value))
    @property
    def m(self) -> int:
        try:
            return int(self.__inp_m.text())
        except ValueError:
            raise ValueError("Magnetic quantum number must be a whole number")
    @m.setter
    def m(self, value: int) -> None:
        self.__inp_m.setText(str(value))

__all__ = ['Row']
