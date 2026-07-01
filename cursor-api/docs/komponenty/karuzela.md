# Karuzela (GicleeApp)

Ustawienia sekcji **Wybrane dzieła** na sklepie — dwa niezależne wymiary:

| Wymiar | Opcje | Co zmienia |
|--------|-------|------------|
| **Zachowanie karuzeli** | Karuzela1 / Karuzela2 | JS karuzeli, dynamiczne tło produktu (Karuzela2) |
| **Wygląd sekcji** | V1 / V2 / V3 | Tylko tło sekcji: gradient, kontrast, tekstura, overlay Karuzela2 |

Hub: [`README.md`](README.md) · Motyw: [`docs/motyw/kolekcja-autora-showcase.md`](../../../docs/motyw/kolekcja-autora-showcase.md)

---

## Pliki

| Plik | Rola |
|------|------|
| `Komponenty/karuzela/gui.py` | Panel — radio Karuzela1/2 + V1/V2/V3, podgląd, przycisk **Cytaty** |
| `Komponenty/karuzela/quotes_gui.py` | Okno cytatów — lista kolekcji, edycja tekstu |
| `Komponenty/karuzela/quotes_service.py` | Metafield + cache lokalny |
| `Komponenty/karuzela/service.py` | `settings.json`, `assets/giclee-carousel-config.js` |
| `Komponenty/karuzela/settings.json` | `carousel_version`, `showcase_look`, URL podglądu |
| `assets/giclee-karuzela.js` | Router + `data-giclee-showcase-look` na `<html>` |
| `assets/giclee-carousel-config.js` | Domyślne wartości po deploy motywu |
| `assets/giclee-artist-collection-showcase.css` | V2 = domyślne tokeny; V1/V3 = override `[data-giclee-showcase-look]` |
| `assets/giclee-karuzela2.css` | V1 = mocniejsze overlaye tła produktu |

---

## Użycie

1. GicleeApp → kafelek **Karuzela**.
2. **Zachowanie:** Karuzela1 lub Karuzela2.
3. **Wygląd sekcji:** V1 (ciemniejsze, sprzed korekty), V2 (jaśniejsze z teksturą) lub **V3** (spokojniejsze, mniej kontrastu — karuzela na pierwszym planie).
4. **Zapisz** — `settings.json` + `giclee-carousel-config.js`.
5. **Otwórz podgląd** — URL z `?giclee_karuzela=` i `?giclee_showcase_look=` (+ localStorage).
6. **Cytaty…** — wiele cytatów per kolekcja (Shopify metafield `custom.collection_quotes`); na storefront losowy cytat przy wejściu na autora.

Domyślny URL podglądu: `https://gicleeart.eu/collections/jacob-van-ruisdael`.

---

## Cytaty per kolekcja

| Warstwa | Lokalizacja |
|---------|-------------|
| Metafield (lista) | `custom.collection_quotes` (type `json`, storefront `PUBLIC_READ`) |
| Metafield (legacy) | `custom.collection_quote` — pierwszy cytat z listy (kompatybilność) |
| Cache lokalny | `Komponenty/karuzela/data/collection_quotes.json` (wersja 2, pole `quotes: []`, snapshot `catalog`) |

**Wydajność:** lista kolekcji + oba metafieldy cytatów w **jednym** przebiegu GraphQL. Przy starcie UI — ostatni snapshot z cache, potem odświeżenie w tle.

**GUI:** lista cytatów per kolekcja — **Dodaj cytat**, **Usuń zaznaczony**, edytor, **Zapisz cytaty**. Kolumna statusu pokazuje liczbę cytatów.

**Storefront:** overlay w sekcji galerii — przy zmianie autora wybierany cytat z listy, **najpierw ten, którego użytkownik jeszcze nie widział** (localStorage `giclee-gacs-seen-quotes`; po obejrzeniu wszystkich — cykl od nowa). Stały do następnej zmiany autora. Fallback: pojedynczy `collection_quote`. Pliki: `giclee-showcase-slide-overlays.js`, `giclee-artist-showcase-artist-json.liquid`, `giclee-artist-collection-showcase.liquid`.

Przy pierwszym zapisie komponent tworzy definicję metafield (GraphQL). Wzorzec jak [`tldobio.md`](tldobio.md).

---

## Persystencja (kolejność)

**Karuzela1/2:** URL `?giclee_karuzela=` → `localStorage` `giclee-carousel-version` → `__GICLEE_CAROUSEL_DEFAULT` → Karuzela1.

**Wygląd V1/V2/V3:** URL `?giclee_showcase_look=` → `localStorage` `giclee-showcase-look` → `__GICLEE_SHOWCASE_LOOK_DEFAULT` → V2.

| Wersja | Opis |
|--------|------|
| V1 | Ciemniejsze tło sprzed korekty balansu |
| V2 | Jaśniejsze tło z większą teksturą (domyślne) |
| V3 | Widoczne tło, ~12% mniej kontrastu/nasycenia — uspokojone względem karuzeli |

**API w przeglądarce:** `GicleeKaruzela.setVersion('Karuzela2')`, `GicleeKaruzela.setShowcaseLook('V3')` — przeładowuje stronę.

---

## Deploy motywu

Po **Zapisz** w GicleeApp wdrożyć m.in.:

- `assets/giclee-carousel-config.js`
- `assets/giclee-karuzela.js`
- `assets/giclee-artist-collection-showcase.css`
- `assets/giclee-karuzela2.css` (gdy używana Karuzela2)
