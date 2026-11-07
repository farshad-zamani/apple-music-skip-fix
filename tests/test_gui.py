import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QLabel
from amsf.gui import MainWindow
from amsf import windows


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def wait(app, window):
    deadline = time.monotonic() + 8
    while window.busy and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.01)
    app.processEvents()
    assert not window.busy


@pytest.fixture
def demo(app, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Demo accessed a real Windows adapter")
    for name in ["discover", "launch", "ensure_closed", "transaction", "elevate", "media_sample", "data_root"]:
        monkeypatch.setattr(windows, name, forbidden)
    w = MainWindow(demo=True)
    w.show()
    app.processEvents()
    yield w
    wait(app, w)
    w.close()


def test_demo_full_workflow_never_uses_windows(app, demo):
    w = demo
    w.primary_action()
    assert w.stage == 1
    w.consent.setChecked(True)
    w.primary_action()
    wait(app, w)
    assert w.stage == 2
    w.primary_action()
    wait(app, w)
    assert w.stage == 3
    w.open_authorize()
    w.authorized.setChecked(True)
    w.primary_action()
    assert w.stage == 4
    for i in range(3):
        if i == 2:
            w.restart_music()
        w.observe()
        wait(app, w)
        w.heard.setChecked(True)
        w.primary_action()
    w.primary_action()
    wait(app, w)
    assert w.stage == 5
    assert w.session.data["verification"]["online"] is True
    assert w.session.data["verification"]["offline"] is None


def test_required_consent_and_authorization(app, demo):
    demo.primary_action()
    demo.primary_action()
    assert demo.stage == 1
    assert "Confirm" in demo.status.text()
    demo.demo_session()
    demo.show_stage(3)
    demo.primary_action()
    assert demo.stage == 3


def test_small_window_keeps_primary_action(app, demo):
    demo.resize(700, 500)
    app.processEvents()
    assert not demo.rail.isVisible()
    assert demo.primary.isVisible()
    assert demo.primary.geometry().height() >= 44
    assert demo.scroll.isVisible()


def test_reopened_test_cannot_skip_restart(app, demo):
    demo.demo_session()
    demo.evidence = demo.audible = [True, True, False]
    demo.show_stage(4)
    demo.observe()
    assert not demo.busy
    assert "reopen" in demo.status.text()


def test_result_is_honest_when_unresolved(app, demo):
    demo.demo_session()
    demo.session.data["verification"] = {"online": False, "offline": False}
    demo.show_stage(5)
    labels = " ".join(label.text() for label in demo.findChildren(QLabel))
    assert "Not yet confirmed" in labels
    assert "Still failing" in labels
    assert "Let’s find the next step." in labels
    assert demo.heading_label.text() == "Let’s find the next step."


def test_manual_confirmation_cannot_bypass_restart(app, demo):
    demo.demo_session()
    demo.evidence, demo.audible = [True, True, False], [True, True, False]
    demo.media_api = False
    demo.show_stage(4)
    demo.manual.setChecked(True)
    demo.heard.setChecked(True)
    demo.primary_action()
    assert demo.evidence[2] is False
    assert "reopen" in demo.status.text()


def test_completed_history_remains_available(app, demo):
    from amsf.core import Session
    demo.demo_session()
    demo.session.state("completed")
    assert demo.session.id in Session.saved(demo.root / "Sessions")


def test_restored_result_does_not_claim_current_offline_success(app, demo):
    demo.demo_session()
    demo.session.data["verification"] = {"online": True, "offline": True}
    demo.session.state("restored")
    demo.show_stage(5)
    labels = " ".join(label.text() for label in demo.findChildren(QLabel))
    assert "Previous cache restored." in labels
    assert "Needs a new check after restore" in labels
    assert demo.heading_label.text() == "Previous cache restored."


def test_declined_permission_keeps_verified_backup(app, demo, monkeypatch):
    demo.demo_session()
    demo.demo = False
    monkeypatch.setattr(windows, "ensure_closed", lambda: None)
    def denied(*args):
        raise PermissionError("test denial")
    monkeypatch.setattr(windows, "transaction", denied)
    monkeypatch.setattr(windows, "elevate", lambda *args: False)
    demo.show_stage(2)
    demo.primary_action()
    wait(app, demo)
    assert demo.stage == 2
    assert demo.session.data["state"] == "backup_verified"
    assert "declined" in demo.status.text()


def test_history_can_reopen_completed_result(app, demo, monkeypatch):
    from PySide6.QtWidgets import QInputDialog
    demo.demo_session()
    demo.session.state("completed")
    monkeypatch.setattr(QInputDialog, "getItem", lambda *args: (args[3][0], True))
    demo.session = None
    demo.open_history()
    assert demo.stage == 5
    assert demo.session is not None
    assert demo.restore_btn.isVisible()


def test_authorization_retry_clears_previous_verification(app, demo):
    demo.demo_session()
    demo.session.data["verification"] = {"online": True, "offline": True}
    demo.retry_authorization()
    assert demo.stage == 3
    assert demo.session.data["verification"] == {}
    assert demo.evidence == [False] * 3
