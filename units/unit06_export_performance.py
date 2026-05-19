"""Unit 06: large-data plotting, downsampling, and simple exports."""

from pathlib import Path
import sys

import numpy as np
import pyqtgraph as pg
import pyqtgraph.exporters
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class LargeSignalPlot(pg.PlotWidget):
    """PyQtGraph plot that owns the large-data curve and render options."""

    def __init__(self, x: np.ndarray, y: np.ndarray) -> None:
        super().__init__(title="Large signal")
        self.setLabel("bottom", "time", units="s")
        self.setLabel("left", "value")
        self.showGrid(x=True, y=True, alpha=0.2)
        self.curve = self.plot(x, y, pen=pg.mkPen("#0072B2", width=1))

    def set_performance_options(self, downsample: bool) -> None:
        # 启用/禁用裁剪到视图：只渲染可见区域内的数据点，减少绘制开销
        # 只绘制当前窗口里看得见的数据，不管窗口外的数据。
        self.curve.setClipToView(downsample)
        # 启用/禁用自动降采样：使用峰值检测法在数据密集时自动减少绘制点数
        self.curve.setDownsampling(auto=downsample, method="peak")

    @property
    def plot_item(self) -> pg.PlotItem:
        return self.plotItem


class ExportPerformanceWindow(QMainWindow):
    """Qt window that owns controls, dialogs, and export actions."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Unit 06 - Export and performance")
        self.resize(1050, 620)

        self.x, self.y = self.make_data(point_count=250_000) # 250000

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        toolbar = QHBoxLayout()
        layout.addLayout(toolbar)

        self.downsample = QCheckBox("Downsample")
        self.downsample.setChecked(True)
        self.downsample.toggled.connect(self.apply_performance_options)
        toolbar.addWidget(self.downsample)

        export_csv = QPushButton("Export CSV")
        export_csv.clicked.connect(self.choose_csv_path)
        toolbar.addWidget(export_csv)

        export_png = QPushButton("Export PNG")
        export_png.clicked.connect(self.choose_png_path)
        toolbar.addWidget(export_png)
        toolbar.addStretch(1)

        self.plot = LargeSignalPlot(self.x, self.y)
        layout.addWidget(self.plot)

        self.apply_performance_options()

    """
    把它标记为 @staticmethod 表明："这个函数碰巧写在类里面，但它完全独立于实例和类，
    只是为了 组织上的便利 才放在这里。"
    """
    @staticmethod
    def make_data(point_count: int) -> tuple[np.ndarray, np.ndarray]:
        """Build a large but deterministic signal for repeatable testing."""
        x = np.linspace(0.0, 20.0, point_count)
        rng = np.random.default_rng(12)
        y = (
            np.sin(2.0 * np.pi * 2.0 * x) # f=2
            + 0.35 * np.sin(2.0 * np.pi * 17.0 * x)
            + 0.08 * rng.normal(size=point_count)
        )
        return x, y

    def apply_performance_options(self) -> None:
        """
        Keep interaction smooth by drawing fewer points when zoomed out.
        当缩小时，通过绘制更少的点来保持交互流畅
        """
        self.plot.set_performance_options(self.downsample.isChecked())

    def choose_csv_path(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export data",
            "large_signal.csv",
            "CSV files (*.csv)",
        )
        if path:
            self.export_csv(Path(path))

    def choose_png_path(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export plot",
            "large_signal.png",
            "PNG files (*.png)",
        )
        if path:
            self.export_png(Path(path))

    def export_csv(self, path: Path) -> None:
        """CSV export is data export, not a screenshot of the visual plot."""
        # 把两个一维数组 按列拼接 成一个二维数组(25000, 2)
        data = np.column_stack([self.x, self.y])
        np.savetxt(
            path,           # 保存的文件路径
            data,           # 要保存的二维数据数组
            delimiter=",",  # 使用逗号作为列分隔符
            header="sample,value",  # CSV文件头部列名
            comments="",    # 禁用默认的注释符号（避免在头部前添加#）
        )

    def export_png(self, path: Path) -> None:
        """ImageExporter renders the current PlotItem to a bitmap file."""
        # self.plot.plot_item 是一个 property ，返回 self.plotItem ，
        # 即 pyqtgraph 内部的 PlotItem 对象（坐标轴、曲线、图例等都画在它上面）
        # 准备一个图片导出器，它要把这个 PlotItem 的内容渲染成图片
        exporter = pyqtgraph.exporters.ImageExporter(self.plot.plot_item)
        # 把当前图表渲染为图片，保存到用户指定的路径
        exporter.export(str(path))


def main() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Unit 06 - Export and performance")
    app.setStyle("Fusion")
    window = ExportPerformanceWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
