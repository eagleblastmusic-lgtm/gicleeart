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
python -m pytest tests/test_studio_perf.py -q
```
