# Losuj Obraz — Fine Art Oracle

Strona „Losuj Obraz” losuje realny produkt Shopify, uruchamia opcjonalną scenę WebGL i pokazuje wynik w HTML/CSS. System zachowuje fallback CSS, reduced motion i układ desktopowy mieszczący header, scenę oraz footer bez dodatkowego scrolla.

## Warianty designu

| Wariant | Zachowanie |
|---|---|
| **V1 — podstawowa** | Oryginalny portal, tło, narracja, WebGL i wynik bez dodatkowej atmosfery. |
| **V2 — atmosfera muzealna** | Subtelny glow kursora, mgiełka i oszczędny pył z osobnych assetów V2. |
| **V3 — Living Museum Light** | Eliptyczny reflektor galerii, zoptymalizowany pył sprite/canvas, choreografia stanów i światło ekspozycyjne wyniku. |
| **V4 — finał muzealny** | Zachowuje scenę i atmosferę V3, ale dodaje ceremonialny handoff zwycięzcy, większą ekspozycję, transformację portalu w halo, lżejszą oprawę, kuratorską typografię i hierarchię akcji. |

Assety V2, V3 i V4 są ładowane wyłącznie dla aktywnego wariantu. V4 korzysta z tych samych danych i parametrów Living Museum Light co V3, ale ma osobny moduł WebGL oraz osobne assety finału.

## Pliki

| Plik | Rola |
|---|---|
| `templates/page.losuj-produkt.json` | Aktywny wariant strony |
| `sections/giclee-random-artwork.liquid` | Markup, schema i selektywne ładowanie assetów |
| `snippets/giclee-random-artwork-pool.liquid` | Startowa pula Liquid, maks. 50 produktów |
| `assets/giclee-random-artwork.js` | Wspólny model produktów, parser tytułu/roku, losowanie i stany |
| `assets/giclee-random-artwork-living-museum.css` | Warstwa wizualna Living Museum Light |
| `assets/giclee-random-artwork-living-museum.js` | Kontroler światła, pyłu i współdzielonego parallaxu V3/V4 |
| `assets/giclee-random-artwork-webgl.js` | Bazowa scena Three.js dla V1–V3 |
| `assets/giclee-random-artwork-webgl-v4.js` | Izolowana scena V4 z dodatkowym finałem 800 ms |
| `assets/giclee-random-artwork-v4.css` | Oprawa, portal, typografia, akcje i etapy wyniku V4 |
| `assets/giclee-random-artwork-v4.js` | Sekwencja `frame → identity → actions`, reset i cleanup V4 |

## Kontrakt danych dzieła

Vendor produktu jest stały (`Giclee Art`) i nie identyfikuje artysty. Kanoniczny tytuł produktu ma format:

```text
Artysta - Tytuł dzieła
```

Oba źródła puli są normalizowane do:

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

## Choreografia V3/V4

Wspólna atmosfera:

- `idle`: reflektor podąża za kursorem, a pył jest wzmacniany wewnątrz światła;
- hover CTA: lekkie przyciągnięcie światła do przycisku;
- `loading`: światło kieruje się do portalu;
- `drawing`: światło i canvas 2D wygasają, odpowiedzialność przejmuje WebGL;
- `result`: reflektor przechodzi za obraz, a winieta stabilizuje ekspozycję;
- `error`: neutralne, wyciszone światło.

Dodatkowy finał V4:

1. bazowa ściana obrazów zachowuje istniejące wejście, orbitowanie i wybór;
2. zwycięzca stabilizuje się i rośnie około 17% bardziej niż w bazowej scenie;
3. pozostałe karty odsuwają się w głąb i pozostają śladowo widoczne do końca handoffu;
4. pierścienie portalu wygasają, a glow rozszerza się w owalne światło ekspozycyjne;
5. po dodatkowych 800 ms DOM-owa oprawa przejmuje obraz przez kontrolowany crossfade;
6. wynik odsłania kolejno ramę, artystę i tytuł, a na końcu akcje;
7. „Wylosuj ponownie” resetuje etapy, timery, portal i scenę przed kolejnym losowaniem.

## Wynik V4

- maksymalna szerokość oprawy wzrosła z 440 px do 540 px, czyli o około 23%;
- oprawa ma jeden cienki kontur, cienkie passe-partout i spokojny cień;
- portal po wyborze nie pozostaje dominującym kołem — pierścienie zanikają, a halo staje się eliptyczne;
- artysta jest mały, uppercase i champagne; tytuł używa spokojnej typografii heading/serif o wadze 400;
- główna akcja jest ciemnym prostokątnym przyciskiem z subtelną strzałką;
- „Wylosuj ponownie” jest lekką akcją tekstową bez kapsuły i bez konkurencji z głównym CTA.

## Wydajność

Living Museum Light:

- jeden pasywny listener `pointermove` ograniczony do sceny;
- jeden scheduler `requestAnimationFrame` dla reflektora, parallaxu i pyłu;
- domyślnie 120 drobinek, 24 FPS i DPR 1.25;
- sprite 32×32 oraz `drawImage` zamiast `shadowBlur` na każdej cząstce;
- `IntersectionObserver`, `ResizeObserver` i `document.visibilityState` pauzują pracę;
- mobile/coarse pointer, mała pamięć i reduced motion upraszczają dekoracje;
- pełny cleanup listenerów, obserwatorów, RAF i canvasu.

V4 nie dodaje kolejnej ciągłej pętli. Sekwencja HTML wyniku używa dwóch kontrolowanych timeoutów, które są czyszczone przy resecie i odłączeniu komponentu. Osobny moduł WebGL V4 nadal używa jednej pętli RAF.

## Ustawienia Theme Editor i GicleeApp

V3 i V4 współdzielą:

- `living_light_enabled`;
- `living_dust_enabled`;
- `living_light_intensity`;
- `living_dust_particles`;
- `living_dust_opacity`;
- `living_dust_size`;
- `living_dust_speed`;
- `living_dust_fps`;
- `living_dust_dpr_cap`.

## Regresje chronione

Źródło puli, endpoint `/collections/all/products.json`, dobór zwycięzcy, dostępność produktów, link wyniku, fallback CSS, dynamiczny import WebGL, zabezpieczenie przed podwójnym losowaniem i układ stopki pozostają bez zmian funkcjonalnych.
