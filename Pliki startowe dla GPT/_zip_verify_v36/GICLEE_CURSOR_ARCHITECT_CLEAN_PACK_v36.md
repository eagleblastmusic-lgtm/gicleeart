# GICLEE CURSOR ARCHITECT — CLEAN PACK v3.6

Manifest plików wiedzy Custom GPT. **Stare pliki na dysku nie są usuwane** — ten dokument mówi, co włożyć do finalnego ZIP-a.

---

## AKTYWNE — do finalnego ZIP-a

### Routing i instrukcje v3.6

| Plik | Rola |
|------|------|
| `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v36.md` | **Źródło do pola Instructions** (v3.6: checkpoint F3/F3.2.1.1, routing, granice Studio, zasady testowania) |
| `GICLEE_DUAL_REPO_REVIEW_ROUTING_v35.md` | Kanon dual-repo |
| `GICLEE_GITHUB_SNAPSHOT_REVIEW_WORKFLOW_v35.md` | Workflow review snapshotów |
| `GICLEE_CURSOR_MASTER_INDEX_v36.md` | Hierarchia (POZIOM 0), wskazuje COMPACT v36 |
| `README_GICLEE_CURSOR_ARCHITECT_UPDATE_v36.md` | Instrukcja wdrożenia v3.6 |
| `GICLEE_CURSOR_ARCHITECT_CLEAN_PACK_v36.md` | Ten manifest |
| `CURRENT_APP_STATE.md` | Aktualny stan GicleeApp po F3/F3.2.1.1 |

### Motion / effects / patterns (aktualne, bez nowej wersji)

| Plik |
|------|
| `GICLEE_AWWWARDS_MOTION_SYSTEM_v3.md` |
| `GICLEE_BAD_EFFECTS_BLACKLIST_v31.md` |
| `GICLEE_CODE_PLUS_PROMPT_WORKFLOW_v3.md` |
| `GICLEE_CURSOR_EXAMPLES_v31.md` |
| `GICLEE_EFFECT_LIBRARY_v31.md` |
| `GICLEE_IMPLEMENTATION_PATTERNS_v31.md` |
| `GICLEE_MOTION_QUALITY_RUBRIC_v31.md` |
| `GICLEE_MOTION_REVIEW_LOOP_v33.md` |
| `GICLEE_PROMPT_RESPONSE_MODES_v3.md` |
| `GICLEE_RESEARCH_DRIVEN_EFFECTS_v3.md` |
| `GICLEE_SECTION_PLAYBOOK_v32.md` |
| `GICLEE_SIGNATURE_MOMENTS_v33.md` |

**Razem aktywne: 19 plików** (7 routing/instructions v36 + 12 motion/effects).

---

## ARCHIWALNE — nie dodawać do finalnego ZIP-a

Te pliki mogą **mieszać routing** (single-repo, stare wersje, duplikaty Instructions):

| Plik | Powód |
|------|--------|
| `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v35.md` | zastąpione przez v36 |
| `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v34.md` | zastąpione przez v36 |
| `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_8000.md` | stary compact |
| `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_v3.md` | pełna wersja, brak dual-repo |
| `GICLEE_GITHUB_SNAPSHOT_REVIEW_WORKFLOW_v34.md` | zastąpione przez v35 |
| `GICLEE_CURSOR_MASTER_INDEX_v32.md` | zastąpione przez v36 |
| `GICLEE_CURSOR_MASTER_INDEX_v35.md` | zastąpione przez v36 |
| `README_GICLEE_CURSOR_ARCHITECT_UPDATE_v35.md` | zastąpione przez v36 |
| `README_GICLEE_CURSOR_ARCHITECT_UPDATE_v34.md` | zastąpione przez v36 |
| `GICLEE_CURSOR_ARCHITECT_CLEAN_PACK_v35.md` | zastąpione przez v36 |
| `README_GICLEE_CURSOR_ARCHITECT_FINAL_v33.md` | stary README |
| `README_GICLEE_CURSOR_ARCHITECT_v31.md` | stary README |
| `README_GICLEE_CURSOR_ARCHITECT_v3.md` | stary README |
| `Załączam pliki wiedzy…txt` | stara wiadomość startowa (archiwum) |

---

## POZA ZIP-em (osobno, nie Knowledge)

| Plik | Uwaga |
|------|--------|
| `Wiadomość początkowa.txt` | **Do aktualizacji** — dual-repo routing + checkpoint Studio |

---

## Wykluczenia bezpieczeństwa (nigdy w ZIP)

- `.git/`, logi, runtime/temp
- `gpt_config.json`, `.shopify_session.json`
- `.env`, tokeny, hasła, OAuth

---

## Opcjonalne (poza standardowym ZIP)

Dodaj tylko jeśli świadomie dołączasz do Custom GPT:

- `TECH_STACK.md`
- `GICLEE_PROJECT_VISION.md`
- `GICLEE_PROJECT_CONTEXT_2.md`

Master Index v36 traktuje je jako opcjonalne.

---

## Wersja

**v3.6** = v3.5 (dual-repo) + checkpoint F3/F3.2.1.1 + zasady testowania + granice Studio
