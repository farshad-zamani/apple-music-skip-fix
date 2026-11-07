# Architecture and safety boundaries

`gui.py` owns the six-step state machine and background jobs. `core.py` owns verified copies, private journals, media inventory, ADI rename transactions and report allowlisting. `windows.py` and fixed bundled PowerShell scripts are the only Windows integration layer. `__main__.py` routes GUI, synthetic demo, read-only self-check and the closed helper command.

## Transaction

The active library must contain `Library.musicdb`; the selected Media folder must contain audio payloads. Essential `.musicdb`, `.itdb`, `.plist` metadata and current package preferences are copied while Apple Music is closed. Each copied file is hashed before/after copying and checked against its source. All copies must pass before `backup_verified` is persisted. Media is inventoried, not copied or modified.

ADI is always derived from the Windows ProgramData Known Folder, never from a supplied user path. The original directory is renamed beside itself with a validated UUID; this retains its contents and ACLs. A sibling transaction record is written before the rename. Staging and restore are idempotent around interruption points. Restore retains the fresh directory under `.after` before putting the original back. No repair code recursively deletes an ADI directory.

The app uses a desktop mutex and a global cache-operation mutex. It checks that the relevant Apple processes are closed; other Windows users' active Apple Music/TV sessions conservatively block the shared-cache operation. Sources and destinations are checked for reparse points. Copy failures, unavailable drives, insufficient backup space and inconsistent source files prevent cache refresh.

## Privilege boundary

The GUI runs as the current user. A permission failure during the fixed cache operation may invoke the same application executable through Windows `runas`, with only `--helper stage|restore --session <UUID> --caller-pid <PID>`. (The first release is unsigned.) The helper checks the still-running caller's executable, resolves the original user's LocalAppData through that process's Windows token, requires the existing session, independently verifies every recovery copy, and compares the exact cache contents with the verified snapshot. It accepts no arbitrary paths or shell text. The mutation target is the OS-resolved ProgramData ADI path and UUID-derived siblings. It does not launch Apple Music, read credentials or create session records in an alternate administrator profile. It returns an exit status; the GUI retains recovery state when permission is declined.

Scripts run with fixed argument arrays, no user-supplied code, `-NoProfile`, no shell interpolation, bounded timeouts and hidden console windows. `-ExecutionPolicy Bypass` is process-scoped for the bundled scripts; it does not change Windows' configured execution policy. Managed environments that block scripts are reported as unsupported integration steps, not bypassed by registry edits.

## Diagnostics and privacy

Recent ETL files are bounded in size/count and converted with Windows `tracerpt`. XML parsing disables entity expansion. Error signatures are clues, not an assertion of a unique cause. Locale-formatted trace dates are not parsed as Gregorian dates; no exact before/after attribution is fabricated from ambiguous timestamps.

Windows Media Sessions are read only. Titles are used transiently to distinguish samples; reports include no titles. Offline and audible playback require the user's own confirmation. The assistant never captures sound or disconnects networking.

Private journals/backups use the current user's LocalAppData profile. Sharing is allowlist-based: only numeric versions, recognized codes and fixed outcomes are serialized. The app has no telemetry or upload endpoint. Source/build directories must never contain real `.pb`, `.musicdb`, `.plist`, media or personal log fixtures.

## Demo

Demo owns a new temporary root and synthetic library, preference, audio and identity files. It never calls live discovery, playback, launch, close, elevation or transaction adapters. Screenshots are permitted only in demo mode. The test suite enforces these boundaries.
