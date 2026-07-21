# Losuj Obraz — Fine Art Oracle

Strona „Losuj Obraz” losuje realny produkt Shopify, uruchamia opcjonalną scenę WebGL i pokazuje wynik w HTML/CSS. System zachowuje fallback CSS, reduced motion i układ desktopowy mieszczący header, scenę oraz footer bez dodatkowego scrolla.

## Warianty designu

| Wariant | Zachowanie |
|---|---|
| **V1 — podstawowa** | Oryginalny portal, tło, narracja, WebGL i wynik bez dodatkowej atmosfery. |
| **V2 — atmosfera muzealna** | Subtelny glow kursora, mgiełka i oszczędny pył z osobnych assetów V2. |
| **V3 — Living Museum Light** | Eliptyczny reflektor galerii, pył widoczny głównie w świetle, choreografia stanów, handoff do WebGL i światło ekspozycyjne wyniku. |

V2 i V3 są odseparowane. Assety atmosfery są ładowane wyłącznie dla wybranego wariantu.

## Pliki

| Plik | Rola |
|---|---|
| `templates/page.losuj-produkt.json` | Aktywny wariant strony |
| `sections/giclee-random-artwork.liquid` | Markup, schema i selektywne ładowanie assetów |
| `snippets/giclee-random-artwork-pool.liquid` | Startowa pula Liquid, maks. 50 produktów |
| `assets/giclee-random-artwork.js` | Wspólny model produktów, parser tytułu/roku, losowanie i stany |
| `assets/giclee-random-artwork-living-museum.css` | Warstwa wizualna V3 |
| `assets/giclee-random-artwork-living-museum.js` | Kontroler światła, pyłu i współdzielonego parallaxu V3 |
| `assets/giclee-random-artwork-webgl.js` | Dynamiczna scena Three.js; bez zmian w V3 |

## Kontrakt danych dzieła

Vendor produktu jest stały (`Giclee Art`) i nie identyfikuje artysty. Kanoniczny tytuł produktu ma format:

```text
Artysta - Tytuł dzieła
```

Dlatego oba źródła puli są normalizowane do:

```js
{
  rawTitle,
  title,
  year,
  artist,
  url,
  image,
  imageAlt,
  available
}
```

Pula Liquid przekazuje `rawTitle` i artystę wyciętego z prefiksu. Pula AJAX przekazuje pełny tytuł, a ten sam normalizator JS rozdziela artystę i dzieło. Nazwy zapisane katalogowo, np. `Gogh, Vincent van`, są prezentowane jako `Vincent van Gogh`, zgodnie z istniejącą konwencją cząstek nazwiska.

`parseArtworkIdentity(rawTitle)` najpierw wydobywa rok lub zakres lat z pełnego tekstu, następnie wybiera tytuł przed pierwszym nawiasem, usuwa rok z głównego tytułu i czyści końcową interpunkcję. Alternatywne tytuły w nawiasach nie są wyświetlane.

## Choreografia V3

- `idle`: reflektor łagodnie podąża za kursorem, pył jest widoczny głównie wewnątrz światła;
- hover CTA: subtelne podbicie i lekkie przyciągnięcie w stronę przycisku;
- `loading`: światło kieruje się do portalu, pył delikatnie zyskuje obecność;
- `drawing`: światło i canvas 2D wygasają, a odpowiedzialność przejmuje istniejący WebGL;
- `result`: reflektor przechodzi za wylosowany obraz, pył prawie zanika, włącza się lekka winieta ekspozycyjna;
- `error`: neutralne, wyciszone światło bez czerwonych efektów.

## Wydajność V3

- jeden pasywny listener `pointermove` ograniczony do sceny;
- jeden scheduler `requestAnimationFrame` dla reflektora, parallaxu i pyłu;
- pył rysowany maks. 24 FPS, canvas DPR ograniczony do 1.35;
- 40–70 drobinek desktopowych;
- brak odczytów layoutu w każdej klatce;
- `IntersectionObserver`, `ResizeObserver` i `document.visibilityState` pauzują pracę;
- inicjalizacja pyłu przez `requestIdleCallback` z fallbackiem;
- mobile/coarse pointer, mała pamięć i reduced motion wyłączają dekoracyjny pył lub tracking;
- pełny cleanup listenerów, obserwatorów, RAF i canvasu w `disconnectedCallback`.

## Ustawienia Theme Editor dla V3

- `living_light_enabled` — reflektor kursora;
- `living_dust_enabled` — pył ambientowy;
- `living_light_intensity` — intensywność 0–100, domyślnie 45.

Techniczne parametry cząsteczek i ruchu pozostają stałymi w kodzie.

## Regresje chronione

Źródło puli, endpoint `/collections/all/products.json`, prawdopodobieństwo losowania, CTA, dynamiczny import WebGL, fallback CSS, zabezpieczenie przed podwójnym losowaniem i układ stopki pozostają bez zmian funkcjonalnych.
