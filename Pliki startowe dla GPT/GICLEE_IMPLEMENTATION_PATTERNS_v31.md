# GICLEE IMPLEMENTATION PATTERNS v3.1

Techniczne wzorce wdrożenia efektów premium w projekcie Giclée Art.

---

## 1. DOMYŚLNA ŚCIEŻKA DLA MOTYWU SHOPIFY

Dla frontu sklepu domyślnie używaj:

- Shopify Liquid,
- CSS w `assets/`,
- vanilla JS w `assets/`,
- istniejących sekcji/snippetów,
- istniejących modułów `giclee-*`,
- import map Horizon, jeśli potrzebne,
- selektywnego ładowania assetów z Liquid.

Nie zakładaj:

- React,
- Next.js,
- Tailwind,
- TypeScript,
- Framer Motion,
- Lenis,
- GSAP,
- Sass,
- CSS Modules.

---

## 2. GDZIE DODAWAĆ EFEKTY

### Jeśli efekt dotyczy jednej sekcji

Preferuj:

- CSS w istniejącym pliku sekcji/feature, jeśli istnieje,
- JS w istniejącym module `giclee-*`, jeśli dotyczy tej samej funkcji,
- nowe pliki tylko gdy efekt jest większy albo ma być wielokrotnego użytku.

### Jeśli efekt jest globalnym wzorcem

Rozważ:

- `assets/giclee-premium-effects.css`,
- `assets/giclee-premium-effects.js`,
- dokumentację w `docs/motyw/`.

Ale nie twórz globalnego systemu, jeśli efekt występuje tylko raz.

---

## 3. JAK ŁADOWAĆ ASSETY

Ładuj assety selektywnie.

Dobre:

```liquid
{{ 'giclee-premium-effects.css' | asset_url | stylesheet_tag }}

<script type="module" src="{{ 'giclee-premium-effects.js' | asset_url }}" defer></script>
```

Jeszcze lepiej: ładować tylko w konkretnej sekcji/szablonie, jeśli efekt nie jest globalny.

Złe:

- dodanie wszystkiego globalnie do `theme.liquid` bez potrzeby,
- ładowanie dużych bibliotek na każdej stronie dla jednej animacji.

---

## 4. INTERSECTIONOBSERVER PATTERN

Dla prostych reveal używaj IntersectionObserver.

Wzorzec:

```js
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

if (!prefersReducedMotion) {
  const elements = document.querySelectorAll('[data-giclee-reveal]');

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-visible');
      observer.unobserve(entry.target);
    });
  }, {
    threshold: 0.18,
    rootMargin: '0px 0px -8% 0px',
  });

  elements.forEach((element) => observer.observe(element));
} else {
  document.querySelectorAll('[data-giclee-reveal]').forEach((element) => {
    element.classList.add('is-visible');
  });
}
```

Używaj tego dla:

- tekstów,
- obrazów,
- separatorów,
- kart,
- prostych wejść sekcji.

---

## 5. REQUESTANIMATIONFRAME SCROLL PATTERN

Dla scroll progress używaj rAF i CSS variables.

Używaj tylko, gdy efekt naprawdę zależy od progresu scrolla.

Wzorzec logiczny:

```js
let ticking = false;

function update() {
  ticking = false;

  // policz progress sekcji
  // ustaw CSS variable, np. --giclee-progress
}

function requestTick() {
  if (ticking) return;
  ticking = true;
  requestAnimationFrame(update);
}

window.addEventListener('scroll', requestTick, { passive: true });
window.addEventListener('resize', requestTick);
requestTick();
```

Używaj dla:

- parallax,
- scroll storytelling,
- progress separatorów,
- płynnego fade sekcji.

Nie używaj dla zwykłego fade-in.

---

## 6. CSS REVEAL PATTERN

Preferowany CSS:

```css
.giclee-reveal {
  opacity: 0;
  transform: translateY(28px);
  filter: blur(8px);
  transition:
    opacity 1.1s cubic-bezier(0.16, 1, 0.3, 1),
    transform 1.1s cubic-bezier(0.16, 1, 0.3, 1),
    filter 1.1s cubic-bezier(0.16, 1, 0.3, 1);
  will-change: opacity, transform, filter;
}

.giclee-reveal.is-visible {
  opacity: 1;
  transform: translateY(0);
  filter: blur(0);
}

@media (prefers-reduced-motion: reduce) {
  .giclee-reveal {
    opacity: 1;
    transform: none;
    filter: none;
    transition: none;
    will-change: auto;
  }
}
```

Uwaga:

- nie zostawiaj `will-change` na setkach elementów,
- ogranicz blur na mobile,
- testuj iOS Safari.

---

## 7. SEPARATOR PATTERN

Dobre:

```css
.giclee-divider::before {
  content: "";
  display: block;
  height: 1px;
  background: rgba(198, 169, 107, 0.28);
  transform: scaleX(0);
  transform-origin: center;
  transition: transform 1.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.giclee-divider.is-visible::before {
  transform: scaleX(1);
}
```

Złe:

```css
width: 0;
```

Nie animuj width, jeśli można użyć transform.

---

## 8. OVERLAY PATTERN

Dobre:

```css
.giclee-section-bg-overlay {
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  background:
    radial-gradient(...),
    linear-gradient(...),
    linear-gradient(...);
}
```

Wymagania:

- rodzic ma `position: relative`,
- obraz jest pod overlayem,
- content jest nad overlayem,
- overlay ma `pointer-events: none`,
- mobile może mieć osobny gradient.

---

## 9. KIEDY NIE DODAWAĆ GSAP

Nie dodawaj GSAP dla:

- hovera,
- fade-in,
- prostego reveal,
- separatora,
- overlayu,
- jednej animacji tekstu,
- jednej karty produktu.

## 10. KIEDY ROZWAŻYĆ GSAP

Rozważ GSAP + ScrollTrigger po audycie, gdy:

- jest pinning,
- jest scrub,
- wiele warstw musi być zsynchronizowanych,
- jest długa scena storytellingowa,
- vanilla JS byłby zbyt złożony i trudny do utrzymania.

Warunki:

- ładowanie selektywne,
- fallback reduced motion,
- test iOS Safari,
- dokumentacja w `docs/motyw/`,
- uzasadnienie kosztu.

---

## 11. CACHE BUST

Po zmianie JS/CSS sprawdź, czy trzeba podbić parametr wersji w Liquid:

- `?v=...`,
- `&giclee_v=...`,
- import map, jeśli dotyczy.

Cursor ma zgłosić, czy cache bust był potrzebny.

---

## 12. DOKUMENTACJA

Po ważnej zmianie dopisz lub zaktualizuj dokumentację modułową:

- `docs/motyw/<nazwa-modulu>.md`

Nie aktualizuj archiwalnych plików wiedzy, jeśli są oznaczone jako archiwum.

---

## 13. TESTY PO WDROŻENIU

Cursor ma sprawdzić:

- desktop,
- mobile ≤749px,
- tablet,
- iOS Safari,
- hover/focus,
- reduced motion,
- brak layout shift,
- brak błędów console,
- brak konfliktu z istniejącymi `giclee-*`,
- koszyk/drawer, jeśli zmiana dotyczy elementów globalnych,
- LCP/INP, jeśli efekt dotyczy hero lub dużych obrazów.

---

## 14. ZASADA MINIMALNEGO DIFFU

Najpierw rozszerz istniejące rozwiązanie.

Dopiero potem twórz nowe pliki.

Nie duplikuj modułów scroll/reveal, jeśli istnieje podobny `giclee-*`.

Nie zmieniaj architektury tylko dlatego, że efekt wygląda ciekawie.
