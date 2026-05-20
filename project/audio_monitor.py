"""Realtime microphone monitor built with PySide6 QtMultimedia and PyQtGraph."""

from pathlib import Path
import sys

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore
from PySide6.QtMultimedia import (
    QAudio, 
    QAudioDevice, 
    QAudioFormat, 
    QAudioSource, 
    QMediaDevices
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


DISPLAY_SECONDS = 2.0
FFT_SIZE = 4096
REFRESH_INTERVAL_MS = 40
SPECTRUM_HISTORY = 120
TARGET_SAMPLE_RATE = 48000
FREQUENCY_VIEW_LIMIT = 8000
DB_FLOOR = -100.0


class MonitorControlPanel(QWidget):
    """Compact controls for choosing an input device and operating capture."""

    device_changed = QtCore.Signal(int)
    window_changed = QtCore.Signal(str)

    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Input device"))
        self.device_combo = QComboBox()
        layout.addWidget(self.device_combo)

        self.refresh_devices_button = QPushButton("Refresh Devices")
        layout.addWidget(self.refresh_devices_button)

        layout.addWidget(QLabel("FFT window"))
        self.window_combo = QComboBox()
        self.window_combo.addItems(["Hann", "Hamming", "Rectangular"])
        layout.addWidget(self.window_combo)

        self.pause_button = QPushButton("Pause")
        layout.addWidget(self.pause_button)

        self.clear_button = QPushButton("Clear")
        layout.addWidget(self.clear_button)

        self.export_button = QPushButton("Export Buffer CSV")
        layout.addWidget(self.export_button)

        self.status_label = QLabel("Waiting for microphone...")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.level_label = QLabel("Level: -inf dBFS")
        layout.addWidget(self.level_label)

        layout.addStretch(1)

        self.device_combo.currentIndexChanged.connect(self.device_changed)
        self.window_combo.currentTextChanged.connect(self.window_changed)

    def set_devices(self, names: list[str], current_index: int) -> None:
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        self.device_combo.addItems(names)
        if names:
            self.device_combo.setCurrentIndex(current_index)
        self.device_combo.blockSignals(False)
        self.device_combo.setEnabled(bool(names))

    def set_running(self, running: bool) -> None:
        self.pause_button.setText("Pause" if running else "Resume")

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def set_level(self, dbfs: float) -> None:
        if np.isfinite(dbfs):
            self.level_label.setText(f"Level: {dbfs:.1f} dBFS")
        else:
            self.level_label.setText("Level: -inf dBFS")


class MonitorPlots(pg.GraphicsLayoutWidget):
    """PyQtGraph dashboard with waveform, spectrum, and rolling spectrogram."""

    def __init__(self) -> None:
        super().__init__()

        self.time_plot = self.addPlot(row=0, col=0, title="Microphone waveform")
        self.time_plot.setLabel("bottom", "time", units="s")
        self.time_plot.setLabel("left", "amplitude")
        self.time_plot.setYRange(-1.0, 1.0, padding=0)
        self.time_plot.showGrid(x=True, y=True, alpha=0.2)
        self.time_curve = self.time_plot.plot(pen=pg.mkPen("#0072B2", width=1))

        self.freq_plot = self.addPlot(row=1, col=0, title="Frequency spectrum")
        self.freq_plot.setLabel("bottom", "frequency", units="Hz")
        self.freq_plot.setLabel("left", "level", units="dBFS")
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


class AudioMonitor(QMainWindow):
    """Capture microphone samples and render waveform plus frequency analysis."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PyQtGraph Microphone Monitor")
        self.resize(1280, 760)

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

        self.media_devices = QMediaDevices(self)
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

        self.audio_format = self.choose_audio_format(device)
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

    def choose_audio_format(
        self,
        device: QAudioDevice,
    ) -> QAudioFormat:
        preferred = device.preferredFormat()

        requested = QAudioFormat()
        requested.setSampleRate(self.target_sample_rate(device, preferred.sampleRate()))
        requested.setChannelCount(self.target_channel_count(device))
        requested.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        if device.isFormatSupported(requested):
            return requested

        int16_preferred_rate = QAudioFormat()
        int16_preferred_rate.setSampleRate(preferred.sampleRate())
        int16_preferred_rate.setChannelCount(preferred.channelCount())
        int16_preferred_rate.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        if device.isFormatSupported(int16_preferred_rate):
            return int16_preferred_rate

        return preferred

    def target_sample_rate(
        self,
        device: QAudioDevice,
        fallback: int,
    ) -> int:
        minimum = device.minimumSampleRate()
        maximum = device.maximumSampleRate()
        if minimum <= TARGET_SAMPLE_RATE <= maximum:
            return TARGET_SAMPLE_RATE
        if minimum <= fallback <= maximum:
            return fallback
        return max(min(TARGET_SAMPLE_RATE, maximum), minimum)

    def target_channel_count(self, device: QAudioDevice) -> int:
        if device.minimumChannelCount() <= 1 <= device.maximumChannelCount():
            return 1
        return device.minimumChannelCount()

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
        samples = self.decode_audio(raw, self.audio_format)
        if samples.size:
            self.append_samples(samples)

    def decode_audio(
        self,
        raw: bytes,
        audio_format: QAudioFormat,
    ) -> np.ndarray:
        sample_format = audio_format.sampleFormat()
        channel_count = max(1, audio_format.channelCount())

        if sample_format == QAudioFormat.SampleFormat.Int16:
            sample_width = np.dtype(np.int16).itemsize
            dtype = np.int16
            scale = 32768.0
            offset = 0.0
        elif sample_format == QAudioFormat.SampleFormat.Int32:
            sample_width = np.dtype(np.int32).itemsize
            dtype = np.int32
            scale = 2147483648.0
            offset = 0.0
        elif sample_format == QAudioFormat.SampleFormat.UInt8:
            sample_width = np.dtype(np.uint8).itemsize
            dtype = np.uint8
            scale = 128.0
            offset = -128.0
        elif sample_format == QAudioFormat.SampleFormat.Float:
            sample_width = np.dtype(np.float32).itemsize
            dtype = np.float32
            scale = 1.0
            offset = 0.0
        else:
            return np.empty(0, dtype=np.float32)

        frame_width = sample_width * channel_count
        usable_bytes = len(raw) - (len(raw) % frame_width)
        if usable_bytes <= 0:
            return np.empty(0, dtype=np.float32)

        audio = np.frombuffer(raw[:usable_bytes], dtype=dtype).astype(np.float32)
        if offset:
            audio += offset
        audio /= scale

        if channel_count > 1:
            audio = audio.reshape(-1, channel_count).mean(axis=1)

        return np.clip(audio, -1.0, 1.0)

    def append_samples(self, samples: np.ndarray) -> None:
        count = min(samples.size, self.buffer_size)
        self.buffer[:-count] = self.buffer[count:]
        self.buffer[-count:] = samples[-count:]
        self.sample_index += samples.size

    def update_views(self) -> None:
        self.plots.set_time_data(self.time_axis, self.buffer)

        frame = self.latest_fft_frame()
        window = self.analysis_window()
        windowed = frame * window
        spectrum = np.abs(np.fft.rfft(windowed))
        coherent_gain = max(float(np.sum(window)) / 2.0, 1.0)
        amplitude = spectrum / coherent_gain
        amplitude[0] /= 2.0
        amplitude[-1] /= 2.0
        levels_dbfs = 20.0 * np.log10(np.maximum(amplitude, 10 ** (DB_FLOOR / 20)))
        frequencies = np.fft.rfftfreq(FFT_SIZE, d=1.0 / self.sample_rate)

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

    def analysis_window(self) -> np.ndarray:
        if self.window_name == "Hann":
            return np.hanning(FFT_SIZE).astype(np.float32)
        if self.window_name == "Hamming":
            return np.hamming(FFT_SIZE).astype(np.float32)
        return np.ones(FFT_SIZE, dtype=np.float32)

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


def main() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("PyQtGraph Microphone Monitor")
    app.setStyle("Fusion")
    window = AudioMonitor()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
