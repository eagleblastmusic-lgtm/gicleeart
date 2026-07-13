# Launcher component logs outside the checkout

The classic launcher and Studio delegate capture subprocess stdout/stderr in one
log per component. These append-only logs are mutable runtime data and must not
be written to `cursor-api/logs` inside the source checkout.

## Runtime contract

- new logs target:
  `%LOCALAPPDATA%/GicleeArt/GicleeApp/logs/components/<folder>.log`,
- both launch paths use the shared `giclee_app.launcher_logs` helper,
- normal resolution uses `giclee_app.app_paths.log_path`,
- reading is external-first and falls back to the historical
  `cursor-api/logs/<folder>.log` without creating directories,
- the first append copies existing legacy history once when no external log
  exists,
- the legacy file is never deleted, moved, truncated or otherwise modified,
- subsequent starts, subprocess output and exit markers append only externally,
- clearing a log targets the external path; when only legacy history exists it
  is seeded first and the external copy is then truncated,
- `_LOGS_DIR` remains an explicit override point in both launcher modules for
  tests and controlled callers,
- unsafe folder names that could escape the component-log directory are rejected.

## Shared helper

`giclee_app/launcher_logs.py` exposes separate read and write resolution:

- `component_log_read_path()` has no write side effects,
- `component_log_write_path()` prepares the external path and performs one-time
  legacy seeding.

This distinction keeps **Pokaż log** read-only while launches and **Wyczyść log**
operate on application-owned runtime data.

## Tests

`tests/test_launcher_logs_appdata.py` and `tests/test_launcher_delegate.py` verify:

1. external-first reads,
2. read-only legacy fallback,
3. one-time history seeding and append behavior,
4. explicit logs-directory overrides,
5. rejection of path traversal,
6. isolated delegate subprocess logging,
7. removal of launcher log findings from runtime-write inventory.
