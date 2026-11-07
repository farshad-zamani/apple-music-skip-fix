import pytest
from amsf.core import Session


@pytest.fixture
def setup(tmp_path):
    library, prefs, media, adi = [tmp_path / p for p in ["کتابخانه Music.musiclibrary", "Preferences", "External Music", "Apple/adi"]]
    for p in [library, prefs, media, adi]:
        p.mkdir(parents=True)
    (library / "Library.musicdb").write_bytes(b"unchanged library")
    (prefs / "settings.plist").write_bytes(b"unchanged preferences")
    (media / "old.frag").write_bytes(b"original protected audio")
    (adi / "adi.pb").write_bytes(b"original identity")
    return Session(tmp_path / "Sessions"), library, prefs, media, adi
