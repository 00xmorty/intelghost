# IntelGhost v0.4.0

Coverage gaps are now visible instead of silently disappearing.

- Adds aggregate `coverage.missing_roots`, `unreadable_roots`, `unreadable_directories`, and `unreadable_files` counts to JSON, without disclosing those paths.
- Emits a scope warning for nonzero counts in normal and quiet text output.
- Adds fixture tests for missing inputs and denied directory/file traversal. Keeps v0.3.0 bundled-helper traversal, global file cap and existing JSON finding fields.
- Preserves finding-based exit codes: exit 0 does not certify full coverage; inspect coverage, including skipped Mach-O files.

Default recursion stays conservative. Permission races, symlinks and unrecognized formats remain coverage limitations. Findings contain local paths; review before sharing.

Safety: read-only, no deletion, no sudo, no telemetry, no network calls. Expanded scans can take longer but retain the file cap and existing per-file lipo timeout.
