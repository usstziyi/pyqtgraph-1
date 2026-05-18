"""Unit 03: realtime plotting with QTimer and setData()."""

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets


class RealtimeWindow(QtWidgets.QMainWindow):
    """A fixed-size rolling buffer updated by a Qt timer."""

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

        self.plot = pg.PlotWidget(title="Streaming data")
        self.plot.setLabel("bottom", "sample")
        self.plot.setLabel("left", "value")
        self.plot.showGrid(x=True, y=True, alpha=0.2)
        layout.addWidget(self.plot)

        self.curve = self.plot.plot(
            self.x,
            self.y,
            pen=pg.mkPen("#0072B2", width=2),
            name="sensor",
        )

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
        self.curve.setData(self.x, self.y)

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
    app = pg.mkQApp("Unit 03 - Realtime timer")
    window = RealtimeWindow()
    window.show()
    pg.exec()


if __name__ == "__main__":
    main()

