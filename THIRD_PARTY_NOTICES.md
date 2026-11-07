# Third-party notices

Apple Music Skip Fix's own source is MIT licensed. The original icon is authored SVG geometry, also MIT. Apple software, music, account data, authorization files and binaries are **not** distributed with this project.

| Component | Version in release | License / source |
| --- | --- | --- |
| Python | 3.13 | [PSF License and bundled notices](https://docs.python.org/3/license.html) |
| Qt for Python / PySide6 Essentials | 6.12.0 | [LGPLv3 / GPLv3 / commercial options and third-party notices](https://doc.qt.io/qtforpython-6/licenses.html) |
| Shiboken6 | 6.12.0 | [Qt for Python source and license](https://code.qt.io/cgit/pyside/pyside-setup.git/) |
| defusedxml | 0.7.1 | [PSF License](https://github.com/tiran/defusedxml) |
| PyInstaller bootloader/build tool | 6.22.3 | [GPL with distribution exception](https://pyinstaller.org/en/stable/license.html) |

Qt/PySide6 is distributed here under its LGPLv3 option. Full license texts and Qt third-party notices are copied into the distribution's `_internal/licenses` folder. Upstream notice URLs and hashes are recorded in `packaging/licenses/SOURCES.json`. Qt is distributed as shared libraries, not statically linked into application code. Compatible Qt DLLs and plugins in `_internal/PySide6` can be replaced; preserve the matching ABI and directory structure. Source releases are available from [Qt for Python](https://download.qt.io/official_releases/QtForPython/) and [Qt](https://download.qt.io/official_releases/qt/). The application source and build instructions are available in this repository. Reverse engineering for debugging modifications to the LGPL components is permitted.

Build/test-only tools include pytest (MIT), Ruff (MIT), Pillow (HPND), setuptools (MIT), and PyInstaller build dependencies. They are not application features. See the pinned build lock and each upstream distribution for their notices. Windows APIs and PowerShell are supplied by Windows and are not bundled by this project.

Public PNG screenshots are native captures of `--demo` with synthetic data. Their origin is embedded in PNG metadata. No screenshots of personal accounts or libraries are included.
