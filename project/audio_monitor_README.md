# Audio Monitor 麦克风实时频谱监视器

这是一个基于 PySide6、QtMultimedia、PyQtGraph 和 NumPy 的实时音频监视小项目。程序从系统麦克风采集外界声音，将原始 PCM 音频转换成浮点信号，然后同时绘制时域波形、频域频谱和滚动频谱图。

## 功能

- 使用 PySide6 `QAudioSource` 采集麦克风输入。
- 自动枚举系统输入设备，并可在左侧下拉框切换麦克风。
- 将 `Int16`、`Int32`、`UInt8`、`Float` PCM 数据解码成 `[-1.0, 1.0]` 范围内的单声道浮点信号。
- 显示最近约 2 秒的时域波形。
- 使用 4096 点 FFT 做频谱分析，频谱幅度以 dBFS 显示。
- 显示滚动频谱图，用颜色表示不同时间帧里的频率能量。
- 支持暂停/继续、清空缓存、导出当前音频 buffer 为 CSV。

## 运行方式

在仓库根目录运行：

```bash
uv run python project/audio_monitor.py
```

如果不用 `uv`，需要先确保当前 Python 环境已经安装依赖：

```bash
pip install "numpy>=2.0" "pyqtgraph" "PySide6"
python project/audio_monitor.py
```

macOS 第一次运行时可能会弹出麦克风权限请求，需要允许应用访问麦克风。

## 文件结构

```text
project/
  audio_monitor.py       程序入口，创建 QApplication 并启动主窗口
  audio_app.py           主窗口、设备管理、采集流程、buffer 和 CSV 导出
  audio_controls.py      左侧控制面板
  audio_plots.py         时域图、频谱图、滚动频谱图
  audio_processing.py    音频格式选择、PCM 解码、FFT/dBFS 计算
  audio_constants.py     共享常量
```

## 数据流

```text
麦克风设备
  ↓ QAudioSource
原始 PCM bytes
  ↓ decode_audio()
float32 单声道采样 [-1.0, 1.0]
  ↓ append_samples()
滚动时域 buffer
  ↓ update_views()
时域波形 + FFT 频谱 + 滚动频谱图
```

## 关键模块说明

### `audio_monitor.py`

入口文件。它只负责创建 `QApplication`、设置应用名称和样式，然后实例化 `AudioMonitor`。

### `audio_app.py`

主控制层。负责：

- 通过 `QMediaDevices` 查询麦克风设备。
- 根据用户选择创建 `QAudioSource`。
- 读取音频输入流。
- 维护滚动音频 buffer。
- 定时刷新图表。
- 处理暂停、清空、导出 CSV。

这里是 GUI、音频采集和绘图刷新之间的协调中心。

### `audio_processing.py`

音频处理层。负责：

- 选择合适的采集格式，优先使用 `48000 Hz / mono / Int16`。
- 将原始 PCM bytes 解码为 NumPy 数组。
- 多声道输入会按帧 reshape 后求平均，转换成单声道。
- 根据窗口函数计算 FFT。
- 将频谱幅度转换为 dBFS。

### `audio_plots.py`

绘图层。负责创建和更新三幅图：

- `Microphone waveform`：时域波形。
- `Frequency spectrum`：当前 FFT 频谱。
- `Rolling spectrogram`：频谱历史热力图。

### `audio_controls.py`

控制面板。包含：

- 输入设备下拉框。
- 刷新设备按钮。
- FFT 窗函数选择。
- 暂停/继续按钮。
- 清空按钮。
- 导出 CSV 按钮。
- 采集状态和电平显示。

## 核心概念

### `QMediaDevices` 和 `QAudioSource`

`QMediaDevices` 负责发现系统里的输入设备：

```python
self.media_devices.audioInputs()
self.media_devices.defaultAudioInput()
```

`QAudioSource` 负责使用其中一个 `QAudioDevice` 真正开始采集音频：

```python
self.audio_source = QAudioSource(device, self.audio_format, self)
self.audio_io = self.audio_source.start()
```

### PCM 解码

麦克风读出来的是原始二进制数据，不是可以直接画图的数字。`decode_audio()` 会根据 `QAudioFormat.SampleFormat` 判断每个采样点的格式，再用 `np.frombuffer()` 转成 NumPy 数组。

例如 `Int16` 音频的范围是：

```text
-32768 ~ 32767
```

代码会除以 `32768.0`，把它归一化到接近：

```text
-1.0 ~ 1.0
```

### 多声道排列

多声道 PCM 通常是交错排列：

```text
L0, R0, L1, R1, L2, R2, ...
```

代码会用：

```python
audio.reshape(-1, channel_count).mean(axis=1)
```

将每一帧的多个声道平均成一个单声道采样。

### FFT 和 dBFS

程序取最近 `FFT_SIZE = 4096` 个采样点做 FFT。频谱幅度转换为 dBFS 后显示：

```text
0 dBFS    接近满幅
-100 dBFS 显示下限
```

## 常用调整点

可以在 `audio_constants.py` 中修改这些值：

```python
DISPLAY_SECONDS = 2.0
FFT_SIZE = 4096
REFRESH_INTERVAL_MS = 40
SPECTRUM_HISTORY = 120
TARGET_SAMPLE_RATE = 48000
FREQUENCY_VIEW_LIMIT = 8000
DB_FLOOR = -100.0
```

常见修改：

- 想看更长时间的波形：增大 `DISPLAY_SECONDS`。
- 想提高频率分辨率：增大 `FFT_SIZE`。
- 想刷新更快：减小 `REFRESH_INTERVAL_MS`。
- 想看更高频率范围：增大 `FREQUENCY_VIEW_LIMIT`。

## 导出 CSV

点击 `Export Buffer CSV` 后，会导出当前时域 buffer：

```text
sample,time_seconds,value
```

其中：

- `sample`：采样编号。
- `time_seconds`：按当前采样率换算的时间。
- `value`：归一化后的音频幅值。

## 注意事项

- 如果没有波形，先确认系统麦克风权限已经打开。
- 如果下拉框没有设备，可以点击 `Refresh Devices`。
- 程序默认优先请求单声道 `Int16` 输入；如果设备不支持，会回退到设备首选格式。
- 当前项目没有使用 `sounddevice`，音频采集完全通过 PySide6 QtMultimedia 完成。
