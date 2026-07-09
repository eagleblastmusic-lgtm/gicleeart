# GICLEE EFFECT LIBRARY v3.1

Biblioteka efektów dla Giclée Cursor Architect.  
Ten plik daje modelowi gotowe typy efektów premium / cinematic / Awwwards, które może adaptować do konkretnych sekcji strony Giclée Art.

---

## GŁÓWNA ZASADA

Nie wybieraj efektu losowo.

Najpierw oceń:

- gdzie jest tekst,
- gdzie jest obraz,
- czy tło jest jasne czy ciemne,
- czy sekcja jest hero, PDP, kolekcją, koszykiem czy stroną informacyjną,
- czy efekt ma działać on-load, on-scroll, on-hover czy jako przejście między sekcjami,
- czy efekt wspiera narrację Fine Art,
- czy nie psuje wydajności i mobile.

Dopiero potem wybierz efekt z biblioteki lub połącz 2–3 efekty w jeden spójny moment.

---

# 01. PREMIUM TYPOGRAPHY REVEAL

## Zastosowanie

- nagłówki hero,
- tytuły sekcji,
- komunikaty typu „Dzień dobry”,
- hasła brandowe,
- splash screen,
- manifest marki.

## Efekt

Tekst pojawia się spod maski, z delikatnym blur i kontrolowanym staggerem.

## Składniki

- wrapper z `overflow: hidden`,
- słowa lub litery jako osobne spany,
- `transform: translateY(110%)`,
- `opacity: 0`,
- `filter: blur(8px)`,
- wejście do `translateY(0)`, `opacity: 1`, `blur(0)`,
- opcjonalny light sweep,
- opcjonalna cienka linia po tekście.

## Parametry

- duration: 1.0–1.6s,
- stagger: 40–80ms,
- easing: `cubic-bezier(0.16, 1, 0.3, 1)`.

## Uwaga

Na mobile często lepiej animować słowa, nie pojedyncze litery.

---

# 02. CINEMATIC SECTION OVERLAY

## Zastosowanie

- hero z obrazem,
- sekcje z dużym background image/video,
- galerie,
- strony kolekcji,
- sekcje Restoration / Fine Art / Frame.

## Efekt

Zaawansowana nakładka z kilku gradientów, która poprawia czytelność i nadaje filmowy klimat.

## Składniki

- radial-gradient jako winieta / spotlight,
- linear-gradient poziomy pod tekst,
- linear-gradient pionowy dla cięższego dołu,
- subtelny warm tint,
- opcjonalny grain.

## Warianty

- `left-copy` — tekst po lewej, mocniej ciemna lewa strona,
- `right-copy` — tekst po prawej,
- `center-spotlight` — ważny obiekt w centrum,
- `museum-warm` — cieplejszy, galeryjny klimat,
- `dark-cinematic` — mocniejszy, filmowy look.

## Uwaga

Nie używaj prostego `rgba(0,0,0,0.5)` jako finalnego rozwiązania.

---

# 03. SEPARATOR LINE EXPANSION

## Zastosowanie

- dividers między sekcjami,
- linia pod nagłówkiem,
- splash screen,
- sekcje editorial,
- homepage stack.

## Efekt

Cienka linia rozwija się od środka na lewo i prawo.

## Składniki

- pseudo-element lub osobny div,
- `transform: scaleX(0)`,
- `transform-origin: center`,
- reveal do `scaleX(1)`,
- `opacity` 0 → 1.

## Parametry

- duration: 0.9–1.4s,
- delay: po wejściu nagłówka,
- easing: `cubic-bezier(0.16, 1, 0.3, 1)`.

## Uwaga

Nie animuj `width`, użyj `transform`.

---

# 04. MUSEUM IMAGE REVEAL

## Zastosowanie

- obrazy dzieł,
- mockupy ram,
- zdjęcia procesu,
- detale materiałów,
- zdjęcia Fine Art restoration.

## Efekt

Obraz pojawia się przez maskę, z minimalnym scale-down i subtelnym rozjaśnieniem.

## Składniki

- wrapper z overflow hidden,
- obraz startuje jako `scale(1.04)`,
- mask / clip-path odsłania obraz,
- overlay opacity schodzi do 0,
- opcjonalny gradient shadow na krawędziach.

## Parametry

- duration: 1.2–1.8s,
- scale: 1.04 → 1.0,
- blur: maksymalnie 4–8px, ostrożnie.

## Uwaga

Nie deformuj reprodukcji i nie zmieniaj ich kolorystyki agresywnymi filtrami.

---

# 05. PRODUCT CARD LUXURY HOVER

## Zastosowanie

- listing produktów,
- karuzele,
- rekomendacje,
- kolekcje autorów.

## Efekt

Karta reaguje subtelnie: obraz minimalnie skaluje się, tekst dostaje delikatny underline reveal, a cień/głębia rośnie bardzo spokojnie.

## Składniki

- image scale 1 → 1.025,
- opacity overlay 0 → 0.08,
- underline reveal,
- micro movement ikony 2–4px,
- transition 300–500ms.

## Uwaga

Nie używać bounce, neon glow, mocnego box-shadow ani dużego zoomu.

---

# 06. EDITORIAL SCROLL REVEAL

## Zastosowanie

- teksty sekcji,
- akapity edukacyjne,
- proces produkcji,
- sekcje trust,
- manifest.

## Efekt

Treść pojawia się w kolejności: label → headline → line → paragraph → CTA.

## Składniki

- IntersectionObserver,
- klasy `.is-visible`,
- transform/opacity/filter,
- stagger przez CSS variables.

## Parametry

- translateY: 16–36px,
- duration: 0.9–1.3s,
- delay między elementami: 80–160ms.

## Uwaga

Nie revealować wszystkiego naraz. Rytm ma prowadzić wzrok.

---

# 07. CINEMATIC LIGHT SWEEP

## Zastosowanie

- duże nagłówki,
- CTA,
- logo/splash,
- wybrane premium akcenty.

## Efekt

Bardzo subtelne światło przechodzi przez tekst lub przycisk.

## Składniki

- pseudo-element `::after`,
- gradient liniowy,
- `transform: translateX(-120%) → translateX(120%)`,
- mix-blend-mode opcjonalnie,
- opacity niska.

## Parametry

- duration: 1.4–2.2s,
- delay po reveal,
- opacity: 0.08–0.22.

## Uwaga

Ma wyglądać jak miękkie światło na papierze lub druku, nie jak tani błysk.

---

# 08. GALLERY CURTAIN TRANSITION

## Zastosowanie

- przejścia między sekcjami,
- wejście galerii,
- przejście na stronach kolekcji,
- duże visual moments.

## Efekt

Ciemna kurtyna/warstwa powoli odsłania obraz lub sekcję.

## Składniki

- overlay absolutny,
- transform scaleY/translateY,
- clip-path reveal,
- delayed content reveal.

## Parametry

- duration: 1.1–1.8s,
- easing premium,
- content delay: 150–300ms.

## Uwaga

Nie przesadzać z teatralnością. Giclée ma być spokojne i muzealne.

---

# 09. FINE ART PARALLAX FRAME

## Zastosowanie

- ramy,
- mockupy,
- hero produktowe,
- sekcje Giclée Frame™.

## Efekt

Warstwy obrazu, ramy i tła przesuwają się z minimalnie inną prędkością podczas scrolla.

## Składniki

- CSS variables z progress,
- requestAnimationFrame,
- minimalne translateY,
- optional scale.

## Parametry

- translateY: maksymalnie 8–24px,
- scale: maksymalnie 1.02,
- mobile: ograniczyć albo wyłączyć.

## Uwaga

Nie używać mocnego parallaxu na dziełach sztuki. Ma dawać głębię, nie efekt 3D z reklamy.

---

# 10. PREMIUM CTA MICRO-INTERACTION

## Zastosowanie

- przyciski,
- linki,
- checkout,
- „Zobacz kolekcję”,
- „Stwórz swój wydruk”.

## Efekt

Przycisk ma spokojny fill, delikatny underline/border i minimalny ruch ikony.

## Składniki

- pseudo-element background fill,
- border color transition,
- icon translateX 2–5px,
- focus-visible state,
- reduced motion.

## Parametry

- duration: 280–480ms,
- easing premium.

## Uwaga

CTA musi być czytelne i dostępne. Nie usuwać focus outline bez zamiennika.

---

# 11. BEFORE / AFTER EDITORIAL TRANSITION

## Zastosowanie

- suwaki przed/po,
- restauracja,
- korekcja kolorystyczna,
- potencjał fotografii.

## Efekt

Suwak pojawia się jako dowód jakości: najpierw obraz, potem linia porównania, potem opis.

## Składniki

- image reveal,
- handle reveal,
- label stagger,
- opis po 200–300ms.

## Uwaga

Nie robić agresywnego „wow effect”. Jakość ma być pokazana spokojnie, jak w galerii.

---

# 12. SCROLL STORYTELLING SECTION

## Zastosowanie

- homepage,
- proces produkcji,
- Giclée Frame™,
- Restoration Edition,
- własna fotografia.

## Efekt

Sekcja ma rytm: tło → obraz → nagłówek → tekst → separator → CTA. Scroll buduje narrację.

## Składniki

- IntersectionObserver dla prostych wersji,
- rAF + CSS variables dla scroll progress,
- GSAP tylko po audycie dużej sceny.

## Uwaga

Nie używać kilku konkurencyjnych scroll engine w jednej sekcji.

---

# 13. DARK MUSEUM AMBIENT GLOW

## Zastosowanie

- ciemne sekcje,
- hero,
- galeria,
- splash,
- background z obrazem.

## Efekt

Subtelne światło za treścią lub obrazem, tworzące wrażenie ekspozycji muzealnej.

## Składniki

- radial-gradient pseudo-element,
- opacity 0.08–0.18,
- blur ostrożnie,
- brak interakcji.

## Uwaga

Nie robić neonowego glow. To ma być ambient light, nie efekt sci-fi.

---

# 14. RESTORATION DETAIL REVEAL

## Zastosowanie

- cyfrowa restauracja,
- detale pędzla,
- zoom HD,
- sekcje edukacyjne.

## Efekt

Detal obrazu pojawia się powoli, jak odkrywanie tekstury pod światłem.

## Składniki

- mask reveal,
- overlay shadow,
- subtle scale,
- opis jako delayed reveal.

## Uwaga

Nie zwiększać kontrastu i ostrości obrazu agresywnie CSS-em.

---

# 15. COLLECTION AUTHOR STAGGER

## Zastosowanie

- lista artystów,
- menu katalogu,
- kolekcje,
- nawigacja autorów.

## Efekt

Elementy listy wchodzą z małym staggerem, jak elegancka lista katalogowa.

## Składniki

- opacity,
- translateY 8–16px,
- delay przez index,
- hover underline.

## Uwaga

Lista ma być spokojna, nie dynamiczna jak aplikacja SaaS.

---

## JAK WYBIERAĆ EFEKT

Jeśli użytkownik mówi „zrób premium”:

1. wybierz efekt główny,
2. dodaj maksymalnie jeden efekt wspierający,
3. nie łącz pięciu efektów naraz,
4. przygotuj kod referencyjny,
5. przygotuj prompt do Cursor.

Przykład:

Napis „Dzień dobry”:
- efekt główny: Premium Typography Reveal,
- wspierający: Separator Line Expansion,
- opcjonalny: bardzo subtelny Light Sweep.
