# Stage 2 CI Runbook

## Purpose

Stage 2 provides blocking, reproducible validation for GicleeApp while preserving repository-safety and data-safety boundaries.

Workflow:

```text
.github/workflows/stage2-ci-baseline.yml
```

## Blocking job sequence

### 1. Hermetic smoke

Runs on Windows 2022 with Python 3.13 and validates contracts that do not require a real Tk root, including repository safety, external AppData stores, packaging and the Tcl/Tk mirror contract.

This job must remain independent of `tkinter.Tk()` and `customtkinter.CTk()` creation.

### 2. Tk GUI smoke

Runs only for ready PRs or manual dispatch after Hermetic passes. It:

- creates a unique per-run mirror of the complete `actions/setup-python` Tcl/Tk tree under `RUNNER_TEMP`;
- validates a full relative-path/length/SHA-256 manifest;
- points `TCL_LIBRARY` and `TK_LIBRARY` to the mirror;
- performs a real Tk-root capability probe;
- executes selected Component Hub, inline lifecycle and Giclée Frame GUI tests;
- uploads probe, JUnit and pytest evidence.

A red Tk GUI job is blocking and must be classified as environment, test-contract or product failure. Do not change production behavior to hide a broken runtime.

### 3. Full pytest baseline

Runs on a separate Windows 2022 runner after Tk GUI passes. It:

1. prepares its own isolated application roots;
2. creates its own unique Tcl/Tk mirror;
3. installs dependencies;
4. runs the historical Tk warmup test;
5. executes `prepare-tk-runtime.ps1 -VerifyOnly` to revalidate every mirrored file and a fresh Tk/ttk preflight;
6. runs the complete pytest collection;
7. uploads JUnit, complete pytest output and runtime-write inventory on every outcome.

The full baseline is blocking. A PR is not merge-ready until the exact-head artifact reports zero failures and errors.

## Tcl/Tk mirror contract

The source is only:

```text
<actions/setup-python root>/tcl/**
```

The target is unique for `RuntimeName`, `GITHUB_RUN_ID`, `GITHUB_RUN_ATTEMPT` and `GITHUB_JOB`:

```text
${RUNNER_TEMP}/python-tcl-runtime-<identity>
```

Only the Tcl/Tk tree is copied. The interpreter, `Lib`, `site-packages` and repository files are not copied.

Preparation fails before tests when:

- required Tcl/Tk files are absent;
- `robocopy` fails;
- source and mirror differ by relative path, byte length or SHA-256;
- `TCL_LIBRARY` or `TK_LIBRARY` resolves outside the mirror;
- a real Tk root, Spinbox or ttk style cannot be created.

`-VerifyOnly` never recopies the source. It validates the persisted mirror manifest and creates a new independent Tk root immediately before the full baseline.

Do not retry `Tk.__init__` on a partially initialized object.

## Runtime isolation

Every job or local reproduction must isolate at least:

```text
LOCALAPPDATA
APPDATA
GICLEEAPP_LOCAL_ROOT
GICLEEAPP_ROAMING_ROOT
PYTHONPYCACHEPREFIX
GPT_STARTER_DIR
THEME_ROOT
TEMP
TMP
```

Tests must not access user AppData, mutable starter files, the production Shopify store or the archived checkout at `C:\Strona\pusty`.

## External integrations

Automated tests must use temporary repositories, fixtures and stubs. They must not use:

- production GitHub repositories as mutation targets;
- real Shopify credentials or stores;
- production APIs;
- user-owned mutable data.

## Local focused reproduction

From `cursor-api`:

```powershell
python -m pytest -q tests/test_tcl_transient_retry.py
```

For a local GUI reproduction, first verify a real root:

```powershell
python -c "import tkinter as tk; root=tk.Tk(); root.withdraw(); print(root.tk.call('info','patchlevel')); print(root.tk.globalgetvar('tcl_library')); print(root.tk.globalgetvar('tk_library')); root.destroy()"
```

Then run only the relevant focused GUI tests. A failed capability probe is an environment result, not permission for a blanket skip.

## Evidence requirements

Before merge, review artifacts for the exact head:

- Hermetic JUnit and pytest output;
- Tk GUI probe, JUnit and pytest output;
- full baseline JUnit and pytest output;
- runtime-write inventory.

Required final state:

- zero JUnit failures/errors;
- expected test count and skips explained;
- zero runtime-write parse errors;
- zero runtime source-write findings;
- PR `behind_by=0`;
- final diff within allowlist;
- no unresolved review threads.

## Failure procedure

For every failed job:

1. inspect JUnit and complete logs;
2. classify code, test contract or environment;
3. do not rerun blindly;
4. reproduce with the same isolated variables when possible;
5. fix the smallest coherent package;
6. rerun focused tests and the relevant CI sequence;
7. record deferred infrastructure failures explicitly.

At most one diagnostically justified repeat of a full baseline is allowed on the same unchanged head. A second failure blocks merge and requires a separate fix.

## Repository-safety rules

- Never weaken safety tests to accept a blocker.
- Mutable runtime configuration must not be tracked.
- Every change uses a strict path allowlist.
- Do not use force push, rebase, `git reset --hard` or `git clean`.
- Do not update starter files during small Stage 2 packages.
- Do not generate a GPT knowledge ZIP without separate explicit authorization.

## PR procedure

1. Start from exact current `master`.
2. Use a dedicated `gpt-work/<task>` branch.
3. Freeze scope and allowlist.
4. Open a draft PR.
5. Pass focused tests and draft Hermetic.
6. Review the complete diff.
7. Mark ready to run Tk GUI and full baseline.
8. Review artifacts and inventory.
9. Reverify exact head, `behind_by=0` and review threads.
10. Merge only with the expected head SHA.
