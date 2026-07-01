# SHOP_KNOWLEDGE.md - Brief dla AI (ARCHIWUM — tylko czytanie)

> **⚠️ Nie aktualizuj tego pliku.** Nowe fakty → [`docs/komponenty/`](docs/komponenty/) (prawda) · hub: [`docs/README.md`](docs/README.md)  
> **START:** [`../MATKA.md`](../MATKA.md) · **Integracja:** [`../docs/zaleznosci.md`](../docs/zaleznosci.md)

> **Cel historyczny:** kontekst biznesowy, rynki, tagi, prompty LLM sprzed refaktoryzacji docs modułowych.  
> Czytaj **sekcję po sekcji** tylko gdy brakuje w pliku `docs/komponenty/<moduł>.md`. Nie skanuj całości.

---

## 1. PRODUKT BIZNESOWY

- **Sklep:** GicleeArt (Shopify, plan: standardowy)
- **Domena:** `gicleeart.eu`
- **Domyslna domena Shopify:** `giclee-art-3.myshopify.com` (alias uzywany w `.env` SHOP
  i przy `npm run oauth`). **Kanoniczny `myshopify_domain` sklepu to `19v3bj-n0.myshopify.com`**
  (domena publiczna: `gicleeart.eu`) - OAuth zapisuje wlasnie ten kanoniczny adres w
  `.shopify_session.json` (`shop`), to ten sam sklep "Giclee Art".
- **Co sprzedajemy** (DWIE galezie, oba produkty na tej samej stronie, drukowane ta sama technika giclee):
  1. **Reprodukcje klasykow malarstwa** - gotowe produkty w katalogu, kazdy obraz to jeden produkt
     (np. "Hans Dahl - Babie lato"), z wariantami wymiaru / rodzaju drewna ramy / koloru ramy.
     To jest galaz obslugiwana przez komponent `dodajobraz` (auto-generacja produktow, tlumaczenia,
     smart-collections, 7 rynkow).
  2. **Wydruki na zamowienie z wlasnego zdjecia (custom print / foto na plotnie)** - klient wgrywa
     wlasne zdjecie (rodzinne, slubne, portret, sesja, krajobraz, logo) przez **edytor w sklepie**,
     sam dopasowuje kadr w **live mockupie** (widzi podglad na scianie w pokoju), wybiera rozmiar,
     drukujemy na tym samym plotnie giclee co reprodukcje. Grupa: klienci indywidualni, fotografowie,
     male firmy. **Ta galaz NIE wymaga osobnych produktow w katalogu** - obsluguje ja mechanizm
     edytora na stronie (Liquid + JS w motywie, poza scope'em komponentu `dodajobraz`).
- **Kategoria w sklepie (reprodukcje):** wylacznie **"Obrazy"** (jedyna wartosc pola `custom.kategoria`).
- **Vendor (Shopify):** `Giclee Art`
- **Product type (Shopify):** `Obraz`
- **Tytul produktu:** zawsze w formacie `"{Artysta} - {Tytul polski}"` (np. `Hans Dahl - Babie lato`).
  Nazwa pliku zrodlowego ma format `Artysta - Tytul.jpg` (separator: spacja-mysjnik-spacja).

---

## 2. RYNKI I CENNIK (Shopify Markets)

Sklep ma rownolegle wersje na 7 rynkow. Markup liczony **od ceny PL (bazowej)**.

| Rynek         | Kod      | URL prefix                | Jezyk        | Markup vs PL |
|---------------|----------|---------------------------|--------------|--------------|
| Polska (baza) | `pl`     | `gicleeart.eu/pl-pl`      | polski       | **0%** (baza)|
| Hiszpania     | `es`     | `gicleeart.eu/es-es`      | hiszpanski   | **+5%**      |
| Wlochy        | `it`     | `gicleeart.eu/it-it`      | wloski       | **+5%**      |
| Europa (UE)   | `eu`     | `gicleeart.eu/en-eu`      | angielski    | **+8%**      |
| Francja       | `fr`     | `gicleeart.eu/fr-fr`      | francuski    | **+10%**     |
| Niemcy        | `de`     | `gicleeart.eu/de-de`      | niemiecki    | **+15%**     |
| Holandia      | `nl`     | `gicleeart.eu/nl-nl`      | holenderski  | **+15%**     |

- **Kazdy rynek ma osobny katalog (Catalog) w Shopify** z procentowym narzutem na cenniki.
  Rynki i katalogi sa juz utworzone w Shopify Admin **recznie przez wlasciciela**.
- **Zrodlo prawdy o markup'ach** w aplikacji: `cursor-api/Komponenty/dodajobraz/markets_config.json`.
  Jesli wlasciciel zmieni markup w aplikacji, mozemy go pushowac do Shopify Catalog
  (jezeli mamy scope `write_markets`/`write_price_lists`).
- **Waluta dla wszystkich rynkow:** EUR (rynki UE/europejskie). PL ma wlasna walute (PLN).

> **WAZNE dla AI:** ceny w aplikacji w GUI cennika sa liczone z uwzglednieniem **kursu walut**:
> - PLN: `cena_PL * (1 + markup%/100)`.
> - EUR / inne: `cena_PL / kurs_PLN_per_waluta * (1 + markup%/100)`.
>
> Kurs walut pobierany z **NBP API** (https://api.nbp.pl, darmowe, bez klucza) przez
> `Komponenty/_shared/fx_rates.py`. Cache 24h w `Komponenty/_shared/data/fx_cache.json`.
> Dialog `Rynki...` pokazuje aktualny kurs + przyciski "Odswiez z NBP", "Kurs recznie..." oraz
> **EUR w Shopify...** (GraphQL `Shop.currencySettings`: `manualRate` / `rateUpdatedAt` dla EUR).
> Przy kursie **automatycznym** w panelu Shopify pole `manualRate` jest puste — pelnej stawki
> jak NBP API **nie ma** w Admin API; porownanie z NBP jest w tym samym oknie informacyjnym.

---

## 3. JEZYKI I TLUMACZENIA

- **Jezyk bazowy sklepu (Shopify default locale):** polski (PL).
- **Aktywne jezyki (Online Store -> Languages):** PL, EN, DE, FR, ES, NL, IT.
- **Co MUSI byc tlumaczone na kazdy z 6 jezykow obcych** dla kazdego produktu:
  - tytul produktu (czesc po mysjniku, np. `Babie lato` -> `Indian Summer` / `Été indien` itd.)
  - opis (`body_html`) - 3 akapity (+ opcjonalnie 4. z ciekawostkami o obrazie) i etykiety w tabeli "SZCZEGOLY"
  - SEO `title_tag` (metafield `global.title_tag`)
  - SEO `description_tag` (metafield `global.description_tag`)
  - alt text glownego zdjecia
  - **opcjonalnie**: tagi (zostaja po polsku, bo tagi w Shopify sa per-shop, nie per-language;
    Shopify nie tlumaczy tagow per market - rozwiazanie: dla kazdego jezyka mamy rownolegle
    `ALWAYS_TAGS_<LANG>` jako ekwiwalenty SEO po obcemu i one rowniez zostaja na produkcie
    jako pelnoprawne tagi - dzieki temu produkt znajduje sie w kazdym jezyku po slowach
    typu `wall art`, `Wandbild`, `tableau mural` itd.).
- **Push tlumaczen** odbywa sie przez Shopify Admin GraphQL API: `translationsRegister`
  mutation z `Locale` (`en`, `de`, `fr`, `es`, `nl`, `it`) i typem zasobu `Product`,
  `Collection`, `Metafield`, `OnlineStoreTheme` etc.
- **Wymagany scope OAuth (juz wpisany w `.env` i `shopify.app.toml`):**
  ```
  read_products, write_products, read_publications, write_publications,
  read_translations, write_translations, read_markets, write_markets,
  read_content, write_content, read_orders, read_files, write_files,
  read_online_store_navigation, write_online_store_navigation
  ```
  - `read_content, write_content` sa wymagane przez komponent **blog** (Blog/Article REST API).
  - `read_orders` jest wymagane przez komponent **produkcja** (polling zamowien Shopify).
  - `read/write_online_store_navigation` - edycja menu nawigacji (GraphQL `menus`/`menuUpdate`),
    uzywane do dodawania artystow do menu (patrz sekcja 9 + `add_artist_to_menu.py`).
  - **WORKFLOW dla nowego scope** (bezwzglednie w tej kolejnosci!):
    1. Dopisz scope do `.env` (SCOPES=...) **i** do `shopify.app.toml` (`[access_scopes] scopes = "..."`) - MUSZA sie zgadzac.
    2. `cd cursor-api && npm run deploy -- --allow-updates` -> push konfiguracji do Shopify Partners (opublikuje nowa wersje aplikacji).
    3. `cd cursor-api && npm run oauth` -> otworz `http://127.0.0.1:3000`, kliknij link z `?shop=giclee-art-3.myshopify.com`, zatwierdz nowe uprawnienia (sklep `.shopify_session.json` dostaje token ze wszystkimi scope'ami).
  - **NIE** pomijac kroku 2 (deploy) - bez tego Shopify nie wie o nowych scopach i OAuth pokaze stary, okrojony ekran zgody.
  - Aktualna wersja opublikowana w Shopify Partners: `cursor-api-9` (czerwiec 2026; dodane scope nawigacji).

---

## 4. ARCHITEKTURA APLIKACJI

```
cursor-api/                                # backend Pythona + OAuth + Shopify klient
  .env                                     # SHOPIFY_API_KEY, SCOPES, SHOP, SERPAPI_KEY
  .shopify_session.json                    # token OAuth (po `npm run oauth`)
  shopify.app.toml                         # konfiguracja Shopify CLI (klient, scopes)
  oauth-server.mjs                         # Node OAuth server (port 3000)
  giclee_app/                              # launcher Tkinter (kafelki komponentow)
    launcher.py                            # uruchamia komponenty jako osobne procesy; toolbar: Stan sesji, Dziennik akcji
    session_status.py                      # raport tekstowy: .shopify_session.json, NBP fx_cache, mtime/git shopify.app.toml
    component_loader.py
    runtime.py
  Komponenty/                              # WSZYSTKIE komponenty GUI
    dodajobraz/                            # GLOWNY komponent - tworzenie produktow
      gui.py                               # Tkinter GUI (drag-drop, kolejka, prompt, batch, dialog cennika, dialog rynkow)
      create.py                            # orkiestrator: produkt + zdjecie + meta + smart-coll. + push tlumaczen
      shopify_client.py                    # REST + GraphQL; iter_each_product_page / fetch_all_products (anulowanie, postep)
      prompt_builder.py                    # buduje prompt LLM + waliduje JSON (z tlumaczeniami i18n)
      parser.py                            # parsuje 'Artysta - Tytul.jpg', sufiksy F2/KK/WK
      tags_taxonomy.py                     # PL: ALWAYS_TAGS, whitelisty styl/room/gift/genre, smart-collections (+ orientation/color)
      tags_taxonomy_i18n.py                # ALWAYS_TAGS dla EN/DE/FR/ES/NL/IT (~100 fraz lacznie)
      image_analysis.py                    # PIL: orientacja (pionowy/poziomy/kwadrat/panorama) + dominujacy kolor (15 kolorow PL)
      html_template.py                     # szablon HTML body_html (tabela SZCZEGOLY)
      markets_config.json                  # 7 rynkow z markup %, locale, currency, URL, Shopify GIDs
      markets.py                           # helpery: load/save, compute_market_price, push do Shopify Markets/PriceLists API
    _shared/activity_log.py                # dziennik zdarzen JSONL (Komponenty/_shared/data/activity_log.jsonl)
    _shared/activity_log_ui.py              # okno podgladu + kopiowanie; task_notify.py = dzwiek po batchu
    nazwijobraz/                           # nazewnictwo + SEO obrazow zrodlowych
    mockup/                                # mock-up ramki A4 -> galeria Shopify (mockup)
      gui.py                               # drag-drop kolejka, wybór zestawu szablonu, batch upload
      compositor.py                        # PIL: wstawienie obrazu w pole A4 (cover) + wykrywanie slotu
      publish.py                           # parse nazwy, render WEBP, add_follow_up_image (mockup)
      templates.py                         # data/templates.json + assets/*.png
    pobierzobraz/                          # pobieracz obrazow IIIF z muzeow
    blog/                                  # marketing/blog: generator tresci + tematow + publikacja 7 jez.
      component.json                       # mode=inline, icon 📝
      view.py                              # glowny inline view (3 kafelki + sub-views)
      shopify_blog.py                      # REST blogs/articles + image base64 + translations
      prompts.py                           # prompty Opus/GPT (tresc + 10 tematow)
      preview.py                           # generator podgladu HTML z 7 zakladkami (Bodoni/Cormorant)
      generator_tresci.py                  # Toplevel: temat -> prompt -> paste -> send (auto-copy/paste)
      generator_tematow.py                 # Toplevel: fetch tytuly -> prompt -> parse 10 propozycji
      propozycje_tematow.py                # sub-view: lista propozycji + PPM (kopiuj/generuj tresc/usun)
      obecne_posty.py                      # sub-view: lista postow z Shopify (auto-fetch)
      storage.py                           # topics.json + articles_cache.json
      data/                                # cache: topics.json, articles_cache.json, preview.html
    socialmedia/                           # marketing/social: generator + planer postow + cykl
      component.json                       # mode=inline, icon 📱, kolor #e91e63
      view.py                              # main (3 kafelki: Generator, Planer, Cykl)
      platforms.py                         # IG Feed/Stories/Reels, FB, TikTok, Pinterest - limity, ton, struktura
      hashtag_library.py                   # LOCKED_HASHTAGS PL/EN + SUGGESTED_THEMES
      prompts.py                           # prompty: single / multi-platform / series + parsery JSON
      generator_tresci.py                  # Toplevel: checkboxy platform (MULTI) -> prompt -> paste -> podglad -> zapis
      planer_postow.py                     # sub-view: kolejka postow + PPM + eksport CSV + licznik znakow + sortowanie kolumn
      storage.py                           # posts.json (wszystkie posty ze statusem)
      data/                                # posts.json
      cykl/                                # sub-komponent 'Cykl - Obraz na rano, popoludnie i wieczor'
        view.py                            # inline Treeview kolejki + toolbar + context menu
        storage.py                         # CykleItem + queue.json + generation_state + meta_state + config + creds
        platforms_cykl.py                  # 4 kanaly (fb_pl/fb_en/ig_pl/ig_en) + SLOT_TIMES 08/14/20
        queue_builder.py                   # fetch kolekcji artystow (REST custom_collections) + delta detect
        scheduler.py                       # assign_slots (3/dzien), shift +/-1 day, reorder_move, reassign_from_now
        images.py                          # Obrazy/<artysta>/<tytul>/ + sufiks MOCKUP + sync + missing_report
        content_gen.py                     # build_week_prompt (21 poz. x 2 jezyki) + parse_week_response + apply
        meta_config.py                     # Dialog 'Ustawienia Meta API' - tokeny 4 kanalow + test
        meta_publisher.py                  # Graph API v19: FB photos, IG carousel + upload_to_shopify_files
        edit_dialog.py                     # Toplevel 4-tab (per kanal) + images pick/reorder + manual_override
        help_text.py                       # HELP_TEXT + IMAGE_SPECS_QUICK
    zadania/                               # marketing/strategia: organizer z LLM + Shopify + kalendarz
      component.json                       # mode=inline, icon 📆, kolor #00897b
      view.py                              # main: lista zadan + filtry (status/kanal/jezyk/rynek/priorytet) + PPM + sortowanie kolumn
      shopify_signals.py                   # fetch_new_products/collections/artists (REST + iter_all_products)
      holidays.py                          # kalendarz swiat 2026-2028 (per rynek PL/EU/FR/DE/ES/NL/IT)
      prompts.py                           # prompt LLM: multi-channel + multi-market + description_translations
      generator_zadan.py                   # Toplevel: fetch sygnalow -> prompt -> paste -> parse -> save
      storage.py                           # tasks.json + signals_cache.json + reminders.json
      data/                                # tasks.json, signals_cache.json, reminders.json
  giclee_app/launcher.py                   # + monthly reminder (1-5 dzien miesiaca -> propozycja planu)
    cenyMarketing/                         # analiza pricing-u (standalone HTML + inline tile view)
    obrazy/, kalkulacja/, kpir/, dokumentysprzedazy/, ksiegowosc/, finanse/, planer/, ...  # inne komponenty
```

### Komponent `dodajobraz` - flow

1. **Drag&drop pliku** (`Artysta - Tytul.jpg`) -> parser wyciaga `(artist, raw_title)`.
2. **Sufiksy w tytule** (parser):
   - `F2` / `F3` / ... = "follow-up image" (dogrywka kolejnego zdjecia do istniejacego produktu).
   - `KK` (korekta koncowa) / `WK` (korekta wstepna) - takze z separatorem `- KK` / `- WK`.
   - Mozna laczyc: `Babie lato F2 KK` lub `Babie lato F2 - KK`.
   - **Detekcja jezyka tytulu** (`is_polish_title`, heurystyka): ustawia flage
     `title_is_polish` na pozycji. Flaga jest uzywana w promptach LLM (czy tlumaczyc
     tytul na polski) i w `_kick_precheck` (matching produktow po tytule obcym).
   - **Reczna korekta jezyka:** w GUI mozna przelaczyc `polski` <-> `OBCY` przez
     przycisk *"Przelacz polski/obcy"* (panel po prawej stronie kolejki) lub
     dwuklikiem na kolumnie *"Jezyk tytulu"*. Rotation rekurencyjnie przegenerowuje
     prompt. Recznie ustawiona flaga jest oznaczona `*` w kolumnie (pole
     `title_is_polish_manual` na pozycji). Dzialanie tylko dla nowych produktow
     (dogrywki F2+ maja jezyk `-`).
   - **Inline-edycja `artysta` / `tytul`:** dwuklik w komorce kolumny *"Artysta"*
     lub *"Tytul"* otwiera overlay-Entry. Enter = zapisz, Esc = anuluj.
     Edycja tytulu automatycznie re-parse'uje sufiksy (`F<N>`, `KK`, `WK`) i
     ponownie uruchamia detekcje jezyka oraz `_kick_precheck` (chyba ze jezyk
     zostal juz przelaczony recznie - wtedy flaga nie jest nadpisywana).
     Edycja artysty nie rusza tytulu. Po edycji prompt LLM jest regenerowany.
3. **GUI generuje prompt** (po polsku) przez `prompt_builder.build_prompt`/`build_batch_prompt`
   i wkleja go do Cursor chat. Uzytkownik kopiuje JSON odpowiedzi z LLM z powrotem.
4. **Parsowanie i walidacja JSON** (`parse_response_json` / `parse_batch_response_json`):
   - Sprawdza wymagane pola (REQUIRED_KEYS).
   - **Wymusza stale tagi** (`ensure_required_tags`) z `tags_taxonomy.ALWAYS_TAGS`.
   - **Wymusza kategorie = "Obrazy"** (`force_fixed_kategoria`).
   - Rozszerza tagi o synonimy gatunkow (`expand_with_synonyms`).
5. **Tworzenie produktu** (`create_painting_product`):
   a) Pobiera warianty z **lokalnego szablonu** (`variant_templates.json`, patrz sekcja 9 ponizej).
      Domyslnie uzywa szablonu `is_default=True` (pierwszy uruchomienie = auto-import
      z `REFERENCE_PRODUCT_ID = 15524677845340`, potem juz lokalny snapshot).
   b) Buduje SEO `title_tag` + `meta_desc` (wzbogacone o gatunek/nurt + frazy zakupowe PL).
   c) Buduje SEO **alt text** zdjecia (artysta + tytul + gatunek + nurt + technika +
      "reprodukcja giclee na plotnie", max 125 znakow).
   d) Tworzy produkt w Shopify (REST `POST /products.json`).
   e) Wgrywa zdjecie z alt text'em.
   f) Ustawia metapola SEO (`global.title_tag`, `global.description_tag`).
   g) Ustawia `custom.kategoria = "Obrazy"`.
   h) Dodaje produkt do **kolekcji artysty** (custom collection o tytule
      "Nazwisko, Imie", np. "Dahl, Hans"). Jesli kolekcja artysty nie istnieje,
      produkt powstaje **bez przypisania** i trafia do `collection_gaps`
      (`collection_assign_error="collection_not_found"`).
      - Po batchu otwiera sie okno **«Kolekcja artysty»** (`_show_collection_fix_dialog`).
        Dla kazdego artysty bez kolekcji sa dwie akcje:
        - **«Stworz artyste»** -> `create.create_artist_collection_and_menu(...)`:
          tworzy custom-collection, publikuje ja na kanalach, **buduje strone
          kolekcji jak u innych artystow** (opcjonalne pola w dialogu: daty zycia
          -> `<h4>`, krotki opis -> akapity, zdjecie/portret -> upload do Shopify
          Files i osadzenie jako okragly `<img>`; nowej kolekcji ustawia tez wspolny
          baner `ARTIST_COLLECTION_BANNER_SRC`), dodaje pozycje do menu glownego pod
          **«ARTYŚCI»** (alfabetycznie, scope nawigacji) i przypisuje produkty.
          Uzyj, gdy kolekcji jeszcze NIE MA. Body buduje
          `html_template.build_artist_collection_body_html(...)`.
        - **«Przypisz do kolekcji»** -> `assign_products_to_collection_title(...)`:
          gdy kolekcja istnieje pod inna nazwa (tylko podpina produkty).
   i) **AUTO-TWORZY smart-collections** z tagow `style/room/gift/genre`
      (`ensure_smart_collections_from_tags`):
      - smart-collection dla kazdego tagu z `tags_taxonomy.COLLECTION_RULES`,
      - regula: `tag equals <tag>`,
      - tytul, body_html i SEO metapola - wedlug blueprintu z `tags_taxonomy.py`,
      - kolekcja jest publikowana na wszystkich kanalach,
      - cache w pamieci sesji - nie spamuje API w batch'u.
   j) Publikuje produkt na wszystkich kanalach (`publishablePublish`).

### Komponent `dodajobraz` - reuse zdjec do istniejacych produktow

- **`(preview)` w nazwie pliku** (`Hans Dahl - Babie lato - (preview).webp`) ->
  `add_preview_image`: alt `Artysta - Tytul (preview)`, ustawia **featured** (kolekcje,
  menu Katalog). W PDP motyw ukrywa media z `(preview)` w alt (`giclee-product-gallery-media.liquid`).
- **`Full` w nazwie pliku** (`Hans Dahl - Babie lato - Full.webp`) ->
  `add_full_image` lub tworzenie produktu z JSON przypisanym do tego pliku:
  alt `Artysta - Tytul (Full)`, **position=1** w galerii; featured zostaje preview jesli jest.
- **Batch:** najpierw nowe produkty (LLM), potem `(preview)`, potem `Full` (bez duplikatu
  po create), na koncu `F2+`.
- **GUI:** trzy osobne pola drag-and-drop (+ klik / przycisk pod polem) dla preview, Full
  i pozostalych — filtruja typ pliku po nazwie. Walidacja kolejki (`queue_audit.py`):
  kazde dzielo wymaga obu plikow w kolejce zanim «Utworz wszystko» (wyjatek: sama dogrywka F2+).
- **Sufiks `F2` w nazwie pliku** (`Hans Dahl - Babie lato F2.jpg`) -> dogrywa kolejne
  zdjecie do produktu bazowego (`add_follow_up_image`). Produkt bazowy musi juz istniec.
- **`I1`, `I2`, `I3`…** (`Hans Dahl - Babie lato I2.jpg`) -> dogrywka z alt `(I<N>)`.
- **`(mockup)`** (`Hans Dahl - Babie lato - (mockup) - CZB.webp` / `... - CZCZ.webp`) ->
  dogrywka mockupu; widoczny w galerii PDP. Sufiks **`CZB`** = czarna ramka + biale passe-partout,
  **`CZCZ`** = czarna ramka + czarne passe-partout. Tylko `(preview)` jest ukryte w galerii.
  Komponent **`mockup`** generuje ten plik automatycznie: naklada obraz zrodlowy na szablon
  ramki (pole A4, pion/poziom wg orientacji) i wysyla przez `add_follow_up_image`.
- **Sufiks `KK` / `WK`** - oznacza korekte kolorystyczna; produkt zachowuje sie jak
  zwykla dogrywka, ale alt text dostaje suffix `(KK)` lub `(WK)`.
- **Akcja `replace_image`** w GUI - podmienia tylko zdjecie glowne (`replace_primary_image`).
- **Akcja `replace_image_and_description`** - podmienia zdjecie + nadpisuje tytul, opis,
  tagi, SEO i metapola (uzywa nowego JSON-a z LLM).

### Komponent `dodajobraz` — Zoom HD → R2 (szybkosc uploadu)

- **Flow:** `zoom_tiles.generate_zoom_package` (CPU, Pillow) → `r2_storage.upload_many`
  (sieć) → metafield `custom.zoom_manifest` + szablon `nowy-szblon-produktu`.
- **Upload:** jeden wspolny klient S3 na paczke kafelkow; rownolegle PUT-y
  (`r2_storage.upload_many`, domyslnie **12** watkow). Env w `cursor-api/.env`:
  - `R2_UPLOAD_WORKERS` — ile kafelkow naraz na jeden produkt (1–64, domyslnie 12).
  - `R2_ZOOM_PARALLEL` — ile produktow zoomuje sie rownolegle przy batchu z Shopify
    (1–8, domyslnie 3; wczesniej na sztywno 2).
- **Batch:** przy «Utworz wszystko» + zoom — Shopify i zoom ida rownolegle; zoom startuje
  gdy znamy `product_id` (nie czeka na caly batch Shopify).
- **GUI:** wiersz «Czas» pod paskiem Zoom HD — ostatni plik + srednia batcha
  (`kafelki` / `R2` / `Shopify`); te same wartosci w logu `[zoom] Czas (...)`.
- **Nie przyspiesza R2:** generowanie kafelkow WEBP (`method=6`) — to osobny etap CPU.

### Komponent `aktualizujopis` — Aktualizuj opis (GUI)

- Kafelek **«Aktualizuj opis»** w sekcji Administracja produktu GicleeApp — okno z filtrowalna lista produktow
  typu `Obraz`, wyborem trybu i wklejeniem tablicy JSON z LLM (`parse_batch_response_json`).
- **Tryby:** `Podmien wszystko` (caly zestaw akapitow PL + tlumaczen), `Podmien wybrany akapit`
  (nr 1–4), `Dodaj jeszcze jeden akapit` (np. 4. z ciekawostkami gdy sa juz 3).
- **Dopasowanie JSON → produkt:** pole `plik` (nazwa glownej grafiki), `source_key` z nazwy pliku,
  `tytul_polski` vs tytul obrazu; przy jednym wpisie w tablicy — auto-wybór.
- **Podglad:** po kliknieciu produktu na liscie od razu laduje **obecny opis** z Shopify
  (PL lub wybrany jezyk z przyciskow EN/DE/…). Po «Analizuj JSON» prawa kolumna pokazuje
  wersje po zmianie (edytowalna przed zapisem). Ekstrakcja akapitow: `html_template.extract_paragraphs_from_body_html`.
- **Prompt tlumaczenia:** przy wybranej wersji jezykowej i akapicie pojawia sie przycisk
  «Prompt tlumaczenia» — po pytaniu (biezacy akapit / wszystkie) kopiuje prompt LLM
  (`build_translation_prompt` / `build_translation_prompt_all`) z instrukcja tlumaczenia na 6 rynkow.
- **Prompt do nowego opisu:** suwak **Auto prompt** (Wl/Wyl, `description_update_prefs.json`) — gdy wlaczony,
  po zaznaczeniu produktu prompt kopiuje sie automatycznie do schowka (toast); recznie: przycisk
  «Prompt do nowego opisu» lub **Ctrl+C** na liscie produktow. Kopiuje
  prompt LLM z artysta i tytulem z listy oraz wytycznymi do pola `akapity`
  (`prompt_builder.build_new_description_prompt`). Tytuly: angielski (JSON EN / tlumaczenie
  Shopify / nazwa pliku grafiki), oryginalny (JSON / kolumna SZCZEGOLY), polski (sklep).
- **Wklej tlumaczenia do akapitu:** okno z JSON `{en, de, fr, es, nl, it}` — jeden obiekt
  dla zaznaczonego akapitu, **kilka obiektow pod soba** (akapity 1–4 naraz) albo
  **jeden obiekt** `{akapit_1: {...}, akapit_2: {...}, ...}`; parser naprawia cudzyslowy
  w tekscie LLM (`parse_paragraph_translations_batch`).
- **Porownywarka:** okno z 6 slotami wersji akapitu (wklej z LLM) obok edytowalnego oryginalu;
  suwak **Model** (Sonnet / Gemini / GPT) ustawia domyslny slot przy otwarciu porownywarki:
  Sonnet → Wersja 1, Gemini → Wersja 3, GPT → Wersja 5 (`description_compare_llm.json`);
  «Kopiuj wersje do roboczego» + «Zastosuj do opisu» (biezacy akapit) +
  **«Zastosuj wszystkie akapity»** (robocze wersje 1–4 naraz); **«Wklej calosc»** — JSON `{"akapity":[...]}`
  wypelnia wybrana **Wersje** (1–6): akapity[i] → Akapit i+1 w tym slocie; pozostale wersje
  i oryginal/roboczy po prawej bez zmian (`parse_full_akapity_json`). W polach tekstu porownywarki
  **Ctrl+V** wkleja zwykly tekst; **Wklej calosc** (przycisk lub Ctrl+V poza polem) parsuje JSON.
  Po udanym wklejeniu calosci **PPM** (prawy przycisk myszy) zamyka okno porownywarki.
- **Zapis:** `PUT body_html` (PL) + `push_product_translations` dla jezykow obcych
  (`description_update.apply_description_update`). Log: `[opis]`.
- **Oznaczanie postepu:** kolumna **Akt.** w liscie produktow — ptaszek ✓ gdy produkt
  zostal zaktualizowany przez to okno (zapis do Shopify: «Zastosuj w Shopify», «Zapisz obecny opis»,
  «Zapisz kazda wersje jezykowa», «Zastosuj wszystkie akapity» w porownywarce itd.). Persystencja:
  `Komponenty/dodajobraz/data/description_update_marks.json` (lista `product_id`). Wczesniejsze
  oznaczenia z tego pliku wyswietlaja sie od razu jako ✓. Przyciski filtrowania «Wszystkie» /
  «Po aktualizacji» / «Bez oznaczenia», sortowanie po «Artysta» lub «Akt.» (strzalka kierunku).
  Na pasku licznika: **«Po aktualizacji: N/T (P%)»**. Produkty z wypelniona porownywarka bez ✓
  maja **blekitne tlo** (zielone = ✓, zolte = flaga).

### Komponent `dodajobraz` — Kontrola kolekcji (GUI)

- Okno **Kontrola kolekcji...** porownuje oczekiwana kolekcje artysty (`artist_collection_title`)
  z tym, w jakich kolekcjach jest produkt w Shopify.
- Po odswiezeniu: licznik **unikalnych artystow** (kolumna Artysta) w podsumowaniu i na pasku
  filtra (`artystow: N`, opcjonalnie `w widoku` przy filtrze / «Tylko problemy»).
- **OK** — produkt jest w pasujacej kolekcji artysty. **BRAK W KOLEKCJI** — kolekcja w sklepie
  istnieje, produkt do niej nie trafil. **BRAK KOLEKCJI** — nie znaleziono kolekcji o pasujacej
  nazwie (czesto mylone z „nie w kolekcji”; produkt moze byc w «Van Gogh, Vincent» mimo oczekiwanego
  «Gogh, Vincent Van»). Od 2026-06 porownanie nazw: te same tokeny slow (kolejnosc, myslniki, diakrytyki).

### Komponent `mockup` — generowanie mockupow ramki

- **Wejscie:** pliki `Artysta - Tytul.ext` (Full, `(preview)` lub bez sufiksu). Produkt musi juz istniec w Shopify.
- **Szablony:** `Komponenty/mockup/data/templates.json` + PNG w `assets/`. Dwa zestawy czarnej ramki:
  **białe** lub **czarne passe-partout** (wybor w combobox «Zestaw»); w kazdym wariant **pion**
  i **poziom** — orientacja dobierana automatycznie wg obrazu zrodlowego. Dla czarnego
  passe-partout **obowiazkowe** reczne `slot` w JSON (auto flood-fill myli ciemne okno z matą).
- **Pole A4:** wspolrzedne `[x, y, w, h]` w JSON (fallback). Domyslnie **flood-fill od srodka**
  szablonu — wykrywa przezroczyste lub ciemne otwory w passe-partout (nie cala ramke).
- **Skladanie:** obraz skalowany **cover** (wypelnienie pola, przyciecie nadmiaru), zapis WEBP,
  nazwa docelowa `Artysta - Tytul - (mockup) - CZB.webp` (bialy pp) lub `... - CZCZ.webp` (czarny pp).
- **GUI:** drag-drop kolejka + **panel podgladu** (auto po zaznaczeniu) + okno «Pelny podglad» + **Eksportuj na dysk**
  (zaznaczony obraz z kolejki → folder docelowy, WEBP bez wysylki do Shopify) przed uploadem.
- **Braki na stronie** (`audit.py`): skan produktow bez CZB/CZCZ w galerii. Wykrywanie po **alcie i URL-u**
  pliku (`_mockup_` w CDN) — starsze aktualizacje tytulow potrafily nadpisac alt bez «(mockup)» mimo
  ze plik mockupu zostal w Shopify. Do generowania brakujacego mockupu zrodlo: **preview**, potem
  **Full / WK / KK**, na koncu pierwsze nie-mockup zdjecie (produkty bez `(preview)` tez da sie dograc).
  Gdy mockup jest w Shopify, ale **nie widac go na PDP** — alt stracil «(mockup)»; naprawa:
  `Komponenty/mockup/repair_alts.py` (masowo `repair_all_mockup_alts()`).

### Komponent `print_optimize` — optymalizacja zdjec pod druk (Gemini + kalibracja Whitewall)

- **Cel:** warstwa jak Whitewall «Image optimisation» — rozpoznanie sceny (Gemini) → kontrast,
  saturacja, balans kolorow, podbicie cieni; suwak `strength` 0–100 (domyslnie 70, odpowiednik `pcStrength`).
- **Kod:** `Komponenty/print_optimize/` — `optimize_to_file()`, `compare_images()` (ΔE LAB, SSIM).
- **CLI:** `python -m Komponenty.print_optimize optimize|compare|collect-pairs|collect-id|calibrate`
  (z `cursor-api/`). Wymaga `GEMINI_API_KEY` dla analizy sceny; `playwright` tylko do `collect-pairs`.
- **GUI (GicleeApp):** kafelek **Optymalizacja druku** — zakladki Optymalizuj / Zestaw testowy /
  Kalibracja / Porownaj. Domyslne foldery: `data/test_photos/`, `data/ww_pairs/`.
- **Kalibracja:** wlasny folder zdjec testowych → `collect-pairs` (upload Whitewall, pary `original` /
  `ww70` z imageserver) → `calibrate` generuje `ours70` + `calibration_report.json`. Podglad Whitewall
  (`type=12`) ≠ caly pipeline produkcyjny (SuperResolution, UltraHD to osobne opcje).
- **Docs:** `cursor-api/docs/komponenty/print_optimize.md`. Integracja z Workerem / mockupem klienta — TODO.

### Komponent `passepartout` — kalkulator jednostek Allegro

- **Kod:** `Komponenty/passepartout/` — widok **inline Tkinter** w launcherze (bez przeglądarki).
- **Launcher:** sekcja **Zamówienia**, `mode=inline` — klik kafelka montuje `view.build_view`.
- **Logika:** `calculations.py` — koszt od wymiaru zewnętrznego; dwa tryby zaokrąglania; tabela 1–30 szt.; wiadomość do sprzedawcy.
- **Weryfikacja:** `python -m Komponenty.passepartout.verify_examples`
- **Docs:** `cursor-api/docs/komponenty/passepartout.md`.

### Komponent `infoplikow` — Informacje o plikach (GUI)

- Kafelek **«Informacje o plikach»** w sekcji Administracja produktu — podglad grafik produktu w Shopify.
- Lista produktow typu `Obraz` (jak w «Aktualizuj opis»); po wyborze: tabela wszystkich zdjec galerii
  (`products/{id}/images.json`) z kolumnami: pozycja, plik CDN (nazwa z URL), **alt** (nazwa na stronie),
  rola (`preview` / `Full` / `mockup` / inne), widocznosc w galerii PDP, czy glowne, wymiary, warianty.
- Klasyfikacja roli: `Komponenty/dodajobraz/parser.py` (`alt_is_catalog_preview`, `image_ref_is_mockup`, itd.).
- Dodatkowo: wykryte tagi `<img>` w `body_html` opisu produktu.
- PPM / dwuklik na grafice: URL, alt, miniaturka do schowka; linki do admina i `gicleeart.eu/pl-pl/products/{handle}`.

---

## 5. KLUCZE / IDENTYFIKATORY

- `REFERENCE_PRODUCT_ID = 15524677845340` (`cursor-api/Komponenty/dodajobraz/templates.py`)
  - **TYLKO PRZY PIERWSZYM URUCHOMIENIU** - aplikacja zaciaga z tego produktu
    warianty i zapisuje lokalnie jako szablon "Podstawowy". Potem NIE PYTA Shopify -
    dane sa w `cursor-api/Komponenty/dodajobraz/data/variant_templates.json`.
  - Mozesz bezpiecznie usunac ten produkt w Shopify - apka i tak bedzie dzialac
    (uzywa lokalnego snapshotu).
  - Aby odswiezyc szablon z Shopify: dialog **Szablony...** -> "Odswiez z Shopify"
    (zastepuje warianty biezacego szablonu aktualnymi danymi z produktu o podanym ID).
  - Cennik mozna tez edytowac recznie w dialogu **Szablony...** (CRUD wariantow
    bez potrzeby pytania Shopify).
- **Stabilny identyfikator produktu** (do unikania duplikatow przy wielokrotnym wgrywaniu):
  `tag = src:<slug(artysta)>__<slug(tytul_bazowy)>` (np. `src:hans-dahl__babie-lato`).
  Jest dodawany **automatycznie** do kazdego produktu jako tag i jako metafield
  `custom.source_key`.
- **Kolekcje artysty:** custom collection o tytule `"Nazwisko, Imie"` (np. `"Dahl, Hans"`,
  `"Gogh, Vincent van"`). **Handle URL:** slug z `"Imie Nazwisko"` — np. `"Dahl, Hans"` ->
  `hans-dahl` (`parser.artist_collection_handle_from_title`). Przy tworzeniu kolekcji
  (`create_custom_collection`) handle jest ustawiany automatycznie. Masowa naprawa:
  `python scripts/fix_artist_collection_handles.py` (dry-run: `--dry-run`).
  Tworzone osobno (poza tym kodem, bo kolekcje artystow ma sie
  ksztaltowac recznie - katalog dziel artysty).
- **Domyslna sortacja smart-kolekcji:** `best-selling` (zmieniane w `create_smart_collection_for_tag`).

---

## 6. STAndarDOWE TAGI (`ALWAYS_TAGS`) - 17 PL

Te tagi trafiaja na **kazdy** produkt (sa wymuszane przez `ensure_required_tags`):

```
gicleeart, giclee, art, obraz na sciane, obraz do salonu, obraz na plotnie,
reprodukcja, reprodukcja giclee, wydruk giclee, dekoracja wnetrz,
prezent na rocznice, prezent na slub, prezent dla niej, prezent dla niego,
prezent na parapetowke, prezent na urodziny, pomysl na prezent
```

Kazdy z tych tagow **NIE jest** trigger'em smart-collection (zbieralby wszystkie produkty;
patrz "Smart Collections" nizej).

---

## 7. SMART COLLECTIONS (auto-tworzone)

Plik: `tags_taxonomy.py` -> `COLLECTION_RULES` (~56 wpisow).

Smart-collection powstaje **lazy** - dopiero gdy do bazy trafi pierwszy produkt z danym
tagiem. Dla kazdego utworzonego smart-collection:
- ustawiamy SEO metapola (`global.title_tag`, `global.description_tag`),
- publikujemy na wszystkich kanalach,
- domyslnie sortowanie `best-selling`.

**Grupy tagow napedzajace smart-collections (`COLLECTION_DRIVING_KINDS`):**

1. **Style wnetrz** (14): nowoczesny, klasyczny, skandynawski, boho, glamour, minimalistyczny,
   vintage, retro, loft, industrialny, art deco, prowansalski, rustykalny, elegancki.
   - Tytul: `"Obrazy w stylu <X-narzednik>"` (np. `"Obrazy w stylu skandynawskim"`).
2. **Pomieszczenia** (13): salon, sypialnia, jadalnia, kuchnia, gabinet, biuro, lazienka,
   przedpokoj, hol, pokoj dziecka, pokoj mlodziezowy, restauracja, hotel.
   - Tytul: `"Obrazy do <X-dopelniacz>"` (np. `"Obrazy do salonu"`).
3. **Prezenty** (13): prezent na rocznice/slub/parapetowke/urodziny/swieta,
   prezent dla niej/niego/rodzicow/mamy/taty/dziadkow/milosnika sztuki, pomysl na prezent.
   - Tytul: `"<Tag z duzej>"` (np. `"Prezent na slub"`).
4. **Gatunki** (16): pejzaz, krajobraz, marynistyka, portret, akt, martwa natura, kwiaty,
   konie, psy, koty, gory, las, miasto, wies, religia, abstrakcja.
   - Tytul: `"<liczba mnoga z duzej>"` (np. `"Pejzaze"`, `"Marynistyka"`, `"Portrety"`).

**Synonimy gatunkow** (`GENRE_SYNONYMS_PL`) - automatycznie dolaczane:
- `krajobraz` -> +`pejzaz`, +`obraz krajobrazowy`
- `marynistyka` -> +`morze`, +`obraz z morzem`, +`pejzaz marynistyczny`
- `kwiaty` -> +`bukiet`, +`obraz z kwiatami`, ...

5. **Orientacja** (4 - automatycznie z PIL `image_analysis.py`): pionowy, poziomy,
   kwadratowy, panorama. Tagi: `format pionowy`, `format poziomy`, `format kwadratowy`,
   `panorama`. Smart-coll: `Obrazy pionowe`, `Obrazy poziome`, ...
6. **Dominujacy kolor** (15 - automatycznie z PIL): czarny, bialy, szary, bezowy,
   brazowy, zloty, czerwony, rozowy, pomaranczowy, zolty, zielony, niebieski,
   granatowy, fioletowy, turkusowy. Tagi: `<kolor>` + `obraz <kolor>` (np.
   `niebieski` + `obraz niebieski`). Smart-coll: `Obrazy w kolorze: <kolor>`.

### PIL - automatyczna analiza obrazu

`image_analysis.analyze_image(path)` zwraca:
- `orientation_kind` ('pionowy'/'poziomy'/'kwadrat'/'panorama') na bazie aspect ratio:
  - kwadrat: 0.95-1.05, panorama: >=2.4, poziomy: >1.05 i <2.4, pionowy: <=0.95.
- `dominant_color_name` - najczestszy kolor z palety 15 PL po:
  1) downscale do 96x96,
  2) kwantyzacja PIL Median-Cut do 16 kolorow,
  3) odfiltrowanie pixeli zbyt jasnych (brightness > 240 = tlo) i ciemnych (<25 = cien),
  4) Euclidean distance w przestrzeni RGB do palety prototypowych kolorow.
- `extra_tags` lista 3 tagow gotowych do dorzucenia do produktu
  (`['format pionowy', 'niebieski', 'obraz niebieski']`).

Dorzucane do `tags_list` w `create.py` zaraz po sparsowaniu LLM-owej listy tagow
(przed pushem do Shopify).

---

## 8. PROMPT LLM (jak go zmieniac)

- Plik: `cursor-api/Komponenty/dodajobraz/prompt_builder.py`
- 3 prompty:
  - `build_prompt(artist, title, image_filename, title_is_polish)` - 1 obraz
  - `_build_batch_prompt_opus(items_block)` - paczka, dla Claude (krotszy, mniej rygoru)
  - `_build_batch_prompt_gpt(items_block, n)` - paczka, dla GPT (twardsze rygory JSON)
- **Wymagane pola w JSON-ie odpowiedzi LLM** (`REQUIRED_KEYS`):
  ```
  tytul_polski, tytul_orginalny, akapity (lista 3 lub 4 stringow — 4. opcjonalny: ciekawostki),
  data_powstania, miejsce_powstania, technika, gatunek, nurt, forma,
  tagi (lista 25-35), kategoria
  ```
- **Walidator** (`_validate_item`) automatycznie:
  - dorzuca `ALWAYS_TAGS`,
  - rozszerza tagi o `GENRE_SYNONYMS_PL`,
  - **wymusza** `kategoria = "Obrazy"`.
- **WAZNE dla AI:** `tytul_orginalny` musi byc w jezyku artysty (dunski/niemiecki/wloski/...).
  Tytul z pliku jest zazwyczaj angielski (wersja popularna), ale to NIE jest oryginal.
  Jesli LLM nie zna oryginalu - "Nieznana" (NIE wpisujemy mechanicznie tytulu z pliku).

---

## 9. SHOPIFY KLIENT (`shopify_client.py`)

- **API_VERSION = "2026-04"**
- **Auth:** load `shop` + `accessToken` z `cursor-api/.shopify_session.json`
  (token zapisany przez `oauth-server.mjs` po `npm run oauth`).
- **HTTP reliability:** `_urlopen_with_retries()` ustawia timeout 45s, throttling ~0,55s
  miedzy wywolaniami (limit Shopify REST: 2/s) i ponawia tymczasowe bledy dla
  idempotentnych requestow (`GET`/`PUT`/`DELETE`/`HEAD`): timeouty/WinError
  10060/10053/10054 oraz HTTP 429/5xx (z `Retry-After`, jesli Shopify poda).
  `POST` nie jest ponawiany przy 5xx (ryzyko duplikatow), ale HTTP 429 na `POST`
  jest ponawiane — Shopify odrzucilo request przez limiter, nie przetworzylo go.
  Transient network error jest zawijany w `ShopifyError`, wiec batch moze zapisac blad
  w podsumowaniu zamiast wywalic cale okno przez surowy `OSError`.
- **Kluczowe funkcje:**
  - REST: `rest_get/post/put`, `iter_all_products`, `find_artist_collection`,
    `create_product`, `update_product`, `upload_image`, `set_image_position`,
    `delete_product_image`, `create_product_variant`, `update_variant`,
    `delete_product_variant`, `update_variant_price`, `add_to_collect`,
    `set_seo_metafields`, `set_custom_metafield`, `upsert_metafield`,
    `find_metafield`, `find_smart_collection_by_handle/title`,
    `create_smart_collection_for_tag`, `upsert_smart_collection_for_tag`,
    `set_collection_seo_metafields`, `find_products_by_tag` (REST + GraphQL fallback),
    `find_custom_collection_by_title`, `create_custom_collection`,
    `update_custom_collection` (body_html/baner), `upload_file_to_shopify_files`
    (Shopify Files: stagedUploadsCreate + multipart + fileCreate + polling; scope `write_files`).
  - GraphQL: `graphql()`, `list_publications`, `publish_product_everywhere`,
    `publish_collection_everywhere`.
- **Nawigacja / menu (NOWE, scope `read/write_online_store_navigation`):**
  - `list_menus(shop, token)` - GraphQL `menus` z zagniezdzonymi pozycjami (do 3 poziomow).
  - `find_menu(..., handle=, contains_item_title=)` - znajdz menu po handle lub po
    obecnosci pozycji o danym tytule.
  - `add_menu_child_collection(..., parent_title, child_title, collection_gid, keep_sorted=True)`
    - dodaje pozycje typu COLLECTION pod parentem. **GOTCHA:** GraphQL `menuUpdate`
    NADPISUJE cale menu, wiec funkcja rekonstruuje pelne drzewo (`_item_to_input`
    zachowuje id/type/url/resourceId/tags + zagniezdzenia) i dokłada 1 pozycje.
    `keep_sorted` wstawia alfabetycznie miedzy rodzenstwo bez ruszania pozostalych.
  - **Struktura menu artystow:** `main-menu` -> pozycja `Katalog` [COLLECTIONS]
    -> dziecko `ARTYŚCI` [COLLECTION] -> ~76+ pozycji-artystow [COLLECTION], kazda
    `Nazwisko, Imie` linkujaca do kolekcji custom artysty. Artysci sa **posortowani
    alfabetycznie** po nazwisku. Rodzic to **`ARTYŚCI`**, nie `Katalog`.
  - **Skrypt:** `python add_artist_to_menu.py "Nazwisko, Imie" [--create-collection]`
    - znajduje/tworzy kolekcje custom o tym tytule i dodaje ja do menu pod `ARTYŚCI`
    (wstawienie alfabetyczne). Wymaga sesji ze scope nawigacji.
- **Translations API (NOWE):**
  - `get_translatable_resource(shop, token, resource_gid)` - lista pol mozliwych do
    tlumaczenia + `digest` per pole (wymagane do `translationsRegister`).
  - `register_translations(shop, token, resource_gid, locale, fields)` -
    `translationsRegister` GraphQL z gotowymi `TranslationInput`-ami.
  - `get_product_options_with_gids(shop, token, product_gid)` - GraphQL
    `product.options { id name optionValues { id name } }`. Potrzebne, bo
    nazwy opcji wariantow (`Kolor`/`Rozmiar`/`Rodzaj drewna`) i ich wartosci
    (`Czarny`/`Sosna`/`Dąb`/...) sa **odrebnymi** translatable resources
    (`ProductOption`, `ProductOptionValue`) - kazdy ma wlasny GID i wymaga
    osobnego `translationsRegister` per locale.
- **WAZNE - SEO meta na Product (nie na metafieldach!):**
  - SEO `meta_title` / `meta_description` w Shopify Translations API to klucze
    bezposrednio na zasobie `Product` - to JE czyta aplikacja Translate & Adapt
    oraz storefront przy renderowaniu `<title>`/`<meta name="description">` na rynkach.
  - Stara droga (tlumaczenie metafieldow `global.title_tag` / `global.description_tag`)
    NIE dziala i zostala wycieta z `push_product_translations` w `create.py`.
- **Tlumaczenia sekcji 'SZCZEGOLY' w body_html - statyczny slownik:**
  - `Komponenty/dodajobraz/body_i18n.py` - mapping
    `BODY_LABELS_I18N` (naglowek + 10 etykiet pol + wartosc 'Typ' per locale)
    oraz `COMMON_VALUE_TRANSLATIONS` (typowe wartosci faktograficzne PL ->
    6 jezykow: techniki malarskie, gatunki, nurty, szkoly, formy, epoki/wieki,
    miasta, kraje, 'Nieznana').
  - `body_labels(lang)` - dict etykiet dla locale (fallback na PL).
  - `translate_field_value(value_pl, lang)` / `translate_field_value_or_pl(...)` -
    tlumaczenie z obsluga wieloczlonowych wartosci (separatory ',', '/', ';';
    np. `'Düsseldorf / Ostenda'` (PL) -> `'Düsseldorf / Ostende'` (FR);
    `'Romantyzm/Realizm, szkoła düsseldorfska'` (PL) ->
    `'Romantisme/Réalisme, École de Düsseldorf'` (FR)).
  - `html_template.build_body_html(..., lang='fr')` przyjmuje locale - naglowek
    'SZCZEGOLY' i 10 etykiet w sekcji prawej kolumny renderowane sa po obcemu.
    `lang='pl'` to default (kompatybilnosc wsteczna).
- **Lokalizowane fakty - pierwszenstwo zrodel:** w `push_product_translations`
  wartosci pol faktograficznych dla obcego locale wybierane sa wg priorytetu:
    1) blok `tlumaczenia.<lang>` z LLM (`data_powstania`, `miejsce_powstania`,
       `technika`, `gatunek`, `nurt`, `forma` jako stringi),
    2) statyczny slownik `body_i18n.translate_field_value`,
    3) oryginalna polska wartosc (lepsze niz puste pole).
  - `prompt_builder.TRANSLATION_KEYS` rozszerzone o 6 nowych pol (powyzej);
    walidator `_normalize_translations` przyjmuje je jako stringi i strippuje.
- **Tlumaczenia opcji wariantow - statyczny slownik:**
  - `Komponenty/dodajobraz/options_i18n.py` - mapping
    `OPTION_NAME_TRANSLATIONS` (Kolor/Rozmiar/Rodzaj drewna) i
    `OPTION_VALUE_TRANSLATIONS` (Czarny/Brąz/Jasny Brąz/Ciemny Brąz/
    Sosna/Dąb/Buk/Jesion/Orzech/Biały/Złoty/Srebrny/Szary).
  - Wartosci typu `S/L/XL/XS/XXL` oraz wymiarowe `50x70`, `70x100` sa
    pass-through (rejestrujemy je w Translations API z ta sama wartoscia,
    zeby Shopify mial wpis tlumaczenia, a nie pusty backstop).
  - `push_option_translations(product_gid, languages, logger)` w `create.py`
    pushuje tlumaczenia opcji + wartosci na 6 jezykow (en/de/fr/es/nl/it).
    Wywolywane automatycznie po `push_product_translations` przy publikacji
    nowego produktu i przy update istniejacego.
  - **Brak tlumaczenia w slowniku** -> ostrzezenie w logu, polski oryginal
    zostaje na froncie. Dopisz brakujaca pozycje do `options_i18n.py`.
- **Backfill istniejacych produktow:**
  - `cursor-api/scripts/backfill_option_translations.py` - re-pushuje tlumaczenia
    opcji wariantow dla wszystkich produktow `vendor=Giclee Art` (bez LLM).
    Idempotentne; uruchamiac przy zmianie slownika `options_i18n.py`.
  - `cursor-api/scripts/backfill_seo_meta_translations.py` - dla produktow ze
    starym SEO na metafieldach `global.*` zapisuje polskie SEO jako fallback
    we wszystkich 6 jezykach (lepsze niz puste pole; dopiero kolejna
    re-publikacja produktu z `dodajobraz` da prawidlowe tlumaczenia z LLM).
    Tryb raportowy: `--no-fallback`.
  - `cursor-api/scripts/backfill_body_translations.py` - bierze juz pushniety
    body_html w kazdym jezyku obcym (z polskim naglowkiem 'SZCZEGOLY' i polskimi
    etykietami z poprzedniej wersji aplikacji), i lokalizuje go: podmienia
    naglowek/etykiety/wartosci 'Typ' na docelowe (z `body_i18n.body_labels(lang)`)
    + tlumaczy wartosci faktograficzne pod etykietami (technika/gatunek/nurt/
    forma/data_powstania/miejsce_powstania) przez `body_i18n.translate_field_value_or_pl`.
    Akapity opisu zostaja nietkniete. Tryb diagnostyczny: `--dry-run`.
- **Markets API (NOWE):**
  - `list_markets(shop, token)` - lista rynkow z catalogs + priceList GIDs.
  - `update_price_list_percentage_adjustment(shop, token, price_list_id, percent)` -
    `priceListUpdate` z `parent.adjustment.{type, value}` (PERCENTAGE_INCREASE/DECREASE).
- **Orders API (NOWE):**
  - `iter_orders_since(shop, token, updated_at_min=..., financial_status="paid", status="any")` -
    REST `/orders.json` z paginacja Link-header. Uzywane przez komponent `produkcja`
    do pollingu zamowien. **Wymaga scope `read_orders`**.
- **Blog/Article API** (komponent `blog`, plik `Komponenty/blog/shopify_blog.py` - reuzywa
  `graphql`, `rest_*`, `register_translations` z `dodajobraz/shopify_client.py`):
  - `list_blogs(shop, token)` - REST `/blogs.json` (zwykle 1 blog "News").
  - `list_articles(shop, token, blog_id)` - paginacja 250 per request, `since_id`.
  - `list_all_articles(shop, token)` - artykuly ze wszystkich blogow z dodanymi polami
    `_blog_id`, `_blog_handle`, `_blog_title` (dla GUI).
  - `create_article(shop, token, blog_id, ...)` - REST `POST /blogs/{id}/articles.json`
    z body_html, summary_html, tags, author, image (url ALBO base64 attachment), metafields
    SEO (`global.title_tag`, `global.description_tag`), `published=True`.
  - `_build_image_payload(image_src, alt)` - automatyczna detekcja URL vs lokalny plik
    (lokalny -> `base64` + `filename`, max 20 MB, walidacja MIME `image/*`).
  - `register_article_translations(shop, token, article_id, locale, ...)` - wrapper na
    `register_translations` (GraphQL `translationsRegister`) dla Article z keys:
    `title`, `body_html`, `summary_html`, `meta_title`, `meta_description`.
  - `article_admin_url(shop, blog_id, article_id)` / `article_storefront_url(...)` - URL-e.
  - `get_shop_primary_domain(shop, token)` - GraphQL `{shop{primaryDomain{host}}}` do
    budowy storefront URL (np. `gicleeart.eu/blogs/news/<handle>`).

---

## 9a. KOMPONENT `blog` - Marketing / publikacja postow

**Cel:** generowanie postow na bloga w 7 jezykach (PL bazowy + 6 tlumaczen),
zarzadzanie propozycjami tematow, podglad opublikowanych postow.

**Sekcja w launcherze:** `Marketing` (razem z `cenyMarketing`) - patrz `giclee_app/launcher.py`
w `_SECTIONS`.

### Hierarchia ekranow (mode=inline, bez spawn procesu)

```
Blog (main)                                     <- 5 kafelkow
├── Generator tresci       (Toplevel)           <- prompt + paste + send (+ wczytaj HTML)
├── Import z HTML          (Toplevel)           <- plik podgladu AI -> Shopify
├── Generator tematow      (Toplevel)           <- prompt + paste + save 10 propozycji
├── Propozycje tematow     (sub-view)           <- lista z PPM (kopiuj/generuj/usun)
└── Posty na blogu         (sub-view)           <- obecne posty: auto-fetch + dwuklik -> storefront
```

### Flow Generator tresci (`generator_tresci.py`)

1. Uzytkownik wpisuje temat + opcjonalnie wskazuje **obrazek** (URL https:// ALBO lokalny plik przez file picker).
2. Klik **"Prompt dla Opus"** lub **"Prompt dla GPT"**:
   - Buduje prompt przez `prompts.build_content_prompt_opus/gpt(topic, image_url, existing_titles)`,
     gdzie `existing_titles` pochodzi z `storage.load_articles_cache()` (zeby LLM nie duplikowal tematyki).
   - Prompt jest AUTO-KOPIOWANY do schowka systemowego (`dlg.clipboard_clear/append/update`) + pokazany w textarea.
3. Uzytkownik wkleja prompt do Cursor/Claude/GPT i wraca z JSON-em.
4. Klik **"Wklej odpowiedz ze schowka"** -> auto-paste do response textarea.
5. **"Sprawdz odpowiedz"** -> `prompts.parse_content_response(raw)` - rzuca ValueError gdy brak pola
   `languages` lub brakuje `title`/`body_html` w ktoryms z 7 locale. Uaktualnia checkboxy jezykow.
6. **"Podglad w przegladarce"** -> `preview.build_preview_html(parsed)` zapisuje
   `Komponenty/blog/data/preview.html` (zakladki per jezyk, Bodoni Moda + Cormorant Garamond jak motyw
   Horizon, liczniki znakow SEO) i otwiera w domyslnej przegladarce.
   **Alternatywnie:** **"Wczytaj plik HTML"** -> `html_import.parse_preview_html_file(path)` - odwrotna
   operacja: plik podgladu (zapisany przez AI lub z przegladarki) wraca do struktury `parsed` gotowej
   do wysylki bez ponownego wklejania JSON.
7. Uzytkownik moze **odznaczyc jezyki** (checkboxy) ktorych nie chce publikowac.
8. **"Wyslij na bloga"**:
   - `publish.publish_parsed_article(...)` - wspolna logika: PL jako baza + image (URL lub base64 attachment),
     tlumaczenia, opcjonalnie `mark_topic_used`, refresh cache.

### Flow Import z HTML (`import_html.py` + `html_import.py`)

1. Kafelek **Import z HTML** (lub przycisk w Generatorze tresci).
2. Wybor pliku `.html` - oczekiwany format: wyjscie z **Podglad w przegladarce** (panele `#panel-pl`,
   `#panel-en`, ... z tytulem, summary, body, SEO, tagami).
3. Parser `html_import.parse_preview_html` buduje ten sam slownik co `prompts.parse_content_response`.
4. Podglad / wybor jezykow / obrazek / autor -> **Wyslij na bloga** (`publish.publish_parsed_article`).

### Flow Generator tematow (`generator_tematow.py`)

1. Przy otwarciu - `shopify_blog.list_all_articles` w tle -> cache + lista tytulow.
2. Prompt Opus/GPT: **obecne tytuly** + **juz zapisane propozycje** jako dwa bloki "nie duplikuj".
3. LLM zwraca `{"proposals": [{title, reason, keywords}, x10]}`.
4. **"Zapisz propozycje"** -> `prompts.parse_topics_response(raw)` + `storage.add_topics(items)`.
   Deduplikacja po znormalizowanym (lowercase, strip) tytule.

### Propozycje tematow (`propozycje_tematow.py`)

- Treeview: status (✓/•), title, reason, keywords. Wykorzystane (`used=True`) maja overstrike font.
- **PPM (Button-3)** menu: Kopiuj temat / Kopiuj temat+uzasadnienie / Generuj tresc posta /
  Oznacz (nie)wykorzystany / Usun.
- "Generuj tresc" -> `open_content_generator(root, initial_topic=t.title, topic_id=t.id)` -
  po udanej publikacji temat zostaje przekreslony automatycznie.

### Obecne posty (`obecne_posty.py`)

- **Auto-fetch** przy wejsciu na ekran: najpierw cache (szybki render), potem background thread -> refresh.
- Treeview: status (📄/✏️), title, blog, author, published_at, tags. Sort DESC po dacie publikacji.
- Dwuklik / Enter -> `article_storefront_url(...)` w przegladarce.
- PPM: Otworz storefront / Admin / Kopiuj tytul / Kopiuj body_html.

### Persystencja (`storage.py`, `Komponenty/blog/data/`)

- `topics.json`: `{"topics": [TopicProposal, ...]}` gdzie `TopicProposal = {id, title, reason, keywords, created_at, used}`.
- `articles_cache.json`: `{"fetched_at": int, "articles": [...]}` - snapshot z Shopify.
- `preview.html`: regenerowany za kazdym kliknieciem "Podglad w przegladarce".

### Prompty (`prompts.py`)

- Dwa warianty per flow: **Opus** (luzniejsze, code fence `json ...`, literacki jezyk) i
  **GPT** (twardsze rygory: "zwroc WYLACZNIE JSON bez code fences, bez komentarzy").
- `SHOP_CONTEXT` - staly blok kontekstowy o GicleeArt, dolaczany do kazdego prompta.
  Zawiera opis **OBU galezi dzialalnosci** sklepu:
  1. **Reprodukcje klasykow malarstwa** (Monet, Van Gogh, Vermeer, Klimt, polscy kolorysci itd.)
     drukowane giclee na plotnie. Grupa: milosnicy sztuki, dekoracja wnetrz (klasyka/boho/skandynawski/glamour).
  2. **Custom print - wydruk z wlasnego zdjecia** przez edytor z live mockupem na stronie
     (klient wgrywa foto, dopasowuje kadr, widzi podglad na scianie, drukujemy giclee).
     Grupa: klienci indywidualni (prezenty personalizowane, sesje slubne/rodzinne/portretowe, pamiatki z podrozy),
     fotografowie (wydruki dla klientow), male firmy.
  - Ton (obie galezie): elegancki, ciepy, merytoryczny, bez napuszenia.
- **Dopasowanie CTA do galezi** (wymuszone w regulach promptu tresci, zasada #11):
  - Temat klasyka/artysci/reprodukcje -> CTA o reprodukcjach mistrzow.
  - Temat fotografia/personalizacja/prezent ze zdjeciem -> CTA o edytorze z mockupem.
  - Temat mostkujacy -> CTA laczaca oba produkty (ale krotko).
- **Generator tematow** ma narzucona **proporcje 10 propozycji**: ~4-5 reprodukcje klasyki
  + ~4-5 custom print / foto na zamowienie + 1-2 tematy mostkujace.
- Zasady tresci: 700-1100 slow body per jezyk, czysty HTML (tylko `<p>/<h2>/<h3>/<ul>/...`),
  3 akapity PL + naglowki H2, SEO title 55-60 znakow, SEO desc 140-158, tagi 5-8.
- Kategorie: `"historia sztuki" | "technika" | "kierunki i style" | "artysci" | "aranzacja wnetrz" | "porady zakupowe" | "custom print" | "foto na plotnie"`.

### Mapping keys tlumaczen Article (Shopify)

| Pole w JSON LLM          | Shopify translations key | REST article field            |
|--------------------------|--------------------------|-------------------------------|
| `title`                  | `title`                  | `article.title`               |
| `body_html`              | `body_html`              | `article.body_html`           |
| `summary_html`           | `summary_html`           | `article.summary_html`        |
| `seo_title`              | `meta_title`             | metafield `global.title_tag`  |
| `seo_description`        | `meta_description`       | metafield `global.description_tag` |
| `tags`                   | (nie tlumaczone)         | `article.tags` (CSV)          |

Tagi NIE sa tlumaczone w Shopify per locale - podobnie jak w produktach. Rozwiazanie
podobne do produktow: alternatywa to dodanie ALWAYS_TAGS_\<LANG\> per jezyk do tagow
artykulu (na razie nie zrobione - do rozwazenia gdy blog urosnie).

---

## 9b. KOMPONENT `socialmedia` - Marketing / posty na social

**Cel:** generowanie postow na 6 platform social (IG Feed/Stories/Reels, FB, TikTok,
Pinterest) w 2 jezykach (PL + EN) + lokalny planer postow (kolejka, statusy, eksport CSV).

**Publikacja:** planer i generator nadal moga byc **reczne** (kopiuj do Meta Suite).
Dodatkowo sa **Cykl** i **Dodaj post** z publikacja przez Meta Graph API (tokeny w
`data/cykl/meta_credentials.json`). Pinterest / TikTok / telefon — bez API w tym repo.

### Dodaj post + przycisk Id socjali

- **Dodaj post:** zakladki FB PL / FB EU / IG PL / IG EU (`manual_post.build_manual_post_ui`;
  opcjonalnie `open_manual_post_wizard` = osobne okno) — upload CDN Shopify,
  potem `meta_publisher`. Na **Facebooku** mozliwy jest tez post **tylko z tekstem**
  (`POST /{page-id}/feed`); **Instagram** nadal wymaga co najmniej jednego obrazu (API).
  Link **Profil:** jest klikalny; URL FB buduje sie preferencyjnie
  jako `https://www.facebook.com/{page_id}` z creds (`platforms_cykl.public_profile_url`).
- **Id socjali:** przycisk na ekranie wyboru kanalu — lista Page ID / Instagram user ID
  + linki do profili (te same credentiale co Cykl).

### Platformy (`platforms.py`)

Kazda platforma ma dataklase `Platform` z polami:
- `caption_limit` (IG: 2200, FB: 63206, Pinterest: 500, Stories: 200).
- `hashtag_limit` (IG/TikTok: 30, FB: 10, Pinterest: ~0).
- `recommended_hashtags` (sugestia dla LLM).
- `recommended_words` (zakres dlugosci caption).
- `format_hint` (1:1 / 9:16 / 4:5 / 2:3 ...).
- `tone` + `structure` (gotowe instrukcje dla LLM jak pisac pod dana platforme).

### Locked hashtagi (`hashtag_library.py`)

Staly zestaw hashtagow **marki** zawsze dolaczany do kazdego posta (osobno PL vs EN):
- PL: `#gicleeart #reprodukcjagiclee #obrazynaplotnie #sztukawdomu #dekoracjascian`.
- EN: `#gicleeart #gicleeprint #canvasart #fineartprint #walldecor`.
Plus `SUGGESTED_THEMES_PL/EN` - pula 15-17 hashtagow motywicznych do wyboru przez LLM.

### Flow Generator tresci (multi-platform od v2)

1. Uzytkownik wybiera:
   - **Platformy - multi-select checkboxami** (6 opcji: IG Feed/Stories/Reels, FB, TikTok, Pinterest).
     Mozna zaznaczyc dowolna liczbe platform.
   - **Jezyk** (pl/en).
   - **Tryb**: `single` (pojedynczy post) albo `series` (seria 2-7 postow - TYLKO przy 1 platformie).
2. Wpisuje temat, opcjonalnie link docelowy i dodatkowy kontekst.
3. Klik **"Prompt dla Opus/GPT"** - budowanie zalezy od kombinacji:
   - **1 platforma + single**: `build_post_prompt_*` (klasyk).
   - **1 platforma + series**: `build_series_prompt_*` (N postow z lukem narracyjnym).
   - **N platform + single**: `build_multi_post_prompt_*` (JEDEN prompt zwraca N wersji, kazda dostosowana do reguly swojej platformy - rozne dlugosci, hashtagi, struktury).
   - **N platform + series**: automatyczne przelaczenie na `single` (ostrzezenie dialogu) - eksplozja kombinacji byla niepraktyczna.
   - Prompt zawsze zawiera `SHOP_CONTEXT` (2 galezie), `locked_hashtags`, `SUGGESTED_THEMES` per jezyk.
   - Auto-kopiuje do schowka.
4. Uzytkownik wkleja do Claude/GPT -> wraca z JSON-em (format zalezny od trybu).
5. **"Sprawdz i podglad"** wywoluje odpowiedni parser:
   - `parse_post_response` (single) -> `{platform, language, topic, post: {...}}`
   - `parse_multi_post_response` (multi) -> `{language, topic, platforms: {code: {post: {...}}}}`
   - `parse_series_response` (series) -> `{platform, language, topic, series_meta, posts: [...]}`
   - Toplevel z Notebook: **1 zakladka per platforma** (multi) lub **1 zakladka per post** (series).
   - Kazda zakladka: caption (licznik znakow + ostrzezenie >limit), hashtagi (licznik), on_screen_text (Reels/TikTok), music_hint, image_hint, sciezka obrazu (file picker), link, data planowana, notatki.
6. **"Zapisz do planera"**: kazdy post trafia do `posts.json`; dla serii wspolny `series_id`;
   dla multi-platform **N osobnych postow** (kazda platforma to osobny wpis w kolejce).

**Waga dla integracji z `zadania`**: `open_content_generator(initial_platforms: list[str], ...)` - zadania z kanalami `["ig_feed","fb","pinterest"]` otwieraja generator z pre-zaznaczonymi 3 checkboxami. Po zapisaniu, wszystkie posty (kilka) dostaja `from_task_id` i task dostaje `linked_post_ids = [id1, id2, id3]`.

### Flow Planer postow

- Inline sub-view z Treeview: status | data | platforma | jezyk | temat | caption (preview) | seria.
- Filtry: platforma / jezyk / status.
- Statusy: `pending` / `in_progress` / `done` / `skipped` - dedykowane kolory + overstrike dla done/skipped.
- Dwuklik / PPM "Edytuj..." -> Toplevel z wszystkimi polami posta.
- PPM: **Kopiuj caption+hashtagi** / **Kopiuj caption** / **Kopiuj hashtagi** /
  **Otworz obraz** / **Generuj seria z tego tematu** (otwiera generator w mode=series
  z pre-wypelnionym tematem) / **Zmien status** / **Usun**.
- **Eksport CSV** (nazwa pliku `socialmedia_posts.csv`, separator `;`, UTF-8 BOM -
  kompatybilne z Excel PL i Meta Business Suite import).

### Persystencja (`storage.py`, `Komponenty/socialmedia/data/`)

- `posts.json`: `{"posts": [Post, ...]}`. Post ma id (uuid12), platform, language,
  caption, hashtags, image_path, scheduled_at, status, series_id, from_task_id (link do zadan), ...

---

## 9c. KOMPONENT `zadania` - Marketing / organizer z LLM

**Cel:** inteligentny planer miesiecznych zadan marketingowych - LLM generuje plan
na bazie: (a) nowych produktow/kolekcji/autorow w Shopify, (b) nadchodzacych swiat
per rynek, (c) juz zaplanowanych zadan (zeby nie duplikowal).

### Sygnaly (`shopify_signals.py`)

Funkcja `aggregate_signals(days=14)` zwraca slownik z:
- `new_products`: produkty z `created_at` nowszym niz N dni (iter_all_products + filter lokalny).
- `new_artists`: autorzy (z wzorca "Autor - Tytul") ktorych mamy w nowych produktach.
- `new_collections`: smart + custom kolekcje z ostatnich 30 dni (`/smart_collections.json`, `/custom_collections.json`).
- `products_without_image` + `unpublished_products`: zadania administracyjne "urgent".

Helper `format_signals_for_prompt(signals)` buduje krotki tekst do wklejenia w prompt LLM
(pierwsze 15 produktow, 10 autorow, 10 kolekcji - zeby nie przerzucic kontekstu LLM).

### Kalendarz swiat (`holidays.py`)

Hardcodowana lista `EVENTS: list[HolidayEvent]` (dane rok 2026-2028) zawiera:
- Global: Nowy Rok, Walentynki, Wielkanoc (data ruchoma, wpisywana recznie per rok),
  Dzien Matki (roznie per rynek), Black Friday, Cyber Monday, Boze Narodzenie.
- PL: Dzien Babci/Dziadka, Dzien Matki 26.05, Dzien Kobiet, Mikolajki.
- DE/NL/IT/ES/FR: lokalne (Sinterklaas, Ferragosto, Dia de la Madre, Vatertag itd.).

Kazde wydarzenie ma `lead_time_days` - ile wczesniej zaczynac kampanie (np. Walentynki=21d,
Boze Narodzenie=45d). LLM w prompcie jest instruowany zeby rozkladac kampanie od
`data_swieta - lead_time_days`.

**UWAGA**: Po kwietniu 2028 trzeba dopisac nowe lata do `_RAW` w `holidays.py` -
inaczej `events_upcoming` zwroci pusta liste.

### Flow Generator zadan

1. Przy otwarciu dialogu: w tle `aggregate_signals(days=14)` + `holidays.events_upcoming(days_ahead=44)`.
2. UI pokazuje podsumowanie sygnalow w textarea (read-only).
3. Uzytkownik wybiera: **okres** (7/30/90 dni) + **liczba zadan** (5-40).
4. Klik **"Prompt dla Opus/GPT"**:
   - `prompts.build_tasks_prompt_*(signals_text, holidays_text, planned_text, target_count, period_label)`.
   - Prompt zawiera 10 zasad planowania: rozlozenie w czasie, rozklad miedzy kanalami
     (nie 10x IG pod rzad), 50/40/10 balance galezi (klasyka/custom/bridge),
     20-30% EN, lead_time dla swiat, priorytety (urgent dla produktow bez obrazka), itd.
   - Auto-kopia do schowka.
5. Wklejamy odpowiedz -> **"Zapisz zadania"** -> `parse_tasks_response` + dedup po
   `(title, due_date)` -> `storage.add_tasks(...)`.

### Model Task (v2) - multi-channel, multi-market, tlumaczenia

Pola Task (JSON w `tasks.json`):
- `channels: list[str]` - jedno zadanie moze dotyczyc kilku kanalow (np. `["ig_feed","fb","pinterest"]`).
- `languages: list[str]` - lista jezykow contentu (`pl`, `en`, `de`, `fr`, `es`, `nl`, `it`).
- `target_markets: list[str]` - rynki Shopify (`pl`, `eu`, `fr`, `de`, `es`, `nl`, `it`).
- `description_translations: dict[str, str]` - dict `{lang: tlumaczenie}` dla opisow
  zadan celujacych w zagraniczne rynki. Klucz `pl` niedozwolony (bo description to PL).
- Wsteczna kompatybilnosc: stary format (`channel: str`, `language: str`) jest parsowany -
  `_from_dict` konwertuje do list. `language: "both"` -> `languages: ["pl","en"]`.
- Property `task.channel` i `task.language` zwracaja pierwszy element listy (dla starszego kodu).

### Flow lista zadan (`view.py`)

- Treeview kolumny: Status | Termin | Priorytet | Kanaly | Jezyki | Rynki | Tytul | Zrodlo | Post.
  - **Priorytety po polsku**: `Pilne / Wysoki / Zwykly / Niski` (etykiety z `storage.PRIORITY_LABELS_PL`).
  - Status tez po polsku: `Oczekuje / W toku / Zrobione / Pominiete` (z ikonka).
  - Kanaly: pierwsze 3 sklejone przecinkiem + `"+"` jesli wiecej (np. `📷 IG Feed, 📘 Facebook, 📌 Pinterest`).
  - Jezyki: flagi emoji 🇵🇱 🇬🇧 🇩🇪 🇫🇷 🇪🇸 🇳🇱 🇮🇹.
  - Rynki: kody upper (`PL EU DE`) lub `—` jesli pusto.
- **Sortowanie kolumn**: klik na naglowek toggluje asc/desc, pokazuje strzalke ▲/▼.
  Robione przez helper `Komponenty/_shared/tree_sort.py:attach_sortable_headings`.
- Filtry: status / kanal / jezyk / rynek / priorytet.
- Action bar ma szybkie przesuwanie terminow:
  - `📅 Wszystkie -1 dzien` i `📅 Wszystkie +1 dzien` przesuwaja `due_date` dla wszystkich zadan
    z poprawna data ISO (`YYYY-MM-DD`).
  - `🎯 Zaznaczone -1 dzien` i `🎯 Zaznaczone +1 dzien` przesuwaja pierwszy zaznaczony task.
  - Zadania bez terminu lub z niepoprawna data sa pomijane (globalnie) albo pokazywany jest warning
    (dla trybu zaznaczonego).
- **Statystyki w naglowku** (po prawej): `Tydzien: 2/5 | Miesiac: 8/18 | ⚠ 3 po terminie`
  (ile done / ile planned; overdue = pending + termin w przeszlosci).
- **"Overdue"** tag - pending zadania po terminie czerwone ⚠.
- Domyslne sortowanie (do pierwszego kliku kolumny): status (in_progress > pending > done > skipped)
  -> priorytet (urgent > high > normal > low) -> termin.
- PPM:
  - **"✍️ Generuj post"** - jesli w kanalach jest `blog` -> otwiera `Komponenty.blog.generator_tresci`.
    Inaczej jesli sa kanaly social -> otwiera `Komponenty.socialmedia.generator_tresci.open_content_generator(initial_platforms=[ig_feed, fb, ...], ...)` z WSZYSTKIMI kanalami social z zadania.
    - Task przechodzi na `in_progress`.
    - Po zapisaniu postow, callback `_on_post_saved_from_task` laczy **wszystkie** posty
      z ostatnich 60 sekund z zadaniem (wazne przy multi-platform!).
  - **"Edytuj..."** - Toplevel z checkboxami per kanal/jezyk/rynek + pola tlumaczen
    (dynamicznie pokazywane dla kazdego zaznaczonego jezyka innego niz pl).
  - **"Duplikuj"** - tworzy kopie z terminem +7 dni.
  - **"Kopiuj"** cascade: Temat / Opis PL / Opis DE / Opis EN / ... (pozycje dla kazdego
    jezyka w `description_translations`).
  - **"Zmien status"** / **"Usun"**.

### Persystencja (`storage.py`, `Komponenty/zadania/data/`)

- `tasks.json`: `{"tasks": [Task, ...]}` (v2 model z multi polami).
- `signals_cache.json`: ostatni snapshot Shopify (fallback gdy API nie dziala).
- `reminders.json`: `{"monthly_plan": "2026-04"}` - zapis ze dialogu miesiecznego pokazano dla YYYY-MM.

### Monthly Reminder (launcher)

Launcher (`giclee_app/launcher.py`) po starcie odpala `_check_monthly_reminder()` (1.5s delay)
ktory:
1. Wczytuje `reminders.json` z `Komponenty/zadania/data/`.
2. Sprawdza czy dzis jest w pierwszych 5 dniach miesiaca (`today.day <= 5`).
3. Jesli tak i biezacy YYYY-MM != zapisany `monthly_plan` -> pokazuje `messagebox.askyesno`
   zachecajace do wygenerowania planu na nowy miesiac.
4. Zapisuje biezacy YYYY-MM jako `monthly_plan` (niezaleznie od odpowiedzi user-a,
   zeby nie spamowac). Jesli user klika "Tak" -> otwiera `open_tasks_generator(root)`.
5. Okno zadan moze byc pominiete / zamkniete - reminder nie pokaze sie ponownie w tym miesiacu.

---

## 9d. KOMPONENT `produkcja` - Zamowienia i status produkcji

**Cel:** sledzenie statusu zamowien (wydruk, ramka z utwardzaniem, wysylka)
ze szczegolowym live countdownem 72h utwardzania farby.

**Sekcja w launcherze:** `Zamowienia` (z `obrazy`, `kalkulacja`).

### Integracja Shopify (polling)

- **Scope wymagany:** `read_orders` (dodany do [shopify.app.toml](shopify.app.toml)
  i `.env`). Po zmianie scope: `cd cursor-api && npm run deploy -- --allow-updates && npm run oauth`.
- **Polling:** launcher (`giclee_app/launcher.py::_poll_orders_from_shopify`) co 5 min
  wola `orders_sync.sync_orders()` w tle. Pierwszy sync 30s po starcie.
- **Manualny sync:** przycisk **↓ Pobierz z Shopify** w toolbarze produkcji.
- **Mapowanie:** kazdy `line_item` z kazdego order = 1 rekord produkcji (dedup po
  `shopify_order_id + shopify_line_item_id`).
  - `client` = `customer.first_name + last_name`.
  - `tytul_obrazu` = `line_item.title` (po rozdzieleniu "Artysta - Tytul" bierze czesc po myslniku).
  - `ramka_drewno`, `ramka_rozmiar`, `ramka_kolor` = rozklad `line_item.variant_title`
    jak w sklepie (separator ` / ` miedzy opcjami). `ramka_wariant` = laczona etykieta
    (do CSV / wyszukiwania). Stary skrot jednym stringiem: [frame_variant.py](cursor-api/Komponenty/produkcja/frame_variant.py).
  - `adres_wysylki` = sklejony `shipping_address`.
- **State:** `Komponenty/produkcja/dane/sync_state.json` z `last_sync_iso` - przy kolejnej
  sync pobieramy tylko `updated_at_min=last_sync_iso`.
- **Klient Shopify:** `iter_orders_since` w
  [shopify_client.py](cursor-api/Komponenty/dodajobraz/shopify_client.py) (paginacja Link-header).

### Live countdown utwardzania

- **72h sekundowa precyzja.** W modelu danych `data_pomalowania` to ISO8601 z czasem
  (np. `"2026-04-18T12:34:56"`). Migracja starego formatu `"YYYY-MM-DD"` robiona w `_load_db`.
- **Odswiezanie co 1s** (`_tick_countdown`) - aktualizuje TYLKO label countdown + progressbar
  (bez re-renderu detalu, zeby nie zabijac UI).
- **Kolor tla:** czerwony (<24h), pomaranczowy (24-48h), zielony (>48h / utwardzone).
- **Format:** `"2d 05g 43m 12s"` (albo krotszy gdy <1d).
- Sekcja **Ramka** pokazuje tez `ttk.Progressbar` 0-100% (procent uplynietego czasu).
- **Pomin schniecie:** przycisk w detalu (gdy licznik > 0) ustawia `pomin_schniecie: true` —
  zamowienie traktowane jak po 72h (mozna zaznaczyc Zlozone). Przy ponownym zaznaczeniu
  „Ramka pomalowana” lub cofnieciu kroku malowania flaga jest zerowana. To samo pole
  czyta [web_server.py](cursor-api/Komponenty/produkcja/web_server.py) przy odblokowaniu finalizacji.

### GUI

- **Sortowanie kolumn** (klik naglowka): id / klient / drewno / rozmiar / kolor / postep / status.
- **Filtr tekstowy** nad lista - szuka w kliencie, tytule, numerze Shopify, notatce.
- **Filtry kolumn (substring):** drewno / rozmiar / kolor - lacza sie z pozostalymi filtrami.
- **Filtr statusu:** Aktywne / Wszystkie / Zrealizowane / Opoznione (>14 dni nie-wyslane).
- **Postep w liscie:** kolumna `■■■□□` z 5 glownych krokow.
- **Alerty overdue:** czerwone tlo + prefix "OPOZNIONE" w statusie.
- **Eksport CSV:** przycisk `⬇ Eksport CSV` zapisuje biezaca liste (po filtrach)
  w UTF-8-BOM z separatorem `;`.
- **Statystyki:** okno z liczbami (lacznie, aktywne, zakonczone, opoznione, wyslane 7 dni,
  sredni wiek aktywnych, segmenty wydruk / po wydruku bez pakowania) - modul
  [stats.py](cursor-api/Komponenty/produkcja/stats.py).
- **Etykiety warsztatowe (HTML):** zapis pliku do druku z przegladarki (PDF) -
  [label_html.py](cursor-api/Komponenty/produkcja/label_html.py).
- **Shopify w detalu:** miniatura wariantu (API: `get_variant_featured_image_url` w
  [shopify_client.py](cursor-api/Komponenty/dodajobraz/shopify_client.py); pola
  `shopify_variant_id`, `shopify_product_id`, `shopify_image_url` w zamowieniu po sync).
- **Link do Admin:** przycisk otwiera `https://admin.shopify.com/store/<subdomain>/orders/<id>`
  ([shopify_links.py](cursor-api/Komponenty/produkcja/shopify_links.py)) gdy jest sesja OAuth.
- **Przypomnienie o trackingu:** przy ustawieniu kroku **Wyslane** lub potwierdzeniu wysylki
  bez numeru przesylki pokazuje sie ostrzezenie.
- **Panel www** ([web_server.py](cursor-api/Komponenty/produkcja/web_server.py)): na kartach
  i w detalu opcjonalnie link Admin + obrazek z `shopify_image_url`.

### Persystencja (`dane/`)

- `zamowienia.json`: `{"next_id": N, "orders": [Order, ...]}`. Model zamowienia
  (z migracja wstecz): `_new_order_template` w [view.py](cursor-api/Komponenty/produkcja/view.py)
  - opcjonalnie `shopify_variant_id`, `shopify_product_id`, `shopify_image_url`;
  `pomin_schniecie` (bool) — reczne pominiecie 72h utwardzania.
- `sync_state.json`: `{"last_sync_iso": "...", "last_added_count": N}`.
- Auto-save po kazdej zmianie pola / kroku.

---

## 9d2. KOMPONENT `kalkulacja` - Koszty produkcji ramek

**Cel:** natywny kalkulator kosztow produkcji (zamiast recznego Excela) — materialy,
marze, optymalizacja partii drewna, mix sprzedazy.

**Sekcja w launcherze:** `Zamowienia` (z `obrazy`, `produkcja`, `passepartout`, `kalkulacja`).

**Tryb:** `inline` — `Komponenty/kalkulacja/view.py`.

### Zrodlo danych

Import z `.xlsm` (`import_excel.py`) — arkusze: `CENNIK MATERIALOW`, `TABELA CEN WG MATERIALOW`,
`CENNIK`, `KALKULATOR KOSZTU DREWNA`. JSON w `Komponenty/kalkulacja/data/`.

### Logika

- **6 wariantow:** Sosna / Deb x A4 / A3+ / A2 (profil 20x20).
- **Koszt produkcji** = produkcja + wydruk + opakowanie (bez wysylki — jak kolumna N w CENNIK).
- **Cennik:** edytowalny narzut (%), marza (%) i cena sprzedazy — zsynchronizowane; zapis w `settings.json` → `variant_pricing` (bez cen z Excela). Domyslny narzut nowych wariantow: 250%.
- **Drewno:** optymalna partia = pierwsza, gdzie wspolczynnik H &lt; 0,2 (Excel `H7`).
- **Mix sprzedazy:** stala lista 6 wariantow; sprzedaz (sztuki) edytowalna lokalnie; udzial = sztuki / suma; ceny i zyski z kalkulatora.

**Powiazane:** `finanse` (legacy, ukryty w launcherze — otwiera zewnetrzny `GicleeArt3.xlsm`); docs:
[cursor-api/docs/komponenty/kalkulacja.md](cursor-api/docs/komponenty/kalkulacja.md).

---

## 9f. KOMPONENT `kpir` - Ksiega Przychodow i Rozchodow (JDG bez VAT)

**Cel:** samodzielne prowadzenie uproszczonej KPiR dla JDG zwolnionej z VAT, zintegrowanej z Shopify i fakturami bez VAT.

**Launcher:** sekcja `Finanse` > kafelek **KPiR** (oraz skrot z `ksiegowosc` > JDG — KPiR).

**Kod:** `Komponenty/kpir/` — `view.py` (dashboard + 9 ekranow), `models.py`, `storage.py` (JSON),
`shopify_service.py`, `invoice_integration.py`, `cost_service.py`, `fee_import.py` (CSV Stripe/PayPal),
`entry_detail.py` (szczegoly wpisu + historia zmian), `summary_service.py`, `export_service.py`.

**Integracje:**
- Zamowienia Shopify: `dokumentysprzedazy/shopify_orders.py` + NBP: `dokumentysprzedazy/nbp_service.py`
- Faktury bez VAT: `dokumentysprzedazy` (`invoices.json`) — regula: nie dubluj przychodu jesli jest faktura
- Widok zamowien w `dokumentysprzedazy/view.py` — sekcja „Ksiegowosc KPiR”

**Persystencja:** `Komponenty/kpir/dane/kpir.json`, `kpir_settings.json`; eksporty w `documents/exports/YYYY/MM/`.

**Testy:** `python -m Komponenty.kpir.verify_kpir`

**Placeholdery:** JPK_PKPIR (XML), roznic kursowych, pelny tryb DNR i ryczalt.

Docs: [cursor-api/docs/komponenty/kpir.md](cursor-api/docs/komponenty/kpir.md).

---

## 9e. KOMPONENT `socialmedia/cykl` - Automatyczny cykl 3 postow dziennie

**Cel:** codzienna automatyczna publikacja reprodukcji w 4 kanalach Meta:
- **FB PL** (https://www.facebook.com/GicleeArtPolska) + **IG PL** (https://www.instagram.com/gicleeart.polska/) - rynek polski.
- **FB EN** (https://www.facebook.com/GicleeArtEurope) + **IG EN** (https://www.instagram.com/gicleeart.europe/) - zagranica.

3 sloty dziennie (08:00 / 14:00 / 20:00 Europe/Warsaw, konfigurowalne w `config.json`),
1 obraz per slot, wiec dziennie 3 obrazy x 4 kanaly = 12 postow wyemitowanych.

**Sekcja w launcherze:** `Marketing` > `Social Media` > 3. kafelek "Cykl".

### Kolejka i jej logika

Kolejka budowana z **custom collections artystow** (tytul "Nazwisko, Imie",
patrz sekcja 4-5). Sort alfabetyczny po nazwisku:
- Achenbach -> Aivazovsky -> Chelminski -> ... -> Whistler.

Dla kazdego artysty wszystkie jego produkty w kolejnosci sort_order kolekcji.

**Flagi kontekstu** na kazdej pozycji (`CykleItem`):
- `is_first_of_artist` -> intro "Rozpoczynamy cykl z obrazami X".
- `is_last_of_artist` + `next_artist` -> outro "To ostatni obraz X, w kolejnym: Y".
- `is_new_artist` -> "Na stronie pojawil sie nowy artysta X!" (wyzsza priorytet niz is_first).
- `is_new_painting` -> "Dolozylismy nowy obraz do kolekcji X".

**Delta detection** (`queue_builder.detect_deltas` + `apply_deltas`):
- Porownuje biezacy stan kolekcji w Shopify z `generation_state.artists_snapshot`.
- Nowy artysta: wciska sie po ostatnim pending obrazie AKTUALNEGO artysty.
- Nowe obrazy u istniejacego artysty: wciskaja sie po jego obecnej kolce.
- Po apply: `scheduler.reassign_from_now` przelicza sloty.

### Flow Content Generator (Opus)

1. User klika "Generuj tresc tygodnia" w toolbarze.
2. `content_gen.build_week_prompt(items)` buduje duzy prompt:
   - SHOP_CONTEXT (reuse z `Komponenty/socialmedia/prompts.py`),
   - URL-e 4 kanalow + 2 storefronty (pl-pl / en-eu),
   - LOCKED_HASHTAGS_PL/EN (z `hashtag_library.py` - wymuszane),
   - 21 blokow pozycji (artysta, tytul PL/EN, 3 akapity PL + 3 akapity EN, flagi),
   - zasady (intro/outro, nowy artysta, nowy obraz).
3. Prompt kopiowany do schowka + wyswietlany w textarea.
4. User wkleja w Cursor chat (Claude Opus), wraca z JSON-em.
5. `parse_week_response(raw, expected_ids)` parsuje JSON (walidacja: 4 captions
   per pozycja, locked hashtagi dokladane automatycznie, rzuca ValueError gdy braki).
6. `apply_to_queue(items, content_map)` wpisuje captions + hashtags + zoom_hints
   do pol `caption_fb_pl/fb_en/ig_pl/ig_en`. Pomija pozycje z `manual_override=True`.

**Schema JSON odpowiedzi:**
```json
{"items": [{"id": "<uuid>", "pl": {"caption_fb", "caption_ig", "hashtags", "zoom_hints"}, "en": {...}}]}
```

### Flow publikacji (Meta Graph API v19)

`meta_publisher.publish_item(item, channels)` per-channel:

**Facebook (fb_pl/fb_en):**
- `POST https://graph.facebook.com/v19.0/{page_id}/photos` url=<cdn> message=<caption> access_token=<page_token>.
- 1 zdjecie (main image).

**Instagram (ig_pl/ig_en) - karuzela 2-10 obrazow:**
1. Per obraz: `POST /{ig_user_id}/media image_url=... is_carousel_item=true` -> child_id.
2. `POST /{ig_user_id}/media media_type=CAROUSEL children=id1,id2,... caption=...` -> creation_id.
3. Wait az `GET /{creation_id}?fields=status_code` zwroci `FINISHED`.
4. `POST /{ig_user_id}/media_publish creation_id=...` -> media_id.

Kolejnosc obrazow w IG karuzeli: **main.jpg -> zoomy alfabetycznie -> MOCKUP (ostatni)**.

**Problem publicznych URL-i dla IG:**
- IG wymaga publicznych URL zdjec (nie accept multipart upload).
- Main image uzywa CDN `product.image.src` - juz publiczny.
- Zoomy + MOCKUP sa uplodowane do **Shopify Files API** przez GraphQL
  `stagedUploadsCreate` + POST multipart + `fileCreate` + polling `fileStatus=READY`.
- URL-e cache'owane w `CykleItem.cdn_main` / `cdn_zooms[]` / `cdn_mockup` zeby nie re-uplodowac.

### Konfiguracja Meta

Plik `data/cykl/meta_credentials.json` (GITIGNORE):
```json
{
  "fb_pl": {"page_id": "...", "access_token": "..."},
  "fb_en": {"page_id": "...", "access_token": "..."},
  "ig_pl": {"ig_user_id": "...", "access_token": "..."},
  "ig_en": {"ig_user_id": "...", "access_token": "..."}
}
```

- `access_token` = **Long-Lived Page Access Token** (wymagane scopes: pages_show_list,
  pages_manage_posts, pages_read_engagement, instagram_basic, instagram_content_publish).
- Dla IG `access_token` = ten sam page token co dla powiazanej strony FB.
- `ig_user_id` = Instagram Business Account ID (z `GET /{page_id}?fields=instagram_business_account`).

Dialog konfiguracyjny (`meta_config.open_meta_config_dialog`) ma przycisk
"Test polaczenia" per kanal + instrukcje konfiguracji. Bez **App Review** w Meta
for Developers publikacja zadziala tylko dla administratorow aplikacji (konta
testowe) - produkcja wymaga App Review (2-6 tygodni).

### Publisher daemon w launcherze

`giclee_app/launcher.py::_poll_cykl_publisher` (co 60s):
- Zaplanowany po 45s od startu launchera (razem z produkcja-sync i innymi pollami).
- Worker thread: `meta_publisher.publish_due_items()` - publikuje pozycje
  `scheduled_at <= now` ktore maja tresc + obrazy + config.auto_publish=True.
- Per-channel try/except: blad w jednym kanale nie blokuje pozostalych.
- Powiadomienia (toast + status bar) gdy cos opublikowane.

`_check_cykl_weekly_reminder` (po 3s od startu):
- Czyta `scheduler.days_of_content_left(items)`.
- Gdy <=2 dni pozostalej tresci -> notify("Cykl - czas wygenerowac tresc").
- Stan w pamieci (`self._cykl_reminder_shown=True`) - nie powtarzamy w tym samym starcie.

### UI: panel kolejki (`cykl/view.py`)

Treeview kolumny: Data | Godz | Slot | Artysta | Tytul | FB PL | FB EN | IG PL | IG EN | Tresc (preview) | Status.

Kolorowanie wierszy (tagi):
- `overdue` (pending + scheduled_at < now) -> czerwone tlo.
- `missing_img` (brak main) -> pomaranczowy tekst.
- `done` -> zielony tekst.
- `skipped` -> szary tekst.
- `error` -> zolte tlo.

PPM menu: Edytuj... / Publikuj teraz / Wyslij recznie / Przesun +/-1 dzien
(ta pozycja) / Gora / Dol / Kopiuj caption PL / EN / Pomin / Usun.

Toolbar: Odswiez z Shopify (delta albo pelny rebuild) / Generuj tresc tygodnia /
+1 dzien WSZYSTKIE / -1 dzien WSZYSTKIE / Lista kontrolna / Otworz folder obrazow /
Ustawienia Meta API / Instrukcja.

Status bar: "Kolejka: X pending / Y done / Z skipped" + "Tresc wygenerowana do:
DD.MM.YYYY" (zolta etykieta gdy <=2 dni) + "Aktualnie: X (3/7) -> Y".

### Obrazy

Folder `data/cykl/Obrazy/<artysta-slug>/<tytul-slug>/`:
- `main.jpg` - glowne zdjecie (do FB i 1-szego slidu IG). Fallback: `product.image.src`.
- `zoom_*.jpg` - zblizenia (do srodka IG karuzeli, alfabetycznie).
- `*MOCKUP*.jpg` - mockup w ramce (ostatni slide IG karuzeli).

Sufiks `MOCKUP` wykrywany case-insensitive (regex `mockup`). Drag-drop obsluga
w `edit_dialog.py` - kopiuje pliki do folderu i dopisuje do listy.

**Preferowane specyfikacje** (w `help_text.IMAGE_SPECS_QUICK`):
- IG: 1080x1350 (4:5) lub 1080x1080 (1:1), JPG/PNG, sRGB, <8 MB.
- FB: 1200x1200 lub 1200x628 (1.91:1), JPG/PNG, <4 MB.
- Karuzela IG: 2-10 obrazow, TEN SAM aspect ratio (IG wymaga).

`images.sync_item_images(item)` odswieza `item.image_*` z dysku (wywolywane
przy kazdym `_refresh_from_disk` w view). Pomija pola FB/IG gdy `manual_override=True`.

### Persystencja (`data/cykl/`)

- `queue.json` - kolejka (`items: [CykleItem, ...]`). **Commitujemy do repo**
  (to zywy plan - przy wymianie komputera/restarcie nie trzeba rebuild'owac).
- `generation_state.json` - `{artists_hash, paintings_hash, artists_snapshot}`.
  **Commitujemy.**
- `config.json` - `{slot_times, active_channels, auto_publish, ...}`. **Commitujemy.**
- `meta_state.json` - log publikacji (500 ostatnich). **GITIGNORE** (duzy, regenerowalny).
- `meta_credentials.json` - tokeny. **GITIGNORE (SEKRET!).**
- `Obrazy/` - lokalne zdjecia. **GITIGNORE** (duze pliki, trzymaj na NAS/OneDrive).

---

## 10. ZNANE PUNKTY UWAGI / GOTCHAS

1. **Polskie znaki w nazwach plikow / tagach:** parser konwertuje `_` -> spacja oraz tonkii
   `-/–/—` jako separator. Pillow czyta JPEG z exifem - nazwy plikow z polskimi znakami
   musza dzialac tez w PowerShell (PYTHONIOENCODING=utf-8 zalecane).
2. **Smart-collections cache:** zywy w pamieci procesu (`_SMART_COLLECTION_CACHE` w `create.py`).
   Restart aplikacji = pierwsze utworzenie kazdej kolekcji znow trafia do API (idempotentne,
   ale pierwsza paczka po starcie bedzie wolniejsza o ~1s na kazdy nowy tag).
3. **Publikacja kolekcji** wymaga scope `write_publications`. Bez niej kolekcje powstaja,
   ale sa niewidoczne na froncie (nie sa opublikowane). Komunikat w logach informuje o tym.
4. **Slug handle smart-collection** - slugifier w `tags_taxonomy.py._slug` konwertuje polskie
   diakrytyki na ASCII. Handle jest stabilny dla tej samej nazwy tagu - dwa pierwsze produkty
   z tym samym stylem trafia do TEJ SAMEJ kolekcji (idempotencja po handle).
5. **Tytul produktu w Shopify** = `"{Artysta} - {Tytul polski}"`. Walidacja w `find_product_by_title`
   probuje zarowno po dokladnym tytule, jak i po slug-handle. Jesli wlasciciel rec znie zmieni
   tytul w admin, follow-up zdjecia (F2) moga przestac trafiac w produkt - alarm w logu.
6. **Cennik z lokalnego szablonu:** kazdy nowy produkt dziedziczy warianty/ceny z szablonu
   domyslnego (`variant_templates.json`, dialog **Szablony...** w dodajobraz). Kafelek **Zmień ceny**
   (`zmienceny`) zmienia ceny we WSZYSTKICH produktach, a jako wzorzec wariantow bierze rowniez lokalny
   szablon (a nie live produkt z Shopify, jak bylo wczesniej).
   - Mozesz miec wiele szablonow (np. "Podstawowy", "Plotno XL", "Tylko rama premium").
   - Mozesz zaimportowac szablon z dowolnego produktu Shopify (przycisk "+ Z Shopify...").
   - Mozesz wygenerowac warianty automatycznie z opcji (Cartesian product w dialogu).
   - **Szablony... -> Zastosuj do wszystkich produktow...** stosuje wybrany szablon
     do calego katalogu Shopify: tworzy brakujace warianty, aktualizuje pasujace
     pola/ceny i usuwa warianty nadmiarowe. Operacja ma dwa potwierdzenia, progress
     dialog i anulowanie miedzy produktami. Szablon musi miescic sie w limitach Shopify:
     max 3 opcje i max 100 wariantow na produkt.
   - **Szablony... -> Zastosuj do produktu...** otwiera liste produktow z Shopify
     (filtr tekstowy + ptaszki w pierwszej kolumnie). Mozna zaznaczyc wiele produktow
     i zastosowac szablon do wszystkich naraz (`Zaznacz widoczne` / `Odznacz widoczne`).
   - Przy stosowaniu szablonu do istniejacych produktow aplikacja jawnie wysyla
     `inventory_management: null` dla wariantow. To wylacza sledzenie magazynu w Shopify,
     zeby reprodukcje robione na zamowienie nie pokazywaly sie jako "wyprzedane"
     przy stanie magazynowym 0.
7. **Blog - scope `read_content/write_content`:** BEZ tych scope REST `/blogs.json` zwraca
   403. Po dodaniu scope trzeba koniecznie `npm run deploy -- --allow-updates` ZANIM
   zrobi sie `npm run oauth` - inaczej Shopify pokaze stary ekran zgody bez nowych uprawnien.
8. **Blog - image attachment 20 MB:** Shopify REST dla Article ma limit ~20 MB na pole
   `image.attachment` (base64). Komponent blog waliduje to w `_build_image_payload` -
   dla zdjec >20 MB rzuca ShopifyError; wiekszym plikom trzeba najpierw zmniejszyc rozdzielczosc
   albo uzyc `src` (URL zdjecia hostowanego gdzie indziej).
9. **Blog - translation `tags`:** Shopify NIE tlumaczy tagow artykulu per locale. Tagi
   ida po polsku na wszystkie wersje. Jesli blog urosnie i bedzie trzeba filtrowac posty
   po locale - trzeba dorobic `ALWAYS_TAGS_<LANG>` do article tags (podobnie jak dla produktow).
10. **Blog - `data/` pliki:** w `Komponenty/blog/data/`:
    - `topics.json` - propozycje tematow uzytkownika (**commitujemy do repo** - to wartosciowa baza wiedzy).
    - `articles_cache.json` - snapshot API Shopify, ignorowany przez `.gitignore`.
    - `preview.html` - transient artefakt z "Podglad w przegladarce", ignorowany przez `.gitignore`.
11. **Socialmedia - publikacja recznie:** Komponent NIE publikuje postow automatycznie.
    Kolejka w planerze to lokalny organizer - uzytkownik musi sam skopiowac caption + otworzyc obraz
    i wkleic w Meta Business Suite / Pinterest / TikTok / telefon. Integracja z Meta Graph API
    jest mozliwa, ale wymaga Facebook App Review (2-6 tygodni) + Business Account + Page tokens -
    to osobny projekt.
12. **Socialmedia - posts.json:** plik w `Komponenty/socialmedia/data/posts.json` commitujemy
    do repo (to historia/plan postow - wartosciowa baza wiedzy, nie tylko cache).
    Image_path jest lokalna sciezka - NIE kopiuje pliku, tylko trzyma referencje.
    Jesli przenosisz repo na inny komputer - sciezki obrazow beda miec wartosc tylko jesli sa
    w stalym miejscu (np. OneDrive / NAS mapped) albo w folderze wewnatrz repo.
13. **Zadania - kalendarz swiat po 2028:** `Komponenty/zadania/holidays.py` ma hardcodowane
    daty tylko dla lat 2026-2028. Wielkanoc/Dzien Matki/Dzien Ojca (niektore) sa ruchome -
    trzeba recznie dopisac nowe lata do `_RAW` zanim wejdziemy w kolejny rok, inaczej
    `events_upcoming()` zwroci pusta liste i LLM nie bedzie widzial swiat w kontekscie.
14. **Zadania - iter_all_products limit:** `shopify_signals.fetch_new_products` iteruje
    po WSZYSTKICH produktach w sklepie z limitem 500 (zabezpieczenie). Przy 10k+ produktach
    to zacznie byc wolne - wtedy warto dorobic REST param `created_at_min=<ISO>` do
    `iter_all_products` w `dodajobraz/shopify_client.py`.
15. **Zadania - link do socialmedia:** PPM "Generuj post" z zadania otwiera generator socialmedia
    z `from_task_id`. Po zapisaniu posta callback robi `storage.link_post(task_id, post_id)` -
    zadanie dostaje status `in_progress`. Jesli uzytkownik nie zapisze posta tylko zamknie
    okno - zadanie zostaje w `in_progress` (trzeba recznie cofnac na pending przez PPM).
16. **Multi-channel / multi-platform callback:** Gdy zadanie ma kanaly `["ig_feed","fb","pinterest"]`
    i user wygeneruje multi-post, generator socialmedia zapisze 3 posty w krotkim czasie.
    `_on_post_saved_from_task` w `zadania/view.py` lapie **wszystkie posty z ostatnich 60 sekund** i laczy
    je z zadaniem - nie tylko jeden najnowszy. Jesli user zmeczy sie i bedzie zapisywal kolejne
    partie > 60s od siebie, tylko najswiezsza partia sie polaczy. Mozna manualnie dolaczyc przez edycje.
17. **Multi-platform + series = niedozwolone:** Tryb "Seria postow" dziala TYLKO przy 1 zaznaczonej
    platformie. Gdy user zaznaczy wiecej + series -> dialog ostrzega i forsuje przelaczenie na "single".
    Eksplozja kombinacji (N platform x N postow) byla niepraktyczna - lepiej wygenerowac
    serie pod jedna platforme, potem duplikowac zadanie na inne.
18. **Tlumaczenia opisu (description_translations):** Klucze MUSZA byc jezyki inne niz `pl` i `both`
    (bo `description` jest po polsku, a `both` to shortcut ktory parser rozwija). LLM czasem
    probuje dac `"pl": "..."` - parser to odrzuca. Jesli tlumaczenie jest puste po strip() - pomijamy.
19. **Monthly reminder - test:** Zeby sprawdzic ze dialog sie pokazuje bez czekania na 1. dzien miesiaca -
    usun plik `Komponenty/zadania/data/reminders.json` przed uruchomieniem launchera
    **w 1-5 dniu miesiaca**. W innych dniach reminder sie NIE pokaze (to swiadomy design -
    inaczej spamowalby przy kazdym starcie aplikacji).
20. **Sortowanie Treeview (tree_sort helper):** `Komponenty/_shared/tree_sort.py:attach_sortable_headings`
    dziala na wierszach top-level (bez nested). Dla kolumn typu `"date"` string compare na ISO YYYY-MM-DD
    jest wystarczajacy (puste wartosci sortuja sie na koncu jako "9999-99-99"). Dla typu `"int"`/`"float"`
    ekstrahuje znaki numeryczne (ignoruje emojis i dekoratory). Dla `"text"` lowercase + string compare.
21. **Szablony wariantow - bootstrap:** Pierwsze uruchomienie `dodajobraz` probuje zaciagnac szablon
    "Podstawowy" z `REFERENCE_PRODUCT_ID`. **Wymaga zywej sesji Shopify** (`.shopify_session.json`).
    Jesli sesji brak - apka startuje ale bez szablonow; trzeba otworzyc **Szablony...** i dodac
    szablon (z Shopify lub recznie). Po dodaniu pierwszego szablonu bootstrap nigdy wiecej nie
    probuje - niezaleznie od statusu Shopify. Reset: skasuj `variant_templates.json`.
22. **Produkcja - polling zamowien:** `giclee_app/launcher.py::_poll_orders_from_shopify` dziala
    co 5 min w watku daemon. **Nie crashuje launchera** jesli Shopify nie odpowiada (try/except).
    Jesli dodano scope `read_orders` ale nie zrobiono `npm run oauth`, Shopify wrzuca 403 -
    w logu pojawia sie `[orders_sync] BLAD Shopify: ...`. Reset sync state
    (aby cofnac sie do calej historii) = skasuj `produkcja/dane/sync_state.json`.
23. **Produkcja - live countdown:** odswiezanie co 1s atakuje TYLKO referencje widgetow
    zapamietane w `self._countdown_widgets` - zeby reszta UI (combo-box wariantu ramki, text
    notatki) nie gubila focusu. Jesli dodajesz nowy widget ktory ma byc live-updated, dopisz
    go do listy `_countdown_widgets` z odpowiednim `role` (`label` / `bg` / `info`).
24. **FX rates (NBP):** `Komponenty/_shared/fx_rates.py` woła `https://api.nbp.pl` z TTL 24h.
    Przy offline + brak cache `get_rate()` rzuca `FxError`. Dialog Rynki obsluguje to graceful -
    pokazuje blad i pozwala wpisac kurs recznie (`set_manual_rate`). Reczny kurs ma TTL
    nieskonczony (source=`manual`) - zeby sie nie nadpisywal przy kolejnym `get_rate`.
25. **Notatnik - struktura rozdzialow:** `Komponenty/notatnik/notatki/` = root; podfoldery =
    rozdzialy; pliki `.md` = notatki. Plik `.favorites.json` (ukryty przed drzewkiem) trzyma
    liste wzglednych sciezek ulubionych. Przenosi/rename aktualizuje tez ulubione (fixup).
26. **Cykl - Meta App Review:** bez zatwierdzenia aplikacji w Meta for Developers ("App Review")
    publikacja dziala TYLKO dla administratorow aplikacji (swoje konta testowe). Dla publikacji
    na produkcyjne strony firmowe trzeba zlozyc App Review z permissions: `pages_manage_posts`,
    `instagram_content_publish`. Czas rozpatrzenia 2-6 tygodni. Wymagane: Privacy Policy URL,
    Data Use Checkup, screencasty uzywania. Do tego czasu publisher bedzie zwracal blad
    "(#200) The user hasn't authorized the application...".
27. **Cykl - token wygasa:** Long-Lived Page Access Token formalnie nie wygasa, ale User Access
    Token uzywany do jego pobrania ma TTL 60 dni. Po zmianie hasla Facebook albo logout z
    Business Suite page tokens moga unevaluae - publisher zwroci HTTP 400 z komunikatem
    "Error validating access token". Napraw: Ustawienia Meta API -> wpisz nowe tokeny.
28. **Cykl - IG wymaga publicznych URL zdjec:** Instagram Graph API NIE przyjmuje multipart
    upload (tylko `image_url`). Dlatego dla zoomow + mockupow uzywamy
    `meta_publisher.upload_to_shopify_files` (GraphQL `stagedUploadsCreate` -> POST multipart
    na GCS -> `fileCreate` -> polling `fileStatus=READY`). URL-e cache'owane w
    `CykleItem.cdn_main/cdn_zooms/cdn_mockup` - nie re-uplodowujemy przy ponownej publikacji.
    Gdy uzytkownik podmieni plik lokalnie ALE `cdn_*` jest ustawione -> wyslemy stare zdjecie.
    Fix: wyczysc `cdn_zooms`/`cdn_mockup` w edit_dialog albo zmien auto-invalidation (TBD).
29. **Cykl - carousel min 2 zdjecia:** IG Carousel wymaga 2-10 zdjec tego samego aspect ratio.
    Gdy pozycja ma tylko main (bez zoomow ani mockupa) -> publikacja IG jest `publish_ig_single`
    (nie karuzela). Automatyka w `meta_publisher._ig_image_urls`.
30. **Cykl - rate limit Meta:** Graph API ma limit ~200 calls/hour per app per user. W cyklu
    publikujemy na 4 kanalach max 3 razy dziennie = 12 calls + ~2-3 calls per upload/publish =
    ~48 calls/dzien. Bezpiecznie. Ale przy pierwszej publikacji calej kolejki (30+ pozycji) +
    upload 5+ zdjec per kazda -> mozemy upicz w limit. Rozwiazanie: publisher leci co 60s
    = max 1 pozycja / minute (nawet gdy wszystkie overdue), nie spamuje.
31. **Cykl - kolejka w repo (queue.json):** `data/cykl/queue.json` commitujemy do repo jako
    zywy plan marketingowy (jak `blog/data/topics.json`). To nie jest cache - to plan artystow
    + obrazow + zrzut opisow + harmonogram. Przy synchronizacji miedzy komputerami plan lada.
    `Obrazy/` i `meta_credentials.json` NIE commitujemy (gitignore).
32. **Cykl - manual_override flag:** gdy user edytuje pozycje w `edit_dialog` - ustawia sie
    `manual_override=True`. Oznacza ze NIE nadpisujemy jej przy kolejnym `apply_to_queue`
    (Opus dostanie taka pozycje ale my ignorujemy odpowiedz). Zeby "odswiezyc" - usun pozycje
    recznie i zrob pelny rebuild lub delta.

---

## 11. CO TRZEBA WIEDZIEC GDY DODAJEMY NOWY JEZYK / RYNEK

1. Aktywowac jezyk w Shopify Admin -> Online Store -> Languages.
2. Utworzyc Market w Shopify Admin -> Settings -> Markets (przypisac jezyk i kraj/e).
3. Utworzyc Catalog (price list) z markupem % - wlasciciel robi recznie w Shopify Admin
   ALBO programowo via Markets API.
4. Dodac wpis do `markets_config.json` (`{ "code": "...", "name_pl": "...", "locale": "...",
   "url_prefix": "...", "markup_percent": ..., "shopify_market_gid": "..." }`).
5. Stworzyc `tags_taxonomy_<lang>.py` z analogicznymi `ALWAYS_TAGS`/whitelistami w jezyku
   docelowym (mozna sciagnac z googla "wall art keywords <lang>" - kluczowe sa frazy
   "wall art / Wandbild / tableau mural / cuadros decorativos / quadri da parete /
   schilderij voor aan de muur").
6. Rozszerzyc `prompt_builder.py` zeby LLM zwracal blok `translations.<lang>` z tytulem,
   akapitami, SEO i alt-text'em.
7. Dorobic w `shopify_client.py` `register_translations()` (`translationsRegister` mutation).
8. Wpiac w `create.py` `push_translations(product_id, translations_dict)` po utworzeniu
   produktu i smart-kolekcji.
9. Dodac do `.env` SCOPES nowy scope (jesli pierwszy raz uzywamy `write_translations`
   lub `write_markets`). Zapisac TEZ w `cursor-api/shopify.app.toml` (`[access_scopes]`).
10. `npm run oauth` w `cursor-api/` zeby ponownie zaakceptowac uprawnienia.

---

## 12. CO ZROBIC PRZED KAZDA NOWA SESJA AI

1. **Przeczytaj ten dokument i `THEME_KNOWLEDGE.md`** w folderze nadrzednym.
2. Sprawdz `cursor-api/.env` (SCOPES, SHOP).
3. Sprawdz `cursor-api/.shopify_session.json` istnieje (jesli nie - powiedz uzytkownikowi
   `cd cursor-api && npm run oauth`).
4. Sprawdz `markets_config.json` - moze sie zmienic markup, dodac rynek.
5. Jesli robisz cos kreatywnego (zmienia sie szablon HTML, prompt, taksonomia tagow)
   - zaktualizuj odpowiedni plik W TYM dokumencie ZARAZ po zmianie.
6. Jesli dodajesz nowy scope OAuth - **zawsze** trzy kroki w kolejnosci:
   (a) `.env` SCOPES + `shopify.app.toml` `[access_scopes]`,
   (b) `npm run deploy -- --allow-updates` (publikacja wersji aplikacji w Shopify Partners),
   (c) `npm run oauth` (uzytkownik akceptuje nowe uprawnienia w przegladarce).
   Pominiecie (b) = stary ekran zgody, nowe scope nie zadzialaja.
7. **Komponent `blog`:** jesli dodajesz nowe pole do Article (np. nowa kolumna w Treeview,
   nowy translation key), zaktualizuj tabele mapping w sekcji 9a. Jesli zmieniasz prompt -
   zaktualizuj opis w sekcji 9a (Prompty) i zasady dlugosci/strukturyHTML.

---

## 13. CO JESZCZE WARTO WIEDZIEC

- **`SERPAPI_KEY`** w `.env` - klucz do serpapi.com (wykorzystywany przez komponent
  `pobierzobraz` lub `nazwijobraz` do wyszukiwania info o obrazie).
- **`oauth-server.mjs`** - prosty Node serwer OAuth, dziala na `127.0.0.1:3000`. Zawsze
  startuje recznie (`npm run oauth`), nie jest ciagle uruchomiony.
- **Komponenty inne niz `dodajobraz`** (`obrazy`, `finanse`, `planer`, `notatnik`,
  `produkcja`, `sklep`, `nazwijobraz`, `pobierzobraz`) - kazdy ma `component.json`,
  swoj `gui.py` i jest osobnym modulem Pythona w `Komponenty/<nazwa>/`. Launcher
  uruchamia kazdy jako osobny proces (`python -m Komponenty.<nazwa>`), wiec crash
  jednego nie ubija calej aplikacji.
- **Build .exe** (PyInstaller): `cursor-api/giclee_app.spec` + `requirements-build.txt`.
- **Folder `_shared/`** w `Komponenty/` - wspolne helpery dla wielu komponentow.
- **Folder nadrzedny (`../` wzgledem `cursor-api/`)** to **motyw Shopify** (Liquid).
  Brief o motywie -> `THEME_KNOWLEDGE.md` w tamtym folderze.

---

## 14. INFRASTRUKTURA / BEZPIECZENSTWO / BACKUP

### 14a. Autentykacja (haslo do GicleeApp)

- Modul: [Komponenty/_shared/auth.py](cursor-api/Komponenty/_shared/auth.py).
- Haslo hashowane przez **PBKDF2-SHA256** (480 000 iteracji, 32-bajtowy salt). Plik
  `auth.json` trzymany w `%APPDATA%/Giclee/auth.json` (Win) / `~/Library/Application Support/Giclee/` (macOS) / `~/.config/Giclee/` (Linux).
  **Per-user per-machine** - nie w repo, nie wchodzi do backupu aplikacji.
- Launcher przy starcie wywoluje `auth.prompt_setup_or_login(None)`. Pierwszy start =
  dialog "Ustaw haslo". Kolejne starty = dialog "Zaloguj" (3 proby, po 3 bledach apka
  sie zamyka).
- Recznie: `cd cursor-api && python set_password.py` (zmiana/reset).
- Weryfikacja stala-czasowa (`hmac.compare_digest`) - odporne na timing attack.

### 14b. Auto-backup

- Modul: [Komponenty/_shared/backup.py](cursor-api/Komponenty/_shared/backup.py).
- Uruchamia sie **raz dziennie** (idempotentne) z launchera 2s po starcie.
- Pakuje do `cursor-api/backups/YYYY-MM-DD.zip`:
  - `Komponenty/*/dane/*.json` (zamowienia, planer, zadania, finanse),
  - `Komponenty/*/data/*.json` i `*.md` (bez `*_cache.json`, `preview.html`),
  - `Komponenty/notatnik/notatki/**/*.md` + `.favorites.json`,
  - `markets_config.json`, `shopify.app.toml`, `.env.example`.
- **Nie backupuje sekretow** (`.env`, `.shopify_session.json`) - to celowe.
- Rotacja: trzymamy 14 ostatnich zipow, starsze sa usuwane.
- Przywracanie: `backup.restore_from_backup(Path("backups/YYYY-MM-DD.zip"))` (UWAGA - nadpisuje pliki!).

### 14c. Desktop notifications

- Modul: [Komponenty/_shared/notifications.py](cursor-api/Komponenty/_shared/notifications.py).
- Windows: opcjonalnie `winotify` (pip install winotify) - prawdziwe Windows 10/11 toasty.
  Fallback: `MessageBeep` + print.
- Wysylane z launchera:
  - Ramka skonczyla 72h utwardzania (`_check_cure_done_notifications` co 60s).
  - Nowe zamowienie z Shopify (po pollingu).
- State pokazanych: `Komponenty/produkcja/dane/notified.json` (`cure_done: [ORD-IDs]`).

### 14d. Log viewer w launcherze

- Kazdy subprocess komponentu ma stdout/stderr przekierowane do `cursor-api/logs/<nazwa>.log`.
- **PPM na kafelku** w launcherze -> menu "Pokaz log / Wyczysc log / Otworz folder komponentu".
- Dialog log viewer auto-odswieza co 2s (tail live).

### 14e. Retention zamowien

- Modul: [Komponenty/produkcja/retention.py](cursor-api/Komponenty/produkcja/retention.py).
- Przycisk **Archiwizuj stare** w produkcji: przenosi `wyslane=True` zamowienia
  starsze niz N miesiecy (user podaje, domyslnie 6) do `archive_YYYY.json`.
- `zamowienia.json` zostaje mniejsze -> lista szybciej sie laduje.

### 14f. Rentownosc per zamowienie

- Nowe pola w modelu zamowienia: `cena_sprzedazy`, `koszt_plotno`, `koszt_wydruku`,
  `koszt_drewna`, `koszt_farby`, `koszt_wysylki`, `koszt_inne` (wszystko PLN brutto).
- Funkcja `_profit_summary(o)` w `view.py` liczy marze i marza%.
- Sekcja "Rentownosc" w detalu zamowienia - user wpisuje wartosci po fakcie.

### 14g. Etykiety wysylkowe (prefilled-form pattern)

- Modul: [Komponenty/produkcja/shipping.py](cursor-api/Komponenty/produkcja/shipping.py).
- **Furgonetka.pl** (PL) + **Przesylarka.pl** (zagranica) - dwie platformy nie maja
  otwartych API dla osob fizycznych, wiec uzywamy prefilled-form-redirect pattern.
- Przycisk "Przygotuj przesylke..." w finalizacji:
  1. Kopiuje dane odbiorcy + wymiary paczki (proponowane per wariant ramki) do schowka.
  2. Otwiera strone kuriera w przegladarce.
  3. User wkleja dane w formularzu kuriera.
  4. Wkleja numer trackingu z powrotem do pola `tracking_number` w apce.
- Detekcja kraju: `is_poland()` sprawdza PL post code (NN-NNN) + slowa "polska/poland".

### 14h. Webowy serwer produkcji (telefon w warsztacie)

- Modul: [Komponenty/produkcja/web_server.py](cursor-api/Komponenty/produkcja/web_server.py).
- Uruchamianie: `python -m Komponenty.produkcja.web_server` (lub `.cmd` w katalogu `cursor-api/`).
- **Sluchamy na 0.0.0.0:5000** - dostep z kazdego urzadzenia w LAN (telefon, tablet).
  **NIE wystawiamy tego na internet** bez dodatkowego TLS + hardening.
- Czysta biblioteka standardowa (http.server + wsgiref) - zero pip dependencies.
- Auth: ten sam pbkdf2 co GicleeApp (`Komponenty._shared.auth.verify_password`).
- Sesje w pamieci procesu (restart = wylog wszystkich). TTL 12h.
- CSRF: token w hidden input, porownywany z sesja.
- Mobile-friendly HTML (viewport + CSS grid). Live countdown utwardzania w JS.
- Checkboxy krokow produkcyjnych -> POST /order/<id>/toggle -> zapis do `zamowienia.json`.

### 14i. Testy jednostkowe

- `cursor-api/tests/` (pytest).
- `pip install pytest` + `python -m pytest tests/ -v` -> m.in. auth, markets, produkcja, dodajobraz (parser + klucze wariantow).
- Nie wymagaja Shopify/NBP/sieci.
