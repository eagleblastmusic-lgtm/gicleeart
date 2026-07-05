# Komponent: stronydozycia

**Cel:** Osobista lista linków do stron (sklep, Shopify Admin, narzędzia zewnętrzne, **inspiracje WWW**) z opisem **co na nich można robić** albo **co jest fajnego** (design/UX).

| Plik | Rola |
|------|------|
| `gui.py` | Okno: lista, filtr, opis, CRUD |
| `storage.py` | Zapis JSON w `data/pages.json`, `CATEGORY_INSPIRATIONS`, etykiety opisu |

Tryb: `subprocess`. Sekcja launchera: **Narzędzia pomocnicze**.

## Workflow

1. **+ Dodaj** — nazwa, URL, kategoria, opis.
2. **Wklej linki…** — masowy import z schowka (`Nazwa | URL` lub sam URL).
3. Zaznacz wiersz → pole opisu — edycja inline (zapis przy utracie fokusu lub Ctrl+S).
4. **Otwórz** / dwuklik — przeglądarka.
5. Filtr po kategorii i tekście (szuka też w opisie).

## Kategoria «Inspiracje WWW»

- Domyślna kategoria w dialogach **+ Dodaj** i **Wklej linki…**, gdy filtr listy = **Inspiracje WWW**.
- Etykieta opisu zmienia się dynamicznie:
  - **Inspiracje WWW** → «Co jest fajnego»
  - pozostałe kategorie → «Co można robić»
- Typowy workflow: filtr **Inspiracje WWW** → wklej linki → uzupełnij opis (hero, nawigacja, animacje, PDP itd.).

## Dane

- `data/pages.json` — wpisy: `title`, `url`, `description`, `category`, `sort_key`
- Domyślne kategorie: Sklep, Shopify Admin, GicleeApp, Narzędzia, Inspiracje WWW, Inne (można dodać własne przy edycji)

→ [`README.md`](README.md)
