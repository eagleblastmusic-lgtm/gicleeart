# GICLEE CURSOR ARCHITECT — CLEAN PACK v3.8

Manifest plików wiedzy Custom GPT. **Stare pliki na dysku nie są usuwane** — ten dokument mówi, co włożyć do finalnego ZIP-a.

---

## AKTYWNE — do finalnego ZIP-a

### Routing i instrukcje v3.8

| Plik | Rola |
|------|------|
| `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v38.md` | **Źródło do pola Instructions** (v3.8: GPT Git Branch Mode, mapa remotes, bezpieczny import) |
| `GPT_GIT_BRANCH_WORKFLOW.md` | Procedura branch GPT, import theme/GicleeApp, checklisty, raport |
| `GICLEE_DUAL_REPO_REVIEW_ROUTING_v35.md` | Kanon dual-repo |
| `GICLEE_GITHUB_SNAPSHOT_REVIEW_WORKFLOW_v35.md` | Workflow review snapshotów |
| `GICLEE_CURSOR_MASTER_INDEX_v38.md` | Hierarchia (POZIOM 0), wskazuje COMPACT v38 |
| `README_GICLEE_CURSOR_ARCHITECT_UPDATE_v38.md` | Instrukcja wdrożenia v3.8 |
| `GICLEE_CURSOR_ARCHITECT_CLEAN_PACK_v38.md` | Ten manifest |
| `CURRENT_APP_STATE.md` | Aktualny stan GicleeApp Studio + checkpointy proceduralne |
| `GICLEEAPP_STUDIO_2_0_MODULE_TEMPLATE.md` | Sztywny szablon modułów GicleeApp Studio 2.0 |

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

**Razem aktywne: 39 plików** (9 routing/instructions v38 + 12 motion/effects + 9 analyst modes + 9 Shopify modes).

**Generated ZIP name:** `giclee_cursor_architect_knowledge_v38.zip`

**Repo-dokument GicleeApp (poza ZIP-em, w monorepo):** `cursor-api/docs/GICLEEAPP_IMPLEMENTED_SOLUTIONS_INDEX.md` — przy zadaniach komponentowych Cursor/GPT **musi** go sprawdzić przed nowym komponentem/helperem i zaktualizować po dodaniu reużywalnego mechanizmu (jak `gicleeframe-planning.md` — referencja repo, nie plik paczki ZIP).

---

## ARCHIWALNE — nie dodawać do finalnego ZIP-a

Te pliki mogą **mieszać routing** (single-repo, stare wersje, duplikaty Instructions):

| Plik | Powód |
|------|--------|
| `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v37.md` | zastąpione przez v38 |
| `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v36.md` | zastąpione przez v38 |
| `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v35.md` | zastąpione przez v38 |
| `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v34.md` | zastąpione przez v38 |
| `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_8000.md` | stary compact |
| `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_v3.md` | pełna wersja, brak dual-repo |
| `GICLEE_GITHUB_SNAPSHOT_REVIEW_WORKFLOW_v34.md` | zastąpione przez v35 |
| `GICLEE_CURSOR_MASTER_INDEX_v37.md` | zastąpione przez v38 |
| `GICLEE_CURSOR_MASTER_INDEX_v36.md` | zastąpione przez v38 |
| `GICLEE_CURSOR_MASTER_INDEX_v35.md` | zastąpione przez v38 |
| `GICLEE_CURSOR_MASTER_INDEX_v32.md` | zastąpione przez v38 |
| `README_GICLEE_CURSOR_ARCHITECT_UPDATE_v37.md` | zastąpione przez v38 |
| `README_GICLEE_CURSOR_ARCHITECT_UPDATE_v36.md` | zastąpione przez v38 |
| `README_GICLEE_CURSOR_ARCHITECT_UPDATE_v35.md` | zastąpione przez v38 |
| `README_GICLEE_CURSOR_ARCHITECT_UPDATE_v34.md` | zastąpione przez v38 |
| `GICLEE_CURSOR_ARCHITECT_CLEAN_PACK_v37.md` | zastąpione przez v38 |
| `GICLEE_CURSOR_ARCHITECT_CLEAN_PACK_v36.md` | zastąpione przez v38 |
| `GICLEE_CURSOR_ARCHITECT_CLEAN_PACK_v35.md` | zastąpione przez v38 |
| `README_GICLEE_CURSOR_ARCHITECT_FINAL_v33.md` | stary README |
| `README_GICLEE_CURSOR_ARCHITECT_v31.md` | stary README |
| `README_GICLEE_CURSOR_ARCHITECT_v3.md` | stary README |
| `Załączam pliki wiedzy…txt` | stara wiadomość startowa (archiwum) |

---

## POZA ZIP-em (osobno, nie Knowledge)

| Plik | Uwaga |
|------|--------|
| `Wiadomość początkowa.txt` | Osobno od ZIP — aktualizuj z bieżącego lokalnego checkpointu; nie zakładaj starej wersji z archiwum |

---

## Maintenance paczki wiedzy

**Źródło prawdy:** pliki `.md` w `C:\Strona\pusty\Pliki startowe dla GPT` (ten folder).

**ZIP:** `giclee_cursor_architect_knowledge_v38.zip` to **output programu użytkownika** — nie edytuj ZIP-a ręcznie ani nie traktuj go jako źródła prawdy.

**Regeneracja ZIP (tylko użytkownik):** automatycznie przy wysyłce przez **Okno rozmowy** (Integracja z GPT). Implementacja: `build_starter_knowledge_zip()` w `cursor-api/Komponenty/integracjagpt/zip_knowledge.py` — **Cursor tego nie uruchamia** bez osobnego polecenia.

**Komenda użytkownika:** „Aktualizuj pliki startowe” — patrz COMPACT v38. GPT → prompt; Cursor → edycja źródeł + raport git. **Bez ZIP z Cursora.**

**Checkpoint refresh:** aktualizuj `CURRENT_APP_STATE.md` i powiązane metadane v38; **nie bumpuj** na v39 przy samym odświeżeniu checkpointu.

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

Master Index v38 traktuje je jako opcjonalne.

---

## Wersja

**v3.8** = v3.7 + GPT Git Branch Implementation Mode + mapa remotes monorepo + bezpieczny import theme i GicleeApp + lokalna walidacja przed finalnym commitem + `GPT_GIT_BRANCH_WORKFLOW.md`

**v3.7** = v3.6 + checkpoint Studio v1.37.0 / 16febff + Katalog F1+F2 done + local planning layer next + pacing rule (group safe layers, split writer/Shopify/migrations)

**Checkpoint refresh 2026-07-06:** Studio v1.38.0 / monorepo 65e862b / gicleeapp main a056bb5 / Katalog F3+F4 done / next = bounded writer after separate acceptance. Paczka nadal v3.7 — bez bumpu na v38.

**Checkpoint refresh 2026-07-06 (post Push GicleeApp):** project checkpoint `4760a29` / Studio code `65e862b` / gicleeapp snapshot `21bc3ed` / GPT starter refreshed / primary next = GICLÉE FRAME™. Bez wiązania docs z `origin/master`. Paczka nadal v3.7.

**Checkpoint refresh 2026-07-06 (post F2.1):** HEAD / origin/master `4647c1b` / GicleeApp Studio **v1.40.1** / GICLÉE FRAME F2.1 **done** + **Studio Page Component Editor Pattern** / next = **(A)** hygiene working tree **or (B)** GICLÉE FRAME F3 (not started). Paczka nadal v3.7 — bez bumpu na v38.

**Checkpoint refresh 2026-07-07 (Studio Performance 5F–6G.2):** fazy performance done lokalnie w Cursorze; źródło prawdy diagnozy = `giclee_app/logs/studio_perf.log`; zasada: metryki przed kodem; GitHub connector może być za lokalnym working tree. Paczka nadal v3.7 — bez bumpu na v38.

**Checkpoint refresh 2026-07-07 (Studio Performance 6G.5 closure):** główna nitka **6G.5** **PASS / checkpoint**; aktualny stan w `CURRENT_APP_STATE.md`; przy nowych objawach — najpierw `studio_perf.log` / raport Cursora, bez szerokiej optymalizacji bez objawu. Paczka nadal v3.7 — bez bumpu na v38.

**Checkpoint refresh 2026-07-07 (Performance Agent PA-1C.2):** PA-1A–PA-1C.2 **done** w `cursor-api/tools/performance_agent/`; lokalny commit `c966912`; testy 46/46 PASS; push pending; preferuj bundle `report.md`/`summary.json` nad surowym logiem; `SCENARIO_LOG_NOT_CONFIRMED` = jakość sesji; nie startować PA-1D bez prośby. Paczka nadal v3.7 — bez bumpu na v38.

**Checkpoint refresh 2026-07-07 (GitHub app v1.41.2):** aktualna wersja aplikacji na GitHub **v1.41.2**; monorepo origin/master `845191c`; F2.1 historycznie `4647c1b` v1.40.1; PA lokalnie `c966912` push pending. Paczka nadal v3.7 — bez bumpu na v38.

**Checkpoint refresh 2026-07-08 (GV-7 + GAS 2.0 template):** Giclee Viewer GitHub `eagleblastmusic-lgtm/giclee-viewer` · HEAD `26446ce487d6fe1a511c7c137215834c78b6849f` — GV-7 **done** (143/143 tests); next GV-8; nowy `GICLEEAPP_STUDIO_2_0_MODULE_TEMPLATE.md`; GAS-0 future direction. Paczka nadal v3.7 — bez bumpu na v38.

**Checkpoint refresh 2026-07-08 (architecture principles):** nowe sekcje § Programming / Architecture Principles + § Current technical lessons from Giclee Viewer w COMPACT v37 i `CURRENT_APP_STATE.md` — praktyczne zasady C# / WPF + Python + SQLite/JSON dla przyszłych aplikacji lokalnych. Paczka nadal v3.7 — bez bumpu na v38.

**Checkpoint refresh 2026-07-08 (strategic direction):** nowe sekcje § Strategic Direction — Giclée Art Studio OS + § Work Planning Rule + § UI / Product Taste Direction w COMPACT v37 i `CURRENT_APP_STATE.md` — kierunek ekosystemu, tempo prac i estetyka produktu dla nowych sesji GPT. Paczka nadal v3.7 — bez bumpu na v38.

**Checkpoint refresh 2026-07-08 (source of truth / decision memory):** nowa sekcja § Source of Truth / Decision Memory w COMPACT v37 i `CURRENT_APP_STATE.md` — GV ≠ GAS 2.0, lokalne pliki ≠ ZIP, szablon modułów, decyzja C#/Python, roadmapa, checkpoint startowy sesji. Paczka nadal v3.7 — bez bumpu na v38.

**Checkpoint refresh 2026-07-11 (launcher / patch safety / FAQ effects):** monorepo `2dde9e4`; lokalne markery v1.50.0 są dirty po HEAD; launcher categories/options/shortcuts/DnD zaakceptowany; WinAPI shortcuts = trwała decyzja; patch w PowerShell przez `--output`; oba cross-repo `--check` przed apply; FAQ `image_effect_selector` / `targetSelector` pending validation; Home Flow/prehero chronione przed szerokim cleanupem. Paczka nadal **v3.8** — bez bumpu na v39.

## Analyst mode extension

Paczka zawiera dodatkowy zestaw trybów analitycznych `GICLEE_ANALYST_*_v1.md`.

Ich celem jest rozszerzenie głównych Instructions v38 o specjalizowane sposoby pracy:

- performance,
- debug/regresja,
- review implementacji Cursora,
- architektura etapów,
- UI/UX premium,
- Shopify snapshot review,
- GPT integration / ZIP workflow,
- Veo / Flow / image-video prompt director.

Tryby nie zastępują głównych Instructions. Należy stosować je razem z `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v38.md` oraz aktualnym `CURRENT_APP_STATE.md`.

Przy zadaniach komponentowych GicleeApp sprawdź repo-dokument `cursor-api/docs/GICLEEAPP_IMPLEMENTED_SOLUTIONS_INDEX.md` (poza ZIP-em).

### Analyst modes (v1)

| Plik |
|------|
| `GICLEE_ANALYST_BASE_PROMPT_v1.md` |
| `GICLEE_ANALYST_MODE_PERFORMANCE_v1.md` |
| `GICLEE_ANALYST_MODE_DEBUG_REGRESSION_v1.md` |
| `GICLEE_ANALYST_MODE_CURSOR_REVIEW_v1.md` |
| `GICLEE_ANALYST_MODE_STAGE_ARCHITECT_v1.md` |
| `GICLEE_ANALYST_MODE_UI_UX_PREMIUM_v1.md` |
| `GICLEE_ANALYST_MODE_SHOPIFY_SNAPSHOT_v1.md` |
| `GICLEE_ANALYST_MODE_GPT_ZIP_INTEGRATION_v1.md` |
| `GICLEE_ANALYST_MODE_VEO_FLOW_IMAGE_VIDEO_PROMPT_DIRECTOR_v1.md` |

### Shopify modes (v1)

| Plik |
|------|
| `GICLEE_SHOPIFY_MODE_HOMEPAGE_ART_DIRECTION_v1.md` |
| `GICLEE_SHOPIFY_MODE_PRODUCT_PAGE_PDP_v1.md` |
| `GICLEE_SHOPIFY_MODE_COLLECTION_CATALOG_v1.md` |
| `GICLEE_SHOPIFY_MODE_COPY_BRAND_STORY_v1.md` |
| `GICLEE_SHOPIFY_MODE_MOTION_INTERACTION_v1.md` |
| `GICLEE_SHOPIFY_MODE_CONVERSION_TRUST_v1.md` |
| `GICLEE_SHOPIFY_MODE_RESPONSIVE_ACCESSIBILITY_v1.md` |
| `GICLEE_SHOPIFY_MODE_SEO_CONTENT_v1.md` |
| `GICLEE_SHOPIFY_MODE_TRANSLATION_MARKETS_v1.md` |

## Shopify mode extension

Paczka zawiera dodatkowy zestaw trybów Shopify `GICLEE_SHOPIFY_MODE_*_v1.md`. Ich celem jest rozszerzenie głównych Instructions v38 oraz Shopify Snapshot workflow o specjalizowane sposoby pracy dla strony Giclée Art:

- homepage art direction,
- product page / PDP,
- collection / catalog,
- copy / brand story,
- motion / interaction,
- conversion / trust,
- responsive / accessibility,
- SEO / content,
- translation / markets.

Tryby Shopify nie zastępują głównych Instructions. Należy stosować je razem z `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v38.md`, aktualnym `CURRENT_APP_STATE.md` oraz trybem Shopify Snapshot.
