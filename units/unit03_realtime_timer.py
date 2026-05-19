"""Unit 03: realtime plotting with QTimer and setData()."""

import sys

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


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
            pen=pg.mkPen("#33FF33", width=2),
            name="sensor",
        )

    def set_samples(self, x: np.ndarray, y: np.ndarray) -> None:
        self.curve.setData(x, y)


class RealtimeWindow(QMainWindow):
    """Qt window with controls and a QTimer that updates a rolling buffer."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Unit 03 - Realtime timer")
        self.resize(980, 560)

        self.buffer_size = 600
        self.sample_index = 0
        self.x = np.arange(self.buffer_size)
        # 初始化数据缓冲区，用 NaN 填充表示尚未有有效数据
        self.y = np.full(self.buffer_size, np.nan)

        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        toolbar = QHBoxLayout()
        layout.addLayout(toolbar)

        self.toggle = QPushButton("Pause")
        self.toggle.clicked.connect(self.toggle_timer)
        toolbar.addWidget(self.toggle)

        self.status = QLabel("running")
        toolbar.addWidget(self.status)
        toolbar.addStretch(1)

        self.plot = RealtimePlotWidget(self.x, self.y)
        layout.addWidget(self.plot)

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(30) # 每30ms添加一个点，控制刷新率
        self.timer.timeout.connect(self.append_sample)
        self.timer.start()

    def append_sample(self) -> None:
        """Append one synthetic sample while keeping the array size stable."""
        t = self.sample_index / 100 # 100个点绘制1.5个完整sin波 # 100*30=3000ms=3s
        sample = np.sin(2.0 * np.pi * 1.5 * t) # 1s 绘制 1.5 个完整sin波
        self.sample_index += 1

        # 模拟FIFO
        # np.roll 会复制整个数组，而这两句是 原地操作 （in-place），不分配新内存，
        # 对于每 30ms 就调用一次的高频场景更高效。
        self.y[:-1] = self.y[1:] # 整体前移1位，丢掉第0位
        self.y[-1] = sample      # 把最后1位腾出来存新的值

        # 如果采用 deque 方案
        # append() 是 O(1)，但只是入队这一步快
        # np.array(self.buffer) 才是瓶颈 ：每次分配 4.8KB 新内存 + 遍历 Python 对象（deque 元素是 boxed Python float）→ 比 memcpy 慢很多
        # 每 30ms 分配一次内存还会触发频繁 GC

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
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Unit 03 - Realtime timer")
    window = RealtimeWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
