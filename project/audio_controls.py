"""Control panel widgets for the microphone monitor."""

import numpy as np
from PySide6 import QtCore
from PySide6.QtWidgets import QComboBox, QLabel, QPushButton, QVBoxLayout, QWidget


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

        # 信号转发 (signal relay)，这是架构分层的设计模式。
        # MonitorControlPanel 对外只暴露自己的信号，主窗口不需要关心内部实现细节。
        self.device_combo.currentIndexChanged.connect(self.device_changed)
        self.window_combo.currentTextChanged.connect(self.window_changed)

    def set_devices(self, names: list[str], current_index: int) -> None:
        # 临时阻断信号，避免清空/添加条目过程中意外触发设备切换。
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
        # 检查 dBFS 值是否为有限数（非 NaN、非无穷大）
        if np.isfinite(dbfs):
            self.level_label.setText(f"Level: {dbfs:.1f} dBFS")
        else:
            # 对于无效值（如 -inf），显示为负无穷
            self.level_label.setText("Level: -inf dBFS")
