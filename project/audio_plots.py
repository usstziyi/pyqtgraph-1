"""PyQtGraph plot widgets for the microphone monitor."""

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore

try:
    from .audio_constants import DB_FLOOR, FREQUENCY_VIEW_LIMIT
except ImportError:
    from audio_constants import DB_FLOOR, FREQUENCY_VIEW_LIMIT


class MonitorPlots(pg.GraphicsLayoutWidget):
    """
    yQtGraph dashboard with 
    waveform, 时域波形图
    spectrum, 频域波形图
    olling spectrogram, 滚动频谱图
    """

    def __init__(self) -> None:
        super().__init__()

        self.time_plot = self.addPlot(row=0, col=0, title="Microphone waveform")
        self.time_plot.setLabel("bottom", "time", units="s")
        self.time_plot.setLabel("left", "amplitude")
        self.time_plot.getAxis("left").autoSIPrefix = False
        self.time_plot.setYRange(-1.0, 1.0, padding=0)
        self.time_plot.showGrid(x=True, y=True, alpha=0.2)
        self.time_curve = self.time_plot.plot(pen=pg.mkPen("#33FF33", width=1))

        self.freq_plot = self.addPlot(row=1, col=0, title="Frequency spectrum")
        self.freq_plot.setLabel("bottom", "frequency", units="Hz")
        self.freq_plot.setLabel("left", "level", units="dBFS") 
        self.freq_plot.getAxis("bottom").autoSIPrefix = False
        self.freq_plot.setYRange(DB_FLOOR, 0, padding=0)
        self.freq_plot.showGrid(x=True, y=True, alpha=0.2)
        self.freq_curve = self.freq_plot.plot(pen=pg.mkPen("#D55E00", width=1))

        self.spec_plot = self.addPlot(row=2, col=0, title="Rolling spectrogram")
        self.spec_plot.setLabel("bottom", "frequency", units="Hz")
        self.spec_plot.setLabel("left", "history", units="frame")
        self.spec_plot.getAxis("bottom").autoSIPrefix = False
        self.spec_plot.getAxis("left").autoSIPrefix = False
        self.spec_bottom_axis = self.spec_plot.getAxis("bottom")
        # self.spec_plot.invertY(True) # 翻转Y轴

        self.spec_image = pg.ImageItem(data=None, axisOrder="row-major")
        self.spec_plot.addItem(self.spec_image)
        cmap = pg.colormap.get("plasma") #plasma #magma
        self.spec_image.setLookupTable(cmap.getLookupTable(nPts=256))
        marker_pen = pg.mkPen("#FFFFFF", width=1, style=pg.QtCore.Qt.PenStyle.DashLine)
        self.spec_marker_lines = {
            20: pg.InfiniteLine(angle=90, movable=False, pen=marker_pen),
            20000: pg.InfiniteLine(angle=90, movable=False, pen=marker_pen),
        }
        for line in self.spec_marker_lines.values():
            self.spec_plot.addItem(line)

    def set_time_data(self, times: np.ndarray, values: np.ndarray) -> None:
        self.time_curve.setData(times, values)
        if times.size:
            # 固定x轴刻度
            self.time_plot.setXRange(float(times[0]), float(times[-1]), padding=0)

    def set_frequency_data(
        self,
        frequencies: np.ndarray,
        levels_dbfs: np.ndarray,
        sample_rate: int,
    ) -> None:
        self.freq_curve.setData(frequencies, levels_dbfs)
        self.freq_plot.setXRange(
            0,
            min(sample_rate / 2, FREQUENCY_VIEW_LIMIT),
            padding=0,
        )

    def set_spectrogram(self, spectrogram: np.ndarray, sample_rate: int) -> None:
        n_frames, n_bins = spectrogram.shape
        nyquist = sample_rate / 2
        # 默认情况下，如果你没有额外设置 setRect() 或 transform，那么这张图像会按数组索引坐标显示
        self.spec_image.setImage(spectrogram, levels=(DB_FLOOR, 0), autoLevels=False)
        if n_bins > 1 and nyquist > 0:
            # 每个频率箱的频率宽度：频率分辨率
            bin_width = nyquist / (n_bins - 1)
            self.spec_image.setRect(
                # 把图像映射到：
                # x: [0 , nyquist]
                # y: [0 , n_frames]
                QtCore.QRectF(0, 0, nyquist, n_frames)
                # QtCore.QRectF(-bin_width / 2, 0, nyquist + bin_width, n_frames)
            )
        
        # 更新频谱图中的频率标记线位置
        self._set_frequency_markers(sample_rate)

    def _set_frequency_markers(self, sample_rate: int) -> None:
        # 计算奈奎斯特频率（采样率的一半，频谱显示的最大频率）
        nyquist = sample_rate / 2
        if nyquist <= 0:
            for line in self.spec_marker_lines.values():
                line.hide()
            return

        for hz, line in self.spec_marker_lines.items():
            if hz <= nyquist:
                line.setValue(hz)
                line.show()
            else:
                line.hide()
