# Run from the repository root with the pinned build environment.
from pathlib import Path
root = Path(SPECPATH).parent
a = Analysis([str(root / 'run_app.py')], pathex=[str(root / 'src')],
             datas=[(str(root / 'src/amsf/scripts'), 'amsf/scripts'),
                    (str(root / 'src/amsf/resources'), 'amsf/resources'),
                    (str(root / 'build/licenses'), 'licenses'),
                    (str(root / 'THIRD_PARTY_NOTICES.md'), '.')],
             hiddenimports=['PySide6.QtSvg'],
             excludes=['tkinter', 'pytest', 'PIL', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
                       'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtPdf'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='AppleMusicSkipFix',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, icon=str(root / 'build/icon.ico'),
          version=str(root / 'packaging/version.txt'), uac_admin=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='AppleMusicSkipFix')
