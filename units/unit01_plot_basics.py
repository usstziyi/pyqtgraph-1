"""Unit 01: basic curves, scatter points, axes, grids, and legends."""

import sys

import numpy as np
import pyqtgraph as pg

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
)


class PlotBasicsWidget(pg.PlotWidget):
    """PyQtGraph widget that owns the plot item and its data layers."""

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Unit 01 - Plot basics")
        self.configure_plot()
        self.add_data_layers()

    def configure_plot(self) -> None:
        self.setLabel("bottom", "time", units="s")
        self.setLabel("left", "amplitude", units="V")
        self.showGrid(x=True, y=True, alpha=0.25)
        self.addLegend(offset=(10, 10))

    def add_data_layers(self) -> None:
        x = np.linspace(0.0, 2.0, 800)
        sine = np.sin(2.0 * np.pi * 3.0 * x)
        cosine = 0.6 * np.cos(2.0 * np.pi * 5.0 * x)

        # plot() returns a PlotDataItem. Keep it when the data will change later.
        self.plot(x, sine, pen=pg.mkPen("#0072B2", width=2), name="3 Hz sine")
        self.plot(x, cosine, pen=pg.mkPen("#D55E00", width=2), name="5 Hz cosine")

        # pen=None disables the connecting line, so only symbols are visible.
        sample_x = x[::40]
        sample_y = sine[::40]
        self.plot(
            sample_x,
            sample_y,
            pen=None,
            symbol="o",
            symbolSize=8,
            symbolBrush=pg.mkBrush("#009E73"),
            name="sampled points",
        )


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Unit 01 - Plot basics")
        self.resize(900, 520)
        # 启用抗锯齿功能，使绘制的曲线边缘更加平滑，减少锯齿状效果
        # 这会略微降低渲染性能，但能显著提升视觉质量
        # pg 是 pyqtgraph 模块本身， 
        # pg.setConfigOptions() 是在调用该模块提供的配置函数，
        # 属于 全局配置，一旦调用，会影响之后创建的所有 pyqtgraph 绘图组件。
        pg.setConfigOptions(antialias=True)
        self.plot = PlotBasicsWidget()
        # setCentralWidget 会自动建立父子关系
        self.setCentralWidget(self.plot)




def main() -> None:
    # 先检查当前进程中是否已经存在一个 QApplication 实例
    # 如果 已经存在 （返回非 None ），则 or 短路，直接复用这个已有的实例，不会再创建新的。
    # 如果 不存在 （返回 None ），则 or 右侧的 QApplication(sys.argv) 会被执行，创建一个新的 QApplication 实例。
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Unit 01 - Plot basics") # 不会显示在窗口标题栏上
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
