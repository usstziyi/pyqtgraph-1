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
        previous_id = self.current_device_id()
        self.audio_devices = list(self.media_devices.audioInputs())
        names = [device.description() for device in self.audio_devices]

        if not self.audio_devices:
            self.stop_capture()
            self.controls.set_devices([], 0)
            self.controls.set_status("No microphone input device was found.")
            self.update_views()
            return

        default_id = bytes(self.media_devices.defaultAudioInput().id())
        current_index = 0
        for index, device in enumerate(self.audio_devices):
            device_id = bytes(device.id())
            if previous_id and device_id == previous_id:
                current_index = index
                break
            if not previous_id and device_id == default_id:
                current_index = index

        self.controls.set_devices(names, current_index)
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

        self.audio_format = choose_audio_format(device)
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
        if sample_rate == self.sample_rate and self.buffer.size and not reset:
            return

        self.sample_rate = sample_rate
        self.buffer_size = max(FFT_SIZE, int(sample_rate * DISPLAY_SECONDS))
        self.buffer = np.zeros(self.buffer_size, dtype=np.float32)
        self.time_axis = self._make_time_axis()
        self.spectrogram = np.full(
            (SPECTRUM_HISTORY, FFT_SIZE // 2 + 1),
            DB_FLOOR,
            dtype=np.float32,
        )
        self.sample_index = 0

    def _make_time_axis(self) -> np.ndarray:
        samples = np.arange(self.buffer_size, dtype=np.float32)
        return (samples - self.buffer_size + 1) / self.sample_rate

    def read_audio_data(self) -> None:
        if self.audio_io is None:
            return

        raw = bytes(self.audio_io.readAll())
        samples = decode_audio(raw, self.audio_format)
        if samples.size:
            self.append_samples(samples)

    def append_samples(self, samples: np.ndarray) -> None:
        count = min(samples.size, self.buffer_size)
        self.buffer[:-count] = self.buffer[count:]
        self.buffer[-count:] = samples[-count:]
        self.sample_index += samples.size

    def update_views(self) -> None:
        self.plots.set_time_data(self.time_axis, self.buffer)

        frame = self.latest_fft_frame()
        frequencies, levels_dbfs = spectrum_dbfs(frame, self.window_name)
        frequencies = frequencies * self.sample_rate

        self.plots.set_frequency_data(frequencies, levels_dbfs, self.sample_rate)
        self.spectrogram[:-1] = self.spectrogram[1:]
        self.spectrogram[-1] = levels_dbfs
        self.plots.set_spectrogram(self.spectrogram, self.sample_rate)

        rms = float(np.sqrt(np.mean(frame * frame)))
        level = 20.0 * np.log10(max(rms, 10 ** (DB_FLOOR / 20)))
        self.controls.set_level(level)

    def latest_fft_frame(self) -> np.ndarray:
        if self.buffer_size >= FFT_SIZE:
            return self.buffer[-FFT_SIZE:].astype(np.float32, copy=True)

        frame = np.zeros(FFT_SIZE, dtype=np.float32)
        frame[-self.buffer_size :] = self.buffer
        return frame

    def set_window_name(self, window_name: str) -> None:
        self.window_name = window_name

    def toggle_running(self) -> None:
        if self.audio_source is None:
            return

        if self.running:
            self.audio_source.suspend()
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
