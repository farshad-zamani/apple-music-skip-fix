import pytest
from amsf import windows
from amsf.core import SafetyError
from test_core import backed  # shared synthetic helper, never real ADI


def test_helper_rejects_missing_caller_before_any_system_access(monkeypatch):
    def forbidden(*args):
        pytest.fail("Should not reach Windows")
    monkeypatch.setattr(windows, "fixed_adi", forbidden)
    with pytest.raises(SafetyError, match="original repair window"):
        windows.transaction("stage", "00000000-0000-0000-0000-000000000001", elevated=True)


def test_helper_requires_verified_existing_backup(setup, monkeypatch):
    s, _, _, _, adi = setup
    monkeypatch.setattr(windows, "caller_data_root", lambda _: s.root.parent)
    monkeypatch.setattr(windows, "fixed_adi", lambda: adi)
    with pytest.raises(SafetyError, match="verified backup"):
        windows.transaction("stage", s.id, elevated=True, caller_pid=100)
    assert adi.exists()


def test_helper_uses_only_fixed_target_and_verifies_cache(setup, monkeypatch):
    s, adi = backed(setup)
    monkeypatch.setattr(windows, "caller_data_root", lambda _: s.root.parent)
    monkeypatch.setattr(windows, "fixed_adi", lambda: adi)
    monkeypatch.setattr(windows, "ps", lambda *args: {"closed": True})
    class Lock:
        def __init__(self, _): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
    monkeypatch.setattr(windows, "Mutex", Lock)
    (adi / "adi.pb").write_bytes(b"changed since backup")
    with pytest.raises(SafetyError, match="changed after backup"):
        windows.transaction("stage", s.id, elevated=True, caller_pid=100)
    (adi / "adi.pb").write_bytes(b"original identity")
    windows.transaction("stage", s.id, elevated=True, caller_pid=100)
    assert not adi.exists()
    windows.transaction("restore", s.id, elevated=True, caller_pid=100)
    assert (adi / "adi.pb").read_bytes() == b"original identity"


def test_shared_process_guard_blocks_stage(setup, monkeypatch):
    s, adi = backed(setup)
    monkeypatch.setattr(windows, "data_root", lambda: s.root.parent)
    monkeypatch.setattr(windows, "ps", lambda *args: {"closed": False})
    with pytest.raises(SafetyError, match="all Windows user sessions"):
        windows.transaction("stage", s.id)
    assert adi.exists()
