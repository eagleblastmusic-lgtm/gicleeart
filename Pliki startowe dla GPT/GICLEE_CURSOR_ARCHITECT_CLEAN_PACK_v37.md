# GICLEE CURSOR ARCHITECT — CLEAN PACK v3.7

Manifest plików wiedzy Custom GPT. **Stare pliki na dysku nie są usuwane** — ten dokument mówi, co włożyć do finalnego ZIP-a.

---

## AKTYWNE — do finalnego ZIP-a

### Routing i instrukcje v3.7

| Plik | Rola |
|------|------|
| `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v37.md` | **Źródło do pola Instructions** (v3.7: checkpoint v1.37.0 / 16febff, Katalog F1+F2, pacing rule, routing, granice Studio) |
| `GICLEE_DUAL_REPO_REVIEW_ROUTING_v35.md` | Kanon dual-repo |
| `GICLEE_GITHUB_SNAPSHOT_REVIEW_WORKFLOW_v35.md` | Workflow review snapshotów |
| `GICLEE_CURSOR_MASTER_INDEX_v37.md` | Hierarchia (POZIOM 0), wskazuje COMPACT v37 |
| `README_GICLEE_CURSOR_ARCHITECT_UPDATE_v37.md` | Instrukcja wdrożenia v3.7 |
| `GICLEE_CURSOR_ARCHITECT_CLEAN_PACK_v37.md` | Ten manifest |
| `CURRENT_APP_STATE.md` | Aktualny stan GicleeApp Studio v1.37.0 |

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

**Razem aktywne: 19 plików** (7 routing/instructions v37 + 12 motion/effects).

**Generated ZIP name:** `giclee_cursor_architect_knowledge_v37.zip`

---

## ARCHIWALNE — nie dodawać do finalnego ZIP-a

Te pliki mogą **mieszać routing** (single-repo, stare wersje, duplikaty Instructions):

| Plik | Powód |
|------|--------|
| `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v36.md` | zastąpione przez v37 |
| `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v35.md` | zastąpione przez v37 |
| `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v34.md` | zastąpione przez v37 |
| `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_8000.md` | stary compact |
| `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_v3.md` | pełna wersja, brak dual-repo |
| `GICLEE_GITHUB_SNAPSHOT_REVIEW_WORKFLOW_v34.md` | zastąpione przez v35 |
| `GICLEE_CURSOR_MASTER_INDEX_v32.md` | zastąpione przez v37 |
| `GICLEE_CURSOR_MASTER_INDEX_v35.md` | zastąpione przez v37 |
| `GICLEE_CURSOR_MASTER_INDEX_v36.md` | zastąpione przez v37 |
| `README_GICLEE_CURSOR_ARCHITECT_UPDATE_v35.md` | zastąpione przez v37 |
| `README_GICLEE_CURSOR_ARCHITECT_UPDATE_v36.md` | zastąpione przez v37 |
| `README_GICLEE_CURSOR_ARCHITECT_UPDATE_v34.md` | zastąpione przez v37 |
| `GICLEE_CURSOR_ARCHITECT_CLEAN_PACK_v35.md` | zastąpione przez v37 |
| `GICLEE_CURSOR_ARCHITECT_CLEAN_PACK_v36.md` | zastąpione przez v37 |
| `README_GICLEE_CURSOR_ARCHITECT_FINAL_v33.md` | stary README |
| `README_GICLEE_CURSOR_ARCHITECT_v31.md` | stary README |
| `README_GICLEE_CURSOR_ARCHITECT_v3.md` | stary README |
| `Załączam pliki wiedzy…txt` | stara wiadomość startowa (archiwum) |

---

## POZA ZIP-em (osobno, nie Knowledge)

| Plik | Uwaga |
|------|--------|
| `Wiadomość początkowa.txt` | **Do aktualizacji** — dual-repo routing + checkpoint Studio v1.37.0 |

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

Master Index v37 traktuje je jako opcjonalne.

---

## Wersja

**v3.7** = v3.6 + checkpoint Studio v1.37.0 / 16febff + Katalog F1+F2 done + local planning layer next + pacing rule (group safe layers, split writer/Shopify/migrations)
