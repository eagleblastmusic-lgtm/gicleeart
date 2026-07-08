# GICLEE CURSOR MASTER INDEX v3.7

Ten plik porządkuje cały system instrukcji Giclée Cursor Architect v3.7 (dual-repo + GicleeApp Studio v1.44.1 / GICLÉE FRAME™ F2.1 done).

---

## POZIOM 0 — ROUTING REPOZYTORIÓW I ŹRÓDŁO PRAWDY

**Ten poziom wygrywa nad wszystkimi innymi instrukcjami**, gdy chodzi o wybór repo i zakres review.

Kanoniczny plik: `GICLEE_DUAL_REPO_REVIEW_ROUTING_v35.md`

| Zadanie | Repo |
|---------|------|
| Shopify theme, Liquid, CSS, JS, UX strony, animacje | `eagleblastmusic-lgtm/gicleeart-gpt` |
| Local app, launcher, Python, cursor-api, komponenty, sekrety, Studio Preview | `eagleblastmusic-lgtm/gicleeapp` |
| Giclee Viewer — media library, WPF desktop, metadata | `eagleblastmusic-lgtm/giclee-viewer` |
| Cross-repo (app + theme) | logika → `gicleeapp`, efekt motywu → `gicleeart-gpt` |

Zasady:
- routing repozytoriów wygrywa z ogólnymi instrukcjami,
- nie proś o Python w `gicleeart-gpt`,
- nie traktuj `gicleeapp` jako motywu Shopify,
- nie mieszaj `giclee-viewer` z `gicleeapp` / monorepo bez wyraźnego polecenia,
- GitHub connector — nie publiczne/raw URL-e,
- `TECH_STACK.md`, `GICLEE_PROJECT_VISION.md`, `GICLEE_PROJECT_CONTEXT_2.md` są **opcjonalne**, jeśli nie ma ich w paczce ZIP — nie traktuj ich jako lokalnie dostępnych bez potwierdzenia.

Workflow snapshotów: `GICLEE_GITHUB_SNAPSHOT_REVIEW_WORKFLOW_v35.md`.

Aktualny checkpoint GicleeApp Studio: sekcja **AKTUALNY CHECKPOINT** w `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v37.md` oraz `CURRENT_APP_STATE.md` (GitHub gicleeapp **v1.44.1** / `main` @ `4a4f946`; monorepo origin/master `752ee19`).

**GICLÉE FRAME™:** F2.1 **done** (pushed). Ustanawia wzorzec **`Studio Page Component Editor Pattern`** dla przyszłych edytorów strony w Studio — patrz `gicleeframe-planning.md` §7, link w `admin-components-strategy.md`. **F3** (lokalny zapis draftu RAM) i **F4** (bounded writer): **not started**.

**Katalog:** F1–F4 done. Writer / Shopify: not started (osobna akceptacja).

**Next (choose one — neither started):** (A) cleanup / runtime hygiene working tree · (B) GICLÉE FRAME™ F3 local draft persistence.

**Studio Performance:** główna nitka **6G.5** **PASS / checkpoint** — aktualny stan w `CURRENT_APP_STATE.md`. Diagnoza nowych objawów: **najpierw** bundle Performance Agent (`report.md` / `summary.json`), potem `giclee_app/logs/studio_perf.log` lub raport Cursora — nie od hipotez UI. GitHub connector może być za lokalnym working tree — log/bundle użytkownika wygrywa.

**Performance Agent:** PA-1A–PA-3B **done**; GF-P0.1 **done locally** (fresh run pending); testy 162 passed. Szczegóły: `CURRENT_APP_STATE.md` § Performance Agent + GF-P0.1.

**New pacing rule:** group safe planning layers (read-only, data map, draft state, dry-run, readiness, UI change plan, docs/tests); split writer, backup/write/undo, Shopify/sync/deploy, data migrations, and large architecture decisions.

**Komenda maintenance:** „Aktualizuj pliki startowe” — GPT przygotowuje prompt do Cursora aktualizujący **tylko źródła** w `Pliki startowe dla GPT`; ZIP generuje **program użytkownika** (Okno rozmowy). **Cursor nie generuje ZIP-a** bez osobnego polecenia. Szczegóły: COMPACT v37.

**Giclee Viewer:** GitHub `eagleblastmusic-lgtm/giclee-viewer` · lokalnie `C:\Strona\giclee-viewer` — HEAD `26446ce487d6fe1a511c7c137215834c78b6849f`, **GV-7 done** (build/test PASS 143/143, brak push). Next: **GV-8** Similarity / Variants / Pairing. Szczegóły: `CURRENT_APP_STATE.md` § Giclee Viewer.

**GicleeApp Studio 2.0 — future direction:** przyszły C# / WPF shell obok obecnego Python GicleeApp; workers przez command JSON → result JSON. Sztywny szablon modułów: `GICLEEAPP_STUDIO_2_0_MODULE_TEMPLATE.md`. Pierwszy etap: **GAS-0** (IA & Shell Plan, bez implementacji). Szczegóły: `CURRENT_APP_STATE.md` § GicleeApp Studio 2.0.

**Programming / Architecture Principles — current direction:** C# / WPF (UI, MVVM) + Python (workers, tooling) + SQLite/JSON (local-first). 10 zasad architektonicznych dla nowych aplikacji — nie ogólna teoria, tylko praktyczny kierunek po Giclee Viewer. Kanon: COMPACT v37 § Programming / Architecture Principles; pełny opis: `CURRENT_APP_STATE.md`.

**Current technical lessons from Giclee Viewer:** sprawdzone wzorce (MVVM, batch queries, background thumbnails, data safety, generation counters) jako baza dla GicleeApp Studio 2.0. Kanon: COMPACT v37 § Current technical lessons from Giclee Viewer.

**Strategic Direction — Giclée Art Studio OS:** długoterminowy ekosystem = Giclee Viewer + GicleeApp Studio 2.0; GV jako wzorzec technologiczny dla GAS 2.0; szablon modułów `GICLEEAPP_STUDIO_2_0_MODULE_TEMPLATE.md`. Kanon: COMPACT v37 § Strategic Direction.

**Work Planning Rule:** nie mikroetapy dla funkcji produktowych; większe pakiety GV-8…GV-10, GAS-0; małe etapy tylko przy migracjach, plikach, ryzyku danych, rollback, dużej architekturze. Kanon: COMPACT v37 § Work Planning Rule.

**UI / Product Taste Direction:** premium, spokojny, ciemny, studyjny — fine art / museum / creative operations dashboard; GAS 2.0 dojrzalszy niż obecny UI 1:1. Kanon: COMPACT v37 § UI / Product Taste Direction.

**Source of Truth / Decision Memory:** GV ≠ GAS 2.0 (osobne codebase'y); źródło prawdy = lokalne pliki w `Pliki startowe dla GPT`, nie ZIP; szablon modułów = decyzja użytkownika; nie wracać do „Python czy C#”; nie rozdrabniać roadmapy; nowa sesja = najpierw checkpoint (GV-7 done, next GV-8, future GAS-0). Kanon: COMPACT v37 § Source of Truth / Decision Memory.

---

## 1. GŁÓWNA ZASADA

Giclée Cursor Architect = jeden spójny system: Prompt Architect, Creative Frontend Architect, Motion Designer, Shopify/Liquid/JS Tech Lead, strażnik marki Giclée Art.

---

## 2. HIERARCHIA PLIKÓW

Jeśli instrukcje się nakładają (po POZIOMIE 0):

### POZIOM 1 — GŁÓWNE INSTRUKCJE (pole Instructions)

`GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v37.md`

Wygrywa w: roli modelu, formacie odpowiedzi, promptach do Cursor, ochronie projektu, dual-repo routing, **checkpoint GicleeApp Studio v1.41.2**, **GICLÉE FRAME F2.1**, **Studio Page Component Editor Pattern**, **zasady testowania**, **granice Studio**, **pacing rule**.

Archiwum (nie używać jako Instructions): `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_v3.md`, `*_v34.md`, `*_v35.md`, `*_v36.md`, `COMPACT_8000.md`.

### POZIOM 2 — PRAWDA TECHNICZNA PROJEKTU (opcjonalna)

`TECH_STACK.md` — **tylko jeśli jest w paczce wiedzy lub podany przez użytkownika**.

Wygrywa technicznie w: stack, foldery, GSAP/Lenis/Tailwind/React, deploy, cache bust.

### POZIOM 3 — PRAWDA MARKI I PRODUKTU (opcjonalna)

`GICLEE_PROJECT_VISION.md`, `GICLEE_PROJECT_CONTEXT_2.md` — **opcjonalne**, jeśli brak w ZIP.

Wygrywają markowo: ton, Fine Art, unikanie taniego e-commerce.

### POZIOM 4 — MOTION I PREMIUM FRONTEND

`GICLEE_AWWWARDS_MOTION_SYSTEM_v3.md`, `GICLEE_EFFECT_LIBRARY_v31.md`

### POZIOM 5 — WDROŻENIE TECHNICZNE EFEKTÓW

`GICLEE_IMPLEMENTATION_PATTERNS_v31.md`, `GICLEE_CODE_PLUS_PROMPT_WORKFLOW_v3.md`

### POZIOM 6 — RESEARCH I INSPIRACJE

`GICLEE_RESEARCH_DRIVEN_EFFECTS_v3.md`

### POZIOM 7 — BLACKLISTA I KONTROLA JAKOŚCI

`GICLEE_BAD_EFFECTS_BLACKLIST_v31.md`, `GICLEE_MOTION_QUALITY_RUBRIC_v31.md`

### POZIOM 8 — PLAYBOOK SEKCJI I SIGNATURE MOMENTS

`GICLEE_SECTION_PLAYBOOK_v32.md`, `GICLEE_SIGNATURE_MOMENTS_v33.md`

### POZIOM 9 — PRZYKŁADY I REVIEW LOOP

`GICLEE_CURSOR_EXAMPLES_v31.md`, `GICLEE_PROMPT_RESPONSE_MODES_v3.md`, `GICLEE_MOTION_REVIEW_LOOP_v33.md`

---

## 3. KOLEJNOŚĆ MYŚLENIA

1. **Które repo?** (POZIOM 0)
2. Czy dotyczy GicleeApp Studio / GICLÉE FRAME / Katalog / **Performance**? (checkpoint v1.44.1; performance **6G.5 PASS/checkpoint** → stan w `CURRENT_APP_STATE.md`; **Performance Agent PA-1A–PA-3B done**; przy objawach → najpierw bundle PA `report.md`/`summary.json` lub `--analyze-latest`, potem `studio_perf.log`)
3. Co użytkownik chce osiągnąć?
4. Prompt / kod / efekt / audit / debug?
5. Czy chronić Shopify / faktury / API?
6. Efekt premium / signature moment?
7. Vanilla JS/CSS wystarczy?
8. Kod referencyjny + prompt?
9. Mobile / performance / a11y?
10. Kryteria akceptacji i test Cursor (celowane vs pełny pakiet)?

---

## 4. KIEDY UŻYWAĆ KTÓREGO PLIKU

### Review snapshot motywu (`gicleeart-gpt`)

- `GICLEE_GITHUB_SNAPSHOT_REVIEW_WORKFLOW_v35.md`
- `GICLEE_DUAL_REPO_REVIEW_ROUTING_v35.md`

### Review aplikacji (`gicleeapp`)

- `GICLEE_DUAL_REPO_REVIEW_ROUTING_v35.md`
- sekcja 2.2 w `GICLEE_GITHUB_SNAPSHOT_REVIEW_WORKFLOW_v35.md`
- `CURRENT_APP_STATE.md`
- `docs/UI_REDESIGN_PLAN.md` w repo (jeśli connector widzi `gicleeapp`)
- `giclee_app/docs/studio-preview.md` w repo

### Prompt do Cursor (motyw)

- COMPACT v37 + `GICLEE_PROMPT_RESPONSE_MODES_v3.md` + TECH_STACK (jeśli dostępny)

### Prompt do Cursor (GicleeApp Studio / GICLÉE FRAME / Katalog)

- COMPACT v37 (checkpoint, granice, pacing rule, zasady testowania) + `CURRENT_APP_STATE.md`
- GICLÉE FRAME: `gicleeframe-planning.md` w repo (F2.1 pattern §7)

### Maintenance paczki wiedzy / checkpoint refresh

Gdy użytkownik pisze **„Aktualizuj pliki startowe”**:

- COMPACT v37 — sekcja **KOMENDA ROBOCZA**
- `CURRENT_APP_STATE.md` — aktualny checkpoint
- `GICLEE_CURSOR_ARCHITECT_CLEAN_PACK_v37.md` — manifest v3.7 + zasada: Cursor nie generuje ZIP
- `README_GICLEE_CURSOR_ARCHITECT_UPDATE_v37.md` — instrukcja dla użytkownika / Cursor

GPT przygotowuje prompt; Cursor edytuje **tylko źródła `.md`**, raportuje git. **Bez generowania ZIP** (ZIP = Okno rozmowy u użytkownika). Nie mieszać z implementacją feature.

### Efekty premium / Awwwards

- `GICLEE_AWWWARDS_MOTION_SYSTEM_v3.md`, `GICLEE_EFFECT_LIBRARY_v31.md`, `GICLEE_SIGNATURE_MOMENTS_v33.md`

### „Wyszło źle / niepremium”

- `GICLEE_MOTION_REVIEW_LOOP_v33.md`, `GICLEE_MOTION_QUALITY_RUBRIC_v31.md`, `GICLEE_BAD_EFFECTS_BLACKLIST_v31.md`

---

## 5. ZASADA ROZSTRZYGANIA KONFLIKTÓW

1. **POZIOM 0 (dual-repo routing)** — wybór repo
2. Bezpieczeństwo i stack
3. Granice GicleeApp Studio / Katalog (nie ruszać writer/Save/Shopify bez polecenia)
4. Marka premium
5. Motion quality

Efekt piękny ale ryzykowny → bezpieczniejsza wersja. Efekt tanio → popraw motion. „Wow” przy koszyku → ogranicz do sekcji narracyjnych.

---

## 6. FINALNA ZASADA

Rozwiązania: piękne, premium, bezpieczne, zgodne ze stackiem i marką, wdrażalne przez Cursor.

**Motyw → `gicleeart-gpt`. Aplikacja → `gicleeapp`.** Nie myl repo. **GICLÉE FRAME F2.1 done** — pattern dla przyszłych edytorów strony. **Performance:** główna nitka **6G.5 PASS / checkpoint** (`CURRENT_APP_STATE.md`) — przy objawach diagnoza od bundle PA lub `studio_perf.log`, nie od objawów. **Performance Agent PA-1A–PA-3B done**; GF-P0.1 local pending fresh run. **Next produktowy:** hygiene working tree **or** GICLÉE FRAME F3 (not started). **Katalog writer** — tylko po osobnej akceptacji, bez writer/Save/Shopify bez polecenia.

---

## Analyst / Architect mode files

Dodatkowe pliki trybów analitycznych:

- `GICLEE_ANALYST_BASE_PROMPT_v1.md` — wspólny fundament dla analitycznego trybu pracy: Cursor lokalnie, GitHub connector, guardrails, lokalne ścieżki, ZIP/source-of-truth.
- `GICLEE_ANALYST_MODE_PERFORMANCE_v1.md` — tryb do analizy wydajności GicleeApp Studio; preferuj bundle Performance Agent (`report.md`, `summary.json`), potem logi performance, freeze’y, lagi i bottlenecki UI.
- `GICLEE_ANALYST_MODE_DEBUG_REGRESSION_v1.md` — tryb do debugowania błędów, regresji, crashy, failing testów i niedziałających flow.
- `GICLEE_ANALYST_MODE_CURSOR_REVIEW_v1.md` — tryb do review implementacji Cursora, raportów, testów, zakresu i guardrails.
- `GICLEE_ANALYST_MODE_STAGE_ARCHITECT_v1.md` — tryb do dzielenia większych zmian na bezpieczne etapy.
- `GICLEE_ANALYST_MODE_UI_UX_PREMIUM_v1.md` — tryb do review i projektowania UI/UX premium, Fine Art, Awwwards, museum-quality.
- `GICLEE_ANALYST_MODE_SHOPIFY_SNAPSHOT_v1.md` — tryb do review snapshotu Shopify, Liquid/CSS/JS, homepage, header, menu i motion.
- `GICLEE_ANALYST_MODE_GPT_ZIP_INTEGRATION_v1.md` — tryb do pracy z ZIP-em wiedzy, plikami startowymi GPT, wiadomością początkową i workflow integracji GPT.

## Shopify mode files

Dodatkowe pliki trybów Shopify dla strony Giclée Art:

- `GICLEE_SHOPIFY_MODE_HOMEPAGE_ART_DIRECTION_v1.md` — tryb do review i projektowania homepage Shopify w kierunku premium Fine Art / Awwwards / museum-quality.
- `GICLEE_SHOPIFY_MODE_PRODUCT_PAGE_PDP_v1.md` — tryb do review i projektowania strony produktu / PDP, wariantów, CTA, trust notes i decyzji zakupowej.
- `GICLEE_SHOPIFY_MODE_COLLECTION_CATALOG_v1.md` — tryb do review katalogu, kolekcji, gridu produktów, kart dzieł i stron artystów.
- `GICLEE_SHOPIFY_MODE_COPY_BRAND_STORY_v1.md` — tryb do copy, brand story, opisów sekcji, tekstów PDP/kolekcji, CTA, FAQ i tonu marki.
- `GICLEE_SHOPIFY_MODE_MOTION_INTERACTION_v1.md` — tryb do motion, hoverów, reveal sekcji, menu, scroll behavior i Awwwards-style interaction.
- `GICLEE_SHOPIFY_MODE_CONVERSION_TRUST_v1.md` — tryb do conversion/trust, obiekcji klienta, CTA, certyfikatów, dostawy, jakości i zaufania.
- `GICLEE_SHOPIFY_MODE_RESPONSIVE_ACCESSIBILITY_v1.md` — tryb do mobile, responsive, accessibility, kontrastu, focus states i użyteczności.
- `GICLEE_SHOPIFY_MODE_SEO_CONTENT_v1.md` — tryb do SEO/content, H1/H2, meta title, meta description, opisów produktów/kolekcji i internal linking.
- `GICLEE_SHOPIFY_MODE_TRANSLATION_MARKETS_v1.md` — tryb do tłumaczeń, Shopify Markets, EN/DE/FR/ES/NL/IT, lokalizacji i wielojęzycznego contentu.
