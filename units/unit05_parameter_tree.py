"""Unit 05: ParameterTree as a small settings model and editor."""

import sys

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QWidget
from pyqtgraph.parametertree import Parameter, ParameterTree


def create_parameters() -> Parameter:
    """Create the pyqtgraph Parameter model edited by the tree widget."""
    return Parameter.create(
        name="settings",
        type="group",
        children=[
            {
                "name": "Signal",
                "type": "group",
                "children": [
                    {
                        "name": "Frequency",
                        "type": "float",
                        "value": 4.0,
                        "limits": (0.1, 30.0),
                        "step": 0.1,
                        "suffix": " Hz",
                    },
                    {
                        "name": "Amplitude",
                        "type": "float",
                        "value": 1.0,
                        "limits": (0.1, 5.0),
                        "step": 0.1,
                    },
                ],
            },
            {
                "name": "Style",
                "type": "group",
                "children": [
                    {"name": "Color", "type": "color", "value": pg.mkColor("#0072B2")},
                    {"name": "Show grid", "type": "bool", "value": True},
                ],
            },
        ],
    )


class ParameterDrivenPlot(pg.PlotWidget):
    """PyQtGraph plot that exposes update methods for data and style."""

    def __init__(self) -> None:
        super().__init__(title="Parameter-driven plot")
        self.setLabel("bottom", "time", units="s")
        self.setLabel("left", "amplitude")
        self.curve = self.plot()

    def set_signal(self, x: np.ndarray, y: np.ndarray, color: object) -> None:
        self.curve.setData(x, y)
        self.curve.setPen(pg.mkPen(color, width=2))

    def set_grid_visible(self, enabled: bool) -> None:
        self.showGrid(x=enabled, y=enabled, alpha=0.2)


class ParameterPanel(ParameterTree):
    """PyQtGraph ParameterTree widget bound to a Parameter model."""

    def __init__(self, params: Parameter) -> None:
        super().__init__()
        self.setParameters(params, showTop=False)


class ParameterTreeWindow(QMainWindow):
    """Qt window that lays out the parameter editor and plot widget."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Unit 05 - ParameterTree")
        self.resize(1050, 620)

        self.x = np.linspace(0.0, 1.0, 1200)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        self.params = create_parameters()
        self.tree = ParameterPanel(self.params)
        layout.addWidget(self.tree, 0)

        self.plot = ParameterDrivenPlot()
        layout.addWidget(self.plot, 1)

        self.params.sigTreeStateChanged.connect(self.on_parameter_change)
        self.update_plot()

    def on_parameter_change(self, param: Parameter, changes: list[tuple]) -> None:
        """ParameterTree sends batched changes; this demo simply redraws all."""
        self.update_plot()

    def update_plot(self) -> None:
        """Pull values from the parameter model and apply them to the plot."""
        frequency = self.params.param("Signal", "Frequency").value()
        amplitude = self.params.param("Signal", "Amplitude").value()
        color = self.params.param("Style", "Color").value()
        show_grid = self.params.param("Style", "Show grid").value()

        y = amplitude * np.sin(2.0 * np.pi * frequency * self.x)
        self.plot.set_signal(self.x, y, color)
        self.plot.set_grid_visible(show_grid)


def main() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Unit 05 - ParameterTree")
    window = ParameterTreeWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
