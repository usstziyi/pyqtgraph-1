"""Unit 02: embed PyQtGraph in a Qt layout and update it with signals."""

import sys

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QMainWindow,
    QWidget,
)


class SignalPlotWidget(pg.PlotWidget):
    """PyQtGraph widget that owns the plot item and curve object."""

    def __init__(self) -> None:
        super().__init__(title="Signal controlled by Qt widgets")
        self.setLabel("bottom", "time", units="s")
        self.setLabel("left", "amplitude")
        self.showGrid(x=True, y=True, alpha=0.2)
        self.curve = self.plot(pen=pg.mkPen("#0072B2", width=2))

    def set_signal(self, x: np.ndarray, y: np.ndarray) -> None:
        self.curve.setData(x, y)

    def set_grid_visible(self, enabled: bool) -> None:
        self.showGrid(x=enabled, y=enabled, alpha=0.2)


class SignalControlWindow(QMainWindow):
    """Qt window that owns layouts, controls, and signal/slot wiring."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Unit 02 - Qt layouts and signals")
        self.resize(980, 560)

        self.x = np.linspace(0.0, 1.0, 1000)

        central = QWidget()
        self.setCentralWidget(central)

        layout = QGridLayout(central)
        controls = QFormLayout()
        layout.addLayout(controls, 0, 0)

        self.plot = SignalPlotWidget()
        layout.addWidget(self.plot, 0, 1)
        layout.setColumnStretch(1, 1)

        self.frequency = QDoubleSpinBox()
        self.frequency.setRange(0.1, 50.0)
        self.frequency.setSingleStep(0.5)
        self.frequency.setValue(5.0)
        self.frequency.setSuffix(" Hz")
        controls.addRow("Frequency", self.frequency)

        self.amplitude = QDoubleSpinBox()
        self.amplitude.setRange(0.1, 5.0)
        self.amplitude.setSingleStep(0.1)
        self.amplitude.setValue(1.0)
        controls.addRow("Amplitude", self.amplitude)

        self.phase = QDoubleSpinBox()
        self.phase.setRange(-180.0, 180.0)
        self.phase.setSingleStep(15.0)
        self.phase.setSuffix(" deg")
        controls.addRow("Phase", self.phase)

        self.grid = QCheckBox("Show grid")
        self.grid.setChecked(True)
        controls.addRow(self.grid)

        self.frequency.valueChanged.connect(self.redraw)
        self.amplitude.valueChanged.connect(self.redraw)
        self.phase.valueChanged.connect(self.redraw)
        self.grid.toggled.connect(self.toggle_grid)

        self.redraw()

    def redraw(self) -> None:
        """Recalculate data and update the existing curve object."""
        freq = self.frequency.value()
        amp = self.amplitude.value()
        phase_rad = np.deg2rad(self.phase.value())
        y = amp * np.sin(2.0 * np.pi * freq * self.x + phase_rad)
        self.plot.set_signal(self.x, y)

    def toggle_grid(self, enabled: bool) -> None:
        """Qt sends the checkbox state here whenever the user toggles it."""
        self.plot.set_grid_visible(enabled)


def main() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Unit 02 - Qt layouts and signals")
    window = SignalControlWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
