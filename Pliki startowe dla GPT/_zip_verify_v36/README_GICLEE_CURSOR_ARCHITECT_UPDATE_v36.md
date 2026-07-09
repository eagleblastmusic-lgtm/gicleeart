# Giclee Cursor Architect — v36 update

v36 updates the startup knowledge after GicleeApp Studio F3/F3.2.1.1.

Added:
- current canonical checkpoint: `gicleeapp` HEAD `92866ec`
- F3/F3.1/F3.2/F3.2.1/F3.2.1.1 status
- GitHub Actions CI status and security fix context
- targeted testing rules for Cursor commands
- warning to prefer Python 3.11/3.12 for GUI tests, not broken Python 3.14/Tk
- known non-blocking issue: `stronaglowna TclError` as possible F3.2.2
- F4 explicitly not started

---

v3.5 = dual-repo routing po utworzeniu `eagleblastmusic-lgtm/gicleeapp`.  
v3.6 = checkpoint F3/F3.2.1.1 + zasady testowania + granice Studio w instrukcjach compact.

---

## Co nowego

1. **`GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v36.md`** — Instructions z checkpointem, routingiem, granicami Studio i zasadami testowania
2. **`GICLEE_CURSOR_MASTER_INDEX_v36.md`** — hierarchia v3.6, główny plik instrukcji = COMPACT v36
3. **`README_GICLEE_CURSOR_ARCHITECT_UPDATE_v36.md`** — ten plik
4. **`GICLEE_CURSOR_ARCHITECT_CLEAN_PACK_v36.md`** — manifest v3.6
5. **`CURRENT_APP_STATE.md`** — zaktualizowany stan po F3/F3.2.1.1

Bez zmian wersji (nadal v3.5 / v3.x): dual-repo routing, snapshot workflow, motion/effects.

---

## Jak użyć (Custom GPT)

### Pole Instructions

Wklej zawartość:

**`GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v36.md`**

### Pliki wiedzy (Knowledge)

Dodaj **aktywne pliki v3.6** (patrz `GICLEE_CURSOR_ARCHITECT_CLEAN_PACK_v36.md`):

**Routing / workflow / checkpoint:**
- `GICLEE_DUAL_REPO_REVIEW_ROUTING_v35.md`
- `GICLEE_GITHUB_SNAPSHOT_REVIEW_WORKFLOW_v35.md`
- `GICLEE_CURSOR_MASTER_INDEX_v36.md`
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

Stare README, stare compact instructions (v35 i wcześniejsze), pełne `INSTRUCTIONS_v3.md` — patrz **CLEAN_PACK v36**.

---

## Następny krok (poza tym update)

Zaktualizować **`Wiadomość początkowa.txt`** — dual-repo routing + checkpoint Studio F3/F3.2.1.1.
