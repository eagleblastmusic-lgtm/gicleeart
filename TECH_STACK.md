# TECH_STACK

> Dokument kontekstowy dla Custom GPT tworzącego prompty do Cursor.  
> Repozytorium: **GicleeArt** — sklep artystyczny (gicleeart.eu).  
> Ostatnia analiza: 2026-07-03.

---

## 1. Stack projektu

### Warstwy (3 niezależne systemy w jednym repo)

| Warstwa | Folder | Technologie | Rola |
|---------|--------|-------------|------|
| **Motyw sklepu** | korzeń `pusty/` | Shopify Liquid, vanilla JS (ES modules), CSS | Front sklepu (PDP, koszyk, mockup klienta, zoom HD) |
| **API / mechanika** | `cursor-api/` | Python 3.x, Tkinter, Express, Shopify Admin API | Backoffice: produkty, faktury, produkcja, analityka |
| **Launcher** | `cursor-api/giclee_app/` | Python (Tkinter GUI) | Uruchamianie komponentów z GUI |

### Motyw Shopify (front)

| Technologia | Wersja / uwagi |
|-------------|------------------|
| **Shopify Theme** | Motyw bazowy **Horizon 3.5.0** (Online Store 2.0) |
| **Liquid** | Szablony, sekcje, snippety, bloki |
| **JavaScript** | ES modules, **import map** `@theme/*` (patrz `snippets/scripts.liquid`) |
| **Web Components** | Klasa bazowa `Component` w `assets/component.js` (Horizon + rozszerzenia Giclee) |
| **CSS** | Pliki statyczne w `assets/` — **bez Tailwind, bez React, bez TypeScript** |
| **Three.js** | `assets/three.module.js` — scena WebGL („Losuj Obraz”) |
| **OpenSeadragon** | Zoom HD reprodukcji (CDN jsDelivr) |
| **Playwright** | Testy layoutu (devDependency w korzeniowym `package.json`) |

**Animacje (stan obecny):** vanilla JS + CSS (`transform`, `opacity`, `IntersectionObserver`, `requestAnimationFrame`, CSS custom properties dla scroll progress). Moduły `giclee-*` ładowane **selektywnie** z Liquid per szablon/sekcja. Szczegóły wyboru technologii → [§ Strategia animacji](#strategia-rozwoju-animacji-i-scroll-storytellingu).

### cursor-api (backoffice)

| Technologia | Wersja / uwagi |
|-------------|------------------|
| **Python** | 3.x, GUI: **Tkinter** |
| **Shopify Admin API** | REST + GraphQL, wersja API `2026-04` |
| **Express** | OAuth server (`oauth-server.mjs`) |
| **Cloudflare Worker** | Wrangler 4.x — upload R2, webhook Shopify, analityka D1 |
| **SQLite** | Analityka lokalna, niektóre moduły finansowe |
| **reportlab** | Generowanie PDF faktur |
| **Gemini / OpenAI** | Tytuły AI, optymalizacja druku, zadania marketingowe |
| **PyInstaller** | Build exe GicleeApp (`giclee_app.spec`) |

### Inne aplikacje w repo

| Folder | Stack | Rola |
|--------|-------|------|
| `cursor-api/mockup-order-worker/` | Cloudflare Worker (JS) | Upload klienta → R2, mail po zakupie, collect analityki |
| `ceny-marketingowe-app/` | Vite 6, vanilla JS | Osobna mini-apka (P&L marketing) |
| `lib/giclee-print-analysis/` | Vanilla JS | Matematyka PPI w mockupie (współdzielona z motywem) |

### Usługi zewnętrzne

| Usługa | Użycie |
|--------|--------|
| **Shopify** | Sklep, checkout, Markets, Translations API, Customer Events (pixel) |
| **Cloudflare R2** | Zoom HD, uploady klientów (`giclee-zoom`) |
| **Cloudflare D1** | Eventy analityki (`giclee-analytics`) |
| **Resend** | E-mail po opłaceniu zamówieniu z uploadem |
| **NBP API** | Kursy EUR/PLN (cache 24h, bez klucza) |
| **Gmail IMAP/SMTP** | Poczta firmowa, wysyłka faktur |
| **Meta Graph API** | Social media (cykl postów) |
| **SerpAPI** | Google Lens w „Nazwij obraz" |
| **Vercel** | Kalkulator GicleeLab (iframe) |

### Czego **domyślnie nie ma** w projekcie (możliwe po audycie — patrz strategia animacji)

- Brak React / Vue / Next.js na froncie sklepu (nie domyślna ścieżka dla motywu Shopify)
- Brak TypeScript (tylko JSDoc / `@ts-nocheck` w wybranych plikach)
- Brak Tailwind CSS, styled-components, CSS Modules (nie domyślna ścieżka stylowania)
- Brak centralnego routera SPA — routing obsługuje Shopify
- Brak GSAP / ScrollTrigger w repo (stan na 2026-07-03) — **dopuszczalne** przy większym scroll storytellingu po audycie sekcji
- Brak Framer Motion, Lenis, Locomotive Scroll — nie domyślna ścieżka dla obecnego motywu

---

## 2. Struktura folderów

```
pusty/                          ← REPO (motyw + docs)
├── layout/                     ← layouty Liquid (theme.liquid)
├── templates/                  ← szablony JSON (OS 2.0) — mapowanie URL Shopify
├── sections/                   ← sekcje motywu (Horizon + giclee-*)
├── blocks/                     ← bloki OS 2.0 (kompozycja sekcji)
├── snippets/                   ← fragmenty Liquid (giclee-*, header, cart…)
├── assets/                     ← JS, CSS, obrazy (giclee-* = custom GicleeArt)
├── config/                     ← settings_schema.json, settings_data.json
├── locales/                    ← tłumaczenia motywu (pl, en, de, fr, es, nl, it)
├── lib/                        ← współdzielone JS (PPI, rozmiary ramek)
├── docs/                       ← dokumentacja motywu (PRAWDA modułowa)
├── MATKA.md                    ← skrót startowy dla AI
├── USLUGI.md                   ← konta zewnętrzne, limity, plany
├── shopify.theme.toml          ← konfiguracja Shopify CLI
├── package.json                ← Playwright (audit layoutu)
│
├── cursor-api/                 ← warstwa API
│   ├── Komponenty/             ← moduły Python (jeden folder = jeden komponent)
│   │   ├── _shared/            ← auth, NBP, activity_log, UI helpers
│   │   ├── dodajobraz/         ← tworzenie produktów Shopify
│   │   ├── dokumentysprzedazy/ ← faktury, sync zamówień
│   │   ├── produkcja/          ← zamówienia produkcyjne
│   │   ├── finanse/            ← hub księgowości
│   │   ├── analytics/          ← analityka ruchu
│   │   └── …                   ← ~35 komponentów (component.json każdy)
│   ├── giclee_app/             ← launcher GUI (Tkinter)
│   ├── mockup-order-worker/    ← Cloudflare Worker
│   ├── tests/                  ← pytest (~46 plików testowych)
│   ├── docs/                     ← dokumentacja API (PRAWDA modułowa)
│   ├── .env                      ← sekrety (NIE commitować)
│   ├── .shopify_session.json     ← token OAuth (NIE commitować)
│   └── shopify.app.toml          ← konfiguracja Shopify App
│
├── ceny-marketingowe-app/      ← Vite app (osobny)
└── docs/                       ← hub integracyjny (README, zaleznosci.md)
```

### Foldery pomocnicze / tymczasowe (ignorować przy zmianach)

`_live_*`, `_remote_check*`, `_audit_live`, `_tmp_*` — kopie weryfikacyjne motywu live, nie źródło prawdy.

### Dokumentacja — gdzie szukać prawdy

| Typ | Lokalizacja |
|-----|-------------|
| Integracja 3 warstw | `docs/README.md`, `docs/zaleznosci.md` |
| Motyw | `docs/motyw/*.md` |
| Komponenty Python | `cursor-api/docs/komponenty/<moduł>.md` |
| Worker | `cursor-api/docs/worker/` |
| GicleeApp | `cursor-api/giclee_app/docs/` |
| Archiwum (czytaj, nie pisz) | `THEME_KNOWLEDGE.md`, `cursor-api/SHOP_KNOWLEDGE.md` |

---

## 3. Routing i strony

**Shopify obsługuje routing.** Brak własnego routera — URL → szablon JSON w `templates/`.

### Layouty

| Plik | Rola |
|------|--------|
| `layout/theme.liquid` | Główny layout: import map, mockup config (`#pm-config`), koszyk, splash, katalog artystów |
| `layout/password.liquid` | Strona hasła sklepu |

### Kluczowe szablony (templates/*.json)

| Szablon JSON | Typ strony | Zastosowanie |
|--------------|------------|--------------|
| `index.json` | Strona główna | Hero, karuzele, sekcje marketingowe |
| `product.json` | PDP domyślny | Produkty bez custom flow |
| `product.nowy-szblon-produktu.json` | PDP reprodukcji | Zoom HD, galeria, trust, scroll reveal |
| `product.szablon-produktu-v2.json` | PDP reprodukcji v2 | Jak wyżej + porównanie przed/po |
| `product.szablon-wlasna-fotografia.json` | PDP własna fotografia | Mockup w flow zakupu |
| `product.fotografia-obraz.json` | PDP fotografia | Wariant produktu custom print |
| `page.fotografia-obraz.json` | Strona `/pages/fotografia-obraz` | Pełnoekranowy edytor zdjęcia |
| `page.losuj-produkt.json` | Strona „Losuj Obraz" | Scena WebGL Three.js |
| `page.giclee-frame.json` | Strona informacyjna | Ramy Giclée |
| `page.filozofia-marki.json`, `page.faq.json`, `page.wspolpraca.json` | Strony CMS | Treści marketingowe |
| `collection.json`, `collection.produkty.json` | Kolekcje | Listing produktów |
| `cart.json` | Koszyk | Prośba o fakturę, podsumowanie |
| `search.json` | Wyszukiwarka | Predictive search Horizon |
| `blog.json`, `article.json` | Blog | Posty wielojęzyczne |

### Warunki routingu w Liquid

```liquid
{% if template.suffix == 'fotografia-obraz' or template.suffix == 'szablon-wlasna-fotografia' %}
```

Specjalny layout mockupu i scroll-lock — patrz `layout/theme.liquid`.

### Deploy motywu

- **Live:** `#197314249052` („Kopia Giclee Art Br") na `giclee-art-3.myshopify.com`
- **Dev:** `#199252410716` (z `shopify.theme.toml`)
- Komenda: `shopify theme push --store giclee-art-3.myshopify.com --theme 197314249052 --allow-live --only "ścieżka"`

---

## 4. Komponenty UI

### Motyw Shopify — organizacja

| Typ | Folder | Konwencja nazewnictwa |
|-----|--------|----------------------|
| **Sekcje** | `sections/` | Horizon: `hero.liquid`, `header.liquid`; Giclee: `giclee-*.liquid` |
| **Bloki** | `blocks/` | Prefiks `_` dla bloków wewnętrznych (`_header-menu.liquid`) |
| **Snippety** | `snippets/` | `giclee-*` = logika biznesowa GicleeArt |
| **Assety JS/CSS** | `assets/` | Para plików: `giclee-<feature>.js` + `.css` |

### Custom sekcje GicleeArt (motyw)

| Sekcja | Pliki powiązane |
|--------|-----------------|
| `giclee-artist-collection-showcase.liquid` | Galeria 3D kolekcji autora |
| `giclee-artist-biography.liquid` | Biografia autora + scroll stack |
| `giclee-random-artwork.liquid` | Losuj Obraz (WebGL) |
| `product-before-after-compare.liquid` | Suwak przed/po retuszu |

### Custom snippety GicleeArt (najważniejsze)

| Snippet | Rola |
|---------|------|
| `giclee-photo-mockup.liquid` | Mockup własnej fotografii + upload |
| `giclee-product-zoom.liquid` | Zoom HD (OpenSeadragon + R2) |
| `giclee-product-gallery.liquid` | Galeria mockupów na PDP |
| `giclee-passepartout-picker.liquid` | Wybór passe-partout |
| `giclee-pdp-variant-sync-script.liquid` | JSON wariantów dla JS |
| `giclee-i18n-*.liquid` | Tłumaczenia runtime (menu, bloki, JS) |
| `cart-invoice-request.liquid` | Prośba o fakturę w koszyku |

### Horizon Web Components (motyw bazowy)

Klasa `Component` (`assets/component.js`) — custom elements z `ref`, shadow DOM, declarative events. Import przez `@theme/component`.

### Komponenty Python (GicleeApp)

Każdy moduł = folder `cursor-api/Komponenty/<nazwa>/`:

```
Komponenty/<nazwa>/
├── __init__.py
├── __main__.py          ← entry point (subprocess)
├── component.json       ← metadata kafelka (opcjonalnie)
├── view.py              ← GUI inline (opcjonalnie)
├── gui.py               ← GUI subprocess (opcjonalnie)
├── dane/                ← JSON/SQLite lokalne
└── requirements.txt     ← zależności modułu (opcjonalnie)
```

**Tryby uruchomienia** (`component.json` → `mode`):

| Tryb | Opis | Przykłady |
|------|------|-----------|
| `subprocess` | Osobny proces Python | `dodajobraz`, `mockup`, `nazwijobraz` |
| `inline` | Widok w oknie launchera | `produkcja`, `finanse`, `analytics`, `blog` |
| `url` | Otwiera URL w przeglądarce | `sklep` → gicleeart.eu |

Discovery: `giclee_app/component_loader.py` — skanuje `Komponenty/*/`.

### Moduły animacji / scroll (`assets/giclee-*`) — stan obecny

| Moduł | Rola |
|-------|------|
| `giclee-home-stack.js` / `.css` | Scroll-over warstw homepage (wariant 3) |
| `giclee-product-scroll-reveal.js` | Scroll reveal na PDP reprodukcji |
| `giclee-product-story.js` / `.css` | PDP v3 — hybrid sticky, pin, hold |
| `giclee-artist-biography.js` | Biografia autora — scroll stack, shift |
| `giclee-artist-collection-showcase.js` | Galeria 3D — coverflow, przejścia autora |
| `giclee-photo-mockup.js` | Mockup klienta — scroll coupling, pin |
| `giclee-hero-video-collage.js` | Hero homepage — kolaż wideo |
| `giclee-random-artwork-webgl.js` | Losuj obraz — Three.js + fallback CSS |

Dokumentacja scen scroll: [`docs/motyw/pdp-v3-pusty-scroll.md`](docs/motyw/pdp-v3-pusty-scroll.md), [`docs/motyw/strona-glowna.md`](docs/motyw/strona-glowna.md), [`docs/motyw/kolekcja-autora-showcase.md`](docs/motyw/kolekcja-autora-showcase.md).

---

## 5. Stylowanie

### System

- **Horizon theme CSS** — `assets/base.css`, zmienne CSS (`--font-*`, color schemes)
- **Override GicleeArt** — `assets/custom.css` (globalne poprawki layoutu, koszyk, menu, PDP mobile)
- **Feature CSS** — osobne pliki `assets/giclee-<feature>.css` ładowane selektywnie z Liquid

### Konwencje klas CSS

- Prefiks **`.giclee-*`** dla komponentów custom (BEM-like: `.giclee-gallery__thumb`, `.giclee-gallery__stage`)
- Color scheme Horizon: `scheme-1`, `scheme-2` — nie nadpisywać bez analizy hover/focus
- Breakpointy mockupu: `<1024px` (mobile/tablet), `1024–1400px` (laptop), `>1400px` (desktop)
- Breakpoint mobile motywu: **`749px`** (standard Horizon)

### Fonty

Google Fonts w `layout/theme.liquid`: Bodoni Moda, Cormorant Garamond.

### Cache busting

Przy deploy JS/CSS bump parametru `?v=…` lub `&giclee_v=…` w Liquid (import map też ma wersje).

### Czego nie używać (stylowanie — domyślnie)

- Tailwind, Bootstrap, styled-components, CSS Modules, Sass (brak w projekcie; nie dodawać dla pojedynczych efektów UI)

---

## Strategia rozwoju animacji i scroll storytellingu {#strategia-rozwoju-animacji-i-scroll-storytellingu}

Giclée Art może rozwijać się w stronę zaawansowanego, profesjonalnego scroll storytellingu (kinowe przejścia, narracja sekcji, editorial motion). **Obecny stack tego kierunku nie blokuje.** Na tym etapie projekt korzysta z własnych animacji vanilla JS/CSS; przy większych scenach narracyjnych dopuszczalne jest rozważenie **GSAP + ScrollTrigger** jako świadomej warstwy animacyjnej. Decyzja powinna wynikać ze **skali potrzeb**, a nie z pojedynczej mikroanimacji.

### 1. Mikroanimacje (domyślnie preferuj)

- CSS `transition` / `transform` / `opacity`
- `IntersectionObserver` (wejście w viewport)
- `requestAnimationFrame` + CSS custom properties (scroll progress, jak `giclee-home-stack`)
- Vanilla JS bez nowych bibliotek
- Zawsze: `prefers-reduced-motion: reduce` — wyłączenie lub uproszczenie efektu

**Przykłady w projekcie:** `draw-line` w `assets/base.css`, fade header homepage, `scaleX` separatorów stack, opacity/blur warstw.

### 2. Średnie animacje editorialne

- **Najpierw** sprawdź istniejące moduły `giclee-*` (tabela w §4) — rozszerz zamiast duplikować
- Rozważ wspólny lekki helper (scroll progress, smoothstep, reduced-motion gate) tylko gdy ≥3 miejsca powtarzają ten sam wzorzec
- Unikaj wielu równoległych mechanizmów scroll progress w jednym szablonie
- Ładuj assety **selektywnie** z Liquid (`{% if template %}` / sekcja), nie globalnie w `theme.liquid` bez uzasadnienia

### 3. Duży scroll storytelling (rozważ po audycie)

**GSAP + ScrollTrigger** może mieć sens, gdy:

- vanilla JS staje się zbyt złożony (timeline, wiele elementów zsynchronizowanych)
- potrzebny pinning z scrub, sekwencja scen narracyjnych, choreografia wielu warstw
- sekcja wymaga kinowego przejścia trudnego do utrzymania w rAF + CSS

**Warunki dopuszczenia:**

1. Audyt konkretnej sekcji/szablonu (performance mobile, długość strony, sticky już obecne)
2. Ładowanie **selektywnie** per template/sekcja — nie globalnie na cały sklep
3. `prefers-reduced-motion` — fallback statyczny lub uproszczony
4. Uzasadnienie kosztu: rozmiar bundla, wpływ na LCP/INP, test iOS Safari
5. Dokumentacja w `docs/motyw/<moduł>.md` — kiedy GSAP jest użyty i dlaczego

### 4. Technologie zmieniające architekturę (nie domyślna ścieżka)

| Technologia | Domyślnie | Kiedy rozważyć |
|-------------|-----------|----------------|
| **React / Next.js** | Nie na froncie motywu Shopify | Osobna aplikacja, iframe, osobna decyzja architektoniczna |
| **Framer Motion** | Nie w motywie Liquid | Tylko przy migracji do React — poza obecnym modelem |
| **Tailwind** | Nie | Konflikt z Horizon CSS + `custom.css`; nie dla pojedynczych efektów |
| **Lenis / Locomotive Scroll** | Nie | Smooth-scroll globalny koliduje ze sticky stackiem i natywnym scroll; tylko po analizie całej strony |

### Zasady ochrony projektu (animacje)

- **Domyślnie preferuj** vanilla — **dopuść po audycie** bibliotekę animacyjną przy większej skali
- **Nie instaluj** paczek npm w motywie dla jednego hovera, jednej linii dividera ani prostego fade-in
- **Nie duplikuj** kolejnego scroll engine obok `giclee-home-stack` / `giclee-product-story` bez uzasadnienia
- **Uzasadnij** koszt i wpływ na performance przed dodaniem GSAP lub zmianą architektury scrolla
- Szczegóły implementacji scen → docs modułowe; wzorzec PDP v3 → [`docs/motyw/pdp-v3-pusty-scroll.md`](docs/motyw/pdp-v3-pusty-scroll.md)

---

## 6. Dane i integracje

### Shopify — produkty i warianty

| Obszar | Gdzie |
|--------|-------|
| Tworzenie produktów | `cursor-api/Komponenty/dodajobraz/create.py` |
| Klient Admin API | `cursor-api/Komponenty/dodajobraz/shopify_client.py` (REST + GraphQL, API 2026-04) |
| OAuth / sesja | `cursor-api/oauth-server.mjs`, `.shopify_session.json` |
| Zoom manifest (metafield) | `custom.zoom_manifest` — publikacja: `zoom_publish.py` |
| Tłumaczenia produktów | Shopify Translations API (komponenty: `aktualizujopis`, skrypty w `cursor-api/scripts/`) |
| Szablony produktów | `wyborszablonu`, przypisanie w Admin API |
| Ceny rynkowe / Markets | `zmienceny`, `market_variant_prices.py`, kursy NBP via `_shared/fx_rates.py` |
| Sync wariantów PDP (front) | `assets/giclee-pdp-variant-sync.js` — reguła sosna→tylko czarny, ceny z JSON |

### Koszyk i checkout (motyw)

| Obszar | Gdzie |
|--------|-------|
| Dodawanie do koszyka (mockup) | `layout/theme.liquid` → `pmAddConfiguredToCart` |
| Cart API | `/cart/add.js`, `/cart/update.js` (Shopify Ajax API) |
| Property uploadu | `properties[_Upload ID]` w line item |
| Property passe-partout | `properties[Passepartout]` — `giclee-passepartout-picker` |
| Prośba o fakturę | `snippets/cart-invoice-request.liquid`, `assets/cart-invoice-request.js` → `cart.attributes` |
| BLIK (PL) | `snippets/blik-checkout-button.liquid` zamiast Shop Pay |
| Drawer koszyka | Horizon `cart-drawer` + poprawki w `custom.css` |

### Upload klienta (własna fotografia)

```
Motyw (JS) → POST Worker → R2 → cart property → Shopify webhook → Resend → email
```

| Krok | Plik |
|--------|------|
| Upload JS | `assets/giclee-photo-mockup.js` → `pmPrepareOrderUpload` |
| Worker | `cursor-api/mockup-order-worker/src/index.js` |
| R2 bucket | `giclee-zoom`, prefix `customer-uploads/` |
| Webhook | Shopify → Worker → mail z linkami R2 |

**Uwaga:** Mockup **klienta** (motyw + Worker) ≠ mockup **katalogowy** (`Komponenty/mockup/`).

### Faktury i księgowość

| Moduł | Rola |
|-------|------|
| `dokumentysprzedazy` | Faktury bez VAT, PDF, sync zamówień Shopify, wysyłka SMTP |
| `finanse` | Hub księgowości w launcherze |
| `kpir` | KPiR (JDG) |
| `dnr` | Działalność nierejestrowana |
| `nbp_service.py` | Kursy NBP historyczne dla faktur |
| `_shared/fx_rates.py` | Cache kursów bieżących (24h) |

Atrybuty faktury z koszyka: `_Invoice requested`, `_Invoice type`, `_Company name`, `_Tax ID` → odczyt w `order_attributes.py`.

### Analityka

| Warstwa | Plik / usługa |
|---------|---------------|
| Pixel Shopify | `Komponenty/analytics/pixel/giclee-analytics-pixel.js` |
| Collect (chmura) | Worker `POST /api/analytics/collect` → D1 |
| Dashboard lokalny | `python -m Komponenty.analytics.server` (port 5100) |
| Sync chmura→PC | `POST /api/analytics/pull-worker` |

Lejek: wejście → produkt → koszyk → checkout → zakup + lejek konfiguratora ram (`giclee_app:*`).

### Zoom HD (reprodukcje)

| Warstwa | Plik |
|---------|------|
| Publikacja kafelków | `Komponenty/dodajobraz/zoom_publish.py` → R2 |
| Metafield | `custom.zoom_manifest` |
| Front | `snippets/giclee-product-zoom.liquid`, `assets/giclee-product-zoom.js` |
| CDN viewer | OpenSeadragon (jsDelivr) |

### Inne integracje

| Integracja | Moduł |
|------------|-------|
| Gmail IMAP | `Komponenty/poczta/imap_client.py` |
| Meta Graph | `Komponenty/socialmedia/cykl/` |
| SerpAPI (Google Lens) | `Komponenty/nazwijobraz/` |
| IIIF muzeów | `Komponenty/pobierzobraz/`, `stronyzobrazami/` |
| Gemini AI | `tytulyai`, `print_optimize`, `zadania` |
| Cloudflare limity | `Komponenty/limity/collectors.py` |

---

## 7. Typy, schemas i walidacja

### JavaScript (motyw)

- **Brak TypeScript** — projekt używa vanilla JS
- **JSDoc** w plikach Horizon (`assets/component.js`, `assets/utilities.js`)
- **`@ts-nocheck`** w wybranych plikach Giclee (`giclee-pdp-variant-sync.js`)
- **Import map** zamiast bundlera — moduły ładowane natywnie przez przeglądarkę
- **Dane produktu na PDP** — JSON inline w DOM: `[data-giclee-pdp-product-data]`, `window.__GICLEE_PDP_PRODUCT__`
- **i18n runtime** — `window.__gicleeI18n` z `snippets/giclee-i18n-js.liquid`

### Python (cursor-api)

- **Type hints** — `from __future__ import annotations`, typowanie w nowym kodzie
- **Dataclasses** — m.in. `component_loader.Component`, modele KPiR
- **JSON schemas** — dane w `Komponenty/*/dane/*.json` (faktury, kolekcje, prompty, sync state)
- **SQLite** — analityka (`analytics.db`), niektóre moduły finansowe
- **Walidacja faktur** — `invoice_service.py`, reguły DNR/JDG w ustawieniach JSON
- **Testy** — `cursor-api/tests/test_*.py` (pytest-style, ~46 plików)

### Liquid / Shopify

- **Metafields** — `custom.zoom_manifest`, `custom.before_retouch_url`, inne w SHOP_KNOWLEDGE (archiwum)
- **Locales** — `locales/*.json`, master tłumaczeń: `locales/_giclee_i18n_all.json`
- **Settings schema** — `config/settings_schema.json` (Horizon + custom: `pm_upload_api_url`, `show_cart_invoice_request`)

---

## 8. Ważne pliki

### Konfiguracja i start

| Plik | Rola |
|------|------|
| `MATKA.md` | Skrót startowy: trasy, ID, deploy, zasady AI |
| `docs/README.md` | Hub integracyjny, identyfikatory, scenariusze |
| `docs/zaleznosci.md` | Mapa przepływów między warstwami |
| `USLUGI.md` | Konta zewnętrzne, plany, limity |
| `shopify.theme.toml` | Shopify CLI — store, theme dev |
| `cursor-api/.env` | Sekrety API (**nie commitować**) |
| `cursor-api/shopify.app.toml` | Konfiguracja Shopify App (OAuth) |
| `cursor-api/mockup-order-worker/wrangler.toml` | Worker: R2, D1, CORS, Resend |

### Motyw — pliki krytyczne (nie ruszać bez analizy)

| Plik | Rola |
|------|------|
| `layout/theme.liquid` | Layout globalny, mockup config, koszyk, splash, katalog |
| `snippets/scripts.liquid` | Import map `@theme/*`, preloads |
| `snippets/giclee-photo-mockup.liquid` | Mockup klienta |
| `assets/giclee-photo-mockup.js` | Logika mockupu, upload, scroll→koszyk |
| `assets/giclee-pdp-variant-sync.js` | Sync cen/dostępności wariantów PDP |
| `assets/custom.css` | Globalne override CSS |
| `config/settings_schema.json` | Ustawienia motywu (+ custom Giclee) |
| `snippets/cart-invoice-request.liquid` | Faktura w koszyku |

### cursor-api — pliki krytyczne

| Plik | Rola |
|------|------|
| `Komponenty/dodajobraz/shopify_client.py` | Klient Shopify Admin API |
| `Komponenty/dodajobraz/create.py` | Pipeline tworzenia produktu |
| `Komponenty/dokumentysprzedazy/invoice_service.py` | Wystawianie faktur |
| `Komponenty/dokumentysprzedazy/nbp_service.py` | Kursy NBP |
| `Komponenty/_shared/fx_rates.py` | Cache kursów NBP |
| `Komponenty/_shared/auth.py` | Hasło startowe aplikacji |
| `mockup-order-worker/src/index.js` | Worker upload + webhook + analityka |
| `giclee_app/launcher.py` | GUI launchera |
| `giclee_app/component_loader.py` | Discovery komponentów |

### Dokumentacja modułowa (aktualizować po zmianach)

| Obszar | Plik |
|--------|------|
| Mockup klienta | `docs/motyw/mockup-wlasna-fotografia.md` |
| Worker | `cursor-api/docs/worker/mockup-order-worker.md` |
| Dodaj obraz | `cursor-api/docs/komponenty/dodajobraz.md` |
| Faktury | `cursor-api/docs/komponenty/dokumentysprzedazy.md` |
| Finanse | `cursor-api/docs/komponenty/finanse.md` |
| Analityka | `cursor-api/docs/komponenty/analytics.md` |

---

## 9. Konwencje kodu

### Nazewnictwo

| Obszar | Konwencja |
|--------|-----------|
| Assety motywu Giclee | Prefiks `giclee-` (`giclee-photo-mockup.js`) |
| Snippety Liquid Giclee | Prefiks `giclee-` |
| Sekcje custom | Prefiks `giclee-` |
| Komponenty Python | Folder lowercase bez spacji (`dodajobraz`, `dokumentysprzedazy`) |
| Moduły współdzielone | `Komponenty/_shared/` |
| Import map motywu | `@theme/<nazwa-modułu>` |

### Organizacja plików

- **Para JS+CSS** per feature Giclee w `assets/`
- **Liquid markup** w `snippets/` lub `sections/`, logika w `assets/*.js`
- **Jeden fakt = jeden plik docs** — nie duplikować między `MATKA.md` a plikami modułowymi
- **Dane komponentu** w `Komponenty/<moduł>/dane/` (JSON, SQLite, sync state)

### Importy JS (motyw)

```javascript
import { Component } from '@theme/component';
import { debounce } from '@theme/utilities';
```

Nowe moduły Horizon-style: dodać wpis w `snippets/scripts.liquid` (import map).

### Importy Python

```python
from Komponenty._shared.activity_log import log_activity
from Komponenty.dodajobraz.shopify_client import ShopifyError
```

Uruchamianie komponentu: `python -m Komponenty.<nazwa>` z katalogu `cursor-api/`.

### Typowanie

- Python: type hints w nowym kodzie, `ShopifyError` jako wyjątek domenowy
- JS: JSDoc `@typedef`, `@type` — bez kompilacji TS

### Obsługa błędów

- **Shopify API:** retry z backoff (`shopify_client.py`), `ShopifyError`, rate limit 0.55s
- **Worker:** CORS whitelist, walidacja rozmiaru pliku, JSON responses
- **Motyw:** `console.warn` w catch, graceful fallback (np. brak zoom → statyczny obraz)
- **GicleeApp:** toast, dziennik akcji (`activity_log.jsonl`)

### Tworzenie nowych funkcji

1. **Ustal warstwę** — motyw / cursor-api / Worker (nie mieszaj bez potrzeby)
2. **Sprawdź istniejący komponent** — discovery w `Komponenty/` lub snippety `giclee-*`
3. **Minimalny diff** — rozszerz istniejący plik zamiast duplikować
4. **Dokumentacja** — po ważnej zmianie zaktualizuj plik modułowy w `docs/`
5. **Deploy selektywny** — `--only "konkretne/pliki"` przy `shopify theme push`
6. **Cache bust** — bump `?v=` po zmianie JS/CSS

### Praca z UI (motyw)

- Respektuj breakpointy Horizon (`749px`) i Giclee mockup (`1024px`, `1400px`)
- Tłumaczenia: klucze `giclee.*` w `locales/`, runtime przez `giclee-i18n-*.liquid`
- Testuj drawer koszyka i scroll-lock na mobile (iOS fetch + `position: fixed`)
- Color schemes Horizon — testuj hover w ciemnym drawerze (`custom.css` ma znane fixy)

### Praca z UI (GicleeApp)

- Tkinter, inline views przez `tile_grid.py`
- `component.json`: `inline_width`, `inline_height` dla rozmiaru okna
- Wersja app: podbij `giclee_app/__init__.py` + `cursor-api/package.json` przy widocznych zmianach

---

## 10. Zasady bezpieczeństwa dla przyszłych zmian

### Ogólne

- **Nie przepisywać całej aplikacji** bez wyraźnej prośby — minimalny, ukierunkowany diff
- **Nie usuwać istniejących funkcji** bez potwierdzenia — sklep produkcyjny (gicleeart.eu)
- **Nie zmieniać routingu / szablonów** bez powodu — URL Shopify są powiązane z marketingiem i SEO
- **Nie dodawać bibliotek** (npm/pip) bez uzasadnienia — domyślnie vanilla JS; wyjątki wg [§ Strategia animacji](#strategia-rozwoju-animacji-i-scroll-storytellingu) (GSAP po audycie dużej sceny, nie dla mikroefektów)
- **Nie duplikować komponentów** — szukaj istniejącego modułu przed tworzeniem nowego
- **Zachować konwencje** — prefiks `giclee-`, struktura `Komponenty/`, import map `@theme/*`
- **Zmiany etapowo** — deploy selektywny (`--only`), test na theme dev przed live

### Strefy wysokiego ryzyka (wymagają wcześniejszej analizy docs)

| Strefa | Dlaczego |
|--------|----------|
| **Shopify Admin API** (`shopify_client.py`) | Rate limits, OAuth, produkty live |
| **Koszyk / checkout** (`theme.liquid`, cart snippets) | Przepływ zakupu, properties zamówienia |
| **Upload Worker** (`mockup-order-worker/`) | R2, webhook, maile Resend — dane klientów |
| **Faktury / KPiR / DNR** | Dokumenty prawne, numeracja, NBP, numeracja bez duplikatów |
| **Finanse — tryb DNR/JDG** | Synchronizacja między `invoice_settings.json` a `kpir_settings.json` |
| **Analityka** | Pixel + D1 + sync — spójność eventów |
| **Tłumaczenia** (`locales/`, Translations API) | 7 rynków, limit 1000 znaków/klucz |
| **Mockup klienta vs katalogowy** | To dwa różne systemy — nie mylić ścieżek |
| **Sekrety** (`.env`, `.shopify_session.json`, wrangler secrets) | Nigdy nie commitować do repo |

### Dokumentacja po zmianie

Po ważnej zmianie **automatycznie aktualizuj** plik modułowy w `docs/` — bez pytania usera (chyba że prosi „bez docs"). Nie aktualizuj archiwum (`SHOP_KNOWLEDGE.md`, `THEME_KNOWLEDGE.md`).

### Deploy

```powershell
# Motyw (live) — tylko zmienione pliki
shopify theme push --store giclee-art-3.myshopify.com --theme 197314249052 --allow-live --only "ścieżka"

# Worker
cd cursor-api\mockup-order-worker && npx wrangler deploy

# GicleeApp
cd cursor-api && pythonw -m giclee_app
```

---

## 11. Rekomendacje dla Custom GPT

### Jak tworzyć prompty do Cursor

1. **Zacznij od warstwy** — doprecyzuj: motyw / cursor-api / Worker / GicleeApp
2. **Wklej kontekst** — `MATKA.md` + odpowiedni plik z `docs/motyw/` lub `cursor-api/docs/komponenty/`
3. **Podaj ścieżki plików** — konkretne pliki do edycji, nie „cały projekt"
4. **Ogranicz scope** — `--only` przy deploy, lista plików do zmiany
5. **Zabraniaj** — refactor całości, nowe biblioteki bez audytu (patrz § Strategia animacji), zmiany checkout/faktur bez analizy docs
6. **Wymagaj docs** — „po zmianie zaktualizuj `<moduł>.md`"
7. **Przypomnij o cache bust** — bump `?v=` / `giclee_v` po JS/CSS

### Szablon promptu (przykład)

```
Warstwa: motyw (pusty/)
Cel: [konkretna zmiana]
Pliki: [lista ścieżek]
Docs do przeczytania: docs/motyw/[moduł].md
Ograniczenia:
- minimalny diff; nowe zależności tylko po audycie (TECH_STACK § Strategia animacji)
- nie ruszać checkout/faktur/upload
- zachować prefiks giclee-
- po zmianie: zaktualizuj docs + bump cache ?v=
Deploy: shopify theme push --only "[pliki]"
```

### Checklist przed merge

- [ ] Właściwa warstwa (motyw ≠ API ≠ Worker)
- [ ] Istniejący plik rozszerzony zamiast duplikatu
- [ ] Brak sekretów w diff
- [ ] Dokumentacja modułowa zaktualizowana
- [ ] Cache bust dla JS/CSS
- [ ] Test na theme dev (#199252410716) przed live

### Identyfikatory (szybka referencja)

| Element | Wartość |
|---------|---------|
| Domena | `gicleeart.eu` |
| Shopify store | `giclee-art-3.myshopify.com` |
| Motyw live | `#197314249052` |
| Worker | `giclee-mockup-orders.eagleblastmusic.workers.dev` |
| R2 bucket | `giclee-zoom` |
| Cart property upload | `_Upload ID` |
| Zoom metafield | `custom.zoom_manifest` |

Pełna lista: `docs/README.md` § Identyfikatory.

---

## Powiązane dokumenty

| Dokument | Rola |
|----------|------|
| [`MATKA.md`](MATKA.md) | Skrót startowy |
| [`docs/README.md`](docs/README.md) | Hub integracyjny |
| [`docs/zaleznosci.md`](docs/zaleznosci.md) | Przepływy cross-warstwowe |
| [`docs/motyw/README.md`](docs/motyw/README.md) | Indeks docs motywu |
| [`cursor-api/docs/README.md`](cursor-api/docs/README.md) | Indeks docs API |
| [`cursor-api/docs/komponenty/README.md`](cursor-api/docs/komponenty/README.md) | Indeks komponentów Python |
| [`USLUGI.md`](USLUGI.md) | Konta zewnętrzne |
