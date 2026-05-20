"""
音频常量
Shared configuration values for the microphone monitor.
"""

DISPLAY_SECONDS = 2.0  # 显示时长（秒）
FFT_SIZE = 4096  # FFT 窗口大小
REFRESH_INTERVAL_MS = 40  # 刷新间隔（毫秒）
SPECTRUM_HISTORY = 120  # 频谱历史记录数量
TARGET_SAMPLE_RATE = 48000  # 目标采样率（Hz）
FREQUENCY_VIEW_LIMIT = 8000  # 频率显示上限（Hz）
DB_FLOOR = -100.0  # 分贝下限（dB）


"""
定时器每 40 ms 刷新一次图
而
表示每次 FFT 使用最近 4096 个采样点，对应时间长度是：
4096 / 48000 ≈ 0.0853 秒 ≈ 85 ms
它意味着相邻两次 FFT 窗口是重叠的

时间 →
[--------- 85 ms FFT 窗口 ---------]
                    [--------- 85 ms FFT 窗口 ---------]
                                        [--------- 85 ms FFT 窗口 ---------]
刷新间隔：40 ms

相邻窗口重叠约：
85 - 40 = 45 ms，也就是大约 53% 重叠。

这种做法在实时频谱里很常见，叫做 overlap。好处是：
显示更流畅
如果每 85 ms 才刷新一次，频谱图变化会更跳。
频率分辨率保持不变
"""