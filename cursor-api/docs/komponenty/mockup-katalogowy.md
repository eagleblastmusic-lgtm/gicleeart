# Komponent: mockup (katalogowy)

Hub: [`README.md`](README.md)

**Cel:** Wstawienie reprodukcji w szablon ramki A4 (CZB/CZCZ, pion/poziom) → upload jako zdjęcie produktu w Shopify z sufiksem `(mockup)`.

**To NIE jest mockup klienta** na stronie sklepu. Mockup klienta = [`../../../docs/motyw/mockup-wlasna-fotografia.md`](../../../docs/motyw/mockup-wlasna-fotografia.md) + Worker.

---

## Wejście / wyjście

| Wejście | Wyjście |
|---------|---------|
| Obraz reprodukcji + szablon ramki | WEBP mockup w galerii produktu Shopify |
| Nazwa pliku `Artysta - Tytuł.jpg` | Parsowanie przez `dodajobraz.parser` |

---

## Kluczowe pliki

| Plik | Rola |
|------|------|
| `gui.py` | Kolejka drag-drop, podgląd, eksport na dysk, wysyłka do Shopify |
| `compositor.py` | PIL: cover w polu A4, wykrywanie slotu |
| `publish.py` | Render, `save_mockup_to_disk`, `add_follow_up_image` (Shopify) |
| `templates.py` | `data/templates.json` + `assets/*.png` |
| `transparent.py` | Wersje przezroczyste mockupow + metafield `custom.mockup_display` |
| `transparent_dialog.py` | GUI: lista produktow, upload z dysku, wybor wersji, usuwanie |
| `data/templates.json` | Definicje szablonow CZB/CZCZ |

---

## Przezroczyste mockupy (PDP)

Przycisk **Przezroczyste...** w toolbarze:

1. Lista produktow typu Obraz (Shopify).
2. Po wyborze produktu — mockupy z galerii (oryginalny / przezroczysty).
3. **Dodaj wersje przezroczysta...** — zaznacz oryginalny mockup, wybierz plik z dysku (ramka + grafika z alfa, bez bialego passe-partout). Alt: `… - (mockup) - CZB - (przezroczysty)`. Gdy wersja juz istnieje — pytanie o zastapienie.
4. **Wyswietlaj na stronie** — zapis metafieldu JSON `custom.mockup_display`, np. `{"CZB":"transparent","CZCZ":"original"}`.
5. **Usun zaznaczone mockupy** — usuwa pliki z galerii Shopify.

Motyw: `snippets/giclee-product-gallery.liquid` — dla kazdego wariantu pokazuje tylko wybrana wersje (domyslnie oryginalna). Slajdy `--transparent` maja lzejsza scene i mniejszy padding.

---

## Zależności

| Moduł | Od czego |
|-------|----------|
| `dodajobraz/create.add_follow_up_image` | Upload zdjęcia do produktu |
| `dodajobraz/parser.py` | Nazewnictwo plików |

Używany też przez `socialmedia/cykl/images.py` (szukanie plików MOCKUP).

---

## SHOP_KNOWLEDGE

Sekcja architektury §4 — folder `mockup/`

---

## Typowe błędy

| Objaw | Sprawdź |
|-------|---------|
| Złe kadrowanie | `compositor.py`, orientacja szablonu |
| Brak produktu | Parser nazwy — produkt musi istnieć w Shopify |
| «Braki na stronie» mimo mockupu w adminie | Alt mógł stracić `(mockup)` przy aktualizacji tytułu — skan patrzy też na URL pliku (`parser.mockup_suffixes_in_product_images`) |
| Dogrywanie: 4 błędy, brak preview | Fallback na Full/WK; tytuł z `/` w nazwie pliku tymczasowego — `_safe_temp_artwork_name` w `publish.py` |
| Mockup w Shopify, brak w galerii PDP | Alt stracił `(mockup)` — `repair_alts.py` lub deploy `giclee-product-gallery.liquid` (src CDN) |

→ [`../../../docs/zaleznosci.md`](../../../docs/zaleznosci.md)
