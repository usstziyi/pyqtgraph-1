"""Unit 04: ImageView, histogram controls, and ROI statistics."""

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets


def make_image(size: int = 180) -> np.ndarray:
    """Generate a smooth image with noise so ROI statistics are interesting."""
    axis = np.linspace(-3.0, 3.0, size)
    xx, yy = np.meshgrid(axis, axis)
    bright_spot = np.exp(-(xx**2 + yy**2))
    ridge = 0.5 * np.exp(-((xx + 1.2) ** 2 + (yy - 0.8) ** 2) / 0.3)
    noise = 0.05 * np.random.default_rng(7).normal(size=(size, size))
    return bright_spot + ridge + noise


class ImageRoiWindow(QtWidgets.QMainWindow):
    """Display a 2D array and compute statistics inside a movable ROI."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Unit 04 - ImageView and ROI")
        self.resize(980, 650)

        self.data = make_image()

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        self.image_view = pg.ImageView()
        self.image_view.getImageItem().axisOrder = "row-major"
        layout.addWidget(self.image_view)

        self.stats = QtWidgets.QLabel()
        layout.addWidget(self.stats)

        self.image_view.setImage(self.data, autoLevels=True)

        # RectROI lives in the ImageView's ViewBox and can sample the ImageItem.
        self.roi = pg.RectROI([55, 55], [60, 60], pen=pg.mkPen("#D55E00", width=2))
        self.roi.addScaleHandle([1, 1], [0, 0])
        self.image_view.getView().addItem(self.roi)
        self.roi.sigRegionChanged.connect(self.update_roi_stats)

        self.update_roi_stats()

    def update_roi_stats(self) -> None:
        """Read the selected pixels and show simple descriptive statistics."""
        region = self.roi.getArrayRegion(self.data, self.image_view.getImageItem())
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
    app = pg.mkQApp("Unit 04 - ImageView and ROI")
    window = ImageRoiWindow()
    window.show()
    pg.exec()


if __name__ == "__main__":
    main()
