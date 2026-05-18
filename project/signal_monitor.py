"""Practical project: a realtime signal monitor built with PyQtGraph."""

from pathlib import Path

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
from pyqtgraph.parametertree import Parameter, ParameterTree


class SignalMonitor(QtWidgets.QMainWindow):
    """Realtime time-domain, frequency-domain, and spectrogram dashboard."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PyQtGraph Practical Project - Signal Monitor")
        self.resize(1280, 760)

        self.buffer_size = 4096
        self.chunk_size = 128
        self.spectrum_history = 120
        self.sample_index = 0
        self.running = True

        self.buffer = np.zeros(self.buffer_size)
        self.time_axis = np.arange(self.buffer_size)
        self.spectrogram = np.zeros((self.spectrum_history, self.buffer_size // 2 + 1))

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QHBoxLayout(central)

        left = QtWidgets.QVBoxLayout()
        layout.addLayout(left, 0)

        self.params = self.create_parameters()
        self.tree = ParameterTree()
        self.tree.setParameters(self.params, showTop=False)
        left.addWidget(self.tree)

        self.pause_button = QtWidgets.QPushButton("Pause")
        self.pause_button.clicked.connect(self.toggle_running)
        left.addWidget(self.pause_button)

        clear_button = QtWidgets.QPushButton("Clear")
        clear_button.clicked.connect(self.clear_data)
        left.addWidget(clear_button)

        export_button = QtWidgets.QPushButton("Export Buffer CSV")
        export_button.clicked.connect(self.choose_export_path)
        left.addWidget(export_button)
        left.addStretch(1)

        self.graphics = pg.GraphicsLayoutWidget()
        layout.addWidget(self.graphics, 1)

        self.time_plot = self.graphics.addPlot(row=0, col=0, title="Time domain")
        self.time_plot.setLabel("bottom", "sample")
        self.time_plot.setLabel("left", "amplitude")
        self.time_plot.showGrid(x=True, y=True, alpha=0.2)
        self.time_curve = self.time_plot.plot(pen=pg.mkPen("#0072B2", width=1))

        self.freq_plot = self.graphics.addPlot(row=1, col=0, title="Frequency domain")
        self.freq_plot.setLabel("bottom", "frequency", units="Hz")
        self.freq_plot.setLabel("left", "magnitude")
        self.freq_plot.showGrid(x=True, y=True, alpha=0.2)
        self.freq_curve = self.freq_plot.plot(pen=pg.mkPen("#D55E00", width=1))

        self.spec_plot = self.graphics.addPlot(row=2, col=0, title="Rolling spectrogram")
        self.spec_plot.setLabel("bottom", "history frame")
        self.spec_plot.setLabel("left", "frequency bin")
        self.spec_image = pg.ImageItem(axisOrder="row-major")
        self.spec_plot.addItem(self.spec_image)

        self.params.sigTreeStateChanged.connect(self.on_parameter_change)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(self.refresh_interval_ms)

        self.update_views()

    @staticmethod
    def create_parameters() -> Parameter:
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

    @property
    def sample_rate(self) -> int:
        return self.params.param("Acquisition", "Sample rate").value()

    @property
    def refresh_interval_ms(self) -> int:
        return self.params.param("Acquisition", "Refresh interval").value()

    @property
    def signal_frequency(self) -> float:
        return self.params.param("Signal", "Frequency").value()

    @property
    def noise_level(self) -> float:
        return self.params.param("Signal", "Noise").value()

    @property
    def window_name(self) -> str:
        return self.params.param("Analysis", "Window").value()

    def on_parameter_change(self, param: Parameter, changes: list[tuple]) -> None:
        """Apply timer changes immediately; other settings are read on demand."""
        self.timer.setInterval(self.refresh_interval_ms)

    def tick(self) -> None:
        """Simulate acquisition, append a chunk, and refresh all views."""
        if not self.running:
            return

        sample_rate = self.sample_rate
        chunk_axis = (np.arange(self.chunk_size) + self.sample_index) / sample_rate
        signal = np.sin(2.0 * np.pi * self.signal_frequency * chunk_axis)
        harmonic = 0.35 * np.sin(2.0 * np.pi * self.signal_frequency * 2.0 * chunk_axis)
        noise = self.noise_level * np.random.normal(size=self.chunk_size)
        chunk = signal + harmonic + noise

        self.sample_index += self.chunk_size
        self.buffer[:-self.chunk_size] = self.buffer[self.chunk_size :]
        self.buffer[-self.chunk_size :] = chunk
        self.update_views()

    def update_views(self) -> None:
        """Update time plot, FFT plot, and spectrogram from the same buffer."""
        self.time_curve.setData(self.time_axis, self.buffer)

        windowed = self.buffer * self.analysis_window()
        magnitude = np.abs(np.fft.rfft(windowed))
        frequencies = np.fft.rfftfreq(self.buffer_size, d=1.0 / self.sample_rate)

        self.freq_curve.setData(frequencies, magnitude)
        self.freq_plot.setXRange(0, min(self.sample_rate / 2, 500), padding=0)

        self.spectrogram[:-1] = self.spectrogram[1:]
        self.spectrogram[-1] = magnitude
        self.spec_image.setImage(self.spectrogram.T, autoLevels=False, levels=(0, max(1.0, magnitude.max())))

    def analysis_window(self) -> np.ndarray:
        """Return the selected FFT window as an array matching the buffer."""
        if self.window_name == "Hann":
            return np.hanning(self.buffer_size)
        if self.window_name == "Hamming":
            return np.hamming(self.buffer_size)
        return np.ones(self.buffer_size)

    def toggle_running(self) -> None:
        self.running = not self.running
        self.pause_button.setText("Pause" if self.running else "Resume")

    def clear_data(self) -> None:
        self.buffer[:] = 0.0
        self.spectrogram[:] = 0.0
        self.sample_index = 0
        self.update_views()

    def choose_export_path(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export buffer",
            "signal_buffer.csv",
            "CSV files (*.csv)",
        )
        if path:
            self.export_buffer(Path(path))

    def export_buffer(self, path: Path) -> None:
        sample_numbers = np.arange(self.sample_index - self.buffer_size, self.sample_index)
        data = np.column_stack([sample_numbers, self.buffer])
        np.savetxt(path, data, delimiter=",", header="sample,value", comments="")


def main() -> None:
    app = pg.mkQApp("PyQtGraph Signal Monitor")
    window = SignalMonitor()
    window.show()
    pg.exec()


if __name__ == "__main__":
    main()
