# Wstaw ekran — instrukcja modułu dla AI

Polecenie `Wstaw ekran` oznacza użycie wspólnego modułu pustej sekcji
viewportowej.

## Kontrakt

1. W menu PPM panelu `Sekcje strony` pokaż `Wstaw ekran…`.
2. Zapytaj o wysokość w `vh`; `100 vh` oznacza jeden pełny viewport.
3. Dodaj nową sekcję typu `giclee-viewport-screen` bezpośrednio po sekcji,
   na której otwarto menu.
4. Zachowaj sekcję w `sections` oraz jej pozycję w `order` bieżącego wariantu.
5. Pokaż nową pozycję na liście sekcji i udostępnij ręcznie wpisywane pole
   `viewport_height_vh`. Dwuklik listy nadal zmienia nazwę sekcji.
6. Do kontrolowanego wdrożenia dołącz
   `sections/giclee-viewport-screen.liquid`.
7. Nie realizuj ekranu przez `margin`, `padding` ani modyfikowanie wysokości
   sąsiedniej sekcji.
8. Po kliknięciu PPM na utworzonym ekranie pokaż `Usuń ekran…`. Akcja usuwa
   tylko sekcję typu `giclee-viewport-screen` oraz jej wpis z `order` i wymaga
   potwierdzenia. Powiązanych warstw tekstowych nie kasuj po cichu — zachowaj
   je jako osierocone dane zgodnie z kontraktem modułu `Dodaj tekst`.

## Pliki wspólne

- model i wykrywanie:
  `cursor-api/Komponenty/_shared/theme_page_editor/viewport_screen.py`;
- menu i edytor:
  `cursor-api/Komponenty/_shared/theme_page_editor/gui_shell.py`;
- GICLÉE FRAME™:
  `cursor-api/giclee_app/ui/gicleeframe_view_film_scroll_context.py`;
- frontend Shopify:
  `sections/giclee-viewport-screen.liquid`;
- test kontraktu:
  `cursor-api/Komponenty/_shared/theme_page_editor/test_viewport_screen.py`.
