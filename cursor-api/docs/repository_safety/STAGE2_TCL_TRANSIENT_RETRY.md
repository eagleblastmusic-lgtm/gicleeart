# Stage 2 Tcl/Tk runtime integrity

## Current decision

Stage 2 does not retry `Tk.__init__` on a partially initialized object. The compatibility helpers in `tools/stage2_tcl_retry.py` delegate exactly once.

The environment boundary is instead a complete, immutable-for-the-job Tcl/Tk mirror under `RUNNER_TEMP`.

## Why direct toolcache is insufficient

On 2026-07-15 two consecutive full baselines on the same LC-3C head passed 2436 tests and then failed because different files disappeared from the direct `actions/setup-python` tree:

- `tk8.6/icons.tcl`;
- `tk8.6/ttk/classicTheme.tcl`.

Both runs had already passed Tcl/Tk preflight, warmup and a separate Tk GUI job. This proves that checking a small fixed list once is not enough for a long full-suite process.

## Per-run mirror

`.github/scripts/prepare-tk-runtime.ps1` copies only:

```text
<python-root>/tcl/**
```

into a unique target identified by runtime name, run id, attempt and job. It does not copy Python, `Lib`, site-packages or repository files.

After copying, it compares every file using:

- relative path;
- byte length;
- SHA-256.

The manifest is persisted outside the mirror. `TCL_LIBRARY` and `TK_LIBRARY` point only into the mirror.

## Required runtime files

The contract explicitly includes:

- `init.tcl`;
- `tk.tcl`;
- `icons.tcl`;
- `spinbox.tcl`;
- `ttk/ttk.tcl`;
- `ttk/defaults.tcl`;
- `ttk/classicTheme.tcl`;
- `ttk/winTheme.tcl`.

The full manifest covers all additional files as well.

## Preflight and verify-only

Preparation creates a real Tk root, Spinbox and ttk Style and verifies that Tcl and Tk resolve to the mirror.

After the full-baseline warmup, the workflow calls:

```powershell
prepare-tk-runtime.ps1 -VerifyOnly
```

This mode does not copy again. It validates the persisted manifest, required files and a new independent Tk root immediately before the complete pytest collection.

## Failure interpretation

- Preparation or manifest failure: infrastructure blocker before tests.
- Verify-only failure: mirror integrity blocker before full pytest.
- Tk GUI or full pytest assertion failure: inspect artifact and classify normally.
- No blanket skips and no production changes are allowed to hide an environment failure.

A second full-baseline failure on an unchanged head blocks merge and requires a separate fix rather than another blind rerun.
