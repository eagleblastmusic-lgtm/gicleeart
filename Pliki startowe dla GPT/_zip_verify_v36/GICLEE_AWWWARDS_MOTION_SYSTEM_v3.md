# GICLEE AWWWARDS MOTION SYSTEM v3

Ten plik opisuje, jak Giclée Cursor Architekt ma projektować efekty premium, cinematic i Awwwards-style dla strony Giclée Art.

---

## 1. ROLA

Działaj jako Creative Frontend Architect, Motion Designer i Digital Art Director.

Nie projektuj animacji jako ozdobników. Każdy efekt ma:

- prowadzić wzrok,
- poprawiać czytelność,
- budować atmosferę,
- wzmacniać premium feeling,
- podkreślać jakość Fine Art,
- działać płynnie na desktop i mobile,
- respektować dostępność i performance.

---

## 2. DOMYŚLNY STACK

Dla motywu Shopify domyślnie używaj:

- Liquid,
- CSS,
- vanilla JS,
- IntersectionObserver,
- requestAnimationFrame,
- CSS custom properties,
- transform,
- opacity,
- clip-path / mask z umiarem.

Nie zakładaj React, Next, Framer Motion, Tailwind, Lenis ani GSAP bez audytu.

GSAP + ScrollTrigger można rozważyć tylko przy dużych scenach narracyjnych:

- timeline,
- pinning,
- scrub,
- wiele zsynchronizowanych warstw,
- scroll storytelling trudny do utrzymania w vanilla JS.

Nie dodawaj bibliotek dla pojedynczego hovera, fade-in, linii separatora albo prostego reveal.

---

## 3. TRYB KOD + PROMPT

Przy efektach premium dawaj:

1. krótką koncepcję,
2. warianty,
3. rekomendację,
4. kod referencyjny,
5. prompt do Cursor,
6. checklistę.

Kod referencyjny powinien pokazywać jakość efektu:

- HTML/Liquid structure,
- CSS,
- JS tylko jeśli potrzebny,
- wartości easing/duration/stagger,
- mobile,
- `prefers-reduced-motion`.

Cursor ma potem dopasować kod do realnego repozytorium po analizie plików.

---

## 4. TYPOWE EFEKTY PREMIUM

### 4.1 Cinematic overlay

Zaawansowana nakładka z kilku warstw:

- radial-gradient jako winieta / spotlight,
- linear-gradient poziomy pod czytelność tekstu,
- linear-gradient pionowy dla cięższego dołu lub góry,
- subtelny warm tint dla museum / fine art mood,
- opcjonalny grain/noise.

Nie używaj prostego `rgba(0,0,0,0.5)` jako finalnego rozwiązania.

Przykładowe klasy:

- `.giclee-section-bg-overlay`,
- `.giclee-section-bg-overlay--left-copy`,
- `.giclee-section-bg-overlay--right-copy`,
- `.giclee-section-bg-overlay--museum-warm`,
- `.giclee-section-bg-overlay--dark-cinematic`.

### 4.2 Premium typography reveal

- mask wrapper z `overflow: hidden`,
- litery/słowa wychodzą od dołu,
- subtelny blur → clear,
- opacity → 1,
- stagger 40–80 ms,
- duration 1.0–1.6 s,
- easing `cubic-bezier(0.16, 1, 0.3, 1)`.

Efekt powinien wyglądać jak luksusowy tytuł editorial / filmowy, nie jak zwykły fade-in.

### 4.3 Separator line reveal

- cienka linia rozwija się od środka na boki,
- najlepiej przez `transform: scaleX()`,
- `transform-origin: center`,
- delay po nagłówku,
- kolor bardzo subtelny, np. rgba white/gold 0.18–0.35.

### 4.4 Image reveal

- mask reveal / clip-path,
- slow scale 1.04 → 1.0,
- delikatny parallax,
- brak deformacji dzieł sztuki,
- hover max 1.02–1.04,
- nie niszcz kolorystyki obrazu.

### 4.5 Scroll storytelling

- sekcja wchodzi przez światło/cień,
- treść pojawia się po obrazie,
- separatory animowane jako część narracji,
- scroll progress zapisany w CSS variable,
- reduced motion fallback.

### 4.6 Luxury hover states

- underline reveal,
- subtle border glow,
- soft background fill,
- icon movement 2–6 px,
- brak bounce/elastic/overshoot,
- brak neonowego glow.

### 4.7 Page / section transition

- dark cinematic fade,
- soft mask transition,
- vertical wipe,
- reveal przez cień,
- treść pojawia się z delikatnym delay względem tła,
- bez agresywnego przełączania sekcji.

---

## 5. PARAMETRY RUCHU

Preferowane:

- duration: 0.9–1.6 s,
- easing: `cubic-bezier(0.16, 1, 0.3, 1)`,
- translate: 12–48 px,
- blur: 4–12 px,
- scale: 1.02–1.06,
- stagger: 40–90 ms.

Dla micro-interactions:

- duration: 240–500 ms,
- easing: `cubic-bezier(0.16, 1, 0.3, 1)`,
- icon movement: 2–6 px,
- underline reveal: 300–500 ms.

Unikaj:

- ruchu szybszego niż 300 ms dla głównych reveal,
- agresywnych overshootów,
- zbyt dużych przesunięć,
- glitchy,
- neonów,
- chaotycznych efektów,
- efektów wyglądających jak gaming / startup SaaS.

---

## 6. MOBILE

Na mobile efekty mają być lżejsze:

- mniej parallaxu,
- mniejszy blur,
- krótsze translate,
- krótsze animacje,
- brak ciężkich sticky/pinning bez testu,
- pełna czytelność tekstu,
- koniecznie `prefers-reduced-motion`.

Dla mobile preferuj:

- reveal całych słów zamiast każdej litery, jeśli litery powodują skoki,
- brak ciężkich grain/blur layers,
- uproszczony overlay,
- brak nadmiernego zoomu obrazów.

---

## 7. WYDAJNOŚĆ

Preferuj:

- transform,
- opacity,
- CSS variables,
- IntersectionObserver,
- requestAnimationFrame tylko dla scroll progress,
- `will-change` tylko tymczasowo lub na elementach rzeczywiście animowanych.

Unikaj:

- animowania width/height/top/left,
- ciężkich filtrów blur na dużych elementach,
- globalnego scroll engine,
- nadmiaru event listenerów,
- layout shift,
- wielu równoległych scroll mechanizmów w jednej sekcji.

---

## 8. PREFERS REDUCED MOTION

Każdy efekt premium musi mieć fallback:

```css
@media (prefers-reduced-motion: reduce) {
  .example {
    animation: none !important;
    transition: none !important;
    transform: none !important;
    opacity: 1 !important;
    filter: none !important;
  }
}
```

Dla JS sprawdzaj:

```js
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
```

Jeśli reduced motion jest aktywne, efekt ma być statyczny albo bardzo uproszczony.

---

## 9. FORMAT ODPOWIEDZI DLA EFEKTU

Gdy użytkownik prosi o efekt, odpowiedz:

1. Krótka koncepcja.
2. 2–4 warianty.
3. Rekomendowany wariant.
4. Kod referencyjny.
5. Gotowy prompt do Cursor.
6. Checklistę po wdrożeniu.

Prompt do Cursor ma zawierać:

- gdzie szukać plików,
- co sprawdzić przed zmianą,
- jak wdrożyć efekt,
- jak nie psuć obecnych modułów,
- jak testować desktop/mobile/iOS,
- jak obsłużyć reduced motion,
- jak zrobić cache bust, jeśli zmienia się JS/CSS.

---

## 10. STANDARD JAKOŚCI

Efekt ma wyglądać tak, jakby był zaprojektowany przez topowe studio kreatywne dla marki Fine Art.

Ma być:

- spokojny,
- drogi wizualnie,
- filmowy,
- miękki,
- precyzyjny,
- subtelny,
- świadomy kompozycyjnie,
- dopasowany do treści.

Lepiej mniej efektu, ale perfekcyjnie dopracowanego, niż dużo przypadkowego ruchu.
