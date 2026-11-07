"""Archive the one-folder build and hash only the distributable release files."""
import hashlib
from pathlib import Path
import shutil
from amsf import __version__

root = Path(__file__).resolve().parents[1]
dist = root / "dist"
shutil.copy2(root / "LICENSE", dist / "AppleMusicSkipFix/LICENSE.txt")
shutil.copy2(root / "THIRD_PARTY_NOTICES.md", dist / "AppleMusicSkipFix/THIRD_PARTY_NOTICES.md")
shutil.copy2(root / "README.md", dist / "AppleMusicSkipFix/README.md")
shutil.make_archive(str(dist / f"AppleMusicSkipFix-{__version__}-Portable"), "zip", dist, "AppleMusicSkipFix")
files = [dist / f"AppleMusicSkipFix-{__version__}-Portable.zip", dist / f"AppleMusicSkipFix-{__version__}-Setup.exe"]
lines = []
for p in files:
    h = hashlib.sha256()
    with p.open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            h.update(block)
    lines.append(h.hexdigest() + "  " + p.name)
(dist / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="ascii")
print("\n".join(lines))
