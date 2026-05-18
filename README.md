# PyQtGraph 循序渐进学习计划

这套材料参考了 PyQtGraph 官方文档与 GitHub 仓库说明，目标是从“能画一条曲线”推进到“能写一个小型实时信号监控工具”。每个 unit 都是一个独立 Python 脚本，建议按顺序阅读、运行、改参数、观察交互效果。

## 参考资料

- 官方文档：<https://pyqtgraph.readthedocs.io/en/latest/>
- Getting Started：<https://pyqtgraph.readthedocs.io/en/latest/getting_started/index.html>
- Plotting 指南：<https://pyqtgraph.readthedocs.io/en/latest/getting_started/plotting.html>
- Images and video：<https://pyqtgraph.readthedocs.io/en/latest/getting_started/images.html>
- ParameterTree：<https://pyqtgraph.readthedocs.io/en/latest/api_reference/parametertree/index.html>
- GitHub 仓库：<https://github.com/pyqtgraph/pyqtgraph>

官方 GitHub README 提醒：最容易的学习方式是运行示例浏览器：

```bash
python -m pyqtgraph.examples
```

## 依赖清单

这里只列依赖，不安装环境。PyQtGraph latest 文档和 GitHub README 当前说明的核心要求是 Python 3.12+、NumPy 2.0+，以及 PyQt5、PyQt6、PySide6 之一；Qt 版本要求为 Qt 5.15 或 Qt 6.8+。任选一个 Qt 绑定即可，推荐先用 PySide6：

```bash
pip install "pyqtgraph" "numpy>=2.0" "PySide6"
```

可选增强：

```bash
pip install scipy matplotlib colorcet h5py pyopengl
```

说明：

- `pyqtgraph`：核心绘图与 GUI 组件。
- `numpy`：生成和处理数组数据。
- `PySide6` / `PyQt6` / `PyQt5`：三选一，PyQtGraph 通过 `pyqtgraph.Qt` 做兼容抽象。
- `scipy`：滤波、图像处理等高级数值功能。
- `matplotlib`：部分导出和颜色映射功能。
- `pyopengl`：3D 可视化。

## 学习路径

### Unit 01：基础曲线、散点和坐标轴

文件：[unit01_plot_basics.py](units/unit01_plot_basics.py)

目标：

- 理解 `PlotWidget`、`PlotItem`、`PlotDataItem` 的关系。
- 使用 `plot()` 绘制曲线和散点。
- 设置标题、坐标轴、图例、网格、画笔和符号。

练习：

- 把 `sin` 改成不同频率。
- 给散点增加透明度。
- 尝试 `pen=None` 只显示点。

### Unit 02：把 PyQtGraph 嵌入 Qt 布局

文件：[unit02_qt_layout_signals.py](units/unit02_qt_layout_signals.py)

目标：

- 建立 `QMainWindow`、`QWidget`、`QGridLayout`。
- 使用 `QDoubleSpinBox`、`QCheckBox` 控制图形。
- 理解 Qt signal/slot 与 PyQtGraph 更新曲线的配合。

练习：

- 增加一个振幅控件。
- 增加一条余弦曲线。
- 将网格开关改成两个独立的 X/Y 网格开关。

### Unit 03：实时曲线和 QTimer

文件：[unit03_realtime_timer.py](units/unit03_realtime_timer.py)

目标：

- 用 `QTimer` 定时更新数据。
- 区分“重新 plot”与“复用曲线对象后 `setData()`”。
- 学会限制缓存长度，避免实时程序越跑越慢。

练习：

- 修改刷新间隔，观察 CPU 和流畅度。
- 把随机噪声改成模拟传感器数据。
- 增加 pause/resume 按钮的状态提示。

### Unit 04：图像、直方图和 ROI

文件：[unit04_imageview_roi.py](units/unit04_imageview_roi.py)

目标：

- 使用 `ImageView` 显示二维数组。
- 理解灰度数据到屏幕颜色的映射。
- 使用 `RectROI` 截取局部区域并计算统计量。

练习：

- 改变图像生成函数。
- 添加 `LineSegmentROI`。
- 将 ROI 统计写入 CSV。

### Unit 05：ParameterTree 参数面板

文件：[unit05_parameter_tree.py](units/unit05_parameter_tree.py)

目标：

- 用 `Parameter` 表示参数模型。
- 用 `ParameterTree` 自动生成可编辑 UI。
- 把参数变化同步到曲线样式和数据。

练习：

- 增加 `Noise` 参数。
- 增加 `Phase` 参数。
- 增加一个按钮参数，用于随机换色。

### Unit 06：导出和性能习惯

文件：[unit06_export_performance.py](units/unit06_export_performance.py)

目标：

- 对大数组使用 downsampling 和 clip-to-view。
- 导出 CSV 和 PNG。
- 把数据生成、绘图、导出拆成清晰函数。

练习：

- 尝试 10 万、100 万、500 万个点。
- 对比 downsampling 开关的交互体验。
- 给导出文件名增加时间戳。

## 实战项目：实时信号监控台

文件：[project/signal_monitor.py](project/signal_monitor.py)

项目功能：

- 合成一段实时信号流。
- 显示时域波形。
- 显示频谱。
- 显示滚动频谱图。
- 通过 ParameterTree 调整采样率、主频、噪声、窗口函数、刷新间隔。
- 支持暂停、清空和导出当前缓存 CSV。

建议实现顺序：

1. 先读 Unit 01，理解绘图对象。
2. 再读 Unit 02，理解 Qt 布局和信号。
3. 用 Unit 03 掌握实时刷新方式。
4. 用 Unit 04 理解图像和 ROI，因为实战项目的频谱图本质上也是二维图像。
5. 用 Unit 05 接管项目参数。
6. 用 Unit 06 补齐性能和导出。

## 代码审查记录

逐单元审查和修正记录在 [CODE_REVIEW.md](CODE_REVIEW.md)。我采用了三层检查：

- 语法编译：`python3 -m py_compile`
- API 静态审查：检查 PyQtGraph / Qt 常见误用点
- 学习路径审查：检查 unit 是否过度跳跃或与前置知识脱节
