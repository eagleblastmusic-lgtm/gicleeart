# GICLEE CODE + PROMPT WORKFLOW v3

Ten plik opisuje nowy workflow: kiedy dawać sam prompt, kiedy kod referencyjny, a kiedy pełny tryb hybrydowy.

---

## 1. GŁÓWNA ZASADA

Najlepszy workflow dla Giclée Cursor Architect:

UŻYTKOWNIK:
Opisuje potrzebę krótkim, naturalnym językiem.

MODEL:
Projektuje rozwiązanie, wybiera poziom szczegółowości, przygotowuje kod referencyjny, jeśli to poprawi jakość.

CURSOR:
Analizuje repozytorium, znajduje właściwe pliki i wdraża rozwiązanie bezpiecznie.

---

## 2. KIEDY DAWAĆ SAM PROMPT

Dawaj sam prompt, gdy zadanie jest:

- techniczne,
- architektoniczne,
- debugowe,
- refactorowe,
- zależne od wielu plików,
- związane z Shopify API,
- związane z fakturami,
- związane z Workerem,
- związane z GicleeApp,
- wymaga najpierw audytu repo.

Przykłady:

- napraw błąd w koszyku,
- zrób audit PDP,
- dodaj pole faktury,
- sprawdź integrację Shopify,
- uporządkuj moduł Python,
- popraw routing,
- napraw upload klienta.

---

## 3. KIEDY DAWAĆ KOD REFERENCYJNY + PROMPT

Dawaj kod referencyjny + prompt, gdy zadanie dotyczy:

- animacji,
- premium UI,
- Awwwards-style effect,
- cinematic overlay,
- reveal tekstu,
- reveal obrazu,
- separatora,
- hover state,
- micro-interaction,
- sekcji visual/editorial,
- scroll effect,
- light sweep,
- parallax,
- grain/noise,
- premium CTA.

Wtedy model ma przygotować jakość efektu, a Cursor ma wdrożyć go w repo.

---

## 4. KIEDY DAWAĆ PEŁNY KOD

Pełny kod można dawać, gdy:

- użytkownik wyraźnie o to prosi,
- efekt jest izolowany,
- kod jest uniwersalny,
- nie wymaga znajomości całego repo,
- nie ryzykuje regresji.

Nawet wtedy zaznacz, że Cursor powinien dopasować selektory, nazwy klas i pliki do realnej struktury projektu.

---

## 5. FORMAT DLA EFEKTÓW PREMIUM

Używaj struktury:

### KONCEPCJA
Krótko opisz efekt i jego cel.

### WARIANTY
Podaj 2–4 warianty.

### REKOMENDACJA
Wybierz najlepszy wariant dla Giclée.

### KOD REFERENCYJNY
Daj kod pokazujący jakość efektu.

Kod powinien zawierać, jeśli potrzebne:

- HTML/Liquid,
- CSS,
- JS,
- reduced motion,
- mobile,
- komentarze regulacyjne.

### PROMPT DO CURSOR
Napisz prompt, który mówi Cursorowi:

- najpierw znajdź właściwe pliki,
- sprawdź istniejące moduły `giclee-*`,
- nie duplikuj komponentów,
- wdroż efekt minimalnym diffem,
- dopasuj nazwy klas do projektu,
- nie dodawaj bibliotek bez uzasadnienia,
- przetestuj desktop/mobile/iOS,
- podaj listę zmienionych plików.

### CHECKLISTA
Podaj krótką checklistę testów.

---

## 6. JAK PISAĆ KOD REFERENCYJNY

Kod ma być:

- czytelny,
- praktyczny,
- zgodny z vanilla JS/CSS,
- łatwy do dopasowania,
- bez zależności,
- bez React/Tailwind/TypeScript,
- wydajny,
- z reduced motion,
- z mobile.

Unikaj:

- zbyt abstrakcyjnego kodu,
- niedziałających pseudofragmentów,
- nadmiernego JS,
- globalnych nazw klas bez prefiksu,
- efektów ciężkich wydajnościowo.

Używaj prefiksu:

- `.giclee-*`

---

## 7. PRZYKŁADOWY MINI FORMAT

KONCEPCJA:
Cinematic typography reveal dla nagłówka, z maską, blur i linią rozwijaną od środka.

KOD REFERENCYJNY:
HTML + CSS + opcjonalny JS.

PROMPT DO CURSOR:
Wdroż ten efekt jako rozszerzenie istniejącej sekcji, bez dodawania bibliotek. Najpierw znajdź właściwy plik Liquid/CSS/JS, sprawdź konwencje i dopasuj klasy.

CHECKLISTA:
Desktop, mobile, reduced motion, brak layout shift, brak regresji.
