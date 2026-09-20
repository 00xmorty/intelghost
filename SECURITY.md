# Security Policy

IntelGhost is designed as a local, read-only diagnostic utility.

## Boundaries

- No network requests.
- No telemetry.
- No `sudo`.
- No file deletion or modification.
- No preference, launchd, or system setting changes.

The tool prints local filesystem paths for diagnosis. Treat reports as potentially private and redact paths before sharing them publicly.

## Reporting a vulnerability

Please open a private security advisory on GitHub or file an issue with a minimal, non-sensitive reproduction. Do not include private file paths, serial numbers, credentials, logs, or proprietary binaries.
