# IntelGhost v0.2.0

Bundle-aware reporting release.

- Groups nested Intel-only binaries under the nearest recognized app, plug-in, framework, or extension bundle.
- Adds `component`, `component_type`, and `component_path` to each JSON finding.
- Adds `affected_component_count` so multiple binaries inside one legacy product count as one component.
- Skips app `Contents/Resources` directories to reduce irrelevant file visits while retaining executable and helper scans.
- Adds fixture-backed VST ownership and multi-binary grouping tests.

Safety: no deletion, no mutation, no sudo, no telemetry, no network calls.
