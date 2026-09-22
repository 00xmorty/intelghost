# IntelGhost v0.3.0

Opt-in bundled-helper coverage and explicit scan limits.

- Adds `--include-bundled` to traverse `Contents/Resources` and `node_modules`, which default recursive scans intentionally skip.
- Adds JSON `coverage` metadata and text scope warnings, including in quiet mode.
- Applies the global file cap to explicit file roots as well as recursive visits; reports when more files were omitted.
- Keeps existing JSON finding fields and finding-based exit codes. Neither exit 0 nor `file_limit_reached: false` certifies complete coverage.
- Adds regression tests for nested helpers, preserved exclusions, directory symlinks, global caps, JSON and text warnings.
- Adds a macOS integration check that compiles Intel and ARM objects, detects the Intel helper in expanded mode, and verifies unchanged fixture bytes without executing either object.

Default recursion stays conservative. Missing paths, unreadable entries, symlinks and unrecognized formats remain coverage limitations. Reports contain local paths; review before sharing.

Safety: read-only, no deletion, no sudo, no telemetry, no network calls. Expanded scans can take longer but retain the file cap and existing per-file lipo timeout.
