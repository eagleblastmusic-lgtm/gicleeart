# Komponent: wyborszablonu

**Cel:** Przegląd produktów typu `Obraz` z przypisanym szablonem wariantów (ceny, opcje) oraz zarządzanie szablonami bez wchodzenia w pełny edytor «Szablony...».

| Plik | Rola |
|------|------|
| `gui.py` | Entry point GicleeApp |
| `dodajobraz/product_template_dialog.py` | UI: lista produktów + panel szablonów |
| `dodajobraz/product_template_assignments.py` | Mapowanie `product_id → template_id` |
| `dodajobraz/templates.py` | CRUD szablonów, stosowanie do Shopify |
| `dodajobraz/data/variant_templates.json` | Definicje szablonów wariantów |
| `dodajobraz/data/product_template_assignments.json` | Jawne przypisania produkt → szablon |

Tryb: `subprocess`. Sekcja launchera: **Administracja produktu** (po «Zmień ceny»).

## Workflow

1. Uruchom kafelek **Wybór szablonu produktu**.
2. Lista produktów (artysta, tytuł, handle, kolumna **Szablon**). Kolory: zielony = jawne przypisanie, szary = domyślny lub dopasowany po wariantach.
3. **Panel szablonów** (prawa kolumna):
   - wybór szablonu z listy,
   - **Zapisz nazwę** — zmiana nazwy szablonu w `variant_templates.json`,
   - **+ Nowy pusty** / **+ Z Shopify...** / **Kopiuj** — tworzenie szablonu,
   - **Edytuj warianty (Szablony...)** — pełny edytor wariantów i cen.
4. Zaznacz produkt(y) + szablon → **Przypisz szablon** — zapis mapowania (bez zmian w Shopify).
5. **Zastosuj w Shopify** — dopasowuje warianty produktu do szablonu (jak w «Szablony... → Zastosuj do produktu») i zapisuje przypisanie.

Przy braku jawnego przypisania kolumna Szablon pokazuje dopasowanie po strukturze wariantów `(dopas.)` lub szablon domyślny `(dom.)`.

→ [`README.md`](README.md)
