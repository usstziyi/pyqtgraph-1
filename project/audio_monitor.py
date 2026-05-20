"""Entry point for the PyQtGraph microphone monitor."""

from pathlib import Path
import sys

from PySide6.QtWidgets import QApplication

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from project.audio_app import AudioMonitor
else:
    from .audio_app import AudioMonitor


def main() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("PyQtGraph Microphone Monitor")
    app.setStyle("Fusion")
    window = AudioMonitor()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
