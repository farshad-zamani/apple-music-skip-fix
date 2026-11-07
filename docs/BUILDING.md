# Build a Windows release

Use Windows x64 and Python 3.13. Building is not a repair and does not require an Apple account.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-build.lock
.\.venv\Scripts\python -m pip install --no-deps -e .
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check src tests tools
.\.venv\Scripts\python tools/prepare_build.py
.\.venv\Scripts\pyinstaller --noconfirm --clean packaging/AppleMusicSkipFix.spec
& 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' packaging/installer.iss
.\.venv\Scripts\python tools/package_release.py
.\tools\smoke_release.ps1
```

Use the complete one-folder distribution. Do not move the executable out of its folder or convert the app to an elevated one-file executable. No UPX compression or paid signing certificate is used for 0.1.0.

The per-user Inno Setup installer requires no administrator account for installation and does not install a background service. Only the in-app cache helper can request elevation for a specific repair.

Run `dist/AppleMusicSkipFix/AppleMusicSkipFix.exe --demo --smoke-test` to verify the frozen GUI/resources without touching an installation. Real cache mutations must be tested only with synthetic fixtures or an explicitly isolated disposable environment.

`tools/smoke_release.ps1` verifies published hashes, extracts the Portable ZIP, starts its synthetic demo with Python removed from PATH, silently installs into a unique workspace build directory, runs the installed synthetic demo, uninstalls it, and checks that a synthetic recovery marker survives. It refuses to replace an existing installed assistant. Results are written to `build/package-qa.json`. You can supply `-ArtifactsRoot` to test a downloaded release instead of the local build.

Qt notice texts are vendored with upstream URLs and SHA-256 hashes. `tools/vendor_licenses.py` refreshes them from the pinned Qt source tags; ordinary builds use the committed copies without fetching them again.

Public release assets are the Setup EXE, Portable ZIP and `SHA256SUMS.txt`. GitHub attaches the source archives. Compare hashes with `Get-FileHash -Algorithm SHA256 <download>`. Rebuilds may not be byte-identical because PE timestamps and packaging metadata can vary; checksums identify the published artifacts rather than claim reproducible binaries.
