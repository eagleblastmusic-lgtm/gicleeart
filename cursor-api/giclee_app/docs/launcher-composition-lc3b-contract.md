# ETAP 4B / LC-3B — Windows Shortcut Platform Adapter

**Status:** fresh reconnaissance · contract freeze  
**Repository:** `eagleblastmusic-lgtm/gicleeart`  
**Base:** `master` @ `639cc7a62b42a8a4593f5755bf8938c80020f68e`  
**Data weryfikacji:** 2026-07-15

## 1. Kontekst po LC-3A

LC-3A wydzielił czyste decyzje pollingu i aktywacji do `launcher_shortcut_controller.py`. `OptionsCategoryGicleeApp` nadal zawiera jednak bezpośrednio platformową warstwę Windows:

- mapowanie liter, cyfr i F1–F12 na virtual-key codes;
- ładowanie `ctypes.windll.user32` i konfigurację podpisów funkcji;
- `GetForegroundWindow()` oraz `GetAncestor()`;
- próbki `GetAsyncKeyState()` dla skrótów, Ctrl i Alt;
- obsługę błędów WinAPI.

Ta warstwa jest niezależna od Tk bindtagów, harmonogramu `root.after()`, reguł focus/dialog oraz czystych decyzji LC-3A.

## 2. Cel LC-3B

Wydzielić platformowe funkcje Windows do osobnego modułu, zachowując dokładnie istniejący sposób użycia w klasie.

Nowy moduł:

```text
cursor-api/giclee_app/launcher_windows_shortcuts.py
```

`OptionsCategoryGicleeApp` nadal:

- przechowuje `_windows_user32`;
- decyduje, czy używać WinAPI czy Tk fallback;
- harmonogramuje pierwszy i kolejne pollingi;
- wywołuje `_launcher_shortcuts_active()`;
- przekazuje próbkę do `resolve_shortcut_poll()`;
- uruchamia `_trigger_shortcut()`;
- obsługuje `tk.TclError` związany z rootem i timerem.

## 3. Zamrożony minimalny kontrakt

Dopuszczalne są równoważne nazwy, lecz oczekiwany zakres to:

```python
@dataclass(frozen=True)
class WindowsShortcutSample:
    current_down: frozenset[str]


def shortcut_virtual_key(key: str) -> int | None:
    ...


def load_windows_user32() -> object | None:
    ...


def windows_launcher_is_foreground(
    user32: object,
    window_id: int,
) -> bool:
    ...


def sample_windows_shortcut_keys(
    user32: object,
    keys: Iterable[str],
) -> WindowsShortcutSample:
    ...


def windows_shortcut_modifiers_down(user32: object) -> bool:
    ...
```

Moduł może zwracać bezpośrednio `frozenset[str]` zamiast dataclass, jeśli testy i nazwa jednoznacznie opisują kontrakt.

## 4. Zachowanie wymagające zachowania 1:1

### Virtual keys

- pojedyncza litera ASCII → kod wielkiej litery;
- pojedyncza cyfra → kod cyfry;
- `F1`–`F12` → `0x70`–`0x7B`;
- inne wartości → `None`;
- normalizacja: trim + lowercase;
- `shortcut_virtual_key` pozostaje importowalne z `options_category_launcher.py` jako kompatybilny re-export.

### Ładowanie user32

- poza Windows zwraca `None`;
- na Windows pobiera `ctypes.windll.user32`;
- ustawia istniejące `restype/argtypes` dla:
  - `GetForegroundWindow`;
  - `GetAncestor`;
  - `GetAsyncKeyState`;
- `AttributeError` lub `OSError` → `None`;
- brak importu Tk i brak side effects przy samym imporcie modułu.

### Foreground

- `window_id` jest konwertowany do integer HWND;
- `GetAncestor(hwnd, GA_ROOT)` z fallbackiem do oryginalnego HWND;
- foreground `0` → `False`;
- wyjątki WinAPI/konwersji → `False`;
- `tk.TclError` z `root.winfo_id()` pozostaje obsługiwany w wrapperze klasy, ponieważ moduł platformowy nie importuje Tk.

### Próbka klawiszy

- iteruje wyłącznie aktualne klucze mapy skrótów;
- ignoruje klucze bez virtual-key code;
- `GetAsyncKeyState(vk) & 0x8000` oznacza pressed;
- błąd pojedynczego klawisza nie przerywa całej próbki;
- wynik jest znormalizowanym niemutowalnym zbiorem.

### Modyfikatory

- Ctrl i Alt odczytywane są przez istniejące kody WinAPI;
- wynik `True`, jeśli którykolwiek jest wciśnięty;
- wyjątek → `False`;
- klasa nadal odczytuje modyfikatory wyłącznie, gdy launcher jest aktywny.

## 5. Integracja z `OptionsCategoryGicleeApp`

Dozwolone zmiany:

- usunięcie bezpośrednich importów `ctypes` i `os` z `options_category_launcher.py`;
- import platformowych helperów z nowego modułu;
- zachowanie aliasu:

```python
from .launcher_windows_shortcuts import (
    load_windows_user32 as _load_windows_user32,
    shortcut_virtual_key,
    ...
)
```

Dzięki temu dotychczasowy prywatny call site oraz publicznie używany w testach `shortcut_virtual_key` pozostają kompatybilne.

`_windows_launcher_is_foreground()` pozostaje cienkim wrapperem klasy, ponieważ pobiera `root.winfo_id()` i łapie `tk.TclError`.

`_poll_windows_shortcuts()` pozostaje właścicielem:

- warunku `user32 is None`;
- `active = foreground and launcher_shortcuts_active`;
- decyzji, czy odczytać modyfikatory;
- wywołania `resolve_shortcut_poll()`;
- aktualizacji `_windows_shortcut_down`;
- kolejności aktywacji;
- ponownego `root.after(35, ...)`.

## 6. Poza LC-3B

LC-3B nie obejmuje:

- obiektu stateful sampler/controller;
- zmiany nazwy `_windows_user32`;
- przeniesienia `root.after()`;
- przeniesienia `_launcher_shortcuts_active()`;
- przeniesienia Tk fallback/bindtagów;
- zmiany `_WINDOWS_SHORTCUT_POLL_MS` lub pierwszego opóźnienia 120 ms;
- zmiany Ctrl/Alt/Win semantics;
- zmiany configu JSON lub shortcut options;
- DnD;
- Studio;
- innych systemów operacyjnych poza istniejącym fallbackiem.

Ewentualne LC-3C może po fresh review wydzielić Tk binding orchestration albo zakończyć ShortcutController i przejść do DragDropController. Ten kontrakt tego nie autoryzuje.

## 7. Allowlista LC-3B

Kod:

- nowy `cursor-api/giclee_app/launcher_windows_shortcuts.py`;
- `cursor-api/giclee_app/options_category_launcher.py`.

Testy i dokumentacja:

- nowy `cursor-api/tests/test_launcher_windows_shortcuts.py`;
- istniejący `cursor-api/tests/test_launcher_shortcuts_config.py` tylko jeśli wymaga kompatybilnego importu;
- `cursor-api/giclee_app/docs/launcher.md`;
- ten kontrakt.

Poza allowlistą:

- `launcher_shortcut_controller.py`;
- `launcher_shortcuts.py` i JSON config;
- `launcher_shortcut_options.py`;
- launcher/category/renderer/grid;
- Styled/DragDrop;
- Studio;
- `Komponenty/*`;
- workflow CI;
- pliki startowe.

## 8. Testy

Focused suite musi potwierdzić:

1. pełne mapowanie litera/cyfra/F1–F12 i odrzucenie innych wartości;
2. `load_windows_user32()` zwraca `None` poza Windows;
3. konfigurację podpisów user32 przez fake ctypes backend;
4. foreground true/false, ancestor fallback i bezpieczne wyjątki;
5. próbkę wielu klawiszy, ignorowanie nieprawidłowych oraz błąd pojedynczego key state;
6. Ctrl/Alt i fallback false przy wyjątku;
7. niemutowalność wyniku próbki;
8. brak importów Tk, launchera, Studio i `Komponenty` w nowym module;
9. `OptionsCategoryGicleeApp` nie wywołuje bezpośrednio `GetAsyncKeyState`, `GetForegroundWindow` ani `GetAncestor`;
10. wrapper zachowuje `tk.TclError`, harmonogram 35 ms, LC-3A controller i dotychczasowy fallback Tk;
11. istniejące testy shortcut config, LC-3A, composition root, kategorii, DnD-order i Studio imports pozostają zielone.

Po focused PASS obowiązują:

- `git diff --check`;
- Stage 2 Hermetic;
- Tk GUI smoke;
- full baseline;
- runtime-write inventory.

## 9. Manual smoke

Canonical Windows CI pozostaje podstawowym dowodem. Należy zachować:

- wykrywanie foreground launchera;
- skróty litera/cyfra/F1–F12;
- Ctrl/Alt blokujące aktywację;
- brak delayed launch po powrocie do okna;
- pojedynczy launch na zbocze;
- Tk fallback na środowisku bez user32;
- brak zmian w edytorze skrótów;
- brak regresji inline, subprocess i DnD.

## 10. Rollback i ukończenie

Brak danych, config migration i I/O. Rollback to revert pojedynczego commitu.

LC-3B jest ukończony, gdy:

- finalny diff mieści się w allowliście;
- platformowy moduł nie importuje Tk/UI/launchera;
- klasa nie zawiera bezpośrednich calli WinAPI;
- polling/timing/fallback pozostają 1:1;
- focused i pełna brama Stage 2 są zielone;
- runtime-write inventory nie ma nowych findings;
- `behind_by=0`, review threads=0;
- brak Shopify mutation, deployu, ZIP-a i pracy nad plikami startowymi.
