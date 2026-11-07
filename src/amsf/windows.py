"""Windows integration, kept outside the transaction engine."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from .core import (AdiTransaction, SafetyError, Session, checked_id, scan_xml,
                   validate_backup, validate_cache_snapshot, no_links)


def known_folder(identifier: str, token=None) -> Path:
    import uuid
    guid = (ctypes.c_ubyte * 16).from_buffer_copy(uuid.UUID(identifier).bytes_le)
    result = ctypes.c_wchar_p()
    shell = ctypes.WinDLL("shell32")
    shell.SHGetKnownFolderPath.argtypes = [ctypes.c_void_p, wintypes.DWORD, wintypes.HANDLE,
                                          ctypes.POINTER(ctypes.c_wchar_p)]
    shell.SHGetKnownFolderPath.restype = ctypes.c_long
    hr = shell.SHGetKnownFolderPath(ctypes.byref(guid), 0, token, ctypes.byref(result))
    if hr:
        raise SafetyError("Windows could not locate a required system folder.")
    try:
        return Path(result.value)
    finally:
        ctypes.windll.ole32.CoTaskMemFree(ctypes.cast(result, ctypes.c_void_p))


def data_root() -> Path:
    if sys.platform != "win32":
        raise SafetyError("This application requires Windows 11 x64.")
    return known_folder("F1B32785-6FBA-4FCF-9D55-7B8E7F157091") / "AppleMusicSkipFix"


def fixed_adi() -> Path:
    return known_folder("62AB5D82-FDC1-4DC3-A9DD-070D1D495D97") / "Apple Computer" / "iTunes" / "adi"


def resource(name: str) -> Path:
    return Path(__file__).parent / "scripts" / name


def ps(script: str, *arguments: str, timeout: int = 45):
    executable = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    proc = subprocess.run([str(executable), "-NoLogo", "-NoProfile", "-NonInteractive",
                           "-ExecutionPolicy", "Bypass", "-File", str(resource(script)), *map(str, arguments)],
                          capture_output=True, encoding="utf-8-sig", errors="replace", timeout=timeout,
                          creationflags=subprocess.CREATE_NO_WINDOW)
    if proc.returncode:
        # Raw PowerShell error output can contain personal paths. Never pass it to reports.
        raise SafetyError("A Windows integration step could not finish. Close Apple dialogs and retry, or use the manual guide.")
    try:
        return json.loads(proc.stdout.strip() or "null")
    except ValueError as exc:
        raise SafetyError("Windows returned an unsupported response. No repair was started.") from exc


class Mutex:
    def __init__(self, name: str):
        self.name, self.handle = name, None

    def __enter__(self):
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        kernel.CreateMutexW.restype = wintypes.HANDLE
        self.handle = kernel.CreateMutexW(None, True, self.name)
        if not self.handle or ctypes.get_last_error() == 183:
            if self.handle:
                kernel.CloseHandle(wintypes.HANDLE(self.handle))
                self.handle = None
            raise SafetyError("Another repair window is already running. Return to that window first.")
        return self

    def __exit__(self, *args):
        if self.handle:
            ctypes.windll.kernel32.ReleaseMutex(wintypes.HANDLE(self.handle))
            ctypes.windll.kernel32.CloseHandle(wintypes.HANDLE(self.handle))
            self.handle = None


def discover() -> dict:
    snapshot = ps("system.ps1", "-Action", "discover")
    music = known_folder("4BD8D571-6D19-48D3-BE97-422220080E43")
    library = music / "Apple Music" / "Apple Music Library.musiclibrary"
    snapshot["library"] = str(library) if library.exists() else ""
    candidates = [music / "Apple Music/Media", music / "Apple Music/Music",
                  music / "iTunes/iTunes Media", music / "Apple Music"]
    snapshot["media"] = next((str(p) for p in candidates if p.exists() and p != library), "")
    snapshot["adi"] = str(fixed_adi())
    snapshot["adi_exists"] = fixed_adi().is_dir()
    return snapshot


def ensure_closed():
    result = ps("system.ps1", "-Action", "close", timeout=40)
    if not result.get("closed"):
        raise SafetyError("Apple Music is still running. Close it and its open dialogs, wait a few seconds, then try again. Other Apple apps may also need to be closed before refreshing the shared cache.")


def launch(authorize: bool = False) -> dict:
    return ps("system.ps1", "-Action", "authorize" if authorize else "launch", timeout=30)


def media_sample() -> dict:
    value = ps("media.ps1", timeout=12)
    return value or {}


def diagnostics(snapshot: dict, work: Path) -> dict:
    from .core import no_links
    counts, starts, failures, logs = {}, 0, 0, 0
    folder = Path(snapshot.get("package_data", "")) / "LocalState/Logs"
    if not folder.is_dir():
        return {"codes": {}, "starts": 0, "failures": 0, "logs": 0}
    files = sorted(folder.rglob("*.etl"), key=lambda p: p.stat().st_mtime, reverse=True)
    selected = [p for p in files if 0 < p.stat().st_size <= 5 * 1024 * 1024
                and time.time() - p.stat().st_mtime < 7 * 86400][:10]
    work.mkdir(parents=True, exist_ok=True)
    for index, source in enumerate(selected):
        no_links(source)
        target = work / f"trace-{index}.xml"
        try:
            executable = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/tracerpt.exe"
            proc = subprocess.run([str(executable), str(source), "-o", str(target), "-of", "XML", "-y"],
                                  capture_output=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
            if proc.returncode or not target.exists() or target.stat().st_size > 100 * 1024 * 1024:
                continue
            result = scan_xml(target)
            for code, count in result["codes"].items():
                counts[code] = counts.get(code, 0) + count
            starts += result["starts"]
            failures += result["failures"]
            logs += 1
        except (OSError, subprocess.TimeoutExpired, SafetyError):
            continue
    return {"codes": counts, "starts": starts, "failures": failures, "logs": logs}


def caller_data_root(pid: int) -> Path:
    """Bind elevation to a still-running copy of this executable and its Windows profile."""
    if not 0 < pid < 2**32:
        raise SafetyError("The repair window is unavailable.")
    kernel, security = ctypes.WinDLL("kernel32", use_last_error=True), ctypes.WinDLL("advapi32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    security.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    process = kernel.OpenProcess(0x1000, False, pid)
    token = wintypes.HANDLE()
    if not process:
        raise SafetyError("The original repair window has closed.")
    try:
        name, size = ctypes.create_unicode_buffer(32768), wintypes.DWORD(32768)
        allowed = {os.path.normcase(str(no_links(Path(sys.executable))))}
        if not getattr(sys, "frozen", False):
            allowed.add(os.path.normcase(str(no_links(Path(getattr(sys, "_base_executable", sys.executable))))))
        if not kernel.QueryFullProcessImageNameW(process, 0, name, ctypes.byref(size)) or os.path.normcase(str(no_links(Path(name.value)))) not in allowed:
            raise SafetyError("The permission request does not belong to this application.")
        if not security.OpenProcessToken(process, 0x0008 | 0x0004, ctypes.byref(token)):
            raise SafetyError("Windows could not identify the original user's profile.")
        return known_folder("F1B32785-6FBA-4FCF-9D55-7B8E7F157091", token) / "AppleMusicSkipFix"
    finally:
        if token:
            kernel.CloseHandle(token)
        kernel.CloseHandle(process)


def transaction(operation: str, session_id: str, elevated: bool = False, caller_pid: int | None = None):
    checked_id(session_id)
    if operation not in {"stage", "restore"}:
        raise SafetyError("Unsupported helper operation.")
    if elevated and caller_pid is None:
        raise SafetyError("An elevated operation requires its original repair window.")
    user_root = caller_data_root(caller_pid) if elevated else data_root()
    record = no_links(user_root / "Sessions" / session_id / "session.json")
    if not record.is_file():
        raise SafetyError("A saved, verified backup is required. Start from the repair window.")
    session = Session(user_root / "Sessions", session_id)
    validate_backup(session)
    if not ps("system.ps1", "-Action", "guard").get("closed"):
        raise SafetyError("Close Apple Music and Apple TV in all Windows user sessions before changing the shared authorization cache.")
    with Mutex(r"Global\AppleMusicSkipFix.AuthorizationCache"):
        txn = AdiTransaction(fixed_adi(), session_id)
        source = txn.old if txn.old.exists() else txn.adi
        validate_cache_snapshot(session, source)
        getattr(txn, operation)()


def elevate(operation: str, session_id: str) -> bool:
    """Run only this application's closed helper command; no arbitrary command API."""
    checked_id(session_id)
    if operation not in {"stage", "restore"}:
        raise SafetyError("Unsupported helper operation.")
    class SHELLEXECUTEINFOW(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("fMask", wintypes.ULONG), ("hwnd", wintypes.HWND),
                    ("lpVerb", wintypes.LPCWSTR), ("lpFile", wintypes.LPCWSTR),
                    ("lpParameters", wintypes.LPCWSTR), ("lpDirectory", wintypes.LPCWSTR),
                    ("nShow", ctypes.c_int), ("hInstApp", wintypes.HINSTANCE), ("lpIDList", ctypes.c_void_p),
                    ("lpClass", wintypes.LPCWSTR), ("hkeyClass", wintypes.HKEY), ("dwHotKey", wintypes.DWORD),
                    ("hIcon", wintypes.HANDLE), ("hProcess", wintypes.HANDLE)]
    args = [] if getattr(sys, "frozen", False) else ["-m", "amsf"]
    args += ["--helper", operation, "--session", session_id, "--caller-pid", str(os.getpid())]
    info = SHELLEXECUTEINFOW()
    info.cbSize, info.fMask, info.lpVerb = ctypes.sizeof(info), 0x40 | 0x100, "runas"
    info.lpFile, info.lpParameters, info.nShow = sys.executable, subprocess.list2cmdline(args), 0
    ctypes.windll.shell32.ShellExecuteExW.argtypes = [ctypes.POINTER(SHELLEXECUTEINFOW)]
    ctypes.windll.kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    ctypes.windll.kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    ctypes.windll.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(info)):
        return False  # Includes user declining UAC; the verified backup remains usable.
    try:
        if ctypes.windll.kernel32.WaitForSingleObject(info.hProcess, 120000) != 0:
            raise SafetyError("The permission helper is still pending. Finish its Windows prompt, then resume this session.")
        code = wintypes.DWORD()
        ctypes.windll.kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(code))
        return code.value == 0
    finally:
        ctypes.windll.kernel32.CloseHandle(info.hProcess)
