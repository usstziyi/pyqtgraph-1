"""Unit 05: ParameterTree as a small settings model and editor."""

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets
from pyqtgraph.parametertree import Parameter, ParameterTree


class ParameterTreeWindow(QtWidgets.QMainWindow):
    """Use a ParameterTree to control both data and style."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Unit 05 - ParameterTree")
        self.resize(1050, 620)

        self.x = np.linspace(0.0, 1.0, 1200)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QHBoxLayout(central)

        self.params = Parameter.create(
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

        self.tree = ParameterTree()
        self.tree.setParameters(self.params, showTop=False)
        layout.addWidget(self.tree, 0)

        self.plot = pg.PlotWidget(title="Parameter-driven plot")
        self.plot.setLabel("bottom", "time", units="s")
        self.plot.setLabel("left", "amplitude")
        layout.addWidget(self.plot, 1)

        self.curve = self.plot.plot()
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
        self.curve.setData(self.x, y)
        self.curve.setPen(pg.mkPen(color, width=2))
        self.plot.showGrid(x=show_grid, y=show_grid, alpha=0.2)


def main() -> None:
    app = pg.mkQApp("Unit 05 - ParameterTree")
    window = ParameterTreeWindow()
    window.show()
    pg.exec()


if __name__ == "__main__":
    main()

