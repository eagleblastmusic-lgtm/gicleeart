# Jakość wydruku (PPI / werdykt)

Panel **„Jakość wydruku”** w konfiguratorze mockupu pokazuje werdykt (np. „Beznadziejna”), PPI, wymiary pliku i pasek jakości.

---

## Kod

| Plik | Rola |
|------|------|
| `lib/giclee-print-analysis/giclee-print-analysis.js` | Logika PPI, werdykty, rozmiary M/L/XL |
| `lib/giclee-print-analysis/README.md` | Szczegóły algorytmu |
| `layout/theme.liquid` | `initPmQualityPanel()` — render panelu `#pm-quality-panel` |
| `assets/giclee-photo-mockup.js` | Eventy `pm-image-loaded`, `pm-view-change` |

---

## Jak to działa (skrót)

1. Po wgraniu zdjęcia: `pm-image-loaded` z `widthPx`, `heightPx`, `fileBytes`
2. Przy zmianie rozmiaru M/L/XL lub zoomu: przeliczenie **limiting PPI** dla wybranego formatu A4 ramki (`normalizeShopifySize` — legacy `S` → `M`)
3. Werdykt z progów (cel **300 DPI** w analizie = `TARGET_DPI`)
4. Przy mocnym zoomie używany może być PPI **kadru** (widoczny fragment), nie całego pliku

---

## UI panelu

```
JAKOŚĆ WYDRUKU          A4 · M
Beznadziejna
49 PPI · cel 300 DPI · plik 68 PPI
640×800 px · 0.5 MP · 53 KB
[====············]  pasek
Opis werdyktu…
```

Wymiary pliku: `formatFileInfo()` w `theme.liquid`.

---

## Rozmiary ramki (cm)

Źródło w JS mockupu: `PM_FRAME_SIZES_CM` w `giclee-photo-mockup.js` (M/L/XL) — orientacja pozioma/pionowa zamienia w/h.

Powiązane z wariantami produktu Shopify w konfiguratorze `#pm-config`.

Algorytm (szczegóły): [`../../lib/giclee-print-analysis/README.md`](../../lib/giclee-print-analysis/README.md)  
Mapa zależności: [`../zaleznosci.md`](../zaleznosci.md)
