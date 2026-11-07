# Validation and limits

The suite tests synthetic backup verification, changed recovery files, disk-space refusal, permission/copy failures, original-audio preservation, Unicode/custom paths, symlink/junction refusal, session-ID traversal, interruption/resume at both rename boundaries, saved sessions, report privacy, malformed/entity XML, Persian-calendar log timestamps, and false playback verification from seeking, stalling or skipping.

Qt workflow tests use the offscreen platform and synthetic demo. They cover required confirmations, three playback checks, manual outcome labeling, compact layout, restart gating and honest unresolved results. Demo tests replace live Windows adapters with functions that fail if called.

Release QA also checks: desktop light/dark screenshots, compact layout with scrolling and fixed actions, 200% scale, source read-only discovery on Windows 11, frozen demo startup, per-user installer and uninstaller, and recovery retention. No destructive test is run against a user's repaired Apple Music installation.

## What the first release does not prove

- The end-to-end repair is grounded in one successful Windows 11 incident; it has not been established as a universal fix across accounts or Apple Music versions.
- Real Apple Account sign-in, Apple's authorization limits and unavailable catalogs cannot be simulated by CI.
- Offscreen tests simulate permission decline and integration failures; they do not certify every UAC secure-desktop configuration or alternate administrator policy.
- Windows 10/ARM64 and managed environments blocking PowerShell are outside version 0.1 support.
- UI Automation is best effort. The manual guide is the stable fallback when Apple changes/localizes its controls.

Do not substitute successful playback of newly downloaded tracks for tests on old downloads. Do not report an offline result unless the user performed that test. Do not publish raw logs or recovery files as test evidence.
