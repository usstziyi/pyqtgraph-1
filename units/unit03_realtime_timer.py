"""Unit 03: realtime plotting with QTimer and setData()."""

import sys

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets


class RealtimePlotWidget(pg.PlotWidget):
    """PyQtGraph plot wrapper that owns the reusable PlotDataItem."""

    def __init__(self, x: np.ndarray, y: np.ndarray) -> None:
        super().__init__(title="Streaming data")
        self.setLabel("bottom", "sample")
        self.setLabel("left", "value")
        self.showGrid(x=True, y=True, alpha=0.2)
        self.curve = self.plot(
            x,
            y,
            pen=pg.mkPen("#0072B2", width=2),
            name="sensor",
        )

    def set_samples(self, x: np.ndarray, y: np.ndarray) -> None:
        self.curve.setData(x, y)


class RealtimeWindow(QtWidgets.QMainWindow):
    """Qt window with controls and a QTimer that updates a rolling buffer."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Unit 03 - Realtime timer")
        self.resize(980, 560)

        self.buffer_size = 600
        self.sample_index = 0
        self.x = np.arange(self.buffer_size)
        self.y = np.full(self.buffer_size, np.nan)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        layout = QtWidgets.QVBoxLayout(central)
        toolbar = QtWidgets.QHBoxLayout()
        layout.addLayout(toolbar)

        self.toggle = QtWidgets.QPushButton("Pause")
        self.toggle.clicked.connect(self.toggle_timer)
        toolbar.addWidget(self.toggle)

        self.status = QtWidgets.QLabel("running")
        toolbar.addWidget(self.status)
        toolbar.addStretch(1)

        self.plot = RealtimePlotWidget(self.x, self.y)
        layout.addWidget(self.plot)

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(30)
        self.timer.timeout.connect(self.append_sample)
        self.timer.start()

    def append_sample(self) -> None:
        """Append one synthetic sample while keeping the array size stable."""
        t = self.sample_index / 60.0
        sample = np.sin(2.0 * np.pi * 1.5 * t) + 0.15 * np.random.normal()
        self.sample_index += 1

        self.y[:-1] = self.y[1:]
        self.y[-1] = sample
        self.plot.set_samples(self.x, self.y)

    def toggle_timer(self) -> None:
        """Pause or resume without destroying the timer."""
        if self.timer.isActive():
            self.timer.stop()
            self.toggle.setText("Resume")
            self.status.setText("paused")
        else:
            self.timer.start()
            self.toggle.setText("Pause")
            self.status.setText("running")


def main() -> None:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Unit 03 - Realtime timer")
    window = RealtimeWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
