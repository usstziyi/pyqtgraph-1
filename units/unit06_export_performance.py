"""Unit 06: large-data plotting, downsampling, and simple exports."""

from pathlib import Path

import numpy as np
import pyqtgraph as pg
import pyqtgraph.exporters
from pyqtgraph.Qt import QtWidgets


class ExportPerformanceWindow(QtWidgets.QMainWindow):
    """Plot a large dataset and provide CSV/PNG export actions."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Unit 06 - Export and performance")
        self.resize(1050, 620)

        self.x, self.y = self.make_data(point_count=250_000)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        toolbar = QtWidgets.QHBoxLayout()
        layout.addLayout(toolbar)

        self.downsample = QtWidgets.QCheckBox("Downsample")
        self.downsample.setChecked(True)
        self.downsample.toggled.connect(self.apply_performance_options)
        toolbar.addWidget(self.downsample)

        export_csv = QtWidgets.QPushButton("Export CSV")
        export_csv.clicked.connect(self.choose_csv_path)
        toolbar.addWidget(export_csv)

        export_png = QtWidgets.QPushButton("Export PNG")
        export_png.clicked.connect(self.choose_png_path)
        toolbar.addWidget(export_png)
        toolbar.addStretch(1)

        self.plot = pg.PlotWidget(title="Large signal")
        self.plot.setLabel("bottom", "time", units="s")
        self.plot.setLabel("left", "value")
        self.plot.showGrid(x=True, y=True, alpha=0.2)
        layout.addWidget(self.plot)

        self.curve = self.plot.plot(self.x, self.y, pen=pg.mkPen("#0072B2", width=1))
        self.apply_performance_options()

    @staticmethod
    def make_data(point_count: int) -> tuple[np.ndarray, np.ndarray]:
        """Build a large but deterministic signal for repeatable testing."""
        x = np.linspace(0.0, 20.0, point_count)
        rng = np.random.default_rng(12)
        y = (
            np.sin(2.0 * np.pi * 2.0 * x)
            + 0.35 * np.sin(2.0 * np.pi * 17.0 * x)
            + 0.08 * rng.normal(size=point_count)
        )
        return x, y

    def apply_performance_options(self) -> None:
        """Keep interaction smooth by drawing fewer points when zoomed out."""
        enabled = self.downsample.isChecked()
        self.curve.setClipToView(enabled)
        self.curve.setDownsampling(auto=enabled, method="peak")

    def choose_csv_path(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export data",
            "large_signal.csv",
            "CSV files (*.csv)",
        )
        if path:
            self.export_csv(Path(path))

    def choose_png_path(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export plot",
            "large_signal.png",
            "PNG files (*.png)",
        )
        if path:
            self.export_png(Path(path))

    def export_csv(self, path: Path) -> None:
        """CSV export is data export, not a screenshot of the visual plot."""
        data = np.column_stack([self.x, self.y])
        np.savetxt(path, data, delimiter=",", header="time,value", comments="")

    def export_png(self, path: Path) -> None:
        """ImageExporter renders the current PlotItem to a bitmap file."""
        exporter = pyqtgraph.exporters.ImageExporter(self.plot.plotItem)
        exporter.export(str(path))


def main() -> None:
    app = pg.mkQApp("Unit 06 - Export and performance")
    window = ExportPerformanceWindow()
    window.show()
    pg.exec()


if __name__ == "__main__":
    main()

