# python internals
from __future__ import annotations
from typing import Optional, Callable
# internal packages
from .ntypes import *
# external packages
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QImage, QPixmap, QMouseEvent, QWheelEvent, QCloseEvent, QHideEvent, QShowEvent, \
    QResizeEvent
from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QGridLayout, QVBoxLayout, QSizePolicy
import numpy as np
import pyqtgraph as pg
import pyqtgraph.opengl as gl

class ColorBar(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.__cmap: Optional[ColormapT] = None
        self.__norm_func: Optional[Callable[[NPFloatT], NPFloatT]] = None
        self.__scale: NPFloatT = 1.0
        self.__nticks: NPIntT = 5

        self.__bar = QLabel(self)
        self.__bar.setFixedWidth(10)
        self.__bar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.__bar.setScaledContents(True)

        self.__labels_layout = QGridLayout()
        self.__labels_layout.setContentsMargins(6, 0, 0, 0)
        self.__labels_layout.setHorizontalSpacing(0)
        self.__labels_layout.setVerticalSpacing(0)

        self.__labels: list[QLabel] = []

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        main_layout.addWidget(self.__bar)
        main_layout.addLayout(self.__labels_layout)

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.hide()
    @property
    def scale(self) -> NPFloatT:
        return self.__scale
    def set_scale(self, value: NPFloatT) -> None:
        if value <= 0.0:
            raise ValueError("Scale value must be greater than 0")

        self.__scale = value
        self.__set_labels()
    @property
    def colormap(self) -> Optional[ColormapT]:
        return self.__cmap
    @colormap.setter
    def colormap(self, cmap: ColormapT) -> None:
        self.__cmap = cmap
    @property
    def normalize_function(self):
        return self.__norm_func
    @normalize_function.setter
    def normalize_function(self, func: Callable[[NPFloatT], NPFloatT]) -> None:
        self.__norm_func = func
    def __set_labels(self) -> None:
        if self.__norm_func is None:
            raise ValueError("Normalization function has not been set")

        for lbl in self.__labels:
            lbl.deleteLater()
        self.__labels.clear()

        while self.__labels_layout.count():
            self.__labels_layout.takeAt(0)

        val = np.linspace(0.0, self.__scale, 256)
        vnorm = self.__norm_func(val)

        target = np.linspace(1.0, 0.0, self.__nticks + 1)[:-1]

        idx = np.asarray([np.argmin(np.abs(vnorm - t)) for t in target], dtype=NPIntT)
        values = val[idx]

        for r in range(self.__nticks * 2 - 1):
            self.__labels_layout.setRowStretch(r, 1)

        for i, v in enumerate(values):
            lbl = QLabel(f"{v:.3f}", self)
            lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            lbl.setPalette(self.palette())

            self.__labels_layout.addWidget(lbl, i * 2, 0)
            self.__labels.append(lbl)
    def set_val(self, val: NPFArrayT) -> None:
        if self.__cmap is None:
            raise ValueError("Colormap has not been set")
        if self.__norm_func is None:
            raise ValueError("Normalization function has not been set")

        vmax = np.max(val)
        resolution = 256
        used = int(np.clip(vmax / self.__scale, 0.0, 1.0) * resolution)

        vnorm = self.__norm_func(np.linspace(vmax, 0.0, used))

        rgba = np.zeros((resolution, 4), dtype=NPFloatT)

        rgba[-used:] = self.__cmap.map(vnorm, mode='float')
        rgba[:-used, 3] = 0.0

        img = (rgba * 255).astype(np.uint8).reshape((resolution, 1, 4))
        qimg = QImage(img.data,img.shape[1], img.shape[0], img.strides[0], QImage.Format.Format_RGBA8888).copy()
        self.__bar.setPixmap(QPixmap.fromImage(qimg))

class Hud(QLabel):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        font = QFont("Monospace", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()

class PlotView(gl.GLViewWidget):
    mousePressOccurred = pyqtSignal()
    mouseReleaseOccurred = pyqtSignal()
    wheelScrollOccurred = pyqtSignal()
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.setCameraPosition(distance=30.0, elevation=20.0, azimuth=45.0)
    def mousePressEvent(self, ev: QMouseEvent) -> None:
        self.mousePressOccurred.emit()
        super().mousePressEvent(ev)
    def mouseReleaseEvent(self, ev: QMouseEvent) -> None:
        self.mouseReleaseOccurred.emit()
        super().mouseReleaseEvent(ev)
    def wheelEvent(self, ev: QWheelEvent) -> None:
        delta = ev.angleDelta().y()
        if delta == 0:
            ev.ignore()
            return

        self.wheelScrollOccurred.emit()

        distance = self.opts['distance']
        scale = 0.999 ** delta
        new_distance = distance * scale
        if 25 <= new_distance <= 500:
            self.setCameraPosition(distance=new_distance)

        ev.accept()

class WindowView(QWidget):
    mousePressOccurred = pyqtSignal()
    mouseReleaseOccurred = pyqtSignal()
    wheelScrollOccurred = pyqtSignal()
    resizeOccurred = pyqtSignal()
    windowMinimizeOccurred = pyqtSignal()
    windowRestoreOccurred = pyqtSignal()
    windowCloseOccurred = pyqtSignal()
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(400, 300)

        self.__hud: Optional[Hud] = None
        self.__colorbar: Optional[ColorBar] = None

        self.__plot = PlotView(self)
        self.__plot.mousePressOccurred.connect(self.mousePressOccurred)
        self.__plot.mouseReleaseOccurred.connect(self.mouseReleaseOccurred)
        self.__plot.wheelScrollOccurred.connect(self.wheelScrollOccurred)

        self.__main_layout = QHBoxLayout(self)
        self.__main_layout.setContentsMargins(0, 0, 0, 0)
        self.__main_layout.setSpacing(0)
        self.__main_layout.addWidget(self.__plot)

        self.__overlay = QWidget(self.__plot)
        self.__overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.__overlay.setStyleSheet("background: transparent;")

        self.__overlay_layout = QHBoxLayout(self.__overlay)
        self.__overlay_layout.setContentsMargins(0, 0, 0, 0)
        self.__overlay_layout.setSpacing(0)

        self.__colorbar_layout = QVBoxLayout()
        self.__colorbar_layout.setContentsMargins(0, 50, 0, 50)
        self.__colorbar_layout.setSpacing(0)

        self.__overlay_layout.addLayout(self.__colorbar_layout)
        self.__overlay_layout.addStretch(1)

        self.__hud_layout = QVBoxLayout()
        self.__hud_layout.setContentsMargins(0, 0, 10, 10)
        self.__hud_layout.setSpacing(0)
        self.__hud_layout.addStretch(1)

        self.__overlay_layout.addLayout(self.__hud_layout)

        self.__plot.setLayout(QHBoxLayout())
        self.__plot.layout().setContentsMargins(0, 0, 0, 0)
        self.__plot.layout().addWidget(self.__overlay)
    @property
    def plot(self) -> gl.GLViewWidget:
        return self.__plot
    @property
    def hud(self) -> Optional[Hud]:
        return self.__hud
    @hud.setter
    def hud(self, hud: Optional[Hud]) -> None:
        if self.__hud is not None:
            self.__hud_layout.removeWidget(self.__hud)
            self.__hud.setParent(None)

        self.__hud = hud
        if hud is not None:
            self.__hud_layout.addWidget(hud, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
            hud.show()
    @property
    def colorbar(self) -> Optional[ColorBar]:
        return self.__colorbar
    @colorbar.setter
    def colorbar(self, colorbar: Optional[ColorBar]) -> None:
        if self.__colorbar is not None:
            self.__colorbar_layout.removeWidget(self.__colorbar)
            self.__colorbar.setParent(None)

        self.__colorbar = colorbar
        if colorbar is not None:
            self.__colorbar_layout.addWidget(colorbar)
            colorbar.show()
    def resizeEvent(self, ev: Optional[QResizeEvent]) -> None:
        self.resizeOccurred.emit()
        super().resizeEvent(ev)
    def hideEvent(self, ev: Optional[QHideEvent]) -> None:
        self.windowMinimizeOccurred.emit()
        super().hideEvent(ev)
    def showEvent(self, ev: Optional[QShowEvent]) -> None:
        self.windowRestoreOccurred.emit()
        super().showEvent(ev)
    def closeEvent(self, ev: Optional[QCloseEvent]) -> None:
        self.windowCloseOccurred.emit()
        super().closeEvent(ev)

__all__ = ['WindowView', 'ColorBar', 'Hud']
