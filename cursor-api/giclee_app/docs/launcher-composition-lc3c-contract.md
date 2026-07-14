# ETAP 4B / LC-3C — Tk Shortcut Binding Adapter

**Status:** fresh reconnaissance · contract freeze  
**Repository:** `eagleblastmusic-lgtm/gicleeart`  
**Base:** `master` @ `2dc2adbe539da2a3f5798b014cebcf6058a81ee7`  
**Data weryfikacji:** 2026-07-15

## 1. Kontekst po LC-3A i LC-3B

Po scaleniu LC-3A i LC-3B odpowiedzialności skrótów są rozdzielone następująco:

- `launcher_shortcut_controller.py` rozstrzyga czyste decyzje pollingu i aktywacji;
- `launcher_windows_shortcuts.py` izoluje WinAPI, virtual-key mapping, foreground i próbki klawiszy;
- `OptionsCategoryGicleeApp` nadal posiada lifecycle Tk, timer `root.after()`, fokus, statusy, `after_idle`, faktyczny launch oraz fallback bindingów Tk.

Fresh review aktualnego `master` potwierdził, że pozostały fallback Tk jest samodzielną, małą granicą. Obejmuje:

- rejestrację class bindingu dla prywatnego bindtagu launchera;
- rekursywne dołączanie bindtagu do drzewa widgetów;
- bezpośredni `widget.bind(..., add="+")` jako zgodnościowy fallback;
- marker zapobiegający wielokrotnemu bezpośredniemu bindowaniu tego samego widgetu;
- tolerowanie znikających widgetów i błędów Tcl podczas przebudowy widoku.

Ta odpowiedzialność nie powinna być mieszana z decyzją, czy skróty są aktywne, ani z interpretacją eventu klawiatury.

## 2. Finding i decyzja zakresowa

Aktualne metody:

- `_bind_launcher_shortcuts()`;
- `_install_shortcut_bindtags()`;
- `_bind_shortcut_directly()`

zawierają platformowo-specyficzną orkiestrację Tk, ale nie należą do czystego kontrolera LC-3A ani do adaptera WinAPI LC-3B.

**Decyzja LC-3C:** wydzielić wyłącznie mechanikę bindingów Tk do osobnego modułu callback-driven. Zachować trzy istniejące metody klasy jako cienkie wrappery, aby nie łamać testów, override hooks ani niejawnych konsumentów.

LC-3C nie przenosi:

- `_on_launcher_key_shortcut()`;
- `_launcher_shortcuts_active()`;
- `_launcher_shortcut_key()`;
- `_restore_shortcut_focus()`;
- lifecycle `_build_ui()` i `_render_tiles()`;
- timerów `80 ms`, `120 ms`, `320 ms` ani pollingu `35 ms`;
- LC-3A activation decisions;
- LC-3B WinAPI adaptera;
- zapisu konfiguracji skrótów.

## 3. Docelowy moduł

Nowy plik:

`cursor-api/giclee_app/launcher_tk_shortcut_bindings.py`

Moduł może importować `tkinter`, ale nie może importować:

- `options_category_launcher`;
- `launcher` ani żadnego entrypointu;
- `launcher_shortcut_controller`;
- `launcher_windows_shortcuts`;
- konfiguracji skrótów i ścieżek runtime;
- Studio;
- `Komponenty`;
- DnD.

Docelowe publiczne helpery:

1. `bind_shortcut_class(root, bindtag, callback) -> bool`
   - próbuje usunąć poprzedni class binding dla `<KeyPress>`;
   - rejestruje dokładnie jeden class binding dla przekazanego bindtagu;
   - zwraca `False`, gdy `bind_class` nie jest dostępny albo kończy się TclError;
   - nie instaluje bindtagów w drzewie.

2. `bind_widget_shortcut(widget, callback, *, marker=...) -> bool`
   - nie tworzy duplikatu, gdy marker już istnieje;
   - używa `<KeyPress>` z `add="+"`;
   - zapisuje identyfikator bindingu albo wartość truthy w markerze;
   - toleruje AttributeError i TclError;
   - zwraca informację, czy wykonano nowe bezpośrednie bindowanie.

3. `install_shortcut_bindtags(root, bindtag, callback, *, bind_direct=...) -> None`
   - przechodzi całe aktualne drzewo widgetów iteracyjnie;
   - umieszcza prywatny bindtag launchera na pierwszej pozycji dokładnie raz;
   - zachowuje kolejność pozostałych bindtagów;
   - wywołuje przekazany `bind_direct` dla każdego osiągalnego widgetu;
   - toleruje widgety zniszczone w trakcie przebudowy;
   - nie przechowuje stanu między wywołaniami.

Parametr `bind_direct` jest jawny, aby `OptionsCategoryGicleeApp._bind_shortcut_directly()` pozostał realnym override hookiem, a nie martwym wrapperem.

## 4. Adapter w `OptionsCategoryGicleeApp`

Po LC-3C klasa zachowuje istniejące nazwy metod:

### `_bind_launcher_shortcuts()`

- nadal natychmiast wraca w trybie WinAPI;
- deleguje class binding do `bind_shortcut_class(...)`;
- po sukcesie wywołuje własny wrapper `_install_shortcut_bindtags()`;
- nie zmienia handlera `_on_launcher_key_shortcut`.

### `_install_shortcut_bindtags()`

- nadal natychmiast wraca w trybie WinAPI;
- deleguje rekursję do `install_shortcut_bindtags(...)`;
- przekazuje `self._bind_shortcut_directly` jako callback bezpośredniego bindu.

### `_bind_shortcut_directly(widget)`

- pozostaje cienkim wrapperem nad `bind_widget_shortcut(...)`;
- zachowuje marker `_giclee_launcher_shortcut_bound`;
- nie zmienia typu zwrotnego istniejącej metody klasy.

Lifecycle pozostaje 1:1:

- `_build_ui()` instaluje menu, bindtagi i `<Map>`;
- `_render_tiles()` ponawia instalację przez `after_idle`;
- `_apply_shortcuts()` ponawia binding i fokus;
- `_restore_shortcut_focus()` nadal ponawia instalację bindtagów.

## 5. Zachowanie, które musi pozostać bez zmian

LC-3C musi zachować:

1. prywatny bindtag per instancja `GicleeLauncherShortcuts_<id>`;
2. class binding `<KeyPress>`;
3. bezpośredni fallback `<KeyPress>` z `add="+"`;
4. marker `_giclee_launcher_shortcut_bound`;
5. brak duplikacji bezpośrednich bindingów po wielokrotnym renderze;
6. bindtag launchera jako pierwszy element tuple;
7. niezmienioną kolejność pozostałych bindtagów;
8. działanie na root i wszystkich aktualnych dzieciach;
9. tolerowanie TclError/AttributeError bez przerwania renderu;
10. całkowite pominięcie fallbacku Tk, gdy `_windows_user32` jest dostępne;
11. `None` albo `"break"` zwracane przez istniejący handler bez zmian;
12. wszystkie teksty statusu, event state masks i mapowanie klawiszy bez zmian.

## 6. Allowlista implementacyjna

Dozwolone pliki:

- `cursor-api/giclee_app/launcher_tk_shortcut_bindings.py` — nowy;
- `cursor-api/giclee_app/options_category_launcher.py` — wyłącznie delegacja trzech metod;
- `cursor-api/tests/test_launcher_tk_shortcut_bindings.py` — nowy;
- `cursor-api/giclee_app/docs/launcher.md` — krótki wpis LC-3C;
- ten kontrakt — zmiana statusu po wdrożeniu.

Nie są dozwolone zmiany w:

- `launcher_shortcuts.py`;
- `launcher_shortcut_controller.py`;
- `launcher_windows_shortcuts.py`;
- `launcher_shortcut_options.py`;
- `dragdrop_category_launcher.py`;
- `launcher.py`, `category_launcher.py`, rendererze i gridzie;
- Studio;
- komponentach;
- workflowach Stage 2;
- danych użytkownika i formatach JSON;
- plikach startowych oraz ZIP-ie.

Każde rozszerzenie allowlisty wymaga nowego findingu przed edycją.

## 7. Focused tests

Nowy focused suite musi potwierdzić:

1. class binding unbinds/rebinds właściwy bindtag i event;
2. błąd `unbind_class` nie blokuje próby `bind_class`;
3. błąd `bind_class` zwraca `False` i nie instaluje drzewa;
4. root oraz dzieci otrzymują bindtag na pierwszej pozycji;
5. pozostałe bindtagi zachowują kolejność;
6. wielokrotna instalacja nie duplikuje bindtagu;
7. bezpośredni binding jest wykonywany dokładnie raz na widget;
8. używane jest `add="+"`;
9. marker przechowuje identyfikator bindingu albo wartość truthy;
10. błędy pojedynczego widgetu nie blokują rodzeństwa;
11. `bind_direct` jest callbackiem i może zostać zastąpiony;
12. moduł nie importuje launchera, WinAPI, kontrolera, Studio, DnD ani `Komponenty`;
13. istniejące trzy metody klasy delegują do adaptera;
14. tryb WinAPI nadal omija fallback Tk;
15. istniejący test konfiguracji skrótów zachowuje dotychczasowe oczekiwania.

Minimalny focused regression set:

- `tests/test_launcher_tk_shortcut_bindings.py`;
- `tests/test_launcher_shortcuts_config.py`;
- `tests/test_launcher_shortcut_controller.py`;
- `tests/test_launcher_windows_shortcuts.py`;
- `tests/test_launcher_composition.py`;
- `tests/test_launcher_tile_order.py`;
- `tests/test_giclee_app_packaging.py`.

Po focused PASS obowiązują:

- `git diff --check`;
- twardy scope guard;
- Hermetic Stage 2;
- canonical Tk GUI smoke;
- full pytest baseline;
- JUnit i runtime-write inventory;
- exact-head review przed merge.

## 8. Manual smoke

Manualny Windows smoke po implementacji powinien potwierdzić:

1. `python -m giclee_app` uruchamia finalny launcher;
2. skróty działają na ekranie kategorii i komponentów;
3. fokus w Entry/Text/Combobox nadal blokuje skróty;
4. osobny dialog nadal blokuje skróty;
5. wielokrotne wejście/wyjście z kategorii nie powoduje podwójnego launchu;
6. przebudowa kafelków nie usuwa działania fallbacku Tk;
7. Windows WinAPI path nadal omija fallback Tk;
8. `Esc`, `Backspace` i `Alt+Left` zachowują dotychczasowe działanie nawigacji;
9. DnD kategorii i komponentów działa bez regresji.

## 9. Rollback

LC-3C nie zmienia danych, konfiguracji ani formatów plików. Rollback to zwykły revert pojedynczego commitu implementacyjnego. Nie wymaga migracji ani czyszczenia AppData.

## 10. Kryteria ukończenia

LC-3C jest ukończone, gdy:

- moduł Tk bindingów istnieje i ma tylko odpowiedzialność adaptera;
- trzy istniejące metody klasy są cienkimi wrapperami;
- lifecycle, aktywność, fokus, event parsing i launch pozostają w klasie;
- finalny diff mieści się w allowliście;
- focused suite jest zielony;
- Hermetic, Tk GUI i full baseline są zielone na tym samym exact headzie;
- artefakt potwierdza 0 failures/errors;
- runtime-write inventory ma 0 findings;
- branch ma `behind_by=0`;
- review threads są puste;
- merge jest wykonywany wyłącznie z expected exact head SHA.

## 11. Następny krok po LC-3C

LC-3C nie autoryzuje zmian DnD. Po merge wymagany jest osobny fresh review `DragDropCategoryGicleeApp`, obejmujący co najmniej:

- granicę czystego stanu gestu;
- geometrię hit-test/drop-after;
- Tk event orchestration;
- zapis kolejności kategorii i komponentów;
- auto-scroll i wizualny feedback;
- istniejące testy oraz ręczny smoke trwałości po restarcie.
