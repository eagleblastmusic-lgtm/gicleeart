# ETAP 4B / LC-3A — Pure Shortcut Activation Decisions

**Status:** fresh reconnaissance · contract freeze  
**Repository:** `eagleblastmusic-lgtm/gicleeart`  
**Base:** `master` @ `6cfbd5b607f5a6afcf49c0d39a77946fdd77bb34`  
**Data weryfikacji:** 2026-07-15

## 1. Kontekst po LC-2

LC-1 oraz LC-2A–LC-2C wydzieliły composition root, model nawigacji, renderer kategorii i placement siatki. Następna granica z planu L-0 to `ShortcutController / DragDropController`.

Fresh review wykazał, że konfiguracja skrótów jest już oddzielona w `launcher_shortcuts.py`, natomiast `OptionsCategoryGicleeApp` nadal łączy:

1. adapter platformowy WinAPI (`GetAsyncKeyState`, foreground HWND);
2. Tk fallback (`bindtag`, bezpośrednie bindingi, event state);
3. wykrywanie nowego naciśnięcia względem poprzedniej próbki;
4. decyzję `unmapped / missing component / launch pending / ready`;
5. status UI i `after_idle` uruchamiające komponent.

LC-3A wydziela wyłącznie punkty 3–4. Adaptery, UI i faktyczne uruchomienie pozostają w klasie.

## 2. Zachowanie wymagające zachowania 1:1

### Windows polling

- próbka obejmuje wyłącznie klawisze obecne w aktualnej mapie skrótów;
- wykrywane jest zbocze `current_down - previous_down`;
- klawisz trzymany poza aktywnym oknem nie może uruchomić komponentu po powrocie do launchera;
- dlatego następny stan `previous_down` zawsze przyjmuje aktualną próbkę, również gdy launcher jest nieaktywny;
- przy Ctrl lub Alt nie ma aktywacji;
- przy wielu nowych klawiszach zachowywana jest deterministyczna kolejność sortowana;
- po pierwszej obsłużonej aktywacji pętla przestaje uruchamiać kolejne skróty w tej próbce.

### Tk fallback

- skróty działają tylko, gdy siatka jest widoczna;
- nie działają w polach tekstowych ani dialogach;
- Ctrl/Alt blokują aktywację;
- event bez prawidłowego klawisza zwraca `None`;
- obsłużony skrót zwraca `"break"`.

### Rozwiązanie aktywacji

- brak mapowania → brak obsługi;
- mapowanie do brakującego komponentu → obsłużone, z dotychczasowym komunikatem statusu;
- aktywacja podczas oczekującego uruchomienia → obsłużona bez drugiego launchu;
- gotowy komponent → ustawienie pending, status „otwieram…”, jeden `after_idle`;
- callback przed `_launch()` zeruje pending;
- zmiana mapy skrótów czyści stan klawiszy Windows.

## 3. Decyzja LC-3A

Nowy moduł:

```text
cursor-api/giclee_app/launcher_shortcut_controller.py
```

Moduł jest czysty: bez Tk, ctypes, WinAPI, I/O, timerów, statusów i launchera.

Minimalny kontrakt:

```python
class ShortcutActivationKind(str, Enum):
    UNMAPPED = "unmapped"
    MISSING_COMPONENT = "missing_component"
    LAUNCH_PENDING = "launch_pending"
    READY = "ready"


@dataclass(frozen=True)
class ShortcutPollDecision:
    pressed_keys: tuple[str, ...]
    next_down: frozenset[str]


@dataclass(frozen=True)
class ShortcutActivation:
    kind: ShortcutActivationKind
    key: str
    folder_name: str | None = None

    @property
    def handled(self) -> bool:
        ...


def resolve_shortcut_poll(
    current_down: Iterable[str],
    previous_down: Iterable[str],
    *,
    active: bool,
    modifiers_down: bool,
) -> ShortcutPollDecision:
    ...


def resolve_shortcut_activation(
    shortcuts: Mapping[str, str],
    key: str,
    *,
    component_exists: bool,
    launch_pending: bool,
) -> ShortcutActivation:
    ...
```

Dopuszczalne są równoważne nazwy, jeśli zachowane zostaną wszystkie własności.

## 4. Własności czystej warstwy

### Poll decision

- normalizuje wejściowe kolekcje do zbiorów stringów;
- `next_down` zawsze odpowiada aktualnej próbce;
- gdy `active=False`, `pressed_keys=()`;
- gdy `modifiers_down=True`, `pressed_keys=()`;
- gdy aktywne i bez modyfikatorów, `pressed_keys` to posortowane `current - previous`;
- nie mutuje kolekcji wejściowych.

### Activation decision

- pusty/brakujący klucz w mapie → `UNMAPPED`, `handled=False`;
- istniejący folder, ale `component_exists=False` → `MISSING_COMPONENT`, `handled=True`;
- istniejący komponent i `launch_pending=True` → `LAUNCH_PENDING`, `handled=True`;
- istniejący komponent i brak pending → `READY`, `handled=True`;
- decyzja przechowuje znormalizowany klawisz oraz folder potrzebny do statusu i lookupu;
- kolejność priorytetu to: mapowanie → istnienie komponentu → pending → ready.

## 5. Integracja z `OptionsCategoryGicleeApp`

### `_poll_windows_shortcuts()`

Klasa nadal:

- pobiera próbkę przez WinAPI;
- oblicza `active` z foreground/focus/dialog;
- pobiera stan Ctrl/Alt;
- harmonogramuje kolejny poll przez `root.after()`.

Nowy resolver:

- otrzymuje `current_down`, poprzedni stan, `active`, stan modyfikatorów;
- zwraca `pressed_keys` oraz `next_down`;
- klasa przypisuje `_windows_shortcut_down = set(decision.next_down)`;
- dla kolejnych `pressed_keys` nadal wywołuje `_trigger_shortcut()` i kończy po pierwszym `True`.

### `_trigger_shortcut()`

Klasa nadal:

- znajduje `Component` przez `_component_by_folder()`;
- ustawia dotychczasowe teksty statusu;
- ustawia/zeruje `_shortcut_launch_pending`;
- używa `root.after_idle()`;
- wywołuje istniejące `_launch(component)`.

Resolver activation decyduje wyłącznie o rodzaju wyniku. Nie może wywoływać lookupu, statusu, timera ani launchu.

## 6. Co pozostaje poza LC-3A

- `shortcut_virtual_key()` i ctypes/WinAPI;
- `_load_windows_user32()`;
- rejestracja i usuwanie Tk bindtagów;
- rekursywne bindingi widgetów;
- focus restoration;
- dialog/focus blockers w `launcher_shortcuts.py`;
- edytor skrótów i format JSON;
- `DragDropController`;
- Studio shortcut path;
- zmiana UX, klawiszy domyślnych, polling interval lub statusów.

Ewentualne LC-3B może po fresh review wydzielić platformowe źródła zdarzeń. LC-3C może osobno objąć DnD orchestration. Ten kontrakt nie autoryzuje tych pakietów.

## 7. Allowlista LC-3A

Kod:

- nowy `cursor-api/giclee_app/launcher_shortcut_controller.py`;
- `cursor-api/giclee_app/options_category_launcher.py`.

Testy i dokumentacja:

- nowy `cursor-api/tests/test_launcher_shortcut_controller.py`;
- rozszerzenie `cursor-api/tests/test_launcher_shortcuts_config.py` tylko jeśli potrzebna jest integracja wrapperów;
- `cursor-api/giclee_app/docs/launcher.md`;
- ten kontrakt.

Poza allowlistą:

- `launcher_shortcuts.py` i format configu;
- `launcher_shortcut_options.py`;
- `launcher.py`;
- Category/Styled/DragDrop;
- LC-2 modules;
- Studio;
- `Komponenty/*`;
- workflow CI;
- pliki startowe.

## 8. Testy

Focused suite musi potwierdzić:

1. aktywna próbka wykrywa posortowane nowe klawisze;
2. przytrzymany klawisz nie pojawia się drugi raz;
3. inactive/modifiers blokują aktywację, ale aktualizują `next_down`;
4. wejściowe zbiory nie są mutowane;
5. wszystkie cztery wyniki activation i właściwość `handled`;
6. priorytet missing component przed pending;
7. moduł nie importuje Tk, ctypes, launchera, Studio ani `Komponenty`;
8. `_poll_windows_shortcuts()` używa poll resolvera i zawsze zapisuje `next_down`;
9. `_trigger_shortcut()` używa activation resolvera, ale zachowuje dotychczasowe statusy, pending i `after_idle`;
10. dotychczasowe testy konfiguracji, bindtagów, composition root, kategorii, DnD-order i Studio imports pozostają zielone.

Po focused PASS obowiązują:

- `git diff --check`;
- Stage 2 Hermetic;
- Tk GUI smoke;
- full baseline;
- runtime-write inventory.

## 9. Manual smoke

Canonical Windows CI jest podstawowym dowodem, ponieważ LC-3A nie zmienia bindtagów ani adaptera WinAPI. Należy zachować:

- skrót domyślny `I`;
- własne litery, cyfry i F1–F12;
- brak aktywacji podczas pisania;
- brak aktywacji z Ctrl/Alt;
- brak aktywacji po powrocie do okna z nadal trzymanym klawiszem;
- pojedynczy launch przy jednym naciśnięciu;
- działanie na indeksie kategorii oraz ekranie komponentów;
- brak skrótów w inline/dialogach;
- zapis/odczyt mapy bez zmian.

## 10. Rollback i ukończenie

LC-3A nie zmienia danych ani configu. Rollback to revert pojedynczego commitu.

Pakiet jest ukończony, gdy:

- finalny diff mieści się w allowliście;
- pure decision module nie ma zależności platformowych/UI;
- polling interval, bindtagi, statusy i launch scheduling są 1:1;
- focused oraz pełna brama Stage 2 są zielone;
- runtime-write inventory nie ma nowych findings;
- `behind_by=0`, review threads=0;
- brak Shopify mutation, deployu, ZIP-a i pracy nad plikami startowymi.
