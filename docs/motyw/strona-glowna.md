# Strona główna (landing)

Szablon: `templates/index.json` · GicleeApp: [`cursor-api/docs/komponenty/stronaglowna.md`](../../cursor-api/docs/komponenty/stronaglowna.md)

---

## Układ

Strona główna to sekwencja sekcji Horizon (slideshow, `section`, `divider`, bloki `comparison-slider`) — bez dedykowanego `giclee-homepage.liquid`.

| Kolejność | Sekcja | Typ treści |
|-----------|--------|------------|
| 1 | Slideshow full frame | Hero — 1 slajd |
| 2 | Giclée Art | Portret + opis pracowni |
| 3 | Odrestaurowywanie dzieł | Tekst + suwak przed/po |
| 4 | Autorska korekcja | Suwak + tekst + CTA |
| 5 | Potencjał… | Tekst + suwak |
| 6 | Zobacz różnicę | 2× suwak + tekst centralny |

Separatory: bloki `divider` między sekcjami.

---

## Zachowanie poza Theme Editor

| Element | Plik |
|---------|------|
| Splash + scroll reveal | `layout/theme.liquid` |
| Mobile hero (lista z JS, nie hardcode) | `assets/giclee-home-mobile.js`, `layout/theme.liquid` |
| Hero kolaż wideo | `blocks/_slide.liquid`, `assets/giclee-hero-video-collage*.js`, `collage_gui.py` |
| Hooki sekcji `data-giclee-home` | `assets/giclee-home-sections.js`, `giclee-home-sections-boot.js` |
| Animacja intro sekcji Giclée Art | `assets/custom.css` (`data-giclee-home="intro"`) |
| Układ mobile sekcji | `assets/custom.css` |
| Suwaki przed/po | `blocks/comparison-slider.liquid`, `assets/comparison-slider.js` |
| Modal «site notice» | `snippets/giclee-site-notice.liquid`, `?giclee_skip_notice=1` |

Parametry podglądu dev: `?giclee_skip_splash=1` (pomiń splash), `?giclee_skip_notice=1` (pomiń modal).

---

## Edycja treści

**GicleeApp → Strona główna** — sekcje, miniaturki, drag-and-drop, diff przed zapisem, walidacja, historia kopii, podgląd live/theme dev, deploy z wyborem celu.

Alternatywa: Shopify Theme Editor (ryzyko nadpisania przy deploy z repo).

Po zmianie w repo: **wdrożenie motywu** na sklep.
