# GICLEE MOTION REVIEW LOOP v3.3

Procedura poprawiania efektów po wdrożeniu przez Cursor.

Ten plik służy do sytuacji, gdy użytkownik mówi:

- wyszło za szybko,
- jest skokowo,
- wygląda tanio,
- nie jest premium,
- za dużo ruchu,
- za jasne,
- za ciemne,
- dziwnie się przycina,
- efekt nie robi wrażenia,
- na mobile źle działa.

---

## 1. GŁÓWNA ZASADA

Nie dokładaj od razu kolejnych efektów.

Najpierw zdiagnozuj, co psuje premium feeling.

Często problemem nie jest brak efektu, tylko:
- złe tempo,
- złe easing,
- zbyt duży ruch,
- brak maski,
- za mocny blur,
- zły overlay,
- za dużo elementów naraz,
- brak hierarchii wejścia,
- brak mobile fallback,
- konflikt scroll listenerów.

---

## 2. PROCEDURA REVIEW

Gdy użytkownik zgłasza problem, odpowiedz w strukturze:

1. Diagnoza prawdopodobnej przyczyny.
2. Co psuje efekt premium.
3. Jak to poprawić.
4. Prompt naprawczy do Cursor.
5. Checklista po poprawce.

---

## 3. TYPOWE PROBLEMY I NAPRAWY

### Problem: „jest za szybko”

Naprawa:

- zwiększ duration,
- dodaj delay między warstwami,
- użyj premium easing,
- zmniejsz liczbę rzeczy animowanych naraz.

Wartości:

- główny reveal: 1.0–1.6s,
- separator: 0.9–1.4s,
- light sweep: 1.4–2.2s,
- hover: 280–520ms.

---

### Problem: „jest skokowo”

Naprawa:

- animuj `transform` i `opacity`,
- unikaj `width`, `height`, `top`, `left`,
- użyj `requestAnimationFrame` dla scroll progress,
- sprawdź, czy nie ma layout reflow,
- sprawdź, czy nie ma wielu scroll listenerów.

---

### Problem: „wygląda tanio”

Naprawa:

- usuń bounce/elastic,
- zmniejsz ruch,
- dodaj mask reveal zamiast zwykłego fade,
- popraw overlay,
- dodaj subtelny separator,
- usuń neon/glow,
- zwolnij tempo,
- ogranicz efekty do 1–2 elementów.

---

### Problem: „za dużo ruchu”

Naprawa:

- zostaw jeden główny efekt,
- usuń efekty wspierające,
- zmniejsz stagger,
- usuń parallax na mobile,
- animuj grupy zamiast pojedynczych liter.

---

### Problem: „za ciemne”

Naprawa:

- zmniejsz opacity overlayu,
- zostaw jaśniejsze centrum,
- użyj radial spotlight,
- zmniejsz dolny gradient,
- sprawdź kontrast tekstu.

---

### Problem: „za jasne / nieczytelny tekst”

Naprawa:

- dodaj poziomy gradient pod tekst,
- zwiększ przyciemnienie po stronie copy,
- dodaj subtelną winietę,
- nie przyciemniaj całego obrazu równomiernie,
- zachowaj główny obiekt zdjęcia.

---

### Problem: „nie robi wrażenia”

Naprawa:

- dodaj sekwencję, nie pojedynczy efekt,
- połącz typographic reveal + line reveal + light sweep,
- dodaj signature moment, jeśli sekcja jest odpowiednia,
- popraw timing i hierarchię,
- upewnij się, że efekt pasuje do narracji sekcji.

---

### Problem: „na mobile źle działa”

Naprawa:

- uprość efekt,
- animuj słowa zamiast liter,
- usuń parallax,
- zmniejsz blur,
- zmniejsz translate,
- skróć delay,
- dodaj reduced motion,
- sprawdź breakpoint 749px.

---

### Problem: „przycina się”

Naprawa:

- usuń ciężkie filtry,
- ogranicz blur,
- usuń globalne scroll listenery,
- użyj rAF,
- ogranicz liczbę animowanych elementów,
- sprawdź duże obrazy i LCP,
- testuj iOS Safari.

---

## 4. PROMPT NAPRAWCZY — SZABLON

```text
TYP ZADANIA: MOTION/ANIMATION AUDIT + FIX

CEL:
Popraw obecny efekt animacji, ponieważ wygląda [za szybko / skokowo / niepremium / zbyt ciężko / źle na mobile].

NAJPIERW SPRAWDŹ:
Znajdź pliki odpowiedzialne za efekt. Sprawdź CSS, JS, Liquid, klasy, event listenery, IntersectionObserver, requestAnimationFrame, animowane właściwości, duration, easing, delay, mobile breakpointy i reduced motion.

DIAGNOZA:
Przygotuj krótką diagnozę, co powoduje problem. Nie wdrażaj dużych zmian bez wskazania przyczyny.

ZADANIE:
Popraw efekt minimalnym diffem:
- użyj transform/opacity zamiast width/height/top/left,
- zastosuj easing cubic-bezier(0.16, 1, 0.3, 1),
- ustaw spokojniejsze duration,
- zmniejsz translate/blur, jeśli efekt jest przesadzony,
- popraw overlay, jeśli tekst jest nieczytelny,
- uprość mobile,
- dodaj lub popraw prefers-reduced-motion.

OCHRONA:
Nie dodawaj nowych bibliotek. Nie duplikuj istniejących modułów. Nie zmieniaj architektury sekcji. Nie psuj istniejących funkcji.

KRYTERIA AKCEPTACJI:
Efekt jest płynny, spokojny, premium, działa na desktop i mobile, nie powoduje layout shift, nie ma błędów console i ma reduced motion.

NA KONIEC:
Podaj zmienione pliki, opis poprawki, ocenę jakości efektu 1–5 i instrukcję testowania.
```

---

## 5. OCENA PO POPRAWCE

Po każdej poprawce Cursor ma podać:

- czy efekt jest płynny,
- czy wygląda bardziej premium,
- ocena 1–5,
- co jeszcze trzeba poprawić do 5/5,
- czy działa mobile,
- czy działa reduced motion,
- czy są ryzyka performance,
- czy dodano nowe zależności.

---

## 6. ZASADA ITERACJI

Pierwsza wersja efektu często jest tylko technicznie poprawna.

Premium motion często wymaga 2–3 iteracji:

1. Wersja techniczna.
2. Poprawa tempa, easing i mobile.
3. Dopieszczenie światła, maski i rytmu.

Nie traktuj iteracji jako błędu. To normalna część pracy nad efektem premium.

---

## 7. FINALNA ZASADA

Jeśli efekt nie wygląda premium, nie pytaj od razu o nowy efekt.

Najpierw popraw:
- tempo,
- easing,
- hierarchię,
- overlay,
- mobile,
- reduced motion.

Dopiero potem dodawaj kolejne warstwy.
