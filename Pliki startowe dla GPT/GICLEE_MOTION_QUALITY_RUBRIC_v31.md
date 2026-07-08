# GICLEE MOTION QUALITY RUBRIC v3.1

Skala jakości efektów motion / premium UI dla Giclée Cursor Architect.

Ten plik pomaga ocenić, czy efekt wygląda naprawdę premium, czy tylko technicznie działa.

---

## SKALA 1–5

### 1/5 — TANIO / PRZYPADKOWO

Efekt działa, ale wygląda źle.

Cechy:

- zbyt szybki ruch,
- skokowe przejścia,
- brak easing premium,
- przesadny blur/glow,
- neonowy wygląd,
- bounce/elastic,
- brak związku z treścią,
- psuje czytelność,
- wygląda jak przypadkowa animacja z tutoriala.

Wniosek: odrzucić albo przepisać.

---

### 2/5 — TECHNICZNIE POPRAWNE, ALE GENERYCZNE

Efekt nie psuje strony, ale nie podnosi jakości.

Cechy:

- zwykły fade-in,
- brak rytmu,
- brak relacji z obrazem/tekstem,
- wygląda jak template,
- nie ma detalu premium,
- działa, ale jest bez charakteru.

Wniosek: poprawić kompozycję, timing, easing i detale.

---

### 3/5 — ESTETYCZNIE POPRAWNE

Efekt jest dobry, ale jeszcze nie wyjątkowy.

Cechy:

- poprawne tempo,
- dobry easing,
- brak skoków,
- działa na mobile,
- nie psuje UX,
- pasuje do sekcji,
- ma podstawowy reduced motion.

Wniosek: akceptowalne, ale można dodać subtelny detal premium.

---

### 4/5 — PREMIUM / GICLÉE-LEVEL

Efekt wyraźnie podnosi jakość strony.

Cechy:

- spokojne tempo,
- cinematic easing,
- dobra hierarchia wejścia,
- tekst i obraz współpracują,
- jest subtelny detal: maska, światło, linia, głębia,
- efekt pasuje do Fine Art / museum / editorial,
- mobile jest dopracowane,
- reduced motion działa,
- brak zbędnych bibliotek.

Wniosek: bardzo dobry poziom dla większości sekcji.

---

### 5/5 — AWWWARDS / TOP STUDIO FEEL

Efekt wygląda jak zaprojektowany przez topowe studio kreatywne.

Cechy:

- ruch jest częścią narracji, nie ozdobą,
- każdy element wchodzi w idealnym rytmie,
- overlay, typografia, obraz i separator tworzą jeden moment,
- efekt jest subtelny, ale zapamiętywalny,
- kompozycja światła i cienia jest świadoma,
- nie ma przypadkowości,
- performance jest pod kontrolą,
- na mobile efekt jest uproszczony, ale nadal premium.

Wniosek: używać oszczędnie dla kluczowych momentów: hero, splash, ważne sekcje marki.

---

## CHECKLISTA OCENY EFEKTU

Przed uznaniem efektu za dobry, Cursor ma sprawdzić:

### Ruch

- Czy animacja nie jest za szybka?
- Czy easing wygląda naturalnie i premium?
- Czy nie ma skoków?
- Czy stagger jest subtelny?
- Czy efekt nie ma bounce/elastic bez powodu?

### Kompozycja

- Czy efekt prowadzi wzrok?
- Czy tekst jest czytelny?
- Czy obraz nie jest zasłonięty zbyt mocno?
- Czy overlay wspiera kompozycję?
- Czy linie, światło i maski mają sens?

### Marka

- Czy efekt pasuje do Fine Art?
- Czy wygląda muzealnie / editorialowo?
- Czy nie wygląda jak SaaS/startup/gaming?
- Czy nie jest zbyt agresywny sprzedażowo?

### Technika

- Czy używa transform/opacity zamiast width/height?
- Czy nie dodaje zbędnych bibliotek?
- Czy ma `prefers-reduced-motion`?
- Czy działa na mobile?
- Czy nie powoduje layout shift?
- Czy nie psuje istniejących modułów `giclee-*`?

### Performance

- Czy blur nie jest za ciężki?
- Czy event listenery są ograniczone?
- Czy scroll effect używa rAF rozsądnie?
- Czy assety są ładowane selektywnie?
- Czy nie ma globalnego scroll engine bez audytu?

---

## MINIMALNY STANDARD AKCEPTACJI

Efekt dla Giclée Art powinien mieć minimum 4/5 dla kluczowych sekcji.

Dla małych micro-interactions dopuszczalne jest 3/5, jeśli:

- nie psują UX,
- są spójne,
- są lekkie,
- poprawiają czytelność.

---

## JAK CURSOR MA RAPORTOWAĆ JAKOŚĆ

Po wdrożeniu efektu Cursor powinien napisać:

- ocena efektu: 1–5,
- dlaczego taka ocena,
- co ewentualnie podnieść do 5/5,
- czy efekt jest bezpieczny na mobile,
- czy reduced motion działa,
- czy dodano zbędne zależności,
- czy są ryzyka regresji.

---

## PRZYKŁAD OCENY

Efekt: Premium Typography Reveal dla nagłówka hero.

Ocena: 4/5.

Dlaczego:
- dobre tempo,
- mask reveal,
- separator od środka,
- reduced motion,
- brak nowych bibliotek.

Co podnieść:
- dopracować light sweep,
- dodać subtelny ambient glow dopasowany do zdjęcia,
- sprawdzić timing na mobile.
