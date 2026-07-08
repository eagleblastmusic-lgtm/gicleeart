# Performance Agent

Audit tooling for `giclee_app/logs/studio_perf.log`.

## Modes

### Parse-only (PA-1A)

```powershell
cd C:\Strona\pusty\cursor-api
python -m tools.performance_agent --parse-only
python -m tools.performance_agent --parse-only --log giclee_app/logs/studio_perf.log
```

### Manual wizard (PA-1B)

Start Studio yourself, then run wizard:

```powershell
$env:GICLEE_STUDIO_PERF = "1"
$env:GICLEE_STUDIO_IDLE_PREWARM = "0"
python -m giclee_app.studio_preview

python -m tools.performance_agent --manual
python -m tools.performance_agent --wizard
```

### Full run — Studio + wizard (PA-1C)

One command: log lifecycle → launch Studio → wizard → optional shutdown → report.

```powershell
python -m tools.performance_agent --run
python -m tools.performance_agent --launch
```

Log lifecycle prompt (default `clear`):
- **clear** — archive old log to `reports/performance/_archive/`, then remove (recommended)
- **keep** — leave existing log
- **copy_only** — archive copy, keep original

After wizard: choose whether to close Studio. Shutdown uses `terminate()` then waits 5s; `kill()` only if you confirm.

If Studio fails to start or exits immediately, a **partial report** is still generated (UX + warnings).

## Latest / report index (PA-1D)

Read-only inspection of existing bundles under `reports/performance/**` — no Studio launch, no new report.

```powershell
python -m tools.performance_agent --latest
python -m tools.performance_agent --list-reports
python -m tools.performance_agent --list-reports 5
```

`--latest` prints operator summary (mode, counts, conflict totals, bundle file presence, paths to `report.md` / `summary.json`) and reminds you to paste the **COPY FOR CHATGPT** block from `report.md`.

`--list-reports` shows a compact list of recent bundles (name, mode, slow/suspect counts, key file flags).

## ChatGPT copy extractor (PA-1E)

Read-only: print only the **COPY FOR CHATGPT** block from the newest bundle — no Studio launch, no new report, no banners.

```powershell
python -m tools.performance_agent --chatgpt-latest
```

Stdout is paste-ready for ChatGPT (Performance Analyst mode): heading + copy sections, without the trailing `---` separator or the technical report below it.

If the technical section marker is missing, the extractor falls back to the end of `report.md` and still strips a trailing `---` when present.

## Clipboard helper (PA-1F)

Read-only: copy the **COPY FOR CHATGPT** block from the newest bundle to the Windows clipboard — no Studio launch, no new report.

```powershell
python -m tools.performance_agent --chatgpt-latest
python -m tools.performance_agent --chatgpt-latest --clip
```

Without `--clip`, stdout is the paste-ready block only (PA-1E). With `--clip`, PowerShell `Set-Clipboard` receives the block via stdin (UTF-8 safe for `→`, `—`, Polish characters, emoji). Stdout shows only:

`COPY FOR CHATGPT block copied to clipboard.`

`--clip` without `--chatgpt-latest` returns a clear error.

## Bundle health gate (PA-1G)

Read-only: assess whether the newest report bundle is ready for ChatGPT analysis — no Studio launch, no new report.

```powershell
python -m tools.performance_agent --health-latest
```

Statuses:

| Status | Meaning |
|--------|---------|
| `READY` | Bundle looks good for ChatGPT analysis |
| `PARTIAL` | Usable, but weak scenario coverage or warnings |
| `NEEDS_RERUN` | Too few events or scenarios — repeat `--run` |
| `BROKEN` | Missing `report.md` or `summary.json` |

Output includes metrics, file presence, completed/skipped scenario counts, and a recommendation with the next command to run.

## Health gate for ChatGPT copy (PA-1H)

Read-only: optionally block printing or clipboard copy when the newest bundle is not safe to paste into ChatGPT — no Studio launch, no new report.

```powershell
python -m tools.performance_agent --chatgpt-latest --health-gate
python -m tools.performance_agent --chatgpt-latest --clip --health-gate
```

| Status | Behavior | Exit |
|--------|----------|------|
| `READY` | Block printed or copied; stderr: `Health gate: READY` | 0 |
| `PARTIAL` | Block printed or copied; stderr warning about weak scenario coverage | 0 |
| `NEEDS_RERUN` | No block; full health summary on stderr | 2 |
| `BROKEN` | No block; full health summary on stderr | 2 |

Without `--health-gate`, `--chatgpt-latest` and `--clip` are unchanged (PA-1E/PA-1F). `--health-gate` alone (without `--chatgpt-latest`) is an error.

## Operator convenience (PA-1I)

Read-only shortcuts — no Studio launch, no new report.

```powershell
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

### `--prepare-chatgpt-latest`

Health-gated clipboard prep (equivalent to `--chatgpt-latest --clip --health-gate`) with operator-friendly stdout. Exit `0` for `READY`/`PARTIAL`, `2` for `NEEDS_RERUN`/`BROKEN`, `1` on clipboard errors.

### `--open-latest`

Prints paths to the newest bundle and opens its directory in Windows Explorer via `os.startfile`. Non-Windows: paths only, no traceback.

### `--doctor`

Version, profile, output root, bundle count, latest health, default log presence, clipboard support, and a three-step recommended workflow.

## Local report analysis (PA-2A)

Read-only local diagnosis and comparison — no Studio launch, no new report.

```powershell
python -m tools.performance_agent --analyze-latest
python -m tools.performance_agent --analyze-report reports/performance/20260707-165000_giclee_studio
python -m tools.performance_agent --compare-latest
python -m tools.performance_agent --compare-reports reports/performance/old reports/performance/new
```

### `--analyze-latest` / `--analyze-report`

Prints bundle name, health, analysis status, data-quality bullets, top signals, interpretation, and recommended next action. Accepts a bundle directory or `summary.json` / `report.md` inside the bundle.

| Analysis status | Health basis |
|-----------------|--------------|
| `OK_FOR_REVIEW` | `READY` |
| `PARTIAL_REVIEW` | `PARTIAL` |
| `NEEDS_RERUN_FIRST` | `NEEDS_RERUN` |
| `BROKEN_BUNDLE` | `BROKEN` |

### `--compare-latest` / `--compare-reports`

Compares old vs new bundles. `--compare-latest` uses index order: old = second newest, new = newest.

| Result | Rule (simplified) |
|--------|-------------------|
| `REGRESSED_DATA_QUALITY` | Major: newer health worse or fewer completed scenarios. Light: same 9/9 with one log-window caveat |
| `IMPROVED` | Both READY/PARTIAL; slow + suspects down |
| `REGRESSED` | Both READY/PARTIAL; slow + suspects up |
| `NO_MEANINGFUL_CHANGE` | Small deltas |
| `MIXED` | Conflicting signals |
| `NOT_COMPARABLE` | Missing summary or non-comparable state |

Missing paths: exit `1`, clear stderr message. Fewer than two bundles for `--compare-latest`: friendly stdout message, exit `0`.

## Deep report insights and Cursor prompt export (PA-2B)

Read-only — no Studio, no new report, no mutation of `reports/performance/**`. PA-2B does not implement fixes; it prepares diagnosis and a Cursor prompt. Implementation is a separate user step.

```powershell
python -m tools.performance_agent --hotspots-latest
python -m tools.performance_agent --hotspots-report reports/performance/20260707-165000_giclee_studio
python -m tools.performance_agent --timeline-latest
python -m tools.performance_agent --timeline-report reports/performance/20260707-165000_giclee_studio
python -m tools.performance_agent --cursor-prompt-latest
python -m tools.performance_agent --cursor-prompt-report reports/performance/20260707-165000_giclee_studio
python -m tools.performance_agent --copy-cursor-prompt-latest
```

### `--hotspots-latest` / `--hotspots-report`

Output: bundle name, health, slow-event totals, top events by count, severities, modules/stages (when present), top 10 slowest rows, interpretation. Missing `slow_events.csv` → clear message, no traceback; `summary.json` count shown as fallback.

### `--timeline-latest` / `--timeline-report`

Output: completed/skipped/total, coverage status counts, longest scenarios, weakest scenarios, interpretation. CSV booleans parsed explicitly (`true`/`false`/`1`/`0`/`yes`/`no`).

### `--cursor-prompt-latest` / `--cursor-prompt-report` / `--copy-cursor-prompt-latest`

Generates a health-aware Cursor prompt from bundle health, hotspots, timeline, and optional comparison (when two bundles exist for `*-latest`). Guardrails always present. `--copy-cursor-prompt-latest` uses `copy_text_to_clipboard()`.

Tests: `tests/test_performance_agent_report_insights.py`

## Performance history, trend and baseline (PA-2C)

Read-only — no Studio, no new report, no baseline on disk. **Data quality before performance conclusions:** lower slow/suspects with weaker coverage ≠ improvement.

```powershell
python -m tools.performance_agent --history
python -m tools.performance_agent --trend-latest 10
python -m tools.performance_agent --baseline-candidate
python -m tools.performance_agent --compare-baseline-latest
python -m tools.performance_agent --copy-analysis-prompt-latest
```

| Command | Output |
|---------|--------|
| `--history [N]` | Table: health, metrics, completed/skipped (N default 10, max 50) |
| `--trend-latest [N]` | Chronological metric arrows + interpretation |
| `--baseline-candidate` | Newest READY, or PARTIAL ≥7/9; rejects NEEDS_RERUN/BROKEN |
| `--compare-baseline-latest` | Baseline vs latest via `compare_report_bundles()` |
| `--copy-analysis-prompt-latest` | Wide Cursor prompt → clipboard |

Tests: `tests/test_performance_agent_report_history.py`

## Coverage recovery and full-run guidance (PA-3A)

Read-only — no Studio, no new report, no runtime changes. Helps operators recover coverage and understand `PARTIAL` / skipped runs. **1/9 coverage is not performance evidence.**

```powershell
python -m tools.performance_agent --run-playbook
python -m tools.performance_agent --run
python -m tools.performance_agent --health-latest
python -m tools.performance_agent --coverage-latest
python -m tools.performance_agent --scenario-checklist
python -m tools.performance_agent --coverage-prompt-latest
python -m tools.performance_agent --copy-coverage-prompt-latest
```

| Command | Output |
|---------|--------|
| `--coverage-latest` | Coverage diagnosis, weak scenarios, recovery checklist |
| `--coverage-report PATH` | Same for a specific bundle |
| `--scenario-checklist` | 9 scenarios with goal, operator action, coverage risk |
| `--run-playbook` | Full-run before/during/after instructions |
| `--coverage-prompt-latest` | Cursor prompt for coverage recovery (not performance optimization) |
| `--copy-coverage-prompt-latest` | Coverage prompt → clipboard |

Tests: `tests/test_performance_agent_report_coverage.py`

## Output bundle

`reports/performance/<YYYYMMDD-HHMMSS>_giclee_studio/`:

- `report.md` — COPY FOR CHATGPT + technical report
- `summary.json` — includes `log_lifecycle`, `studio` metadata in `--run` mode, `scenario_log_coverage`
- `slow_events.csv`
- `scenario_timeline.csv` — includes `log_coverage_status` per scenario
- `questions_answers.json`
- `agent_events.jsonl`
- `events.jsonl`
- `raw/studio_perf.log`

## Scenario log coverage (PA-1C.1)

Each manual scenario defines `expected_event_patterns` in the profile. After the session, the agent compares `start_ts`/`end_ts` from the wizard timeline with `studio_perf.log` events (±2s tolerance).

| status | meaning |
|--------|---------|
| `ok` | At least one expected pattern matched in the time window |
| `missing_expected_events` | Events in window, but none match expected patterns |
| `no_events_in_window` | No perf events in the scenario window |
| `early_event_seen` | Expected events seen before scenario window (dashboard startup; PA-3B) |

## Data quality semantics fixes (PA-3B)

Shared helpers: `tools/performance_agent/report/semantics.py`.

- **1/9 coverage** = weak evidence — strong operator warning.
- **9/9 + `early_event_seen`** = reviewable / READY with caveat — not the same alarm as 1/9.
- **9/9 with one `no_events_in_window`** = reviewable with caveat — not the same alarm as 1/9.
- Compare: lower slow/suspects with weaker coverage is **not** improvement.
- `slow_events.csv` = real duration only (`elapsed_ms`, `since_click_ms`, `since_request_ms`, `since_details_cta_ms`, `queue_latency_ms`); `since_enter_ms` excluded (view age, not click latency). Hotspots filter non-duration rows from existing bundles. Legacy `since_click_ms` / `cancelled` in old bundles is expected.
- Details CTA (`details_cta` scenario): use `since_request_ms` / `since_details_cta_ms` (GF-P0.1).
- `dashboard_cold` + pre-window dashboard events → `early_event_seen` on next report generation.

| `skipped` / `not_completed` / `incomplete_timestamps` | No validation attempted |

**Important:** `missing_expected_events` means the scenario was not confirmed by the log (session/data quality). It does **not** automatically indicate a GicleeApp runtime regression.

`SCENARIO_LOG_NOT_CONFIRMED` conflicts appear in the report when a completed scenario lacks log confirmation.

## UX questionnaire per scenario

Not every scenario asks about cache, overlay, or click response. Question sets are scoped per scenario (see `SCENARIO_QUESTION_IDS` in `questionnaire.py`). `main_complaint` uses a numbered menu (1–9) instead of free-text aliases.

## Human-readable scenarios (PA-1C.2)

Each manual scenario in the profile defines structured UX guidance:

| Field | Purpose |
|-------|---------|
| `id` | Technical ID for logs, coverage, and reports |
| `display_title` | Human-readable title shown in wizard and reports |
| `click_path` | Numbered steps — where to click |
| `goal` | What the scenario tests |
| `observe` | Bullet list — what to watch for |
| `success_hint` | When to press Enter |
| `expected_event_patterns` | Log signals for coverage validation |

The wizard shows a checklist format:

```text
[4/9] GICLÉE FRAME — pierwsze otwarcie

Co kliknąć:
  1. Wróć do hubu motywu / komponentów.
  ...

Co obserwować:
  - Czy overlay trwa za długo?
  ...

Kiedy nacisnąć Enter:
  Naciśnij Enter dopiero wtedy, gdy GICLÉE FRAME jest widoczny i stabilny.

Oczekiwane sygnały w logu:
  studio.gicleeframe
```

Reports show both technical ID and display title: `gf_open — GICLÉE FRAME — pierwsze otwarcie`.

**`dashboard_cold` in `--run` mode:** Dashboard may load before the wizard starts this scenario. The instruction includes a note to evaluate what you saw at app startup. If coverage shows `missing_expected_events` for `dashboard_cold`, the report may warn that events occurred pre-session.

Legacy aliases: `ScenarioDefinition.name` → `display_title`, `instruction` → flattened structured fields.

## Checkpoint status (PA/GF — 2026-07-08)

**Done locally:** PA-1I…PA-3B. **GF-P0.1** done in code; fresh `--run` validation pending. Tests: 162 passed. Full checkpoint: `Pliki startowe dla GPT/CURRENT_APP_STATE.md`.

**Baseline:** `20260707-214246_giclee_studio` = first sensible GF baseline. Do **not** use `20260707-160215_giclee_studio` (no `studio.gicleeframe.*`).

**Operator flow:** `--doctor` → `--coverage-latest` / `--analyze-latest` → `--hotspots-latest` / `--timeline-latest` → `--cursor-prompt-latest`.

## Tests

```powershell
python -m pytest tests/test_performance_agent_log_parser.py -q
python -m pytest tests/test_performance_agent_report_generator.py -q
python -m pytest tests/test_performance_agent_profiles.py -q
python -m pytest tests/test_performance_agent_questionnaire.py -q
python -m pytest tests/test_performance_agent_wizard.py -q
python -m pytest tests/test_performance_agent_scenario_timeline.py -q
python -m pytest tests/test_performance_agent_log_lifecycle.py -q
python -m pytest tests/test_performance_agent_runner.py -q
python -m pytest tests/test_performance_agent_report_index.py -q
python -m pytest tests/test_performance_agent_clipboard.py -q
python -m pytest tests/test_performance_agent_report_analyzer.py -q
python -m pytest tests/test_performance_agent_report_insights.py -q
python -m pytest tests/test_performance_agent_report_history.py -q
python -m pytest tests/test_performance_agent_report_coverage.py -q
python -m pytest tests/test_performance_agent_operator_commands.py -q
python -m pytest tests/test_studio_perf.py -q
```
