# python internals
from __future__ import annotations
import sys
import traceback
from typing import Union, Optional, List
# internal packages
from .stylesheet import stylesheet
from .row import Row
from .switch import ToggleSwitch
from .ntypes import ColormapTypeT, SphDims, Scatter, Volume
from .model import StateSpec, State, Atom, Plotter
from .plot import WindowSpec, ScatterWindow, VolumeWindow
from .scheduler import Scheduler
# external packages
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QImage, QIntValidator
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTabWidget, QCheckBox, QPushButton, QLineEdit, QComboBox,
    QLabel, QMessageBox, QSlider, QScrollArea, QFileDialog, QGroupBox)
import pyqtgraph as pg

QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Menu")
        self.resize(500, 550)
        self.setStyleSheet(stylesheet)
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        self.__atom: Optional[Atom] = None
        self.__plot: Optional[Union[ScatterWindow, VolumeWindow]] = None
        self.__scheduler: Optional[Scheduler] = None
        self.__rows: List[Row] = []

        self.__btn_snapshot = QPushButton("Screenshot")
        self.__btn_snapshot.setMinimumHeight(30)
        self.__btn_snapshot.setFixedWidth(110)
        self.__btn_snapshot.clicked.connect(self.take_snapshot)
        main_layout.addWidget(self.__btn_snapshot, alignment=Qt.AlignmentFlag.AlignRight)

        self.__tabs = QTabWidget()
        self.__tabs.addTab(self.__states_tab(), "Orbital creator")
        self.__tabs.addTab(self.__settings_tab(), "Settings")
        main_layout.addWidget(self.__tabs)

        self.__btn_apply = QPushButton("Apply")
        self.__btn_apply.setObjectName("PrimaryButton")
        self.__btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        self.__btn_apply.clicked.connect(self.__process)

        main_layout.addWidget(self.__btn_apply)

        copyright_label = QLabel("© Mikołaj Suszek & Hubert Rączkiewicz  2026")

        main_layout.addSpacing(15)
        main_layout.addWidget(copyright_label, alignment=Qt.AlignmentFlag.AlignRight)

    @property
    def fps(self) -> int:
        return int(self.__inp_fps.text())
    @property
    def speed(self) -> float:
        return self.__sld_speed.value() / 10.0
    @property
    def dim(self) -> int:
        return int(self.__inp_dim.text())
    @property
    def cmap_name(self) -> ColormapTypeT:
        return self.__box_cmap.currentText()
    @property
    def show_hud(self) -> bool:
        return self.__hud.isChecked()
    @property
    def show_colorbar(self) -> bool:
        return self.__colorbar.isChecked()
    @property
    def plot_type(self) -> str:
        return 'volume' if self.__chk_vol.isChecked() else 'scatter'
    def take_snapshot(self) -> None:
        if self.__plot is None:
            QMessageBox.warning(self, "Error", "Plot window was not found")
            return

        try:
            img_array = self.__plot.snapshot()
            file_path, _ = QFileDialog.getSaveFileName(self,"Save screenshot","snapshot.png","PNG Image (*.png);;JPEG Image (*.jpg);;Bitmap (*.bmp)")

            if file_path:
                height, width, channels = img_array.shape
                qimg = QImage(img_array.tobytes(), width, height, channels * width, QImage.Format.Format_RGBA8888)

                if qimg.save(file_path):
                    QMessageBox.information(self, "Success", f"Screenshot was saved to file:\n{file_path}")
                else:
                    QMessageBox.critical(self, "Error", "Saving file was not a success")

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"An error has occurered:\n{e}")

    def __settings_tab(self):
        Tab1 = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        info_label = QLabel("Additional settings")
        info_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 12px;")

        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form_layout.setHorizontalSpacing(20)
        form_layout.setVerticalSpacing(12)

        label_width = 260

        def make_label(text):
            lbl = QLabel(text)
            lbl.setFixedWidth(label_width)
            return lbl

        self.__box_cmap = QComboBox()
        self.__box_cmap.addItems(sorted(pg.colormap.listMaps()))
        self.__box_cmap.setCurrentText("plasma")
        self.__box_cmap.setMinimumWidth(220)

        form_layout.addRow(make_label("Color scale:"), self.__box_cmap)

        self.__inp_fps = QLineEdit("20")
        self.__inp_fps.setValidator(QIntValidator(5, 120))
        self.__inp_fps.setFixedWidth(80)

        form_layout.addRow(make_label("FPS:"), self.__inp_fps)

        self.__inp_dim = QLineEdit("100")
        self.__inp_dim.setValidator(QIntValidator(20, 1000))
        self.__inp_dim.setFixedWidth(80)

        form_layout.addRow(make_label("Mesh size:"), self.__inp_dim)

        self.__hud = QCheckBox()
        self.__hud.setChecked(True)

        form_layout.addRow(make_label("Show HUD:"), self.__hud)

        self.__colorbar = QCheckBox()
        self.__colorbar.setChecked(True)

        form_layout.addRow(make_label("Colorbar:"), self.__colorbar)

        layout.addWidget(info_label)
        layout.addLayout(form_layout)
        layout.addSpacing(25)

        speed_layout = QHBoxLayout()

        lbl_speed_title = QLabel("Animation speed:")
        lbl_speed_title.setStyleSheet("font-weight: bold; color: #00BCff;")

        self.__lbl_speed_value = QLabel("1.0")
        self.__lbl_speed_value.setStyleSheet("font-weight: bold; color: #00BCff;")

        lbl_speed_unit = QLabel("x")
        lbl_speed_unit.setStyleSheet("font-weight: bold; color: #00BCff;")

        speed_layout.addWidget(lbl_speed_title)
        speed_layout.addSpacing(8)
        speed_layout.addWidget(self.__lbl_speed_value)
        speed_layout.addWidget(lbl_speed_unit)
        speed_layout.addStretch()

        layout.addLayout(speed_layout)

        self.__sld_speed = QSlider(Qt.Orientation.Horizontal)
        self.__sld_speed.setMinimum(1)
        self.__sld_speed.setMaximum(20)
        self.__sld_speed.setValue(int(float(self.__lbl_speed_value.text())*10))
        self.__sld_speed.valueChanged.connect(
            lambda v: self.__lbl_speed_value.setText(f"{v / 10:.1f}")
        )

        layout.addWidget(self.__sld_speed)
        layout.addSpacing(30)

        self.__chk_vol = ToggleSwitch()

        lbl_scatter = QLabel("Scatter")
        lbl_volume = QLabel("Volume")

        font = QFont()
        font.setBold(True)
        lbl_scatter.setFont(font)
        lbl_volume.setFont(font)

        switch_layout = QHBoxLayout()
        switch_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        switch_layout.addWidget(lbl_scatter)
        switch_layout.addSpacing(10)
        switch_layout.addWidget(self.__chk_vol)
        switch_layout.addSpacing(10)
        switch_layout.addWidget(lbl_volume)

        layout.addLayout(switch_layout)

        Tab1.setLayout(layout)
        return Tab1
    def __states_tab(self) -> QWidget:
        Tab2 = QWidget()
        main_tab_layout = QVBoxLayout()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        states_container = QWidget()
        self.__states_layout = QVBoxLayout()
        self.__states_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        states_container.setLayout(self.__states_layout)

        scroll.setWidget(states_container)
        main_tab_layout.addWidget(scroll)

        self.__btn_add_state = QPushButton("+ Add state")
        self.__btn_add_state.clicked.connect(lambda: self.__add_row())
        main_tab_layout.addWidget(self.__btn_add_state)

        self.__add_row(defaults=(3,2,0))
        self.__add_row(defaults=(2,1,0))

        Tab2.setLayout(main_tab_layout)
        return Tab2
    
    def __add_row(self, defaults=None) -> None:
        row = Row(self.__states_layout)
        row.removeBtnClickOccurred.connect(lambda r=row: self.__remove_row(r))
        row.set_index(len(self.__rows))

        if defaults:
            row.n,row.l,row.m = defaults

        self.__states_layout.addWidget(row)
        self.__rows.append(row)
    def __remove_row(self, row_object: Row) -> None:
        if row_object in self.__rows:
            self.__rows.remove(row_object)

        row_object.setParent(None)
        row_object.deleteLater()

        for i,row in enumerate(self.__rows):
            row.set_index(i)
    def __process(self) -> None:
        try:
            states = []
            if not self.__rows:
                raise ValueError("At least one state is required")

            for row in self.__rows:
                states.append(State(StateSpec(row.n,row.l,row.m)))
            self.__atom = Atom(*states)

            plot_spec: WindowSpec = WindowSpec(
                title="Hydrogen atom electrion cloud",
                cmap_name=self.cmap_name,
                show_hud=self.show_hud,
                show_colorbar=self.show_colorbar
            )

            plotter = Plotter(self.__atom,SphDims(self.dim,self.dim))

            if self.plot_type == 'volume':
                source = plotter.volume()
                self.__plot = VolumeWindow(plot_spec)
            else:
                source = plotter.scatter()
                self.__plot = ScatterWindow(plot_spec)

            self.__plot.draw(source.val().masked())

            self.__plot.show()

            is_volume = isinstance(self.__plot, VolumeWindow)
            if is_volume:
                self.__plot.slicer()


            def callback(i: int) -> Union[Scatter,Volume]:
                return source.val(i * self.speed).masked()

            if self.__scheduler is not None:
                self.__scheduler.abort()

            self.__scheduler = self.__plot.auto_update(callback,self.fps)

            fps_rec = []
            en_vals = dict(zip(((spec.n,spec.l,spec.m) for spec in self.__atom.specs),(state.energy_func().ev_val() for state in self.__atom.states)))

            def on_step(i: int) -> None:
                nonlocal fps_rec,en_vals

                current_fps = self.__scheduler.fps
                fps_rec.append(current_fps)
                if len(fps_rec) > self.fps:
                    fps_rec.pop(0)
                fps_avg = sum(fps_rec) / len(fps_rec) if fps_rec else 0.0

                if self.show_hud:
                    self.__plot.set_hud(
                        f"speed:{self.speed:>15.2f}\n"
                        f"fps:{fps_avg:>17.1f}\nspec:\n"
                        + "\n".join(
                            f"{' ' * 5}({s.n},{s.l},{s.m}):\n"
                            f"{' ' * 7}en: {en_vals[(s.n,s.l,s.m)]:.4f} eV"
                            for s in self.__atom.specs
                        )
                    )

            self.__scheduler.stepOccurred.connect(on_step)

        except ValueError as error:
            QMessageBox.warning(self,"Input Error",f"Incorrect input data: {error}")
        except Exception as exception:
            traceback.print_exc()
            QMessageBox.critical(self,"Error",f"An unexpected error has occurred: {exception}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
