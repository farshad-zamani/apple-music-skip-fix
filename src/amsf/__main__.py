from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Apple Music Skip Fix — independent Windows repair assistant")
    parser.add_argument("--demo", action="store_true", help="Use synthetic data; never access Apple Music")
    parser.add_argument("--page", choices=["check", "protect", "refresh", "authorize", "verify", "result"], default="check")
    parser.add_argument("--theme", choices=["system", "light", "dark"], default="system")
    parser.add_argument("--screenshot", type=Path, help="Capture the demo window only")
    parser.add_argument("--width", type=int, default=1060)
    parser.add_argument("--height", type=int, default=760)
    parser.add_argument("--smoke-test", action="store_true", help="Open demo briefly and exit")
    parser.add_argument("--self-check", action="store_true", help="Read-only Windows adapter check")
    parser.add_argument("--helper", choices=["stage", "restore"], help=argparse.SUPPRESS)
    parser.add_argument("--session", help=argparse.SUPPRESS)
    parser.add_argument("--caller-pid", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    from . import windows
    if args.helper:
        if not args.session or not args.caller_pid or args.demo or args.self_check:
            return 2
        try:
            windows.transaction(args.helper, args.session, elevated=True, caller_pid=args.caller_pid)
            return 0
        except Exception:
            return 1
    if args.self_check:
        try:
            value = windows.discover()
            print(json.dumps({k: value[k] for k in ["installed", "supported", "build", "version"]}))
            return 0
        except Exception:
            return 1
    if args.screenshot and not args.demo:
        parser.error("Screenshots are available only with --demo (no personal information).")
    from PySide6.QtWidgets import QApplication, QMessageBox
    from PySide6.QtCore import QTimer
    from .gui import MainWindow, STEPS
    app = QApplication(sys.argv[:1])
    app.setApplicationName("Apple Music Skip Fix")
    app.setOrganizationName("AppleMusicSkipFix")
    app.setStyle("Fusion")
    mutex = None
    try:
        if not args.demo and not args.smoke_test:
            mutex = windows.Mutex(r"Local\AppleMusicSkipFix.Desktop")
            mutex.__enter__()
        window = MainWindow(demo=args.demo or args.smoke_test, theme=args.theme,
                            page=STEPS.index(args.page.title()))
    except Exception as exc:
        from .core import SafetyError
        QMessageBox.information(None, "Apple Music Skip Fix", str(exc) if isinstance(exc, SafetyError) else
                                "The app could not open its local recovery folder. Check Windows folder access and try again.")
        return 1
    available = app.primaryScreen().availableGeometry()
    window.resize(min(args.width, available.width()), min(args.height, available.height()))
    window.show()
    if args.screenshot:
        def capture():
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            window.grab().save(str(args.screenshot))
            window.close()
        QTimer.singleShot(700, capture)
    if args.smoke_test:
        QTimer.singleShot(1000, window.close)
    try:
        return app.exec()
    finally:
        if mutex:
            mutex.__exit__(None, None, None)


if __name__ == "__main__":
    raise SystemExit(main())
