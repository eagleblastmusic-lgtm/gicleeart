# THEME_KNOWLEDGE.md - Brief o motywie sklepu (ARCHIWUM — tylko czytanie)

> **⚠️ Nie aktualizuj tego pliku.** Nowe fakty → [`docs/motyw/`](docs/motyw/) (prawda) · hub: [`docs/README.md`](docs/README.md)  
> **START:** [`MATKA.md`](MATKA.md) · [`docs/zaleznosci.md`](docs/zaleznosci.md)

> **Cel historyczny:** struktura motywu Horizon + customizacje sprzed refaktoryzacji docs modułowych.  
> Czytaj **sekcję po sekcji** tylko gdy brakuje w `docs/motyw/`. Backend: archiwum [`cursor-api/SHOP_KNOWLEDGE.md`](cursor-api/SHOP_KNOWLEDGE.md).

---

## 1. CO TO JEST

- **Sklep:** GicleeArt - sprzedaz reprodukcji obrazow klasykow malarstwa, technika giclee
  na plotnie. Wieloryynkowy: PL (baza), EN/EU, FR, DE, ES, NL, IT.
- **Domena:** `gicleeart.eu`
- **Platforma:** Shopify (Online Store 2.0 / **Shopify Horizon**-style theme).
- **Folder motywu:** ten folder (`h:/Projekty CURSOR/Nowe/pusty/`).
- **Pochodzenie motywu:** wyglada na bazowy Horizon (Shopify) z mocna customizacja
  (custom hero, slideshow, gallery dropdown w naglowku, splash screen, page transitions).
- **Wszystkie pliki `.upstream-*`** w roocie folderu = oryginalne wersje z motywu Horizon
  trzymane na potrzeby porownania/merge'u przy aktualizacji upstream'a.

---

## 2. STRUKTURA FOLDERU

```
pusty/                                     # KORZEN MOTYWU
  layout/
    theme.liquid                           # GLOWNY layout - 1786 linii, MOCNO customowany
                                            #   - Bodoni + Cormorant Garamond (Google Fonts)
                                            #   - splash screen na homepage
                                            #   - page-transition curtain dla przejsc
                                            #   - mega-menu styling
                                            #   - gallery dropdown panel (#giclee-catalog-panel)
                                            #   - dedykowany scroll dla template'u 'fotografia-obraz'
    password.liquid                        # layout dla Coming Soon / password page
  templates/                               # template JSON (Online Store 2.0)
    index.json, product.json, collection.json, search.json,
    cart.json, blog.json, page.json, ...
    +alternatywne suffixy (np. product.fotografia-obraz.json)
  sections/                                # sekcje wstawiane do template'ow (40+ plikow)
    header.liquid (49KB), hero.liquid (45KB), slideshow.liquid (16KB),
    main-product.liquid, main-collection.liquid, footer.liquid,
    layered-slideshow.liquid, product-list.liquid (27KB),
    collection-list.liquid (27KB), quick-order-list.liquid (37KB),
    media-with-content.liquid, marquee.liquid, ...
    *-group.json (header-group.json, footer-group.json) - kontenery sekcji
    _blocks.liquid - centralny renderer blokow
  blocks/                                  # bloki uzywane wewnatrz sekcji (~80 plikow)
    image, text, button, heading, group, spacer, video, accordion, swatches,
    add-to-cart, buy-buttons, variant-picker, product-title, product-description,
    product-card, collection-card, filters, menu, popup-link, social-links,
    payment-icons, ...
    pliki '_*.liquid' = wewnetrzne bloki helperowe (np. _card, _slide, _heading)
  snippets/                                # czesci wielokrotnego uzytku (~150 plikow)
    icon.liquid (133KB - kompletna biblioteka SVG ikon),
    header-actions.liquid (20KB), header-drawer.liquid (57KB),
    cart-products.liquid (29KB), cart-summary.liquid (18KB),
    product-card.liquid, product-grid.liquid, product-media-gallery-content.liquid,
    list-filter.liquid (30KB), price.liquid, format-price.liquid,
    predictive-search-styles.liquid (17KB), localization-form.liquid (17KB),
    meta-tags.liquid, fonts.liquid, color-schemes.liquid, theme-styles-variables.liquid,
    ...
  assets/                                  # CSS/JS/obrazki
  config/
    settings_schema.json                   # 54KB - schema customizera Shopify Admin
    settings_data.json                     # 32KB - WARTOSCI ustawien (zarzadzane przez admin,
                                            # AUTO-GENEROWANE - ostroznie z manualnymi edycjami!)
  locales/                                 # 30+ jezykow + .schema.json dla 25+
    en.default.json                        # JEZYK BAZOWY MOTYWU
    pl.json, pl.schema.json                # polski
    de.json, de.schema.json                # niemiecki
    fr.json, fr.schema.json                # francuski
    es.json, es.schema.json                # hiszpanski
    nl.json, nl.schema.json                # holenderski
    it.json, it.schema.json                # wloski
    + ar, ja, ko, zh-CN, zh-TW, da, sv, no, fi, cs, sk, hu, pt, pt-BR,
      ru, hr, ro, bg, lt, lv, sl, hi, vi, th, tr, fa, en-PT, ...
```

---

## 3. JEZYKI MOTYWU vs JEZYKI PRODUKTOW

**WAZNE:** to sa **dwie OSOBNE warstwy** w Shopify:

1. **Tlumaczenia motywu** (UI strony - przyciski "Dodaj do koszyka", "Filtruj", footer,
   menu, komunikaty) -> pliki w `locales/`. Edytowane recznie ALBO przez Shopify Admin.
2. **Tlumaczenia produktow** (tytul, opis, tagi, SEO, kolekcje) -> przez **Translations API**
   (`translationsRegister` GraphQL mutation). Tym zajmuje sie aplikacja w `cursor-api/`.

Aplikacja Pythona NIE rusza plikow z `locales/`. Ona ustawia tlumaczenia na poziomie
zasobow (Product, Collection, Metafield) - te pojawiaja sie na stronie, gdy uzytkownik
przelaczy market/jezyk.

### Jezyki produktow do obslugi (w aplikacji)

PL (baza), EN, DE, FR, ES, NL, IT (patrz `SHOP_KNOWLEDGE.md` -> "Rynki i cennik").

---

## 4. RYNKI I URL-E

| Rynek         | URL                       | Jezyk (motyw)   | Locale code |
|---------------|---------------------------|-----------------|-------------|
| Polska (baza) | `gicleeart.eu/pl-pl`      | polski          | `pl`        |
| Hiszpania     | `gicleeart.eu/es-es`      | hiszpanski      | `es`        |
| Wlochy        | `gicleeart.eu/it-it`      | wloski          | `it`        |
| Europa (UE)   | `gicleeart.eu/en-eu`      | angielski       | `en`        |
| Francja       | `gicleeart.eu/fr-fr`      | francuski       | `fr`        |
| Niemcy        | `gicleeart.eu/de-de`      | niemiecki       | `de`        |
| Holandia      | `gicleeart.eu/nl-nl`      | holenderski     | `nl`        |

Markety zarzadzane w Shopify Admin (Settings -> Markets). Kazdy ma swoj **Catalog** (cennik
z markupem %) - tworzone recznie przez wlasciciela. Aplikacja Pythona ZNA markupy
(`markets_config.json`), ale nie tworzy katalogow - tylko liczy ceny do podpowiedzi w GUI
i ewentualnie pushuje aktualizacje do istniejacych katalogow.

---

## 5. KLUCZOWE CUSTOMIZACJE W `theme.liquid`

(Numery linii moga sie zmienic - sprawdz aktualne. Skrocone identyfikatory w komentarzach.)

1. **Czcionki:** Bodoni Moda + Cormorant Garamond (preconnect + link Google Fonts).
2. **Mega-menu styling:** override standardowych klas Horizon (`mega-menu__flyout-item--has-children.is-active > a`).
3. **Gallery catalog panel** (`#giclee-catalog-panel`) - rozwijany panel z katalogiem dziel
   po najechaniu na "Katalog" w naglowku. Klik w "Katalog" nie nawiguje (`#` w
   `giclee-resolve-menu-url.liquid` + `preventDefault` w `initGalleryCatalog`).
   Otwarcie/zamykanie (oryginalny mechanizm): `clip-path` panelu 0.85s / 0.5s + lista autorow
   (`listCol` clip-path w JS) + `catalogColIn` na podgladzie. Nawigacja z otwartego
   katalogu: `freezePanelForNavigation` + `is-nav-lifting` — uniesienie inline
   (`translateY` = `bottom + 168px`, `--pt-close-duration`, easing `0.25,0.46,0.45,0.94`),
   `z-index` nad kotara.
4. **Splash screen** (`#splash-screen`) - logo z animacja przy wejsciu na home (homepage tylko).
   **Powiadomienie testowe** (`snippets/giclee-site-notice.liquid` + `assets/giclee-site-notice.js`):
   tylko `index`, przy kazdym wejsciu (bez zapamietywania; czyści legacy `localStorage`);
   po `giclee:splash-done` + fallback 4,5 s; `pageshow` (bfcache) otwiera ponownie.
   **Sekcja „Giclée Art”** (`section_ThWw4Q`): animacja CSS `giclee-home-intro-in` w
   `custom.css`, klasa `html.giclee-home-intro-run` (nie zdejmowana po splash); bez
   `transitionend` na `finishReveal` (tylko `setTimeout` 1300 ms).
5. **Page transition curtain** (`#page-transition`) - kotara CSS przy nawigacji miedzy stronami
   (1.25s opening, 0.72s closing, custom event `giclee:navigation-start`). Przy nawigacji
   kotara: `sessionStorage giclee-curtain-nav` + klasa `html.curtain-pending` (skrypt w
   `<head>`) ukrywa tresc tylko do startu animacji otwarcia; przy `opening` tresc jest
   widoczna pod rozsuwajacymi panelami. Usuwa tez `view-transition-render-blocker`.
6. **Specjalna obsluga template'u `product.fotografia-obraz`** (linia ~1763) - dodatkowe CTA
   "Powrot" + invite "Zapraszam do Laboratorium".
7. **`overflow-x: hidden`** wymuszone na `body` (zapobiega horizontal scrollowi po custom hero).

> **Uwaga dla AI:** `theme.liquid` to JEDNO Z DWOCH MIEJSC, ktore mozna recznie edytowac
> bezpiecznie (drugim sa pliki w `sections/`, `blocks/`, `snippets/`). Pliki w `config/`
> sa pol-auto - zmiana w nich moze byc nadpisana przez Theme Editor w Shopify Admin.

---

## 6. CONFIG SCHEMA (`config/settings_schema.json`)

- Definiuje wszystkie ustawienia widoczne w Shopify Admin -> Customize.
- Color schemes (`scheme-1`, ..., `scheme-6` i nazwane) - zdefiniowane w `settings_data.json`.
- **Aktualnie aktywne kolory** (skrot z `settings_data.json`):
  - tlo czarne / akcent bialy w wielu schematach,
  - typografia: Inter (body), Inter (heading), Inter (subheading) + custom Bodoni i Cormorant
    z `theme.liquid`,
  - h1: 56px, h2: 48px, h3: 32px, h4: 24px, h5: 14px (display-tight/normal line-heights).

---

## 7. GLOBALNE SNIPPETS DO ZNAJOMOSCI

| Snippet                              | Co robi                                              |
|--------------------------------------|------------------------------------------------------|
| `meta-tags.liquid`                   | <head> meta + Open Graph + Twitter Card              |
| `fonts.liquid`                       | font-face / Google Fonts dla typografii motywu       |
| `color-schemes.liquid`               | renderuje CSS custom properties dla schematow        |
| `theme-styles-variables.liquid`      | CSS vars (rozmiary tekstu, paddingi, breakpointy)    |
| `header-actions.liquid` (20KB)       | menu konta, koszyk, search, langauge picker          |
| `header-drawer.liquid` (57KB)        | mobilny drawer menu (mega-menu, multi-level)         |
| `cart-products.liquid` (29KB)        | renderowanie produktow w koszyku z wariantami        |
| `product-card.liquid`                | karta produktu uzywana w kolekcjach i recommendations|
| `product-media-gallery-content.liquid` (37KB) | galeria zdjec na karcie produktu          |
| `localization-form.liquid` (17KB)    | przelacznik kraju/jezyka                             |
| `predictive-search-*` (3 pliki)      | wyszukiwanie real-time                               |
| `list-filter.liquid` (30KB)          | filtry kolekcji (po cenie, kolorze, swatch)          |
| `icon.liquid` (133KB)                | biblioteka SVG ikon - jeden plik, includowany wszedzie |

---

## 8. SEKCJE WARTE UWAGI

| Sekcja                                | Co robi                                              |
|---------------------------------------|------------------------------------------------------|
| `header.liquid` (48KB)                | naglowek z mega-menu, gallery panel, search, login   |
| `hero.liquid` (45KB)                  | duzy hero na homepage (custom design)                |
| `slideshow.liquid` (16KB)             | slideshow z arrows + controls; na mobile home JS podmienia slajd na `MALE_ORG.webp` (`object-fit: contain`), pole slajdów 1:1 (`custom.css` `.giclee-home-slideshow`) |
| `layered-slideshow.liquid` (15KB)     | warstwowy slideshow (parallax-style)                 |
| `main-product.liquid` (jest implicit przez templates/product.json) | strona produktu |
| `main-collection.liquid` (6KB)        | strona kolekcji + filtry                             |
| `featured-product.liquid`             | wyrozniony produkt na home                           |
| `media-with-content.liquid` (12KB)    | sekcja "obraz po lewej, tekst po prawej"             |
| `product-recommendations.liquid` (15KB)| "Mozesz lubic tez..." na karcie produktu            |
| `quick-order-list.liquid` (37KB)      | szybki order form (B2B-friendly?)                    |

---

## 9. JAK ROZSZERZAC MOTYW (best practices)

1. **NIGDY nie edytuj `.upstream-*` plikow** - to porownania.
2. **NIGDY nie edytuj `config/settings_data.json` recznie** (chyba ze MUSISZ - po edycji Theme
   Editor w Shopify nadpisze cala sekcje).
3. **Dodajac nowy snippet:** plik w `snippets/<nazwa>.liquid`, uzycie `{% render 'nazwa' %}`.
4. **Dodajac nowa sekcje:** plik w `sections/<nazwa>.liquid` ze schematem `{% schema %}` na koncu.
5. **Dodajac nowy blok:** plik w `blocks/<nazwa>.liquid` ze schematem na koncu (pole `{% schema %}`).
6. **Tlumaczenia stringow UI:** `{{ 'klucz.podklucz' | t }}` -> dodaj klucz do `en.default.json`,
   potem do `pl.json`, `de.json`, `fr.json`, `es.json`, `nl.json`, `it.json`.
   Dla schematow: `<lang>.schema.json` (osobny plik!).
7. **Custom JS:** wrzucaj do `assets/<nazwa>.js`, dolaczaj `<script src="{{ 'nazwa.js' | asset_url }}" defer></script>`
   (uwaga: niektore CSP / Shopify performance budgets - jest w Theme Inspector).
8. **Custom CSS:** `assets/<nazwa>.css` + `<link rel="stylesheet" href="{{ 'nazwa.css' | asset_url }}">`
   ALBO inline style w sekcji.

---

## 10. PUNKTY UWAGI / GOTCHAS

1. **Performance:** `icon.liquid` ma 133KB - sa to wszystkie ikony jako `<svg>` w jednym pliku.
   Includowany `{% render 'icon' %}` z parametrem name. Nie traktuj tego jako bug - tak
   robi Horizon (lekki render w Liquid, jedno HTTP).
2. **`header.liquid` (49KB) i `header-drawer.liquid` (57KB)** sa bardzo duze - jakakolwiek
   ich modyfikacja moze niechcacy popsuc cos w mobilnym widoku. Testuj na mobile.
3. **Splash screen w `theme.liquid`** ukrywany po 2200ms tylko na homepage (`request.page_type == 'index'`).
   Nie pokazuje sie na innych stronach - to celowe. Anti-FOUC: krytyczne style `#splash-screen`
   + ukrycie `#header-group` / `#MainContent` w `<head>` (klasa `splash-pending`); po `giclee:splash-done`
   `scroll-reveal` nie chowa elementow juz widocznych w viewport (natychmiast `is-visible`).
4. **Page transition** dziala tylko wewnatrz tego samego hostname'u. Linki externalne wlaczaja
   normalnie (bez kotary).
5. **Customizacja per template `fotografia-obraz`** - jezeli dodajesz nowy specjalny template,
   pamiętaj o moze potrzebnym dodatkowym JS hook'u w `theme.liquid`.
6. **Brak custom-search-app:** wyszukiwarka uzywa `predictive-search.liquid` (Shopify built-in,
   real-time). NIE ma obecnie zewnetrznego app'u typu Boost AI / Searchanise.
7. **Markup z markupow rynkow:** ceny pokazywane na froncie SAa juz po przeliczeniu przez
   Shopify (na bazie aktywnego market'u + jego catalog'u). Aplikacja Pythona musi przesylac
   tylko **cene PL** do produktu - reszta sie wylicza po stronie Shopify.

---

## 11. TODO - co planujemy zmieniac

- **Wersje jezykowe motywu:** sprawdzic, czy WSZYSTKIE custom stringi w
  `theme.liquid` (custom invite "Zapraszam do Laboratorium", "Powrot") sa juz w
  `pl.json` jako klucze tlumaczen, czy hardcoded. Jesli hardcoded - przerzucic na
  `{{ 'custom.label' | t }}` i dodac do 7 jezykow.
- **Smart-collections widoczne w mega-menu:** gdy aplikacja zaczyna tworzyc duzo
  smart-kolekcji (style/pomieszczenie/prezent/gatunek), trzeba je dodac do
  `header.liquid` mega-menu (ALBO recznie w Shopify Admin -> Navigation, ALBO
  zautomatyzowac przez API).
- **Kolekcje artystow** (collection o tytule `Nazwisko, Imie`) - mega-menu "Galeria"
  powinno je listowac alfabetycznie.
- **Color picker na karcie produktu** - swatches blok (`blocks/swatches.liquid`)
  jest gotowy, sprawdzic czy uzywa metafield'u `custom.kategoria` lub inny do
  filtrowania.
- **Tlumaczenia metafield'ow** (`custom.kategoria` = "Obrazy") - moze tez wymagac
  pushu przez `translationsRegister`. Plan: zostawic po polsku jako wewnetrzny
  identifier i nie tlumaczyc.

---

## 12. ZASOBY ZEWNETRZNE / DOKUMENTACJA

- **Shopify Theme Architecture:** https://shopify.dev/docs/storefronts/themes/architecture
- **Liquid reference:** https://shopify.dev/docs/api/liquid
- **Translations API:** https://shopify.dev/docs/api/admin-graphql/latest/mutations/translationsregister
- **Markets API:** https://shopify.dev/docs/api/admin-graphql/latest/mutations/marketcreate
- **Horizon theme upstream:** patrz pliki `.upstream-*` w roocie folderu.

---

## 13. KIEDY ZAGLADAC DO ICH PLIKOW

| Co chcesz zmienic                           | Plik                                          |
|---------------------------------------------|-----------------------------------------------|
| Logo, favicon, kolory, fonty                | Shopify Admin -> Customize (zapisuje do `config/settings_data.json`) |
| Tekst w naglowku/footer (statyczne)         | `locales/<lang>.json`                         |
| Mega-menu (linki + uklad)                   | `sections/header.liquid` lub Shopify Admin -> Navigation |
| Strona produktu                             | `templates/product.json` + `sections/main-product.liquid` |
| Strona kolekcji + filtry                    | `templates/collection.json` + `snippets/list-filter.liquid` |
| Kolekcja autora: bio + galeria + sync autorów | `sections/giclee-artist-biography.liquid`, `sections/giclee-artist-collection-showcase.liquid`, `assets/giclee-active-author.js` — docs: `docs/motyw/kolekcja-autora-showcase.md` |
| Splash screen / animacje wejscia            | `layout/theme.liquid` (~linie 1742-1762)      |
| Hero homepage                               | `sections/hero.liquid`                        |
| Galeria zdjec na karcie produktu            | `snippets/product-media-gallery-content.liquid`|
| Format ceny / waluta                        | `snippets/format-price.liquid`, `snippets/price.liquid` |
| Cart drawer                                 | `snippets/cart-products.liquid`, `snippets/cart-summary.liquid` |
| Wyszukiwarka real-time                      | `sections/predictive-search.liquid` + snippets |
| Szablon posta na blogu (artykulu)           | `templates/article.json` + `sections/main-article.liquid` |
| Lista artykulow (strona blogu)              | `templates/blog.json` + `sections/main-blog.liquid` |

---

## 14. BLOG - PUBLIKACJA Z APLIKACJI `cursor-api/Komponenty/blog`

Od wersji `cursor-api-6` istnieje komponent Python do publikacji postow na blog sklepu.
Szczegoly techniczne: patrz `cursor-api/SHOP_KNOWLEDGE.md` sekcja 9a.

**Z perspektywy motywu Shopify ("Horizon"):**
- Artykuly trafiaja do **blog "News"** (handle `news`). URL storefront:
  `https://gicleeart.eu/blogs/news/<article-handle>`.
- Tlumaczenia artykulu (title, body_html, summary_html, meta_title, meta_description)
  trafiaja przez `translationsRegister` GraphQL i sa automatycznie serwowane przez
  **Shopify Markets + locales** - motyw nic nie musi robic, pokazuje wlasciwy jezyk
  na bazie aktywnego `request.locale.iso_code`.
- **SEO metafields** (`global.title_tag`, `global.description_tag`) sa standardowo
  obslugiwane przez motyw (patrz `sections/main-article.liquid` -> `{{ article.metafields.global.title_tag }}`).
- **Podglad offline** (`preview.html` generowany przez `Komponenty/blog/preview.py`) uzywa
  `font-family: "Bodoni Moda", serif` dla naglowkow i `"Cormorant Garamond", serif` dla body -
  identycznych z motywem Horizon (patrz `layout/theme.liquid` `@font-face` imports).
  Dzieki temu podglad wyglada ~1:1 jak finalny post po publikacji.
- **Tagi artykulu** sa wspolne dla wszystkich jezykow (Shopify nie tlumaczy tagow bloga).
  W motywie filtry/chmura tagow na `blog.liquid` dziala na surowym tagu PL.
