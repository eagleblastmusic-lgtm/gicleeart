# GICLEE ANALYST — LESSONS LEARNED

Trwałe lekcje i antywzorce. Przykłady historyczne oznaczaj **`HISTORICAL`** — nie traktuj ich jako bieżącego stanu repo.

---

## Antywzorce

- Nie retry'uj częściowo utworzonego obiektu Tk.
- Nie wykonuj blind rerun po failure CI.
- Nie zakładaj, że `windows-latest` oznacza ten sam system.
- Nie uznawaj zielonego smoke za dowód stabilności całego suite.
- Nie merge'uj bez odczytu artifactów **i** bez autoryzacji użytkownika.
- Nie dąż mechanicznie do inventory = 0.
- Nie whitelistuj globalnie helpera wyłącznie na podstawie jego nazwy.
- Nie migruj danych przed sklasyfikowaniem ich własności.
- Nie twórz ogromnego PR-a obejmującego kilka niezależnych granic.
- Nie zostawiaj tymczasowego workflowu ani patchera w finalnym diffie.
- Nie używaj force-pusha do synchronizacji brancha.
- Nie kopiuj starych SHA i wersji do głównych Instructions.
- Nie dopisuj nowego checkpointu bez usunięcia lub oznaczenia sprzecznego starego.
- Nie traktuj automatycznie wygenerowanego ZIP v38 jako źródła prawdy v39.
- Nie importuj ciężkiego package root w teście granicy modułu (importuj najmniejszy potrzebny moduł).
- Nie traktuj user workspace jak cache do czyszczenia, migracji ani scalania.
- **Produkcja może być dobra, a stabilization zła** — osobny kontrakt testów i allowlista.
- **Masowe patchery testów maskują ownership** — punktowa migracja zależnych testów.
- **Full suite loop** — max 2 szerokie przebiegi bez postępu; potem STOP.
- **Sprawdzaj faktyczny plik** — raport agenta ≠ dowód; pusty plik = blocker.
- **Kontrolowany retry joba** — tylko po artifact analysis i klasyfikacji środowiskowej.
- **Makro-etapy zamiast mikrozarządzania** — patrz [GICLEE_AUTONOMOUS_ENGINEERING_PIPELINE_v1.md](GICLEE_AUTONOMOUS_ENGINEERING_PIPELINE_v1.md).

---

## Sprawdzone dobre praktyki

- Jeden spójny pakiet odpowiedzialności na PR.
- Wczesny draft PR.
- Focused tests przed Full baseline.
- Hermetic w draft.
- Ready dopiero po zielonym Hermetic.
- Failure oznacza powrót do draftu.
- Artifacty są dowodem; status UI jest tylko sygnałem.
- Expected inventory delta ustalana przed zmianą.
- Dokumentacja trwałego kontraktu w tym samym PR.
- Dynamiczne override'y są częścią kompatybilności.
- Legacy domyślnie pozostaje read-only fallbackiem.
- Finalny merge z exact `expected_head_sha` po autoryzacji użytkownika.
- Po merge ponownie odczytać master.

---

## Lesson: Opcjonalne zależności w testach

Problem:
Test granicy modułu importował cały pakiet, którego `__init__.py` ładował opcjonalny `numpy`, nieobecny celowo w Full baseline.

Wrong approach:
Import package root zamiast najmniejszego modułu granicznego; dodawanie opcjonalnej zależności do baseline tylko po to, by test przeszedł.

Invariant:
Test granicy powinien importować najmniejszy potrzebny moduł, a nie ciężki package root.

Regression proof:
Po izolowanym załadowaniu modułu granicznego (np. `paths.py`) Full baseline przechodzi bez dodawania zależności.

Starter-file destination:
[GICLEE_ANALYST_LESSONS_LEARNED_v1.md](GICLEE_ANALYST_LESSONS_LEARNED_v1.md); powiązane tryby CI/debug.

---

## Lesson: User workspace nie jest cache'em

Problem:
Dane robocze użytkownika (zdjęcia testowe, pary kalibracyjne, raporty) mogą zostać błędnie potraktowane jako cache aplikacji podlegający auto-czyszczeniu lub migracji.

Wrong approach:
Automatyczne usuwanie, scalanie lub migracja katalogów workspace bez jawnej procedury i zgody użytkownika.

Invariant:
Dane `test_photos`, `ww_pairs`, raporty i własne pliki użytkownika są workspace'em. Nie wolno ich automatycznie usuwać, scalać ani migrować jako cache.

Regression proof:
Workspace Safety utrzymuje jawne ścieżki użytkownika i domyślne katalogi poza checkout bez auto-migracji legacy.

Starter-file destination:
[GICLEE_ANALYST_MODE_RUNTIME_DATA_OWNERSHIP_v1.md](GICLEE_ANALYST_MODE_RUNTIME_DATA_OWNERSHIP_v1.md)

---

## Lesson: Zapis ustawień i writer źródłowy to osobne akcje

Problem:
Zwykły przycisk Zapisz mógłby po cichu zmieniać śledzony plik motywu zamiast zapisywać wyłącznie wariant lub ustawienia panelu.

Wrong approach:
Łączenie zapisu ustawień z zapisem do pliku motywu w jednej akcji bez preview, diffu i jawnej autoryzacji.

Invariant:
Zwykłe `Zapisz` nie może cicho zmieniać śledzonego pliku motywu. Bezpieczny writer wymaga osobnej akcji z pełnym kontraktem Writer Safety.

Regression proof:
Writer Safety contract: plan bez zapisu, exact target, diff, SHA przed/po, stale-state check, jawna fraza, backup poza repo, atomic write, weryfikacja końcowego SHA.

Starter-file destination:
[GICLEE_ANALYST_MODE_WRITER_EXPORT_SAFETY_v1.md](GICLEE_ANALYST_MODE_WRITER_EXPORT_SAFETY_v1.md)

---

## Lesson: False positives bez wyciszania policy

Problem:
Runtime jest bezpieczny, lecz składnia lub wzorzec wywołania jest nieczytelny dla analizatora — licznik inventory pokazuje false positive.

Wrong approach:
Allowlista pliku, global suppression, osłabienie reguły analizatora lub ukrywanie wywołań przed skanerem wyłącznie po to, by spaść do zera.

Invariant:
Gdy runtime jest bezpieczny, lecz składnia nieczytelna dla analizatora, wprowadź semantyczną granicę (np. nazwany store `settings/db/changelog`). Nie stosuj allowlisty pliku, globalnego suppression, osłabienia reguły ani ukrywania wywołań.

Regression proof:
Semantyczna granica store + testy graniczne; inventory spada bez whitelistowania helperów `_write_path` / `_write_json`.

Starter-file destination:
[GICLEE_ANALYST_MODE_RUNTIME_DATA_OWNERSHIP_v1.md](GICLEE_ANALYST_MODE_RUNTIME_DATA_OWNERSHIP_v1.md); [GICLEE_ANALYST_LESSONS_LEARNED_v1.md](GICLEE_ANALYST_LESSONS_LEARNED_v1.md)

---

## Szablon Lesson

```md
## Lesson: <krótki tytuł>

Problem:
Co faktycznie było przyczyną?

Wrong approach:
Jakie podejście nie zadziałało albo było ryzykowne?

Invariant:
Jaka trwała zasada powinna obowiązywać od teraz?

Regression proof:
Jaki test, artifact albo kontrakt udowadnia poprawność?

Starter-file destination:
Do którego pliku startowego ta wiedza powinna zostać dopisana?
```

---

## Przykład HISTORICAL — Tk initialization retry

**Status: HISTORICAL** — ilustruje invariant, nie bieżący run CI.

Problem:
Late Full baseline failure after partial `_tkinter.create(...)`.

Wrong approach:
Retrying `Tk.__init__` on the same object.

Invariant:
Never retry initialization on a partially initialized Tk instance.

Regression proof:
Blocking Tk GUI smoke, same-runner warm-up and two complete green Full baseline runs before merge.

Starter-file destination:
`GICLEE_ANALYST_MODE_GITHUB_PR_CI_v1.md`

---

## Mapowanie destination

| Temat | Plik |
|-------|------|
| PR / CI / merge / Tcl/Tk | `GICLEE_ANALYST_MODE_GITHUB_PR_CI_v1.md` |
| Runtime ownership / inventory | `GICLEE_ANALYST_MODE_RUNTIME_DATA_OWNERSHIP_v1.md` |
| Export / Shopify writer | `GICLEE_ANALYST_MODE_WRITER_EXPORT_SAFETY_v1.md` |
| Cross-repo | `GICLEE_ANALYST_MODE_CROSS_REPO_COORDINATOR_v1.md` |
| Handoff sesji | `GICLEE_ANALYST_MODE_HANDOFF_CONTINUITY_v1.md` |
| Roadmapa refaktoru / kolejność etapów | [GICLEE_PROJECT_REFACTOR_ROADMAP_v2.md](GICLEE_PROJECT_REFACTOR_ROADMAP_v2.md) |
| Konstytucja modelu | `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v40.md` |
| Bieżący stan | `CURRENT_APP_STATE.md` |
