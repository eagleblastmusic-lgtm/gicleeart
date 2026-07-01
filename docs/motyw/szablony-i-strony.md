# Szablony i strony custom

Hub motywu: [`README.md`](README.md)

Kluczowe szablony Online Store 2.0 poza standardowym `product.json` / `page.json`.

---

## Własna fotografia klienta

| Szablon | Plik JSON | Użycie |
|---------|-----------|--------|
| Strona edytora | `templates/page.fotografia-obraz.json` | `/pages/fotografia-obraz` — pełnoekranowy edytor |
| Produkt custom print | `templates/product.szablon-wlasna-fotografia.json` | PDP z mockupem w flow zakupu |

Wspólne snippety:

- `snippets/giclee-photo-mockup.liquid` — mockup + upload
- `snippets/giclee-lab-shell.liquid` — drawer GicleeLab
- `snippets/product-information-content.liquid` — gałąź `szablon-wlasna-fotografia`

Warunki w `layout/theme.liquid`:

```liquid
{% if template.suffix == 'fotografia-obraz' or template.suffix == 'szablon-wlasna-fotografia' %}
```

Szczegóły mockupu: [`mockup-wlasna-fotografia.md`](mockup-wlasna-fotografia.md) (w tym flow scroll → panel koszyka po **Dodaj do koszyka**).

Mobile (`≤749px`): opis produktu na pełną szerokość — `assets/custom.css` (`product.szablon-wlasna-fotografia`; ukryta kolumna SZCZEGÓŁY nie rezerwuje już połowy tabeli).

---

## Reprodukcje katalogowe (PDP)

| Szablon | Plik JSON | Użycie |
|---------|-----------|--------|
| Nowy PDP | `templates/product.nowy-szblon-produktu.json` | Reprodukcje z zoom HD, galeria, trust |
| PDP v2 | `templates/product.szablon-produktu-v2.json` | Kopia `nowy-szblon-produktu` + sekcja porównania przed/po; **bez** sticky paska «Dodaj do koszyka» |

Mobile (`≤749px`):

- panel **SZCZEGÓŁY** w opisie produktu pod akapitami (nie obok) na mobile; na desktopie kolumna SZCZEGÓŁY wyśrodkowana — `assets/custom.css`, selektor `main[data-giclee-repro-pdp='true']` (ustawiane w `layout/theme.liquid` dla `nowy-szblon-produktu` i `szablon-produktu-v2`);
- zoom R2: stały kontener (`58vh`) + `fitArtworkCover` na starcie — `assets/giclee-product-zoom.js` + `assets/giclee-product-zoom.css`;
- galeria mockupów: scena dopasowuje proporcje do aktywnego zdjęcia, obraz wypełnia więcej miejsca; separator pod galerią — `assets/giclee-product-gallery.js` + `.css`;
- scroll reveal (mobile + desktop): nagłówek (tytuł/autor/daty) → opis → SZCZEGÓŁY → galeria → konfigurator — osobne animacje, `assets/giclee-product-scroll-reveal.js` + `.css`.

Powiązane snippety:

- `snippets/giclee-product-gallery.liquid`
- `snippets/giclee-product-zoom.liquid`
- `snippets/giclee-product-trust.liquid`
- `snippets/giclee-product-process.liquid`
- `snippets/giclee-product-before-after-compare.liquid` — markup suwaka przed/po (tylko `szablon-produktu-v2`)
- `sections/product-before-after-compare.liquid` — ustawienia w edytorze (`image_before`, `image_after`, teksty)

**Porównanie przed/po (v2):** sekcja `before_after_compare` w `product.szablon-produktu-v2.json` (pierwsza w `order`). Markup trafia do slotu nad `giclee-product-process` przez synchroniczny przenos w `product-information-content.liquid`. **Grafika «przed»:** metafield `custom.before_retouch_url` (GicleeApp → **Przed/Po**). **«Po»:** obraz Full z galerii produktu. Bez obu warstw sekcja się nie renderuje. Assety: `giclee-product-before-after-compare.css` / `.js`. Teksty (eyebrow, tytuł, opis) — ustawienia sekcji w edytorze motywu.

Szczegóły zoom: [`produkt-i-zoom.md`](produkt-i-zoom.md)

### Przycisk BLIK (PL zamiast Shop Pay)

Dla `localization.country.iso_code == 'PL'` blok `blocks/accelerated-checkout.liquid` renderuje własny przycisk zamiast `payment_button` (Shop Pay).

| Plik | Rola |
|------|------|
| `snippets/blik-checkout-button.liquid` | UI: „Wygodna płatność z” + logo `assets/logo-blik.png` |
| `assets/blik-checkout-button.js` | `/cart/add.js` → przekierowanie `/checkout` (BLIK w Shopify Payments) |
| `snippets/buy-buttons-styles.liquid` | Style przycisku (czarny, jak Shop Pay) |

Logo pochodzi z oficjalnych [materiałów marketingowych BLIK](https://www.blik.com/materialy-marketingowe). To nie jest ekspresowy portfel 1-klik — klient przechodzi standardową kasę Shopify.

---

## Nawigacja / menu

- `snippets/giclee-resolve-menu-url.liquid` — link „Własna fotografia” kieruje na PDP produktu, nie na `/pages/fotografia-obraz`
- `layout/theme.liquid` — scroll lock / layout specjalny dla `fotografia-obraz`

---

## Ustawienia motywu (mockup)

`config/settings_schema.json` → sekcja **Mockup — własna fotografia**:

- `pm_upload_api_url` — nadpisanie URL Workera (domyślnie w snippecie)

---

## Deploy szablonów

```powershell
shopify theme push --store giclee-art-3.myshopify.com --theme 197314249052 --allow-live `
  --only "templates/page.fotografia-obraz.json" `
  "templates/product.szablon-wlasna-fotografia.json"
```

Pełna lista custom suffixów: [`../../THEME_KNOWLEDGE.md`](../../THEME_KNOWLEDGE.md) §2.
