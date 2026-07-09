# GICLEE CURSOR ARCHITECT UPDATE v3.5

Update **dual-repo workflow**: `gicleeart-gpt` (motyw) + `gicleeapp` (aplikacja lokalna).

v3.4 = workflow snapshot motywu.  
v3.5 = dual-repo routing po utworzeniu `eagleblastmusic-lgtm/gicleeapp`.

---

## Co nowego

1. **`GICLEE_DUAL_REPO_REVIEW_ROUTING_v35.md`** — kanoniczny routing dwóch repo
2. **`GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v35.md`** — Instructions z sekcją DUAL-REPO ROUTING
3. **`GICLEE_GITHUB_SNAPSHOT_REVIEW_WORKFLOW_v35.md`** — workflow motywu + mini-workflow `gicleeapp`
4. **`GICLEE_CURSOR_MASTER_INDEX_v35.md`** — POZIOM 0 routing wygrywa nad resztą
5. **`GICLEE_CURSOR_ARCHITECT_CLEAN_PACK_v35.md`** — lista aktywnych vs archiwalnych plików

---

## Jak użyć (Custom GPT)

### Pole Instructions

Wklej zawartość:

**`GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v35.md`**

(plik ≤ 8000 znaków, z sekcją DUAL-REPO ROUTING)

### Pliki wiedzy (Knowledge)

Dodaj **aktywne pliki v3.5** (patrz `GICLEE_CURSOR_ARCHITECT_CLEAN_PACK_v35.md`):

**Routing / workflow:**
- `GICLEE_DUAL_REPO_REVIEW_ROUTING_v35.md`
- `GICLEE_GITHUB_SNAPSHOT_REVIEW_WORKFLOW_v35.md`
- `GICLEE_CURSOR_MASTER_INDEX_v35.md`

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

Stare README, stare compact instructions, pełne `INSTRUCTIONS_v3.md` — patrz **CLEAN_PACK v35**.

---

## Następny krok (poza tym update)

Zaktualizować **`Wiadomość początkowa.txt`** — obecnie wskazuje tylko `gicleeart-gpt`; po v3.5 powinna zawierać dual-repo routing.
