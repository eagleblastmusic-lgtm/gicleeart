# Komponent: losujobraz

**Cel:** edycja wyglądu i treści `templates/page.losuj-produkt.json` dla pozycji menu **Losuj Obraz**.

Tryb: `inline` w sekcji **Administracja strony**. Uruchomienie: `python -m Komponenty.losujobraz`. Podgląd: `/pages/losuj-produkt`.

## Warianty designu w Giclee App

Lista **Wersja** jest selektorem pełnych wariantów strony:

| Wariant | ID | Efekt |
|---|---|---|
| **V1 — podstawowa** | `lo1` / `v1` | Baza bez dodatkowej warstwy atmosfery. |
| **V2 — atmosfera muzealna** | `lo2` / `v2` | Edytowalny glow, mgiełka i pył V2. |
| **V3 — Living Museum Light** | `lo3` / `v3` | Reflektor galerii, pył zależny od światła, handoff do WebGL oraz muzealna tabliczka artysta / tytuł / rok. |

Aktywnym wariantem jest `lo3`. **Zapisz** utrwala bieżący wariant i aktywny szablon przez istniejący workflow kopii zapasowej i zapisu edytora stron.

## Edytuj atmosferę…

Przycisk na pasku narzędzi otwiera strefę ustawień atmosfery bieżącego wariantu.

V2 zachowuje szczegółowe parametry glow, mgiełki i pyłu. V3 udostępnia minimalny zestaw:

- `living_light_enabled` — włącz reflektor;
- `living_dust_enabled` — włącz pył ambientowy;
- `living_light_intensity` — intensywność 0–100, domyślnie 45.

V1 zachowuje wartości w JSON, ale nie ładuje żadnego assetu atmosfery. Dzięki temu przełączanie wariantów nie kasuje strojenia.

## Własne tło

Strefa **Losuj obraz — interfejs** obsługuje obraz, film i `background_parallax`. W V1/V2 parallax pozostaje w głównym kontrolerze. W V3 ten sam model pozycji wskaźnika steruje reflektorem, pyłem i parallaxem, dzięki czemu nie powstaje drugi globalny listener ani konkurująca pętla RAF.

## Pliki danych

- manifest: `Komponenty/losujobraz/data/variants/manifest.json`;
- warianty: `lo1`, `lo2`, `lo3`;
- aktywny szablon: `templates/page.losuj-produkt.json`;
- mapowanie pól: `Komponenty/losujobraz/registry.py`;
- skrót panelu: `Komponenty/losujobraz/gui.py`.

Kod motywu i pełny kontrakt V3 opisuje `docs/motyw/losuj-obraz.md`.
