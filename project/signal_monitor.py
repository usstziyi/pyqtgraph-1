"""Practical project: a realtime signal monitor built with PyQtGraph."""

from pathlib import Path
import sys

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from pyqtgraph.parametertree import Parameter, ParameterTree


def create_parameters() -> Parameter:
    """Create the pyqtgraph Parameter model used by the settings tree."""
    return Parameter.create(
        name="settings",
        type="group",
        children=[
            {
                "name": "Acquisition",
                "type": "group",
                "children": [
                    {
                        "name": "Sample rate",
                        "type": "int",
                        "value": 1000,
                        "limits": (100, 5000),
                        "step": 100,
                        "suffix": " Hz",
                    },
                    {
                        "name": "Refresh interval",
                        "type": "int",
                        "value": 40,
                        "limits": (10, 500),
                        "step": 10,
                        "suffix": " ms",
                    },
                ],
            },
            {
                "name": "Signal",
                "type": "group",
                "children": [
                    {
                        "name": "Frequency",
                        "type": "float",
                        "value": 30.0,
                        "limits": (1.0, 450.0),
                        "step": 1.0,
                        "suffix": " Hz",
                    },
                    {
                        "name": "Noise",
                        "type": "float",
                        "value": 0.08,
                        "limits": (0.0, 1.0),
                        "step": 0.01,
                    },
                ],
            },
            {
                "name": "Analysis",
                "type": "group",
                "children": [
                    {
                        "name": "Window",
                        "type": "list",
                        "values": ["Hann", "Hamming", "Rectangular"],
                        "value": "Hann",
                    }
                ],
            },
        ],
    )


class MonitorControlPanel(QWidget):
    """PySide6 control panel with buttons and a ParameterTree editor."""

    def __init__(self, params: Parameter) -> None:
        super().__init__()
        layout = QVBoxLayout(self)

        self.tree = ParameterTree()
        self.tree.setParameters(params, showTop=False)
        layout.addWidget(self.tree)

        self.pause_button = QPushButton("Pause")
        layout.addWidget(self.pause_button)

        self.clear_button = QPushButton("Clear")
        layout.addWidget(self.clear_button)

        self.export_button = QPushButton("Export Buffer CSV")
        layout.addWidget(self.export_button)
        layout.addStretch(1)

    def set_running(self, running: bool) -> None:
        self.pause_button.setText("Pause" if running else "Resume")


class MonitorPlots(pg.GraphicsLayoutWidget):
    """PyQtGraph dashboard with time, frequency, and image plot items."""

    def __init__(self) -> None:
        super().__init__()

        # 第一幅图：这一刻的原始波形
        # 第二幅图：这一刻有哪些频率成分
        # 第三幅图：过去一段时间里，频率成分是怎么变化的

        # 创建时域波形图（第一行）：(x数组, y数组) → 一条线
        self.time_plot = self.addPlot(row=0, col=0, title="Time domain")
        self.time_plot.setLabel("bottom", "sample")  # 设置X轴标签为采样点
        self.time_plot.setLabel("left", "amplitude")  # 设置Y轴标签为幅值
        self.time_plot.showGrid(x=True, y=True, alpha=0.2)  # 显示半透明网格线
        self.time_curve = self.time_plot.plot(pen=pg.mkPen("#0072B2", width=1))  # 创建蓝色曲线

        # 创建频域幅度图（第二行）:(x数组, y数组) → 一条线
        self.freq_plot = self.addPlot(row=1, col=0, title="Frequency domain")
        self.freq_plot.setLabel("bottom", "frequency", units="Hz")  # 设置X轴标签为频率（单位Hz）
        self.freq_plot.setLabel("left", "magnitude")  # 设置Y轴标签为幅度
        self.freq_plot.showGrid(x=True, y=True, alpha=0.2)  # 显示半透明网格线
        # 固定 y 轴范围
        self.freq_plot.setYRange(0, 2, padding=0)
        self.freq_curve = self.freq_plot.plot(pen=pg.mkPen("#D55E00", width=1))  # 创建橙色曲线

        # 创建滚动频谱图（第三行）:(行, 列) 二维矩阵 → 每个像素颜色代表数值大小
        # 一个专门用来“装图片数据”的画布图层
        self.spec_plot = self.addPlot(row=2, col=0, title="Rolling spectrogram")
        self.spec_plot.setLabel("bottom", "frequency", units="Hz") # 作x辅轴
        self.spec_plot.setLabel("top", "frequency", units="bin") # 作x主轴
        self.spec_plot.setLabel("left", "history", units="frame")
        # 禁用单位倍率
        self.spec_plot.getAxis("bottom").autoSIPrefix = False
        self.spec_plot.getAxis("top").autoSIPrefix = False
        self.spec_plot.getAxis("left").autoSIPrefix = False

        # 设置xy轴的范围
        # self.spec_plot.setXRange(0, 2048, padding=0) # 两边不留白
        # self.spec_plot.setYRange(0, 120, padding=0)
   

        # 1.创建空图
        # numpy在内存中是行优先排列为一维数组
        # 所以要告诉ImageItem按步长读取，读取内容视为一行
        self.spec_image = pg.ImageItem(data=None, axisOrder="row-major")
        # spec_plot是画布，提供坐标轴、网格、标题、缩放/拖拽能力
        # spec_image是持有并渲染二维数据矩阵（热力图的像素）
        # 后续更新数据也是更新内容，不碰画布

        # 2.占位画布
        self.spec_plot.addItem(self.spec_image)  # 把图像挂到坐标轴上
        # 3.setImage 赋予像素和尺寸
        # self.spec_image.setImage(spectrogram, ...)  # 改内容（换一张新图）
        # 4.setRect 赋予坐标尺寸
        # self.spec_image.setRect(...)                  # 改内容的位置/大小

        self.spec_bottom_axis = self.spec_plot.getAxis("bottom")


    def set_time_data(self, samples: np.ndarray, values: np.ndarray) -> None:
        """设置时域波形图的数据"""
        self.time_curve.setData(samples, values)

    def set_frequency_data(
        self,
        frequencies: np.ndarray,  # 频率数组，单位Hz
        magnitude: np.ndarray,    # 对应的幅度值数组
        max_frequency: float,     # 最大频率值，用于设置X轴显示范围
    ) -> None:
        """设置频域幅度图的数据和X轴范围"""
        self.freq_curve.setData(frequencies, magnitude)
        self.freq_plot.setXRange(0, min(max_frequency, 500), padding=0)

    def set_spectrogram(
        self,
        spectrogram: np.ndarray,  # 频谱图数据，形状为 (n_frames, n_freqbins)
        sample_rate: int,
    ) -> None:
        """
        设置滚动频谱图的图像数据和显示范围
        数据怎么更新：一帧一帧滚动
        图像怎么绘制：整张图一次 setImage
        """
        # 这是一个 安全兜底 。考虑信号很弱或全是噪声的情况
        # 计算频谱数据的第99百分位数作为上限，用于动态调整颜色映射范围
        # 这样可以避免个别异常值（如尖峰噪声）导致整体图像过暗
        # percentile: 百分位数，表示将数据从小到大排序后，位于第99%位置的值
        # upper = np.percentile(spectrogram[-1], 99)
        # levels = (0, max(0.5, float(upper)))

        n_frames = spectrogram.shape[0]
        n_bins = spectrogram.shape[1]
        # setImage 赋予像素和尺寸
        self.spec_image.setImage(spectrogram, autoLevels=True)

        nyquist = sample_rate / 2
        max_bin = n_bins - 1

        # 目标 5~6 个刻度
        target_count = 5
        # 计算原始步长，然后取整到 "nice" 值
        raw_step = nyquist / target_count
        magnitude = 10 ** int(np.log10(max(raw_step, 1)))  # 量级（1, 10, 100...）
        residual = raw_step / magnitude

        if residual < 1.5:
            step = magnitude          # 如 nyquist=50 → step=10
        elif residual < 3:
            step = 2 * magnitude      # 如 nyquist=140 → step=20
        elif residual < 7:
            step = 5 * magnitude      # 如 nyquist=300 → step=50
        else:
            step = 10 * magnitude     # 如 nyquist=900 → step=100

        bottom_ticks = []
        hz = 0
        while hz <= nyquist + step * 0.01:  # 浮点兜底
            bin_pos = hz / nyquist * max_bin
            bottom_ticks.append((bin_pos, f"{hz:.0f}"))
            hz += step
        # 频率轴本质上不是直接用 Hz 画的，而是用数组的列下标画的
        self.spec_bottom_axis.setTicks([bottom_ticks])

     

        """
                        history frame →
        frequency bin
            ↑
        2048 |  □ □ □ □ □ □ □
             |  □ □ ■ ■ □ □ □
             |  □ □ ■ ■ ■ □ □
             |  □ □ □ □ ■ ■ □
             |  □ □ □ □ □ □ □
             |
         0 +--------------------→
                0        ...     119
        """


class SignalMonitor(QMainWindow):
    """Realtime controller that coordinates Qt controls and PyQtGraph plots."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PyQtGraph Practical Project - Signal Monitor")
        self.resize(1280, 760)

        self.buffer_size = 1000  # 缓冲区大小（采样点数）
        self.chunk_size = 128  # 每次采集的块大小（采样点数）
        self.sample_index = 0  # 当前采样索引（用于生成信号的时间轴）
        self.running = True

        self.buffer = np.zeros(self.buffer_size)
        self.time_axis = np.arange(self.buffer_size)
        # 初始化滚动频谱图数据矩阵
        # 形状为 (历史帧数, 频率分箱数)
        # spectrum_history: 120帧历史数据，用于水平方向（时间轴）显示
        # buffer_size // 2 + 1: FFT后的频率分箱数（实数FFT结果长度），用于垂直方向（频率轴）显示
        # 初始化为全零，表示开始时没有频谱数据
        self.spectrum_history = 120  # 频谱历史帧数（用于滚动显示）
        # 这里的 buffer_size // 2 + 1 不是“采样率的一半”，而是 rfft 之后会产生多少个频率点
        # 这里要区分两个概念：
        # 频率范围由采样率决定；
        # 频率分箱数量由 FFT 点数决定。
        # 当buffer_size=4096,self.buffer_size // 2 + 1 = 2048 + 1，刚好是Nyquist
        # 当buffer_size=4097,self.buffer_size // 2 + 1 = 2048 + 1，略小于Nyquist
        # 不论奇偶， +1 都不能省，这样才能保证宽度都是2049
        # 为什么 +1 和奇偶无关+1 加的是 bin 0（直流分量） ，不是奈奎斯特。
        # //2 得到最高 bin 编号， 
        # +1 是因为 bin 编号从 0 开始算。和奇偶完全无关。
        self.spectrogram = np.zeros((self.spectrum_history, self.buffer_size // 2 + 1))

        self.params = create_parameters()
        self.controls = MonitorControlPanel(self.params)
        self.plots = MonitorPlots()

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.addWidget(self.controls, 0)
        layout.addWidget(self.plots, 1)

        self.controls.pause_button.clicked.connect(self.toggle_running)
        self.controls.clear_button.clicked.connect(self.clear_data)
        self.controls.export_button.clicked.connect(self.choose_export_path)
        self.params.sigTreeStateChanged.connect(self.on_parameter_change)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(self.refresh_interval_ms) # 像读一个字段一样自然

        self.update_views()

    """
    它把这个 方法 变成了一个 属性 ，改变了调用方式：
        # 没有 @property —— 写成方法调用
        monitor.refresh_interval_ms()

        # 有 @property —— 写成属性访问（不用括号）
        monitor.refresh_interval_ms

        @property:可读不可写
        每次调用都从参数树重新取值
    """
    @property
    def sample_rate(self) -> int:
        # ReadOnly
        return self.params.param("Acquisition", "Sample rate").value()

    @property
    def refresh_interval_ms(self) -> int:
        # ReadOnly
        return self.params.param("Acquisition", "Refresh interval").value()

    @property
    def signal_frequency(self) -> float:
        # ReadOnly
        return self.params.param("Signal", "Frequency").value()

    @property
    def noise_level(self) -> float:
        # ReadOnly
        return self.params.param("Signal", "Noise").value()

    @property
    def window_name(self) -> str:
        # ReadOnly
        return self.params.param("Analysis", "Window").value()

    def on_parameter_change(self, param: Parameter, changes: list[tuple]) -> None:
        """Apply timer changes immediately; other settings are read on demand."""
        self.timer.setInterval(self.refresh_interval_ms)
        

    def tick(self) -> None:
        """
        Simulate acquisition, append a chunk, and refresh all views.
        1. 生成一小段新信号 chunk
        2. 把 chunk 塞进滚动缓冲区 buffer 的末尾
        3. 刷新所有图表
        """
        if not self.running:
            return
        # 每当时钟触发一次，模拟波就生成 chunk_size 个新采样点。
        sample_rate = self.sample_rate # 从参数中取值
        # chunk_axis 是这一段新数据对应的时间轴，单位是秒
        # sample_index 保证每次时间的连续性
        chunk_axis = (np.arange(self.chunk_size) + self.sample_index) / sample_rate
        # sin(2πft)
        signal = np.sin(2.0 * np.pi * self.signal_frequency * chunk_axis)
        # sin(2π2ft)
        harmonic = 0.35 * np.sin(2.0 * np.pi * self.signal_frequency * 2.0 * chunk_axis)
        noise = self.noise_level * np.random.normal(size=self.chunk_size)
        # 合成信号：基波 + 谐波 + 噪声
        # 基波是主信号，谐波是二次谐波（频率为基波的2倍），噪声用于模拟真实环境
        chunk = signal + harmonic + noise

        # sample_index 保证每次时间的连续性
        self.sample_index += self.chunk_size
        # 滚动 buffer：旧数据往前挪
        self.buffer[:-self.chunk_size] = self.buffer[self.chunk_size :]
        # 新的数据添加到末尾
        self.buffer[-self.chunk_size :] = chunk
        # 每次定时器到时间就刷新图表(尾部进来128个新数据)
        self.update_views()

    def update_views(self) -> None:
        """
        Update time plot, 
        FFT plot, 
        spectrogram 
        from the same buffer.
        """
        """设置时域数据"""
        self.plots.set_time_data(self.time_axis, self.buffer)
        
        """设置频域数据"""
        window = self.analysis_window()
        windowed = self.buffer * window  # 将缓冲区数据与选定的分析窗函数相乘，以减少频谱泄漏
        magnitude = np.abs(np.fft.rfft(windowed))  # 对加窗后的数据进行实数FFT，并取绝对值得到幅度谱
        frequencies = np.fft.rfftfreq(self.buffer_size, d=1.0 / self.sample_rate)  # 计算FFT对应的频率轴，d为采样周期
        # frequencies个数为buffer_size/2,数值范围是0～Nyquist
        # 频率上限 = sample_rate / 2
        # 频率分箱数 = buffer_size / 2 + 1
        # 频率分辨率 = sample_rate / buffer_size
        # 对于总采样数是偶数，最后一个 bin 是 Nyquist 点
        # 对于总采样数是奇数，最后一个 bin 只是最接近 Nyquist 的正频率点
        magnitude = magnitude * 2.0 / np.sum(window)
        # 对直流分量（0 Hz）进行幅度校正，除以2是因为rfft的直流分量没有对称分量
        magnitude[0] /= 2.0
        # 如果缓冲区长度为偶数，奈奎斯特频率点也没有对称分量，同样需要除以2进行校正
        if self.buffer_size % 2 == 0:
            magnitude[-1] /= 2.0
        self.plots.set_frequency_data(frequencies, magnitude, self.sample_rate / 2)
        
        """设置滚动频谱图"""
        # spectrogram(n_frames,n_freqbins)
        self.spectrogram[:-1] = self.spectrogram[1:] # 上移一帧
        self.spectrogram[-1] = magnitude
        # self.plots.set_spectrogram(self.spectrogram)
        self.plots.set_spectrogram(self.spectrogram, self.sample_rate)

    def analysis_window(self) -> np.ndarray:
        """Return the selected FFT window as an array matching the buffer."""
        if self.window_name == "Hann":
            return np.hanning(self.buffer_size)
        if self.window_name == "Hamming":
            return np.hamming(self.buffer_size)
        return np.ones(self.buffer_size)

    def toggle_running(self) -> None:
        self.running = not self.running
        self.controls.set_running(self.running)

    def clear_data(self) -> None:
        # 清空时域缓冲区，将所有采样点重置为零
        self.buffer[:] = 0.0
        # 清空频谱图历史数据，将所有帧重置为零
        self.spectrogram[:] = 0.0
        self.sample_index = 0
        self.update_views()

    def choose_export_path(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export buffer",
            "signal_buffer.csv",
            "CSV files (*.csv)",
        )
        if path:
            self.export_buffer(Path(path))

    def export_buffer(self, path: Path) -> None:
        # 表示程序到目前为止一共生成到了哪个采样位置
        # sample_numbers = np.arange(12800 - 4096, 12800)
        # 4096～12799
        # np.column_stack() 会把它们按列拼成二维表：
        # sample     value
        # 8704       0.12
        # 8705       0.18
        # 8706       0.21
        # ...        ...
        # 12799     -0.05
        sample_numbers = np.arange(self.sample_index - self.buffer_size, self.sample_index)
        data = np.column_stack([sample_numbers, self.buffer])
        np.savetxt(path, data, delimiter=",", header="sample,value", comments="")


def main() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("PyQtGraph Signal Monitor")
    app.setStyle("Fusion")
    window = SignalMonitor()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
