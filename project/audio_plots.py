"""PyQtGraph plot widgets for the microphone monitor."""

import numpy as np
import pyqtgraph as pg

try:
    from .audio_constants import DB_FLOOR, FREQUENCY_VIEW_LIMIT
except ImportError:
    from audio_constants import DB_FLOOR, FREQUENCY_VIEW_LIMIT


class MonitorPlots(pg.GraphicsLayoutWidget):
    """PyQtGraph dashboard with waveform, spectrum, and rolling spectrogram."""

    def __init__(self) -> None:
        super().__init__()

        self.time_plot = self.addPlot(row=0, col=0, title="Microphone waveform")
        self.time_plot.setLabel("bottom", "time", units="s")
        self.time_plot.setLabel("left", "amplitude")
        self.time_plot.setYRange(-1.0, 1.0, padding=0)
        self.time_plot.showGrid(x=True, y=True, alpha=0.2)
        self.time_curve = self.time_plot.plot(pen=pg.mkPen("#33FF33", width=1))

        self.freq_plot = self.addPlot(row=1, col=0, title="Frequency spectrum")
        self.freq_plot.setLabel("bottom", "frequency", units="Hz")
        self.freq_plot.setLabel("left", "level", units="dBFS") # decibels relative to full scale 相对于数字音频最大满幅值的分贝 表示：当前数字音频信号离系统能表示的最大幅度还有多远
        self.freq_plot.setYRange(DB_FLOOR, 0, padding=0)
        self.freq_plot.showGrid(x=True, y=True, alpha=0.2)
        self.freq_curve = self.freq_plot.plot(pen=pg.mkPen("#D55E00", width=1))

        self.spec_plot = self.addPlot(row=2, col=0, title="Rolling spectrogram")
        self.spec_plot.setLabel("bottom", "frequency", units="Hz")
        self.spec_plot.setLabel("left", "history", units="frame")
        self.spec_plot.getAxis("bottom").autoSIPrefix = False
        self.spec_plot.getAxis("left").autoSIPrefix = False
        self.spec_bottom_axis = self.spec_plot.getAxis("bottom")

        self.spec_image = pg.ImageItem(data=None, axisOrder="row-major")
        self.spec_plot.addItem(self.spec_image)
        cmap = pg.colormap.get("plasma")
        self.spec_image.setLookupTable(cmap.getLookupTable(nPts=256))

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
        self.spec_image.setImage(spectrogram, levels=(DB_FLOOR, 0), autoLevels=False)
        self._set_frequency_ticks(spectrogram.shape[1], sample_rate)

    def _set_frequency_ticks(self, n_bins: int, sample_rate: int) -> None:
        nyquist = sample_rate / 2
        if n_bins <= 1 or nyquist <= 0:
            self.spec_bottom_axis.setTicks([])
            return

        max_bin = n_bins - 1
        raw_step = nyquist / 5
        magnitude = 10 ** int(np.log10(max(raw_step, 1)))
        residual = raw_step / magnitude
        if residual < 1.5:
            step = magnitude
        elif residual < 3:
            step = 2 * magnitude
        elif residual < 7:
            step = 5 * magnitude
        else:
            step = 10 * magnitude

        ticks = []
        hz = 0.0
        while hz <= nyquist + step * 0.01:
            ticks.append((hz / nyquist * max_bin, f"{hz:.0f}"))
            hz += step
        self.spec_bottom_axis.setTicks([ticks])
