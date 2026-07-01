# GicleeLab — logika analizy wydruku

Kopia matematyki z projektu GicleeLab (React/Vite):

- **Źródło:** `E:\Kopia zapasowa projektów\kalkulator mockup - kopia zapasowa`
- **Live:** https://kalkulator1-henna.vercel.app/

## Plik

- `giclee-print-analysis.js` — samodzielny moduł (browser: `window.GicleePrintAnalysis`, Node: `require`)

## Mapowanie rozmiarów Shopify

| Shopify | Format GicleeLab | Wymiary (mm)   |
|---------|------------------|----------------|
| **S**   | A4               | 210 × 297      |
| **L**   | A3+              | 329 × 483      |
| **XL**  | A2               | 420 × 594      |

## Stałe

- `TARGET_DPI = 300`
- Werdykt (jak GicleeLab): ≥300 najwyższa, ≥240 bardzo dobra, ≥200 dobra, ≥150 przeciętna, ≥120 niezalecana, &lt;120 beznadziejna
- PPI w werdykcie liczone z **całego pliku**; opcjonalnie `visibleSource` tylko do podglądu kadru (zoom)

## Przykład

```javascript
var gpa = window.GicleePrintAnalysis;
var image = { widthPx: 4000, heightPx: 6000 };

// Wszystkie formaty
var all = gpa.analyseAllFormats(image, "portrait");

// Rozmiar ze sklepu
var forL = gpa.analyseForShopifySize(image, "L", "portrait");
// → format A3+, limitingPpi, verdict, cropPctW/H, …

// Mapowanie nazw
gpa.shopifySizeToFormatName("XL"); // "A2"
gpa.formatNameToShopifySize("A4"); // "S"
```

## Oryginalne pliki w kalkulatorze

| Ten moduł              | Źródło TS                          |
|------------------------|------------------------------------|
| `calculateFormatResult`| `sizeCalculator.ts`, `usePrintAnalysis.ts` |
| `verdictForPpi`        | `verdict.ts`                       |
| `mmToIn`, `inToCm`     | `imageMath.ts`                     |
| `getCropMetrics`       | `mockupMath.ts`                    |
| `FORMATS`, `TARGET_DPI`| `constants/printLab.ts`            |
