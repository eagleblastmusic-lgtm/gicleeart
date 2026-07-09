# Giclee Cursor Architect — v37 update

## v37 update

- Updates current checkpoint to GicleeApp Studio v1.37.0.
- Sets canonical HEAD / origin/master to 16febff71dd2aad397f6c35ff8b8eef896abbb49.
- Marks Background Builder local v1 as frozen.
- Marks Administracja strony rebuild strategy as done.
- Marks Katalog rebuild plan, F1 read-only shell, and F2 bounded data map as done.
- Sets next recommended phase to Katalog local planning layer.
- Adds pacing rule: group safe planning layers; split writer, Shopify, migrations, and major architecture decisions.

> **Uwaga:** Poniższa sekcja „v37 update” to historyczne notatki pierwotnego release v3.7 — **nie** aktualny checkpoint aplikacji. Aktualny stan projektu zawsze w `CURRENT_APP_STATE.md` (obecnie Studio v1.41.2 na GitHub, monorepo origin/master `845191c`, Performance Agent lokalnie `c966912` push pending, Performance 6G.5: **PASS / checkpoint**).

---

v3.5 = dual-repo routing po utworzeniu `eagleblastmusic-lgtm/gicleeapp`.  
v3.6 = checkpoint F3/F3.2.1.1 + zasady testowania + granice Studio w instrukcjach compact.  
v3.7 = checkpoint Studio v1.37.0 + Katalog F1+F2 + local planning layer next + pacing rule.

---

## Checkpoint refresh (post-65e862b)

Bez bumpu paczki na v38 — tylko odświeżenie checkpointu w plikach v3.7:

- GicleeApp Studio **v1.38.0**
- monorepo HEAD / origin/master: **65e862b**
- gicleeapp main: **a056bb5**
- Katalog local planning layer F3+F4: **done**
- Next: **bounded writer / save layer** — tylko po osobnej akceptacji
- F5.5: not started

Zaktualizowane pliki: `CURRENT_APP_STATE.md`, checkpoint block w COMPACT v37, `GICLEE_CURSOR_MASTER_INDEX_v37.md`, ten README, `Wiadomość początkowa.txt`. ZIP generuje użytkownik przez Okno rozmowy — Cursor nie generuje ZIP-a.

---

## Checkpoint refresh (post Push GicleeApp + GICLÉE FRAME™)

Bez bumpu paczki na v38:

- monorepo project checkpoint: **4760a29** (pełny checkpoint projektu / plików startowych po Studio 1.38.0)
- Studio code checkpoint: **65e862b** (Katalog planning layer feature)
- gicleeapp snapshot (main): **21bc3ed** (Push GicleeApp, hygiene OK)
- GPT starter files: **refreshed after Push GicleeApp** (bez wiązania z `origin/master` — unikaj pętli SHA)
- Push GicleeApp hygiene: **done**
- Pliki startowe GPT: **monorepo only** (sync skip do gicleeapp)
- Primary next: **GICLÉE FRAME™** — design strony / komponent premium
- Technical backlog: Katalog bounded writer — tylko po osobnej akceptacji

---

## Checkpoint refresh (post F2.1 — v1.40.1)

Bez bumpu paczki na v38:

- HEAD / origin/master: **4647c1b** — GICLÉE FRAME F2.1 editor workflow polish
- Poprzedni checkpoint: **46fc718** (v1.40.0 F2 inventory)
- GicleeApp Studio: **v1.40.1**
- Branch: **master synced with origin/master**
- GICLÉE FRAME F2.1: **done** (multi-variant RAM, type-aware editor, settings/reorder RAM, dry-run, pattern doc)
- **Studio Page Component Editor Pattern** — udokumentowany w repo
- Next (choose one — **not started**): **(A)** cleanup / runtime hygiene · **(B)** GICLÉE FRAME F3 local draft persistence
- F3/F4/writer/Save/Shopify: **not started**

Zaktualizowane pliki: `CURRENT_APP_STATE.md`, COMPACT v37, MASTER_INDEX v37, CLEAN_PACK v37, ten README, `Wiadomość początkowa.txt`. **ZIP generuje użytkownik** przez Okno rozmowy — Cursor **nie** uruchamia generatora ZIP.

---

## Checkpoint refresh (Studio Performance 5F–6G.2 — 2026-07-07)

Bez bumpu paczki na v38:

- Fazy **5F–6G.2:** done lokalnie (Hub, cold views, GF progressive boot/page_context, lazy dividers, lightweight rows, responsive selection, route shell, freeze reduction)
- **Źródło prawdy diagnozy:** `cursor-api/giclee_app/logs/studio_perf.log` — GPT zaczyna od logów, nie od hipotez UI
- Metryki po 6G.2: GF `open` ~31 ms, `visible_ready` ~179 ms; Asset Lab shell batches ~13–18 ms
- **Zasada:** „dalej muli” → najpierw `studio_perf.log` lub raport Cursora; **najpierw metryki, potem kod**
- GitHub connector może widzieć starszy stan niż lokalny working tree — log użytkownika wygrywa

Zaktualizowane pliki: `CURRENT_APP_STATE.md`, COMPACT v37, MASTER_INDEX v37, CLEAN_PACK v37, ten README, `Wiadomość początkowa.txt`. **ZIP generuje użytkownik** przez Okno rozmowy.

---

## Checkpoint refresh (GICLÉE FRAME Performance 6G.5 closure — 2026-07-07)

Bez bumpu paczki na v38:

- **Główna nitka 6G.5:** **PASS / checkpoint** (K → S.2B zamknięte)
- Kluczowe wyniki: early lane ~35 ms queue; `first_visible_ready` ~175–250 ms; `CTkScrollableFrame` odroczony do scroll upgrade; click → populate_enter median ~17.5 ms (S.2B)
- **Current recommendation:** STOP / checkpoint — nie startować kolejnej szerokiej optymalizacji bez wyraźnego problemu UX po ręcznym teście
- Opcjonalnie później (P2): page context polish, perceived-ready semantics, control late work; hygiene analyzer scenario C
- Guardrails bez zmian: nie `Komponenty/*`, writer, Save, Shopify/sync/deploy, launcher lifecycle, static lane/scroll upgrade, DnD bez osobnego scope

Zaktualizowane pliki: `CURRENT_APP_STATE.md`, ten README (aktywny checkpoint). **ZIP generuje użytkownik** przez Okno rozmowy — Cursor nie generuje ZIP.

---

## Checkpoint refresh (Performance Agent PA-1C.2 — 2026-07-07)

Bez bumpu paczki na v38:

- **Performance Agent** PA-1A–PA-1C.2: **done** — guided performance audit workflow w `cursor-api/tools/performance_agent/`
- Lokalny commit: `c966912` — `feat(perf-agent): add guided performance audit workflow`; testy 46/46 PASS; **push pending** (nie zakładać push bez potwierdzenia)
- Komendy: `--parse-only`, `--manual`, `--run`
- Bundle: `report.md`, `summary.json`, `events.jsonl`, `agent_events.jsonl`, `questions_answers.json`, `scenario_timeline.csv`, `slow_events.csv`, `raw/studio_perf.log`
- Runtime output: `reports/performance/**` (gitignored); runtime log: `giclee_app/logs/studio_perf.log` (gitignored)
- **Diagnoza wydajności:** preferuj bundle PA (`report.md` / `summary.json`) nad surowym logiem
- **`SCENARIO_LOG_NOT_CONFIRMED`:** jakość danych sesji, nie automatycznie regresja runtime
- **Nie startować PA-1D** (headless/GUI/marker injection) bez wyraźnej prośby
- Opcjonalnie na przyszłość: analiza realnych raportów (`DETAILS_CTA_SLOW`, `scroll_upgrade`, UX score GF itd.)

Zaktualizowane pliki: `CURRENT_APP_STATE.md`, COMPACT v37, MASTER_INDEX v37, CLEAN_PACK v37, `GICLEE_ANALYST_MODE_PERFORMANCE_v1.md`, ten README. **ZIP generuje użytkownik** przez Okno rozmowy — Cursor nie generuje ZIP.

---

## Checkpoint refresh (GitHub app v1.41.2 — 2026-07-07)

Bez bumpu paczki na v38:

- **GitHub gicleeapp:** aktualna wersja aplikacji **v1.41.2** (`giclee_app/__init__.py`, `package.json`)
- Stary checkpoint ZIP (v1.40.1 / `4647c1b` F2.1) jest nieaktualny co do numeru wersji
- **monorepo origin/master:** `845191c` (docs); kod aplikacji na origin = linia v1.40.1
- **Performance Agent** lokalnie `c966912` — push pending (bez zmian)

Zaktualizowane pliki: `CURRENT_APP_STATE.md`, COMPACT v37, MASTER_INDEX v37, CLEAN_PACK v37, `Wiadomość początkowa.txt`, ten README. **ZIP generuje użytkownik** przez Okno rozmowy — Cursor nie generuje ZIP.

---

## Zasada: Cursor nie generuje ZIP

- **Cursor** aktualizuje tylko pliki źródłowe w `Pliki startowe dla GPT/`.
- **ZIP wiedzy** generuje automatycznie program użytkownika przy wysyłce przez **Okno rozmowy** (Integracja z GPT).
- Cursor **nie** uruchamia `build_starter_knowledge_zip()`, GUI **Skopiuj .zip** ani ręcznego generatora — **chyba że użytkownik da osobne, wyraźne polecenie**.

---

## Komenda: Aktualizuj pliki startowe

Stała komenda robocza użytkownika do Custom GPT. Pełna definicja: sekcja **KOMENDA ROBOCZA** w `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v37.md`.

### Kiedy używać

- po większym commicie Studio / zmianie wersji GicleeApp,
- po zamknięciu lub rozpoczęciu fazy Katalog (F1–F5.5),
- po nowych guardrails, pacing rules lub zmianach workflow review,
- gdy `CURRENT_APP_STATE.md` nie odzwierciedla już checkpointów projektu / Studio / gicleeapp snapshot (nie aktualizuj docs o SHA przyszłego commita jako `origin/master`)

### Co robi GPT vs Cursor

| Krok | GPT (Custom) | Cursor |
|------|----------------|--------|
| 1 | Audyt stanu, lista plików do aktualizacji | — |
| 2 | Przygotowuje precyzyjny prompt maintenance | — |
| 3 | — | Edytuje `.md` w `Pliki startowe dla GPT` |
| 4 | — | Raport git — **bez generowania ZIP** |
| 5 | Użytkownik | Wysyła paczkę przez **Okno rozmowy** (program generuje ZIP automatycznie) |

GPT **nie implementuje** feature aplikacji. Nie miesza maintenance z writerem, Shopify/sync/deploy, Push GicleeApp ani runtime cleanupem.

### Checklista (typowy prompt do Cursora)

1. Zaktualizuj `CURRENT_APP_STATE.md` (checkpoint, SHA, fazy, next).
2. Zsynchronizuj checkpoint w COMPACT v37, MASTER_INDEX, CLEAN_PACK, ten README — **bez bumpu v38**.
3. **Nie** uruchamiaj generatora ZIP z Cursora — ZIP robi użytkownik przez Okno rozmowy.
4. Nie dotykaj runtime dirty; nie `git add -A`; nie push; nie commit bez raportu.
5. Osobny commit docs po akceptacji raportu.

---

## Co nowego

1. **`GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v37.md`** — Instructions z routingiem, granicami Studio/Katalog, pacing rule i zasadami testowania (checkpoint odświeżany w `CURRENT_APP_STATE.md`)
2. **`GICLEE_CURSOR_MASTER_INDEX_v37.md`** — hierarchia v3.7, główny plik instrukcji = COMPACT v37
3. **`README_GICLEE_CURSOR_ARCHITECT_UPDATE_v37.md`** — ten plik
4. **`GICLEE_CURSOR_ARCHITECT_CLEAN_PACK_v37.md`** — manifest v3.7
5. **`CURRENT_APP_STATE.md`** — źródło prawdy aktualnego checkpointu (nie ten README)

Bez zmian wersji (nadal v3.5 / v3.x): dual-repo routing, snapshot workflow, motion/effects.

---

## Jak użyć (Custom GPT)

### Pole Instructions

Wklej zawartość:

**`GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v37.md`**

### Pliki wiedzy (Knowledge)

Dodaj **aktywne pliki v3.7** (patrz `GICLEE_CURSOR_ARCHITECT_CLEAN_PACK_v37.md`):

**Routing / workflow / checkpoint:**
- `GICLEE_DUAL_REPO_REVIEW_ROUTING_v35.md`
- `GICLEE_GITHUB_SNAPSHOT_REVIEW_WORKFLOW_v35.md`
- `GICLEE_CURSOR_MASTER_INDEX_v37.md`
- `CURRENT_APP_STATE.md`

**Motion / effects / patterns (bez zmian wersji):**
- `GICLEE_AWWWARDS_MOTION_SYSTEM_v3.md`
- `GICLEE_BAD_EFFECTS_BLACKLIST_v31.md`
- `GICLEE_CODE_PLUS_PROMPT_WORKFLOW_v3.md`
- `GICLEE_CURSOR_EXAMPLES_v31.md`
- `GICLEE_EFFECT_LIBRARY_v31.md`
- `GICLEE_IMPLEMENTATION_PATTERNS_v31.md`
- `GICLEE_MOTION_QUALITY_RUBRIC_v31.md`
- `GICLEE_MOTION_REVIEW_LOOP_v33.md`
- `GICLEE_PROMPT_RESPONSE_MODES_v3.md`
- `GICLEE_RESEARCH_DRIVEN_EFFECTS_v3.md`
- `GICLEE_SECTION_PLAYBOOK_v32.md`
- `GICLEE_SIGNATURE_MOMENTS_v33.md`

## Added Shopify mode files

Dodano zestaw plików `GICLEE_SHOPIFY_MODE_*_v1.md`, które wprowadzają modularne tryby pracy dla strony Shopify Giclée Art. Nowe tryby obejmują:

- homepage art direction,
- product page / PDP,
- collection / catalog,
- copy / brand story,
- motion / interaction,
- conversion / trust,
- responsive / accessibility,
- SEO / content,
- translation / markets.

Te pliki są dodatkowymi rozszerzeniami do głównych Instructions v37 oraz Shopify Snapshot workflow. Nie zastępują `CURRENT_APP_STATE.md` i nie oznaczają zmian w produkcji/live.

### GitHub connector

Podłącz **oba** prywatne repo (jeśli review obu warstw):

- `eagleblastmusic-lgtm/gicleeart-gpt`
- `eagleblastmusic-lgtm/gicleeapp`

Nie używaj publicznych URL-i ani `raw.githubusercontent.com`.

---

## Nie dodawać do finalnego ZIP (archiwum)

Stare README, stare compact instructions (v36 i wcześniejsze), pełne `INSTRUCTIONS_v3.md` — patrz **CLEAN_PACK v37**.

---

## Następny krok (poza tym update)

**Zrobione:** `Wiadomość początkowa.txt` zawiera dual-repo routing, pacing rule i odniesienie do aktualnego checkpointu z `CURRENT_APP_STATE.md` (nie z historycznych notatek v1.37.0 w tym README).

## Added analyst mode files

Dodano zestaw plików `GICLEE_ANALYST_*_v1.md`, które wprowadzają modularne tryby pracy dla analizy GicleeApp i Giclée Art.

Nowe tryby obejmują:

- base analyst prompt,
- performance,
- debug/regression,
- Cursor implementation review,
- stage architect,
- UI/UX premium,
- Shopify snapshot,
- GPT integration / ZIP.

Te pliki są dodatkowymi rozszerzeniami do głównych Instructions v37. Nie zmieniają źródła prawdy projektu i nie zastępują `CURRENT_APP_STATE.md`.

---

## Checkpoint refresh (GV-7 + GicleeApp Studio 2.0 template)

Bez bumpu paczki na v38:

- **Giclee Viewer** GitHub `eagleblastmusic-lgtm/giclee-viewer` · HEAD: `26446ce487d6fe1a511c7c137215834c78b6849f` — GV-7 Creative Metadata Workspace **done**
- build PASS · test PASS 143/143 · working tree clean · brak push
- next likely: **GV-8** Similarity / Variants / Pairing
- **GicleeApp Studio 2.0** — future direction (C# / WPF shell + Python workers); sztywny szablon: `GICLEEAPP_STUDIO_2_0_MODULE_TEMPLATE.md`
- pierwszy etap GAS: **GAS-0** Information Architecture & Shell Plan (bez implementacji)

Zaktualizowane pliki: `CURRENT_APP_STATE.md`, `GICLEEAPP_STUDIO_2_0_MODULE_TEMPLATE.md` (nowy), checkpoint w COMPACT v37, `GICLEE_CURSOR_MASTER_INDEX_v37.md`, `Wiadomość początkowa.txt`, ten README. ZIP generuje użytkownik przez Okno rozmowy — Cursor nie generuje ZIP-a.

---

## Checkpoint refresh (architecture principles)

Bez bumpu paczki na v38:

- **Programming / Architecture Principles — current direction** — 10 praktycznych zasad: C# / WPF (UI, MVVM) + Python (workers) + SQLite/JSON (local-first); data safety; no per-tile queries; GicleeApp jako foundation, nie błąd
- **Current technical lessons from Giclee Viewer** — sprawdzone wzorce z GV jako baza dla GicleeApp Studio 2.0

Kanon: `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v37.md` (sekcje w COMPACT). Pełny opis: `CURRENT_APP_STATE.md`. Skrót: `GICLEE_CURSOR_MASTER_INDEX_v37.md` POZIOM 0.

Zaktualizowane pliki: COMPACT v37, `CURRENT_APP_STATE.md`, MASTER INDEX v37, CLEAN PACK v37, ten README. ZIP generuje użytkownik — Cursor nie generuje ZIP-a.

---

## Checkpoint refresh (strategic direction)

Bez bumpu paczki na v38:

- **Strategic Direction — Giclée Art Studio OS** — ekosystem = Giclee Viewer + GicleeApp Studio 2.0; GV jako wzorzec technologiczny; szablon modułów `GICLEEAPP_STUDIO_2_0_MODULE_TEMPLATE.md`
- **Work Planning Rule** — większe pakiety produktowe (GV-8…GV-10, GAS-0); mikroetapy tylko przy ryzyku danych / migracjach / plikach
- **UI / Product Taste Direction** — premium, spokojny, ciemny, studyjny; fine art / museum / creative operations dashboard

Kanon: `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v37.md` (trzy nowe sekcje). Pełny opis: `CURRENT_APP_STATE.md`. Skrót: `GICLEE_CURSOR_MASTER_INDEX_v37.md` POZIOM 0.

Zaktualizowane pliki: COMPACT v37, `CURRENT_APP_STATE.md`, MASTER INDEX v37, CLEAN PACK v37, `Wiadomość początkowa.txt`, ten README. ZIP generuje użytkownik — Cursor nie generuje ZIP-a.

---

## Checkpoint refresh (source of truth / decision memory)

Bez bumpu paczki na v38:

- **Source of Truth / Decision Memory** — GV ≠ GAS 2.0 (osobne codebase'y); ZIP = aktualny snapshot wiedzy załączony do rozmowy; źródłem edycji dla Cursora = lokalne pliki w `Pliki startowe dla GPT`; szablon modułów = decyzja użytkownika; nie wracać do „Python czy C#”; nie rozdrabniać roadmapy; nowa sesja = najpierw checkpoint (GV-7 done, next GV-8, future GAS-0)

Kanon: `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v37.md` § Source of Truth / Decision Memory. Pełny opis: `CURRENT_APP_STATE.md`. Skrót: `GICLEE_CURSOR_MASTER_INDEX_v37.md` POZIOM 0.

Zaktualizowane pliki: COMPACT v37, `CURRENT_APP_STATE.md`, MASTER INDEX v37, CLEAN PACK v37, `Wiadomość początkowa.txt`, ten README. ZIP generuje użytkownik — Cursor nie generuje ZIP-a.
