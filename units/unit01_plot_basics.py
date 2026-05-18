"""Unit 01: basic curves, scatter points, axes, grids, and legends."""

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets


def build_window() -> pg.PlotWidget:
    """Create a PlotWidget and add several data layers to it."""
    pg.setConfigOptions(antialias=True)

    plot = pg.PlotWidget(title="Unit 01 - Plot basics")
    plot.resize(900, 520)
    plot.setLabel("bottom", "time", units="s")
    plot.setLabel("left", "amplitude", units="V")
    plot.showGrid(x=True, y=True, alpha=0.25)
    plot.addLegend(offset=(10, 10))

    x = np.linspace(0.0, 2.0, 800)
    sine = np.sin(2.0 * np.pi * 3.0 * x)
    cosine = 0.6 * np.cos(2.0 * np.pi * 5.0 * x)

    # plot() returns a PlotDataItem. Keep it when the data will change later.
    plot.plot(x, sine, pen=pg.mkPen("#0072B2", width=2), name="3 Hz sine")
    plot.plot(x, cosine, pen=pg.mkPen("#D55E00", width=2), name="5 Hz cosine")

    # pen=None disables the connecting line, so only symbols are visible.
    sample_x = x[::40]
    sample_y = sine[::40]
    plot.plot(
        sample_x,
        sample_y,
        pen=None,
        symbol="o",
        symbolSize=8,
        symbolBrush=pg.mkBrush("#009E73"),
        name="sampled points",
    )

    return plot


def main() -> None:
    app = pg.mkQApp("Unit 01 - Plot basics")
    window = build_window()
    window.show()
    pg.exec()


if __name__ == "__main__":
    main()

