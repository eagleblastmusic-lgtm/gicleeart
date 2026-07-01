# Zmień ceny (`zmienceny`)

Masowa aktualizacja cen wariantów we **wszystkich** produktach typu „Obraz” w Shopify + widok **Rynki…** (markup per rynek).

## Uruchomienie

- Kafelek **Zmień ceny** w sekcji **Administracja produktu** (GicleeApp)
- `python -m Komponenty.zmienceny`

## Implementacja

| Plik | Rola |
|------|------|
| `gui.py` | Cienki wrapper — `open_price_change_dialog` z `dodajobraz` |
| `dodajobraz/price_change_dialog.py` | Dialog cen, widok Rynki, push markupów do Shopify |
| `dodajobraz/create.py` | `get_reference_variant_rows`, `update_all_product_prices` |
| `dodajobraz/markets.py` | `markets_config.json`, kolumna **W EUR** |
| `dodajobraz/market_variant_prices.py` | Reczne ceny grup (drewno+rozmiar) per rynek w dialogu Rynki |
| `kalkulacja/variant_template_sync.py` | **Zaktualizuj w szablonie** — zapis cen do `variant_templates.json` |
| `kalkulacja/calculator.py` | Cena w nawiasie (M→A4, L→A3+, XL→A2; legacy S→A4), **Zastosuj ceny z nawiasu** |

## Flow

1. Pobranie wzorcowych wariantów z produktu referencyjnego
2. Widok **Globalny** / **Szczegółowy** — wpisanie nowych cen (PL, cały katalog)
3. **Rynki…** — markup % per rynek; **rozwiń rynek** → pozycje jak w Globalnym (drewno+rozmiar): PL baza, auto z markupu, **Cena (edycja)** (double-click); zapis w `market_variant_prices.json` (puste = auto)
4. **Zatwierdź** — masowy update wariantów w katalogu (ceny PL)

## Zależności

- `.shopify_session.json` + scope do rynków (`read_markets` / `write_markets`) przy sync Shopify
- `_shared/fx_rates.py` — kursy NBP w widoku Rynki

→ [`dodajobraz.md`](dodajobraz.md) · [`kalkulacja.md`](kalkulacja.md)
