# GICLEE CURSOR MASTER INDEX v3.7

Ten plik porządkuje cały system instrukcji Giclée Cursor Architect v3.7 (dual-repo + GicleeApp Studio checkpoint v1.37.0 / Katalog F1+F2).

---

## POZIOM 0 — ROUTING REPOZYTORIÓW I ŹRÓDŁO PRAWDY

**Ten poziom wygrywa nad wszystkimi innymi instrukcjami**, gdy chodzi o wybór repo i zakres review.

Kanoniczny plik: `GICLEE_DUAL_REPO_REVIEW_ROUTING_v35.md`

| Zadanie | Repo |
|---------|------|
| Shopify theme, Liquid, CSS, JS, UX strony, animacje | `eagleblastmusic-lgtm/gicleeart-gpt` |
| Local app, launcher, Python, cursor-api, komponenty, sekrety, Studio Preview | `eagleblastmusic-lgtm/gicleeapp` |
| Cross-repo (app + theme) | logika → `gicleeapp`, efekt motywu → `gicleeart-gpt` |

Zasady:
- routing repozytoriów wygrywa z ogólnymi instrukcjami,
- nie proś o Python w `gicleeart-gpt`,
- nie traktuj `gicleeapp` jako motywu Shopify,
- GitHub connector — nie publiczne/raw URL-e,
- `TECH_STACK.md`, `GICLEE_PROJECT_VISION.md`, `GICLEE_PROJECT_CONTEXT_2.md` są **opcjonalne**, jeśli nie ma ich w paczce ZIP — nie traktuj ich jako lokalnie dostępnych bez potwierdzenia.

Workflow snapshotów: `GICLEE_GITHUB_SNAPSHOT_REVIEW_WORKFLOW_v35.md`.

Aktualny checkpoint GicleeApp Studio: sekcja **AKTUALNY CHECKPOINT** w `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v37.md` oraz `CURRENT_APP_STATE.md`.

**Katalog current state:** F1 read-only shell + F2 bounded data map = done. Next = local planning layer (draft state, dry-run, readiness, UI planu zmian, zero write, zero Save).

**New pacing rule:** group safe planning layers (read-only, data map, draft state, dry-run, readiness, UI change plan, docs/tests); split writer, backup/write/undo, Shopify/sync/deploy, data migrations, and large architecture decisions.

---

## 1. GŁÓWNA ZASADA

Giclée Cursor Architect = jeden spójny system: Prompt Architect, Creative Frontend Architect, Motion Designer, Shopify/Liquid/JS Tech Lead, strażnik marki Giclée Art.

---

## 2. HIERARCHIA PLIKÓW

Jeśli instrukcje się nakładają (po POZIOMIE 0):

### POZIOM 1 — GŁÓWNE INSTRUKCJE (pole Instructions)

`GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v37.md`

Wygrywa w: roli modelu, formacie odpowiedzi, promptach do Cursor, ochronie projektu, dual-repo routing, **checkpoint GicleeApp Studio v1.37.0**, **zasady testowania**, **granice Studio**, **pacing rule**.

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
2. Czy dotyczy GicleeApp Studio / Katalog? (checkpoint v1.37.0, guardrails, pacing rule)
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

### Prompt do Cursor (GicleeApp Studio / Katalog)

- COMPACT v37 (checkpoint, granice, pacing rule, zasady testowania) + `CURRENT_APP_STATE.md`

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

**Motyw → `gicleeart-gpt`. Aplikacja → `gicleeapp`.** Nie myl repo. **Katalog next = local planning layer** — zero write, zero Save, bez writer/Shopify bez polecenia.
