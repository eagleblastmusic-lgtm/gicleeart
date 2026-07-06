# GICLEE CURSOR ARCHITECT — CLEAN PACK v3.7

Manifest plików wiedzy Custom GPT. **Stare pliki na dysku nie są usuwane** — ten dokument mówi, co włożyć do finalnego ZIP-a.

---

## AKTYWNE — do finalnego ZIP-a

### Routing i instrukcje v3.7

| Plik | Rola |
|------|------|
| `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v37.md` | **Źródło do pola Instructions** (v3.7: Studio v1.40.1 / 4647c1b, GICLÉE FRAME F2.1 done, pattern, next A/B) |
| `GICLEE_DUAL_REPO_REVIEW_ROUTING_v35.md` | Kanon dual-repo |
| `GICLEE_GITHUB_SNAPSHOT_REVIEW_WORKFLOW_v35.md` | Workflow review snapshotów |
| `GICLEE_CURSOR_MASTER_INDEX_v37.md` | Hierarchia (POZIOM 0), wskazuje COMPACT v37 |
| `README_GICLEE_CURSOR_ARCHITECT_UPDATE_v37.md` | Instrukcja wdrożenia v3.7 |
| `GICLEE_CURSOR_ARCHITECT_CLEAN_PACK_v37.md` | Ten manifest |
| `CURRENT_APP_STATE.md` | Aktualny stan GicleeApp Studio v1.40.1 |

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
| `Wiadomość początkowa.txt` | Osobno od ZIP — checkpoint Studio v1.40.1 |

---

## Maintenance paczki wiedzy

**Źródło prawdy:** pliki `.md` w `C:\Strona\pusty\Pliki startowe dla GPT` (ten folder).

**ZIP:** `giclee_cursor_architect_knowledge_v37.zip` to **output programu użytkownika** — nie edytuj ZIP-a ręcznie ani nie traktuj go jako źródła prawdy.

**Regeneracja ZIP (tylko użytkownik):** automatycznie przy wysyłce przez **Okno rozmowy** (Integracja z GPT). Implementacja: `build_starter_knowledge_zip()` w `cursor-api/Komponenty/integracjagpt/zip_knowledge.py` — **Cursor tego nie uruchamia** bez osobnego polecenia.

**Komenda użytkownika:** „Aktualizuj pliki startowe” — patrz COMPACT v37. GPT → prompt; Cursor → edycja źródeł + raport git. **Bez ZIP z Cursora.**

**Checkpoint refresh:** aktualizuj `CURRENT_APP_STATE.md` i powiązane metadane v37; **nie bumpuj** na v38 przy samym odświeżeniu checkpointu.

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

**Checkpoint refresh 2026-07-06:** Studio v1.38.0 / monorepo 65e862b / gicleeapp main a056bb5 / Katalog F3+F4 done / next = bounded writer after separate acceptance. Paczka nadal v3.7 — bez bumpu na v38.

**Checkpoint refresh 2026-07-06 (post Push GicleeApp):** project checkpoint `4760a29` / Studio code `65e862b` / gicleeapp snapshot `21bc3ed` / GPT starter refreshed / primary next = GICLÉE FRAME™. Bez wiązania docs z `origin/master`. Paczka nadal v3.7.

**Checkpoint refresh 2026-07-06 (post F2.1):** HEAD / origin/master `4647c1b` / GicleeApp Studio **v1.40.1** / GICLÉE FRAME F2.1 **done** + **Studio Page Component Editor Pattern** / next = **(A)** hygiene working tree **or (B)** GICLÉE FRAME F3 (not started). Paczka nadal v3.7 — bez bumpu na v38.
