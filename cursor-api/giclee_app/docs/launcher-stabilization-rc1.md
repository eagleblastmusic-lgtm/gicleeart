# GicleeApp Launcher — Stabilization / Release Candidate 1

**Status kanoniczny:** automatyczna walidacja RC1 zakończona; manualny smoke Windows oczekuje  
**Repository:** `eagleblastmusic-lgtm/gicleeart`  
**Baza stabilizacji:** `master` @ `7e984794ea0b1ccda2529532ce6fc7bad2d5c0a3`  
**RC1 validated head:** `28af43b350a63ff2780b19689dccc49fe1d868a9`  
**PR:** #116  
**Data:** 2026-07-15

---

## 1. Rola tego dokumentu

Ten plik jest kanonicznym statusem zakończenia refaktoru launchera ETAP 4B i passu stabilizacyjnego RC1.

Nagłówki starszych kontraktów LC opisują stan z chwili ich tworzenia lub implementacji. W szczególności robocze teksty typu `awaiting exact review` albo `implementation revision in progress` są historycznym śladem procesu. Bieżący status należy odczytywać z tego dokumentu i ze scalonych pull requestów.

RC1 nie dodaje nowej architektury i nie rozpoczyna LC-7. Jego zadaniem jest:

- potwierdzenie finalnej kompozycji;
- zebranie dowodów CI;
- wskazanie granic własności;
- zamrożenie zakresu przed przejściem do Shopify;
- oddzielenie automatycznej walidacji od manualnego smoke testu Windows.

---

## 2. Status ETAPU 4B

**ETAP 4B jest architektonicznie zakończony.**

Ostatni pakiet, LC-6, został scalony przez PR #115 jako:

```text
master@7e984794ea0b1ccda2529532ce6fc7bad2d5c0a3
```

Kanoniczny package entrypoint:

```text
python -m giclee_app
  -> giclee_app.__main__
  -> giclee_app.launcher_app.main
  -> launcher.main(app_factory=LauncherApp)
```

Finalna klasa:

```python
LauncherApp is DragDropCategoryGicleeApp
```

Exact MRO pozostaje:

```text
DragDropCategoryGicleeApp
  -> OptionsCategoryGicleeApp
  -> StyledCategoryGicleeApp
  -> CategoryGicleeApp
  -> launcher.GicleeApp
  -> object
```

Studio pozostaje osobnym shellem:

```text
python -m giclee_app.studio_preview
```

---

## 3. Zamknięte pakiety architektoniczne

| Pakiet | Wynik |
|---|---|
| L-0 / LC-1 | jawny `app_factory`; brak runtime class replacement |
| LC-2 | navigation model, category renderer i grid placement |
| LC-3 | shortcut controller, WinAPI, Tk bindings oraz granice DnD |
| LC-4A | klasyczny subprocess launch adapter |
| LC-4B | neutralne, pojedyncze wywołanie buildera inline |
| LC-5 | scheduler dziewięciu usług tła |
| LC-6 | kanoniczny `LauncherApp` composition root |

Po LC-6 nie planuje się kolejnego pakietu architektonicznego launchera. Dalsze zmiany wymagają konkretnego błędu, wymagania produktu albo osobnego projektu.

---

## 4. Finalna odpowiedzialność modułów

### Composition i entrypoint

- `launcher_app.py` — kanoniczny finalny composition root;
- `__main__.py` — delegacja package entrypointu;
- `launcher.py` — bazowy shell klasycznego launchera i orchestration aplikacji.

### Warstwy klasycznego UI

- `category_launcher.py` — nawigacja kategorie → komponenty;
- `styled_category_launcher.py` — prezentacja kafelków;
- `options_category_launcher.py` — menu Opcje i skróty;
- `dragdrop_category_launcher.py` — gest DnD oraz reorder orchestration.

### Wydzielone adaptery i modele

- `category_navigation.py`;
- `category_renderer.py`;
- `launcher_grid_layout.py`;
- `launcher_shortcut_controller.py`;
- `launcher_shortcut_keys.py`;
- `launcher_windows_shortcuts.py`;
- `launcher_tk_shortcut_bindings.py`;
- `launcher_drag_geometry.py`;
- `launcher_drag_gesture.py`;
- `launcher_tk_drag_bindings.py`;
- `launcher_tk_drag_targets.py`;
- `launcher_tk_drag_feedback.py`;
- `launcher_tk_drag_auto_scroll.py`;
- `launcher_drag_category_persistence.py`;
- `launcher_drag_component_persistence.py`;
- `launcher_classic_subprocess.py`;
- `launcher_inline_builder.py`;
- `launcher_background_services.py`.

---

## 5. Status LC-5

LC-5 jest zakończony i scalony przez PR #103.

Kanoniczny squash commit:

```text
a64dce2030faf48cca4c28fb86249d9ea8014fe3
```

Zachowana semantyka:

- dziewięć usług startowych;
- exact registration order;
- osobny expected firing order;
- synchroniczny direct `auto_rescan`;
- recurrence dla Shopify, accounting, cure i social publisher;
- worker bodies i daemon threads pozostają w `GicleeApp`;
- leniwe importy `Komponenty` pozostają w callbackach;
- Studio nie importuje schedulera;
- brak timer IDs, cancellation, retry, jitter i backoff.

Roboczy nagłówek `awaiting exact review` w historycznym kontrakcie LC-5 nie jest bieżącym statusem projektu.

---

## 6. Status LC-6

LC-6 jest zakończony i scalony przez PR #115.

Kanoniczny squash commit:

```text
7e984794ea0b1ccda2529532ce6fc7bad2d5c0a3
```

Finalny wynik:

- `LauncherApp` jest aliasem finalnej klasy DnD;
- identity i MRO nie zmieniły się;
- package entrypoint deleguje przez `launcher_app.py`;
- entrypointy warstw pozostają dostępne diagnostycznie;
- Studio pozostaje niezależne;
- brak nowego DI containera, service locatora i dynamicznej kompozycji.

Roboczy nagłówek `implementation revision in progress after Stage 2 finding` w historycznym kontrakcie LC-6 nie jest bieżącym statusem projektu.

---

## 7. Dowód finalnej automatycznej walidacji LC-6

Finalny Stage 2 dla exact head:

```text
c9aa8ffb1a6da916074aa5c13193d03efef917c3
```

Wyniki:

- Hermetic smoke — success;
- Tk GUI smoke — success;
- full pytest baseline — `2799 passed, 1 skipped, 3 warnings`;
- JUnit — 2800 testów, 0 failures, 0 errors, 1 skipped;
- runtime-write inventory — 734 pliki Python, 0 parse errors, 0 findings;
- artifact digest — `sha256:c6f06300c05f9b39fbed482ff7f2e04f91dd983a8f42a9caa2497ca00fb4f7e0`;
- `behind_by=0`;
- brak review threads;
- exact pięcioplikowy diff;
- squash merge z `expected_head_sha`.

Pierwszy baseline LC-6 ujawnił:

1. przestarzałą asercję LC-1 dotyczącą bezpośredniego importu DnD — poprawioną w allowlistowanym teście;
2. niezależny brak `ttk/clamTheme.tcl` w mirrorze hosted runnera — bez regresji kodu, przy zielonym dedykowanym Tk GUI.

Poprawiony Stage 2 przeszedł bez retry.

---

## 8. Dowód automatycznej walidacji RC1

Stage 2 run:

```text
#448 / run 29436190423
```

Exact validated head:

```text
28af43b350a63ff2780b19689dccc49fe1d868a9
```

Wyniki:

- Hermetic smoke — success;
- Tk GUI smoke — success;
- full pytest baseline — `2799 passed, 1 skipped, 3 warnings`;
- JUnit — 2800 testów, 0 failures, 0 errors, 1 skipped;
- runtime-write inventory — 734 pliki Python, 0 parse errors, 0 findings;
- artifact digest — `sha256:cd3aad5a76f3596e9dd285acdef8a3af6ff4e216d4b7f0ecc6e32fe8a78341df`;
- retry — nie był potrzebny.

RC1 jest docs-only. Ten przebieg potwierdza, że finalny stan kodu po LC-6 pozostaje zielony niezależnie od implementacyjnego PR #115.

---

## 9. Znane właściwości CI

Hosted Windows runner sporadycznie nie odtwarza kompletnego mirrora Tcl/Tk. Obserwowane brakujące pliki obejmowały między innymi:

- `init.tcl`;
- `ttk/cursors.tcl`;
- `ttk/clamTheme.tcl`.

Klasyfikacja takiego failure wymaga zawsze:

1. sprawdzenia konkretnego logu;
2. potwierdzenia, że Hermetic i dedykowany Tk GUI są zielone;
3. sprawdzenia JUnit i listy faktycznie niedziałających testów;
4. najwyżej jednego diagnostycznie uzasadnionego retry.

Nie wolno automatycznie klasyfikować każdego błędu Tk jako infrastrukturalnego.

---

## 10. Automatyczne kryteria RC1

- [x] ETAP 4B LC-1 — LC-6 scalony;
- [x] kanoniczny `launcher_app.py` istnieje;
- [x] package entrypoint prowadzi przez `launcher_app.main`;
- [x] exact identity i MRO finalnej klasy zamrożone testami;
- [x] Studio pozostaje osobnym shellem;
- [x] Hermetic RC1 green;
- [x] Tk GUI RC1 green;
- [x] pełny pytest RC1 green;
- [x] JUnit bez failures/errors;
- [x] inventory bez findings;
- [x] brak otwartych PR-ów po merge LC-6;
- [x] brak migracji danych i zmian formatów runtime;
- [x] docs-only RC1 przeszedł pełny Stage 2;
- [x] RC1 jest gotowy do exact-head merge.

---

## 11. Manualny smoke Windows — wymagany przed oznaczeniem release-ready

Tego zestawu nie zastępuje sam CI. Należy wykonać lokalnie na docelowym komputerze Windows:

### Start i nawigacja

- [ ] uruchomić `python -m giclee_app`;
- [ ] potwierdzić splash i pokazanie ekranu kategorii;
- [ ] wejść do kategorii i wrócić przyciskiem;
- [ ] wrócić przez `Esc`, `Backspace` i `Alt+Left`;
- [ ] potwierdzić bezpieczny powrót z pustej/usuniętej kategorii.

### Kafelki i DnD

- [ ] przeciągnąć kategorię przed i za inną kategorię;
- [ ] przeciągnąć komponent przed i za inny komponent;
- [ ] potwierdzić auto-scroll przy krawędziach;
- [ ] zrestartować launcher i potwierdzić trwałość kolejności;
- [ ] potwierdzić, że zwykły klik bez drag nadal uruchamia komponent.

### Skróty

- [ ] przypisać literę, cyfrę i klawisz F1–F12;
- [ ] potwierdzić WinAPI polling na Windows;
- [ ] potwierdzić blokadę w Entry/Text/Combobox;
- [ ] potwierdzić blokadę w dialogu i inline;
- [ ] zmienić przypisanie i potwierdzić działanie bez restartu.

### Tryby uruchamiania

- [ ] otworzyć komponent inline i wrócić do właściwej kategorii;
- [ ] uruchomić komponent subprocess i sprawdzić log;
- [ ] otworzyć komponent URL;
- [ ] zamknąć launcher i potwierdzić, że subprocess pozostaje aktywny.

### Usługi tła

- [ ] potwierdzić brak błędów przy starcie schedulera;
- [ ] potwierdzić auto-rescan komponentów;
- [ ] sprawdzić logi Shopify/accounting/cure/social bez wymuszania zmian biznesowych;
- [ ] potwierdzić, że launcher pozostaje responsywny.

### Studio

- [ ] uruchomić `python -m giclee_app.studio_preview`;
- [ ] potwierdzić start CustomTkinter;
- [ ] otworzyć przykładowy inline view;
- [ ] potwierdzić brak uruchomienia klasycznych usług tła.

---

## 12. Kryterium przejścia do Shopify

Można rozpocząć właściwy refaktor Shopify po spełnieniu łącznie:

1. docs-only RC1 PR jest scalony;
2. automatyczny Stage 2 RC1 jest zielony;
3. manualny smoke Windows nie wykazuje blokera;
4. ewentualne problemy są sklasyfikowane jako:
   - blocker wymagający poprawki przed Shopify, albo
   - osobny, nieblokujący issue/backlog;
5. nie ma otwartego branchowego wdrożenia launchera.

Następny duży program prac:

```text
Shopify theme fresh inventory
  -> wybór największych granic Liquid/CSS/JS
  -> małe kontrakty i moduły
  -> testy motywu
  -> bezpieczny deploy
```

---

## 13. Rollback RC1

Ten pakiet jest docs-only. Rollback nie zmienia kodu, AppData ani danych użytkownika. W razie błędu wystarczy revert dokumentacji RC1.
