# GICLEE AUTONOMOUS ENGINEERING PIPELINE v1

Pełny system autonomicznej inżynierii dla monorepo `gicleeart`, Custom GPT i lokalnego Cursora.

Stosuj razem z: [GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v40.md](GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v40.md), [CURRENT_APP_STATE.md](CURRENT_APP_STATE.md), [GICLEE_ANALYST_MODE_GITHUB_PR_CI_v1.md](GICLEE_ANALYST_MODE_GITHUB_PR_CI_v1.md).

---

## Makro-etapy

| Makro-etap | Zakres |
|------------|--------|
| **IMPLEMENTATION** | discovery → exact-base → izolowany branch → implementacja pełnej granicy → boundary suite → punktowa migracja zależnych testów |
| **STABILIZATION** | focused tests → docs → selective staging → push → draft PR → niezależny exact-head review |
| **FINAL VALIDATION & SHIP** | draft Hermetic → ready canonical Tk + full baseline → artifact/JUnit/runtime inventory → kontrolowany retry → squash merge z `expected_head_sha` → post-merge reread master → aktualizacja starterów/handoff |

Nie rozbijaj pracy na mikrokroki wymagające akceptacji użytkownika między normalnymi krokami. Zatrzymaj się wyłącznie przy **anomalii**.

---

## Pipeline — 19 kroków

1. **Discovery** — repo, moduł, consumers, tests, manifest, guardrails.
2. **Exact-base i scope contract** — Base SHA, allowlista plików, expected inventory delta.
3. **Izolowany branch/worktree** — `gpt-work/<task-slug>`; single-writer worktree.
4. **Implementacja pełnej granicy** — jeden spójny pakiet odpowiedzialności.
5. **Boundary suite** — testy granicy modułu przed szerokim pytest.
6. **Punktowa migracja zależnych testów** — tylko testy dotknięte granicą; bez masowych patcherów.
7. **Focused tests** — nodeids / moduł / `-x --tb=short`.
8. **Jeden finalny szeroki przebieg** — full baseline tylko gdy focused green; max 2 bez postępu.
9. **Dokumentacja** — modułowy doc + checkpoint w `CURRENT_APP_STATE.md`.
10. **Selective staging** — jawne ścieżki; bez `git add -A`.
11. **Push i draft PR** — mały pierwszy commit jeśli potrzebny do otwarcia PR.
12. **Niezależny exact-head review** — diff, pliki, rozmiary, ownership; raport agenta ≠ dowód.
13. **Draft Hermetic** — szybki sygnał; failure → draft + artifact analysis.
14. **Ready canonical Tk + full baseline** — dopiero po zielonym Hermetic.
15. **Artifact/JUnit/runtime inventory** — obowiązkowy odczyt przed merge gate.
16. **Kontrolowany retry** — wyłącznie po klasyfikacji środowiskowej; tylko czerwony job; finalny artifact z exact head.
17. **Squash merge z `expected_head_sha`** — tylko przy autoryzacji użytkownika.
18. **Post-merge reread master** — nowy SHA przed kolejnym etapem.
19. **Aktualizacja starterów/handoff** — lokalne pliki startowe; ZIP = snapshot na osobne polecenie.

---

## Anomaly gates — STOP

Zatrzymaj się i raportuj anomalie, gdy:

- lokalny branch/HEAD nie odpowiada oczekiwaniom;
- istnieją niepowiązane dirty changes, których nie można bezpiecznie odseparować;
- aktywny manifest Knowledge nie zgadza się z CLEAN_PACK;
- występują sprzeczne źródła wersji;
- walidacja lub testy ujawniają produktowy blocker;
- bezpieczne wygenerowanie ZIP-a wymaga kasowania cudzej pracy.

Zakazane: `git reset --hard`, `git clean`, broad restore, force-push, masowe patchery, osłabianie testów.

---

## Full suite — anty-pętla

- Maksymalnie **2** pełne przebiegi suite bez mierzalnego postępu.
- Po drugim failure bez root cause: STOP, klasyfikacja product/test/environment/API, zmiana strategii lub eskalacja anomalii.
- Zakaz pełnego suite po każdej drobnej zmianie.

---

## Antyprzykład procesu (anonimowy — modularizacja host boundary)

**Kontekst:** poprawna produkcyjna ekstrakcja dużego mixinu do osobnego modułu.

**Błąd procesu (nie kodu produkcyjnego):**

1. Ekstrakcja produkcyjna zakończona poprawnie.
2. Migracja testów utraciła kontrolę — masowe patchery zamiast punktowej migracji.
3. Ponad 20 szerokich przebiegów full suite bez postępu.
4. Raportowany suite pusty lub niespójny z artifactem.
5. Odzyskanie: backup brancha, cleanup patcherów, punktowy pipeline (focused → jeden finalny full run → artifact review).

**Invariant:** produkcja może być dobra, a stabilization zła. Granica implementacji ≠ granica testów — obie wymagają osobnego kontraktu i allowlisty.

Szczegóły lekcji: [GICLEE_ANALYST_LESSONS_LEARNED_v1.md](GICLEE_ANALYST_LESSONS_LEARNED_v1.md).

---

## Powiązane moduły

| Temat | Plik |
|-------|------|
| PR / CI / merge | [GICLEE_ANALYST_MODE_GITHUB_PR_CI_v1.md](GICLEE_ANALYST_MODE_GITHUB_PR_CI_v1.md) |
| Debug / regresja | [GICLEE_ANALYST_MODE_DEBUG_REGRESSION_v1.md](GICLEE_ANALYST_MODE_DEBUG_REGRESSION_v1.md) |
| Review Cursora | [GICLEE_ANALYST_MODE_CURSOR_REVIEW_v1.md](GICLEE_ANALYST_MODE_CURSOR_REVIEW_v1.md) |
| Planowanie etapów | [GICLEE_ANALYST_MODE_STAGE_ARCHITECT_v1.md](GICLEE_ANALYST_MODE_STAGE_ARCHITECT_v1.md) |
| Handoff | [GICLEE_ANALYST_MODE_HANDOFF_CONTINUITY_v1.md](GICLEE_ANALYST_MODE_HANDOFF_CONTINUITY_v1.md) |
| Git branch workflow | [GPT_GIT_BRANCH_WORKFLOW.md](GPT_GIT_BRANCH_WORKFLOW.md) |
| Roadmapa | [GICLEE_PROJECT_REFACTOR_ROADMAP_v2.md](GICLEE_PROJECT_REFACTOR_ROADMAP_v2.md) |
