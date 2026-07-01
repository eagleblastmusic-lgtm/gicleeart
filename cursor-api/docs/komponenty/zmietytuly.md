# Komponent: zmietytuly

**Cel:** Dwuetapowy kreator promptu do zmiany tytułów produktu w Shopify — wynik do schowka, wklejenie w Cursorze.

| Plik | Rola |
|------|------|
| `gui.py` | Krok 1: lista produktów ze sklepu; krok 2: wklejone tytuły z LLM → prompt |
| `description_update.py` (dodajobraz) | Parser pól, `build_title_change_prompt`, `load_product_title_fields`, `apply_product_title_fields` |

Tryb: `subprocess`. Sekcja launchera: **Administracja produktu**.

## Workflow

1. **Krok 1** — lista produktów z Shopify (kolumny: status tytułu, nazwisko, imię…). **Pokaz:** Wszystkie / Po aktualizacji / Bez oznaczenia (jak «Aktualizuj opis»). Wiersze na zielono = `Tytuł zmieniony` (`data/title_update_marks.json`, wspólne z **Tytuły AI**). Przycisk **Oznacz: tytuł po aktualizacji** (ręcznie — jeden lub wiele zaznaczonych; przełącza stan przy wielokrotnym zaznaczeniu). **Lista promptów** — okno z presetami startowymi do nowej rozmowy Gemini (pierwszy: *Ekspert historii sztuki* z `tytulyai/prompts.py`; drugi: starszy krótszy prompt). Podgląd + «Kopiuj» / dwuklik. **Prompt startowy Gemini** — szybkie skopiowanie starszego presetu (jak wcześniej). **PPM** → Oznacz / Odznacz zaznaczone, **Edytuj tytuły w językach…**, «Kopiuj grafikę»… Filtr tekstowy, odświeżanie. Zaznaczenie wielu: Ctrl+klik / Shift+klik. Wybór jednego + «Dalej» lub dwuklik → krok 2.
2. **Krok 2** — wklej blok tytułów (Ctrl+V lub «Wklej ze schowka»). Prompt trafia **automatycznie** do **Schowka**; produkt z listy dostaje oznaczenie **Tytuł zmieniony** (od teraz — przy każdym udanym wklejeniu). Powrót do listy z ostatnim zaznaczeniem. «Wpisz ręcznie» bez ID produktu — bez auto-oznaczenia.
3. **Schowek** — widoczny w kroku 1 i 2; zbiera wiele promptów. «Kopiuj schowek» → wszystkie naraz do systemowego schowka (wklej w Cursor). «Wyczyść» usuwa zawartość.

Przy generowaniu promptu: `A lub B` zamienia się na `A (spójnik B)` w języku pola — np. PL `lub`, EN `or`, DE `oder`, FR `ou`, ES/IT `o`, NL/orig `of`. Przy wielu alternatywach drugi i kolejne spójniki w nawiasie stają się `/` — np. `A (lub B/C)` zamiast `A (lub B (lub C))`.

## Wielkość liter w tytułach

Zachowuj konwencję typową dla danego języka (katalog muzealny):

| Język | Konwencja | Przykład |
|-------|-----------|----------|
| **PL** | Pierwsza litera + nazwy własne | Wielki staw (lub Głęboki staw) |
| **EN** | Title case — główne słowa wielką | The Great Pool |
| **DE** | Rzeczowniki wielką, reszta małą | Der große Teich |
| **FR** | Sentence case | Le grand étang |
| **ES** | Sentence case | El gran estanque |
| **IT** | Sentence case | Il grande stagno |
| **NL / orig** | Sentence case | De grote poel |

Unikaj angielskiego Title Case we FR/ES/IT (np. ~~Le Grand Étang~~ → **Le grand étang**).

Wykonanie zmian na Shopify: skrypt/agent w Cursorze (np. `scripts/fix_*_titles.py`) albo **Edytuj tytuły w językach…** z menu PPM (zapis bezpośrednio przez API).

Alternatywa: komponent **Tytuły AI (Gemini)** — batch z obrazów przez API → prompty do Cursora (patrz [`tytulyai.md`](../tytulyai.md)).

→ [`README.md`](README.md)
