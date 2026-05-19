"""Unit 04: ImageView, histogram controls, and ROI statistics."""

import sys

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget


def make_image(size: int = 180) -> np.ndarray:
    """
    Generate a smooth image with noise so ROI statistics are interesting.
    中心有一个主要亮斑
    左上附近有一个较小亮团
    整张图叠加少量噪声
    """
    axis = np.linspace(-3.0, 3.0, size)
    xx, yy = np.meshgrid(axis, axis)
    # xx保存每个像素点的 x 坐标
    # yy保存每个像素点的 y 坐标
    bright_spot = np.exp(-(xx**2 + yy**2))
    ridge = 0.5 * np.exp(-((xx + 1.2) ** 2 + (yy - 0.8) ** 2) / 0.3)
    noise = 0.05 * np.random.default_rng(7).normal(size=(size, size))
    return bright_spot + ridge + noise
    # 最终图像 = 中心亮斑 + 偏移亮团 + 随机噪声


class RoiImageView(pg.ImageView):
    """
    PyQtGraph ImageView plus the ROI used to sample image data.
    在 PyQtGraph 的 ImageView 基础上，增加一个可拖动、可缩放的矩形 ROI，
    用于从图像中截取一块区域数据。
    RoiImageView 仍然是一个 ImageView，但额外增加了 ROI 功能。
    这个类把一张 NumPy 图像显示出来，并在图像上放了一个矩形 ROI，
    方便用户交互式选择区域，然后从原始数组里取出该区域的数据。
    """

    def __init__(self, data: np.ndarray) -> None:
        super().__init__()
        self.data = data
        # 意思是按 NumPy 常见的二维数组顺序解释图像 data[row, column]
        self.getImageItem().axisOrder = "row-major"
        """
        ImageView 本身是一个复合控件，内部包含：
            ImageItem 负责显示图像
            ViewBox 负责缩放、平移、坐标系统
            Histogram/Levels 控制灰度显示范围
        """
        # 表示自动根据图像数据的最小值和最大值设置显示亮度范围
        self.setImage(self.data, autoLevels=True)

        # RectROI lives in the ImageView's ViewBox and can sample the ImageItem.
        """
        左上角坐标: x=55, y=55
        宽度: 60
        高度: 60
        ROI 的外框会显示成一条较粗的橙红色矩形边框
        """
        self.roi = pg.RectROI([55, 55], [60, 60], pen=pg.mkPen("#D55E00", width=2))
        # 给 ROI 添加一个缩放手柄,手柄放在 ROI 的右下角
        # 缩放时，以左上角作为固定点锚点
        self.roi.addScaleHandle([1, 1], [0, 0])
        # 把 ROI 加到图像视图里
        self.getView().addItem(self.roi)

    def selected_region(self) -> np.ndarray | None:
        """
        定义一个方法，返回 ROI 框选区域内的数据.
        因为 ROI 的位置是在 ViewBox 坐标系统里的，而数组数据是在 NumPy 索引系统里的。
        """
        return self.roi.getArrayRegion(self.data, self.getImageItem())


class ImageRoiWindow(QMainWindow):
    """Qt window that lays out the image view and ROI statistics label."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Unit 04 - ImageView and ROI")
        self.resize(980, 650)

        
        # 生成示例图像数据
        self.data = make_image()

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # 创建自定义的 ROI 图像视图实例，传入示例图像数据
        self.image_view = RoiImageView(self.data)
        layout.addWidget(self.image_view)

        self.stats = QLabel()
        layout.addWidget(self.stats)
        # 将 ROI 区域变化信号连接到更新统计信息的槽函数
        # 当用户拖动或缩放 ROI 时，会自动触发 update_roi_stats 方法重新计算并显示统计信息
        self.image_view.roi.sigRegionChanged.connect(self.update_roi_stats)

        self.update_roi_stats()

    def update_roi_stats(self) -> None:
        """
        Read the selected pixels and show simple descriptive statistics.
        读取所选像素并显示简单的描述性统计数据。
        """
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

# 右侧是 ImageView 的直方图和灰度映射控制器，用来查看像素值分布、调整图像亮度/对比度和颜色映射。
def main() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Unit 04 - ImageView and ROI")
    window = ImageRoiWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
