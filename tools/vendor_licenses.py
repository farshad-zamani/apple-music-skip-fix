"""Refresh plain-text license notices from Qt's upstream source trees (build-time only)."""
import hashlib
import json
from pathlib import Path
import urllib.request

root = Path(__file__).resolve().parents[1]
records = []
for repo, ref in [("qt/qtbase", "v6.12.0"), ("qt/qtsvg", "v6.12.0"), ("pyside/pyside-setup", "v6.12.0")]:
    url = f"https://api.github.com/repos/{repo}/contents/LICENSES?ref={ref}"
    request = urllib.request.Request(url, headers={"User-Agent": "AppleMusicSkipFix-license-build"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            entries = json.load(response)
    except Exception:
        if repo.startswith("pyside/"):
            continue  # Qt base includes LGPL/GPL; binding wheel notice is also bundled.
        raise
    for entry in entries:
        if entry["type"] != "file" or not entry["name"].endswith(".txt"):
            continue
        with urllib.request.urlopen(entry["download_url"], timeout=30) as response:
            payload = response.read(1024 * 1024)
        path = root / "packaging/licenses" / repo.split("/")[-1] / entry["name"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        records.append({"file": path.relative_to(root).as_posix(), "source": entry["download_url"],
                        "sha256": hashlib.sha256(payload).hexdigest()})
(root / "packaging/licenses/SOURCES.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
print(f"Vendored {len(records)} upstream license files.")
