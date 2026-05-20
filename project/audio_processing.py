"""Audio format selection, PCM decoding, and FFT helpers."""
"""音频格式选择，PCM解码，和FFT的帮助。"""

import numpy as np
from PySide6.QtMultimedia import QAudioDevice, QAudioFormat

try:
    from .audio_constants import DB_FLOOR, FFT_SIZE, TARGET_SAMPLE_RATE
except ImportError:
    from audio_constants import DB_FLOOR, FFT_SIZE, TARGET_SAMPLE_RATE

"""音频解码部分"""
def choose_audio_format(device: QAudioDevice) -> QAudioFormat:
    """Prefer mono Int16 at the target rate, then fall back to supported formats."""
    """在目标速率下首选:单声道+Int16，否则退回到支持的格式。"""
    preferred = device.preferredFormat()

    requested = QAudioFormat()
    requested.setSampleRate(target_sample_rate(device, preferred.sampleRate()))
    requested.setChannelCount(target_channel_count(device))
    requested.setSampleFormat(QAudioFormat.SampleFormat.Int16)
    # 驱动上再次确认
    if device.isFormatSupported(requested):
        return requested
    # 如果目标采样率不支持，直接用设备偏好的采样率
    int16_preferred_rate = QAudioFormat()
    int16_preferred_rate.setSampleRate(preferred.sampleRate())
    int16_preferred_rate.setChannelCount(preferred.channelCount())
    int16_preferred_rate.setSampleFormat(QAudioFormat.SampleFormat.Int16)
    if device.isFormatSupported(int16_preferred_rate):
        return int16_preferred_rate

    return preferred

# 数值上初步检测
def target_sample_rate(device: QAudioDevice, fallback: int) -> int:
    """根据设备支持的采样率范围，选择最合适的采样率。"""
    minimum = device.minimumSampleRate()
    maximum = device.maximumSampleRate()
    # 如果目标采样率在设备支持的范围内，直接使用目标采样率
    if minimum <= TARGET_SAMPLE_RATE <= maximum:
        return TARGET_SAMPLE_RATE
    # 如果回退采样率在设备支持的范围内，使用回退采样率
    if minimum <= fallback <= maximum:
        return fallback
    # 否则，将目标采样率限制在设备支持的最小和最大采样率之间
    return max(min(TARGET_SAMPLE_RATE, maximum), minimum)


def target_channel_count(device: QAudioDevice) -> int:
    if device.minimumChannelCount() <= 1 <= device.maximumChannelCount():
        return 1
    return device.minimumChannelCount()


def decode_audio(raw: bytes, audio_format: QAudioFormat) -> np.ndarray:
    """Decode raw PCM bytes into mono float32 samples in the [-1.0, 1.0] range."""
    sample_format = audio_format.sampleFormat()
    channel_count = max(1, audio_format.channelCount())

    # 根据 Qt 给出的采样格式，决定怎样解释原始二进制音频数据。
    if sample_format == QAudioFormat.SampleFormat.Int16:
        sample_width = np.dtype(np.int16).itemsize
        dtype = np.int16
        scale = 32768.0  # 2^15
        offset = 0.0
    elif sample_format == QAudioFormat.SampleFormat.Int32:
        sample_width = np.dtype(np.int32).itemsize
        dtype = np.int32
        scale = 2147483648.0  # 2^31
        offset = 0.0
    elif sample_format == QAudioFormat.SampleFormat.UInt8:
        sample_width = np.dtype(np.uint8).itemsize
        dtype = np.uint8
        scale = 128.0  # 2^7
        offset = -128.0
    elif sample_format == QAudioFormat.SampleFormat.Float:
        sample_width = np.dtype(np.float32).itemsize
        dtype = np.float32
        scale = 1.0
        offset = 0.0
    else:
        return np.empty(0, dtype=np.float32)

    # 多声道音频通常是交错排列：L0, R0, L1, R1, ...
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

"""FFT计算部分"""
def analysis_window(window_name: str) -> np.ndarray:
    if window_name == "Hann":
        return np.hanning(FFT_SIZE).astype(np.float32)
    if window_name == "Hamming":
        return np.hamming(FFT_SIZE).astype(np.float32)
    return np.ones(FFT_SIZE, dtype=np.float32)

# decibels relative to full scale 
# 相对于数字音频最大满幅值的分贝 
# 表示：当前数字音频信号离系统能表示的最大幅度还有多远
def spectrum_dbfs(
    frame: np.ndarray,
    window_name: str,
    sample_rate: int,
) -> tuple[np.ndarray, np.ndarray]:
    window = analysis_window(window_name)
    windowed = frame * window
    # 对加窗后的信号进行实数FFT变换，并取幅度谱
    # rfft (Real FFT) 对实数输入信号进行快速傅里叶变换
    # 由于输入是实数，FFT结果具有共轭对称性，rfft只返回非负频率部分（0到Nyquist频率）
    # 相比完整的fft，rfft计算量减半，返回的频谱长度为FFT_SIZE/2+1
    # np.abs() 计算复数频谱的模值，得到幅度谱
    spectrum = np.abs(np.fft.rfft(windowed))
    # 计算相干增益：窗函数所有采样点的和除以2，确保至少为1.0
    # 这是为了补偿加窗操作造成的能量损失，使FFT结果的幅度能正确反映原始信号
    coherent_gain = max(float(np.sum(window)) / 2.0, 1.0)
    # 将FFT幅度谱除以相干增益进行归一化，得到校正后的幅度值
    amplitude = spectrum / coherent_gain
    # 对直流分量(DC)和奈奎斯特频率分量进行幅度修正
    # 这两个频率分量在实数FFT中只有实部，没有虚部，能量只集中在单一频率点
    # 而其他频率分量是共轭对称的，能量分布在正负频率两个点上
    # 因此需要将这两个特殊分量的幅度除以2，以保持与其他频率分量的能量一致性
    amplitude[0] /= 2.0
    amplitude[-1] /= 2.0
    # 将幅度转换为 dBFS（相对于数字满幅的分贝值）
    # 公式：dBFS = 20 * log10(幅度)
    # 使用 np.maximum 限制最小幅度值，避免 log10(0) 产生 -inf
    # 最小幅度值由 DB_FLOOR 计算得出：10^(DB_FLOOR/20)
    # 例如 DB_FLOOR = -120 时，最小幅度约为 10^-6
    levels_dbfs = 20.0 * np.log10(np.maximum(amplitude, 10 ** (DB_FLOOR / 20)))
    # len(frequencies) = FFT_SIZE / 2 + 1
    frequencies = np.fft.rfftfreq(FFT_SIZE, d=1.0 / sample_rate)
    return frequencies, levels_dbfs
