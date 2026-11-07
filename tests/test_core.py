import json
import os
import shutil
from pathlib import Path

import pytest

from amsf.core import (AdiTransaction, PlaybackCheck, SafetyError, Session, compare_inventory,
                       inventory, no_links, protect, scan_xml, shareable_report, validate_backup)


def backed(setup):
    s, lib, prefs, media, adi = setup
    protect(s, lib, prefs, media, adi)
    return s, adi


def test_backup_and_refresh_never_write_music(setup):
    s, lib, prefs, media, adi = setup
    before = (media / "old.frag").read_bytes()
    backed(setup)
    validate_backup(s)
    tx = AdiTransaction(adi, s.id)
    tx.stage()
    assert not adi.exists()
    assert (tx.old / "adi.pb").read_bytes() == b"original identity"
    assert (media / "old.frag").read_bytes() == before
    assert (lib / "Library.musicdb").read_bytes() == b"unchanged library"
    assert (prefs / "settings.plist").read_bytes() == b"unchanged preferences"


def test_restore_keeps_fresh_identity(setup):
    s, adi = backed(setup)
    tx = AdiTransaction(adi, s.id)
    tx.stage()
    adi.mkdir()
    (adi / "adi.pb").write_bytes(b"fresh identity")
    tx.restore()
    assert (adi / "adi.pb").read_bytes() == b"original identity"
    assert (tx.new / "adi.pb").read_bytes() == b"fresh identity"
    tx.restore()  # idempotent


def test_interrupted_stage_can_resume(setup, monkeypatch):
    s, adi = backed(setup)
    import amsf.core as core
    original = core.atomic_json
    def interrupt(path, data):
        if data.get("operation") == "staged":
            raise OSError("simulated power loss")
        original(path, data)
    tx = AdiTransaction(adi, s.id)
    monkeypatch.setattr(core, "atomic_json", interrupt)
    with pytest.raises(OSError):
        tx.stage()
    assert tx.old.exists()
    monkeypatch.setattr(core, "atomic_json", original)
    tx.stage()
    tx.restore()
    assert (adi / "adi.pb").exists()


def test_interrupted_restore_can_resume(setup, monkeypatch):
    s, adi = backed(setup)
    tx = AdiTransaction(adi, s.id)
    tx.stage()
    import amsf.core as core
    original = core.atomic_json
    def interrupt(path, data):
        if data.get("operation") == "restored":
            raise OSError("simulated power loss")
        original(path, data)
    monkeypatch.setattr(core, "atomic_json", interrupt)
    with pytest.raises(OSError):
        tx.restore()
    monkeypatch.setattr(core, "atomic_json", original)
    tx.restore()
    assert (adi / "adi.pb").read_bytes() == b"original identity"


def test_tampered_backup_prevents_ready(setup):
    s, _ = backed(setup)
    (s.folder / "backup/library/Library.musicdb").write_bytes(b"tampered")
    with pytest.raises(SafetyError, match="recovery file"):
        validate_backup(s)


def test_copy_failure_never_marks_backup_ready(setup, monkeypatch):
    s, lib, prefs, media, adi = setup
    def fail(*args, **kwargs):
        raise PermissionError("locked")
    monkeypatch.setattr(shutil, "copy2", fail)
    with pytest.raises(PermissionError):
        protect(s, lib, prefs, media, adi)
    assert s.data["state"] == "created"
    assert (adi / "adi.pb").exists()


def test_no_space_blocks_repair(setup, monkeypatch):
    s, lib, prefs, media, adi = setup
    usage = shutil.disk_usage(s.folder)
    monkeypatch.setattr(shutil, "disk_usage", lambda _: type(usage)(usage.total, usage.used, 0))
    with pytest.raises(SafetyError, match="free space"):
        protect(s, lib, prefs, media, adi)
    assert not s.data.get("backup_verified")


def test_inventory_distinguishes_added_from_changed_audio(setup):
    _, _, _, media, _ = setup
    before = inventory(media)
    (media / "new.frag").write_bytes(b"new")
    assert compare_inventory(media, before)["missing_or_changed"] == 0
    (media / "old.frag").unlink()
    assert compare_inventory(media, before)["missing_or_changed"] == 1


@pytest.mark.parametrize("value", ["../adi", "", "UPPER", "00000000-0000-0000-0000-000000000000/../x"])
def test_session_traversal_rejected(tmp_path, value):
    with pytest.raises((SafetyError, ValueError)):
        Session(tmp_path, value)


def test_link_rejected(tmp_path):
    target, link = tmp_path / "target", tmp_path / "link"
    target.mkdir()
    if os.name == "nt":
        import subprocess
        p = subprocess.run(["cmd.exe", "/c", "mklink", "/J", str(link), str(target)], capture_output=True)
        assert p.returncode == 0
    else:
        link.symlink_to(target, target_is_directory=True)
    with pytest.raises(SafetyError, match="junction"):
        no_links(link / "adi")


def test_xml_persian_dates_do_not_affect_error_detection(tmp_path):
    p = tmp_path / "trace.xml"
    p.write_text('<Events><Event><TimeCreated SystemTime="1405-08-15T02:21:56+03:29"/><Data Name="StringMessage">play&gt; qos&gt; error: -11800/-42812</Data></Event></Events>')
    result = scan_xml(p)
    assert result["codes"] == {"-11800": 1, "-42812": 1}
    assert result["failures"] == 1


@pytest.mark.parametrize("xml", ['<Events><Event>', '<!DOCTYPE x [<!ENTITY xxe SYSTEM "file:///secret">]><Events>&xxe;</Events>'])
def test_malformed_and_entity_logs_not_used(tmp_path, xml):
    p = tmp_path / "trace.xml"
    p.write_text(xml)
    with pytest.raises(SafetyError):
        scan_xml(p)


def test_report_allowlist_never_leaks_private_fields(setup):
    s = setup[0]
    s.data.update(email="private@example.com", media=r"E:\Private Music", key="secret",
                  verification={"online": True, "offline": None})
    value = shareable_report(s, {"build": 26100, "version": "1.2.3", "sid": "private"}, {"codes": {"-42812": 4}, "raw": "secret"})
    output = json.dumps(value)
    for private in ["private@example", "Private Music", "secret", "sid"]:
        assert private not in output
    assert value["offline_confirmed_by_user"] is False
    assert value["error_codes"]["-42812"] == 4


def test_existing_backup_not_overwritten(setup):
    s, adi = backed(setup)
    tx = AdiTransaction(adi, s.id)
    tx.old.mkdir()
    with pytest.raises(SafetyError, match="already exists"):
        tx.stage()
    assert adi.exists()


def test_resume_retains_metadata_and_current_state(setup):
    s, _ = backed(setup)
    s.state("waiting_for_authorization")
    restored = Session(s.root, s.id)
    assert restored.data["backup_verified"]
    assert Session.pending(s.root) == [s.id]
    restored.state("completed")
    assert Session.pending(s.root) == []


def test_playback_requires_elapsed_time_and_progress():
    p = PlaybackCheck()
    for t in range(0, 34, 3):
        result = p.feed({"Title": "Old", "Artist": "Artist", "Position": t, "Status": "Playing"}, clock=t)
    assert result


def test_seek_stall_and_skip_cannot_fake_verification():
    for behavior in [lambda t: 0, lambda t: t * 20, lambda t: t % 8]:
        p = PlaybackCheck()
        for t in range(0, 40, 3):
            assert not p.feed({"Title": "Old", "Artist": "A", "Position": behavior(t), "Status": "Playing"}, clock=t)


def test_restore_missing_record_does_not_mutate(setup):
    s, adi = backed(setup)
    with pytest.raises(SafetyError):
        AdiTransaction(adi, s.id).restore()
    assert (adi / "adi.pb").exists()


def test_permission_denied_stage_keeps_original(setup, monkeypatch):
    s, adi = backed(setup)
    original = Path.rename
    def denied(self, destination):
        if self == adi:
            raise PermissionError("denied")
        return original(self, destination)
    monkeypatch.setattr(Path, "rename", denied)
    with pytest.raises(PermissionError):
        AdiTransaction(adi, s.id).stage()
    assert (adi / "adi.pb").read_bytes() == b"original identity"


@pytest.mark.parametrize("offline,expected", [(None, "not-tested"), (False, "failed"), (True, "confirmed")])
def test_offline_report_preserves_all_outcomes(setup, offline, expected):
    s = setup[0]
    s.data["verification"] = {"offline": offline}
    assert shareable_report(s, {}, {})["offline_result"] == expected


def test_restored_report_does_not_reuse_prior_success(setup):
    s = setup[0]
    s.data["verification"] = {"online": True, "offline": True}
    s.state("restored")
    value = shareable_report(s, {}, {})
    assert not value["online_confirmed"]
    assert value["offline_result"] == "not-tested"
