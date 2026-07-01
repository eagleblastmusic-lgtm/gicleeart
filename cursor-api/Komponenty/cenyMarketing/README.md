# Ceny w marketingu

Samodzielna aplikacja webowa z analizą cen marketingowych dla reprodukcji giclée GicleeArt — trzy rozmiary (M/L/XL), dwa typy ramy (sosna/dąb), siedem rynków UE.

## Uruchomienie

**Dwuklik na `Ceny w marketingu.cmd`** — otwiera aplikację w domyślnej przeglądarce.

Albo bezpośrednio: dwuklik na `index.html`.

Aplikacja **nie wymaga** Node.js, npm, Vite ani niczego — to czysty HTML + CSS + JS, działa offline.

## Co zawiera (v3.0)

1. **Jasny / ciemny motyw** (zapamiętany w localStorage)
2. **Reality Check** — porównanie z realnymi cenami konkurencji (Manufaktura Obrazów, Desenio, JUNIQE, King & McGaw, Galeria Klasyki, Masiulaniec) z linkami do weryfikacji
3. **Kalkulator cen** — interaktywny, dla każdego rozmiaru/drewna/rynku
4. **Spec produktów** M/L/XL z pozycjonowaniem
5. **3 strategie cenowe (przełącznik na żywo)**: penetracja / aktualna / ultra-premium — aktualizuje WSZYSTKIE sekcje
6. **Analiza kosztów i marży** + wykres marż
7. **Pełen cennik 7 rynków × 6 wariantów**
8. **Symulator miesięcznego P&L** (suwaki + breakdown + break-even)
9. **Symulator zmiany ceny (what-if)** z modelem elastyczności cenowej
10. **Kalkulator LTV/CAC/ROAS** — ile możesz wydać na pozyskanie klienta z Meta/Google Ads
11. **Bundle pricing** — 6 gotowych zestawów z policzonymi marżami
12. **Kalendarz promocji 2026** — kiedy puszczać akcje (12 miesięcy)
13. **Storytelling cheat-sheet** — 6 gotowych komunikatów uzasadniających premium cenę
14. **Psychologia końcówek cen**
15. **6 strategii marketingowych**
16. **Specyfika kulturowa 7 rynków UE**
17. **Czego unikać**
18. **Wnioski** w jednym akapicie

## Zmiany

Wszystkie ceny i koszty są w `app.js` (obiekt `PRODUCTS`). Wystarczy edytować i odświeżyć stronę (`F5`).

Markupy rynkowe — w `app.js` w obiekcie `MARKETS`. Trzymaj zsynchronizowane z `cursor-api/Komponenty/dodajobraz/markets_config.json`.
