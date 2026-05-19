"""Unit 04: ImageView, histogram controls, and ROI statistics."""

import sys

import numpy as np
import pyqtgraph as pg
from PySide6 import QtWidgets


def make_image(size: int = 180) -> np.ndarray:
    """Generate a smooth image with noise so ROI statistics are interesting."""
    axis = np.linspace(-3.0, 3.0, size)
    xx, yy = np.meshgrid(axis, axis)
    bright_spot = np.exp(-(xx**2 + yy**2))
    ridge = 0.5 * np.exp(-((xx + 1.2) ** 2 + (yy - 0.8) ** 2) / 0.3)
    noise = 0.05 * np.random.default_rng(7).normal(size=(size, size))
    return bright_spot + ridge + noise


class RoiImageView(pg.ImageView):
    """PyQtGraph ImageView plus the ROI used to sample image data."""

    def __init__(self, data: np.ndarray) -> None:
        super().__init__()
        self.data = data
        self.getImageItem().axisOrder = "row-major"
        self.setImage(self.data, autoLevels=True)

        # RectROI lives in the ImageView's ViewBox and can sample the ImageItem.
        self.roi = pg.RectROI([55, 55], [60, 60], pen=pg.mkPen("#D55E00", width=2))
        self.roi.addScaleHandle([1, 1], [0, 0])
        self.getView().addItem(self.roi)

    def selected_region(self) -> np.ndarray | None:
        return self.roi.getArrayRegion(self.data, self.getImageItem())


class ImageRoiWindow(QtWidgets.QMainWindow):
    """Qt window that lays out the image view and ROI statistics label."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Unit 04 - ImageView and ROI")
        self.resize(980, 650)

        self.data = make_image()

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        self.image_view = RoiImageView(self.data)
        layout.addWidget(self.image_view)

        self.stats = QtWidgets.QLabel()
        layout.addWidget(self.stats)

        self.image_view.roi.sigRegionChanged.connect(self.update_roi_stats)

        self.update_roi_stats()

    def update_roi_stats(self) -> None:
        """Read the selected pixels and show simple descriptive statistics."""
        region = self.image_view.selected_region()
        if region is None or region.size == 0:
            self.stats.setText("ROI is outside the image")
            return

        self.stats.setText(
            "ROI mean={:.4f}, min={:.4f}, max={:.4f}, pixels={}".format(
                float(np.nanmean(region)),
                float(np.nanmin(region)),
                float(np.nanmax(region)),
                int(region.size),
            )
        )


def main() -> None:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Unit 04 - ImageView and ROI")
    window = ImageRoiWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
