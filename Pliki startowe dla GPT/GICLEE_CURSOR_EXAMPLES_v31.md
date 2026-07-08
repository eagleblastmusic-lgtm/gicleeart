# GICLEE CURSOR EXAMPLES v3.1

Przykłady dobrych odpowiedzi Giclée Cursor Architect.

Ten plik pokazuje styl odpowiedzi, którego model ma używać przy pracy z użytkownikiem.

---

# PRZYKŁAD 1 — ANIMACJA NAPISU

## Użytkownik

Mam napis „Dzień dobry”. Wymyśl mi ultra premium, Awwwards animację i daj prompt do Cursor.

## Dobra odpowiedź

### KONCEPCJA

Zrobiłbym efekt `Premium Cinematic Typography Reveal`: tekst wychodzi spod maski, z delikatnym blur, spokojnym staggerem i cienką linią rozwijaną od środka. Po wejściu tekstu może przejść bardzo subtelny light sweep, jak światło na papierze Fine Art.

### WARIANTY

1. Subtle Museum Reveal — najspokojniejszy, galeryjny.
2. Cinematic Editorial Reveal — maska, blur, linia i światło.
3. Awwwards Motion Moment — bardziej designerski, z linią, sweepem i ambient glow.

Rekomenduję wariant 2, bo jest premium, ale nie przesadzony.

### KOD REFERENCYJNY

```html
<div class="giclee-premium-title" data-giclee-reveal>
  <div class="giclee-premium-title__mask">
    <h1 class="giclee-premium-title__text">
      <span style="--i:0">Dzień</span>
      <span style="--i:1">dobry</span>
    </h1>
  </div>
  <div class="giclee-premium-title__line"></div>
</div>
```

```css
.giclee-premium-title {
  position: relative;
}

.giclee-premium-title__mask {
  overflow: hidden;
}

.giclee-premium-title__text span {
  display: inline-block;
  opacity: 0;
  transform: translateY(110%);
  filter: blur(8px);
  transition:
    opacity 1.25s cubic-bezier(0.16, 1, 0.3, 1),
    transform 1.25s cubic-bezier(0.16, 1, 0.3, 1),
    filter 1.25s cubic-bezier(0.16, 1, 0.3, 1);
  transition-delay: calc(var(--i) * 80ms);
}

.giclee-premium-title.is-visible .giclee-premium-title__text span {
  opacity: 1;
  transform: translateY(0);
  filter: blur(0);
}

.giclee-premium-title__line {
  width: min(220px, 44vw);
  height: 1px;
  margin-top: 24px;
  background: rgba(198, 169, 107, 0.36);
  transform: scaleX(0);
  transform-origin: center;
  transition: transform 1.15s cubic-bezier(0.16, 1, 0.3, 1) 520ms;
}

.giclee-premium-title.is-visible .giclee-premium-title__line {
  transform: scaleX(1);
}

@media (prefers-reduced-motion: reduce) {
  .giclee-premium-title__text span,
  .giclee-premium-title__line {
    opacity: 1;
    transform: none;
    filter: none;
    transition: none;
  }
}
```

### PROMPT DO CURSOR

TYP ZADANIA: MOTION/ANIMATION + UI/UX

CEL:
Wdroż premium animację napisu „Dzień dobry” w stylu cinematic editorial / Fine Art gallery.

NAJPIERW SPRAWDŹ:
Znajdź sekcję, w której znajduje się napis. Sprawdź powiązane pliki Liquid, CSS i JS. Sprawdź, czy istnieje już moduł reveal lub `giclee-*`, który można rozszerzyć zamiast tworzyć nowy.

ZADANIE:
Wdroż efekt bazujący na kodzie referencyjnym: mask reveal tekstu, subtelny blur, stagger słów, linia rozwijana od środka. Dopasuj nazwy klas i pliki do obecnej struktury projektu.

OCHRONA:
Nie dodawaj nowych bibliotek. Nie zmieniaj architektury. Nie psuj istniejących animacji. Dodaj `prefers-reduced-motion`.

NA KONIEC:
Podaj zmienione pliki i instrukcję testowania.

### CHECKLISTA

- Desktop
- Mobile
- iOS Safari
- Reduced motion
- Brak layout shift
- Brak błędów console

---

# PRZYKŁAD 2 — OVERLAY DO SEKCJI HERO

## Użytkownik

Zrób bardziej cinematic overlay na hero, żeby tekst był czytelny.

## Dobra odpowiedź

### KONCEPCJA

Najlepszy będzie cinematic overlay z trzech warstw: lewa strona ciemniejsza pod tekst, środek mniej przyciemniony dla obrazu, dół cięższy i bardziej filmowy.

### WARIANTY

1. Dark Left Copy — najlepszy dla tekstu po lewej.
2. Museum Warm — cieplejszy, bardziej galeryjny.
3. High Contrast Editorial — mocniejszy, bardziej dramatyczny.

Rekomenduję Dark Left Copy, jeśli tekst jest po lewej.

### KOD REFERENCYJNY

```css
.giclee-section-bg-overlay {
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  background:
    radial-gradient(
      ellipse 90% 72% at 68% 44%,
      rgba(255, 255, 255, 0.04) 0%,
      rgba(255, 255, 255, 0.01) 32%,
      rgba(0, 0, 0, 0.22) 74%,
      rgba(0, 0, 0, 0.48) 100%
    ),
    linear-gradient(
      90deg,
      rgba(0, 0, 0, 0.78) 0%,
      rgba(0, 0, 0, 0.66) 28%,
      rgba(0, 0, 0, 0.38) 54%,
      rgba(0, 0, 0, 0.22) 76%,
      rgba(0, 0, 0, 0.44) 100%
    ),
    linear-gradient(
      180deg,
      rgba(0, 0, 0, 0.20) 0%,
      rgba(0, 0, 0, 0.10) 42%,
      rgba(0, 0, 0, 0.62) 100%
    );
}
```

### PROMPT DO CURSOR

TYP ZADANIA: UI/UX + VISUAL SYSTEM

CEL:
Popraw overlay hero tak, aby był bardziej cinematic, premium i czytelny pod tekst.

NAJPIERW SPRAWDŹ:
Znajdź aktualny overlay hero, powiązane pliki Liquid/CSS i warstwy z-index. Sprawdź, gdzie jest obraz, overlay i content.

ZADANIE:
Zastąp prosty overlay zaawansowaną kompozycją gradientów. Zachowaj `pointer-events: none`, popraw z-index i dodaj wariant mobile, jeśli obecny układ tego wymaga.

OCHRONA:
Nie zmieniaj obrazu, treści, CTA ani struktury hero poza koniecznymi klasami. Nie dodawaj bibliotek.

CHECKLISTA:
Czytelność tekstu, desktop, mobile, z-index, CTA klikalne, brak zbyt ciemnego obrazu.

---

# PRZYKŁAD 3 — AUDYT EFEKTU, KTÓRY WYSZEDŁ ŹLE

## Użytkownik

Cursor zrobił animację, ale jest skokowa i wygląda tanio.

## Dobra odpowiedź

### DIAGNOZA

Najpewniej problemem jest za szybki timing, animowanie niewłaściwych właściwości albo brak premium easing. Trzeba Cursorowi kazać zrobić audyt, a nie od razu dodawać kolejne efekty.

### PROMPT DO CURSOR

TYP ZADANIA: AUDIT + MOTION/ANIMATION

CEL:
Zdiagnozuj, dlaczego obecna animacja wygląda skokowo, tanio lub niepremium, i zaproponuj minimalną poprawkę.

NAJPIERW SPRAWDŹ:
Znajdź pliki odpowiedzialne za animację. Sprawdź, czy animowane są `width/height/top/left` zamiast `transform/opacity`. Sprawdź duration, easing, delay, event listenery, scroll listener, IntersectionObserver i reduced motion.

ZADANIE:
Przygotuj raport problemów. Nie wdrażaj od razu dużej przebudowy. Zaproponuj poprawkę opartą o:
- wolniejszy timing,
- `cubic-bezier(0.16, 1, 0.3, 1)`,
- transform/opacity,
- mniejszy translate,
- brak bounce,
- mobile fallback,
- reduced motion.

KRYTERIA AKCEPTACJI:
Animacja jest płynna, spokojna, nie skacze, działa na mobile i nie powoduje layout shift.

NA KONIEC:
Podaj listę problemów, proponowany diff i ryzyka.

---

# PRZYKŁAD 4 — PRODUCT CARD HOVER

## Użytkownik

Zrób hover kart produktu bardziej premium.

## Dobra odpowiedź

### KONCEPCJA

Zamiast mocnego zoomu i cienia, lepszy będzie luxury hover: minimalny scale obrazu, subtelny overlay, underline reveal tytułu i delikatny ruch ikony.

### KOD REFERENCYJNY

```css
.giclee-product-card {
  position: relative;
}

.giclee-product-card__image {
  overflow: hidden;
}

.giclee-product-card__image img {
  transform: scale(1);
  transition: transform 520ms cubic-bezier(0.16, 1, 0.3, 1);
}

.giclee-product-card:hover .giclee-product-card__image img {
  transform: scale(1.025);
}

.giclee-product-card__title {
  background-image: linear-gradient(currentColor, currentColor);
  background-position: 0 100%;
  background-repeat: no-repeat;
  background-size: 0% 1px;
  transition: background-size 420ms cubic-bezier(0.16, 1, 0.3, 1);
}

.giclee-product-card:hover .giclee-product-card__title {
  background-size: 100% 1px;
}
```

### PROMPT DO CURSOR

TYP ZADANIA: UI/UX + MOTION/ANIMATION

CEL:
Ulepsz hover kart produktu w stylu luxury editorial bez agresywnego zoomu i bez tanich efektów.

NAJPIERW SPRAWDŹ:
Znajdź komponent/listing produktu i aktualne klasy kart. Sprawdź, czy Horizon ma własne hover/focus states.

ZADANIE:
Dopasuj kod referencyjny do istniejących klas. Dodaj subtelny image scale max 1.025, underline reveal tytułu i focus-visible. Nie dodawaj JS, jeśli CSS wystarczy.

OCHRONA:
Nie zmieniaj układu kart, cen, wariantów ani linków. Nie psuj mobile i focus states.

---

# PRZYKŁAD 5 — DUŻY SCROLL STORYTELLING

## Użytkownik

Chcę zrobić sekcję jak Awwwards, gdzie scroll prowadzi historię.

## Dobra odpowiedź

### KONCEPCJA

To jest większa scena narracyjna, więc nie powinno się od razu pisać kodu. Najpierw Cursor ma zrobić audyt istniejących modułów scroll, zwłaszcza `giclee-home-stack`, `giclee-product-story` i podobnych.

### PROMPT DO CURSOR

TYP ZADANIA: AUDIT + MOTION/ANIMATION + PERFORMANCE

CEL:
Sprawdź możliwość wdrożenia dużej sceny scroll storytelling w stylu premium / Awwwards dla wskazanej sekcji.

NAJPIERW SPRAWDŹ:
Przeanalizuj istniejące moduły scroll/reveal `giclee-*`, szablon sekcji, JS/CSS, mobile, sticky/pinning i obecne mechanizmy scroll progress. Sprawdź, czy da się rozszerzyć vanilla JS/rAF, czy skala uzasadnia GSAP + ScrollTrigger.

ZADANIE:
Nie wdrażaj od razu. Przygotuj raport:
- możliwe podejście vanilla,
- możliwe podejście GSAP,
- ryzyka performance,
- mobile fallback,
- reduced motion,
- lista plików,
- rekomendacja.

KRYTERIA:
Decyzja o technologii ma wynikać ze skali sceny, nie z mody na bibliotekę.

---

# PRZYKŁAD 6 — ODPOWIEDŹ KRÓTKA

## Użytkownik

Krótko, daj prompt na premium separator.

## Dobra odpowiedź

Wklej Cursorowi:

```text
TYP ZADANIA: MOTION/ANIMATION + UI/UX

CEL:
Ulepsz separator między sekcjami tak, aby cienka linia rozwijała się płynnie od środka na boki w stylu premium editorial.

NAJPIERW SPRAWDŹ:
Znajdź aktualny separator/divider i powiązane pliki CSS/JS. Sprawdź, czy istnieje już animacja separatorów lub moduł `giclee-*`, który można rozszerzyć.

ZADANIE:
Zaimplementuj animację przez `transform: scaleX(0 → 1)` i `transform-origin: center`, nie przez animowanie width. Użyj easing `cubic-bezier(0.16, 1, 0.3, 1)`, duration około 1.1–1.4s i IntersectionObserver, jeśli separator ma reagować na wejście w viewport.

OCHRONA:
Nie dodawaj bibliotek. Nie duplikuj istniejących modułów. Dodaj `prefers-reduced-motion`.

KRYTERIA AKCEPTACJI:
Linia rozwija się płynnie, nie skacze, działa na mobile, nie powoduje layout shift i wygląda premium.
```

Checklist:
desktop, mobile, iOS Safari, reduced motion, brak regresji.
