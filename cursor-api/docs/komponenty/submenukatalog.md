# Submenu katalog

Animowana lista artystów w rozwijanym panelu menu **Katalog** (nawigacja główna).

## Uruchomienie

Tryb: `inline` (sekcja **Administracja strony**). Uruchomienie: `python -m Komponenty.submenukatalog`.

## Dane

| Plik | Rola |
|------|------|
| `Komponenty/submenukatalog/data/variants/manifest.json` | Aktywny wariant |
| `Komponenty/submenukatalog/data/variants/<id>/giclee-catalog-submenu-config.json` | Konfiguracja wariantu |
| `assets/giclee-catalog-submenu-config.json` | Deploy target — czytany przez motyw |

## Strefy edycji

- **Lista artystów** — liczba kolumn, nagłówek «Artyści», ukryci autorzy (handle kolekcji, jeden na linię)
- **Animacja wejścia** — opóźnienie, kaskada, odstępy między linkami
- **Wygląd panelu** — pole readonly **Grafika** (V1/V2), szerokość podglądu, maks. wysokość panelu

## Warianty grafiki

- **V1** — dotychczasowy filtr `brightness(0.5) saturate(0.75)`.
- **V2** — jaśniejszy obraz (`brightness(0.68) saturate(0.88) contrast(1.02)`) i lokalny gradient wyłącznie pod tekstem.
- Motyw zapisuje wybór jako `data-preview-graphics-variant` na `#giclee-catalog-panel`.

## Motyw

`layout/theme.liquid` ładuje `assets/giclee-catalog-submenu-config.json` i ustawia zmienne CSS (`--giclee-catalog-preview-width`, `--giclee-catalog-list-columns`, …).

Ukryci autorzy: panel Katalog + menu mobilne. Kolekcja nadal działa pod bezpośrednim URL.

## Powiązane

- [`katalog.md`](katalog.md) — strona kolekcji
- [`docs/motyw/kolekcja-autora-showcase.md`](../../docs/motyw/kolekcja-autora-showcase.md) — synchronizacja list ukrytych autorów
