# Studio performance log outside the checkout

`giclee_app/studio/perf.py` writes optional JSONL diagnostics only when
`GICLEE_STUDIO_PERF=1`. The log is mutable runtime data and must not be written
inside the source checkout.

## Runtime contract

- new writes target:
  `%LOCALAPPDATA%/GicleeArt/GicleeApp/logs/giclee_app/studio_perf.log`,
- normal resolution uses `giclee_app.app_paths.log_path`,
- the historical `giclee_app/logs/studio_perf.log` file is copied once on the
  first external append when no external log exists,
- the legacy file is never deleted, moved or modified,
- subsequent events append only to the external JSONL log,
- `_LOG_PATH` remains an explicit override point for tests and controlled callers,
- disabled diagnostics create no directories or files,
- all path and write failures remain non-fatal to Studio.

The one-time seed preserves existing diagnostic history while keeping every new
runtime write outside the checkout.

## Tests

`tests/test_studio_perf.py` verifies:

1. opt-in enablement,
2. no side effects while diagnostics are disabled,
3. explicit `_LOG_PATH` override compatibility,
4. one-time legacy seeding and external append behavior,
5. Unicode JSONL payloads and elapsed-time spans,
6. non-fatal write failures,
7. removal of `giclee_app/studio/perf.py` from runtime-write findings.
