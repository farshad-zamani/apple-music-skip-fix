# Apple Music Skip Fix

<!-- impeccable:product-schema 1 -->

## Platform
Windows 11 x64 desktop (Qt Widgets).

## Stack
Delegated by the user and confirmed in the implementation plan: Python 3.13, PySide6, fixed PowerShell Windows adapters, PyInstaller one-folder distribution, per-user Inno Setup installer.

## Users and purpose
People whose Microsoft Store Apple Music app skips previously downloaded tracks. Restore authorization-related playback while preserving existing downloads. This is an independent MIT-licensed project, not an Apple product.

## Confirmed workflow
Check, Protect, Refresh, Authorize, Verify, Result. User chose cache refresh before official authorization. Passwords and verification codes are entered only in Apple Music. A verified backup is required before ADI changes. Verification requires real playback progress and audible-playback confirmation; offline confirmation is optional and distinct.

## Constraints
English UI. Discover package and user paths. Do not modify music, library databases, quality settings, registry, networking, drivers or services. Private backups remain local. Export allowlisted diagnostic fields only. No telemetry, account, server or automatic updater. No live cache-reset tests on the user's now healthy installation. Demo mode must never use real adapters.

## Approved design
The user explicitly approved a Windows task assistant with a left step rail, central content, one primary bottom action, expandable technical detail, Segoe UI, raspberry accent, light/dark themes, authored icon, keyboard navigation and 100–200% DPI support. This pinned direction is the visual authority; do not reopen the design interview.

## Evidence
One real repair with preserved downloaded payloads and official reauthorization succeeded. The user subsequently confirmed offline playback. This is evidence from one machine, not a universal success rate. Original personal logs, media, keys, settings and backups must not enter the repository.

## Release
Public repository farshad-zamani/apple-music-skip-fix; version 0.1.0; unsigned installer and portable ZIP, SHA-256 checksums and honest test coverage.
