"""Prepare authored icon and third-party licenses; never reads Apple data."""
import importlib.metadata as metadata
from pathlib import Path
import shutil
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from PIL import Image, PngImagePlugin

root = Path(__file__).resolve().parents[1]
build = root / "build"
build.mkdir(exist_ok=True)
app = QGuiApplication.instance() or QGuiApplication([])
svg = root / "src/amsf/resources/icon.svg"
image = QImage(256, 256, QImage.Format.Format_ARGB32)
image.fill(Qt.GlobalColor.transparent)
painter = QPainter(image)
QSvgRenderer(str(svg)).render(painter)
painter.end()
image.save(str(build / "icon.png"))
with Image.open(build / "icon.png") as icon:
    icon.save(build / "icon.ico", sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
licenses = build / "licenses"
licenses.mkdir(exist_ok=True)
shutil.copytree(root / "packaging/licenses", licenses / "Qt-upstream", dirs_exist_ok=True)
shutil.copy2(root / "LICENSE", licenses / "Application-MIT.txt")
python_license = Path(sys.base_prefix) / "LICENSE.txt"
if python_license.exists():
    shutil.copy2(python_license, licenses / "Python.txt")
for name in ["PySide6_Essentials", "shiboken6", "defusedxml", "pyinstaller"]:
    dist = metadata.distribution(name)
    out = licenses / name
    out.mkdir(exist_ok=True)
    for entry in dist.files or []:
        path = str(entry).replace("\\", "/")
        if ".dist-info/" in path and ("/licenses/" in path or entry.name.lower().startswith(("license", "copying", "notice"))):
            source = Path(dist.locate_file(entry))
            if source.is_file():
                destination = out / path.split(".dist-info/", 1)[1]
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
# Embed screenshot origin, not generated-art or real-user provenance.
for path in (root / "docs/images").glob("*.png"):
    with Image.open(path) as source:
        info = PngImagePlugin.PngInfo()
        info.add_text("Origin", "Native Qt screenshot of Apple Music Skip Fix --demo; synthetic data; source: src/amsf/gui.py")
        info.add_text("Software", "Apple Music Skip Fix 0.1.0 / PySide6; local demo capture")
        source.save(path, pnginfo=info)
print("Prepared original vector icon and bundled component licenses.")
