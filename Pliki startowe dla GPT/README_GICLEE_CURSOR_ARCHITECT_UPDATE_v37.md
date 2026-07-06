# Giclee Cursor Architect — v37 update

## v37 update

- Updates current checkpoint to GicleeApp Studio v1.37.0.
- Sets canonical HEAD / origin/master to 16febff71dd2aad397f6c35ff8b8eef896abbb49.
- Marks Background Builder local v1 as frozen.
- Marks Administracja strony rebuild strategy as done.
- Marks Katalog rebuild plan, F1 read-only shell, and F2 bounded data map as done.
- Sets next recommended phase to Katalog local planning layer.
- Adds pacing rule: group safe planning layers; split writer, Shopify, migrations, and major architecture decisions.

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

Zaktualizowane pliki: `CURRENT_APP_STATE.md`, checkpoint block w COMPACT v37, `GICLEE_CURSOR_MASTER_INDEX_v37.md`, ten README, `Wiadomość początkowa.txt`. Przebuduj `giclee_cursor_architect_knowledge_v37.zip` z generatora projektu.

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
| 4 | — | Przebudowuje ZIP przez generator |
| 5 | — | Raport: `git status -sb`, `git diff --stat`, lista plików |

GPT **nie implementuje** feature aplikacji. Nie miesza maintenance z writerem, Shopify/sync/deploy, Push GicleeApp ani runtime cleanupem.

### Checklista (typowy prompt do Cursora)

1. Zaktualizuj `CURRENT_APP_STATE.md` (checkpoint, SHA, fazy, next).
2. Zsynchronizuj checkpoint w COMPACT v37, MASTER_INDEX, CLEAN_PACK, ten README — **bez bumpu v38**.
3. Przebuduj `giclee_cursor_architect_knowledge_v37.zip` z generatora.
4. Nie dotykaj runtime dirty; nie `git add -A`; nie push; nie commit bez raportu.
5. Osobny commit docs po akceptacji raportu.

---

## Co nowego

1. **`GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v37.md`** — Instructions z checkpointem v1.37.0, routingiem, granicami Studio/Katalog, pacing rule i zasadami testowania
2. **`GICLEE_CURSOR_MASTER_INDEX_v37.md`** — hierarchia v3.7, główny plik instrukcji = COMPACT v37
3. **`README_GICLEE_CURSOR_ARCHITECT_UPDATE_v37.md`** — ten plik
4. **`GICLEE_CURSOR_ARCHITECT_CLEAN_PACK_v37.md`** — manifest v3.7
5. **`CURRENT_APP_STATE.md`** — zaktualizowany stan Studio v1.37.0

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

Zaktualizować **`Wiadomość początkowa.txt`** — dual-repo routing + checkpoint Studio v1.37.0 + pacing rule.
