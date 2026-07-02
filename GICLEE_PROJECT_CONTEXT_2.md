# GICLEE_PROJECT_CONTEXT_2

> Kontekst marki i aktualnego stanu projektu dla Custom GPT tworzącego prompty do Cursor.  
> Uzupełnienie pliku `TECH_STACK.md` — tu **co** jest na stronie i **jak** to wygląda, nie **jak** jest zbudowane technicznie.  
> Sklep: **gicleeart.eu** · domena produkcyjna · motyw Shopify Horizon (custom Giclée Art).  
> Ostatnia analiza kodu: 2026-07-01.

---

## 1. Aktualny stan projektu

### Czym jest Giclée Art (z kodu i treści)

**Giclée Art** to autorska pracownia druku Fine Art i galeryjnej oprawy dzieł — sklep e-commerce na Shopify, który łączy:

1. **Reprodukcje dzieł malarskich** — w tym cyfrowo odrestaurowane klasyki (kolekcja *© Giclée Art — Restoration Edition 2026*).
2. **Własną fotografię klienta** — upload zdjęcia, podgląd w ramie, konfiguracja i zakup gotowego wydruku w oprawie.

Marka komunikuje się językiem **pracowni artystycznej / galerii muzealnej**, nie typowego sklepu internetowego. Produkt końcowy to **gotowe dzieło do ekspozycji** — wydruk + passe-partout + rama — a nie „plakat" ani surowa reprodukcja.

### Co jest już zaimplementowane (widoczne w kodzie)

| Obszar | Stan |
|--------|------|
| **Strona główna** | Splash screen, slideshow full-frame, sekcje editorial z suwakami przed/po, opisy pracowni, restauracji i korekty |
| **Katalog artystów** | Menu wielopoziomowe „Katalog", panel artystów z podglądem, strony kolekcji z biografią autora |
| **Galeria kolekcji** | Sekcja coverflow / karuzela 3D „Wybrane dzieła" z nawigacją między autorami |
| **PDP reprodukcji** | Galeria mockupów, zoom HD (OpenSeadragon + kafelki R2), warianty (drewno/kolor/rozmiar), passe-partout, proces produkcji, sekcja zaufania |
| **PDP własna fotografia** | Edytor mockupu (kadrowanie, zoom, upload), panel jakości PPI, konfigurator ramy |
| **Strona edytora** | `/pages/fotografia-obraz` — pełnoekranowy mockup bez standardowego layoutu sklepu |
| **Koszyk** | Drawer + strona koszyka, prośba o fakturę (osoba prywatna / firma), rekomendacje produktów |
| **Checkout** | Standard Shopify Checkout; PL: przycisk BLIK zamiast Shop Pay |
| **Strony informacyjne** | Manifest marki, Giclée Frame™, FAQ, współpraca z fotografami, kontakt |
| **Losuj obraz** | Interaktywna strona WebGL „Fine Art Oracle" — losowy wybór dzieła z kolekcji |
| **Wielojęzyczność** | 7 rynków: PL (baza), EN, DE, FR, ES, NL, IT — tłumaczenia motywu + produktów |
| **Powiadomienie startowe** | Modal na homepage: „Strona w fazie testów…" (konfigurowalny w ustawieniach motywu) |

### Backoffice (poza sklepem, ale wpływa na to, co widać)

GicleeApp (`cursor-api/`) zarządza katalogiem (dodawanie reprodukcji, mockupy katalogowe, tłumaczenia), fakturami bez VAT, produkcją zamówień i analityką — **nie jest częścią frontu sklepu**, ale dostarcza produkty, zoom manifesty i dokumenty sprzedaży.

---

## 2. Charakter marki widoczny w kodzie

### Pozycjonowanie

- **Fine Art / muzealny standard** — powtarzalne frazy: „standard muzealny", „archiwalny", „kolekcjonerski", „galeryjna oprawa".
- **Rzemiosło + technologia** — ręczna rama z litego drewna + pigmentowy druk Epson + cyfrowa restauracja.
- **Od pliku do obiektu** — manifest marki (`page.filozofia-marki`): „Od obrazu potencjalnego — do obiektu obecnego. Od pliku — do obiektu."
- **Autorskość** — pierwsza osoba w tekstach („tworzę", „realizuję osobiście"), sygnatura kolekcji Restoration Edition, marka **Giclée Frame™**.

### Dwa filary produktowe

| Filar | Narracja w kodzie |
|-------|-------------------|
| **Reprodukcje / restauracja** | Przywracanie zapomnianych dzieł, szacunek do oryginału, unikanie „nadmiernej poprawy", certyfikat autentyczności z numerem edycji |
| **Fotografia klienta** | Domknięcie procesu twórczego fotografa, „Fine Art Preview", panel PPI jako edukacja jakości, automatyczny upload pliku po zakupie |

### Klimat wizualny (z komponentów)

- **Ciemne tła** — splash (#000), galeria autora (gradienty, vignette), scheme-6 na hero/slideshow.
- **Złoty akcent marki** — `#c6a96b` (obrys przycisku checkout w koszyku, akcenty UI).
- **Editorial / magazine** — duże typografie, suwaki porównawcze przed/po, sekcje z liniami divider, scroll reveal na PDP.
- **Galeria, nie sklep** — copy showcase: „prezentacja jak w galerii, nie w sklepie"; coverflow zamiast siatki produktów.

### Ton komunikacji

- **Ekspercki, spokojny, pewny** — bez krzykliwych CTA; długie akapity edukacyjne.
- **Konkret materiałowy** — nazwy marek (Hahnemühle, Epson, Rubio Monocoat, Fabriano), normy (ISO 9706), liczby (300 DPI, 100+ lat trwałości, złoty podział φ ≈ 1,618).
- **Polski jako język bazowy** — angielskie terminy branżowe (Fine Art, Giclée, passe-partout) zachowane świadomie.

---

## 3. Obecne sekcje strony

### Strona główna (`templates/index.json`)

| Sekcja | Rola |
|--------|------|
| **Splash screen** | Tylko na homepage: czarne tło, „Giclée Art", linia, „Witamy w świecie sztuki" — animowane wejście |
| **Slideshow full-frame** | Rotujące slajdy (autoplay ~3 s), pełna szerokość |
| **Dividery** | Cienkie linie między blokami editorial |
| **Media with content** | Sekcja łącząca obraz/wideo z tekstem (część wyłączona w JSON) |
| **Giclée Art — intro** | Nagłówek + opis autorskiej pracownii, kolekcjonerskie wydruki, standard muzealny |
| **Odrestaurowywanie dzieł** | Suwak przed/po + tekst o cyfrowej restauracji, sygnatura Restoration Edition 2026 |
| **Autorska korekcja kolorystyczna** | Suwak + opis indywidualnej korekty (nie tylko profile ICC) |
| **Potencjał fotografii** | Suwak + tekst o odkrywaniu jakości ukrytej w złym świetle/kolorystyce |
| **Zobacz różnicę** | „Pierwsza na świecie autorska kolekcja cyfrowo odrestaurowanych dzieł malarskich" + suwaki |

### Katalog / kolekcje (`templates/collection.json`)

| Sekcja | Rola |
|--------|------|
| **Biografia autora** (`giclee-artist-biography`) | Tło z metafieldów kolekcji, tekst z opisu kolekcji, scroll-overlap z galerią |
| **Kolekcja autora — galeria** (`giclee-artist-collection-showcase`) | Karuzela coverflow, nawigacja autorów z menu Katalog, autoplay, lead „Restoration Edition 2026" |
| **Listing produktów** | Standard Horizon + custom layout kolekcji |

### Karta produktu — reprodukcja (`product.nowy-szblon-produktu`, `product.szablon-produktu-v2`)

| Element | Rola |
|---------|------|
| **Nagłówek** | Tytuł dzieła, autor, cena |
| **Panel SZCZEGÓŁY** | Data powstania, technika, gatunek — parsowane z opisu produktu |
| **Zoom HD** | OpenSeadragon — głębokie powiększenie dzieła (gdy jest `custom.zoom_manifest`) |
| **Galeria mockupów** | Miniatury + scena z ramą — podgląd produktu w oprawie |
| **Konfigurator wariantów** | Drewno (dąb/sosna), kolor ramy, rozmiar; reguła: sosna → tylko czarny |
| **Passe-partout** | Białe / czarne — osobna opcja obok wariantów |
| **Scroll reveal** | Sekwencyjne pojawianie: nagłówek → opis → szczegóły → galeria → konfigurator |
| **Porównanie przed/po** (v2) | Suwak retuszu — metafield `custom.before_retouch_url` vs obraz Full |
| **Proces produkcji** | 5 kroków: skan → korekta → druk → rama → certyfikat |
| **Sekcja zaufania** | Epson, Hahnemühle, Rubio Monocoat, darmowa wysyłka, 14 dni zwrotu |
| **Powiązane / rekomendacje** | Horizon product recommendations |

### Karta produktu / strona — własna fotografia

| Element | Rola |
|---------|------|
| **Mockup Fine Art Preview** | Upload JPG/PNG/HEIC/WebP, kadrowanie w ramie, zoom, scroll, eksport JPG |
| **Konfigurator** | Drewno (dąb/sosna), kolory (jasny brąz, brąz, ciemny brąz, czarny), rozmiary M/L/XL |
| **Panel jakości PPI** | Ocena rozdzielczości pod wybrany rozmiar (najwyższa → krytycznie niska) |
| **GicleeLab** | Drawer z iframe kalkulatora (Vercel) — narzędzie pomocnicze |
| **Cena na żywo** | Aktualizacja po wyborze wariantu |
| **Upload po zakupie** | Plik + kadrowanie trafia do chmury; property `_Upload ID` w koszyku |

### Inne strony (dedykowane szablony)

| Strona | Szablon | Zawartość |
|--------|---------|-----------|
| **Filozofia marki** | `page.filozofia-marki` | MANIFEST MARKI — od pliku do obiektu, dwa obszary (malarstwo + fotografia) |
| **Giclée Frame™** | `page.giclee-frame` | Rozbudowany opis systemu oprawy: materiały, Rubio Monocoat, passe-partout Fabriano, papiery Fine Art, złoty podział, wymiary S/L/XL |
| **Losuj obraz** | `page.losuj-produkt` | „Fine Art Oracle" — WebGL + fallback, losowe dzieło z kolekcji |
| **FAQ** | `page.faq` | Accordion z pytaniami (treść z edytora motywu) |
| **Współpraca** | `page.wspolpraca` | Program partnerski dla fotografów sesyjnych |
| **Kontakt** | `page.contact` | Hero + formularz / dane kontaktowe |
| **Blog** | `blog.json`, `article.json` | Posty wielojęzyczne (Horizon) |

### Globalne elementy (layout)

| Element | Rola |
|---------|------|
| **Header** | Logo, menu (Katalog z flyout artystów), wyszukiwarka, koszyk, selektor języka/kraju |
| **Panel katalogu artystów** | Overlay z listą autorów, podglądem dzieła, animacją stagger |
| **Page transition** | Kurtyna przejścia między stronami (homepage) |
| **Footer** | Linki, newsletter, utilities |
| **Site notice** | Modal informacyjny na homepage (obecnie: faza testów) |

---

## 4. Obecne funkcje e-commerce

### Produkty i warianty

- **Reprodukcje** przypisane do kolekcji per autor; szablony PDP: `nowy-szblon-produktu`, `szablon-produktu-v2`.
- **Warianty reprodukcji** (typowe opcje w pickerze): **drewno** (dąb, sosna), **kolor ramy** (brązy, czarny), **rozmiar** (S/M/L/XL — w kodzie ram M/L/XL w cm).
- **Reguła biznesowa w UI**: sosna → dostępny tylko kolor czarny (przekreślenie niedostępnych opcji).
- **Passe-partout**: Białe / Czarne — line item property `Passepartout` (ukryte na szablonie własnej fotografii).
- **Własna fotografia**: osobny produkt/szablon z mockupem; warianty przez standardowy picker + konfigurator w `theme.liquid` (`#pm-config`).

### Ceny

- Wyświetlanie ceny Shopify + opcjonalnie compare-at (promocje).
- Ceny rynkowe per Market (backend: `zmienceny`, kursy NBP) — **na froncie** cena z Shopify Markets/localization.
- Mockup klienta: `#pm-config-price` — dynamiczna cena po wyborze wariantu.

### Koszyk

- **Drawer koszyka** (Horizon) + strona `/cart`.
- **Dodawanie**: standard `/cart/add.js`; mockup — sekwencja upload → add → update → otwarcie drawera.
- **Line item properties**: `_Upload ID` (własna fotografia), `Passepartout` (reprodukcje).
- **Prośba o fakturę** (`show_cart_invoice_request: true`):
  - Checkbox „Chcę fakturę"
  - Typ: osoba prywatna / firma
  - Pola firmy: nazwa + NIP/VAT (etykieta zależna od kraju rynku)
  - Zapis w `cart.attributes` → `note_attributes` na zamówieniu
- **Checkout button**: czarny ze złotym obrysem `#c6a96b`; poprawki hover w ciemnym drawerze.

### Checkout i płatności

- **Shopify Checkout** (hosted) — pełna obsługa płatności, adresów, Markets.
- **PL**: własny przycisk **BLIK** (`blik-checkout-button`) zamiast Shop Pay — `/cart/add.js` → redirect `/checkout`.
- **Faktury**: generowane w backoffice (GicleeApp) jako **faktura bez VAT** / Invoice without VAT — nie widoczne na froncie poza prośbą w koszyku.

### Języki i rynki

- **7 języków motywu**: PL, EN, DE, FR, ES, NL, IT (`locales/*.json`, klucze `giclee.*`).
- **Tłumaczenia treści**: bloki/sekcje przez `giclee-i18n-*`; menu przez klucze `giclee.menu.*`; UI JS przez `window.__gicleeI18n`.
- **Produkty/kolekcje**: Shopify Translations API (backend) — front pokazuje przetłumaczone tytuły/opisy per locale.
- **Prefiks URL** dla rynków (`/de/`, `/fr/` itd.) — obsługa w linkach katalogu (`Shopify.routes.root`).

### Certyfikat i autentyczność

- Komunikowany w sekcji **Proces produkcji** (krok 05): „certyfikat autentyczności z numerem edycji".
- Kolekcja restauracji sygnowana: **© Giclée Art — Restoration Edition 2026**.
- **Brak** dedykowanej sekcji/snippetu „certyfikat" na PDP poza opisem procesu — certyfikat jest elementem narracji, nie osobnym widgetem.

### Ramy (Giclée Frame™)

- Warianty drewna/koloru/rozmiaru na PDP.
- Strona produktowa marki **Giclée Frame™** — rozbudowany opis materiałów, proporcji (złoty podział), wymiarów.
- Mockup klienta: wizualizacja ramy na canvas + overlay (CZB mockup PNG z CDN Shopify).
- Wymiary zewnętrzne ramek M/L/XL w `lib/pm-frame-sizes.json`.

### Passe-partout

- Wybór Białe/Czarne na PDP reprodukcji (picker jak variant buttons).
- Opis archiwalnego passe-partout (Fabriano Elle Erre, ISO 9706) na stronie Giclée Frame™.
- Ukryty picker na szablonie własnej fotografii (passe-partout wbudowane w produkt/mockup).

### Zoom HD

- Metafield `custom.zoom_manifest` → kafelki na R2 → viewer OpenSeadragon.
- Tylko reprodukcje z opublikowanym manifestem (pipeline `dodajobraz` w backoffice).

### Analityka (niewidoczna dla klienta)

- Custom pixel Shopify → lejek: wejście → produkt → koszyk → checkout → zakup.
- Lejek konfiguratora ram (`giclee_app:*` events) — dashboard w GicleeApp.

---

## 5. Styl UI/UX

### Typografia

| Font | Zastosowanie |
|------|--------------|
| **Bodoni Moda** | Nagłówki premium (Google Fonts) |
| **Cormorant Garamond** (weight 300) | Akcenty editorial, lekki serif |
| **Horizon body** | Tekst bieżący, UI komponentów |

### Kolorystyka

- **Dominanta**: czerń (#000) — splash, tła galerii, ciemne schematy (scheme-6).
- **Akcent marki**: złoto `#c6a96b` — obrysy CTA checkout, subtelne akcenty mockupu.
- **Schematy Horizon**: scheme-1 (jasny), scheme-2 (ciemny drawer koszyka), scheme-5/6 — sekcje editorial.
- **Warianty**: czarny pill na białym tle; selected = czarne tło, biały tekst.

### Layout i spacing

- **Page-width** i **full-width** — naprzemiennie na homepage.
- **Sticky details** na desktop PDP — konfigurator przy scrollu.
- **Mobile (≤749px)**: kolumny stack, panel SZCZEGÓŁY pod opisem, zoom w stałym kontenerze 58vh.
- **Mockup breakpoints**: <1024px (panele pod mockupem), 1024–1400px (laptop), >1400px (desktop boczny).

### Animacje i interakcje

- Splash reveal (~1.2s cubic-bezier) na homepage.
- Page transition / curtain między stronami.
- Scroll reveal na PDP reprodukcji (nagłówek → opis → galeria).
- Karuzela coverflow z autoplay (~7 s) i crossfade tła (Karuzela2).
- Comparison slider (przed/po) na homepage i PDP v2.
- Stagger animacja listy artystów w panelu katalogu.
- WebGL losowanie obrazu (`giclee-random-artwork`) z fallback CSS.

### Feeling / poziom premium

- **Wysoki** — dużo negatywnej przestrzeni, wolne tempo (autoplay, długie fade), brak agresywnych badge’y.
- **Muzealny** — ciemne tła galerii, serif headings, copy o archiwalności.
- **Rzemieślniczy** — zdjęcia procesu, logotypy dostawców (Epson, Hahnemühle), ręczna rama w tekstach.
- **Transparentny** — panel PPI uczciwie ocenia jakość uploadu klienta (w tym „nie zalecane").

### Responsywność

- Pełna obsługa mobile/tablet/desktop w mockupie, koszyku, PDP, galerii autora.
- iOS: specjalna kolejność otwarcia drawera po upload (unikanie przerwania fetch).

---

## 6. Treści i komunikacja marki

### Hasła i frazy kluczowe (z kodu)

| Fraza | Kontekst |
|-------|----------|
| „Fine Art Preview" | Badge mockupu własnej fotografii |
| „Stwórz swój wydruk" | Nagłówek mockupu |
| „Witamy w świecie sztuki" | Splash homepage |
| „Restoration Edition 2026" | Kolekcja odrestaurowanych dzieł |
| „Giclée Frame™" | Autorski system oprawy |
| „Fine Art Oracle" / „Niech sztuka wybierze Ciebie" | Strona Losuj obraz |
| „Na czym budujemy Twoje zaufanie" | Sekcja trust PDP |
| „Jak powstaje Twój obraz" | Sekcja procesu (5 kroków) |
| „prezentacja jak w galerii, nie w sklepie" | Lead sekcji showcase |

### Język sprzedażowy

- **Edukacja przed sprzedażą** — długie opisy materiałów, procesu, norm; klient ma rozumieć *dlaczego* cena premium.
- **Wartość kolekcjonerska** — trwałość 100+ lat, certyfikat, archiwalność, numer edycji.
- **Brak presji** — 14 dni zwrotu, darmowa wysyłka; BLIK jako „wygodna płatność", nie „kup teraz".
- **Personalizacja** — własne zdjęcie klienta jako pełnoprawne dzieło Fine Art.

### Budowanie wartości produktu (elementy w UI)

1. Suwaki **przed/po** restauracji i korekty — dowód wizualny jakości.
2. **Zoom HD** — „zobacz każdy detal pędzla".
3. **Galeria mockupów** — produkt w kontekście wnętrza/ramy.
4. **Logotypy marek** (Epson, Hahnemühle, Rubio) — social proof B2B premium.
5. **Panel PPI** — uczciwa ocena jakości uploadu (zaufanie przez transparentność).
6. **5-krokowy proces** — uspójnienie ceny z ręczną pracą.
7. **Giclée Frame™** — własna marka oprawy jako diferencjator.

### Ton w różnych językach

- Polski = język bazowy treści w edytorze motywu.
- EN/DE/FR/ES/NL/IT = tłumaczenia przez system `giclee.*` + locale merge.
- Faktury: osobne etykiety prawne per kraj (NIP, USt-IdNr., n° TVA…).

---

## 7. Braki i rzeczy do doprecyzowania

### Nie da się jednoznacznie odczytać z kodu

| Temat | Uwaga |
|-------|-------|
| **Pełna lista produktów / autorów** | Katalog żyje w Shopify Admin — kod pokazuje mechanizm menu/kolekcji, nie aktualny asortyment |
| **Cennik per rozmiar/rynek** | Ceny w Admin API / Markets — front tylko wyświetla `product.price` |
| **Treść FAQ** | Szablon istnieje; konkretne pytania/odpowiedzi zależą od Theme Editor / strony CMS |
| **Treść site notice** | Obecnie: „faza testów" — może być tymczasowa; wersjonowana przez `site_notice_version` |
| **Newsletter** | Tekst intro w locale; integracja mailingowa nie widoczna w motywie |
| **Polityka zwrotów / regulamin** | Linki prawdopodobnie w footerze CMS — treść prawna poza repozytorium motywu |
| **Dane kontaktowe** | Strona kontakt istnieje; email/telefon/adres w treści CMS, nie w kodzie |
| **Limitowana edycja — liczby** | Certyfikat „numer edycji" w copy; logika numeracji w backoffice, nie na PDP |
| **Które sekcje homepage są aktywne** | Część sekcji ma `"disabled": true` w JSON — live może różnić się od repo |
| **Social proof / opinie** | Brak dedykowanej sekcji reviews w custom komponentach |
| **Program lojalnościowy** | Nie wykryto w kodzie motywu |

### Warto dopisać ręcznie do kontekstu GPT

1. **Misja i historia założyciela** — kod daje manifest, nie biografię osobistą.
2. **Docelowa persona klienta** (kolekcjoner vs fotograf vs dekorator wnętrz).
3. **Polityka cenowa** — marże, promocje, sezonowość.
4. **SLA realizacji** — w backoffice jest „szacowany czas 1–7 dni" na fakturze; brak na froncie sklepu.
5. **Status prawny sprzedaży** — DNR vs JDG, faktura bez VAT (backoffice); klient widzi tylko prośbę o fakturę.
6. **Które podstrony są publiczne / ukryte** w menu.
7. **Aktualny komunikat site notice** — czy nadal „faza testów".
8. **Główny CTA biznesowy** — reprodukcje vs własna fotografia (priorytet sprzedażowy).

---

## 8. Rekomendacje dla Custom GPT

### Jak uwzględniać ten projekt w promptach do Cursor

1. **Rozróżniaj dwa produkty** — prompt musi jasno mówić: reprodukcja katalogowa **albo** własna fotografia klienta (inny flow, inne pliki).
2. **Chroń ton marki** — premium, muzealny, spokojny; unikaj copy typu „mega promocja", „kup teraz", emoji, caps lock.
3. **Używaj słownictwa z projektu** — Fine Art, Giclée Frame™, passe-partout, Restoration Edition, archiwalny, pigmentowy — nie synonimów typu „plakat", „rama IKEA".
4. **Wskazuj konkretne szablony** — np. „PDP reprodukcji = `product.nowy-szblon-produktu`", nie generyczne „product page".
5. **Respektuj języki** — nowy tekst UI → klucz `giclee.ui.*` w `pl.json` + merge do 6 locale; nie hardcode w JS bez i18n.
6. **Nie mieszaj mockupów** — mockup klienta (motyw) ≠ mockup katalogowy (GicleeApp `Komponenty/mockup/`).
7. **UI premium = małe diffy** — animacje subtelne, ciemne tła galerii, złoty akcent oszczędnie.
8. **Przy zmianach PDP** — sprawdź scroll reveal, mobile 749px, zoom manifest, variant sync (sosna→czarny).
9. **Przy zmianach koszyka/faktury** — nie psuj atrybutów `_Invoice *` ani property `_Upload ID`.
10. **Do stacku technicznego** — odsyłaj do `TECH_STACK.md`; ten plik to kontekst marki i UX.

### Szablon promptu (kontekst marki)

```
Kontekst marki: GICLEE_PROJECT_CONTEXT_2.md
Warstwa: [motyw front / tylko copy / PDP reprodukcji / mockup klienta]
Ton: premium, muzealny, ekspercki — bez agresywnej sprzedaży
Język: [PL / EN / …] — jeśli UI, przez giclee.ui.* + locales
Nie zmieniaj: checkout flow, faktury, upload Worker, reguły wariantów
Zachowaj: prefiks giclee-, ciemne tła galerii, akcent #c6a96b oszczędnie
```

### Checklist jakości promptu

- [ ] Określono filar produktowy (reprodukcja vs fotografia klienta)
- [ ] Ton zgodny z manifestem marki (plik → obiekt, standard muzealny)
- [ ] Wskazano szablon/stronę (np. collection vs index vs PDP v2)
- [ ] Uwzględniono wielojęzyczność, jeśli dotyczy tekstu widocznego
- [ ] Nie proponuje funkcji sprzecznych z obecnym UX (np. siatka sklepowa zamiast galerii)

---

## Powiązane pliki kontekstowe

| Plik | Rola |
|------|------|
| [`TECH_STACK.md`](TECH_STACK.md) | Stack techniczny, struktura repo, konwencje kodu |
| [`MATKA.md`](MATKA.md) | Skrót startowy, ID, deploy |
| [`docs/motyw/README.md`](docs/motyw/README.md) | Indeks dokumentacji motywu |
| [`docs/motyw/szablony-i-strony.md`](docs/motyw/szablony-i-strony.md) | Mapa szablonów custom |
| [`docs/motyw/mockup-wlasna-fotografia.md`](docs/motyw/mockup-wlasna-fotografia.md) | Flow własnej fotografii |
| [`docs/motyw/kolekcja-autora-showcase.md`](docs/motyw/kolekcja-autora-showcase.md) | Galeria 3D autora |
| [`docs/motyw/tlumaczenia-tresci.md`](docs/motyw/tlumaczenia-tresci.md) | System i18n motywu |
