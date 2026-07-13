# Karuzela (GicleeApp)

Ustawienia sekcji **Wybrane dzieła** na sklepie — niezależne wymiary:

| Wymiar | Opcje | Co zmienia |
|--------|-------|------------|
| **Zachowanie karuzeli** | Karuzela1 / Karuzela2 | JS karuzeli, dynamiczne tło produktu (Karuzela2) |
| **Wygląd sekcji** | V1 / V2 / V3 | Tylko tło sekcji: gradient, kontrast, tekstura, overlay Karuzela2 |
| **Rozmycie tła (hover)** | wł. / wył. | Blur tła sekcji po najechaniu na obraz karuzeli (tylko Karuzela2) |

Hub: [`README.md`](README.md) · Motyw: [`docs/motyw/kolekcja-autora-showcase.md`](../../../docs/motyw/kolekcja-autora-showcase.md)

Sekcja launchera GicleeApp: **Administracja strony** (kafelek «Karuzela»).

---

## Pliki

| Plik | Rola |
|------|------|
| `Komponenty/karuzela/gui.py` | Panel — radio Karuzela1/2 + V1/V2/V3, podgląd, jawne zastosowanie do motywu, przycisk **Cytaty** |
| `Komponenty/karuzela/quotes_gui.py` | Widok cytatów — lista kolekcji, edycja tekstu (przejście w tym samym oknie) |
| `Komponenty/karuzela/quotes_service.py` | Metafield + cache lokalny |
| `Komponenty/karuzela/service.py` | Ustawienia aplikacji + bounded writer `assets/giclee-carousel-config.js` |
| `Komponenty/karuzela/settings.json` | Legacy fallback; aktywny zapis trafia do Roaming AppData |
| `assets/giclee-karuzela.js` | Router + `data-giclee-showcase-look` na `<html>` |
| `assets/giclee-carousel-config.js` | Domyślne wartości po deploy motywu |
| `assets/giclee-artist-collection-showcase.css` | V2 = domyślne tokeny; V1/V3 = override `[data-giclee-showcase-look]` |
| `assets/giclee-karuzela2.css` | V1 = mocniejsze overlaye tła produktu |

---

## Użycie

1. GicleeApp → kafelek **Karuzela**.
2. **Zachowanie:** Karuzela1 lub Karuzela2.
3. **Wygląd sekcji:** V1, V2 lub V3.
4. **Zapisz** — zapisuje wyłącznie ustawienia aplikacji poza repozytorium.
5. **Otwórz podgląd** — zapisuje ustawienia aplikacji i otwiera URL z parametrami `giclee_karuzela`, `giclee_showcase_look` i `giclee_hover_blur`; nie zmienia pliku motywu.
6. **Zastosuj do motywu…** — osobny writer z podglądem diffu, SHA przed/po, frazą `ZASTOSUJ KARUZELĘ`, stale-state check i kopią bezpieczeństwa poza repo.
7. Po zastosowaniu do pliku lokalnego użytkownik osobno decyduje o deployu motywu. Komponent nie uruchamia deployu ani Shopify mutation.
8. **Cytaty…** — przejście do widoku cytatów w tym samym oknie.

Domyślny URL podglądu: `https://gicleeart.eu/collections/jacob-van-ruisdael`.

---

## Writer Safety dla konfiguracji motywu

Zwykłe zapisy ustawień nigdy nie dotykają `assets/giclee-carousel-config.js`.

Jawna akcja writer-a przebiega w dwóch fazach:

1. `build_theme_config_plan(...)`:
   - rozwiązuje dokładnie jeden dozwolony cel,
   - czyta stan bieżący,
   - generuje deterministyczny kandydat,
   - oblicza SHA-256,
   - buduje unified diff,
   - nie tworzy katalogów i niczego nie zapisuje;
2. `apply_theme_config_plan(...)`:
   - wymaga dokładnej frazy `ZASTOSUJ KARUZELĘ`,
   - sprawdza, czy cel nie został zmieniony po preview,
   - blokuje plan przekierowany na inny plik,
   - tworzy dokładną kopię wersji „przed” w Local AppData `backups/Komponenty/karuzela/theme_config/`,
   - wykonuje zapis atomowy,
   - odczytuje plik ponownie i weryfikuje końcowy SHA.

Brak zmian nie tworzy backupu i nie przepisuje pliku.

---

## Cytaty per kolekcja

| Warstwa | Lokalizacja |
|---------|-------------|
| Metafield (lista) | `custom.collection_quotes` (type `json`, storefront `PUBLIC_READ`) |
| Metafield (legacy) | `custom.collection_quote` — pierwszy cytat z listy (kompatybilność) |
| Cache lokalny | Local AppData, legacy fallback `Komponenty/karuzela/data/collection_quotes.json` |

**Wydajność:** lista kolekcji + oba metafieldy cytatów w **jednym** przebiegu GraphQL. Przy starcie UI — ostatni snapshot z cache, potem odświeżenie w tle.

**GUI:** lista cytatów per kolekcja — **Dodaj cytat**, **Usuń zaznaczony**, edytor, **Zapisz cytaty**. Kolumna statusu pokazuje liczbę cytatów.

**Storefront:** overlay w sekcji galerii — przy zmianie autora wybierany cytat z listy, najpierw ten, którego użytkownik jeszcze nie widział. Fallback: pojedynczy `collection_quote`.

Przy pierwszym zapisie komponent tworzy definicję metafield GraphQL. Ten writer Shopify pozostaje osobnym workflow i nie jest częścią zastosowania konfiguracji karuzeli do lokalnego pliku motywu.

---

## Persystencja na storefront

**Karuzela1/2:** URL `?giclee_karuzela=` → `localStorage` `giclee-carousel-version` → `__GICLEE_CAROUSEL_DEFAULT` → Karuzela1.

**Wygląd V1/V2/V3:** URL `?giclee_showcase_look=` → `localStorage` `giclee-showcase-look` → `__GICLEE_SHOWCASE_LOOK_DEFAULT` → V2.

**Rozmycie tła:** URL `?giclee_hover_blur=on|off` → `localStorage` `giclee-karuzela-hover-blur` → `__GICLEE_HOVER_BLUR_ENABLED` → domyślnie wł.

**API w przeglądarce:** `GicleeKaruzela.setVersion('Karuzela2')`, `GicleeKaruzela.setShowcaseLook('V3')`, `GicleeKaruzela.setHoverBlur(true)`.

---

## Deploy motywu

Po jawnej akcji **Zastosuj do motywu…** plik jest zmieniony wyłącznie lokalnie. Deploy pozostaje osobną, świadomą operacją.

Do wdrożenia mogą należeć:

- `assets/giclee-carousel-config.js`
- `assets/giclee-karuzela.js`
- `assets/giclee-artist-collection-showcase.css`
- `assets/giclee-karuzela2.css` (gdy używana Karuzela2)
