"""Audio format selection, PCM decoding, and FFT helpers."""

import numpy as np
from PySide6.QtMultimedia import QAudioDevice, QAudioFormat

try:
    from .audio_constants import DB_FLOOR, FFT_SIZE, TARGET_SAMPLE_RATE
except ImportError:
    from audio_constants import DB_FLOOR, FFT_SIZE, TARGET_SAMPLE_RATE


def choose_audio_format(device: QAudioDevice) -> QAudioFormat:
    """Prefer mono Int16 at the target rate, then fall back to supported formats."""
    preferred = device.preferredFormat()

    requested = QAudioFormat()
    requested.setSampleRate(target_sample_rate(device, preferred.sampleRate()))
    requested.setChannelCount(target_channel_count(device))
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


def target_sample_rate(device: QAudioDevice, fallback: int) -> int:
    minimum = device.minimumSampleRate()
    maximum = device.maximumSampleRate()
    if minimum <= TARGET_SAMPLE_RATE <= maximum:
        return TARGET_SAMPLE_RATE
    if minimum <= fallback <= maximum:
        return fallback
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


def analysis_window(window_name: str) -> np.ndarray:
    if window_name == "Hann":
        return np.hanning(FFT_SIZE).astype(np.float32)
    if window_name == "Hamming":
        return np.hamming(FFT_SIZE).astype(np.float32)
    return np.ones(FFT_SIZE, dtype=np.float32)


def spectrum_dbfs(frame: np.ndarray, window_name: str) -> tuple[np.ndarray, np.ndarray]:
    window = analysis_window(window_name)
    windowed = frame * window
    spectrum = np.abs(np.fft.rfft(windowed))
    coherent_gain = max(float(np.sum(window)) / 2.0, 1.0)
    amplitude = spectrum / coherent_gain
    amplitude[0] /= 2.0
    amplitude[-1] /= 2.0
    levels_dbfs = 20.0 * np.log10(np.maximum(amplitude, 10 ** (DB_FLOOR / 20)))
    frequencies = np.fft.rfftfreq(FFT_SIZE)
    return frequencies, levels_dbfs
