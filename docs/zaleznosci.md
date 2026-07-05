# Mapa zależności — integracja 3 warstw

Plik startowy: [`MATKA.md`](../MATKA.md) (korzeń `pusty/`)  
Hub integracyjny: [`README.md`](README.md) — polityka docs: **modułowe pliki = prawda**, SHOP/THEME = archiwum.

Ten plik łączy **pusty** (motyw), **cursor-api** (API + komponenty) i **giclee_app** (launcher).  
Używaj go do szybkiej diagnozy: symptom → warstwa → plik.

---

## Przepływ: własna fotografia klienta

```
Klient → motyw (upload JS) → Worker → R2 → Shopify (_Upload ID) → webhook → Resend → mail
```

| Krok | Warstwa | Plik |
|------|---------|------|
| UI mockup, scroll → koszyk | **pusty** | [`assets/giclee-photo-mockup.js`](../assets/giclee-photo-mockup.js) (`pmScrollPageToTopForCart`), [`layout/theme.liquid`](../layout/theme.liquid) (`pmAddConfiguredToCart`) |
| Upload API | **cursor-api** | [`mockup-order-worker/src/index.js`](../cursor-api/mockup-order-worker/src/index.js) |
| Pliki w chmurze | **cursor-api** | R2 bucket `giclee-zoom`, prefix `customer-uploads/{uuid}/` |
| Property zamówienia | **pusty** | `properties[_Upload ID]` w `theme.liquid`; `properties[Passepartout]` w `giclee-passepartout-picker`; cena/dostępność PDP reprodukcji: `giclee-pdp-variant-sync.js` + JSON wariantów w `variant-main-picker.liquid` (sosna → tylko czarny, ceny z `product.variants`) |
| E-mail po opłaceniu | **cursor-api** | Worker webhook + Resend |

Szczegóły: [`motyw/mockup-wlasna-fotografia.md`](motyw/mockup-wlasna-fotografia.md) · [`../cursor-api/docs/worker/mockup-order-worker.md`](../cursor-api/docs/worker/mockup-order-worker.md)

---

## Przepływ: reprodukcja katalogowa

```
GicleeApp → dodajobraz → Shopify (produkt + zoom manifest) → motyw (karta produktu + zoom HD)
```

| Krok | Warstwa | Plik |
|------|---------|------|
| Tworzenie produktu | **cursor-api** | [`Komponenty/dodajobraz/create.py`](../cursor-api/Komponenty/dodajobraz/create.py) |
| Zoom HD (kafelki R2) | **cursor-api** | [`Komponenty/dodajobraz/zoom_publish.py`](../cursor-api/Komponenty/dodajobraz/zoom_publish.py) |
| Wyświetlanie zoom | **pusty** | [`snippets/giclee-product-zoom.liquid`](../snippets/giclee-product-zoom.liquid), [`assets/giclee-product-zoom.js`](../assets/giclee-product-zoom.js) |

Szczegóły: [`motyw/produkt-i-zoom.md`](motyw/produkt-i-zoom.md) · [`../cursor-api/docs/komponenty/dodajobraz.md`](../cursor-api/docs/komponenty/dodajobraz.md)

---

## Przepływ: stronicowany opis (PDP v3)

```
GicleeApp → stronaproduktu → Shopify (metafield custom.story_pages + Shopify Files)
    → motyw (giclee-product-story.js — mini strony pod zoomem R2)
```

| Krok | Warstwa | Plik |
|------|---------|------|
| Konfiguracja stron + upload grafik | **cursor-api** | [`Komponenty/stronaproduktu/service.py`](../cursor-api/Komponenty/stronaproduktu/service.py) |
| Render mini stron | **pusty** | [`snippets/giclee-product-story.liquid`](../snippets/giclee-product-story.liquid), [`assets/giclee-product-story.js`](../assets/giclee-product-story.js) |

Bez metafielda motyw dzieli akapity automatycznie (featured image jako grafika).

**Efekty PDP v3 (globalne):** GicleeApp → stronaproduktu → **Ustawienia efektów** → metafield **shop** `custom.pdp_v3_effects` (JSON) + Shopify Files (tła) → motyw (`window.__PDP_V3_EFFECTS__` w `sections/product-information.liquid`; efekty: immersive zoom, blur R2, tło konfiguratora z parallaxem, wspólne tło proces+trust).

Szczegóły: [`motyw/szablony-i-strony.md`](motyw/szablony-i-strony.md) · wzorzec scroll choreography: [`motyw/pdp-v3-pusty-scroll.md`](motyw/pdp-v3-pusty-scroll.md) · [`../cursor-api/docs/komponenty/stronaproduktu.md`](../cursor-api/docs/komponenty/stronaproduktu.md)

---

## Przepływ: strony menu (wygląd szablonów)

```
GicleeApp → <komponent strony menu> → templates/*.json (motyw lokalny)
    → backup w Komponenty/<id>/data/backups/
    → shopify theme push (deploy)
```

| Pozycja menu | Komponent | Szablon |
|--------------|-----------|---------|
| Giclée Frame | `gicleeframe` | `templates/page.giclee-frame.json` |
| Własna fotografia | `wlasnafotografia` | `templates/product.szablon-wlasna-fotografia.json` |
| Katalog | `katalog` (+ `dodajobraz` dla artystów) | `templates/collection.json` |
| Współpraca | `wspolpraca` | `templates/page.wspolpraca.json` |
| Filozofia marki | `filozofiamarki` | `templates/page.filozofia-marki.json` |
| Kontakt | `kontakt` | `templates/page.contact.json` |
| Blog (layout) | `stronablogu` | `templates/blog.json` |
| FAQ | `faq` | `templates/page.faq.json` |
| Losuj Obraz | `losujobraz` | `templates/page.losuj-produkt.json` |

Wspólna warstwa: `Komponenty/_shared/theme_page_editor/`. Treści postów bloga — osobno komponent `blog` (Marketing).

Szczegóły: [`../cursor-api/docs/komponenty/README.md`](../cursor-api/docs/komponenty/README.md) · wzorzec: [`stronaglowna.md`](../cursor-api/docs/komponenty/stronaglowna.md)

---

## Przepływ: mockup katalogowy (CZB/CZCZ)

```
GicleeApp → Komponenty/mockup → Shopify (zdjęcie produktu z sufiksem mockup)
```

**To NIE jest mockup klienta na stronie.** Mockup klienta = motyw + Worker.

| Warstwa | Plik |
|---------|------|
| **cursor-api** | [`Komponenty/mockup/publish.py`](../cursor-api/Komponenty/mockup/publish.py) |

Szczegóły: [`../cursor-api/docs/komponenty/mockup-katalogowy.md`](../cursor-api/docs/komponenty/mockup-katalogowy.md)

---

## Przepływ: produkcja zamówień

```
GicleeApp → produkcja → Shopify orders (REST)
```

| Warstwa | Plik |
|---------|------|
| **cursor-api** | [`Komponenty/produkcja/orders_sync.py`](../cursor-api/Komponenty/produkcja/orders_sync.py) |

**Luka znana:** komponent `produkcja` widzi pozycje „Własna fotografia” w zamówieniach, ale **nie łączy** `_Upload ID` z plikami w R2 — pliki klienta trafiają mailem z Workera, nie przez produkcję.

---

## Przepływ: jakość PPI (panel w mockupie)

| Warstwa | Plik |
|---------|------|
| **pusty** | [`lib/giclee-print-analysis/`](../lib/giclee-print-analysis/), [`layout/theme.liquid`](../layout/theme.liquid) (`initPmQualityPanel`) |

Wspólna matematyka z kalkulatorem GicleeLab — tylko warstwa motywu (brak zależności od Pythona).

---

## Przepływ: Limity i Poczta (GicleeApp)

```
GicleeApp → limity  → API zewnętrzne (R2, Resend, SerpAPI, Meta debug_token)
GicleeApp → poczta  → Gmail IMAP (odczyt gicleeartpl@gmail.com)
GicleeApp → limity → „Odnów tokeny” → meta_renew_wizard → meta_credentials.json (cykl)
```

| Krok | Warstwa | Plik |
|------|---------|------|
| Dashboard limitów | **giclee_app** → **cursor-api** | [`Komponenty/limity/view.py`](../cursor-api/Komponenty/limity/view.py), [`collectors.py`](../cursor-api/Komponenty/limity/collectors.py) |
| Licznik Resend | **cursor-api** | Paginacja GET `/emails` (nie nagłówki `x-resend-*`) |
| Odnowa Meta (4 kanały) | **cursor-api** | [`socialmedia/cykl/meta_renew_wizard.py`](../cursor-api/Komponenty/socialmedia/cykl/meta_renew_wizard.py) |
| Podgląd Gmail | **cursor-api** | [`Komponenty/poczta/imap_client.py`](../cursor-api/Komponenty/poczta/imap_client.py) |

**Resend — dwa klucze:** Worker (`wrangler secret`) może mieć **send-only**; kafelek Limity w `.env` potrzebuje **Full access** do odczytu listy wysłanych.

Szczegóły: [`../cursor-api/docs/komponenty/limity.md`](../cursor-api/docs/komponenty/limity.md) · [`poczta.md`](../cursor-api/docs/komponenty/poczta.md) · [`meta-tokeny.md`](../cursor-api/docs/komponenty/meta-tokeny.md) · [`USLUGI.md`](../USLUGI.md)

---

## Infrastruktura wspólna

| Zasób | Kto używa | Uwagi |
|-------|-----------|-------|
| **R2** `giclee-zoom` | Worker (`customer-uploads/`), `dodajobraz` (zoom reprodukcji) | Różne prefixy — nie mylić |
| **OAuth** `.shopify_session.json` | Wszystkie komponenty Python | Kanoniczny shop: `19v3bj-n0.myshopify.com` |
| **Shopify CLI alias** | `theme push` | `giclee-art-3.myshopify.com` |
| **Motyw live** | Deploy motywu | ID `#197314249052` |

Szczegóły API: [`../cursor-api/docs/zaleznosci-wewnetrzne.md`](../cursor-api/docs/zaleznosci-wewnetrzne.md)

---

## Macierz diagnozy: symptom → warstwa → plik

| Symptom | Warstwa | Plik / następny krok |
|---------|---------|----------------------|
| Brak maila po opłaceniu | **pusty** → **cursor-api** | Zamówienie: `_Upload ID` → [`worker/mockup-order-worker.md`](../cursor-api/docs/worker/mockup-order-worker.md) webhook |
| Upload fail / CORS | **cursor-api** | `wrangler.toml` `ALLOWED_ORIGINS` + konsola JS |
| Czarny prostokąt zamiast ramki | **pusty** | `giclee-photo-mockup.liquid` → `#pm-frame` + `setFrame()` |
| Po „Dodaj do koszyka” strona nie jedzie na górę | **pusty** | `pmScrollPageToTopForCart` → [`motyw/mockup-wlasna-fotografia.md`](motyw/mockup-wlasna-fotografia.md) |
| Scroll wraca do mockupu po koszyku | **pusty** | `pmPauseMockupAutoScroll`, `scrollMockupToViewportCenter` — ten sam doc |
| Zoom HD pusty na karcie | **pusty** → **cursor-api** | Metafield `custom.zoom_manifest` → `dodajobraz/zoom_publish.py` |
| OAuth wygasł / 401 API | **cursor-api** | `.shopify_session.json`, `npm run oauth` |
| Kafelek nie w launcherze | **giclee_app** | Brak `__main__.py` → [`component-loader.md`](../cursor-api/giclee_app/docs/component-loader.md) |
| Niska jakość w mailu | **cursor-api** | R2: `original-full.jpg` vs `original.*` w Worker |
| Produkcja bez pliku klienta | **znana luka** | Użyj maila z Workera; `_Upload ID` nie jest jeszcze w produkcji |
| OAuth 401 w komponencie | **cursor-api** | `npm run oauth` → [`cursor-api/docs/zaleznosci-wewnetrzne.md`](../cursor-api/docs/zaleznosci-wewnetrzne.md) |
| Reprodukcja bez zoom HD | **cursor-api** → **pusty** | `zoom_publish.py` → metafield → [`motyw/produkt-i-zoom.md`](motyw/produkt-i-zoom.md) |
| Mockup CZB na złym produkcie | **cursor-api** | [`komponenty/mockup-katalogowy.md`](../cursor-api/docs/komponenty/mockup-katalogowy.md) — parser nazwy |
| Blog nie publikuje | **cursor-api** | Scope `write_content`, [`komponenty/blog.md`](../cursor-api/docs/komponenty/blog.md) |
| Limity: Resend HTTP 403 | **cursor-api** | Brak `User-Agent` w requestach — naprawione w `collectors.py`; sprawdź klucz |
| Limity: Resend HTTP 401 restricted | **cursor-api** | Klucz send-only — w `.env` ustaw **Full access** (Worker może zostać send-only) |
| Limity: Resend „brak danych” przy OK | **cursor-api** | Licznik z listy `/emails`, nie z nagłówków quota |
| Poczta: IMAP login failed | **cursor-api** | Hasło **aplikacji** Google (16 znaków), nie zwykłe hasło — [`poczta.md`](../cursor-api/docs/komponenty/poczta.md) |
| Meta: token wygasł / brak daty | **cursor-api** | Limity → **Odnów tokeny** → [`meta-tokeny.md`](../cursor-api/docs/komponenty/meta-tokeny.md) |
| Limity: scroll kółkiem nie działa | **giclee_app** | Re-bind wheel po `render()` w `limity/view.py` |

---

## Indeks komponentów → dokumentacja

| Komponent | Plik docs |
|-----------|-----------|
| dodajobraz | [`../cursor-api/docs/komponenty/dodajobraz.md`](../cursor-api/docs/komponenty/dodajobraz.md) |
| produkcja | [`../cursor-api/docs/komponenty/produkcja.md`](../cursor-api/docs/komponenty/produkcja.md) |
| mockup (katalog) | [`../cursor-api/docs/komponenty/mockup-katalogowy.md`](../cursor-api/docs/komponenty/mockup-katalogowy.md) |
| limity, poczta | [`limity.md`](../cursor-api/docs/komponenty/limity.md) · [`poczta.md`](../cursor-api/docs/komponenty/poczta.md) |
| Meta tokeny (cykl) | [`meta-tokeny.md`](../cursor-api/docs/komponenty/meta-tokeny.md) |
| wszystkie 17 | [`../cursor-api/docs/komponenty/README.md`](../cursor-api/docs/komponenty/README.md) |
| GicleeApp | [`../cursor-api/giclee_app/docs/README.md`](../cursor-api/giclee_app/docs/README.md) |

Troubleshooting per warstwa:

- Motyw: [`motyw/troubleshooting.md`](motyw/troubleshooting.md)
- API: [`../cursor-api/docs/troubleshooting.md`](../cursor-api/docs/troubleshooting.md)
- GicleeApp: [`../cursor-api/giclee_app/docs/troubleshooting.md`](../cursor-api/giclee_app/docs/troubleshooting.md)
- Indeks: [`troubleshooting/README.md`](troubleshooting/README.md)
