# Stage 2 CI Runbook

## Purpose

Stage 2 moves GicleeApp validation from ad-hoc local runs toward reproducible, hermetic GitHub Actions jobs while preserving strict repository-safety and data-safety boundaries.

The current workflow is:

```text
.github/workflows/stage2-ci-baseline.yml
```

## Current CI jobs

### Hermetic smoke

The blocking smoke job runs on Windows with Python 3.13 and validates deterministic contracts that do not create a real Tk root:

- repository-safety tracked-cleanup rules;
- Studio category defaults and overrides;
- PyInstaller resource packaging;
- import-safe Resend diagnostics;
- external AppData store isolation;
- TytułyAI storage round-trips;
- Component Hub filtering without GUI.

It must remain green before a Stage 2 PR can be considered merge-ready. Do not add tests that instantiate `tkinter.Tk`, `customtkinter.CTk` or the full Studio application to this blocking job.

### Tk GUI smoke

The Tk GUI job is diagnostic and non-blocking while the hosted Windows/Python 3.13 Tcl/Tk environment is unstable.

It performs an explicit Tk-root capability probe, records Tcl/Tk details, and then runs selected Component Hub, inline lifecycle and Giclée Frame GUI tests. Probe output, JUnit and pytest logs are uploaded even when the environment fails.

A red Tk diagnostic must be classified as one of:

- runner Tcl/Tk installation failure;
- deterministic test-contract failure;
- product regression.

Do not change production code to hide a broken Tcl/Tk runner.

### Full pytest baseline

The full-suite job is temporarily diagnostic and non-blocking while known Stage 2 failure clusters are repaired.

It still records the real pytest exit code and uploads evidence. Do not change tests or repository-safety baselines merely to make this diagnostic job appear green.

When the remaining clusters are resolved or intentionally separated into explicit environmental jobs, this job must become blocking.

## Runtime isolation contract

Every CI job and every local reproduction must isolate at least:

```text
LOCALAPPDATA
APPDATA
GICLEEAPP_LOCAL_ROOT
GICLEEAPP_ROAMING_ROOT
PYTHONPYCACHEPREFIX
```

The Stage 2 workflow also isolates:

```text
GPT_STARTER_DIR
THEME_ROOT
TEMP
TMP
```

Tests must not read or write the user's real AppData, starter files, theme checkout or mutable repository runtime files.

## External integration contract

Automated tests must not use:

- real GitHub repositories;
- real Shopify stores or credentials;
- production APIs;
- user-owned mutable data;
- the archived checkout at `C:\Strona\pusty`.

Tests requiring Git behavior must use temporary local repositories. Shopify-related tests must use fixtures, stubs or temporary theme roots.

## Local blocking-smoke reproduction

From `cursor-api` in an isolated environment:

```powershell
python -m pip install -r requirements-dev.txt
python -m pip check

python -m pytest -q `
  tests/test_repository_safety_tracked_cleanup.py `
  tests/test_studio_categories.py `
  tests/test_giclee_app_packaging.py `
  tests/test_resend_diagnostic_script.py `
  tests/test_stage1e_external_stores_3.py::test_title_drafts_write_external `
  tests/test_stage1e_external_stores_3.py::test_launcher_config_reads_legacy_and_writes_roaming `
  tests/test_tytulyai_storage.py `
  tests/test_studio_component_hub.py::test_filtered_components_without_gui
```

Do not run this command against unisolated environment variables.

## Local Tk GUI reproduction

First verify that Tk can create and destroy a root:

```powershell
python -c "import tkinter as tk; root=tk.Tk(); root.withdraw(); print(root.tk.call('info','patchlevel')); print(root.tk.globalgetvar('tcl_library')); root.destroy()"
```

Only after the probe succeeds, run the selected GUI set:

```powershell
python -m pytest -q `
  tests/test_studio_component_hub.py::test_pin_toggle_does_not_rebuild_card_cache `
  tests/test_studio_component_hub.py::test_hub_search_during_partial_render `
  tests/test_studio_launcher_inline.py::test_return_from_inline_restores_hub_tiles `
  tests/test_studio_launcher_inline.py::test_return_from_inline_with_inline_resize_restores_hub `
  tests/test_studio_gicleeframe_visual_ready.py::test_gicleeframe_section_reentry_uses_minimal_cache
```

A failed capability probe is an environment result, not permission to weaken product behavior or blanket-skip all GUI tests.

## Local full baseline reproduction

From `cursor-api`, after setting isolated runtime roots:

```powershell
python -m pytest -q --junitxml="<report-root>\junit.xml"
```

Capture the complete terminal output and pytest exit code. After the run, verify every participating worktree using:

```powershell
git status --porcelain=v1 --untracked-files=all
```

Any unexpected modification is a blocker.

## Artifacts

GitHub Actions uploads:

- a blocking-smoke artifact with JUnit and complete pytest output;
- a Tk GUI diagnostic artifact with capability-probe output, JUnit when available and complete pytest output;
- a full-baseline artifact with JUnit and complete pytest output.

Artifacts are evidence for the exact workflow run and must be reviewed before changing a failing contract.

## GUI and Tcl/Tk strategy

GUI/Tk tests require an explicit environment contract.

Do not modify production code to hide a broken Tcl/Tk installation. The dedicated diagnostic job must perform a Tk-root capability check before executing GUI tests.

A skip is permitted only when a specific test has a documented platform contract and the environment check records the reason. Do not apply a blanket GUI skip.

The blocking hermetic smoke must remain independent of Tcl/Tk root creation.

## Async UI testing strategy

Production async behavior must not be changed back to synchronous execution to satisfy old tests.

Tests should use a deterministic fake scheduler or executor that can drain queued `after`, `after_idle` and deferred callbacks without `sleep`.

Prefer behavioral assertions after the queue is drained. Avoid source-text assertions when the behavior can be observed directly.

## Repository-safety rules

- Never weaken a safety test to accept a new blocker.
- Mutable runtime configuration must not be tracked.
- Immutable defaults belong in resources or examples.
- Every bundled resource must be included in package/build configuration.
- Every commit and PR must use a strict path allowlist.
- Do not use `git reset --hard`, `git clean`, force push, rebase or history rewriting.
- Do not delete local branches or worktrees during Stage 2.
- Do not update `CURRENT_APP_STATE.md` until the final accepted Stage 2 checkpoint.

## PR procedure

1. Start from the exact current `master` SHA.
2. Create a dedicated `gpt-work/<task-slug>` branch.
3. Keep changes within the declared allowlist.
4. Push and open a draft PR.
5. Review the full diff and changed-file list.
6. Review GitHub Actions jobs and artifacts.
7. Fix architecture rather than weakening tests.
8. Confirm `master` has not moved unexpectedly.
9. Mark ready and merge with the expected head SHA.
10. Preserve the local branch and worktree until the final safety checkpoint.

## Stacked PR procedure

Use stacked PRs only when a later package genuinely depends on an unmerged earlier package.

Each stacked PR must state:

- exact base branch and base SHA;
- exact head branch and head SHA;
- dependency on the earlier PR;
- its own path allowlist and validation evidence.

Do not retarget or merge a stack automatically after an unexpected `master` change.

## Failure procedure

For every failed job:

1. identify whether the failure is code, test contract or environment;
2. inspect JUnit and complete logs;
3. reproduce with the same isolated variables;
4. verify worktree cleanliness after reproduction;
5. fix the smallest coherent architectural package;
6. rerun focused tests and the relevant CI job;
7. record intentionally deferred failures explicitly.

## Starter files and GPT knowledge

Do not update starter files after each small PR.

After Stage 2 is stabilized, update the starter files in one final documentation package. `CURRENT_APP_STATE.md` remains single-writer and must be updated last.

Do not generate a GPT knowledge ZIP without separate explicit authorization. The ZIP is not the source of truth.
