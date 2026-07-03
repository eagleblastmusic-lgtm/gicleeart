# Komponent: stronydozycia

**Cel:** Osobista lista linków do stron (sklep, Shopify Admin, narzędzia zewnętrzne) z opisem **co na nich można robić**.

| Plik | Rola |
|------|------|
| `gui.py` | Okno: lista, filtr, opis, CRUD |
| `storage.py` | Zapis JSON w `data/pages.json` |

Tryb: `subprocess`. Sekcja launchera: **Narzędzia pomocnicze**.

## Workflow

1. **+ Dodaj** — nazwa, URL, kategoria, opis działań.
2. **Wklej linki…** — masowy import z schowka (`Nazwa | URL` lub sam URL).
3. Zaznacz wiersz → pole **Co można robić** — edycja inline (zapis przy utracie fokusu lub Ctrl+S).
4. **Otwórz** / dwuklik — przeglądarka.
5. Filtr po kategorii i tekście (szuka też w opisie).

## Dane

- `data/pages.json` — wpisy: `title`, `url`, `description`, `category`, `sort_key`
- Domyślne kategorie: Sklep, Shopify Admin, GicleeApp, Narzędzia, Inne (można dodać własne przy edycji)

→ [`README.md`](README.md)
