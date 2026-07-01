# Produkt katalogowy — zoom HD

Hub motywu: [`README.md`](README.md)  
Powiązany backend: [`../../cursor-api/docs/komponenty/dodajobraz.md`](../../cursor-api/docs/komponenty/dodajobraz.md) (zoom R2)

Zoom HD na karcie produktu reprodukcji — kafelki Deep Zoom z R2, nie dotyczy mockupu własnej fotografii.

---

## Pliki motywu

| Plik | Rola |
|------|------|
| `snippets/giclee-product-zoom.liquid` | Warunek metafield `custom.zoom_manifest`, OpenSeadragon |
| `assets/giclee-product-zoom.js` | Inicjalizacja viewer, ładowanie kafelków z manifestu |
| `assets/giclee-product-gallery.css` | Style galerii PDP |
| `snippets/product-information-content.liquid` | Render zoom tylko dla `product.nowy-szblon-produktu` |

---

## Metafield

- **Namespace:** `custom`
- **Key:** `zoom_manifest`
- **Typ:** JSON (manifest kafelków R2)

Snippet renderuje zoom tylko gdy metafield nie jest pusty:

```liquid
{%- assign zoom_mf = product.metafields.custom.zoom_manifest -%}
{%- if zoom_mf != blank -%}
  <div data-giclee-zoom data-giclee-zoom-manifest='{{ zoom_mf.value | json }}'>
```

---

## Przepływ end-to-end

```
dodajobraz (zoom_publish.py) → R2 (kafelki) + manifest JSON → Shopify metafield
    → motyw (giclee-product-zoom.js) → OpenSeadragon w PDP
```

Mapa: [`../zaleznosci.md`](../zaleznosci.md) → *Zoom HD na karcie produktu*

---

## Szablon produktu

Zoom jest podpięty pod szablony Giclee PDP: **`product.nowy-szblon-produktu`** (reprodukcje) i **`product.szablon-wlasna-fotografia`** (własna fotografia + mockup klienta).

### Mobile (`≤749px`)

- **`nowy-szblon-produktu`:** wysokość kontenera `58vh`; `fitArtworkCover` — obraz wypełnia viewer bez pasów tła (poziome i pionowe).
- **`szablon-wlasna-fotografia`:** kontener zoom R2 skrócony o połowę (`36vh`, min. `180px`); widok startowy `fitArtworkCover` (wypełnienie kontenera, bez pasów).
- Panel sterowania (`pinToolbar`): `position: absolute`, wyśrodkowany w widocznej części viewera; na mobile `z-index` poniżej `#header-component` — przy scrollu chowa się pod sticky header; po 2 s bez dotyku R2 fade out (także w fullscreen), dotknięcie przywraca panel.
- Desktop i inne szablony: `fitHorizontally` (pełna szerokość dzieła).
- Reset / double-click / resize (poza fullscreen) wraca do tego samego trybu.

---

## Deploy (typowa poprawka zoom)

```powershell
shopify theme push --store giclee-art-3.myshopify.com --theme 197314249052 --allow-live `
  --only "assets/giclee-product-zoom.js" "assets/giclee-product-zoom.css" "snippets/giclee-product-zoom.liquid" "sections/product-information.liquid"
```

Bump `?v=` w snippecie po zmianie JS.

---

## Diagnoza

| Objaw | Sprawdź |
|-------|---------|
| Brak zoom viewer | Metafield `custom.zoom_manifest` w Admin → Produkt |
| Viewer pusty / błąd 403 | URL kafelków w manifeście (R2 public) |
| Zoom na złym szablonie | `template.suffix == 'nowy-szblon-produktu'` w `product-information.liquid` |

→ [`troubleshooting.md`](troubleshooting.md) · [`../../cursor-api/docs/komponenty/dodajobraz.md`](../../cursor-api/docs/komponenty/dodajobraz.md)
