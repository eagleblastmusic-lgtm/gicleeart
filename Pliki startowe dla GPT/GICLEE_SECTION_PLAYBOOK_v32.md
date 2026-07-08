# GICLEE SECTION PLAYBOOK v3.2

Playbook do dobierania efektów, animacji i poziomu premium dla konkretnych miejsc strony Giclée Art.

---

## GŁÓWNA ZASADA

Nie dawaj tego samego efektu do każdej sekcji.

Hero, PDP, koszyk, kolekcja autora i footer mają różne zadania, więc potrzebują różnego poziomu motion.

Dla każdej sekcji oceń:

- cel biznesowy,
- rolę narracyjną,
- ryzyko UX,
- ryzyko performance,
- mobile,
- czy efekt ma być spokojny, cinematic czy signature moment.

---

# 1. HERO HOMEPAGE

## Rola

Pierwsze wrażenie. Ma pokazać, że Giclée Art to premium Fine Art / galeria / museum-quality.

## Poziom motion

Wysoki, ale kontrolowany. Może być signature moment.

## Najlepsze efekty

- Museum Opening Moment,
- cinematic overlay,
- premium typography reveal,
- subtle image/video reveal,
- separator line expansion,
- ambient museum glow,
- slow parallax layers.

## Unikać

- zbyt szybkiego slidera,
- agresywnego CTA,
- glitch/neon,
- ciężkiego WebGL bez potrzeby,
- przesłonięcia produktu.

## Ryzyka

- LCP,
- mobile performance,
- czytelność tekstu,
- zbyt ciemny overlay.

---

# 2. SPLASH SCREEN

## Rola

Powitanie jak wejście do galerii.

## Poziom motion

Wysoki, ale krótki i elegancki.

## Najlepsze efekty

- black gallery opening,
- line reveal,
- logo mask reveal,
- subtle light sweep,
- fade into homepage.

## Unikać

- długiego blokowania strony,
- zbyt teatralnych przejść,
- zbyt wielu elementów,
- opóźniania użytkownika.

## Ryzyka

- UX,
- perceived performance,
- powtarzanie przy każdej wizycie.

---

# 3. HOMEPAGE EDITORIAL SECTIONS

## Rola

Budowanie wartości marki, edukacja, pokaz jakości.

## Poziom motion

Średni do wysokiego.

## Najlepsze efekty

- editorial scroll reveal,
- image reveal,
- separator expansion,
- subtle parallax,
- before/after editorial transition,
- cinematic overlays.

## Unikać

- reveal wszystkiego naraz,
- scroll chaos,
- zbyt dużego ruchu na każdym bloku,
- duplikowania wielu scroll engine.

## Ryzyka

- mobile,
- czytelność długich tekstów,
- skokowe animacje.

---

# 4. RESTORATION EDITION / BEFORE-AFTER

## Rola

Dowód jakości i kompetencji. Jedna z najważniejszych sekcji „wow”.

## Poziom motion

Wysoki. Może być signature moment.

## Najlepsze efekty

- Restoration Before/After Story,
- museum image reveal,
- conservation light sweep,
- detail reveal,
- label reveal jak podpis muzealny,
- spokojny slider przed/po.

## Unikać

- agresywnej transformacji,
- przesadnego kontrastu,
- efektów wyglądających jak „AI magic”,
- zbyt szybkiego porównania.

## Ryzyka

- klient musi widzieć różnicę,
- nie można obniżyć zaufania przez efekciarstwo,
- obrazy muszą zachować kolorystykę.

---

# 5. GICLÉE FRAME™

## Rola

Pokaz rzemiosła, materiałów, drewna, passe-partout, papieru i jakości oprawy.

## Poziom motion

Średni do wysokiego.

## Najlepsze efekty

- Giclée Frame™ Material Reveal,
- layered material reveal,
- subtle parallax frame,
- edge light on wood,
- material caption reveal,
- warm museum overlay.

## Unikać

- industrial/tech look,
- przesadnego 3D,
- taniego product-spin,
- zbyt szybkich animacji.

## Ryzyka

- zdjęcia materiałów muszą wyglądać naturalnie,
- mobile musi pozostać czytelny.

---

# 6. PDP REPRODUKCJI

## Rola

Sprzedaż konkretnego dzieła. Ma być galeria + konfigurator e-commerce.

## Poziom motion

Średni. Premium, ale nie przeszkadzać w zakupie.

## Najlepsze efekty

- product image reveal,
- scroll reveal dla opisu i szczegółów,
- subtle sticky details entrance,
- gallery hover,
- zoom HD moment,
- trust section reveal.

## Unikać

- ruchu przy wyborze wariantów,
- efektów utrudniających konfigurację,
- przesadnego parallaxu na obrazie,
- spowalniania PDP.

## Ryzyka

- warianty,
- koszyk,
- zoom manifest,
- mobile 749px,
- sticky panel.

---

# 7. PDP WŁASNA FOTOGRAFIA

## Rola

Konfigurator i upload zdjęcia klienta. Najważniejsza jest użyteczność i zaufanie.

## Poziom motion

Niski do średniego.

## Najlepsze efekty

- subtle onboarding reveal,
- calm panel transitions,
- quality PPI education reveal,
- microinteractions,
- gentle frame preview motion.

## Unikać

- efektów zakłócających kadrowanie,
- parallaxu w mockupie,
- ciężkich animacji podczas uploadu,
- zmian layoutu po interakcji.

## Ryzyka

- upload,
- iOS Safari,
- fetch,
- scroll-lock,
- panel jakości,
- cena na żywo.

---

# 8. KOLEKCJA AUTORA

## Rola

Galeria autora, biografia, kolekcja dzieł.

## Poziom motion

Średni do wysokiego.

## Najlepsze efekty

- author biography scroll stack,
- collection author stagger,
- gallery coverflow refinement,
- background crossfade,
- museum captions,
- soft parallax.

## Unikać

- zbyt agresywnego carousel motion,
- gubienia kontekstu autora,
- chaosu w nawigacji między autorami.

## Ryzyka

- performance karuzeli,
- mobile,
- autoplay,
- czytelność biografii.

---

# 9. MENU KATALOGU

## Rola

Eksploracja artystów i kolekcji.

## Poziom motion

Średni.

## Najlepsze efekty

- stagger list reveal,
- hover preview,
- subtle background dim,
- image fade/crossfade,
- underline reveal.

## Unikać

- zbyt długich animacji,
- utrudniania nawigacji,
- efektów wymagających hover na mobile.

## Ryzyka

- accessibility,
- keyboard navigation,
- focus states,
- mobile menu.

---

# 10. KOSZYK / CHECKOUT ENTRY

## Rola

Finalizacja zakupu. Spokój, zaufanie, brak tarcia.

## Poziom motion

Niski. Premium microinteractions, nie Awwwards show.

## Najlepsze efekty

- Collector Checkout Calmness,
- subtle drawer entrance,
- calm invoice field reveal,
- premium CTA hover,
- trust microcopy reveal.

## Unikać

- efektów wow,
- opóźnień,
- skomplikowanych przejść,
- animacji pól formularza,
- czegokolwiek, co może zepsuć checkout.

## Ryzyka

- konwersja,
- atrybuty faktury,
- drawer,
- mobile,
- BLIK,
- Shopify checkout.

---

# 11. FOOTER

## Rola

Domknięcie marki, linki, newsletter, zaufanie.

## Poziom motion

Niski.

## Najlepsze efekty

- subtle line reveal,
- link underline reveal,
- soft newsletter focus state,
- calm section fade.

## Unikać

- ciężkich animacji,
- parallaxu,
- signature moments.

## Ryzyka

- accessibility,
- focus,
- linki,
- newsletter.

---

# 12. FINE ART ORACLE / LOSUJ OBRAZ

## Rola

Eksperymentalna, zapamiętywalna scena. Tu można pozwolić sobie na najwięcej.

## Poziom motion

Wysoki. Najlepsze miejsce na signature moment.

## Najlepsze efekty

- Fine Art Oracle Signature Scene,
- dark gallery atmosphere,
- floating artwork depth,
- cinematic reveal finalnego dzieła,
- subtle particles/grain, jeśli lekkie,
- WebGL only if already supported and with fallback.

## Unikać

- gaming look,
- neon particles,
- ciężkiego WebGL bez fallbacku,
- zbyt chaotycznej animacji.

## Ryzyka

- performance,
- fallback CSS,
- mobile,
- accessibility.

---

# 13. FAQ / STRONY INFORMACYJNE

## Rola

Zaufanie, edukacja, odpowiedzi.

## Poziom motion

Niski do średniego.

## Najlepsze efekty

- calm accordion transitions,
- subtle section reveal,
- line reveal,
- focus-visible polish.

## Unikać

- animacji przeszkadzających w czytaniu,
- zbyt długich przejść accordion,
- efektów wow.

## Ryzyka

- accessibility,
- keyboard navigation,
- semantic HTML.

---

# 14. BLOG / ARTICLE

## Rola

Czytanie, SEO, edukacja.

## Poziom motion

Niski.

## Najlepsze efekty

- editorial heading reveal,
- image reveal,
- progress line optional,
- link underline.

## Unikać

- zakłócania czytania,
- ciężkich scroll effects,
- animowania każdego akapitu.

## Ryzyka

- SEO,
- readability,
- CLS,
- mobile.

---

## REGUŁA INTENSYWNOŚCI

Używaj tej proporcji na całej stronie:

- 80% strony: spokojne premium,
- 15% strony: cinematic motion,
- 5% strony: signature jaw-drop moments.

Nie rób wszystkiego jako signature moment.

---

## FINALNA ZASADA

Efekt ma pasować do zadania sekcji.

Hero może zachwycać.  
Koszyk ma uspokajać.  
PDP ma sprzedawać przez zaufanie.  
Restoration ma pokazywać jakość.  
Fine Art Oracle może być spektakularny.
