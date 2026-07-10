# Strona główna — Pre-Hero scroll video

## Pozycja w edytorze

Pierwsza strefa na liście komponentu **Strona główna**:

```text
Pre-Hero — scrollowane wideo
Hero — slideshow
Giclée Art — intro
…
```

Pre-Hero nie jest osobną natywną sekcją Shopify w `templates/index.json`. Front wstawia ją przed istniejące Hero przez zestaw assetów `giclee-home-prehero-*`.

## Pola edytora

- **Sekcja aktywna** — włącza lub usuwa pre-Hero z generowanego snippetu bez kasowania assetów.
- **Film do scrollowania** — upload lub wybór z Shopify Files; puste pole zachowuje lokalny `assets/giclee-home-prehero-scrub.mp4`.
- **Długość całej sekwencji (ekrany)** — np. `6` = `600vh`.
- **Start portalu przed końcem filmu (ekrany)** — np. `2` = portal zaczyna się około `200vh` przed końcem scrubbingu.
- **Wjazd oryginalnego Hero (ekrany)** — np. `1` = `100vh`.
- **Pokaż tekst w portalu**.
- **Tekst przejścia** — każda niepusta linia jest animowana osobno, maksymalnie pięć linii.

Ustawienia trafiają do `config/settings_data.json`, więc są przechowywane osobno wraz z każdym wariantem strony głównej.

## Sekwencja

1. Kurtyna: natywne menu wyjeżdża do góry, dolny czarny pas w dół.
2. Wideo jest sterowane pozycją scrolla.
3. W końcowej części filmu portal otwiera się symetrycznie od środka i pokazuje skonfigurowany tekst.
4. Po zakończeniu portalu od dołu wjeżdża oryginalny Hero Shopify z filmem-kolażem.

## Eksport

`Komponenty/stronaglowna/prehero_integration.py`:

1. rejestruje edytowalną strefę przed Hero,
2. odczytuje i zapisuje wartości w ustawieniach wariantu,
3. owija `write_home_assets()`,
4. eksportuje `window.GICLEE_PREHERO_CONFIG`,
5. wybiera URL filmu z Shopify Files albo lokalny asset awaryjny,
6. zabezpiecza `snippets/giclee-home-stack-critical.liquid` przed utratą integracji po zapisie lub wdrożeniu.

Integracja jest dodawana tylko dla wariantu używającego `home_stack` i gdy lokalny snapshot motywu zawiera wymagane pliki kodu oraz dostępne źródło filmu.
