# GICLEE CURSOR ARCHITECT v3.1 — PAKIET ULEPSZEŃ

Ten pakiet jest dodatkiem do v3, a nie zamiennikiem.

v3 ustawia główną rolę Giclée Cursor Architect.  
v3.1 dodaje praktyczne biblioteki i standardy jakości.

---

## Pliki w pakiecie

### 1. GICLEE_EFFECT_LIBRARY_v31.md

Biblioteka gotowych typów efektów premium:

- typography reveal,
- cinematic overlay,
- separator line expansion,
- museum image reveal,
- luxury hover,
- scroll storytelling,
- light sweep,
- gallery curtain transition,
- parallax frame,
- CTA micro-interaction.

### 2. GICLEE_MOTION_QUALITY_RUBRIC_v31.md

Skala oceny efektów 1–5:

- 1/5 — tanio i przypadkowo,
- 2/5 — działa, ale generycznie,
- 3/5 — estetycznie poprawnie,
- 4/5 — premium / Giclée-level,
- 5/5 — Awwwards / top studio feel.

### 3. GICLEE_IMPLEMENTATION_PATTERNS_v31.md

Techniczne wzorce wdrażania:

- IntersectionObserver,
- requestAnimationFrame,
- CSS reveal,
- overlay pattern,
- separator pattern,
- kiedy nie dodawać GSAP,
- kiedy rozważyć GSAP,
- cache bust,
- docs,
- testy.

### 4. GICLEE_BAD_EFFECTS_BLACKLIST_v31.md

Lista efektów i decyzji, których unikać:

- neon,
- glitch,
- bounce,
- elastic,
- globalny smooth scroll bez audytu,
- GSAP dla jednej linii,
- React/Tailwind dla motywu Liquid,
- animowanie width/height zamiast transform.

### 5. GICLEE_CURSOR_EXAMPLES_v31.md

Przykłady dobrych odpowiedzi:

- animacja napisu,
- cinematic overlay,
- audyt skokowej animacji,
- product card hover,
- duży scroll storytelling,
- krótki prompt.

---

## Jak używać

Zostaw jako główne instrukcje:

- GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_v3.md

Dodaj jako pliki wiedzy:

- GICLEE_AWWWARDS_MOTION_SYSTEM_v3.md
- GICLEE_RESEARCH_DRIVEN_EFFECTS_v3.md
- GICLEE_PROMPT_RESPONSE_MODES_v3.md
- GICLEE_CODE_PLUS_PROMPT_WORKFLOW_v3.md

I dodatkowo dodaj pakiet v3.1:

- GICLEE_EFFECT_LIBRARY_v31.md
- GICLEE_MOTION_QUALITY_RUBRIC_v31.md
- GICLEE_IMPLEMENTATION_PATTERNS_v31.md
- GICLEE_BAD_EFFECTS_BLACKLIST_v31.md
- GICLEE_CURSOR_EXAMPLES_v31.md

---

## Efekt

Po dodaniu v3.1 model powinien:

- mieć własną bibliotekę efektów premium,
- lepiej oceniać, czy efekt naprawdę wygląda premium,
- unikać tanich animacji,
- częściej dawać kod referencyjny + prompt,
- pilnować performance i stacku,
- działać bardziej jak creative director + motion designer + tech lead.
