# Strona główna — Pre-Hero scroll video

## Pozycja w edytorze

Pierwsza strefa na liście komponentu **Strona główna**:

```text
Pre-Hero — scrollowane wideo
Hero — slideshow
Giclée Art — intro
…
```

Pre-Hero nie jest osobną natywną sekcją Shopify w `templates/index.json`. Front wstawia ją przed istniejące Hero przez zestaw assetów `giclee-home-prehero-*` oraz `giclee-home-hero-horizontal-curtain.*`.

## Pola edytora

- **Sekcja aktywna** — włącza lub usuwa pre-Hero z generowanego snippetu bez kasowania assetów.
- **Film do scrollowania** — upload lub wybór z Shopify Files; puste pole zachowuje lokalny `assets/giclee-home-prehero-scrub.mp4`.
- **Długość całej sekwencji (ekrany)** — np. `6` = `600vh`.
- **Start portalu przed końcem filmu (ekrany)** — np. `2` = portal zaczyna się około `200vh` przed końcem scrubbingu.
- **Wjazd oryginalnego Hero (ekrany)** — np. `1` = `100vh`.
- **Pokaż tekst w portalu**.
- **Tekst przejścia** — każda niepusta linia jest animowana osobno, maksymalnie pięć linii.
- **Pozioma kurtyna Hero → Giclée Art** — włącza drugie przejście po wycentrowaniu kolażu.
- **Postój wycentrowanego Hero (ekrany)** — domyślnie `1`, czyli `100vh` spokojnego scrolla bez ruchu filmu.
- **Otwieranie poziomej kurtyny (ekrany)** — domyślnie `1`, czyli pełne rozdzielenie górnej i dolnej części filmu podczas `100vh`.

Ustawienia trafiają do `config/settings_data.json`, więc są przechowywane osobno wraz z każdym wariantem strony głównej.

## Sekwencja

1. Natywne menu wyjeżdża do góry, a dolny czarny pas w dół.
2. Wideo jest sterowane pozycją scrolla.
3. W końcowej części filmu portal otwiera się symetrycznie od środka i pokazuje skonfigurowany tekst.
4. Po zakończeniu portalu od dołu wjeżdża oryginalny Hero Shopify z filmem-kolażem.
5. Hero pozostaje wycentrowany przez skonfigurowany pusty odcinek scrolla.
6. Pozioma szczelina dzieli ten sam działający film na część górną i dolną; otwarcie rozszerza się ku krawędziom.
7. Pod kurtyną jest wizualna kopia prawdziwej sekcji `Giclée Art — intro`; po pełnym otwarciu następuje bezszwowy hand-off do oryginalnej sekcji Shopify.

## Eksport

`Komponenty/stronaglowna/prehero_integration.py`:

1. rejestruje edytowalną strefę przed Hero,
2. odczytuje i zapisuje wartości w ustawieniach wariantu,
3. owija `write_home_assets()`,
4. eksportuje `window.GICLEE_PREHERO_CONFIG`,
5. wybiera URL filmu z Shopify Files albo lokalny asset awaryjny,
6. zabezpiecza `snippets/giclee-home-stack-critical.liquid` przed utratą integracji po zapisie lub wdrożeniu,
7. ładuje assety pionowego portalu i poziomej kurtyny.

Integracja jest dodawana tylko dla wariantu używającego `home_stack` i gdy lokalny snapshot motywu zawiera wymagane pliki kodu oraz dostępne źródło filmu.
