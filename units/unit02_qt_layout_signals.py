"""Unit 02: embed PyQtGraph in a Qt layout and update it with signals."""

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets


class SignalControlWindow(QtWidgets.QMainWindow):
    """A small Qt window where widgets control a PyQtGraph plot."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Unit 02 - Qt layouts and signals")
        self.resize(980, 560)

        self.x = np.linspace(0.0, 1.0, 1000)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        layout = QtWidgets.QGridLayout(central)
        controls = QtWidgets.QFormLayout()
        layout.addLayout(controls, 0, 0)

        self.plot = pg.PlotWidget(title="Signal controlled by Qt widgets")
        self.plot.setLabel("bottom", "time", units="s")
        self.plot.setLabel("left", "amplitude")
        self.plot.showGrid(x=True, y=True, alpha=0.2)
        layout.addWidget(self.plot, 0, 1)
        layout.setColumnStretch(1, 1)

        self.frequency = QtWidgets.QDoubleSpinBox()
        self.frequency.setRange(0.1, 50.0)
        self.frequency.setSingleStep(0.5)
        self.frequency.setValue(5.0)
        self.frequency.setSuffix(" Hz")
        controls.addRow("Frequency", self.frequency)

        self.amplitude = QtWidgets.QDoubleSpinBox()
        self.amplitude.setRange(0.1, 5.0)
        self.amplitude.setSingleStep(0.1)
        self.amplitude.setValue(1.0)
        controls.addRow("Amplitude", self.amplitude)

        self.phase = QtWidgets.QDoubleSpinBox()
        self.phase.setRange(-180.0, 180.0)
        self.phase.setSingleStep(15.0)
        self.phase.setSuffix(" deg")
        controls.addRow("Phase", self.phase)

        self.grid = QtWidgets.QCheckBox("Show grid")
        self.grid.setChecked(True)
        controls.addRow(self.grid)

        self.curve = self.plot.plot(pen=pg.mkPen("#0072B2", width=2))

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
        self.curve.setData(self.x, y)

    def toggle_grid(self, enabled: bool) -> None:
        """Qt sends the checkbox state here whenever the user toggles it."""
        self.plot.showGrid(x=enabled, y=enabled, alpha=0.2)


def main() -> None:
    app = pg.mkQApp("Unit 02 - Qt layouts and signals")
    window = SignalControlWindow()
    window.show()
    pg.exec()


if __name__ == "__main__":
    main()

