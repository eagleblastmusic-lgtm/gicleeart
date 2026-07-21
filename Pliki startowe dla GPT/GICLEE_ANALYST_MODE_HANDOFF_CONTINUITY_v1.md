# TRYB HANDOFF / CONTINUITY

Ciągłość pracy między oknami rozmowy i sesjami Custom GPT.

Stosuj razem z: [GICLEE_AUTONOMOUS_ENGINEERING_PIPELINE_v1.md](GICLEE_AUTONOMOUS_ENGINEERING_PIPELINE_v1.md), COMPACT v40 § Autonomous Engineering Model.

---

## Na starcie nowej sesji — takeover audit

**Przed pierwszą edycją** wykonaj takeover audit:

1. Główny plik Instructions: `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v40.md`
2. `CURRENT_APP_STATE.md` — § Current repository state (per repo)
3. Pipeline: `GICLEE_AUTONOMOUS_ENGINEERING_PIPELINE_v1.md`
4. Dostępne tryby analityczne
5. Repozytoria wymagane dla zadania
6. Aktualny stan GitHub przez connector (lub lokalny `git ls-remote` / raport użytkownika)
7. Różnice między checkpointem w pliku a bieżącym kodem

Potwierdź użytkownikowi:

- główny plik Instructions,
- aktualny checkpoint per repo,
- aktualny GitHub master/main (jeśli zweryfikowany),
- otwarte lub oczekujące PR-y,
- obecny następny etap **per tor** (nazwa toru + data weryfikacji),
- najważniejsze guardraile,
- status integracji ZIP oraz ewentualne rozbieżności manifestu

Następnie czekaj na konkretne zadanie.

---

## Obowiązkowy checkpoint (handoff / model-switch)

Przed przełączeniem modelu, końcem sesji lub po makro-etapie zapisz:

```text
branch
HEAD
status (--short)
name-status (git diff --name-status)
stat / numstat
ukończony zakres
zielone testy (exact commands + wynik)
czerwone nodeids (jeśli są)
root cause (jeśli failure)
pozostałe zadania
zakazane działania
```

Checkpoint wykonuj automatycznie w tle — nie przerywaj pracy użytkownikowi mikrozarządzaniem.

---

## Na zakończeniu większego etapu

Obowiązkowa reguła w konstytucji: COMPACT v40 § Obowiązkowe zakończenie większego etapu lub okna.

Pełny protokół: [GICLEE_PROJECT_REFACTOR_ROADMAP_v2.md](GICLEE_PROJECT_REFACTOR_ROADMAP_v2.md) §5.

Krótki raport handoff:

```md
## Handoff

Repository:
Branch / PR:
Head SHA:
Co zamknięte:
Co otwarte:
Następny etap (tor + data):
Guardraile:
Artifacty / testy:
Pliki startowe do aktualizacji:
```

---

## Rozróżnienie typów wiedzy

| Typ | Gdzie trafia |
|-----|----------------|
| Trwała lekcja | COMPACT, moduły analyst, LESSONS |
| Bieżący checkpoint | `CURRENT_APP_STATE.md` per repo |
| Historia zamkniętego PR | `CURRENT_APP_STATE.md` lub LESSONS jako HISTORICAL |
| Roadmapa / kolejność etapów | [GICLEE_PROJECT_REFACTOR_ROADMAP_v2.md](GICLEE_PROJECT_REFACTOR_ROADMAP_v2.md) |
| Tymczasowa hipoteza | tylko w rozmowie; nie do Instructions |

---

## Protokół Lesson (skrót)

Po większym etapie — wpis 5-pól: Problem, Wrong approach, Invariant, Regression proof, Starter-file destination.

Pełny szablon: `GICLEE_ANALYST_LESSONS_LEARNED_v1.md`.
