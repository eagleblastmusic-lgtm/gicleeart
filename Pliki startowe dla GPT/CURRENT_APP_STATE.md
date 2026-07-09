# Current App State

<!-- gpt-starter:gicleeapp-push:start -->
GicleeApp Studio v1.45.2

GitHub / aktualna wersja aplikacji (`eagleblastmusic-lgtm/gicleeapp`):
v1.45.2 — zgodnie z `cursor-api/giclee_app/__init__.py` i `cursor-api/package.json`
Ostatni push GicleeApp: `c2dfa93` na `main` (2026-07-09 21:35 UTC) — Refresh GicleeApp repository snapshot

Monorepo origin/master (projekt / docs):
1cbf2b2 docs(gpt): refresh starter files checkpoint

Previous checkpoint:
46fc718 feat(studio): add GICLÉE FRAME page inventory RAM editor (v1.40.0)

Branch status:
- **GitHub gicleeapp:** v1.45.2 / `main` @ `c2dfa93` (auto-sync po Push GicleeApp, 2026-07-09 21:35 UTC)
- **monorepo origin/master:** `1cbf2b2` — docs(gpt): refresh starter files checkpoint

GPT starter files:
auto-sync po Push GicleeApp 2026-07-09 21:35 UTC (gicleeapp `c2dfa93`, v1.45.2; paczka v37; źródło = ten folder, nie ZIP)

Recent context:
- **GitHub gicleeapp:** v1.45.2 / `main` @ `c2dfa93` — auto-sync po Push GicleeApp
- GICLÉE FRAME™ F2.1: closed + pushed (historycznie v1.40.1 / `4647c1b`; aktualna wersja aplikacji na GitHub jest nowsza)
- Local runtime/untracked still outside commit and remote (working tree hygiene pending)
<!-- gpt-starter:gicleeapp-push:end -->

Completed:
- Background Builder local v1: frozen
- Administracja strony rebuild strategy: done
- Katalog rebuild plan: done
- Katalog F1 read-only shell: done
- Katalog F2 bounded data map: done
- Katalog local planning layer F3+F4: done (draft state, dry-run, readiness, UI planu zmian)
- Push GicleeApp hygiene: done
- **GicleeApp push workflow:** użytkownik zwykle pushuje lokalną aplikację przyciskiem **„Push GicleeApp do GitHub”** w UI GicleeApp (nie ręcznie przez terminal): `cursor-api` → staging → `eagleblastmusic-lgtm/gicleeapp`; dry-run → audyt → potwierdzenie → commit + push na `main`. Nie dotyczy motywu Shopify, `gicleeart-gpt`, ZIP-a wiedzy ani plików startowych GPT.
- GICLÉE FRAME™ F2 page inventory + RAM editor foundation (v1.40.0): done
- GICLÉE FRAME™ F2.1 page editor workflow (v1.40.1): done
  - multi-variant RAM, type-aware editor, settings/reorder as RAM patches
  - trigger sekcji w nagłówku edytora, popup + drag reorder
  - dry-run, readiness accordion, F1 brand collapsed
- Studio Page Component Editor Pattern: documented (`gicleeframe-planning.md` §7, `admin-components-strategy.md`)
- **Performance Agent** (PA-1A–PA-3B): done lokalnie — guided audit + read-only analysis CLI w `cursor-api/tools/performance_agent/` (testy 162 passed; szczegóły § Performance Agent + GF-P0.1)
- **GF-P0.1** (Details CTA Timing Anchor / Baseline Hygiene): done w kodzie lokalnym; runtime validation pending (wymaga świeżego `--run`)

## GicleeApp Implemented Solutions Index

- Istnieje: `cursor-api/docs/GICLEEAPP_IMPLEMENTED_SOLUTIONS_INDEX.md`
- Przed nowym komponentem, helperem lub mechanizmem GicleeApp Cursor **musi** go sprawdzić (wzorce `_shared`, rejestracja, storage, logi, dialogi, DnD, operacje na plikach, guardrails)
- Po dodaniu reużywalnego komponentu/helpera/mechanizmu Cursor **musi** zaktualizować indeks — **nie** przy kosmetyce, tylko przy nowym wzorcu do ponownego użycia

Not started:
- GICLÉE FRAME™ F3 — lokalny zapis draftów RAM do pliku
- GICLÉE FRAME™ F4 — bounded writer + backup/undo
- F5 / F5.5 preview quality / Shopify sync-deploy
- Katalog writer
- Katalog Shopify integration
- Katalog migration

Next recommended:

**Studio Performance — GICLÉE FRAME 6G.5:** **PASS / checkpoint** (główna nitka zamknięta — nie startować kolejnej szerokiej optymalizacji bez wyraźnego problemu UX po ręcznym teście).

**Osobne ścieżki produktowe (choose one — neither started):**
- **A.** cleanup / runtime hygiene working tree (local M + untracked outside commits)
- **B.** GICLÉE FRAME™ F3 — lokalny zapis draftów RAM (no writer, no Save, no Shopify)

---

## GicleeApp Studio Performance (checkpoint 2026-07-07)

**Kontekst:** optymalizacja wydajności GicleeApp Studio. Fazy **5F–6G.2** i główna nitka **6G.5** (GICLÉE FRAME) przeprowadzone lokalnie w Cursorze (working tree może wyprzedzać GitHub connector).

**Źródło prawdy dla diagnozy:** bundle z **Performance Agent** (`report.md`, `summary.json`) — preferuj nad surowym logiem. Gdy brak bundle: `cursor-api/giclee_app/logs/studio_perf.log`. **Zawsze od metryk, nie od hipotez po UI.**

### Zasada diagnostyki (obowiązkowa)

Jeśli użytkownik pisze „dalej muli”, „wolno się otwiera”, „sekcje przycinają” — GPT **najpierw prosi o**:
1. najnowszy bundle Performance Agent (`report.md` / `summary.json` z `cursor-api/reports/performance/**`), **albo**
2. najnowszy `giclee_app/logs/studio_perf.log`, **albo**
3. raport Cursora z agregacją ostatniej sesji.

**Nie zgadywać po objawie. Najpierw metryki, potem kod.**

Jeśli GitHub connector widzi starszy stan niż lokalny Cursor — **lokalny working tree / log użytkownika wygrywa** dla bieżącej diagnozy wydajności.

### Status faz (done lokalnie) — skrót 5F–6G.2

**5F / 5G — Hub:** batching, hover/auto hydration OFF; hub nie jest głównym bottleneckiem.

**6A–6F:** cold views, GF progressive boot (~2.8 s → ~0.6–0.7 s), progressive `page_context`, lazy divider groups, lightweight setting rows, responsive section selection.

**6G.1–6G.2:** route shell, freeze reduction; po 6G.2 GF `open` ~31 ms, `visible_ready` ~179 ms; Asset Lab shell batches ~13–18 ms.

---

## GicleeApp / GICLÉE FRAME performance checkpoint

Główna nitka performance **6G.5** jest zamknięta jako **PASS / checkpoint**.

### Zrealizowane fazy

- **6G.5-K** — Sections Column Early Lane.
- **6G.5-L** — Split sections column.
- **6G.5-L.1** — Extras layout fix.
- **6G.5-M** — Defer init refresh behind early lane.
- **6G.5-N.DIAG** — Hub mount lane diagnostics.
- **6G.5-N.1** — `GicleeFrameView.uses_async_first_paint=True`, launcher `update_idletasks` skipped.
- **6G.5-O** — repeatable smoke baseline.
- **6G.5-P.DIAG** — `CTkScrollableFrame` constructor identified as sections shell bottleneck.
- **6G.5-Q.SPIKE** — static lane before scroll upgrade.
- **6G.5-Q.1** — scroll upgrade delayed until after perceived ready.
- **6G.5-R.DIAG** — perceived ready gate attribution; control gate identified as last gate.
- **6G.5-S.DIAG** — section click interaction latency diagnostics.
- **6G.5-S.1** — selection stability during `init_refresh.light` + editor identity prewarm.
- **6G.5-S.2A** — editor rows/form shell warmup.
- **6G.5-S.2A.VERIFY** — click UX cause matrix.
- **6G.5-S.2B** — selection priority lane / populate enter queue reduction.

### Najważniejsze wyniki

- Hub → GICLÉE FRAME mount queue improved; launcher `update_idletasks` is skipped for `GicleeFrameView`.
- `early_lane_enter.queue_latency_ms` stable around ~35 ms.
- Static lane shows real first rows early; `first_visible_ready` moved into roughly ~175–250 ms range depending on run.
- `CTkScrollableFrame` cost is shifted to scroll upgrade after first/perceived readiness.
- `ensure_identity` cold cost was removed from first click via identity prewarm.
- `ensure_rows` cold cost was reduced via rows prewarm.
- Section click latency improved significantly in **S.2B**:
  - `click → populate_enter` median around ~17.5 ms,
  - max around ~27.3 ms in verify run,
  - divider `populate_done` around ~55 ms,
  - section_legacy `populate_done` around ~59 ms,
  - media_section `populate_done` around ~56 ms,
  - highlight remains around ~8–18 ms.
- Rapid clicking works; latest generation wins and stale jobs are cancelled/ignored.
- Page context remains a secondary **P2** topic: it can still take roughly ~200–430 ms cumulative, but it is not the main blocker for the immediate click response.
- Perceived ready can still be influenced by control gate / control deferred chain, but this is no longer the primary UX blocker for clicking sections.

### Current recommendation

- **STOP / checkpoint** the main 6G.5 performance thread.
- Do not start another broad optimization unless manual UX still shows a clear problem.
- Optional later topic: page context polish / perceived-ready semantics / control late work, only if user still feels lag after real manual use.
- Optional small hygiene: update analyzer scenario C criteria so immediate basic populate is not incorrectly reported as FAIL.

### Post-checkpoint UX follow-up

6G.5-S.2B remains a technical PASS / checkpoint for the main GICLÉE FRAME performance thread.

However, the user reported after the checkpoint that real manual interaction still does not feel fully ideal when clicking sections. This does not reopen the whole 6G.5 performance track. Future work should be symptom-driven and scoped narrowly.

Next optional follow-up:
- 6G.5-T.UX — Manual Friction Capture
  - run GICLÉE FRAME with `GICLEE_STUDIO_PERF=1`,
  - manually test early click, normal section clicks, rapid section clicks, and visual stability,
  - identify the exact UX symptom before proposing code changes.

Do not start broad optimization without a concrete manual UX symptom and perf log.
Likely future micro-topics, only if confirmed by manual UX:
- page context polish,
- static lane / scroll upgrade flicker polish,
- selection visual stability,
- preview repaint polish,
- early-click race validation.

### GF-P0.1 — instrumentation follow-up (nie reopen 6G.5)

Lokalnie wdrożono **GF-P0.1**: details CTA loguje latencję od request/CTA (`since_request_ms`, `since_details_cta_ms`), nie od wieku widoku (`since_enter_ms`). To wąski follow-up instrumentation — **nie** ponowne otwarcie nitki 6G.5. Pełna walidacja wymaga **świeżego `--run`** (świadomie odłożone). Stare bundle mogą nadal pokazywać legacy wiersze w `slow_events.csv` — to oczekiwane, nie błąd narzędzia.

### Performance guardrails

- GicleeApp Studio performance = lokalny projekt aplikacji (`gicleeapp`), **nie** Shopify theme.
- Nie ruszać `Komponenty/*`, Shopify sync/deploy, writerów, Save/Zapisz/Zastosuj bez osobnej zgody.
- Nie zmieniać launcher lifecycle bez osobnego scope.
- Nie zmieniać static lane / scroll upgrade bez nowej scoped phase.
- Nie zmieniać DnD behavior bez explicit scope.
- Background Builder local v1 pozostaje frozen.
- Cursor aktualizuje tylko źródła w `Pliki startowe dla GPT` — **nie generuje ZIP-a** (ZIP = Okno rozmowy u użytkownika).

Technical backlog (only after separate acceptance):
- Katalog bounded writer / save layer
- zero Shopify / sync / deploy
- zero Save / Zapisz / Zastosuj without explicit approval
- do not mutate Komponenty/* runtime data from Studio panels

Important guardrails:
- Knowledge pack source folder: `C:\Strona\pusty\Pliki startowe dla GPT` — **Cursor edytuje tylko pliki źródłowe `.md` / `.txt` w tym folderze**
- **Cursor NIE generuje ZIP-a wiedzy** — bez osobnego, wyraźnego polecenia użytkownika
- ZIP wiedzy (`giclee_cursor_architect_knowledge_v37.zip`) generuje **automatycznie program użytkownika** przy wysyłce paczki przez **Okno rozmowy** (Integracja z GPT) — nie traktuj ZIP jako źródła prawdy
- Cursor nie uruchamia: `build_starter_knowledge_zip()`, GUI **Skopiuj .zip**, żadnego ręcznego generatora ZIP
- GICLÉE FRAME F2.1: RAM-only — no write_text, no writer, no sync/deploy, no Komponenty/* mutation from panel
- Do not start F3/F4/writer without separate approval
- Do not add Save/Zapisz/Zastosuj without separate approval
- Do not touch Shopify/sync/deploy
- Katalog F2 remains read-only
- tldobio absorbed into Katalog
- Background Builder local v1 = Level 2 reference (frozen)

Reference docs (repo):
- `cursor-api/giclee_app/docs/gicleeframe-planning.md`
- `cursor-api/giclee_app/docs/admin-components-strategy.md` (Giclee Frame = pattern reference)

---

## Performance Agent + GF-P0.1 (checkpoint PA/GF — 2026-07-08)

**Status:** PA-1A…PA-3B **done lokalnie**. GF-P0.1 **done w kodzie**, **bez świeżej walidacji runtime**.  
**Testy:** 162 passed (pakiet PA + powiązane studio perf).  
**Commit / push / ZIP:** brak w tym checkpointcie — nie zakładać bez potwierdzenia użytkownika.

**Lokalizacja:** `cursor-api/tools/performance_agent/` (narzędzie diagnostyczne; nie mieszać z optymalizacją runtime Studio 6G.5).  
**Canonical docs:** `tools/performance_agent/README.md` (GitHub) = `cursor-api/tools/performance_agent/README.md` (local). Run from `cursor-api/`.

### Mapa faz (done)

| Faza | Zakres | Status |
|------|--------|--------|
| PA-1A–PA-1C.2 | parse-only, wizard, `--run`, coverage, human-readable scenarios | done |
| PA-1D | `--latest`, `--list-reports` (read-only index) | done |
| PA-1E–PA-1H | ChatGPT copy, health gate | done |
| PA-1I | `--doctor`, `--prepare-chatgpt-latest`, `--open-latest` | done |
| PA-2A | `--analyze-*`, `--compare-*` | done |
| PA-2B | `--hotspots-*`, `--timeline-*`, `--cursor-prompt-*` | done |
| PA-2C | `--history`, `--trend-latest`, `--baseline-candidate` | done |
| PA-3A | `--coverage-*`, `--run-playbook`, `--scenario-checklist` | done |
| PA-3B | semantics (`since_enter_ms` filter, evidence tiers) | done |
| GF-P0.1 | details CTA: `since_request_ms` / `since_details_cta_ms` | done locally; fresh run pending |

### Operator CLI — read-only analysis (preferowane w sesji)

```powershell
python -m tools.performance_agent --doctor
python -m tools.performance_agent --prepare-chatgpt-latest
python -m tools.performance_agent --analyze-latest
python -m tools.performance_agent --compare-latest
python -m tools.performance_agent --hotspots-latest
python -m tools.performance_agent --timeline-latest
python -m tools.performance_agent --cursor-prompt-latest
python -m tools.performance_agent --history
python -m tools.performance_agent --trend-latest
python -m tools.performance_agent --baseline-candidate
python -m tools.performance_agent --coverage-latest
python -m tools.performance_agent --run-playbook
python -m tools.performance_agent --scenario-checklist
```

**Generowanie nowego bundle** (gdy potrzebny świeży run): `--parse-only` · `--manual` · `--run`.

**Rekomendowany flow:** `--doctor` → `--coverage-latest` / `--analyze-latest` → `--hotspots-latest` / `--timeline-latest` → `--cursor-prompt-latest`.

### Zasady interpretacji (nie traktować jako bug)

| Sygnał | Znaczenie |
|--------|-----------|
| `1/9` coverage | **Weak evidence** — nie dowód poprawy/regresji wydajności |
| `9/9` + `early_event_seen` | **Reviewable / READY** z caveat (np. `dashboard_cold`) — nie alarm jak 1/9 |
| `since_enter_ms` | Wiek widoku — **nie** latencja kliknięcia |
| details CTA | Prawdziwe pola: **`since_request_ms`**, **`since_details_cta_ms`** (GF-P0.1) |
| Stary `slow_events.csv` | Legacy wiersze (`since_click_ms`, `cancelled`) w starych bundle — **oczekiwane** przy `--hotspots-latest` |
| `SCENARIO_LOG_NOT_CONFIRMED` | Jakość danych sesji — **nie** automatycznie regresja runtime |

### Baseline bundles (GF)

- **Dobry pierwszy GF baseline:** `20260707-214246_giclee_studio`
- **Nie używać jako GF baseline:** `20260707-160215_giclee_studio` — nie mierzył `studio.gicleeframe.*`
- Automatyczny wybór: `--baseline-candidate`; ręczne porównanie: `--compare-reports`

### Pending

1. **Świeży `--run`** — walidacja GF-P0.1 w nowym `slow_events.csv` / timeline (świadomie odłożone)
2. **Opcjonalny P1** — `render_section_list` / selection pipeline — **tylko** jeśli potwierdzi świeży baseline; nie startować bez dowodu

### Bundle wyjściowy

`reports/performance/<YYYYMMDD-HHMMSS>_giclee_studio/` — m.in. `report.md`, `summary.json`, `slow_events.csv`, `scenario_timeline.csv`, `raw/studio_perf.log`. Runtime output i log ignorowane przez git.

---

## Giclee Viewer — current state

Repo GitHub:

`eagleblastmusic-lgtm/giclee-viewer`

Repo lokalne:

`C:\Strona\giclee-viewer`

Aktualny HEAD:

`26446ce487d6fe1a511c7c137215834c78b6849f`

Commit:

`feat: add GV-7 creative metadata workspace`

Status:

- working tree clean
- build PASS
- test PASS: 143/143
- brak push
- znane ostrzeżenia: NU1903 dla transitive dependency `SQLitePCLRaw.lib.e_sqlite3`
- metadane kreatywne zapisywane tylko w SQLite
- zero zapisu do oryginalnych obrazów/wideo/EXIF

Zamknięte etapy Giclee Viewer:

- GV-0 — WPF skeleton
- GV-1 — SQLite index foundation
- GV-2 — thumbnail cache and grid
- GV-6.2 — rename execution
- GV-6.2.1 — collections test stability
- GV-6.3 — rename recovery and cleanup
- GV-6.4 — rename UX and audit polish
- GV-7 — Creative Metadata Workspace

GV-7 done:

- schema SQLite v7
- rozwinięta istniejąca tabela `prompts`
- bez nowej tabeli `creative_prompt_records`
- nowe modele:
  - `CreativePromptRecord`
  - `CreativePromptType`
  - `CreativeMetadataSummary`
  - `CreativeMetadataRules`
- nowe repozytorium:
  - `CreativeMetadataRepository`
- nowy ViewModel:
  - `CreativeMetadataViewModel`
  - `CreativePromptRecordViewModel`
- panel `Creative Metadata`
- pola:
  - Main prompt
  - Negative prompt
  - Video prompt
  - Tool
  - Model
  - Settings
  - Notes
  - Last updated
- Save metadata:
  - pierwszy zapis tworzy `version=1`
  - `record_type=creative`
  - `is_primary=1`
- Add version:
  - nowa wersja z `is_primary=0`
- Set as primary
- Copy Main / Negative / Video / All
- filtry:
  - Has prompt
  - Prompt contains
  - Tool
  - Model
- badge `PROMPT` na kafelkach
- badge ładowany batchowo, zero query per tile
- po save lokalny refresh jednego kafelka
- `_loadGeneration` i `_loadedFileId` chronią przed zapisem do złego pliku przy szybkim klikaniu
- rename module nietknięty
- metadane zachowane przez `file_id`, więc rename zachowuje prompty

Usunięte / zastąpione:

- `PromptRepository`
- `PromptEditorViewModel`
- stare testy promptów

Nowe / zmienione pliki GV-7:

Core:
- `CreativePromptRecord.cs`
- `CreativePromptType.cs`
- `CreativeMetadataSummary.cs`
- `CreativeMetadataRules.cs`
- `MediaFilter.cs`

Data:
- `DbInitializer.cs`
- `CreativeMetadataRepository.cs`
- `CreativeMetadataFilterSql.cs`
- `SqlLikePattern.cs`
- `MediaFileRepository.cs`
- `CollectionRepository.cs`

UI:
- `CreativeMetadataViewModel.cs`
- `CreativePromptRecordViewModel.cs`
- `MainViewModel.cs`
- `ThumbnailGridViewModel.cs`
- `ThumbnailItemViewModel.cs`

App:
- `MainWindow.xaml`
- `MainWindow.xaml.cs`
- `ThumbnailTile.xaml`

Tests:
- `CreativeMetadataRepositoryTests.cs`
- `CreativeMetadataViewModelTests.cs`
- `SqlLikePatternTests.cs`
- `ViewModelTestHelpers.cs`
- `DbInitializerTests.cs`

Docs:
- `ARCHITECTURE.md`
- `MVP_PLAN.md`
- `PERFORMANCE_RULES.md`
- `README.md`

Następny sugerowany etap Giclee Viewer:

GV-8 — Similarity / Variants / Pairing

Zakres przyszły:
- wykrywanie podobnych obrazów
- warianty tego samego obrazu
- różne rozdzielczości tego samego pliku
- wybór wersji głównej
- ręczne zatwierdzanie par
- powiązanie wariantów z promptami/metadanymi

---

## GicleeApp Studio 2.0 — future direction

GicleeApp Studio 2.0 ma być przyszłym C# / WPF shell dla obecnego workflow Giclée Art.

Założenie architektoniczne:

- C# / WPF: UI, dashboard, moduły, routing, statusy, logi, panele, szybka responsywność
- Python / obecny gicleeapp / cursor-api: workers, generatory, Shopify helpers, GPT ZIP, raporty, Performance Agent, automatyzacje
- komunikacja: command JSON → Python worker → result JSON/report → UI

Nie przepisywać obecnego GicleeApp 1:1.
Nie usuwać obecnych narzędzi Python.
Budować nowy shell obok i podpinać istniejące workers etapami.

Sztywny szablon modułów: `GICLEEAPP_STUDIO_2_0_MODULE_TEMPLATE.md` — nie zmieniać nazw, kolejności ani struktury bez wyraźnej decyzji użytkownika.

Pierwszy przyszły etap:

GAS-0 — GicleeApp Studio 2.0 Information Architecture & Shell Plan

Cel GAS-0:

- przeanalizować obecny GicleeApp / cursor-api,
- zaprojektować WPF shell,
- zachować sztywny szablon modułów użytkownika,
- zaproponować dashboard,
- zaproponować worker bridge,
- zaproponować routing,
- zaproponować roadmapę GAS-1/GAS-2/GAS-3,
- bez implementacji i bez przepisywania obecnego GicleeApp.

---

## Programming / Architecture Principles — current direction

Aktualna preferowana architektura dla nowych aplikacji Giclée Art:

```text
C# / WPF
= UI, dashboard, routing, szybka responsywność, MVVM, panele, statusy

Python
= workers, generatory, Shopify helpers, GPT ZIP, raporty, automatyzacje

SQLite / JSON
= lokalny stan, indeks, historia, komunikacja między modułami
```

Nie „Python kontra C#” — oba warstwy współpracują.

1. Dla nowych aplikacji desktopowych preferować **C# / WPF + MVVM**.
   Powód: lepsza responsywność UI, wirtualizacja list, stabilniejsze desktopowe layouty, async/await, dobre testowanie ViewModeli.

2. **Python zostaje ważnym silnikiem narzędziowym.**
   Nie przepisywać działających Pythonowych workerów bez powodu. Python jest dobry do:
   - generowania plików,
   - integracji GPT,
   - Shopify helpers,
   - raportów,
   - automatyzacji,
   - lokalnych narzędzi workflow.

3. **Długie operacje nigdy nie mogą blokować UI.**
   Każda ciężka operacja powinna działać jako:
   - background task,
   - worker process,
   - kolejka,
   - albo async service z CancellationToken.

4. **Local-first.**
   Dane aplikacji trzymać lokalnie:
   - SQLite dla stanu aplikacji,
   - JSON/report files dla wymiany wyników,
   - cache lokalny dla miniatur i artefaktów.
   Nie zapisywać metadanych do oryginalnych plików bez osobnej decyzji użytkownika.

5. **Data safety first.**
   Operacje na prawdziwych plikach muszą mieć:
   - dry-run,
   - walidację,
   - double confirmation,
   - audit,
   - recovery/rollback, jeśli operacja jest destrukcyjna lub częściowo odwracalna.

6. **No per-tile / per-row heavy queries.**
   Dla gridów, miniatur, badge'ów i filtrów preferować batch queries oraz cache. Unikać zapytań DB wykonywanych osobno dla każdego kafelka.

7. **Nie rozdrabniać pracy bez powodu.**
   Małe etapy są dobre tylko przy ryzyku danych, migracji lub operacjach na plikach.
   Dla funkcji produktowych preferować większe, spójne pakiety.

8. **Existing GicleeApp is not a mistake.**
   Obecne Pythonowe GicleeApp traktować jako działający worker/tooling foundation.
   GicleeApp Studio 2.0 ma być nowym WPF shell obok, a nie brutalnym przepisaniem 1:1.

9. **Connector / private repo rule.**
   Dla prywatnych repo używać GitHub connectora, nie publicznych raw URL.

10. **Cursor role.**
    Cursor implementuje lokalnie.
    GPT/assistant projektuje architekturę, reviewuje raporty, wykrywa ryzyka i przygotowuje precyzyjne prompty.

Szczegóły w COMPACT v37 § Programming / Architecture Principles.

---

## Current technical lessons from Giclee Viewer

Giclee Viewer potwierdził, że C# / WPF + SQLite jest dobrym kierunkiem dla nowych lokalnych aplikacji Giclée Art.

Sprawdzone wzorce:
- MVVM z testowalnymi ViewModelami,
- SQLite migracje addytywne i idempotentne,
- batch queries zamiast query per tile,
- background thumbnail generation,
- cache lokalny,
- generation counters dla async loadów,
- dry-run + execution + rollback + audit dla operacji na plikach,
- ViewModel tests bez kruchych Task.Delay,
- oddzielanie UI od worker/service layer.

Te wzorce powinny być traktowane jako baza dla przyszłego GicleeApp Studio 2.0.

Szczegóły w COMPACT v37 § Current technical lessons from Giclee Viewer.

---

## Strategic Direction — Giclée Art Studio OS

Długoterminowy kierunek projektu to budowa lokalnego ekosystemu:

Giclée Art Studio OS

Obecnie składa się / będzie składał z dwóch głównych filarów:

1. Giclee Viewer
   - szybka lokalna biblioteka obrazów/wideo,
   - miniatury,
   - kolekcje,
   - flagi/tagi,
   - creative metadata,
   - prompty,
   - warianty/podobieństwo,
   - preview,
   - selekcja materiałów.

2. GicleeApp Studio 2.0
   - przyszły C# / WPF shell dla workflow Giclée Art,
   - bazujący na obecnym Pythonowym GicleeApp / cursor-api,
   - nie jako przepisanie 1:1, tylko nowy premium desktop shell,
   - Python pozostaje worker/tooling layer.

Giclee Viewer traktować jako praktyczny wzorzec technologiczny dla przyszłego GicleeApp Studio 2.0:
- WPF / MVVM,
- SQLite,
- testowalne ViewModele,
- migracje addytywne,
- batch queries,
- background tasks,
- safety-first workflow,
- lokalny cache,
- brak blokowania UI.

GicleeApp Studio 2.0 ma używać sztywnego szablonu modułów użytkownika z pliku:

`GICLEEAPP_STUDIO_2_0_MODULE_TEMPLATE.md`

Nie zmieniać nazw, kolejności ani struktury modułów bez wyraźnej decyzji użytkownika.

Szczegóły w COMPACT v37 § Strategic Direction — Giclée Art Studio OS.

---

## Work Planning Rule

Nie rozdrabniać dalszych prac na zbyt małe mikroetapy.

Małe etapy są uzasadnione tylko przy:
- migracjach bazy,
- operacjach na prawdziwych plikach,
- ryzyku utraty danych,
- rollback/recovery,
- dużych zmianach architektury.

Dla funkcji produktowych preferować większe, spójne pakiety:
- GV-8 Similarity / Variants / Pairing
- GV-9 Preview Workspace
- GV-10 Review Workflow
- GAS-0 GicleeApp Studio 2.0 Architecture Discovery

Szczegóły w COMPACT v37 § Work Planning Rule.

---

## UI / Product Taste Direction

Docelowy styl nowych aplikacji Giclée Art:
- premium,
- spokojny,
- ciemny,
- czytelny,
- studyjny,
- bez chaosu,
- bez przeładowania efektami,
- dużo oddechu,
- logiczne karty,
- jasne statusy,
- estetyka: fine art / museum / creative operations dashboard.

Nie kopiować chaotycznie obecnego UI 1:1.
Zachować użyteczne elementy obecnego GicleeApp Studio, ale GicleeApp Studio 2.0 projektować jako bardziej dojrzały, elegancki i responsywny shell.

Szczegóły w COMPACT v37 § UI / Product Taste Direction.

---

## Source of Truth / Decision Memory

W nowych sesjach GPT należy traktować poniższe zasady jako obowiązujące:

1. Giclee Viewer i GicleeApp Studio 2.0 to dwa różne projekty.

Giclee Viewer:
- GitHub: `eagleblastmusic-lgtm/giclee-viewer`
- lokalnie: `C:\Strona\giclee-viewer` (osobne od `gicleeapp` / `gicleeart-gpt`)
- C# / WPF / SQLite
- media library, thumbnails, tags, collections, rename, prompts, metadata, future variants/preview

GicleeApp / GicleeApp Studio 2.0:
- obecny workflow bazuje na `C:\Strona\pusty` / `cursor-api`
- obecne GicleeApp to działający Python tooling foundation
- GicleeApp Studio 2.0 ma być przyszłym C# / WPF shell + Python workers

Nie mieszać tych dwóch codebase'ów bez wyraźnego polecenia użytkownika.

2. ZIP wiedzy nie jest źródłem prawdy.

Źródłem prawdy są lokalne pliki:

`C:\Strona\pusty\Pliki startowe dla GPT`

ZIP jest tylko paczką eksportową generowaną z tych źródeł.

Cursor nie generuje ZIP-a bez osobnej komendy użytkownika.

3. Sztywny szablon GicleeApp Studio 2.0 jest obecnie decyzją użytkownika.

Plik:

`GICLEEAPP_STUDIO_2_0_MODULE_TEMPLATE.md`

zawiera aktualny, sztywny układ modułów.

Nie zmieniać nazw, kolejności ani struktury modułów bez wyraźnej decyzji użytkownika.

4. Nie wracać do dyskusji „Python czy C#” od zera.

Aktualna decyzja strategiczna:
- C# / WPF dla nowych desktopowych shelli i UI,
- Python dla istniejących workerów, automatyzacji, generatorów i narzędzi,
- SQLite / JSON / raporty jako lokalna warstwa stanu i wymiany danych.

5. Nie rozdrabniać roadmapy bez powodu.

Preferować większe pakiety produktowe.

Mikroetapy są dopuszczalne tylko przy:
- ryzyku utraty danych,
- operacjach na realnych plikach,
- migracjach bazy,
- rollback/recovery,
- dużych zmianach architektury.

6. Każda nowa sesja GPT powinna najpierw sprawdzić aktualny checkpoint.

Najważniejsze bieżące checkpointy:
- Giclee Viewer HEAD: `26446ce487d6fe1a511c7c137215834c78b6849f`
- GV-7 Creative Metadata Workspace done
- build PASS
- test PASS: 143/143
- working tree clean
- brak push
- next likely GV stage: GV-8 Similarity / Variants / Pairing
- future GAS stage: GAS-0 GicleeApp Studio 2.0 Information Architecture & Shell Plan

Szczegóły w COMPACT v37 § Source of Truth / Decision Memory.
