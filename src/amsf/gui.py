"""Six-step desktop workflow. All Windows work is off the GUI thread."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import time
import hashlib

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, Signal, QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog, QFrame, QHBoxLayout,
                             QLabel, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
                             QScrollArea, QVBoxLayout, QWidget, QInputDialog)

from . import __version__
from .core import (PlaybackCheck, SafetyError, Session, compare_inventory, protect,
                   shareable_report, validate_backup)
from . import windows

STEPS = ["Check", "Protect", "Refresh", "Authorize", "Verify", "Result"]
DESCRIPTIONS = ["Understand the skipping", "Keep a way back", "Refresh device identity",
                "Reconnect your account", "Listen to your old tracks", "See what changed"]
HEADINGS = ["Get back to your music.", "Your downloads stay yours.", "A fresh start for authorization.",
            "One step inside Apple Music.", "The proof is in the playback.", "Back to listening."]
INTRO = ["A guided repair for downloaded songs that skip without playing. First, let’s check your setup.",
         "We’ll protect your library metadata and Apple’s authorization cache before making a change.",
         "We’ll keep the old cache beside its original location, then let Apple Music create a fresh one.",
         "Apple needs to authorize this computer again. Your password stays inside Apple Music.",
         "Choose music you downloaded before the problem started. New downloads don’t prove the repair.",
         "Here’s what was checked, what you confirmed, and what still needs attention."]


class Signals(QObject):
    done = Signal(object)
    error = Signal(str)
    progress = Signal(str)


class Job(QRunnable):
    def __init__(self, fn):
        super().__init__()
        self.fn, self.signals = fn, Signals()

    def run(self):
        try:
            self.signals.done.emit(self.fn(self.signals.progress.emit))
        except Exception as exc:
            message = str(exc) if isinstance(exc, SafetyError) else (
                "The step could not finish. Your recovery files have been kept. Check folder access, "
                "close other Apple apps, and try again. No automatic retry will change your system.")
            if isinstance(exc, PermissionError):
                message = "Windows denied access. Your backup is safe. Check folder permissions or use the permission prompt when refreshing the cache."
            self.signals.error.emit(message)


def text(value: str, role: str = "body") -> QLabel:
    label = QLabel(value)
    label.setObjectName(role)
    label.setWordWrap(True)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label


class MainWindow(QMainWindow):
    def __init__(self, demo: bool = False, theme: str = "system", page: int = 0):
        super().__init__()
        self.demo, self.theme = demo, theme
        self.stage, self.busy, self.session = 0, False, None
        self.snapshot, self.diag = {}, {}
        self.evidence = [False, False, False]
        self.audible = [False, False, False]
        self.media_api = True
        self.monitoring = False
        self.restart_performed = False
        self.observed_tracks = [None, None, None]
        self._temp = tempfile.TemporaryDirectory(prefix="amsf-demo-") if demo else None
        self.root = Path(self._temp.name) if demo else windows.data_root()
        self.root.mkdir(parents=True, exist_ok=True)
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self.job = None
        self.setWindowTitle("Apple Music Skip Fix" + (" — Demo" if demo else ""))
        self.setWindowIcon(QIcon(str(Path(__file__).parent / "resources/icon.svg")))
        self.resize(1060, 760)
        self.setMinimumSize(680, 440)
        self.build_shell()
        self.set_theme(theme)
        if demo:
            self.demo_data()
            if page > 0:
                self.stage = page
                self.demo_session()
            if page == 5:
                self.evidence = self.audible = [True, True, True]
                self.session.data["verification"] = {"online": True, "offline": True, "restart": True,
                                                       "method": "demo"}
                self.session.state("completed")
            self.show_stage(page)
        else:
            pending = Session.pending(self.root / "Sessions")
            if pending:
                self.session = Session(self.root / "Sessions", pending[0])
                self.snapshot = self.session.data.get("system", {})
                self.diag = self.session.data.get("diagnostic", {})
                self.evidence = self.session.data.get("evidence", [False, False, False])
                self.audible = self.session.data.get("audible", [False, False, False])
                stage = self.session.data.get("state")
                if stage == "created":
                    self.session = None
                else:
                    resume = 2 if stage == "backup_verified" else 3
                    self.show_stage(resume)
                    self.notice("A saved repair session was found. Continue below, or restore its previous cache.")
        self.apply_responsive()

    def build_shell(self):
        shell = QWidget()
        self.setCentralWidget(shell)
        outer = QVBoxLayout(shell)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        header = QFrame()
        header.setObjectName("header")
        h = QHBoxLayout(header)
        h.setContentsMargins(24, 16, 24, 16)
        mark = QLabel()
        mark.setPixmap(QIcon(str(Path(__file__).parent / "resources/icon.svg")).pixmap(38, 38))
        h.addWidget(mark)
        brand = QVBoxLayout()
        brand.setSpacing(1)
        brand.addWidget(text("Apple Music Skip Fix", "brand"))
        brand.addWidget(text("Keep your downloads. Restore playback.", "caption"))
        brand.itemAt(0).widget().setMinimumWidth(260)
        h.addLayout(brand)
        h.addStretch()
        self.theme_choice = QComboBox()
        self.theme_choice.setAccessibleName("Color theme")
        self.theme_choice.addItems(["System theme", "Light", "Dark"])
        self.theme_choice.setCurrentIndex({"system": 0, "light": 1, "dark": 2}[self.theme])
        self.theme_choice.currentIndexChanged.connect(lambda i: self.set_theme(["system", "light", "dark"][i]))
        h.addWidget(self.theme_choice)
        outer.addWidget(header)
        middle = QHBoxLayout()
        middle.setSpacing(0)
        self.rail = QFrame()
        self.rail.setObjectName("rail")
        self.rail.setFixedWidth(228)
        nav = QVBoxLayout(self.rail)
        nav.setContentsMargins(24, 30, 20, 24)
        nav.setSpacing(8)
        self.step_labels = []
        for i, name in enumerate(STEPS):
            item = QLabel(f"{i + 1}   {name}\n     {DESCRIPTIONS[i]}")
            item.setObjectName("step")
            item.setWordWrap(True)
            nav.addWidget(item)
            self.step_labels.append(item)
        nav.addStretch()
        nav.addWidget(text("Recovery files stay\non your computer.", "caption"))
        nav.addWidget(text("v" + __version__ + " · Independent project", "caption"))
        middle.addWidget(self.rail)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        self.compact_steps = text("", "caption")
        self.compact_steps.setContentsMargins(28, 14, 28, 0)
        body_layout.addWidget(self.compact_steps)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.page_holder = QWidget()
        self.content = QVBoxLayout(self.page_holder)
        self.content.setContentsMargins(36, 30, 36, 24)
        self.content.setSpacing(18)
        self.scroll.setWidget(self.page_holder)
        body_layout.addWidget(self.scroll, 1)
        self.status = text("", "status")
        self.status.setVisible(False)
        self.status.setContentsMargins(28, 12, 28, 12)
        body_layout.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(3)
        self.progress.hide()
        body_layout.addWidget(self.progress)
        footer = QFrame()
        footer.setObjectName("footer")
        foot = QHBoxLayout(footer)
        foot.setContentsMargins(28, 18, 28, 18)
        self.restore_btn = QPushButton("Restore previous cache")
        self.restore_btn.clicked.connect(self.restore)
        self.restore_btn.setAccessibleDescription("Preserve the new authorization cache and put the original cache back.")
        foot.addWidget(self.restore_btn)
        foot.addStretch()
        self.primary = QPushButton()
        self.primary.setObjectName("primary")
        self.primary.setMinimumHeight(44)
        self.primary.clicked.connect(self.primary_action)
        foot.addWidget(self.primary)
        body_layout.addWidget(footer)
        middle.addWidget(body, 1)
        outer.addLayout(middle, 1)
        self.show_stage(0)

    def set_theme(self, choice):
        self.theme = choice
        dark = choice == "dark" or (choice == "system" and
                QApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark)
        c = ({"bg": "#191C22", "surface": "#22262E", "ink": "#F2F3F6", "muted": "#B7BFCC",
              "line": "#3F4754", "field": "#2B303A", "accent": "#F1879D", "active": "#412B35"}
             if dark else {"bg": "#FFFFFF", "surface": "#F4F5F8", "ink": "#202735", "muted": "#566174",
                           "line": "#D7DCE5", "field": "#FFFFFF", "accent": "#B22B47", "active": "#F8E9EE"})
        self.colors = c
        self.setStyleSheet(f"""
            QWidget {{background:{c['bg']};color:{c['ink']};font-family:'Segoe UI';font-size:14px;}}
            QFrame#header,QFrame#footer {{border:0;background:{c['bg']};}}
            QFrame#header {{border-bottom:1px solid {c['line']};}}
            QFrame#footer {{border-top:1px solid {c['line']};}}
            QFrame#rail,QFrame#rail QLabel {{background:{c['surface']};}}
            QLabel#brand {{font-size:17px;font-weight:600;}}
            QLabel#caption {{font-size:12px;color:{c['muted']};}}
            QLabel#heading {{font-size:29px;font-weight:600;}}
            QLabel#intro {{font-size:15px;color:{c['muted']};}}
            QLabel#subheading {{font-size:17px;font-weight:600;}}
            QLabel#step {{padding:13px 10px;border-radius:8px;font-size:13px;color:{c['muted']};}}
            QLabel#step[active='true'] {{background:{c['active']};color:{c['accent']};font-weight:600;}}
            QLabel#step[done='true'] {{color:{c['ink']};}}
            QLabel#status {{background:{c['active']};color:{c['ink']};}}
            QLabel#fact {{padding:10px 0;border-bottom:1px solid {c['line']};}}
            QPushButton {{background:{c['field']};border:1px solid {c['line']};border-radius:7px;padding:10px 15px;}}
            QPushButton:hover {{background:{c['surface']};border-color:{c['accent']};}}
            QPushButton:focus,QComboBox:focus,QCheckBox:focus {{border:2px solid {c['accent']};}}
            QPushButton#primary {{background:#B22B47;color:white;border:1px solid #B22B47;font-weight:600;}}
            QPushButton#primary:hover {{background:#97213B;}}
            QPushButton:disabled {{color:{c['muted']};background:{c['surface']};border-color:{c['line']};}}
            QPushButton#primary:disabled {{background:{c['surface']};color:{c['muted']};border-color:{c['line']};}}
            QComboBox {{background:{c['field']};padding:7px 12px;border:1px solid {c['line']};border-radius:6px;min-width:105px;}}
            QComboBox QAbstractItemView {{selection-background-color:{c['active']};selection-color:{c['ink']};}}
            QCheckBox {{spacing:10px;padding:5px 0;}}
            QCheckBox::indicator {{width:18px;height:18px;}}
            QPlainTextEdit {{background:{c['surface']};border:1px solid {c['line']};border-radius:6px;padding:8px;font-family:Consolas;font-size:12px;}}
            QProgressBar {{border:0;background:{c['surface']};}}
            QProgressBar::chunk {{background:{c['accent']};}}
            QScrollBar:vertical {{width:10px;background:{c['bg']};}}
            QScrollBar::handle:vertical {{background:{c['line']};border-radius:4px;min-height:28px;}}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {{height:0;}}
        """)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "rail"):
            self.apply_responsive()

    def apply_responsive(self):
        compact = self.width() < 900
        self.rail.setVisible(not compact)
        self.compact_steps.setVisible(compact)
        self.compact_steps.setText(f"Step {self.stage + 1} of 6 · {STEPS[self.stage]}")
        self.content.setContentsMargins(24 if compact else 36, 24, 24 if compact else 36, 24)

    def clear_page(self):
        while self.content.count():
            item = self.content.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def add(self, widget):
        self.content.addWidget(widget)
        return widget

    def fact(self, title, value):
        self.add(text(f"{title}  ·  {value}", "fact"))

    def button(self, title, action):
        btn = QPushButton(title)
        btn.clicked.connect(action)
        self.add(btn)
        return btn

    def detail(self, value):
        toggle = self.button("View technical details", lambda: box.setVisible(not box.isVisible()))
        toggle.setAccessibleDescription("Expand or collapse local technical information.")
        box = QPlainTextEdit(value)
        box.setReadOnly(True)
        box.setMaximumHeight(130)
        box.hide()
        self.add(box)

    def notice(self, message):
        self.status.setText(message)
        self.status.setVisible(bool(message))

    def work(self, fn, done):
        if self.busy:
            return
        self.busy = True
        self.primary.setEnabled(False)
        self.restore_btn.setEnabled(False)
        self.page_holder.setEnabled(False)
        self.progress.show()
        self.job = Job(fn)
        self.job.signals.progress.connect(self.notice)
        self.job.signals.error.connect(self.error)
        self.job.signals.done.connect(lambda result: self.finished(result, done))
        self.pool.start(self.job)

    def finished(self, result, callback):
        self.busy = False
        self.page_holder.setEnabled(True)
        self.progress.hide()
        self.primary.setEnabled(True)
        self.restore_btn.setEnabled(True)
        self.notice("")
        callback(result)

    def error(self, message):
        self.busy = False
        self.page_holder.setEnabled(True)
        self.progress.hide()
        self.primary.setEnabled(True)
        self.restore_btn.setEnabled(True)
        self.monitoring = False
        self.notice(message)

    def show_stage(self, stage):
        self.stage = stage
        self.clear_page()
        self.notice("")
        for i, label in enumerate(self.step_labels):
            label.setProperty("active", i == stage)
            label.setProperty("done", i < stage)
            label.style().unpolish(label)
            label.style().polish(label)
            label.setAccessibleName(f"{STEPS[i]}, " + ("current step" if i == stage else "complete" if i < stage else "upcoming"))
        can_restore = self.session is not None and self.session.data.get("state") in {
            "waiting_for_authorization", "verifying", "completed", "unresolved"}
        if self.session is not None and self.session.data.get("state") == "backup_verified" and self.snapshot.get("adi"):
            can_restore = (Path(self.snapshot["adi"]).parent / f"adi.apple-music-skip-fix.{self.session.id}.backup").exists()
        self.restore_btn.setVisible(can_restore)
        self.heading_label = self.add(text(HEADINGS[stage], "heading"))
        self.intro_label = self.add(text(INTRO[stage], "intro"))
        if self.demo:
            self.add(text("DEMO · Synthetic data. No Apple Music files or settings are accessed.", "caption"))
        getattr(self, f"page_{stage}")()
        self.content.addStretch(1)
        self.apply_responsive()
        self.scroll.verticalScrollBar().setValue(0)
        self.primary.setFocus(Qt.FocusReason.OtherFocusReason)

    def page_0(self):
        self.add(text("A focused repair, with a way back.", "subheading"))
        self.fact("Your music", "Downloads and playlists are kept")
        self.fact("Your account", "Sign in only inside Apple Music")
        self.fact("Your control", "Review findings before any repair")
        self.symptom = QCheckBox("My previously downloaded songs skip without playing")
        self.symptom.setChecked(self.demo)
        self.add(self.symptom)
        self.add(text("For the Microsoft Store app on Windows 11 x64. This assistant targets authorization-related skipping, not every playback problem.", "caption"))
        if not self.demo and Session.saved(self.root / "Sessions"):
            self.button("Open a previous repair / recovery…", self.open_history)
        self.primary.setText("Check my setup")

    def page_1(self):
        self.fact("Apple Music", "Version " + str(self.snapshot.get("version", "unknown")))
        found = bool(self.diag.get("codes"))
        self.fact("Recent logs", "Authorization-related errors found" if found else "No matching evidence yet")
        if not found:
            self.add(text("Missing evidence does not mean the cache is faulty. Continue only if your old downloads are still skipping; use Apple’s general playback help for other symptoms.", "caption"))
        self.button("Choose library folder…", lambda: self.choose("library"))
        self.button("Choose downloaded music folder…", lambda: self.choose("media"))
        self.path_info = text(self.path_summary(), "caption")
        self.add(self.path_info)
        self.consent = QCheckBox("Save recovery files and close Apple Music to continue")
        self.add(self.consent)
        self.detail(json.dumps({"library": self.snapshot.get("library"), "media": self.snapshot.get("media"),
                                "log_files_read": self.diag.get("logs", 0), "codes": self.diag.get("codes", {})}, indent=2))
        self.primary.setText("Protect my library")

    def path_summary(self):
        if self.demo:
            return "Library: C:\\Users\\Demo\\Music\\Apple Music\\Apple Music Library.musiclibrary\nMusic: D:\\Music\\Apple Music"
        return "Library: " + (self.snapshot.get("library") or "Choose the active .musiclibrary folder") + "\nMusic: " + (self.snapshot.get("media") or "Choose the Media folder shown in Apple Music settings")

    def choose(self, key):
        value = QFileDialog.getExistingDirectory(self, "Choose Apple Music " + key + " folder")
        if value:
            self.snapshot[key] = value
            self.path_info.setText(self.path_summary())

    def page_2(self):
        self.fact("Recovery files", "Saved and verified with SHA-256")
        self.fact("Downloaded audio", f"{self.session.data.get('audio_files', 0):,} files recorded")
        self.add(text("The next step refreshes Apple’s shared device-authorization cache. Other Apple apps may ask you to authorize again.", "body"))
        self.add(text("Your downloads, playlists and audio-quality settings are not changed. Windows may ask for permission if the cache is protected.", "caption"))
        self.button("Open my recovery folder", self.open_backup)
        self.primary.setText("Refresh authorization cache")

    def page_3(self):
        self.fact("Previous cache", "Preserved — available to restore")
        self.button("Open Apple Music authorization", self.open_authorize)
        self.add(text("In Apple Music", "subheading"))
        self.add(text("1. Click your name at the bottom of the sidebar.\n\n2. Choose Authorize Machine.\n\n3. Enter your Apple Account password there, then click Authorize."))
        self.add(text("We never read, store, or submit your password or verification code.", "caption"))
        self.button("Read Apple’s official guide", lambda: QDesktopServices.openUrl(QUrl("https://support.apple.com/en-us/118292")))
        self.authorized = QCheckBox("Apple Music confirmed that this computer is authorized")
        self.add(self.authorized)
        self.primary.setText("Continue to playback test")

    def page_4(self):
        completed = next((i for i in range(3) if not (self.evidence[i] and self.audible[i])), 3)
        self.verify_index = min(completed, 2)
        names = ["First old download", "Second old download", "After reopening Apple Music"]
        for i, name in enumerate(names):
            self.fact(name, "Confirmed" if self.evidence[i] and self.audible[i] else "Not checked")
        if completed < 3:
            instruction = ("Choose a different old downloaded track, then start the observation." if completed == 1 else
                           "Reopen Apple Music with the button below, choose an old download, then observe again." if completed == 2 else
                           "Start an old downloaded song in Apple Music, then observe 30 seconds of playback.")
            self.add(text(instruction))
            if completed == 2:
                self.button("Close and reopen Apple Music", self.restart_music)
            self.observe_btn = self.button("Observe playback for 30 seconds", self.observe)
            self.observation = text("Waiting for you to start playback.", "caption")
            self.add(self.observation)
            if not self.media_api:
                self.manual = QCheckBox("I watched this old download play for at least 30 seconds without skipping")
                self.add(self.manual)
        self.heard = QCheckBox("I heard continuous audio, without skipping or repeating")
        if completed < 3:
            self.add(self.heard)
        self.offline = QComboBox()
        self.offline.addItems(["Offline playback not tested", "I disconnected the internet and an old download played", "An old download still failed offline"])
        self.offline.setAccessibleName("Optional offline test result")
        if completed == 3:
            self.add(text("Optional offline check", "subheading"))
            self.add(text("Disconnect the internet yourself, start another old download, then reconnect and select the result below. We do not change your network.", "caption"))
            self.add(self.offline)
        self.button("Playback still skips — show result", self.failed_verification)
        self.primary.setText("Finish verification" if completed == 3 else "Confirm this playback test")

    def page_5(self):
        v = self.session.data.get("verification", {})
        online = v.get("online") is True
        restored = self.session.data.get("state") == "restored"
        self.heading_label.setText("Previous cache restored." if restored else "Back to listening." if online else "Let’s find the next step.")
        if restored:
            self.intro_label.setText("The earlier authorization cache is back. Playback confirmations from the repair are now historical.")
        self.fact("Playback", "Previous cache restored" if restored else "Confirmed by you" if online else "Not yet confirmed")
        self.fact("Offline playback", "Needs a new check after restore" if restored else "Confirmed by you" if v.get("offline") is True else "Still failing" if v.get("offline") is False else "Not tested")
        integrity = self.session.data.get("integrity", {})
        self.fact("Existing audio", "No missing or changed payloads detected" if integrity.get("missing_or_changed") == 0 else "Review the integrity report" if integrity else "Comparison not available")
        if not online and not restored:
            self.add(text("This repair has not been proven to fix your setup. Keep your recovery files. You can restore the previous cache, retry authorization, or share a sanitized report.", "body"))
            self.button("Try authorization again", self.retry_authorization)
        self.button("Save sanitized report…", self.export_report)
        self.button("Open my recovery folder", self.open_backup)
        self.button("Project help and known limitations", lambda: QDesktopServices.openUrl(QUrl("https://github.com/farshad-zamani/apple-music-skip-fix#troubleshooting")))
        self.add(text("Only versions, error counts and step outcomes are exported. No account details, song names, keys or raw logs.", "caption"))
        self.primary.setText("Finish")

    def primary_action(self):
        if self.stage == 0:
            if not self.symptom.isChecked():
                self.notice("Select the symptom only if it matches your old downloads. No repair is recommended on a working installation.")
                return
            if self.demo:
                self.show_stage(1)
                return
            def check(progress):
                progress("Checking the current user’s Microsoft Store installation…")
                system = windows.discover()
                if not system.get("supported"):
                    raise SafetyError("Version 0.1 supports Windows 11 x64. Windows 10 and ARM64 are not supported yet.")
                if not system.get("installed"):
                    raise SafetyError("Apple Music from Microsoft Store was not found for this Windows user. Install and sign in to it first.")
                progress("Reading recent Apple Music diagnostics. Your music is not changed.")
                with tempfile.TemporaryDirectory(prefix="scan-", dir=self.root) as folder:
                    return system, windows.diagnostics(system, Path(folder))
            self.work(check, self.checked)
        elif self.stage == 1:
            if not self.consent.isChecked():
                self.notice("Confirm that Apple Music can be closed so we can make a consistent backup.")
                return
            if not all(self.snapshot.get(k) for k in ["library", "media"]):
                self.notice("Choose your library and downloaded music folders first. Find the Media location in Apple Music → Settings → Files.")
                return
            def backup(progress):
                if not self.demo:
                    windows.ensure_closed()
                self.session = Session(self.root / "Sessions")
                self.session.data.update(system=self.snapshot, diagnostic=self.diag)
                self.session.save()
                protect(self.session, Path(self.snapshot["library"]), Path(self.snapshot["preferences"]),
                        Path(self.snapshot["media"]), Path(self.snapshot["adi"]), progress)
            self.work(backup, lambda _: self.show_stage(2))
        elif self.stage == 2:
            def refresh(progress):
                validate_backup(self.session)
                progress("Preserving the previous Apple authorization cache…")
                if self.demo:
                    from .core import AdiTransaction
                    AdiTransaction(Path(self.snapshot["adi"]), self.session.id).stage()
                else:
                    windows.ensure_closed()
                    try:
                        windows.transaction("stage", self.session.id)
                    except PermissionError:
                        progress("Waiting for Windows permission. Declining keeps your backup available.")
                        if not windows.elevate("stage", self.session.id):
                            raise SafetyError("Windows permission was declined or the cache could not be refreshed. No backup was deleted; you can retry or restore.")
                self.session.state("waiting_for_authorization")
            self.work(refresh, lambda _: self.show_stage(3))
        elif self.stage == 3:
            if not self.authorized.isChecked():
                self.notice("Finish Authorize Machine in Apple Music, then confirm its success here.")
                return
            self.session.state("verifying")
            self.show_stage(4)
        elif self.stage == 4:
            complete = all(a and b for a, b in zip(self.evidence, self.audible))
            if complete:
                result = self.offline.currentIndex()
                self.finish_verification(True, None if result == 0 else result == 1)
            else:
                i = self.verify_index
                if i == 2 and not self.restart_performed:
                    self.notice("Close and reopen Apple Music with the button above before confirming this test.")
                    return
                if not self.media_api and hasattr(self, "manual") and self.manual.isChecked():
                    self.evidence[i] = True
                if not self.evidence[i] or not self.heard.isChecked():
                    self.notice("Complete the observation and confirm continuous audible playback before continuing.")
                    return
                self.audible[i] = True
                self.session.data.update(evidence=self.evidence, audible=self.audible)
                self.session.save()
                self.show_stage(4)
        else:
            self.close()

    def checked(self, result):
        self.snapshot, self.diag = result
        self.show_stage(1)

    def open_history(self):
        ids = Session.saved(self.root / "Sessions")
        labels = []
        for sid in ids:
            s = Session(self.root / "Sessions", sid)
            labels.append(s.data.get("created", "")[:19].replace("T", " ") + " UTC · " + s.data.get("state", "unknown") + " · " + sid[:8])
        chosen, ok = QInputDialog.getItem(self, "Previous repairs", "Choose a local repair session", labels, 0, False)
        if ok:
            self.session = Session(self.root / "Sessions", ids[labels.index(chosen)])
            self.snapshot = self.session.data.get("system", {})
            self.diag = self.session.data.get("diagnostic", {})
            if self.session.data.get("state") == "created":
                self.session = None
                self.show_stage(1)
                self.notice("The previous backup did not finish. Create a fresh verified backup before repairing.")
                return
            self.show_stage(5 if self.session.data.get("state") in {"completed", "unresolved", "restored"} else 2 if self.session.data.get("state") == "backup_verified" else 3)

    def retry_authorization(self):
        self.evidence, self.audible = [False] * 3, [False] * 3
        self.observed_tracks = [None] * 3
        self.restart_performed = False
        self.session.data["verification"] = {}
        self.session.data.update(evidence=self.evidence, audible=self.audible)
        self.session.state("waiting_for_authorization")
        self.show_stage(3)

    def open_backup(self):
        if self.session:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.session.folder)))

    def open_authorize(self):
        if self.demo:
            self.notice("Demo: Apple Music would open here. Enter credentials only in Apple’s own window.")
        else:
            self.work(lambda _: windows.launch(True), lambda result: self.notice(
                "Apple Music is open. Complete Authorize Machine there, then return here." if result.get("authorization_opened") else
                "Apple Music is open. Follow the three steps above; automatic navigation was unavailable."))

    def restart_music(self):
        if self.demo:
            self.restart_performed = True
            self.notice("Demo: the restart check is simulated.")
            return
        def restart(progress):
            progress("Closing Apple Music without forcing its processes…")
            windows.ensure_closed()
            windows.launch()
        def restarted(_):
            self.restart_performed = True
            self.notice("Apple Music was reopened. Select an old download and observe its playback.")
        self.work(restart, restarted)

    def observe(self):
        if self.verify_index == 2 and not self.restart_performed:
            self.notice("Use Close and reopen Apple Music first, so this test checks a fresh launch.")
            return
        self.monitoring = True
        self.observe_btn.setEnabled(False)
        def observe(progress):
            tracker = PlaybackCheck(30)
            deadline = time.monotonic() + (5 if self.demo else 100)
            first = None
            while time.monotonic() < deadline:
                sample = ({"Title": f"Demo old download {self.verify_index + 1}", "Artist": "Demo artist", "Status": "Playing", "Position": 40}
                          if self.demo else {})
                if not self.demo:
                    try:
                        sample = windows.media_sample()
                    except SafetyError:
                        return {"manual": True}
                if not sample:
                    if first is None:
                        return {"manual": True}
                    tracker.feed({})
                else:
                    if first is None:
                        first = sample
                        identity = hashlib.sha256((sample.get("Title", "") + "\0" + sample.get("Artist", "")).encode()).hexdigest()
                        if self.verify_index == 1 and identity == self.observed_tracks[0]:
                            raise SafetyError("Choose a different old downloaded track for the second test.")
                    done = tracker.feed(sample)
                    progress("Observing playback — " + ("30 seconds confirmed" if done else "keep the same old song playing"))
                    if done or self.demo:
                        return {"confirmed": True, "identity": hashlib.sha256((sample.get("Title", "") + "\0" + sample.get("Artist", "")).encode()).hexdigest()}
                time.sleep(3)
            return False
        self.work(observe, self.observed)

    def observed(self, success):
        self.monitoring = False
        if isinstance(success, dict) and success.get("manual"):
            self.media_api = False
            self.show_stage(4)
            self.notice("Windows playback observation is unavailable. Use the manual 30-second confirmation below; the result will be labeled as user-confirmed.")
            return
        if success:
            self.evidence[self.verify_index] = True
            self.observed_tracks[self.verify_index] = success.get("identity")
            self.observation.setText("30 seconds of continuous progress confirmed. Please confirm what you heard.")
            self.notice("Playback progress was confirmed. Tick the audio confirmation to continue.")
        else:
            self.observe_btn.setEnabled(True)
            self.notice("Continuous playback was not confirmed. Try another old download, or report that playback still skips.")

    def failed_verification(self):
        self.finish_verification(False, None)

    def finish_verification(self, online, offline):
        self.session.data["verification"] = {"online": online, "offline": offline,
                                              "restart": self.evidence[2] and self.audible[2],
                                              "method": "windows-media-session-and-user" if self.media_api else "manual-user-confirmation"}
        def finish(progress):
            progress("Comparing the original audio inventory…")
            before = json.loads((self.session.folder / "media-inventory.json").read_text(encoding="utf-8"))
            self.session.data["integrity"] = compare_inventory(Path(self.snapshot["media"]), before)
            self.session.state("completed" if online else "unresolved")
        self.work(finish, lambda _: self.show_stage(5))

    def restore(self):
        if not self.session or self.busy:
            return
        answer = QMessageBox.question(self, "Restore previous authorization cache?",
            "Apple Music will close. We’ll preserve the new cache and put the old cache back. Your music and library databases will not be restored or overwritten.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        def rollback(progress):
            progress("Restoring the previous authorization cache…")
            if self.demo:
                from .core import AdiTransaction
                AdiTransaction(Path(self.snapshot["adi"]), self.session.id).restore()
            else:
                windows.ensure_closed()
                try:
                    windows.transaction("restore", self.session.id)
                except PermissionError:
                    if not windows.elevate("restore", self.session.id):
                        raise SafetyError("Restore was not completed. Keep the recovery folder and retry when Windows permission is available.")
            self.session.state("restored")
        self.work(rollback, lambda _: self.show_stage(5))

    def export_report(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save sanitized diagnostic report", "AppleMusicSkipFix-report.json", "JSON report (*.json)")
        if filename:
            from .core import atomic_json
            atomic_json(Path(filename), shareable_report(self.session, self.snapshot, self.diag))
            self.notice("Sanitized report saved. Private recovery files were not included.")

    def demo_data(self):
        library, media, prefs, adi = [self.root / name for name in ["Demo Library.musiclibrary", "Demo Music", "Demo Preferences", "Apple/adi"]]
        for p in [library, media, prefs, adi]:
            p.mkdir(parents=True)
        (library / "Library.musicdb").write_bytes(b"Synthetic demo metadata, not a real library")
        (prefs / "preferences.plist").write_bytes(b"synthetic preferences")
        (media / "old-download.frag").write_bytes(b"synthetic audio payload")
        (adi / "identity.pb").write_bytes(b"Synthetic identity, not an Apple key")
        self.snapshot = {"version": "1.7 (demo)", "build": "26100 (demo)", "installed": True, "supported": True,
                         "library": str(library), "media": str(media), "preferences": str(prefs), "adi": str(adi)}
        self.diag = {"codes": {"-42812": 8, "-45061": 1}, "logs": 2, "starts": 0, "failures": 8}

    def demo_session(self):
        from .core import AdiTransaction
        self.session = Session(self.root / "Sessions")
        self.session.data.update(system=self.snapshot, diagnostic=self.diag)
        protect(self.session, Path(self.snapshot["library"]), Path(self.snapshot["preferences"]),
                Path(self.snapshot["media"]), Path(self.snapshot["adi"]))
        self.session.data["integrity"] = {"checked": 1, "missing_or_changed": 0}
        if self.stage >= 3:
            AdiTransaction(Path(self.snapshot["adi"]), self.session.id).stage()
            self.session.state("waiting_for_authorization")

    def closeEvent(self, event):
        if self.busy:
            self.notice("Please let this step finish. Recovery status is being saved.")
            event.ignore()
        else:
            event.accept()
