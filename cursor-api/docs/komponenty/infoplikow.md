# Komponent: infoplikow

**Cel:** Podgląd grafik produktu w Shopify — nazwa pliku na CDN, tekst alt, rola (preview / Full / mockup), widoczność w galerii PDP.

| Plik | Rola |
|------|------|
| `gui.py` | Okno: lista produktów + tabela grafik |
| `product_files.py` | Pobieranie z REST API, klasyfikacja ról |

Tryb: `subprocess`. Sekcja launchera: **Administracja produktu** (po «Mock-up»).

## Workflow

1. Uruchom kafelek **Informacje o plikach** w GicleeApp.
2. Wybierz produkt z listy (filtr tekstowy, sortowanie po kolumnie Artysta).
3. Dolna tabela pokazuje wszystkie zdjęcia galerii: pozycja, plik CDN, alt, rola, czy widoczne na PDP, czy główne, wymiary, przypisane warianty.
4. PPM na wierszu grafiki: otwórz URL, kopiuj URL / alt / miniaturkę. Dwuklik — otwiera grafikę w przeglądarce.
5. Przyciski **Admin Shopify** i **Strona produktu (PL)** — szybki podgląd w adminie i na froncie.

→ [`README.md`](README.md)
