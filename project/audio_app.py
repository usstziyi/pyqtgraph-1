"""Main window and capture orchestration for the microphone monitor."""

from pathlib import Path

import numpy as np
from PySide6 import QtCore
from PySide6.QtMultimedia import QAudio, QAudioDevice, QAudioFormat, QAudioSource, QMediaDevices
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QMainWindow, QWidget

try:
    from .audio_constants import (
        DB_FLOOR,
        DISPLAY_SECONDS,
        FFT_SIZE,
        REFRESH_INTERVAL_MS,
        SPECTRUM_HISTORY,
        TARGET_SAMPLE_RATE,
    )
    from .audio_controls import MonitorControlPanel
    from .audio_plots import MonitorPlots
    from .audio_processing import choose_audio_format, decode_audio, spectrum_dbfs
except ImportError:
    from audio_constants import (
        DB_FLOOR,
        DISPLAY_SECONDS,
        FFT_SIZE,
        REFRESH_INTERVAL_MS,
        SPECTRUM_HISTORY,
        TARGET_SAMPLE_RATE,
    )
    from audio_controls import MonitorControlPanel
    from audio_plots import MonitorPlots
    from audio_processing import choose_audio_format, decode_audio, spectrum_dbfs


class AudioMonitor(QMainWindow):
    """Capture microphone samples and render waveform plus frequency analysis."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PyQtGraph Microphone Monitor")
        self.resize(1280, 760)

        # media_devices 负责发现设备，audio_devices 保存发现到的麦克风列表，
        # QAudioSource 用其中某个设备真正开始采集音频。
        self.media_devices = QMediaDevices(self)
        self.audio_devices: list[QAudioDevice] = []
        self.audio_source: QAudioSource | None = None
        self.audio_io: QtCore.QIODevice | None = None
        self.audio_format = QAudioFormat()
        self.sample_rate = TARGET_SAMPLE_RATE
        self.window_name = "Hann"
        self.running = False
        self.sample_index = 0

        # buffer可以装下整个X轴range内需要的总点数
        self.buffer_size = int(TARGET_SAMPLE_RATE * DISPLAY_SECONDS)
        self.buffer = np.zeros(self.buffer_size, dtype=np.float32)
        self.time_axis = self._make_time_axis()
        self.spectrogram = np.full(
            (SPECTRUM_HISTORY, FFT_SIZE // 2 + 1),
            DB_FLOOR,
            dtype=np.float32,
        )

        self.controls = MonitorControlPanel()
        self.plots = MonitorPlots()

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.addWidget(self.controls, 0)
        layout.addWidget(self.plots, 1)

        self.media_devices.audioInputsChanged.connect(self.refresh_audio_devices)
        self.controls.device_changed.connect(self.start_selected_device)
        self.controls.window_changed.connect(self.set_window_name)
        self.controls.refresh_devices_button.clicked.connect(self.refresh_audio_devices)
        self.controls.pause_button.clicked.connect(self.toggle_running)
        self.controls.clear_button.clicked.connect(self.clear_data)
        self.controls.export_button.clicked.connect(self.choose_export_path)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_views)
        self.timer.start(REFRESH_INTERVAL_MS)

        self.refresh_audio_devices()

    def refresh_audio_devices(self) -> None:
        # 备份当前正在使用的设备ID，以便在刷新后尝试恢复选择
        previous_id = self.current_device_id()
        # 从媒体设备中获取所有音频输入设备（麦克风）列表
        self.audio_devices = list(self.media_devices.audioInputs())
        # 提取每个设备的描述名称用于显示
        names = [device.description() for device in self.audio_devices]

        # 如果没有找到任何音频输入设备
        if not self.audio_devices:
            # 停止当前的音频采集
            self.stop_capture()
            # 清空设备列表显示
            self.controls.set_devices([], 0)
            # 设置状态提示用户没有麦克风设备
            self.controls.set_status("No microphone input device was found.")
            # 更新视图显示空状态
            self.update_views()
            return

        # 获取系统默认音频输入设备的ID
        default_id = bytes(self.media_devices.defaultAudioInput().id())
        # 初始化当前选中索引为0（第一个设备）
        current_index = 0
        # 遍历所有设备，寻找应该选中的设备
        for index, device in enumerate(self.audio_devices):
            # 获取当前遍历设备的ID
            device_id = bytes(device.id())
            # 如果之前有选中的设备，并且找到了相同的设备，则选中它
            if previous_id and device_id == previous_id:
                # 之前设备在新列表中的index
                current_index = index
                break
            # 如果之前没有选中设备，则选中系统默认设备
            if not previous_id and device_id == default_id:
                # 系统默认设备在新列表中的index
                current_index = index

        # 将设备名称列表和选中索引设置到UI控件(只更新UI没有发出信号)
        self.controls.set_devices(names, current_index)
        # 重新启动选中的设备进行音频采集(内部根据inde从audio_devices拿设备)
        self.start_selected_device(current_index)

    def current_device_id(self) -> bytes | None:
        index = self.controls.device_combo.currentIndex()
        if 0 <= index < len(self.audio_devices):
            return bytes(self.audio_devices[index].id())
        return None

    def start_selected_device(self, index: int) -> None:
        if not (0 <= index < len(self.audio_devices)):
            return
        self.start_capture(self.audio_devices[index])

    def start_capture(self, device: QAudioDevice) -> None:
        self.stop_capture()

        if device.isNull():
            self.controls.set_status("Selected microphone is not available.")
            return

        # 根据设备支持的格式选择合适的音频:采样率、通道数、采样格式
        self.audio_format = choose_audio_format(device)
        # 根据音频格式的实际采样率配置缓冲区，reset=True表示强制重置缓冲区
        self.configure_buffers(self.audio_format.sampleRate(), reset=True)

        self.audio_source = QAudioSource(device, self.audio_format, self)
        self.audio_source.stateChanged.connect(self.on_audio_state_changed)
        self.audio_io = self.audio_source.start()

        if self.audio_io is None:
            self.controls.set_status("Could not start microphone capture.")
            self.running = False
            self.controls.set_running(self.running)
            return

        self.audio_io.readyRead.connect(self.read_audio_data)
        self.running = True
        self.controls.set_running(self.running)
        self.controls.set_status(self.format_status(device))

    def stop_capture(self) -> None:
        if self.audio_io is not None:
            try:
                # 防止停止或切换设备后，旧的 readyRead 事件继续调用 read_audio_data。
                self.audio_io.readyRead.disconnect(self.read_audio_data)
            except (RuntimeError, TypeError):
                pass
            self.audio_io = None

        if self.audio_source is not None:
            self.audio_source.stop()
            self.audio_source.deleteLater()
            self.audio_source = None

        self.running = False
        self.controls.set_running(self.running)

    def configure_buffers(self, sample_rate: int, reset: bool = False) -> None:
        sample_rate = max(1, sample_rate)
        # 如果采样率没有变化，并且缓冲区已经初始化，且不需要强制重置，则直接返回
        # 避免不必要的缓冲区重新分配和初始化操作
        if sample_rate == self.sample_rate and self.buffer.size and not reset:
            return

        self.sample_rate = sample_rate
        self.buffer_size = max(FFT_SIZE, int(sample_rate * DISPLAY_SECONDS))
        self.buffer = np.zeros(self.buffer_size, dtype=np.float32)
        self.time_axis = self._make_time_axis()
        
        # 初始化频谱图数据：使用DB_FLOOR作为初始值，创建二维数组存储历史频谱数据
        # 行数为SPECTRUM_HISTORY（时间维度），列数为FFT_SIZE // 2 + 1（频率维度）
        self.spectrogram = np.full(
            (SPECTRUM_HISTORY, FFT_SIZE // 2 + 1),
            DB_FLOOR,
            dtype=np.float32,
        )
        self.sample_index = 0

    def _make_time_axis(self) -> np.ndarray:
        # 生成时间轴数组，表示缓冲区中每个样本对应的时间点（秒）
        # 时间范围从 -(buffer_size-1)/sample_rate 到 0，即最近 buffer_size 个样本的时间序列
        # -2～0，均分为buffer_size份
        samples = np.arange(self.buffer_size, dtype=np.float32)
        return (samples - (self.buffer_size - 1)) / self.sample_rate

    def read_audio_data(self) -> None:
        if self.audio_io is None:
            return

        raw = bytes(self.audio_io.readAll())
        # samples长度和定时器间隔时长有关
        samples = decode_audio(raw, self.audio_format)
        if samples.size:
            self.append_samples(samples)

    def append_samples(self, samples: np.ndarray) -> None:
        count = min(samples.size, self.buffer_size)
        # 往前推count个数据(0.04*48000=1920)
        self.buffer[:-count] = self.buffer[count:]
        self.buffer[-count:] = samples[-count:]
        # 程序从开始采集到现在，一共接收过多少个采样点,它主要用于导出 CSV
        self.sample_index += samples.size

    def update_views(self) -> None:
        # buffer由QAudioSource(Qt 底层线程采集)控制
        # 主线程只负责显示这个buffer
        self.plots.set_time_data(self.time_axis, self.buffer)

        frame = self.latest_fft_frame()
        frequencies, levels_dbfs = spectrum_dbfs(
            frame,
            self.window_name,
            self.sample_rate,
        )
        self.plots.set_frequency_data(frequencies, levels_dbfs, self.sample_rate)

        # 往前推一个
        self.spectrogram[:-1] = self.spectrogram[1:]
        self.spectrogram[-1] = levels_dbfs
        self.plots.set_spectrogram(self.spectrogram, self.sample_rate)

        # 计算当前音频帧的RMS（均方根）值，用于表示音频信号的强度
        rms = float(np.sqrt(np.mean(frame ** 2)))
        # 将RMS转换为分贝值，使用DB_FLOOR作为最小值防止log10(0)错误
        level = 20.0 * np.log10(max(rms, 10 ** (DB_FLOOR / 20)))
        # 更新UI显示当前音频电平
        self.controls.set_level(level)

    def latest_fft_frame(self) -> np.ndarray:
        """获取最新的FFT帧数据用于频谱分析。
        当缓冲区数据足够时，返回最后FFT_SIZE个样本；
        当缓冲区数据不足时，返回补零后的FFT_SIZE长度数组。
        和定时器时间间隔没有绝对关系。  
        Returns:
            np.ndarray: 长度为FFT_SIZE的float32数组，包含用于FFT计算的音频样本
        """
        # 检查缓冲区大小是否足够进行FFT计算
        if self.buffer_size >= FFT_SIZE:
            # 如果缓冲区足够大，直接返回最后FFT_SIZE个样本，并确保类型为float32
            return self.buffer[-FFT_SIZE:].astype(np.float32, copy=True)

        # 刚启动如果缓冲区不够大，创建一个全零的FFT帧数组
        frame = np.zeros(FFT_SIZE, dtype=np.float32)
        # 将缓冲区中的数据填充到帧数组的末尾部分
        frame[-self.buffer_size :] = self.buffer
        # 返回填充后的帧数组
        return frame

    def set_window_name(self, window_name: str) -> None:
        self.window_name = window_name

    def toggle_running(self) -> None:
        if self.audio_source is None:
            return

        if self.running:
            self.audio_source.suspend()
            # 数据流断了 — 音频源被挂起后， readyRead 信号不再发射
            # 所以 read_audio_data 不再被调用， append_samples 不再往缓冲区写入新数据。
            self.running = False
        else:
            self.audio_source.resume()
            self.running = True
        self.controls.set_running(self.running)

    def on_audio_state_changed(self, state: QAudio.State) -> None:
        if self.audio_source is None:
            return

        if state == QAudio.State.SuspendedState:
            self.controls.set_status("Microphone capture is paused.")
            return

        if state == QAudio.State.StoppedState:
            error = self.audio_source.error()
            if error != QAudio.Error.NoError:
                self.controls.set_status(f"Microphone stopped: {error.name}")

    def clear_data(self) -> None:
        self.buffer[:] = 0.0
        self.spectrogram[:] = DB_FLOOR
        self.sample_index = 0
        self.update_views()

    def choose_export_path(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export microphone buffer",
            "microphone_buffer.csv",
            "CSV files (*.csv)",
        )
        if path:
            self.export_buffer(Path(path))

    def export_buffer(self, path: Path) -> None:
        sample_numbers = np.arange(
            self.sample_index - self.buffer_size,
            self.sample_index,
        )
        times = sample_numbers / self.sample_rate
        data = np.column_stack([sample_numbers, times, self.buffer])
        np.savetxt(
            path,
            data,
            delimiter=",",
            header="sample,time_seconds,value",
            comments="",
        )

    def format_status(self, device: QAudioDevice) -> str:
        sample_format = self.audio_format.sampleFormat().name
        return (
            f"Capturing: {device.description()}\n"
            f"{self.audio_format.sampleRate()} Hz, "
            f"{self.audio_format.channelCount()} channel(s), {sample_format}"
        )
