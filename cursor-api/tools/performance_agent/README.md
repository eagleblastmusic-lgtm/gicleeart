# Performance Agent

Performance Agent is a local diagnostic tool for GicleeApp Studio performance audits.

It is used before changing performance-sensitive Studio code. When the app feels slow, freezes, or section interactions stutter, generate a fresh report bundle first and analyze `report.md` / `summary.json` before proposing code changes.

## Canonical paths

Local workspace path:

`C:\Strona\pusty\cursor-api\tools\performance_agent`

GitHub repository path:

`tools/performance_agent`

Important: the GitHub repository `eagleblastmusic-lgtm/gicleeapp` is rooted at the local `cursor-api` folder. Do not prefix GitHub paths with `cursor-api/`.

Examples:

| Context | Correct | Incorrect |
|---------|---------|-----------|
| GitHub file path | `tools/performance_agent/README.md` | `cursor-api/tools/performance_agent/README.md` |
| Default perf log (in repo) | `giclee_app/logs/studio_perf.log` | `cursor-api/giclee_app/logs/studio_perf.log` |
| Report output (in repo) | `reports/performance/` | `cursor-api/reports/performance/` |

More detailed operator docs: [`docs/README.md`](docs/README.md).

## Entrypoint

Run from:

`C:\Strona\pusty\cursor-api`

Commands:

```powershell
python -m tools.performance_agent --parse-only
python -m tools.performance_agent --manual
python -m tools.performance_agent --run
python -m tools.performance_agent --latest
python -m tools.performance_agent --list-reports
python -m tools.performance_agent --list-reports 5
python -m tools.performance_agent --chatgpt-latest
python -m tools.performance_agent --chatgpt-latest --clip
python -m tools.performance_agent --health-latest
python -m tools.performance_agent --chatgpt-latest --health-gate
python -m tools.performance_agent --chatgpt-latest --clip --health-gate
python -m tools.performance_agent --prepare-chatgpt-latest
python -m tools.performance_agent --open-latest
python -m tools.performance_agent --doctor
python -m tools.performance_agent --analyze-latest
python -m tools.performance_agent --analyze-report reports/performance/<bundle>
python -m tools.performance_agent --compare-latest
python -m tools.performance_agent --compare-reports reports/performance/<old> reports/performance/<new>
python -m tools.performance_agent --hotspots-latest
python -m tools.performance_agent --timeline-latest
python -m tools.performance_agent --cursor-prompt-latest
python -m tools.performance_agent --copy-cursor-prompt-latest
python -m tools.performance_agent --history
python -m tools.performance_agent --trend-latest
python -m tools.performance_agent --baseline-candidate
python -m tools.performance_agent --coverage-latest
python -m tools.performance_agent --run-playbook
python -m tools.performance_agent --scenario-checklist
```

## Modes

- `--parse-only` — parse an existing Studio performance log and generate a report bundle.
- `--manual` / `--wizard` — run the manual scenario wizard and UX questionnaire.
- `--run` / `--launch` — launch Studio as a subprocess, run the wizard, then generate a report bundle.
- `--latest` — inspect the newest existing report bundle (read-only, PA-1D).
- `--list-reports [N]` — list the N newest report bundles (default 10, read-only, PA-1D).
- `--chatgpt-latest` — print the COPY FOR CHATGPT block from the newest report bundle (read-only, PA-1E).
- `--clip` — with `--chatgpt-latest`, copy that block to the Windows clipboard instead of printing it (read-only, PA-1F).
- `--health-gate` — with `--chatgpt-latest`, check bundle health before printing or copying (read-only, PA-1H).
- `--health-latest` — assess readiness of the newest report bundle for analysis (read-only, PA-1G).
- `--prepare-chatgpt-latest` — health-gated clipboard prep with operator-friendly output (read-only, PA-1I).
- `--open-latest` — open the newest report directory in Explorer (read-only, PA-1I).
- `--doctor` — show read-only tool status and recommended workflow (read-only, PA-1I).
- `--analyze-latest` — local diagnostic analysis of the newest report bundle (read-only, PA-2A).
- `--analyze-report PATH` — local diagnostic analysis of a specific bundle (read-only, PA-2A).
- `--compare-latest` — compare the two newest report bundles (read-only, PA-2A).
- `--compare-reports OLD NEW` — compare two bundles by path (read-only, PA-2A).
- `--hotspots-latest` — show slow-event hotspots from the newest bundle (read-only, PA-2B).
- `--hotspots-report PATH` — show slow-event hotspots for a specific bundle (read-only, PA-2B).
- `--timeline-latest` — show scenario timeline insights from the newest bundle (read-only, PA-2B).
- `--timeline-report PATH` — show scenario timeline insights for a specific bundle (read-only, PA-2B).
- `--cursor-prompt-latest` — print a health-aware Cursor review prompt (read-only, PA-2B).
- `--cursor-prompt-report PATH` — print a Cursor review prompt for a specific bundle (read-only, PA-2B).
- `--copy-cursor-prompt-latest` — copy the Cursor review prompt to clipboard (read-only, PA-2B).
- `--history [N]` — table of N newest bundles with health and coverage (default: 10, PA-2C).
- `--trend-latest [N]` — metric trend across N newest bundles (default: 10, PA-2C).
- `--baseline-candidate` — show best baseline bundle for comparison (read-only, PA-2C).
- `--compare-baseline-latest` — compare baseline candidate vs newest bundle (read-only, PA-2C).
- `--copy-analysis-prompt-latest` — copy wide Cursor analysis prompt with history/trend/baseline (PA-2C).
- `--coverage-latest` — show coverage recovery diagnosis for the newest bundle (read-only, PA-3A).
- `--coverage-report PATH` — show coverage recovery diagnosis for a specific bundle (read-only, PA-3A).
- `--scenario-checklist` — show scenario checklist for a full guided run (read-only, PA-3A).
- `--run-playbook` — show full-run operator playbook (read-only, PA-3A).
- `--coverage-prompt-latest` — print Cursor prompt for coverage/instrumentation recovery (read-only, PA-3A).
- `--copy-coverage-prompt-latest` — copy coverage recovery Cursor prompt to clipboard (read-only, PA-3A).

## Local report analysis (PA-2A)

Read-only local diagnosis and comparison — no Studio launch, no new report, no changes to `reports/performance/**`.

```powershell
python -m tools.performance_agent --analyze-latest
python -m tools.performance_agent --analyze-report reports/performance/20260707-165000_giclee_studio
python -m tools.performance_agent --compare-latest
python -m tools.performance_agent --compare-reports reports/performance/old reports/performance/new
```

`--analyze-latest` / `--analyze-report` print bundle health, data-quality notes, top signals (slow events, UX suspects, conflicts), likely interpretation, and a recommended next CLI step.

Analysis statuses:

| Status | Meaning |
|--------|---------|
| `OK_FOR_REVIEW` | Health `READY` — enough data for review |
| `PARTIAL_REVIEW` | Health `PARTIAL` — narrow conclusions only |
| `NEEDS_RERUN_FIRST` | Health `NEEDS_RERUN` — repeat `--run` first |
| `BROKEN_BUNDLE` | Health `BROKEN` — missing key files |

`--compare-latest` compares `dirs[1]` (old) vs `dirs[0]` (new) from the report index. Comparison results:

| Result | Meaning |
|--------|---------|
| `IMPROVED` | Both READY/PARTIAL; slow events and suspects decreased |
| `REGRESSED` | Both READY/PARTIAL; slow events and suspects increased |
| `MIXED` | Conflicting metric direction |
| `NO_MEANINGFUL_CHANGE` | Small metric deltas |
| `REGRESSED_DATA_QUALITY` | Newer health worse, or fewer completed scenarios; light caveat when 9/9→9/9 with one log-window issue |
| `NOT_COMPARABLE` | Missing summary data or non-comparable health |

`--analyze-report` and `--compare-reports` accept a bundle directory or a file inside the bundle (`summary.json`, `report.md`). Missing paths return exit `1` with a clear error (no traceback).

## Deep report insights and Cursor prompt export (PA-2B)

Read-only deep insights from existing bundles — no Studio launch, no new report, no changes to `reports/performance/**`. PA-2B prepares diagnosis and a Cursor prompt; implementation is a separate user decision.

```powershell
python -m tools.performance_agent --hotspots-latest
python -m tools.performance_agent --hotspots-report reports/performance/20260707-165000_giclee_studio
python -m tools.performance_agent --timeline-latest
python -m tools.performance_agent --timeline-report reports/performance/20260707-165000_giclee_studio
python -m tools.performance_agent --cursor-prompt-latest
python -m tools.performance_agent --cursor-prompt-report reports/performance/20260707-165000_giclee_studio
python -m tools.performance_agent --copy-cursor-prompt-latest
```

### Hotspots (`--hotspots-latest` / `--hotspots-report`)

Reads `slow_events.csv` and `summary.json` to show top slow events, severities, modules/stages, and the 10 slowest rows. If `slow_events.csv` is missing, output states that clearly (no crash); `slow_event_count` from `summary.json` is shown as a fallback when available.

### Timeline (`--timeline-latest` / `--timeline-report`)

Reads `scenario_timeline.csv` and `questions_answers.json` / `summary.json` for completed/skipped counts, coverage status, longest scenarios, and weakest scenarios (`missing_expected_events`, `no_events_in_window`, `skipped`).

### Cursor prompt (`--cursor-prompt-latest` / `--cursor-prompt-report` / `--copy-cursor-prompt-latest`)

Health-aware prompt for Cursor review:

| Health | Prompt behavior |
|--------|-----------------|
| `READY` | Code review and P0 fix proposals allowed — no implementation without user approval |
| `PARTIAL` | Data quality and instrumentation only — no broad Studio optimization |
| `NEEDS_RERUN` / `BROKEN` | Audit repair first — no performance code analysis |

All variants include guardrails: no Studio code changes, no GICLÉE FRAME runtime changes, no `Komponenty/*` edits, no commit/push.

`--copy-cursor-prompt-latest` uses the existing clipboard helper; stdout shows a short confirmation message.

PATH validation matches PA-2A: bundle directory or `summary.json` / `report.md`. No reports for `*-latest` → friendly message, exit `0`. Invalid path → stderr + exit `1`.

## Performance history, trend and baseline (PA-2C)

Read-only analysis across multiple existing bundles — no Studio launch, no new report, no baseline saved to disk. **Data quality first:** lower `slow_events` or `suspects` in a bundle with weaker scenario coverage does **not** mean performance improved.

```powershell
python -m tools.performance_agent --history
python -m tools.performance_agent --history 10
python -m tools.performance_agent --trend-latest
python -m tools.performance_agent --trend-latest 10
python -m tools.performance_agent --baseline-candidate
python -m tools.performance_agent --compare-baseline-latest
python -m tools.performance_agent --copy-analysis-prompt-latest
```

### `--history [N]`

Markdown table of the N newest bundles (default 10, min 1, max 50): health, mode, events, slow, suspects, completed/skipped. Invalid N → exit `1`.

### `--trend-latest [N]`

Metric sequences (chronological): `total_events`, `slow_events`, `suspects`, `completed`. If the latest bundle has weaker coverage than a recent good run, interpretation warns not to treat lower metrics as improvement and recommends a full `--run`.

### `--baseline-candidate`

Selects the newest suitable baseline: prefer `READY`; else `PARTIAL` with at least 7/9 scenario coverage. `NEEDS_RERUN` and `BROKEN` are never baseline.

### `--compare-baseline-latest`

Compares baseline candidate (old) vs newest bundle (new) using PA-2A `compare_report_bundles()`. Same bundle → friendly message. Major coverage regression → `REGRESSED_DATA_QUALITY` (not comparable). Light caveat (9/9 with one `no_events_in_window`) → `REGRESSED_DATA_QUALITY` with comparable-with-caution wording.

### `--copy-analysis-prompt-latest`

Wide Cursor prompt: latest analysis, hotspots, timeline, history, trend, baseline candidate/comparison, data-quality-first warning, guardrails (no Studio, no GICLÉE FRAME runtime, no `Komponenty/*`, no commit/push). Uses clipboard helper; stdout confirmation only.

Tests: `tests/test_performance_agent_report_history.py`

## Data quality semantics fixes (PA-3B)

Read-only semantics fixes — no Studio launch, no runtime changes. Central helpers: `tools/performance_agent/report/semantics.py`.

| Evidence tier | Meaning |
|---------------|---------|
| **1/9 completed** | Weak evidence — strong warning; not performance proof |
| **9/9 + 1 `no_events_in_window`** | Reviewable with caveat — not the same alarm level as 1/9 |
| **9/9 all ok** | READY — sufficient for full review |

Rules:
- Never write `only 9/9` when all scenarios completed.
- `REGRESSED_DATA_QUALITY` distinguishes **major** (e.g. 9/9→1/9) vs **light** (9/9→9/9 with one caveat).
- Lower `slow_events` / `suspects` with weaker coverage ≠ improvement.
- `slow_events.csv` uses duration fields only (`elapsed_ms`, `since_click_ms`, `since_request_ms`, `since_details_cta_ms`, `queue_latency_ms`). `since_enter_ms` excluded (view age, not click latency); hotspots filter legacy CSV rows too. Old bundles may still contain legacy `since_click_ms` / `cancelled` rows — expected, not a tool regression.
- `dashboard_cold` → `early_event_seen` when dashboard events appear before scenario window (visible after next `--run`).
- **9/9 + `early_event_seen`** = reviewable / READY with caveat — not the same alarm as 1/9.

Tests: `tests/test_performance_agent_report_analyzer.py`, `tests/test_performance_agent_scenario_coverage.py`, `tests/test_performance_agent_log_parser.py`

## Coverage recovery and full-run guidance (PA-3A)

Read-only diagnostics and operator guidance — no Studio launch, no new report, no runtime changes. PA-3A helps recover full scenario coverage and understand why runs end `PARTIAL` / skipped. **1/9 coverage is not performance evidence.**

```powershell
python -m tools.performance_agent --run-playbook
python -m tools.performance_agent --run
python -m tools.performance_agent --health-latest
python -m tools.performance_agent --coverage-latest
python -m tools.performance_agent --coverage-report reports/performance/20260707-165000_giclee_studio
python -m tools.performance_agent --scenario-checklist
python -m tools.performance_agent --coverage-prompt-latest
python -m tools.performance_agent --copy-coverage-prompt-latest
```

### `--coverage-latest` / `--coverage-report`

Coverage recovery diagnosis: health, completed/skipped, coverage status (`GOOD_COVERAGE`, `WEAK_COVERAGE_LIGHT`, `WEAK_COVERAGE`, `NO_EVENTS`, `BROKEN_COVERAGE`), weak scenarios, likely causes, recovery checklist. Reuses PA-2B `build_timeline_summary()` — no duplicated timeline logic.

### `--scenario-checklist`

Lists all 9 `giclee_studio` scenarios with goal, operator action, and coverage risk (from profile + local mapping in `coverage.py`).

### `--run-playbook`

Before/during/after instructions for a full guided run and quality target (≥7/9 completed).

### `--coverage-prompt-latest` / `--copy-coverage-prompt-latest`

Cursor prompt for coverage/instrumentation recovery only — not Studio performance optimization. Explains skipped / `no_events_in_window`, proposes coverage improvement plan, no implementation without approval. Guardrails: no Studio, no GICLÉE FRAME runtime, no `Komponenty/*`, no commit/push.

Tests: `tests/test_performance_agent_report_coverage.py`

## Clipboard helper (PA-1F)

Read-only: copy the **COPY FOR CHATGPT** block from the newest bundle to the Windows clipboard — no Studio launch, no new report.

```powershell
python -m tools.performance_agent --chatgpt-latest
python -m tools.performance_agent --chatgpt-latest --clip
```

Without `--clip`, stdout is the paste-ready block only (same as PA-1E). With `--clip`, the block is copied via PowerShell `Set-Clipboard` (stdin, UTF-8) and stdout shows only:

`COPY FOR CHATGPT block copied to clipboard.`

`--clip` without `--chatgpt-latest` is an error.

## Bundle health gate (PA-1G)

Read-only: assess whether the newest report bundle is ready for ChatGPT analysis — no Studio launch, no new report.

```powershell
python -m tools.performance_agent --health-latest
```

Returns a status (`READY`, `PARTIAL`, `NEEDS_RERUN`, or `BROKEN`), bundle metrics, file presence, scenario completion counts, and an operator recommendation.

## Health gate for ChatGPT copy (PA-1H)

Read-only: optionally block printing or clipboard copy when the newest bundle is not safe to paste into ChatGPT — no Studio launch, no new report.

```powershell
python -m tools.performance_agent --chatgpt-latest --health-gate
python -m tools.performance_agent --chatgpt-latest --clip --health-gate
```

Behavior:

| Status | `--chatgpt-latest --health-gate` | Exit |
|--------|----------------------------------|------|
| `READY` | Prints/copies block normally; stderr: `Health gate: READY` | 0 |
| `PARTIAL` | Prints/copies block; stderr warning about weak coverage | 0 |
| `NEEDS_RERUN` | No block output; health summary on stderr | 2 |
| `BROKEN` | No block output; health summary on stderr | 2 |

Without `--health-gate`, `--chatgpt-latest` and `--chatgpt-latest --clip` behave exactly as before (PA-1E/PA-1F).

`--health-gate` without `--chatgpt-latest` returns an error.

## Operator convenience (PA-1I)

Read-only shortcuts for daily operator work — no Studio launch, no new report.

### `--prepare-chatgpt-latest`

Convenient alias for `--chatgpt-latest --clip --health-gate` with clearer stdout:

```powershell
python -m tools.performance_agent --prepare-chatgpt-latest
```

| Status | Behavior | Exit |
|--------|----------|------|
| `READY` | Copies block; operator prep message on stdout | 0 |
| `PARTIAL` | Copies block; warning + prep message on stdout | 0 |
| `NEEDS_RERUN` / `BROKEN` | No copy; health summary on stderr | 2 |
| Clipboard error | Clear error on stderr | 1 |

### `--open-latest`

Opens the newest report bundle directory in Windows Explorer and prints paths to `report.md` and `summary.json`:

```powershell
python -m tools.performance_agent --open-latest
```

On non-Windows platforms, paths are printed and a clear message explains that Explorer open is Windows-only.

### `--doctor`

Quick read-only status: version, profile, output root, bundle count, latest health, default log presence, clipboard support, and recommended workflow:

```powershell
python -m tools.performance_agent --doctor
```

## Default profile

`giclee_studio`

## Default log

`giclee_app/logs/studio_perf.log`

## Default output

`reports/performance`

Each generated bundle lives under `reports/performance/<YYYYMMDD-HHMMSS>_giclee_studio/` and should include, depending on mode:

- `report.md`
- `summary.json`
- `agent_events.jsonl`
- `events.jsonl`
- `scenario_timeline.csv`
- `slow_events.csv`
- `questions_answers.json`
- `raw/studio_perf.log`

## Workflow rule

For performance symptoms such as:

- “dalej muli”
- “wolno się otwiera”
- “sekcje przycinają”
- slow GICLÉE FRAME section clicks
- slow details / media loading

do not guess from symptoms alone.

First generate or inspect a Performance Agent bundle from `reports/performance/**`, then review `report.md` and `summary.json`, and only then plan code changes.

`SCENARIO_LOG_NOT_CONFIRMED` and coverage statuses such as `missing_expected_events` describe session/log data quality — not automatically a runtime regression.

## Checkpoint status (PA/GF — 2026-07-08)

**Done locally:** PA-1I, PA-2A, PA-2B, PA-2C, PA-3A, PA-3B. **GF-P0.1** (details CTA timing instrumentation) done in code; fresh `--run` validation **pending**. Tests: **162 passed**.

Project checkpoint details: `Pliki startowe dla GPT/CURRENT_APP_STATE.md` § Performance Agent + GF-P0.1.

## Operator quick reference (read-only)

Preferred session flow:

```text
--doctor → --coverage-latest / --analyze-latest → --hotspots-latest / --timeline-latest → --cursor-prompt-latest
```

Key commands: `--doctor`, `--prepare-chatgpt-latest`, `--analyze-latest`, `--compare-latest`, `--hotspots-latest`, `--timeline-latest`, `--cursor-prompt-latest`, `--history`, `--trend-latest`, `--baseline-candidate`, `--coverage-latest`, `--run-playbook`, `--scenario-checklist`.

Bundle generators (when a fresh run is needed): `--parse-only`, `--manual`, `--run`.

## GF-P0.1 — Details CTA timing (instrumentation)

Details CTA latency is anchored to request/CTA timing, not view age:

- Log/CSV fields: `since_request_ms`, `since_details_cta_ms`
- `since_enter_ms` is **not** click latency — excluded from slow-event ranking (PA-3B)
- Old bundles (e.g. `20260707-214246_giclee_studio`) may still show legacy `slow_events.csv` rows — `--hotspots-latest` on old data is expected
- Full GF-P0.1 proof requires a **fresh `--run`** (deferred by operator choice)

## Baseline bundles (manual guidance)

| Bundle | Use as GF baseline? |
|--------|---------------------|
| `20260707-214246_giclee_studio` | **Yes** — first sensible GF baseline |
| `20260707-160215_giclee_studio` | **No** — did not measure `studio.gicleeframe.*` |

Automatic selection: `--baseline-candidate`. Manual compare: `--compare-reports`.
