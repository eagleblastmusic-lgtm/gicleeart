# Komponent: dodajobraz

Hub: [`README.md`](README.md)

**Cel:** Tworzenie produktów reprodukcji w Shopify — zdjęcie → LLM prompt → produkt + tłumaczenia + smart collections + opcjonalnie zoom HD (R2).

---

## Wejście / wyjście

| Wejście | Wyjście |
|---------|---------|
| Plik `Artysta - Tytuł.jpg` | Produkt Shopify (REST + GraphQL translations) |
| JSON z LLM (prompt) | Tagi, opisy 7 języków, metafields |
| Obraz wysokiej rozdzielczości | Kafelki zoom → R2 + metafield `custom.zoom_manifest` |

---

## Kluczowe pliki

| Plik | Rola |
|------|------|
| `gui.py` | Tkinter: kolejka, drag-drop |
| `price_change_dialog.py` | Używany przez komponent **zmienceny** (nie z GUI dodajobraz) |
| `create.py` | Orkiestrator tworzenia produktu |
| `shopify_client.py` | REST + GraphQL (współdzielony z innymi komponentami) |
| `prompt_builder.py` | Prompt LLM + walidacja JSON |
| `parser.py` | `Artysta - Tytuł.jpg`, sufiksy F2/KK/WK |
| `zoom_publish.py` | Kafelki → R2 → metafield zoom |
| `zoom_tiles.py` | Generowanie pakietu kafelków |
| `r2_storage.py` | Upload do bucket `giclee-zoom` |
| `markets_config.json` | 7 rynków, markup — edycja w komponencie **zmienceny** |

---

## Zależności

| Moduł | Od czego |
|-------|----------|
| `_shared/fx_rates.py` | Kursy NBP (używane w **zmienceny**) |
| `_shared/activity_log.py` | Dziennik akcji |
| `zmienceny` | [`zmienceny.md`](zmienceny.md) — masowa zmiana cen + rynki |
| `.shopify_session.json` | Wszystkie wywołania API |

**Warstwa pusty:** metafield `zoom_manifest` → [`../../../docs/motyw/produkt-i-zoom.md`](../../../docs/motyw/produkt-i-zoom.md)

---

## Flow (skrót)

1. Drag-drop pliku → parser `(artist, title)`
2. GUI generuje prompt → użytkownik wkleja JSON z LLM
3. `create_painting_product()` → Shopify + smart collections + translations
4. Opcjonalnie: zoom HD → R2 + metafield

---

## SHOP_KNOWLEDGE

§4 (architektura), §9 (shopify_client), flow `dodajobraz` w §4

---

## Skrypty masowe (Shopify)

| Skrypt | Cel |
|--------|-----|
| `scripts/backfill_option_translations.py` | Tłumaczenia opcji wariantów (7 języków) |
| `scripts/rename_size_s_to_m.py` | Zmiana wartości opcji **Rozmiar** `S` → `M` (GraphQL `productOptionUpdate`) |

`rename_size_s_to_m`: domyślnie **dry-run**; `--apply` zapisuje. Filtr: vendor `Giclee Art`, typ `Obraz` (flagi `--all-vendors`, `--product-id`).

---

## Typowe błędy

| Objaw | Sprawdź |
|-------|---------|
| 401 API | OAuth — [`../zaleznosci-wewnetrzne.md`](../zaleznosci-wewnetrzne.md) |
| Zoom nie na stronie | Metafield + szablon `nowy-szblon-produktu` |
| Zły markup rynku | `markets_config.json` vs Shopify Catalog |
| Limity R2 / Cloudflare | Przycisk **Cloudflare** w GUI · [`USLUGI.md`](../../../USLUGI.md) |

→ [`../../../docs/zaleznosci.md`](../../../docs/zaleznosci.md)
