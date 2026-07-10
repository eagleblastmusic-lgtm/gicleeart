# Launcher (`launcher.py` + warstwy kategorii)

Hub GicleeApp: [`README.md`](README.md)

Pliki:

- `cursor-api/giclee_app/launcher.py` — bazowy launcher, uruchamianie komponentów i widoki inline,
- `cursor-api/giclee_app/category_launcher.py` — dwupoziomowy ekran startowy: kategorie → komponenty,
- `cursor-api/giclee_app/styled_category_launcher.py` — spójny styl kafelków komponentów,
- `cursor-api/giclee_app/options_category_launcher.py` — menu **Opcje** i konfigurowalne skróty,
- `cursor-api/giclee_app/dragdrop_category_launcher.py` — przeciąganie kategorii i komponentów,
- `cursor-api/giclee_app/launcher_tile_order.py` — czyste helpery trwałej kolejności,
- `cursor-api/giclee_app/launcher_shortcut_options.py` — okno przypisywania skrótów.

**Studio Preview (F1):** nowy shell CustomTkinter w [`studio-preview.md`](studio-preview.md) — `python -m giclee_app.studio_preview`. Klasyczny launcher pozostaje fallbackiem z pollingiem Shopify, backupami i widokami inline.

---

## Co robi

- Po starcie pokazuje siatkę **kategorii**, a nie wszystkie komponenty naraz
- Kliknięcie kategorii otwiera osobny ekran z kafelkami komponentów należących do tej kategorii
- Kafelki kategorii i komponentów można układać metodą drag-and-drop
- Przycisk **← Wszystkie kategorie**, `Esc`, `Backspace` lub `Alt+Left` wraca do głównego ekranu kategorii
- Uruchamia komponenty jako **osobne procesy** (`subprocess`) lub **inline views** w tym samym oknie
- Powrót z komponentu inline prowadzi do ostatnio otwartej kategorii
- Toolbar zawiera pojedynczy przycisk **Opcje** zamiast osobnych przycisków Token Setup, Stan sesji i układ
- Co 3 s skanuje `Komponenty/` w tle (nowe kafelki)
- Skróty użytkownika działają na ekranie kategorii i komponentów, o ile fokus nie znajduje się w polu tekstowym lub dialogu

---

## Menu Opcje

Przycisk **Opcje** w górnym pasku rozwija menu:

| Pozycja | Działanie |
|---------|-----------|
| **Token Setup** | Otwiera istniejący konfigurator tokenów |
| **Stan sesji** | Pokazuje bieżący raport sesji i integracji |
| **Układ kafelków** | Otwiera dotychczasowe opcje widoczności, kategorii i kolejności kafelków |
| **Skróty** | Otwiera edytor bezpośrednich skrótów do komponentów |

Dzięki temu górny pasek pozostaje krótszy, a wszystkie ustawienia launchera są dostępne z jednego miejsca.

---

## Skróty komponentów

Okno **Opcje → Skróty** pokazuje widoczne komponenty wraz z kategorią i aktualnym przypisaniem.

Do komponentu można przypisać:

- jedną literę,
- jedną cyfrę,
- klawisz `F1`–`F12`.

Zasady:

- jeden klawisz może otwierać tylko jeden komponent,
- komponent może mieć tylko jeden bezpośredni skrót,
- przypisanie zajętego klawisza wymaga potwierdzenia i zastępuje wcześniejsze,
- **Usuń skrót** usuwa przypisanie wybranego komponentu,
- **Przywróć domyślne** przywraca `I → Integracja z GPT`,
- skróty nie działają podczas pisania w `Entry`, `Text` lub `Combobox`,
- skróty nie działają w osobnych oknach dialogowych ani w otwartym komponencie inline.

Konfiguracja jest zapisywana lokalnie w:

```text
giclee_app/data/launcher_shortcuts.json
```

Brak albo uszkodzony plik przywraca bezpieczne ustawienie domyślne. Zapis jest atomowy przez plik tymczasowy i `replace`.

---

## Drag-and-drop kafelków

### Kategorie

Na ekranie głównym można przeciągnąć cały kafelek kategorii i upuścić go przed albo za inną kategorią. Kolejność jest zapisywana natychmiast w `section_order` istniejącego pliku:

```text
giclee_app/data/launcher_layout.json
```

Puste lub chwilowo niewidoczne kategorie zachowują swoje miejsce w konfiguracji i nie są kasowane.

### Komponenty

Po otwarciu kategorii można przeciągać kafelki komponentów w dowolne miejsce bieżącej siatki. Launcher:

- rozpoznaje ruch dopiero po przekroczeniu progu kilku pikseli, więc zwykły klik nadal otwiera komponent,
- podświetla kafelek źródłowy i bieżący cel upuszczenia,
- rozróżnia upuszczenie przed i za wskazanym kafelkiem,
- przewija listę, gdy kursor podczas przeciągania zbliży się do górnej lub dolnej krawędzi,
- zapisuje nową kolejność natychmiast po upuszczeniu,
- zachowuje pozycje ukrytych komponentów należących do tej samej kategorii.

Drag-and-drop zmienia wyłącznie kolejność. Przenoszenie komponentu do innej kategorii nadal odbywa się przez **Opcje → Układ kafelków**.

Mechanizm działa na zwykłych zdarzeniach myszy Tkinter i nie wymaga `tkinterdnd2`; biblioteka DnD plików pozostaje niezależna.

---

## Dwupoziomowa nawigacja

### Ekran główny

Każda niepusta sekcja jest prezentowana jako duży kafelek kategorii zawierający:

- ikonę i kolor rozpoznawczy,
- nazwę kategorii,
- krótki opis zakresu,
- liczbę widocznych komponentów.

Komponenty nie są renderowane na ekranie głównym. Dzięki temu liczba elementów startowych pozostaje mała nawet po dodaniu kolejnych narzędzi.

### Ekran kategorii

Po kliknięciu kategorii launcher pokazuje:

- przycisk powrotu do wszystkich kategorii,
- nazwę i liczbę komponentów,
- kafelki komponentów w spójnym układzie 3-kolumnowym,
- etykietę trybu: **W aplikacji**, **Nowe okno** albo **WWW**.

Zmiana widoczności lub przypisania w **Układzie kafelków** automatycznie aktualizuje licznik i zawartość kategorii. Pusta albo usunięta kategoria powoduje bezpieczny powrót do głównego ekranu.

---

## Sekcje UI (stała kolejność domyślna)

Kolejność startowa nie pochodzi z pola `order` w `component.json`. Domyślny podział definiuje `DEFAULT_SECTIONS` w `launcher_layout.py`, a późniejsze zmiany DnD są zapisywane w lokalnym `launcher_layout.json`:

| Kategoria | Komponenty |
|-----------|------------|
| Administracja produktu | dodajobraz, aktualizujopis, zmienceny, wyborszablonu, zmietytuly, tytulyai, nazwijobraz, pobierzobraz, squoosh, print_optimize, mockup, infoplikow, przedpo |
| Administracja strony | wzorzecszablonu, stronaproduktu, karuzela, submenukatalog, tldobio, stronaglowna, gicleeframe, wlasnafotografia, katalog, wspolpraca, filozofiamarki, kontakt, stronablogu, faq, losujobraz |
| Zamówienia | obrazy, produkcja, passepartout |
| Finanse | finanse, kalkulacja; moduły ukryte mogą być otwierane z huba Księgowość |
| Marketing | blog, socialmedia, zadania, cenyMarketing, analytics |
| Narzędzia pomocnicze | limity, planer, notatnik, bazapromptow, wybortrybu, integracjagpt, stronyzobrazami, stronydozycia, poczta, sklep, segregatorplikow |

Komponenty spoza listy trafiają do dodatkowej kategorii **Inne**.

### Układ kafelków

Pozycja **Opcje → Układ kafelków** nadal pozwala zmieniać:

- przypisanie komponentu do kategorii,
- widoczność (`Pokaż`),
- kolejność wewnątrz kategorii (`▲/▼`) jako alternatywę dla DnD.

Zapis: `giclee_app/data/launcher_layout.json`. **Domyślny układ** przywraca fabryczne kategorie i widoczność z `component.json` (`hidden`).

Moduły z `"hidden": true` można włączyć przez **Układ kafelków**.

---

## Tryby uruchomienia

| Tryb | Zachowanie |
|------|------------|
| `subprocess` | `python -m Komponenty.<nazwa>` — osobne okno Tk |
| `inline` | Import `Komponenty.<nazwa>.view` — zamiana siatki kafelków; **← Wróć** prowadzi do ostatnio otwartej kategorii |
| `url` | `webbrowser.open(url)` — np. `sklep` |

Definicja w `component.json` → [`component-loader.md`](component-loader.md)

---

## Logi subprocess

Katalog: `cursor-api/logs/` — stdout/stderr komponentów uruchomionych z launchera.

---

## Powiązane pliki

| Plik | Rola |
|------|------|
| `dragdrop_category_launcher.py` | Obsługa myszy, cel upuszczenia i trwały zapis DnD |
| `launcher_tile_order.py` | Testowalne helpery zmiany kolejności podzbioru |
| `options_category_launcher.py` | Menu Opcje i uruchamianie skrótów użytkownika |
| `launcher_shortcut_options.py` | Okno przypisywania i usuwania skrótów |
| `launcher_shortcuts.py` | Walidacja, odczyt, zapis i konflikty skrótów |
| `styled_category_launcher.py` | Spójny styl kafelków komponentów |
| `category_launcher.py` | Dwupoziomowy ekran kategorii i komponentów |
| `launcher_layout.py` | Kategorie, widoczność i kolejność komponentów |
| `launcher_options.py` | Edycja układu przez użytkownika |
| `component_loader.py` | Discovery + metadata kafelków |
| `runtime.py` | `resolve_python_interpreter`, `GICLEE_PYTHON` |
| `session_status.py` | Tekst raportu sesji Shopify |
| `splash_screen.py` | Ekran startowy (opcjonalnie) |

---

## Miesięczny reminder

Launcher (1.–5. dzień miesiąca) może zaproponować plan marketingowy — patrz kod w `launcher.py`.
