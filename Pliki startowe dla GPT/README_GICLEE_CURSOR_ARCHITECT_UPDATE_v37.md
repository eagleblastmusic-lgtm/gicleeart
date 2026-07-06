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
