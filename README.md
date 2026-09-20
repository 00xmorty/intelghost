# IntelGhost

IntelGhost is a small, dependency-free, read-only CLI that looks for scoped Intel-only Mach-O components before the macOS 28 Rosetta cutoff.

Apple's own Settings list can miss plugins, loaders, helpers, and developer artifacts. IntelGhost scans common app/plugin locations and reports binaries that contain Intel architectures (`x86_64` or `i386`) without Apple Silicon (`arm64` or `arm64e`).

## Install / run

```bash
curl -L -o intelghost https://github.com/00xmorty/intelghost/releases/latest/download/intelghost
chmod +x intelghost
./intelghost
```

From a clone:

```bash
python3 ./intelghost --path /Applications --max-files 5000
python3 ./intelghost --json --path ~/Library/Audio/Plug-Ins
```

## What it checks

By default IntelGhost scans a bounded set of common locations:

- `/Applications` and `~/Applications`
- Audio, QuickLook, Spotlight, ColorPicker, printer, and Internet plug-in folders
- LaunchAgents / LaunchDaemons
- Homebrew roots (`/usr/local/Homebrew`, `/opt/homebrew`)

For every Mach-O candidate it calls `lipo -archs` and reports only Intel-only findings.

## Safety

- Read-only: no deletion, no quarantine changes, no `sudo`, no preferences writes.
- No telemetry and no network calls.
- Scoped scan with `--max-files` safety cap.
- Reports local paths because paths are necessary for diagnosis; review/redact output before sharing it.

## Limitations

- macOS-focused. On Linux CI it is tested with fixtures and fake `lipo`; real scanning needs macOS tools.
- A finding means the file is Intel-only, not that it is loaded, used, harmful, or safe to delete.
- Universal binaries are not flagged even if some plugins inside a package have separate issues.
- Rosetta detection is best-effort and may change in future macOS releases.
- The default path list is intentionally conservative and will not find every possible binary on disk.

## Exit codes

- `0`: no Intel-only findings
- `2`: one or more Intel-only findings

## Example

```text
IntelGhost v0.1.0 — read-only Intel-only component scan
Rosetta: installed
Mach-O scanned: 42  skipped: 0
Intel-only findings: 1
- /Library/Audio/Plug-Ins/VST/OldPlugin.vst/Contents/MacOS/OldPlugin :: x86_64 :: update/remove before macOS 28
```
