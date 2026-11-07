"""Local transactions. No GUI, shell interpolation, networking, or music writes."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from defusedxml.ElementTree import iterparse
from . import __version__

PAYLOADS = {".frag", ".initfrag", ".m4p", ".m4v", ".m4a", ".mp3", ".flac", ".wav", ".aac"}
CODES = ("-11800", "-42812", "-42829", "-45061", "-45054", "7513", "7505")
METADATA = {".musicdb", ".itdb", ".plist"}
TERMINAL = {"completed", "restored"}


class SafetyError(RuntimeError):
    """An operation cannot safely continue."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def checked_id(value: str) -> str:
    if str(uuid.UUID(value)) != value:
        raise SafetyError("Invalid repair session identifier.")
    return value


def no_links(path: Path) -> Path:
    path = Path(os.path.abspath(path))
    for part in [path, *path.parents]:
        try:
            s = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(s.st_mode) or getattr(s, "st_file_attributes", 0) & 0x400:
            raise SafetyError("A protected path contains a symbolic link or junction. No changes were made.")
    return path


def inside(path: Path, root: Path) -> Path:
    root, path = no_links(root), no_links(path)
    if path == root or not path.is_relative_to(root):
        raise SafetyError("The operation would leave its permitted folder.")
    return path


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path: Path, data: dict | list) -> None:
    no_links(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    no_links(temp)
    with temp.open("w", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def walk_files(root: Path):
    no_links(root)
    if not root.is_dir():
        raise SafetyError("The selected folder is unavailable. Connect its drive and try again.")
    def fail(error):
        raise error
    for directory, dirs, files in os.walk(root, followlinks=False, onerror=fail):
        for name in dirs:
            no_links(Path(directory) / name)
        for name in files:
            p = no_links(Path(directory) / name)
            if not p.is_file():
                raise SafetyError("An unexpected item was found in the backup source.")
            yield p


def inventory(root: Path, progress: Callable[[str], None] = lambda _: None) -> list[dict]:
    rows = []
    for p in walk_files(root):
        if p.suffix.lower() in PAYLOADS:
            s = p.stat()
            rows.append({"relative": p.relative_to(root).as_posix(), "size": s.st_size,
                         "mtime_ns": s.st_mtime_ns})
            if len(rows) % 1000 == 0:
                progress(f"Recording downloaded audio: {len(rows):,} files")
    return rows


def compare_inventory(root: Path, before: list[dict]) -> dict:
    changed = 0
    for row in before:
        p = inside(root / row["relative"], root)
        try:
            s = p.stat()
            changed += s.st_size != row["size"] or s.st_mtime_ns != row["mtime_ns"]
        except FileNotFoundError:
            changed += 1
    return {"checked": len(before), "missing_or_changed": changed,
            "method": "size-and-modification-time"}


class Session:
    def __init__(self, root: Path, session_id: str | None = None):
        self.root = no_links(root)
        self.id = checked_id(str(uuid.uuid4()) if session_id is None else session_id)
        self.folder = inside(self.root / self.id, self.root)
        self.path = self.folder / "session.json"
        if self.path.exists():
            if self.path.stat().st_size > 1024 * 1024:
                raise SafetyError("The repair record is unexpectedly large.")
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
            if self.data.get("id") != self.id or self.data.get("schema") != 1:
                raise SafetyError("The repair record is invalid.")
        else:
            self.data = {"schema": 1, "id": self.id, "created": utc_now(), "state": "created",
                         "events": [], "verification": {}}
            self.save()

    def save(self):
        atomic_json(self.path, self.data)

    def state(self, state: str):
        self.data["state"] = state
        self.data["events"].append({"state": state, "at": utc_now()})
        self.save()

    @staticmethod
    def saved(root: Path) -> list[str]:
        if not root.exists():
            return []
        result = []
        for p in root.glob("*/session.json"):
            try:
                no_links(p)
                data = json.loads(p.read_text(encoding="utf-8"))
                if data.get("schema") == 1:
                    result.append(checked_id(p.parent.name))
            except (OSError, ValueError, SafetyError):
                continue
        return sorted(result, key=lambda sid: (root / sid / "session.json").stat().st_mtime, reverse=True)

    @staticmethod
    def pending(root: Path) -> list[str]:
        return [sid for sid in Session.saved(root) if
                json.loads((root / sid / "session.json").read_text(encoding="utf-8")).get("state") not in TERMINAL]


def verified_copy(source: Path, destination: Path) -> dict:
    no_links(source)
    no_links(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    original = digest(source)
    before = source.stat()
    shutil.copy2(source, destination)
    if original != digest(destination) or original != digest(source):
        raise SafetyError("A backup file failed its SHA-256 check. Repair has not started.")
    after = source.stat()
    if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
        raise SafetyError("An Apple file changed during backup. Close Apple apps and try again.")
    return {"relative": destination.name, "size": after.st_size, "sha256": original}


def protect(session: Session, library: Path, preferences: Path, media: Path, adi: Path,
            progress: Callable[[str], None] = lambda _: None) -> None:
    if session.data["state"] != "created":
        raise SafetyError("This session already has a backup. Resume it instead of creating another.")
    no_links(library)
    no_links(preferences)
    no_links(adi)
    if not (library / "Library.musicdb").is_file():
        raise SafetyError("Choose the active Apple Music .musiclibrary folder first.")
    files = [(p, "library/" + p.relative_to(library).as_posix()) for p in walk_files(library)
             if p.suffix.lower() in METADATA and "artwork" not in p.relative_to(library).parts]
    if preferences.exists():
        files += [(p, "preferences/" + p.relative_to(preferences).as_posix())
                  for p in walk_files(preferences) if p.suffix.lower() == ".plist"]
    adi_files = list(walk_files(adi)) if adi.exists() else []
    if len(adi_files) > 256 or sum(p.stat().st_size for p in adi_files) > 32 * 1024 * 1024:
        raise SafetyError("The Apple authorization cache is not in an expected form. No repair was made.")
    files += [(p, "adi/" + p.relative_to(adi).as_posix()) for p in adi_files]
    needed = sum(p.stat().st_size for p, _ in files) * 2 + 32 * 1024 * 1024
    if shutil.disk_usage(session.folder).free < needed:
        raise SafetyError("There is not enough free space for a verified backup.")
    entries = []
    for index, (source, relative) in enumerate(files):
        progress(f"Protecting library and authorization metadata: {index + 1}/{len(files)}")
        entry = verified_copy(source, inside(session.folder / "backup" / relative, session.folder))
        entry["relative"] = relative
        entries.append(entry)
    progress("Recording existing downloaded audio. Music files are not copied or changed.")
    media_list = inventory(media, progress)
    if not media_list:
        raise SafetyError("No downloaded audio was found in that folder. Choose your Media folder.")
    atomic_json(session.folder / "media-inventory.json", media_list)
    atomic_json(session.folder / "backup-manifest.json", {"schema": 1, "files": entries})
    session.data.update({"library": str(library), "media": str(media), "adi": str(adi),
                         "audio_files": len(media_list), "backup_verified": True})
    session.state("backup_verified")


def validate_backup(session: Session) -> None:
    if not session.data.get("backup_verified"):
        raise SafetyError("A verified backup is required before refreshing the cache.")
    manifest = session.folder / "backup-manifest.json"
    no_links(manifest)
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if data.get("schema") != 1 or not data.get("files"):
        raise SafetyError("The backup record is incomplete.")
    for item in data["files"]:
        p = inside(session.folder / "backup" / item["relative"], session.folder / "backup")
        if not p.is_file() or digest(p) != item["sha256"]:
            raise SafetyError("A recovery file changed or is missing. The cache was not refreshed.")


def validate_cache_snapshot(session: Session, source: Path) -> None:
    """Verify that the exact cache about to be staged is already protected."""
    data = json.loads((session.folder / "backup-manifest.json").read_text(encoding="utf-8"))
    expected = {item["relative"][4:]: item["sha256"] for item in data["files"]
                if item["relative"].startswith("adi/")}
    actual = {p.relative_to(source).as_posix(): p for p in walk_files(source)}
    if not expected or expected.keys() != actual.keys() or any(digest(actual[k]) != v for k, v in expected.items()):
        raise SafetyError("The authorization cache changed after backup. Create a fresh protected session before refreshing it.")


class AdiTransaction:
    """The Windows entrypoint supplies only the fixed, OS-resolved ADI path."""
    def __init__(self, adi: Path, session_id: str):
        self.adi = no_links(adi)
        self.parent = no_links(adi.parent)
        self.id = checked_id(session_id)
        self.old = inside(self.parent / f"adi.apple-music-skip-fix.{self.id}.backup", self.parent)
        self.new = inside(self.parent / f"adi.apple-music-skip-fix.{self.id}.after", self.parent)
        self.journal = inside(self.parent / f"apple-music-skip-fix.{self.id}.json", self.parent)

    def stage(self):
        # Directory rename preserves original contents and ACLs, including after power loss.
        if self.old.exists():
            if self.journal.exists() and json.loads(self.journal.read_text()).get("operation") in {"staging", "staged"}:
                atomic_json(self.journal, {"schema": 1, "operation": "staged", "session": self.id})
                return
            raise SafetyError("A backup already exists. It will not be overwritten.")
        if not self.adi.is_dir():
            raise SafetyError("There is no existing ADI cache to refresh. Authorize Apple Music directly.")
        atomic_json(self.journal, {"schema": 1, "operation": "staging", "session": self.id})
        self.adi.rename(self.old)
        atomic_json(self.journal, {"schema": 1, "operation": "staged", "session": self.id})

    def restore(self):
        record = json.loads(self.journal.read_text(encoding="utf-8")) if self.journal.exists() else {}
        if record.get("session") != self.id or record.get("operation") not in {"staged", "staging", "restoring", "restored"}:
            raise SafetyError("This cache does not have a valid repair record.")
        if record.get("operation") == "restored":
            return
        if not self.old.exists():
            if record.get("operation") == "restoring" and self.adi.exists():
                atomic_json(self.journal, {"schema": 1, "operation": "restored", "session": self.id})
                return
            raise SafetyError("The original cache backup is unavailable.")
        atomic_json(self.journal, {"schema": 1, "operation": "restoring", "session": self.id})
        if self.adi.exists():
            if self.new.exists():
                raise SafetyError("A later cache is already preserved. No folder will be overwritten.")
            self.adi.rename(self.new)
        self.old.rename(self.adi)
        atomic_json(self.journal, {"schema": 1, "operation": "restored", "session": self.id})


def scan_xml(path: Path) -> dict:
    counts = {code: 0 for code in CODES}
    starts = failures = 0
    try:
        for _, element in iterparse(path, events=("end",)):
            if element.attrib.get("Name") == "StringMessage":
                text = element.text or ""
                for code in CODES:
                    # Do not infer meaning from localized wall-clock strings.
                    import re
                    counts[code] += len(re.findall(r"(?<![\d-])" + re.escape(code) + r"(?!\d)", text))
                starts += "-> StartSuccess" in text
                failures += "qos> error:" in text or "HandlePlaybackError" in text
            element.clear()
    except Exception as exc:
        raise SafetyError("A diagnostic log was incomplete or unsupported; it was not used as proof.") from exc
    return {"codes": {k: v for k, v in counts.items() if v}, "starts": starts, "failures": failures}


class PlaybackCheck:
    def __init__(self, seconds: int = 30):
        self.seconds = seconds
        self.identity = None
        self.start_position = self.last = None
        self.started_at = None
        self.complete = False
        self.last_at = None

    def feed(self, sample: dict, clock: float | None = None) -> bool:
        now = time.monotonic() if clock is None else clock
        identity = (sample.get("Title"), sample.get("Artist"))
        p = sample.get("Position")
        if sample.get("Status") != "Playing" or not identity[0] or p is None:
            self.__init__(self.seconds)
            return False
        allowed_jump = max(3, now - self.last_at + 2) if self.last_at is not None else 3
        if identity != self.identity or (self.last is not None and (p < self.last - 1 or p - self.last > allowed_jump)):
            self.identity, self.start_position, self.started_at = identity, p, now
        self.last, self.last_at = p, now
        if self.started_at is not None:
            self.complete = (now - self.started_at >= self.seconds and p - self.start_position >= self.seconds - 2)
        return self.complete


def shareable_report(session: Session, system: dict, diagnostic: dict) -> dict:
    """Allowlist construction: never serialize private dictionaries or exception strings."""
    verification = session.data.get("verification", {})
    if session.data.get("state") == "restored":
        verification = {}
    import re
    def version(value):
        value = str(value)
        return value if re.fullmatch(r"\d+(?:\.\d+){0,4}", value) else "unknown"
    state = session.data.get("state")
    method = verification.get("method")
    return {"application": "Apple Music Skip Fix", "version": __version__, "schema": 1,
            "windows_build": version(system.get("build", "unknown")),
            "apple_music_version": version(system.get("version", "unknown")),
            "error_codes": {code: int(diagnostic.get("codes", {}).get(code, 0)) for code in CODES},
            "repair_state": state if state in {"created", "backup_verified", "waiting_for_authorization", "verifying", "completed", "unresolved", "restored"} else "unknown",
            "backup_verified": bool(session.data.get("backup_verified")),
            "audio_payloads_checked": int(session.data.get("audio_files", 0)),
            "audio_payloads_missing_or_changed": session.data.get("integrity", {}).get("missing_or_changed"),
            "online_confirmed": verification.get("online") is True,
            "offline_confirmed_by_user": verification.get("offline") is True,
            "offline_result": "confirmed" if verification.get("offline") is True else "failed" if verification.get("offline") is False else "not-tested",
            "restart_confirmed_by_user": verification.get("restart") is True,
            "verification_method": method if method in {"windows-media-session-and-user", "manual-user-confirmation", "demo"} else "not-tested"}
