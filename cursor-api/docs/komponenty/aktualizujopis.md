# Komponent: aktualizujopis

**Cel:** Masowa i pojedyncza aktualizacja opisów produktów typu `Obraz` w Shopify — wklejanie tablicy JSON z LLM, podgląd, tłumaczenia 7 języków.

| Plik | Rola |
|------|------|
| `gui.py` | Entry point — uruchamia okno z `dodajobraz/description_update_dialog.py` |
| `description_update_dialog.py` (dodajobraz) | UI: lista produktów, tryby, JSON, porównywarka |
| `description_update.py` (dodajobraz) | Zapis do Shopify, oznaczenia postępu |

Tryb: `subprocess`. Sekcja launchera: **Administracja produktu** (po «Dodaj obraz»).

## Workflow (skrót)

1. Uruchom kafelek **Aktualizuj opis** w GicleeApp.
2. Wybierz produkt z listy (Ctrl+klik / Shift+klik — wiele zaznaczeń). Kolumny: **Akt.** (✓ = pełna aktualizacja), **Wers.** (✓ = wariant w porównywarce), **Do tlum.** (✓ = ręcznie «do tłumaczenia» — klik w komórkę, przycisk paska, PPM; jak tlum. GPT; persystencja: `description_do_tlumaczenia_marks.json`), **tlum. GPT** / **tlum. SONN** / **z obrazu** / **Bez 1-6** (✓ = ręczne oznaczenie; klik w komórkę, PPM lub przyciski paska; persystencja: `description_gpt_translation_marks.json`, `description_sonnet_translation_marks.json`, `description_from_image_marks.json`, `description_bez_16_marks.json`). Filtry **Pokaz:** można włączyć **kilka naraz** (wiersz musi spełnić wszystkie aktywne); **Wszystkie** czyści filtry. Dostępne: Po aktualizacji / Bez oznaczenia / **bez aktualizacji** (brak ✓ w Akt., w tym fioletowe PL) / **do tłumaczenia** (✓) / z obrazu ✓ / bez z obrazu. Przy wielu zaznaczeniach licznik nad listą pokazuje `zaznaczono: N`. Kolory wierszy: zielony / fioletowy (tylko PL) / niebieski (wariant bez Akt.).
3. Wklej tablicę JSON z LLM → **Analizuj JSON** → podgląd akapitów PL + tłumaczeń.
4. **Zastosuj w Shopify** — zapis `body_html` + tłumaczenia; auto-oznaczenie: zielone ✓ gdy zapisano też tłumaczenia, **fioletowe tło** gdy tylko PL (`data/description_pl_pending_marks.json`).
5. **Wklej tłumaczenia do akapitu** — po «Zastosuj» automatycznie uruchamia «Zapisz każdą wersję językową» (bez pytania) i oznacza produkt na **zielono** (✓).
6. **GIGA TŁUMACZENIE** / **Wklej GIGA TŁUMACZENIE** — w sekcji «Podgląd zmian», obok «Prompt tłumaczenia» (zawsze widoczne; aktywne przy ≥2 zaznaczonych produktach). Jeden prompt do schowka z akapitami PL wszystkich pozycji; wklejanie JSON `{produkt_1: {akapit_1: {en,…}, …}, …}`.
7. **JSON obecnych tłumaczeń** — kopiuje do schowka JSON z akapitami z Shopify we wszystkich 7 językach (`akapit_1: {pl, en, de, fr, es, nl, it}, …`); pola `wersja_pierwotna: "pl"` i `uwaga` informują, że **pl** to tekst pierwotny.
8. **Opis z obrazu** / **Opis z obrazu v2** — prompt + grafika do Gemini w **dwoch krokach** (okno pomocnicze: najpierw grafika w schowku, potem «Kopiuj prompt»). Gemini nie wkleja obu formatow jednym Ctrl+V.
9. **Porównywarka** — 10 slotów wersji akapitu: `1`–`6` (domyślnie Sonnet→1, Gemini→3, GPT→5), **ZO1** / **ZO2** (opisy z promptów «Opis z obrazu» / v2) oraz **G1** / **G2** (dodatkowe warianty Gemini). W polach tekstu: **Ctrl+Z** cofa ostatnią edycję (np. przywraca usunięty fragment), **Ctrl+Y** ponawia; historia resetuje się przy zmianie akapitu lub slotu wersji.

Szczegóły trybów, promptów i porównywarki: [`../../SHOP_KNOWLEDGE.md`](../../SHOP_KNOWLEDGE.md) § «Aktualizuj opis».

→ [`README.md`](README.md)
