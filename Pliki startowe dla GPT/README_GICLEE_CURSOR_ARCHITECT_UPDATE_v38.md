# Giclee Cursor Architect — v38 update

## v38 update (2026-07-10)

**v3.8** = v3.7 + **GPT Git Branch Implementation Mode** + mapa remotes monorepo + bezpieczny import theme (`gpt`) i GicleeApp (`gicleeapp`) + lokalna walidacja przed finalnym commitem.

### Co nowego

1. **`GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v38.md`** — główne Instructions z rozdziałem GPT GIT BRANCH IMPLEMENTATION MODE (tryby A/B, wybór trybu, architektura Git, guardrails brancha, pliki runtime).
2. **`GPT_GIT_BRANCH_WORKFLOW.md`** — praktyczny przewodnik: import, diff, test, akceptacja, rollback, checklisty, format raportu GPT (Base SHA + Commit SHA obowiązkowe dla GicleeApp).
3. **`GICLEE_CURSOR_MASTER_INDEX_v38.md`** — hierarchia v3.8, link do workflow branch.
4. **`GICLEE_CURSOR_ARCHITECT_CLEAN_PACK_v38.md`** — manifest aktywnych plików paczki.
5. **`README_GICLEE_CURSOR_ARCHITECT_UPDATE_v38.md`** — ten plik.

**Bez zmian:** guardrails Shopify/GicleeApp, dual-repo routing v3.5, snapshot review workflow, motion/effects, tryby analityczne i Shopify v1.

---

## Jak użyć (Custom GPT)

### Pole Instructions

Wklej zawartość:

**`GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v38.md`**

### Pliki wiedzy (Knowledge)

Dodaj **aktywne pliki v3.8** (patrz `GICLEE_CURSOR_ARCHITECT_CLEAN_PACK_v38.md`):

**Routing / workflow / checkpoint:**
- `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v38.md`
- `GPT_GIT_BRANCH_WORKFLOW.md`
- `GICLEE_DUAL_REPO_REVIEW_ROUTING_v35.md`
- `GICLEE_GITHUB_SNAPSHOT_REVIEW_WORKFLOW_v35.md`
- `GICLEE_CURSOR_MASTER_INDEX_v38.md`
- `CURRENT_APP_STATE.md`

**Motion / effects / patterns** — bez zmian wersji (patrz CLEAN_PACK v38).

**Analyst modes** — `GICLEE_ANALYST_*_v1.md` (patrz CLEAN_PACK v38).

**Shopify modes** — `GICLEE_SHOPIFY_MODE_*_v1.md` (patrz CLEAN_PACK v38).

### GitHub connector

Podłącz prywatne repo review/implementacji (wg zakresu zadania):

- `eagleblastmusic-lgtm/gicleeart-gpt` (remote lokalny: `gpt`)
- `eagleblastmusic-lgtm/gicleeapp` (remote lokalny: `gicleeapp`)

Implementacja na branchu: `gpt-work/<task-slug>`. **Main/master nietknięte** bez jednoznacznego polecenia.

Nie używaj publicznych URL-i ani `raw.githubusercontent.com`.

---

## Zasada: Cursor nie generuje ZIP

- **Cursor** aktualizuje tylko pliki źródłowe w `Pliki startowe dla GPT/`.
- **ZIP wiedzy** (`giclee_cursor_architect_knowledge_v38.zip`) generuje program użytkownika przy wysyłce przez **Okno rozmowy** (Integracja z GPT).
- Cursor **nie** uruchamia `build_starter_knowledge_zip()` bez osobnego polecenia.

---

## Komenda: Aktualizuj pliki startowe

Pełna definicja: sekcja **KOMENDA ROBOCZA** w `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v38.md`.

Przy samym checkpoint refresh: aktualizuj `CURRENT_APP_STATE.md` i metadane **v38** — **nie bumpuj** na v39 bez realnej zmiany struktury instrukcji.

---

## Nie dodawać do finalnego ZIP (archiwum)

Stare compact instructions (v37 i wcześniejsze), stare MASTER_INDEX / CLEAN_PACK / README — patrz **CLEAN_PACK v38** § ARCHIWALNE.

---

## Poprzednia wersja

**v3.7** pozostaje na dysku jako archiwum historyczne. Szczegóły release v3.7: `README_GICLEE_CURSOR_ARCHITECT_UPDATE_v37.md`.
