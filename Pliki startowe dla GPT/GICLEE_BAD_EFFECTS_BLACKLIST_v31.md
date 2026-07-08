# GICLEE BAD EFFECTS BLACKLIST v3.1

Lista efektów i decyzji, których Giclée Cursor Architect ma unikać.

---

## 1. ZŁE EFEKTY WIZUALNE

Nie używaj:

- neon glow,
- glitch reveal,
- cyberpunk light,
- gaming particles,
- przesadny 3D tilt,
- agresywny parallax,
- bounce easing,
- elastic overshoot,
- flash / strobe,
- zbyt szybkie fade-in,
- obracające się litery bez powodu,
- scale zbyt mocny na obrazach,
- ciężki blur na całej sekcji,
- jaskrawe gradienty,
- przypadkowe noise/film grain,
- hover z dużym zoomem,
- animacje przypominające landing page SaaS.

---

## 2. ZŁE DECYZJE TECHNICZNE

Nie rób:

- GSAP dla jednej linii,
- Lenis/global smooth scroll bez audytu całej strony,
- React/Framer Motion w motywie Liquid bez architektonicznej decyzji,
- Tailwind dla pojedynczej sekcji,
- animowania `width`, `height`, `top`, `left`, gdy można użyć `transform`,
- wielu scroll listenerów bez rAF,
- globalnego JS dla efektu używanego raz,
- duplikowania istniejących modułów `giclee-*`,
- ładowania assetów na całym sklepie bez potrzeby,
- ignorowania `prefers-reduced-motion`.

---

## 3. ZŁE DECYZJE UX

Nie rób efektu, który:

- opóźnia dostęp do treści,
- zasłania CTA,
- zmniejsza czytelność,
- utrudnia kliknięcia,
- blokuje koszyk,
- powoduje layout shift,
- działa dobrze tylko na desktop,
- ignoruje mobile,
- wymaga precyzyjnego hovera na urządzeniach dotykowych,
- odciąga uwagę od produktu.

---

## 4. ZŁY STYL DLA GICLÉE

Unikaj wyglądu:

- marketplace,
- tani sklep,
- startup SaaS,
- portfolio junior developera,
- aplikacja gamingowa,
- neon/cyberpunk,
- agresywna promocja,
- „kup teraz!!!”,
- stockowy landing page,
- template bez charakteru.

---

## 5. CZERWONE FLAGI W ODPOWIEDZI MODELU

Jeśli odpowiedź zawiera coś takiego, popraw ją:

- „dodajmy GSAP” bez uzasadnienia,
- „zainstaluj Tailwind” dla jednego efektu,
- „użyj React component” w motywie Shopify,
- „dodaj opacity 0.5 na całe tło” jako premium overlay,
- „zrób szybki fade-in 0.3s” dla hero,
- „dodaj glitch, będzie nowocześnie”,
- „zrób mocny parallax wszędzie”,
- brak mobile,
- brak reduced motion,
- brak checklisty,
- brak ochrony projektu,
- brak analizy istniejących plików.

---

## 6. ZASADA NAPRAWY

Jeśli efekt wygląda zbyt tanio, popraw w tej kolejności:

1. Zwolnij tempo.
2. Zmień easing na premium.
3. Zmniejsz odległość ruchu.
4. Usuń bounce/overshoot.
5. Dodaj maskę zamiast zwykłego fade.
6. Dodaj subtelny separator lub światło, jeśli ma sens.
7. Uprość efekt.
8. Sprawdź mobile.
9. Dodaj reduced motion.
10. Usuń zbędne biblioteki.

---

## 7. PRZYKŁADY ZŁYCH VS DOBRYCH ROZWIĄZAŃ

### Złe

```css
.hero-title {
  animation: bounceIn 0.5s;
  text-shadow: 0 0 30px cyan;
}
```

### Dobre

```css
.hero-title__line {
  transform: translateY(110%);
  opacity: 0;
  filter: blur(8px);
  transition:
    transform 1.25s cubic-bezier(0.16, 1, 0.3, 1),
    opacity 1.25s cubic-bezier(0.16, 1, 0.3, 1),
    filter 1.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.is-visible .hero-title__line {
  transform: translateY(0);
  opacity: 1;
  filter: blur(0);
}
```

---

## 8. FINALNA ZASADA

Jeśli efekt można opisać jako:

- głośny,
- krzykliwy,
- szybki,
- glitchowy,
- neonowy,
- losowy,
- zbyt technologiczny,
- przeszkadzający,

to prawdopodobnie nie pasuje do Giclée Art.

Lepszy efekt dla Giclée jest:

- cichy,
- precyzyjny,
- spokojny,
- filmowy,
- luksusowy,
- galeryjny,
- subtelny,
- świadomy.
