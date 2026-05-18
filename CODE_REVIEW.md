# 逐单元代码审查与修正记录

本文件记录对每个 unit 和实战项目的审查结果。审查目标不是追求复杂，而是确保示例在学习路径中可靠、清晰、能运行。

## 总体检查项

- 使用 `pyqtgraph.Qt`，避免把代码锁死在某一个 Qt 绑定上。
- GUI 程序只创建一次 QApplication，并通过 `pg.mkQApp()` 与 `pg.exec()` 管理事件循环。
- 实时绘图复用 `PlotDataItem.setData()`，避免定时器里不断创建新曲线。
- 大数据示例开启 `setClipToView()` 和 `setDownsampling()`。
- 所有脚本都有 `main()` 和 `if __name__ == "__main__"`，可独立运行。

## Unit 01

审查结果：

- 曲线、散点、图例、坐标轴和网格用法清晰。
- `plot.plot()` 返回值在本单元不需要更新，因此不用保存引用。
- 数据长度一致，`x/y` 对齐。

修正：

- 无需修正。

## Unit 02

审查结果：

- Qt 布局与控件信号连接完整。
- `valueChanged` 会触发 `redraw()`，曲线通过 `setData()` 更新。
- 网格开关使用 `toggled(bool)`，参数类型正确。

修正：

- 无需修正。

## Unit 03

审查结果：

- 使用固定长度 numpy buffer，避免实时数据无限增长。
- `QTimer` 只负责触发增量更新，暂停时不销毁对象。
- `np.nan` 初始化让尚未写入的数据不会误导读者。

修正：

- 无需修正。

## Unit 04

审查结果：

- `ImageView` 适合教学直方图和 LUT 控制。
- `RectROI` 添加到 `ImageView.getView()`，并通过 `getArrayRegion()` 从 `ImageItem` 取数据。
- 对 ROI 为空或出界做了保护。

修正：

- 将直接访问 `ImageView.imageItem` 改为官方公开方法 `getImageItem()`。
- 显式创建 `pg.ImageItem(axisOrder="row-major")`，避免二维数组显示时默认列优先造成坐标理解偏差。

## Unit 05

审查结果：

- `Parameter` 作为模型，`ParameterTree` 作为视图，符合官方文档对参数树的设计描述。
- `sigTreeStateChanged` 可能一次返回多个变化，本示例统一重绘，适合入门。
- 颜色参数返回 `QColor`，`pg.mkPen()` 可直接消费。

修正：

- 无需修正。

## Unit 06

审查结果：

- 大数据绘图使用降采样与视图裁剪。
- CSV 导出与 PNG 导出拆成两个方法，便于单独测试。
- 文件选择器只负责拿路径，实际导出逻辑在独立函数中。

修正：

- 无需修正。

## 实战项目

审查结果：

- 项目覆盖前 6 个 unit 的核心知识点：Qt 布局、参数树、实时刷新、曲线、二维图像和导出。
- 时域、频域、频谱图都来自同一个 rolling buffer，数据流容易追踪。
- 参数变化后刷新间隔立即生效，其他参数在下一帧读取。

修正：

- 将滚动频谱图的 `ImageItem` 改为 `axisOrder="row-major"`，让 numpy 数组的行列含义更贴近“频率 x 历史帧”的显示语义。
