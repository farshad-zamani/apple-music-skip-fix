"""Additional review captures; every screen is synthetic and owns a temporary root."""
from pathlib import Path
import sys
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from amsf.gui import MainWindow

root = Path(__file__).resolve().parents[1]
scenario = sys.argv[1]
app = QApplication([])
app.setStyle("Fusion")
w = MainWindow(demo=True, theme="light", page=5)
if scenario == "unresolved":
    w.session.data["verification"] = {"online": False, "offline": False}
    w.session.state("unresolved")
else:
    w.session.state("restored")
w.show_stage(5)
w.show()
def capture():
    w.grab().save(str(root / "docs/images" / (scenario + ".png")))
    w.close()
QTimer.singleShot(600, capture)
raise SystemExit(app.exec())
