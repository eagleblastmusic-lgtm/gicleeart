/**
 * GicleeLab — logika analizy wydruku (PPI, fit/fill, werdykt).
 *
 * Skopiowane z: E:\Kopia zapasowa projektów\kalkulator mockup - kopia zapasowa
 * (deploy: https://kalkulator1-henna.vercel.app/)
 *
 * Mapowanie rozmiarów Shopify → formaty druku:
 *   M  → A4
 *   L  → A3+
 *   XL → A2
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.GicleePrintAnalysis = factory();
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  var TARGET_DPI = 300;
  /** Progi werdyktu — zgodne z GicleeLab (kalkulator1-henna.vercel.app). */
  var VERDICT_THRESHOLD_EXCELLENT = 300;
  var VERDICT_THRESHOLD_VERY_GOOD = 240;
  var VERDICT_THRESHOLD_GOOD = 200;
  var VERDICT_THRESHOLD_FAIR = 150;
  var VERDICT_THRESHOLD_MIN = 120;

  /** @type {Record<string, string>} */
  var SHOPIFY_SIZE_TO_FORMAT = {
    M: "A4",
    S: "A4",
    L: "A3+",
    XL: "A2",
  };

  /** @type {Record<string, string>} */
  var FORMAT_TO_SHOPIFY_SIZE = {
    A4: "M",
    "A3+": "L",
    A2: "XL",
  };

  /** @type {{ name: string, widthMm: number, heightMm: number }[]} */
  var FORMATS = [
    { name: "A4", widthMm: 210, heightMm: 297 },
    { name: "A3+", widthMm: 329, heightMm: 483 },
    { name: "A2", widthMm: 420, heightMm: 594 },
  ];

  function mmToIn(mm) {
    return mm / 25.4;
  }

  function inToCm(valueIn) {
    return valueIn * 2.54;
  }

  function clamp(n, min, max) {
    return Math.max(min, Math.min(max, n));
  }

  function fmt(n, digits) {
    digits = digits === undefined ? 1 : digits;
    return Number.isFinite(n) ? n.toFixed(digits) : "—";
  }

  function pct(n, digits) {
    digits = digits === undefined ? 0 : digits;
    return fmt(n, digits) + "%";
  }

  function getFormatByName(name) {
    for (var i = 0; i < FORMATS.length; i++) {
      if (FORMATS[i].name === name) return FORMATS[i];
    }
    return null;
  }

  /**
   * Kod rozmiaru Shopify (M / L / XL). Legacy S → M; trim; wyciąga kod z etykiety wariantu.
   * @param {string} shopifySize
   * @returns {"M"|"L"|"XL"|null}
   */
  function normalizeShopifySize(shopifySize) {
    var raw = String(shopifySize || "").trim();
    if (!raw) return "M";
    var key = raw.toUpperCase();
    if (key === "S") return "M";
    if (SHOPIFY_SIZE_TO_FORMAT[key]) return key;
    if (/\bXL\b/.test(key)) return "XL";
    if (/\bL\b/.test(key)) return "L";
    if (/\bM\b/.test(key)) return "M";
    return null;
  }

  function shopifySizeToFormatName(shopifySize) {
    var key = normalizeShopifySize(shopifySize);
    if (!key) return null;
    return SHOPIFY_SIZE_TO_FORMAT[key] || null;
  }

  function formatNameToShopifySize(formatName) {
    return FORMAT_TO_SHOPIFY_SIZE[formatName] || null;
  }

  function gicleeUi(key, fallback) {
    if (typeof window.__gicleeI18nGet === 'function') return window.__gicleeI18nGet(key, fallback);
    var v = window.__gicleeI18n && window.__gicleeI18n[key];
    if (!v || (typeof v === 'string' && /translation missing/i.test(v))) return fallback;
    return v;
  }

  /**
   * Werdykt jakości na podstawie PPI (z GicleeLab verdict.ts).
   * @param {number} ppi
   */
  function verdictForPpi(ppi) {
    if (!Number.isFinite(ppi)) {
      return {
        label: gicleeUi("print_no_data", "Brak danych"),
        note: gicleeUi("print_upload_prompt", "Wgraj obraz, aby zobaczyć analizę."),
        tone: "gray",
      };
    }
    if (ppi >= VERDICT_THRESHOLD_EXCELLENT) {
      return {
        label: gicleeUi("print_quality_highest", "Najwyższa jakość"),
        note: gicleeUi("print_quality_highest_note", "Maksymalna ostrość, Fine Art, Wydruk premium. Najlepszy odbiór z 20–30 cm"),
        tone: "blue",
      };
    }
    if (ppi >= VERDICT_THRESHOLD_VERY_GOOD) {
      return {
        label: gicleeUi("print_quality_very_good", "Bardzo dobra jakość"),
        note: gicleeUi("print_quality_very_good_note", "Praktycznie brak różnicy względem 300 PPI przy normalnym odbiorze z 30–50 cm"),
        tone: "green",
      };
    }
    if (ppi >= VERDICT_THRESHOLD_GOOD) {
      return {
        label: gicleeUi("print_quality_good", "Dobra jakość"),
        note: gicleeUi("print_quality_good_note", "Nadal dobry wydruk, ale widać mniejszy zapas detalu, zalecana odległość oglądania to 50–80 cm"),
        tone: "green-soft",
      };
    }
    if (ppi >= VERDICT_THRESHOLD_FAIR) {
      return {
        label: gicleeUi("print_quality_average", "Przeciętna jakość"),
        note: gicleeUi("print_quality_average_note", "Efekt wystawowy, lekko miększy, akceptowalne z odległości 80–120 cm"),
        tone: "amber",
      };
    }
    if (ppi >= VERDICT_THRESHOLD_MIN) {
      return {
        label: gicleeUi("print_quality_not_recommended", "Niezalecana"),
        note: gicleeUi("print_quality_low_note", "To już jest za mało PPI do oglądania z bliska, jedynie z dystansu 120 cm i więcej wygląda dobrze"),
        tone: "red",
      };
    }
    return {
      label: gicleeUi("print_quality_hopeless", "Beznadziejna"),
      note: gicleeUi("print_quality_critical_note", "Rozdzielczość krytycznie niska — wyraźna pixelacja i brak detalu nawet z daleka; do tego formatu nie nadaje się"),
      tone: "red",
    };
  }

  function barColorForPpi(ppi) {
    if (ppi >= VERDICT_THRESHOLD_EXCELLENT) return "blue";
    if (ppi >= VERDICT_THRESHOLD_VERY_GOOD) return "green";
    if (ppi >= VERDICT_THRESHOLD_GOOD) return "green-soft";
    if (ppi >= VERDICT_THRESHOLD_FAIR) return "amber";
    return "red";
  }

  /**
   * Analiza jednego formatu (usePrintAnalysis / sizeCalculator.ts).
   * @param {{ widthPx: number, heightPx: number }} image
   * @param {{ name: string, widthMm: number, heightMm: number }} format
   * @param {"portrait"|"landscape"} orientation
   */
  /**
   * @param {{ widthPx: number, heightPx: number }|undefined} visibleSource
   *   Widoczny fragment obrazu w px źródła (zoom/kadrowanie mockupu).
   */
  function calculateFormatResult(image, format, orientation, visibleSource) {
    orientation = orientation || (image.widthPx >= image.heightPx ? "landscape" : "portrait");
    var iw = image.widthPx;
    var ih = image.heightPx;
    var widthMm = orientation === "portrait" ? format.widthMm : format.heightMm;
    var heightMm = orientation === "portrait" ? format.heightMm : format.widthMm;
    var fwIn = mmToIn(widthMm);
    var fhIn = mmToIn(heightMm);
    var fwPx = fwIn * TARGET_DPI;
    var fhPx = fhIn * TARGET_DPI;

    var fitScale = Math.min(fwPx / iw, fhPx / ih);
    var fitPxW = iw * fitScale;
    var fitPxH = ih * fitScale;

    var fillScale = Math.max(fwPx / iw, fhPx / ih);
    var cropPxW = fwPx / fillScale;
    var cropPxH = fhPx / fillScale;

    var cropW = Math.max(0, iw - cropPxW);
    var cropH = Math.max(0, ih - cropPxH);
    var cropPctW = (cropW / iw) * 100;
    var cropPctH = (cropH / ih) * 100;
    var croppedAreaPct = 100 - ((cropPxW * cropPxH) / (iw * ih)) * 100;

    var vw = iw;
    var vh = ih;
    if (
      visibleSource &&
      Number.isFinite(visibleSource.widthPx) &&
      Number.isFinite(visibleSource.heightPx) &&
      visibleSource.widthPx > 0 &&
      visibleSource.heightPx > 0
    ) {
      vw = visibleSource.widthPx;
      vh = visibleSource.heightPx;
    }

    var limitingPpi = Math.min(vw / fwIn, vh / fhIn);
    var quality = clamp((limitingPpi / TARGET_DPI) * 100, 0, 120);
    var verdict = verdictForPpi(limitingPpi);

    return {
      name: format.name,
      shopifySize: formatNameToShopifySize(format.name),
      widthMm: widthMm,
      heightMm: heightMm,
      fwIn: fwIn,
      fhIn: fhIn,
      fwPx: fwPx,
      fhPx: fhPx,
      fitWidthCm: inToCm(fitPxW / TARGET_DPI),
      fitHeightCm: inToCm(fitPxH / TARGET_DPI),
      fillWidthCm: inToCm(fwPx / TARGET_DPI),
      fillHeightCm: inToCm(fhPx / TARGET_DPI),
      cropPctW: cropPctW,
      cropPctH: cropPctH,
      croppedAreaPct: croppedAreaPct,
      limitingPpi: limitingPpi,
      quality: quality,
      neededPixelsW: fwPx,
      neededPixelsH: fhPx,
      verdict: verdict,
    };
  }

  /**
   * Analiza wszystkich formatów A4 / A3+ / A2.
   * @param {{ widthPx: number, heightPx: number }} image
   * @param {"portrait"|"landscape"|undefined} orientation
   */
  function analyseAllFormats(image, orientation) {
    if (!image || !image.widthPx || !image.heightPx) return [];
    if (!orientation) {
      orientation = image.widthPx >= image.heightPx ? "landscape" : "portrait";
    }
    return FORMATS.map(function (format) {
      return calculateFormatResult(image, format, orientation);
    });
  }

  /**
   * Najlepszy format (najwyższe PPI).
   */
  function bestFormatForImage(image, orientation) {
    var results = analyseAllFormats(image, orientation);
    if (!results.length) return null;
    return results.slice().sort(function (a, b) {
      return b.limitingPpi - a.limitingPpi;
    })[0];
  }

  /**
   * Analiza dla rozmiaru ze sklepu (M / L / XL).
   * @param {string} shopifySize — "M" | "L" | "XL" (legacy: "S" → A4)
   */
  function analyseForShopifySize(image, shopifySize, orientation, visibleSource) {
    var formatName = shopifySizeToFormatName(shopifySize);
    if (!formatName) return null;
    var format = getFormatByName(formatName);
    if (!format || !image) return null;
    return calculateFormatResult(image, format, orientation, visibleSource);
  }

  /* ── mockupMath.ts (kadrowanie w ramce) ── */

  function clampPan(value, contentSize, frameSize) {
    if (!Number.isFinite(contentSize) || !Number.isFinite(frameSize)) return value;
    if (contentSize <= frameSize) return (frameSize - contentSize) / 2;
    return clamp(value, frameSize - contentSize, 0);
  }

  function getCropMetrics(frameW, frameH, scaledW, scaledH, x, y) {
    var visibleW = clamp(Math.min(frameW, scaledW + x) - Math.max(0, x), 0, scaledW);
    var visibleH = clamp(Math.min(frameH, scaledH + y) - Math.max(0, y), 0, scaledH);
    return {
      cropPctW: clamp(100 - (visibleW / Math.max(scaledW, 1)) * 100, 0, 100),
      cropPctH: clamp(100 - (visibleH / Math.max(scaledH, 1)) * 100, 0, 100),
      croppedAreaPct: clamp(
        100 - ((visibleW * visibleH) / Math.max(scaledW * scaledH, 1)) * 100,
        0,
        100
      ),
    };
  }

  return {
    TARGET_DPI: TARGET_DPI,
    VERDICT_THRESHOLD_EXCELLENT: VERDICT_THRESHOLD_EXCELLENT,
    VERDICT_THRESHOLD_VERY_GOOD: VERDICT_THRESHOLD_VERY_GOOD,
    VERDICT_THRESHOLD_GOOD: VERDICT_THRESHOLD_GOOD,
    VERDICT_THRESHOLD_FAIR: VERDICT_THRESHOLD_FAIR,
    VERDICT_THRESHOLD_MIN: VERDICT_THRESHOLD_MIN,
    FORMATS: FORMATS,
    SHOPIFY_SIZE_TO_FORMAT: SHOPIFY_SIZE_TO_FORMAT,
    FORMAT_TO_SHOPIFY_SIZE: FORMAT_TO_SHOPIFY_SIZE,
    mmToIn: mmToIn,
    inToCm: inToCm,
    clamp: clamp,
    fmt: fmt,
    pct: pct,
    getFormatByName: getFormatByName,
    normalizeShopifySize: normalizeShopifySize,
    shopifySizeToFormatName: shopifySizeToFormatName,
    formatNameToShopifySize: formatNameToShopifySize,
    verdictForPpi: verdictForPpi,
    barColorForPpi: barColorForPpi,
    calculateFormatResult: calculateFormatResult,
    analyseAllFormats: analyseAllFormats,
    bestFormatForImage: bestFormatForImage,
    analyseForShopifySize: analyseForShopifySize,
    clampPan: clampPan,
    getCropMetrics: getCropMetrics,
  };
});
