# Launcher (`launcher.py`)

Hub GicleeApp: [`README.md`](README.md)

Plik: `cursor-api/giclee_app/launcher.py`

---

## Co robi

- Okno Tkinter z siatką kafelków komponentów
- Uruchamia komponenty jako **osobne procesy** (`subprocess`) lub **inline views** w tym samym oknie
- Toolbar: **Stan sesji**, **Dziennik akcji**, **Odśwież**
- Co 3 s skanuje `Komponenty/` w tle (nowe kafelki)

---

## Sekcje UI (stała kolejność)

Kolejność w launcherze **nie** pochodzi z pola `order` w `component.json` — jest hardcoded w `_SECTIONS`:

| Sekcja | Komponenty |
|--------|------------|
| Administracja produktu | dodajobraz, aktualizujopis, zmienceny, wyborszablonu, zmietytuly, tytulyai, nazwijobraz, pobierzobraz, squoosh, print_optimize, mockup, infoplikow |
| Zamówienia | obrazy, produkcja, passepartout |
| Finanse | finanse — kafelek **Księgowość**; kalkulacja (Kalkulator kosztów); kpir, dnr, dokumentysprzedazy ukryte — otwierane z panelu Księgowość |
| Marketing | blog, socialmedia, zadania, cenyMarketing |
| Narzędzia pomocnicze | limity, planer, notatnik, bazapromptow, stronyzobrazami, poczta, sklep |

Komponenty spoza listy → sekcja **Inne**.

Nagłówki sekcji są **rozwijane** (klik w pasek lub strzałkę ▼/▶) — stan zwinięcia zachowany do odświeżenia listy komponentów. Każdy nagłówek steruje własną sekcją (nie ostatnią na liście).

### Opcje (układ kafelków)

Przycisk **Opcje** w pasku narzędzi: przypisanie kafelka do sekcji, widoczność (Pokaż), kolejność w sekcji (▲/▼). Zapis: `giclee_app/data/launcher_layout.json`. **Domyślny układ** przywraca fabryczne sekcje i widoczność z `component.json` (`hidden`).

Moduły z `"hidden": true` (np. kpir, dnr) można włączyć na siatce przez Opcje.

Kod: `launcher_layout.py`, `launcher_options.py`.

---

## Tryby uruchomienia

| Tryb | Zachowanie |
|------|------------|
| `subprocess` | `python -m Komponenty.<nazwa>` — osobne okno Tk |
| `inline` | Import `Komponenty.<nazwa>.view` — zamiana siatki kafelków; **← Wróć** do startu przywraca rozmiar **920×780** (centrum ekranu) |
| `url` | `webbrowser.open(url)` — np. `sklep` |

Definicja w `component.json` → [`component-loader.md`](component-loader.md)

---

## Logi subprocess

Katalog: `cursor-api/logs/` — stdout/stderr komponentów uruchomionych z launchera.

---

## Powiązane pliki

| Plik | Rola |
|------|------|
| `component_loader.py` | Discovery + metadata kafelków |
| `runtime.py` | `resolve_python_interpreter`, `GICLEE_PYTHON` |
| `session_status.py` | Tekst raportu sesji Shopify |
| `splash_screen.py` | Ekran startowy (opcjonalnie) |

---

## Miesięczny reminder

Launcher (1.–5. dzień miesiąca) może zaproponować plan marketingowy — patrz kod w `launcher.py`.
