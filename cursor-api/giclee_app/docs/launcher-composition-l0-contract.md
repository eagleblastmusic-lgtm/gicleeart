# ETAP 4B / L-0 — Launcher Composition: Fresh Reconnaissance & Contract Freeze

**Status:** L-0 complete · LC-1 implemented
**Repository:** `eagleblastmusic-lgtm/gicleeart`  
**Base:** `master` @ `f3d830910b2e9a5f108ec0896cc19c88d3d1eb5f`  
**Data weryfikacji:** 2026-07-14

## 1. Cel etapu

Zamrozić rzeczywisty stan architektury launchera przed dalszym refaktorem oraz wyznaczyć najmniejszy bezpieczny pakiet implementacyjny.

L-0 nie zmienia kodu aplikacji. Nie zmienia UI, zachowania launchera, danych użytkownika, pollingów, backupów, Shopify, komponentów ani Studio Preview.

## 2. Zweryfikowany stan wejściowy

### 2.1 Produkcyjny entrypoint

`python -m giclee_app` wykonuje:

1. `giclee_app.__main__` importuje `main` z `dragdrop_category_launcher`;
2. `dragdrop_category_launcher.main()` zapisuje bieżące `launcher.GicleeApp`;
3. globalnie podmienia `launcher.GicleeApp` na `DragDropCategoryGicleeApp`;
4. wywołuje `launcher.main()`;
5. przywraca wcześniejszy symbol w `finally`.

To samo podejście występuje w samodzielnych entrypointach warstw:

- `category_launcher.py`;
- `styled_category_launcher.py`;
- `options_category_launcher.py`;
- `dragdrop_category_launcher.py`.

`launcher.main()` tworzy root Tk/TkinterDnD, uruchamia splash i wewnątrz callbacku konstruuje klasę przez globalny symbol `GicleeApp(root)`. Ten hardcoded lookup jest przyczyną runtime class replacement.

### 2.2 Aktualne MRO klasycznego launchera

MRO, które musi zostać zachowane bez zmiany kolejności:

```text
DragDropCategoryGicleeApp
  -> OptionsCategoryGicleeApp
  -> StyledCategoryGicleeApp
  -> CategoryGicleeApp
  -> launcher.GicleeApp
  -> object
```

Odpowiedzialności warstw:

| Warstwa | Obecna odpowiedzialność |
|---|---|
| `launcher.GicleeApp` | root UI, discovery, bazowa siatka, inline, subprocess/url, logi, rescan, przypomnienia i usługi tła |
| `CategoryGicleeApp` | nawigacja kategorie → komponenty i powrót |
| `StyledCategoryGicleeApp` | prezentacja kafelków komponentów |
| `OptionsCategoryGicleeApp` | menu Opcje i konfigurowalne skróty |
| `DragDropCategoryGicleeApp` | DnD kategorii i komponentów oraz trwała kolejność |

### 2.3 Dwa niezależne shelle

Repo zawiera dwa celowo rozdzielone shelle:

1. **Klasyczny launcher** — `python -m giclee_app`  
   Produkcyjny fallback z inline, subprocess/url, pollingami, reminderami, backupem i pozostałymi usługami tła.

2. **Studio Preview** — `python -m giclee_app.studio_preview`  
   Osobny shell CustomTkinter, własny routing, cache widoków, inline stack i `launcher_delegate`; bez importu klasycznego `launcher.py` i bez jego usług tła.

Pierwszy pakiet 4B nie scala tych shelli i nie przenosi usług tła do Studio.

## 3. Mapa zachowań, których nie wolno zmienić

### Nawigacja

- ekran kategorii → ekran komponentów;
- powrót przez przycisk, `Esc`, `Backspace`, `Alt+Left`;
- powrót z inline do ostatniej kategorii;
- pusta/usunięta kategoria wraca bezpiecznie do indeksu.

### Tile grid i DnD

- trzy kolumny i aktualne wymiary/paddingi;
- próg rozpoczęcia drag;
- klik bez drag uruchamia komponent;
- rozróżnienie drop przed/za celem;
- auto-scroll przy krawędziach;
- zachowanie pozycji ukrytych elementów;
- natychmiastowy zapis kolejności przez istniejący `launcher_layout`.

### Skróty

- litery, cyfry i F1–F12;
- jeden klawisz na komponent i jeden komponent na klawisz;
- blokada w polach tekstowych, dialogach i inline;
- WinAPI foreground polling na Windows oraz fallback Tk poza nim;
- aktualna konfiguracja i atomic write.

### Component launch

- `url` otwiera przeglądarkę;
- `inline` importuje `view.py`, buduje host i zachowuje back stack/geometry;
- `subprocess` uruchamia `python -m Komponenty.<folder>` w osobnym procesie;
- stdout/stderr pozostają w logu komponentu;
- zamknięcie launchera nie zabija uruchomionych subprocessów.

### Background services

W pierwszym pakiecie bez zmian pozostają wszystkie harmonogramy i wywołania z konstruktora klasycznego launchera, w tym:

- auto-rescan komponentów;
- przypomnienia miesięczne;
- Shopify orders polling;
- accounting orders polling;
- daily backup;
- cure notifications;
- social publisher;
- weekly content reminder.

## 4. Własność stanu i ścieżki runtime

| Stan | Obecna własność | Decyzja L-0 |
|---|---|---|
| `launcher_layout.json` | AppData przez `config_path`, legacy read fallback | zachować |
| `launcher_shortcuts.json` | AppData przez `config_path`, legacy read fallback | zachować |
| logi komponentów | zewnętrzny katalog logów przez `component_logs` | zachować |
| uruchomione procesy | pamięć instancji klasycznego launchera | zachować |
| inline host / return state | pamięć instancji klasycznego launchera | zachować |
| Studio recent/pinned | `StudioState`; osobny tor Studio | poza LC-1; audyt w późniejszym pakiecie state separation |
| pollingi/remindery | konstruktor `launcher.GicleeApp` | poza LC-1; przyszłe `BackgroundServices` |

Żadna migracja danych ani zmiana ścieżek runtime nie jest dozwolona w LC-1.

## 5. Pierwszy pakiet implementacyjny — LC-1 Explicit Composition Root

### Problem

Warstwy launchera wybierają finalną klasę przez chwilową globalną podmianę `launcher.GicleeApp`. Powoduje to ukrytą zależność od stanu modułu, utrudnia testy entrypointu i stwarza ryzyko przy reentrancy, równoległym imporcie lub przyszłym osadzaniu launchera.

### Zamrożone rozwiązanie

`launcher.main()` otrzyma jawny opcjonalny factory/class argument. Callback po splashu skonstruuje aplikację przez przekazany factory, a nie przez podmieniony globalny symbol.

Kontrakt docelowy:

```python
LauncherFactory = Callable[[tk.Tk], object]


def main(app_factory: LauncherFactory | None = None) -> None:
    factory = app_factory or GicleeApp
    ...
    def _show_main() -> None:
        factory(root)
        root.deiconify()
    ...
```

Każdy entrypoint warstwy przekaże własną klasę jawnie:

```python
_launcher.main(app_factory=DragDropCategoryGicleeApp)
```

Nie wolno w LC-1:

- przypisywać do `_launcher.GicleeApp`;
- dynamicznie tworzyć klasy przez `type(...)`;
- zmieniać MRO;
- przenosić metod między klasami;
- zmieniać `__main__.py` na Studio Preview;
- scalać launchera klasycznego i Studio;
- wydzielać jeszcze kontrolerów UI lub usług tła.

### Allowlista LC-1

Kod:

- `cursor-api/giclee_app/launcher.py`;
- `cursor-api/giclee_app/category_launcher.py`;
- `cursor-api/giclee_app/styled_category_launcher.py`;
- `cursor-api/giclee_app/options_category_launcher.py`;
- `cursor-api/giclee_app/dragdrop_category_launcher.py`.

Testy i dokumentacja:

- nowy `cursor-api/tests/test_launcher_composition.py`;
- `cursor-api/giclee_app/docs/launcher.md`;
- ten kontrakt;
- `cursor-api/docs/GICLEEAPP_IMPLEMENTED_SOLUTIONS_INDEX.md` wyłącznie po wdrożeniu trwałego wzorca.

`cursor-api/giclee_app/__main__.py` pozostaje bez zmian, o ile implementacja nie wykaże niezbędnej korekty kontraktowej. Każde rozszerzenie allowlisty wymaga osobnego uzasadnienia przed edycją.

## 6. Testy kontraktowe LC-1

Nowy focused suite musi potwierdzić:

1. dokładne MRO finalnej klasy;
2. brak przypisania do `launcher.GicleeApp` we wszystkich czterech entrypointach warstw;
3. `launcher.main(app_factory=...)` używa przekazanego factory dokładnie raz;
4. factory jest wykonywane po splash callbacku i przed `deiconify`;
5. domyślny `launcher.main()` nadal wybiera bazowe `GicleeApp`;
6. `giclee_app.__main__` nadal prowadzi do finalnego launchera DnD;
7. import Studio nadal nie zależy od klasycznego `launcher.py`.

Focused regression set:

- `tests/test_launcher_composition.py`;
- `tests/test_launcher_tile_order.py`;
- testy layoutu i shortcutów znalezione podczas implementacji;
- `tests/test_launcher_delegate.py`;
- `tests/test_studio_imports.py`;
- `tests/test_giclee_app_packaging.py`.

Dopiero po focused PASS: `git diff --check`, hermetic CI, canonical Tk i full baseline zgodnie z aktualnym Stage 2 runbookiem.

## 7. Manual smoke LC-1

Na Windows, z aktualnego worktree:

1. uruchomić `python -m giclee_app`;
2. potwierdzić splash i pokazanie indeksu kategorii;
3. wejść do kategorii i wrócić każdym obsługiwanym skrótem;
4. przeciągnąć kategorię i kafelek komponentu, zamknąć/restartować launcher i potwierdzić trwałość;
5. przypisać i użyć skrótu komponentu;
6. otworzyć komponent inline i wrócić do właściwej kategorii;
7. uruchomić komponent subprocess i potwierdzić log/PID;
8. otworzyć komponent URL;
9. zamknąć launcher i potwierdzić, że subprocess pozostaje aktywny;
10. uruchomić `python -m giclee_app.studio_preview` i potwierdzić brak regresji importu/entrypointu Studio.

## 8. Rollback

LC-1 nie zmienia danych ani formatów plików. Rollback to zwykły revert pojedynczego commitu implementacyjnego. Nie wymaga migracji wstecznej, czyszczenia AppData ani przywracania plików użytkownika.

## 9. Kolejne pakiety — jeszcze niezamrożone implementacyjnie

Po LC-1 i osobnym fresh review:

- **LC-2 CategoryNavigator / TileGrid boundaries** — rozdzielenie nawigacji od renderowania;
- **LC-3 ShortcutController / DragDropController** — wydzielenie event orchestration bez zmiany UX;
- **LC-4 ComponentLauncher / Inline Host** — jedna jawna granica uruchamiania przy zachowaniu różnic klasyczny/Studio;
- **LC-5 BackgroundServices** — przeniesienie scheduling/orchestration z konstruktora, bez zmiany częstotliwości ani side effects;
- **LC-6 LauncherApp composition** — dopiero po stabilizacji poprzednich granic decyzja o dalszym zbliżeniu klasycznego launchera i Studio.

Nazwy oraz allowlisty LC-2+ wymagają osobnego reconnaissance na bieżącym `master`. Ten dokument nie autoryzuje ich implementacji.

## 10. Kryteria ukończenia L-0

L-0 jest gotowe do review, gdy:

- kontrakt jest w osobnym branchu i draft PR;
- base SHA i brak równoległego PR zostały zweryfikowane;
- opisano entrypoint, MRO, nawigację, grid, DnD, skróty, launch modes, usługi tła, stan i ścieżki runtime;
- zamrożono LC-1, allowlistę, testy, manual smoke, rollback i completion criteria;
- diff jest docs-only;
- nie zmieniono aplikacji, Shopify, danych, workflow CI ani lokalnych plików startowych.
