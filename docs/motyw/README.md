# Motyw Shopify — indeks

Warstwa **pusty** (sklep front). Hub: [`../README.md`](../README.md) · polityka docs: tam samo.

**Prawda:** pliki w tym folderze. **Archiwum (czytaj, nie pisz):** [`../../THEME_KNOWLEDGE.md`](../../THEME_KNOWLEDGE.md).

---

## Dokumenty w tym folderze

| Plik | Temat |
|------|--------|
| [`mockup-wlasna-fotografia.md`](mockup-wlasna-fotografia.md) | Edytor zdjęcia klienta, upload, koszyk, layout |
| [`koszyk-faktura.md`](koszyk-faktura.md) | Prośba o fakturę w koszyku (osoba prywatna / firma) |
| [`produkt-i-zoom.md`](produkt-i-zoom.md) | Zoom HD na karcie reprodukcji (OpenSeadragon + R2) |
| [`szablony-i-strony.md`](szablony-i-strony.md) | Szablony custom: fotografia, PDP, menu |
| [`troubleshooting.md`](troubleshooting.md) | Layout, deploy, UI mockupu |
| [`kolekcja-autora-showcase.md`](kolekcja-autora-showcase.md) | Galeria 3D / editorial kolekcji autora |
| [`losuj-obraz.md`](losuj-obraz.md) | „Losuj Obraz” — scena WebGL (Three.js) + fallback CSS |
| [`tlumaczenia-tresci.md`](tlumaczenia-tresci.md) | Treści motywu po PL — klucze `giclee.*`, locale, JS |

Powiązane: [`../jakosc-wydruku/README.md`](../jakosc-wydruku/README.md) (PPI w panelu mockupu)

---

## Kluczowe lokalizacje w kodzie

| Obszar | Pliki |
|--------|--------|
| Layout globalny | `layout/theme.liquid` — konfigurator `#pm-config`, panel jakości, `pmAddConfiguredToCart`, scroll → koszyk |
| Mockup (snippet) | `snippets/giclee-photo-mockup.liquid` |
| Mockup (logika) | `assets/giclee-photo-mockup.js`, `assets/giclee-photo-mockup.css` |
| Zoom HD | `snippets/giclee-product-zoom.liquid`, `assets/giclee-product-zoom.js` |
| Strona edytora | `templates/page.fotografia-obraz.json` |
| Produkt własna fotografia | `templates/product.szablon-wlasna-fotografia.json` |
| PDP reprodukcji | `templates/product.nowy-szblon-produktu.json` |
| Ustawienia upload URL | `config/settings_schema.json` → `pm_upload_api_url` |
| Style globalne | `assets/custom.css`, `assets/base.css` |
| Galeria kolekcji autora | `sections/giclee-artist-collection-showcase.liquid`, `assets/giclee-artist-collection-showcase.*` |
| Losuj Obraz (WebGL) | `sections/giclee-random-artwork.liquid`, `assets/giclee-random-artwork*.js`, `assets/three.module.js`, `templates/page.losuj-produkt.json` |
| Biografia + stan autora | `sections/giclee-artist-biography.liquid`, `assets/giclee-active-author.js`, `assets/giclee-artist-biography.*` |

---

## Zależności z innymi warstwami

| Motyw używa | Warstwa | Dokument |
|-------------|---------|----------|
| Upload API, mail po zakupie | cursor-api | [`../../cursor-api/docs/worker/mockup-order-worker.md`](../../cursor-api/docs/worker/mockup-order-worker.md) |
| Zoom manifest na produkcie | cursor-api | [`../../cursor-api/docs/komponenty/dodajobraz.md`](../../cursor-api/docs/komponenty/dodajobraz.md) |
| Mapa przepływów | integracja | [`../zaleznosci.md`](../zaleznosci.md) |

---

## Deploy motywu (live)

Motyw docelowy: **Kopia Giclee Art Br** `#197314249052` na `giclee-art-3.myshopify.com`.

```powershell
cd c:\Strona\pusty

shopify theme push --store giclee-art-3.myshopify.com --theme 197314249052 --allow-live `
  --only "assets/giclee-photo-mockup.js" "assets/giclee-photo-mockup.css" `
  "snippets/giclee-photo-mockup.liquid" "layout/theme.liquid"
```

Po zmianie JS/CSS bump wersji cache w liquid (`?v=…`).

---

## Breakpointy layoutu mockupu

| Szerokość | Układ |
|-----------|--------|
| `< 1024px` | Tablet/telefon: elementy **pod** mockupem |
| `1024–1400px` | Laptop: panele z boku; mockup skalowany do `100vh` |
| `> 1400px` | Desktop: pełny układ boczny |

Logika: `syncPmMockupCenterUi()` w `giclee-photo-mockup.js`.

Flow koszyka (scroll na górę → drawer): [`mockup-wlasna-fotografia.md`](mockup-wlasna-fotografia.md#przepływ-dodaj-do-koszyka-ui).
