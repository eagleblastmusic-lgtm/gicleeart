/* ============================================================
   CENY W MARKETINGU — APP LOGIC v3
   ============================================================ */

// ---------- BREAKDOWN KOSZTÓW (z analizy użytkownika) ----------
// Każda wartość w PLN. Wartości można edytować w UI (sekcja 13).
// Zapisywane do localStorage pod kluczem "cwm-costs-v1".
const COST_BREAKDOWN_DEFAULT = {
  // RAMA — materiały budowy ramy
  drewno:           { M: { pine: 19.17, oak: 39.17 }, L: { pine: 26.67, oak: 56.67 }, XL: { pine: 34.17, oak: 74.17 }, group: "rama" },
  passepartout:     { M: { pine: 10.00, oak: 10.00 }, L: { pine: 25.00, oak: 25.00 }, XL: { pine: 40.00, oak: 40.00 }, group: "rama" },
  foamboard:        { M: { pine:  7.00, oak:  7.00 }, L: { pine: 19.01, oak: 19.01 }, XL: { pine: 26.93, oak: 26.93 }, group: "rama" },
  zawieszka:        { M: { pine:  0.40, oak:  0.40 }, L: { pine:  0.40, oak:  0.40 }, XL: { pine:  0.40, oak:  0.40 }, group: "rama" },
  rmcPrecolor:      { M: { pine:  1.25, oak:  1.25 }, L: { pine:  1.99, oak:  1.99 }, XL: { pine:  2.49, oak:  2.49 }, group: "rama" },
  rmc2c:            { M: { pine:  2.97, oak:  2.97 }, L: { pine:  4.74, oak:  4.74 }, XL: { pine:  5.93, oak:  5.93 }, group: "rama" },
  klej:             { M: { pine:  0.09, oak:  0.09 }, L: { pine:  0.09, oak:  0.09 }, XL: { pine:  0.09, oak:  0.09 }, group: "rama" },
  energiaCiecie:    { M: { pine:  0.28, oak:  0.28 }, L: { pine:  0.28, oak:  0.28 }, XL: { pine:  0.28, oak:  0.28 }, group: "rama" },
  energiaSzlif:     { M: { pine:  1.10, oak:  1.10 }, L: { pine:  1.65, oak:  1.65 }, XL: { pine:  2.20, oak:  2.20 }, group: "rama" },
  papierScierny:    { M: { pine:  0.86, oak:  0.96 }, L: { pine:  0.86, oak:  0.96 }, XL: { pine:  0.86, oak:  0.96 }, group: "rama" },
  rekawiczki:       { M: { pine:  0.23, oak:  0.23 }, L: { pine:  0.23, oak:  0.23 }, XL: { pine:  0.23, oak:  0.23 }, group: "rama" },
  szmatka:          { M: { pine:  0.42, oak:  0.42 }, L: { pine:  0.42, oak:  0.42 }, XL: { pine:  0.42, oak:  0.42 }, group: "rama" },
  // WYDRUK
  hahnemuhle:       { M: { pine: 10.63, oak: 10.63 }, L: { pine: 25.04, oak: 25.04 }, XL: { pine: 37.74, oak: 37.74 }, group: "wydruk" },
  kosztWydruku:     { M: { pine:  3.71, oak:  3.71 }, L: { pine:  9.43, oak:  9.43 }, XL: { pine: 14.81, oak: 14.81 }, group: "wydruk" },
  tasmaBezkwasowa:  { M: { pine:  0.52, oak:  0.52 }, L: { pine:  0.71, oak:  0.71 }, XL: { pine:  0.84, oak:  0.84 }, group: "wydruk" },
  // OPAKOWANIE + WYSYŁKA
  karton:           { M: { pine:  3.20, oak:  5.80 }, L: { pine:  5.80, oak:  3.75 }, XL: { pine:  9.90, oak:  9.90 }, group: "opakowanie" },
  wysylka:          { M: { pine: 12.71, oak: 12.71 }, L: { pine: 12.71, oak: 12.71 }, XL: { pine: 12.71, oak: 12.71 }, group: "opakowanie" },
  // ROBOCIZNA (dodane — Twoja kalkulacja tego nie zawierała)
  robocizna:        { M: { pine: 25.00, oak: 30.00 }, L: { pine: 35.00, oak: 45.00 }, XL: { pine: 50.00, oak: 65.00 }, group: "robocizna" },
};

const COST_LABELS = {
  drewno:          { name: "Drewno",                group: "Rama" },
  passepartout:    { name: "Passepartout",          group: "Rama" },
  foamboard:       { name: "Foamboard biała",       group: "Rama" },
  zawieszka:       { name: "Zawieszka",             group: "Rama" },
  rmcPrecolor:     { name: "RMC Precolor 1L",       group: "Rama" },
  rmc2c:           { name: "RMC 2C 1L",             group: "Rama" },
  klej:            { name: "Klej",                  group: "Rama" },
  energiaCiecie:   { name: "Energia cięcie",        group: "Rama" },
  energiaSzlif:    { name: "Energia szlif",         group: "Rama" },
  papierScierny:   { name: "Papier ścierny P80/P120", group: "Rama" },
  rekawiczki:      { name: "Rękawiczki nitrylowe",  group: "Rama" },
  szmatka:         { name: "Szmatka mikrofibra",    group: "Rama" },
  hahnemuhle:      { name: "Hahnemühle Photo Rag 308", group: "Wydruk" },
  kosztWydruku:    { name: "Koszt wydruku (tusz)",  group: "Wydruk" },
  tasmaBezkwasowa: { name: "Taśma bezkwasowa",      group: "Wydruk" },
  karton:          { name: "Karton",                group: "Opakowanie" },
  wysylka:         { name: "Wysyłka DPD",           group: "Opakowanie" },
  robocizna:       { name: "Robocizna (montaż + QC)", group: "Robocizna" },
};

// Aktywne koszty — wczytywane z localStorage lub domyślne
let ACTIVE_COSTS = (() => {
  try {
    const stored = localStorage.getItem("cwm-costs-v1");
    if (stored) return JSON.parse(stored);
  } catch (e) { /* ignore */ }
  return JSON.parse(JSON.stringify(COST_BREAKDOWN_DEFAULT));
})();

function calcCost(size, wood) {
  let total = 0;
  for (const key of Object.keys(COST_LABELS)) {
    const item = ACTIVE_COSTS[key];
    if (item && item[size] && typeof item[size][wood] === "number") {
      total += item[size][wood];
    }
  }
  return Math.round(total * 100) / 100;
}

function getCostsForVariant(size, wood) {
  return calcCost(size, wood);
}

// ---------- DANE: 3 STRATEGIE CENOWE (koszty z breakdown) ----------
function buildStrategyProducts(prices) {
  const out = {};
  for (const size of ["M", "L", "XL"]) {
    out[size] = {};
    for (const wood of ["pine", "oak"]) {
      out[size][wood] = {
        cost: getCostsForVariant(size, wood),
        price: prices[size][wood].price,
        anchor: prices[size][wood].anchor,
      };
    }
  }
  return out;
}

const STRATEGY_PRICES = {
  penetration: {
    M:  { pine: { price: 199,  anchor: 249  }, oak:  { price: 299,  anchor: 349  } },
    L:  { pine: { price: 499,  anchor: 599  }, oak:  { price: 749,  anchor: 899  } },
    XL: { pine: { price: 899,  anchor: 1099 }, oak:  { price: 1199, anchor: 1399 } },
  },
  current: {
    M:  { pine: { price: 299,  anchor: 349  }, oak:  { price: 399,  anchor: 499  } },
    L:  { pine: { price: 699,  anchor: 849  }, oak:  { price: 999,  anchor: 1199 } },
    XL: { pine: { price: 1199, anchor: 1399 }, oak:  { price: 1499, anchor: 1799 } },
  },
  premium: {
    M:  { pine: { price: 399,  anchor: 499  }, oak:  { price: 549,  anchor: 649  } },
    L:  { pine: { price: 899,  anchor: 1099 }, oak:  { price: 1299, anchor: 1499 } },
    XL: { pine: { price: 1599, anchor: 1899 }, oak:  { price: 1999, anchor: 2399 } },
  },
};

const STRATEGIES = {
  penetration: { label: "Penetracja", desc: "Niższe ceny, większy wolumen — dla testu rynku PL i wejścia do nowych kategorii.", get products() { return buildStrategyProducts(STRATEGY_PRICES.penetration); } },
  current:     { label: "Aktualna (premium-mid)", desc: "Premium positioning z bardzo wysoką marżą (~80%). Wymaga storytellingu (Hahnemühle, giclée, autorska selekcja).", get products() { return buildStrategyProducts(STRATEGY_PRICES.current); } },
  premium:     { label: "Ultra-premium", desc: "Pozycjonowanie galeryjne, edycje limitowane. Niski wolumen, najwyższa marża absolutna. Wymaga silnego brandingu.", get products() { return buildStrategyProducts(STRATEGY_PRICES.premium); } },
};

const PRODUCT_META = {
  M:  { label: "M — A4",   frame: "36 × 27 cm",  paper: "Hahnemühle Photo Rag 308, A4"  },
  L:  { label: "L — A3+",  frame: "59 × 43 cm",  paper: "Hahnemühle Photo Rag 308, A3+" },
  XL: { label: "XL — A2",  frame: "72 × 55 cm",  paper: "Hahnemühle Photo Rag 308, A2"  },
};

const MARKETS = {
  pl: { name: "Polska",       currency: "PLN", markup: 0  },
  es: { name: "Hiszpania",    currency: "EUR", markup: 5  },
  it: { name: "Włochy",       currency: "EUR", markup: 5  },
  eu: { name: "Europa (EN)",  currency: "EUR", markup: 8  },
  fr: { name: "Francja",      currency: "EUR", markup: 10 },
  de: { name: "Niemcy",       currency: "EUR", markup: 15 },
  nl: { name: "Holandia",     currency: "EUR", markup: 15 },
};

// Aktualny kurs EUR/PLN (kwiecień 2026 ~4.25)
const PLN_TO_EUR = 1 / 4.25;

const MAGIC_PLN = [
  99, 129, 149, 179, 199, 229, 249, 279, 299, 329, 349, 379, 399, 449, 499,
  549, 599, 649, 699, 749, 799, 849, 899, 949, 999, 1099, 1199, 1299, 1399,
  1499, 1599, 1699, 1799, 1899, 1999, 2199, 2399, 2499, 2799, 2999,
];
const MAGIC_EUR = [
  19, 29, 39, 49, 59, 69, 79, 89, 99, 109, 119, 129, 139, 149, 159, 169, 179,
  189, 199, 219, 229, 249, 269, 279, 299, 319, 329, 349, 369, 379, 399, 429,
  449, 469, 499, 529, 549, 579, 599, 649, 699, 749, 799,
];

// ---------- STAN ----------
let currentStrategy = "current";

function getActiveProducts() {
  return STRATEGIES[currentStrategy].products;
}

// ---------- HELPERY ----------
function roundUpToMagic(value, currency) {
  const scale = currency === "PLN" ? MAGIC_PLN : MAGIC_EUR;
  for (const m of scale) if (m >= value) return m;
  return Math.ceil(value / 100) * 100;
}

function roundDownToMagic(value, currency) {
  const scale = currency === "PLN" ? MAGIC_PLN : MAGIC_EUR;
  let last = scale[0];
  for (const m of scale) {
    if (m > value) return last;
    last = m;
  }
  return last;
}

function formatPrice(value, currency) {
  if (currency === "PLN") return Math.round(value).toLocaleString("pl-PL") + " zł";
  return Math.round(value).toLocaleString("de-DE") + " €";
}

function computePrice(productKey, wood, marketKey) {
  const products = getActiveProducts();
  const market = MARKETS[marketKey];
  const variant = products[productKey][wood];

  const basePLN = variant.price;
  const anchorPLN = variant.anchor;

  let raw, anchorRaw;
  if (market.currency === "PLN") {
    raw = basePLN;
    anchorRaw = anchorPLN;
  } else {
    raw = basePLN * PLN_TO_EUR * (1 + market.markup / 100);
    anchorRaw = anchorPLN * PLN_TO_EUR * (1 + market.markup / 100);
  }

  const final = roundUpToMagic(raw, market.currency);
  const anchor = roundUpToMagic(anchorRaw, market.currency);
  const discount = Math.round(((anchor - final) / anchor) * 100);
  const margin = market.currency === "PLN"
    ? final - variant.cost
    : final - variant.cost * PLN_TO_EUR * (1 + market.markup / 100);
  const marginPct = Math.round((margin / final) * 100);

  return {
    final, anchor, discount,
    margin: Math.round(margin), marginPct,
    currency: market.currency,
    cost: variant.cost,
  };
}

// ============================================================
// THEME TOGGLE
// ============================================================
function initTheme() {
  const stored = localStorage.getItem("cwm-theme");
  const initial = stored || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  setTheme(initial);

  document.querySelectorAll("[data-set-theme]").forEach((btn) => {
    btn.addEventListener("click", () => setTheme(btn.dataset.setTheme));
  });
}

function setTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("cwm-theme", theme);
  document.querySelectorAll("[data-set-theme]").forEach((btn) => {
    btn.classList.toggle("is-active", btn.dataset.setTheme === theme);
  });
  renderMarginChart();
}

// ============================================================
// STRATEGIA CENOWA — przełącznik
// ============================================================
function initStrategy() {
  const stored = localStorage.getItem("cwm-strategy");
  if (stored && STRATEGIES[stored]) currentStrategy = stored;

  document.querySelectorAll("[data-set-strategy]").forEach((btn) => {
    btn.classList.toggle("is-active", btn.dataset.setStrategy === currentStrategy);
    btn.addEventListener("click", () => setStrategy(btn.dataset.setStrategy));
  });

  updateStrategyDescription();
}

function setStrategy(key) {
  if (!STRATEGIES[key]) return;
  currentStrategy = key;
  localStorage.setItem("cwm-strategy", key);

  document.querySelectorAll("[data-set-strategy]").forEach((btn) => {
    btn.classList.toggle("is-active", btn.dataset.setStrategy === key);
  });
  updateStrategyDescription();

  // Przeliczamy wszystkie sekcje
  refreshAllPrices();
}

function updateStrategyDescription() {
  const el = document.getElementById("strategy-desc");
  if (el) el.textContent = STRATEGIES[currentStrategy].desc;

  // Update stats: średnia marża dla aktywnej strategii
  const products = getActiveProducts();
  let totalCost = 0, totalPrice = 0, count = 0;
  for (const p of Object.values(products)) {
    for (const wood of ["pine", "oak"]) {
      totalCost += p[wood].cost;
      totalPrice += p[wood].price;
      count++;
    }
  }
  const avgMarkup = (totalPrice / totalCost).toFixed(2);
  const avgMarginPct = Math.round(((totalPrice - totalCost) / totalPrice) * 100);
  const avgPrice = Math.round(totalPrice / count);

  ["strategy-markup", "strategy-markup-mini"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.textContent = avgMarkup + "×";
  });
  ["strategy-margin", "strategy-margin-mini"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.textContent = avgMarginPct + "%";
  });
  ["strategy-avg", "strategy-avg-mini"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.textContent = formatPrice(avgPrice, "PLN");
  });
}

function refreshAllPrices() {
  if (typeof updateCalculator === "function") updateCalculator();
  if (typeof updateSalesSim === "function") updateSalesSim();
  if (typeof updateWhatIf === "function") updateWhatIf();
  renderMarginTable();
  renderMarginChart();
  renderPricingTable();
  renderProductCards();
  renderBundles();
  renderStrategyCompare();
}

// ============================================================
// PRODUCT CARDS — render
// ============================================================
function renderProductCards() {
  const container = document.getElementById("product-cards");
  if (!container) return;
  const products = getActiveProducts();
  const sizes = [
    { key: "M",  name: "Entry · A4",       tag: "Wejście w kategorię",   tagCls: "neutral", desc: "Korytarz, biuro, sypialnia" },
    { key: "L",  name: "Bestseller · A3+", tag: "Najczęstszy wybór",     tagCls: "success", desc: "Salon, jadalnia, gabinet" },
    { key: "XL", name: "Statement · A2",   tag: "Lux / kotwica",         tagCls: "gold",    desc: "Salon nad sofą, hol, hotel" },
  ];
  const printSize = { M: "A4 (21 × 29,7 cm)", L: "A3+ (32,9 × 48,3 cm)", XL: "A2 (42 × 59,4 cm)" };

  container.innerHTML = sizes.map((s) => {
    const p = products[s.key];
    const pineMargin = Math.round(((p.pine.price - p.pine.cost) / p.pine.price) * 100);
    const oakMargin = Math.round(((p.oak.price - p.oak.cost) / p.oak.price) * 100);
    return `<article class="product">
      <header class="product__head">
        <div>
          <div class="product__size">${s.key}</div>
          <div class="product__name">${s.name}</div>
        </div>
        <span class="pill pill--${s.tagCls}">${s.tag}</span>
      </header>
      <div class="product__body">
        <ul class="spec-list">
          <li><span>Wymiar ramy</span><span>${PRODUCT_META[s.key].frame}</span></li>
          <li><span>Wydruk</span><span>${printSize[s.key]}</span></li>
          <li><span>Papier</span><span>Photo Rag 308</span></li>
          <li><span>Passepartout</span><span>Tak</span></li>
          <li><span>Pasuje do</span><span>${s.desc}</span></li>
        </ul>
        <div class="product__pricing">
          <div class="price-block">
            <div class="price-block__label">Sosna</div>
            <div class="price-block__value">${formatPrice(p.pine.price, "PLN")}</div>
            <div class="price-block__sub">koszt ~${p.pine.cost} zł · marża ${pineMargin}%</div>
          </div>
          <div class="price-block price-block--oak">
            <div class="price-block__label">Dąb</div>
            <div class="price-block__value">${formatPrice(p.oak.price, "PLN")}</div>
            <div class="price-block__sub">koszt ~${p.oak.cost} zł · marża ${oakMargin}%</div>
          </div>
        </div>
      </div>
    </article>`;
  }).join("");
}

// ============================================================
// KALKULATOR
// ============================================================
let updateCalculator = () => {};
function initCalculator() {
  const sizeSel = document.getElementById("calc-size");
  const woodInputs = document.querySelectorAll('input[name="calc-wood"]');
  const marketSel = document.getElementById("calc-market");

  updateCalculator = function () {
    const size = sizeSel.value;
    const wood = document.querySelector('input[name="calc-wood"]:checked').value;
    const market = marketSel.value;
    const r = computePrice(size, wood, market);

    document.getElementById("calc-price").textContent = formatPrice(r.final, r.currency);
    document.getElementById("calc-anchor").textContent = formatPrice(r.anchor, r.currency);
    document.getElementById("calc-discount").textContent = "-" + r.discount + "%";
    document.getElementById("calc-margin").textContent = formatPrice(r.margin, r.currency) + " (" + r.marginPct + "%)";
    document.getElementById("calc-cost").textContent = formatPrice(r.cost, "PLN");
    document.getElementById("calc-markup").textContent = MARKETS[market].markup + "% vs PL";
  };

  sizeSel.addEventListener("change", updateCalculator);
  marketSel.addEventListener("change", updateCalculator);
  woodInputs.forEach((i) => i.addEventListener("change", updateCalculator));
  updateCalculator();
}

// ============================================================
// TABELA marż PL
// ============================================================
function renderMarginTable() {
  const tbody = document.getElementById("margin-tbody");
  if (!tbody) return;
  const products = getActiveProducts();

  const rows = [];
  for (const [pkey, p] of Object.entries(products)) {
    for (const wood of ["pine", "oak"]) {
      const v = p[wood];
      const r = computePrice(pkey, wood, "pl");
      const markup = (v.price / v.cost).toFixed(2);
      rows.push(`<tr class="${wood === "oak" ? "row--gold" : ""}">
        <td><strong>${pkey}</strong> ${wood === "pine" ? "sosna" : "dąb"}</td>
        <td class="ta-r">${formatPrice(v.cost, "PLN")}</td>
        <td class="ta-r"><strong>${formatPrice(v.price, "PLN")}</strong></td>
        <td class="ta-r">${formatPrice(v.price - v.cost, "PLN")}</td>
        <td class="ta-r">${r.marginPct}%</td>
        <td class="ta-c">${markup}×</td>
      </tr>`);
    }
  }
  tbody.innerHTML = rows.join("");
}

// ============================================================
// WYKRES marż
// ============================================================
function renderMarginChart() {
  const container = document.getElementById("chart-rows");
  if (!container) return;
  const products = getActiveProducts();

  const maxValue = Math.max(...Object.values(products).flatMap((p) => [
    p.pine.price, p.oak.price
  ]));

  const rows = [];
  for (const [pkey, p] of Object.entries(products)) {
    for (const wood of ["pine", "oak"]) {
      const v = p[wood];
      const costPct = (v.cost / maxValue) * 100;
      const fullPct = (v.price / maxValue) * 100;
      const marginCls = wood === "pine" ? "chart__bar--margin-pine" : "chart__bar--margin-oak";
      rows.push(`<div class="chart__row">
        <div class="chart__label"><strong>${pkey}</strong> ${wood === "pine" ? "sosna" : "dąb"}</div>
        <div class="chart__bar-wrap" title="koszt ${v.cost} zł / cena ${v.price} zł">
          <div class="chart__bar ${marginCls}" style="width: ${fullPct.toFixed(1)}%"></div>
          <div class="chart__bar chart__bar--cost" style="width: ${costPct.toFixed(1)}%"></div>
        </div>
        <div class="chart__value">${(v.price - v.cost).toLocaleString("pl-PL")} zł</div>
      </div>`);
    }
  }
  container.innerHTML = rows.join("");
}

// ============================================================
// TABELA cross-market
// ============================================================
function renderPricingTable() {
  const tbody = document.getElementById("pricing-tbody");
  if (!tbody) return;
  const products = getActiveProducts();

  const rows = [];
  for (const pkey of Object.keys(products)) {
    for (const wood of ["pine", "oak"]) {
      const cells = [];
      cells.push(`<td><strong>${pkey}</strong> <small style="color:var(--muted)">${PRODUCT_META[pkey].frame}</small></td>`);
      cells.push(`<td><span class="pill ${wood === "oak" ? "pill--gold" : "pill--neutral"}">${wood === "pine" ? "Sosna" : "Dąb"}</span></td>`);
      for (const mkey of Object.keys(MARKETS)) {
        const r = computePrice(pkey, wood, mkey);
        cells.push(`<td class="ta-r"><strong>${formatPrice(r.final, r.currency)}</strong><br><small style="color:var(--muted)">anchor ${formatPrice(r.anchor, r.currency)}</small></td>`);
      }
      rows.push(`<tr class="${wood === "oak" ? "row--gold" : ""}">${cells.join("")}</tr>`);
    }
  }
  tbody.innerHTML = rows.join("");
}

// ============================================================
// PORÓWNANIE 3 STRATEGII (mini-tabela)
// ============================================================
function renderStrategyCompare() {
  const tbody = document.getElementById("strategy-tbody");
  if (!tbody) return;

  const rows = [];
  for (const size of ["M", "L", "XL"]) {
    for (const wood of ["pine", "oak"]) {
      const cells = [`<td><strong>${size}</strong> ${wood === "pine" ? "sosna" : "dąb"}</td>`];
      for (const stratKey of ["penetration", "current", "premium"]) {
        const v = STRATEGIES[stratKey].products[size][wood];
        const margin = Math.round(((v.price - v.cost) / v.price) * 100);
        const isActive = stratKey === currentStrategy;
        cells.push(`<td class="ta-r ${isActive ? "row--info" : ""}">
          <strong>${formatPrice(v.price, "PLN")}</strong>
          <br><small style="color:var(--muted)">marża ${margin}%</small>
        </td>`);
      }
      rows.push(`<tr class="${wood === "oak" ? "row--gold" : ""}">${cells.join("")}</tr>`);
    }
  }
  tbody.innerHTML = rows.join("");
}

// ============================================================
// SYMULATOR P&L
// ============================================================
let updateSalesSim = () => {};
function initSalesSim() {
  const ranges = document.querySelectorAll(".sim__range");
  if (!ranges.length) return;

  function getAvgPriceAndCost(size, wood) {
    const products = getActiveProducts();
    return { price: products[size][wood].price, cost: products[size][wood].cost };
  }

  updateSalesSim = function () {
    const sS = +document.getElementById("sim-s").value;
    const sL = +document.getElementById("sim-l").value;
    const sXL = +document.getElementById("sim-xl").value;
    const oakPct = +document.getElementById("sim-oak").value;
    const fixedCosts = +document.getElementById("sim-fixed").value;

    document.getElementById("sim-s-val").textContent = sS + " szt.";
    document.getElementById("sim-l-val").textContent = sL + " szt.";
    document.getElementById("sim-xl-val").textContent = sXL + " szt.";
    document.getElementById("sim-oak-val").textContent = oakPct + "% dąb";
    document.getElementById("sim-fixed-val").textContent = fixedCosts.toLocaleString("pl-PL") + " zł";

    let revenue = 0, cost = 0, units = 0;
    const breakdown = {};

    [["M", sS], ["L", sL], ["XL", sXL]].forEach(([size, qty]) => {
      const oakQty = Math.round(qty * oakPct / 100);
      const pineQty = qty - oakQty;
      const pine = getAvgPriceAndCost(size, "pine");
      const oak = getAvgPriceAndCost(size, "oak");

      const sizeRev = pineQty * pine.price + oakQty * oak.price;
      const sizeCost = pineQty * pine.cost + oakQty * oak.cost;
      revenue += sizeRev;
      cost += sizeCost;
      units += qty;
      breakdown[size] = { qty, sizeRev, sizeMargin: sizeRev - sizeCost };
    });

    const grossMargin = revenue - cost;
    const netProfit = grossMargin - fixedCosts;
    const aov = units > 0 ? Math.round(revenue / units) : 0;
    const marginPct = revenue > 0 ? Math.round((grossMargin / revenue) * 100) : 0;
    const breakeven = grossMargin > 0
      ? Math.ceil((fixedCosts / grossMargin) * units)
      : "—";

    document.getElementById("sim-revenue").textContent = formatPrice(revenue, "PLN");
    document.getElementById("sim-profit").textContent = formatPrice(netProfit, "PLN");
    document.getElementById("sim-margin-gross").textContent = formatPrice(grossMargin, "PLN");
    document.getElementById("sim-margin-pct").textContent = marginPct + "%";
    document.getElementById("sim-aov").textContent = formatPrice(aov, "PLN");
    document.getElementById("sim-units").textContent = units + " szt.";
    document.getElementById("sim-breakeven").textContent = typeof breakeven === "number"
      ? breakeven + " szt./mies." : "—";

    let breakdownHTML = "";
    ["M", "L", "XL"].forEach((size) => {
      const b = breakdown[size];
      breakdownHTML += `<div class="sim__breakdown-row">
        <span>${size} (${b.qty} szt.)</span>
        <strong>${formatPrice(b.sizeRev, "PLN")} <small style="color:var(--muted);font-weight:400">marża ${formatPrice(b.sizeMargin, "PLN")}</small></strong>
      </div>`;
    });
    document.getElementById("sim-breakdown").innerHTML = breakdownHTML;
  };

  ranges.forEach((r) => r.addEventListener("input", updateSalesSim));
  updateSalesSim();
}

// ============================================================
// WHAT-IF
// ============================================================
const PRICE_ELASTICITY = -0.7;
let updateWhatIf = () => {};
function initWhatIf() {
  const sizeSel = document.getElementById("wi-size");
  const woodInputs = document.querySelectorAll('input[name="wi-wood"]');
  const deltaInput = document.getElementById("wi-delta");
  const baseConvInput = document.getElementById("wi-conv");
  const trafficInput = document.getElementById("wi-traffic");

  updateWhatIf = function () {
    const size = sizeSel.value;
    const wood = document.querySelector('input[name="wi-wood"]:checked').value;
    const delta = +deltaInput.value;
    const baseConv = +baseConvInput.value;
    const traffic = +trafficInput.value;

    const products = getActiveProducts();
    const v = products[size][wood];
    const basePrice = v.price;
    const newPriceRaw = basePrice * (1 + delta / 100);
    const newPrice = delta > 0 ? roundUpToMagic(newPriceRaw, "PLN") : roundDownToMagic(newPriceRaw, "PLN");
    const actualDelta = ((newPrice - basePrice) / basePrice) * 100;

    const convChangePct = actualDelta * PRICE_ELASTICITY;
    const newConv = Math.max(0.05, baseConv * (1 + convChangePct / 100));

    const baseSales = traffic * (baseConv / 100);
    const newSales = traffic * (newConv / 100);

    const baseRev = baseSales * basePrice;
    const newRev = newSales * newPrice;
    const baseProfit = baseSales * (basePrice - v.cost);
    const newProfit = newSales * (newPrice - v.cost);

    document.getElementById("wi-base-price").textContent = formatPrice(basePrice, "PLN");
    document.getElementById("wi-new-price").textContent = formatPrice(newPrice, "PLN");
    document.getElementById("wi-actual-delta").textContent = (actualDelta >= 0 ? "+" : "") + actualDelta.toFixed(1) + "%";

    document.getElementById("wi-base-conv").textContent = baseConv.toFixed(2) + "%";
    document.getElementById("wi-new-conv").textContent = newConv.toFixed(2) + "%";
    document.getElementById("wi-base-sales").textContent = baseSales.toFixed(1) + " szt.";
    document.getElementById("wi-new-sales").textContent = newSales.toFixed(1) + " szt.";
    document.getElementById("wi-base-rev").textContent = formatPrice(baseRev, "PLN");
    document.getElementById("wi-new-rev").textContent = formatPrice(newRev, "PLN");
    document.getElementById("wi-base-profit").textContent = formatPrice(baseProfit, "PLN");
    document.getElementById("wi-new-profit").textContent = formatPrice(newProfit, "PLN");

    const profitDelta = newProfit - baseProfit;
    const profitDeltaPct = baseProfit !== 0 ? (profitDelta / baseProfit) * 100 : 0;
    let verdict;
    if (Math.abs(profitDeltaPct) < 2) {
      verdict = `Zmiana ceny ma <strong>marginalny wpływ na zysk</strong> (${profitDelta >= 0 ? "+" : ""}${formatPrice(profitDelta, "PLN")}). Lepiej skupić się na innych dźwigniach: konwersji, AOV, ruchu.`;
    } else if (profitDelta > 0) {
      verdict = `Zmiana ceny <strong style="color:var(--success)">zwiększa zysk</strong> o ${formatPrice(profitDelta, "PLN")} (${profitDeltaPct.toFixed(1)}%). Warto przetestować w A/B na 2-3 tygodnie.`;
    } else {
      verdict = `Zmiana ceny <strong style="color:var(--danger)">zmniejsza zysk</strong> o ${formatPrice(Math.abs(profitDelta), "PLN")} (${profitDeltaPct.toFixed(1)}%). ${actualDelta > 0 ? "Spadek konwersji zjada zysk z wyższej ceny." : "Niższa cena nie generuje wystarczająco większej sprzedaży."}`;
    }
    document.getElementById("wi-verdict").innerHTML = verdict;

    document.getElementById("wi-delta-val").textContent = (delta >= 0 ? "+" : "") + delta + "%";
    document.getElementById("wi-conv-val").textContent = baseConv.toFixed(2) + "%";
    document.getElementById("wi-traffic-val").textContent = traffic.toLocaleString("pl-PL") + " odsłon";
  };

  [sizeSel, deltaInput, baseConvInput, trafficInput].forEach((el) => el.addEventListener("input", updateWhatIf));
  woodInputs.forEach((i) => i.addEventListener("change", updateWhatIf));
  updateWhatIf();
}

// ============================================================
// LTV / CAC / ROAS calculator
// ============================================================
function initLtvCac() {
  const inputs = document.querySelectorAll(".ltv-input");
  if (!inputs.length) return;

  function update() {
    const aov = +document.getElementById("ltv-aov").value;
    const grossMarginPct = +document.getElementById("ltv-margin").value;
    const repeatRate = +document.getElementById("ltv-repeat").value;
    const ordersPerYear = +document.getElementById("ltv-orders").value;
    const lifespan = +document.getElementById("ltv-lifespan").value;
    const targetRoas = +document.getElementById("ltv-roas").value;

    document.getElementById("ltv-aov-val").textContent = aov.toLocaleString("pl-PL") + " zł";
    document.getElementById("ltv-margin-val").textContent = grossMarginPct + "%";
    document.getElementById("ltv-repeat-val").textContent = repeatRate + "%";
    document.getElementById("ltv-orders-val").textContent = ordersPerYear.toFixed(1);
    document.getElementById("ltv-lifespan-val").textContent = lifespan + " lat";
    document.getElementById("ltv-roas-val").textContent = targetRoas.toFixed(1) + "×";

    // Simplified LTV: AOV * (1 + (repeatRate/100) * ordersPerYear * lifespan)
    const totalOrders = 1 + (repeatRate / 100) * ordersPerYear * lifespan;
    const ltv = aov * totalOrders;
    const ltvProfit = ltv * (grossMarginPct / 100);
    const maxCac = ltvProfit / targetRoas;
    const maxFirstOrderCac = (aov * (grossMarginPct / 100)) / targetRoas;

    document.getElementById("ltv-total").textContent = formatPrice(ltv, "PLN");
    document.getElementById("ltv-profit").textContent = formatPrice(ltvProfit, "PLN");
    document.getElementById("ltv-cac").textContent = formatPrice(maxCac, "PLN");
    document.getElementById("ltv-cac-first").textContent = formatPrice(maxFirstOrderCac, "PLN");

    // Insight
    const insightEl = document.getElementById("ltv-insight");
    let insight;
    if (maxCac < 30) {
      insight = `Twój CAC max ${formatPrice(maxCac, "PLN")} jest <strong style="color:var(--danger)">zbyt niski</strong> dla Meta/Google Ads (typowy CPM 30-80 zł). Musisz polegać na <strong>organic + repeat customers</strong> lub podnieść AOV / marżę.`;
    } else if (maxCac < 80) {
      insight = `Twój CAC max ${formatPrice(maxCac, "PLN")} jest <strong style="color:var(--warn)">na granicy</strong>. Meta Ads OK przy bardzo precyzyjnym targetowaniu, Google Search dla high-intent keywords. Nie pchaj się w broad audience.`;
    } else if (maxCac < 200) {
      insight = `Twój CAC max ${formatPrice(maxCac, "PLN")} jest <strong style="color:var(--success)">zdrowy</strong>. Możesz testować Meta/Google Ads, retargeting, influencerów. Trzymaj koszt poniżej ${formatPrice(maxFirstOrderCac, "PLN")} dla pierwszego zamówienia.`;
    } else {
      insight = `Twój CAC max ${formatPrice(maxCac, "PLN")} jest <strong style="color:var(--success)">bardzo wysoki</strong> — masz duży budżet na pozyskanie. Możesz inwestować w premium kanały: PR, branded content, sponsored placements w designerskich magazynach.`;
    }
    insightEl.innerHTML = insight;
  }

  inputs.forEach((i) => i.addEventListener("input", update));
  update();
}

// ============================================================
// BUNDLE PRICING
// ============================================================
function renderBundles() {
  const tbody = document.getElementById("bundle-tbody");
  if (!tbody) return;
  const products = getActiveProducts();

  const bundles = [
    { name: "Para do sypialni",        desc: "2× M sosna",                  items: [["M", "pine", 2]],                          discount: 10, tag: "starter" },
    { name: "Dyptyk salonowy",         desc: "2× L sosna",                  items: [["L", "pine", 2]],                          discount: 10, tag: "popularny" },
    { name: "Tryptyk klasyczny",       desc: "3× L sosna",                  items: [["L", "pine", 3]],                          discount: 15, tag: "bestseller" },
    { name: "Galeria mieszana",        desc: "1× XL sosna + 2× M sosna",    items: [["XL", "pine", 1], ["M", "pine", 2]],       discount: 12, tag: "polecany" },
    { name: "Premium dyptyk",          desc: "2× L dąb",                    items: [["L", "oak", 2]],                           discount: 12, tag: "premium" },
    { name: "Inwestycyjna kolekcja",   desc: "1× XL dąb + 1× L dąb + 1× M dąb", items: [["XL", "oak", 1], ["L", "oak", 1], ["M", "oak", 1]], discount: 15, tag: "lux" },
  ];

  const rows = bundles.map((b) => {
    const sumPrice = b.items.reduce((s, [size, wood, qty]) => s + products[size][wood].price * qty, 0);
    const sumCost = b.items.reduce((s, [size, wood, qty]) => s + products[size][wood].cost * qty, 0);
    const bundlePrice = roundDownToMagic(sumPrice * (1 - b.discount / 100), "PLN");
    const margin = bundlePrice - sumCost;
    const marginPct = Math.round((margin / bundlePrice) * 100);
    const tagCls = { starter: "neutral", popularny: "accent", bestseller: "success", polecany: "accent", premium: "gold", lux: "gold" }[b.tag] || "neutral";

    return `<tr>
      <td><strong>${b.name}</strong><br><small style="color:var(--muted)">${b.desc}</small></td>
      <td><span class="pill pill--${tagCls}">${b.tag}</span></td>
      <td class="ta-r"><span style="text-decoration:line-through;color:var(--muted)">${formatPrice(sumPrice, "PLN")}</span></td>
      <td class="ta-c"><strong style="color:var(--danger)">-${b.discount}%</strong></td>
      <td class="ta-r"><strong style="font-family:var(--serif);font-size:16px">${formatPrice(bundlePrice, "PLN")}</strong></td>
      <td class="ta-r">${formatPrice(margin, "PLN")}</td>
      <td class="ta-r">${marginPct}%</td>
    </tr>`;
  }).join("");

  tbody.innerHTML = rows;
}

// ============================================================
// EDYTOWALNA TABELA KOSZTÓW
// ============================================================
function renderCostEditor() {
  const tbody = document.getElementById("cost-tbody");
  if (!tbody) return;

  const sizes = ["M", "L", "XL"];
  const woods = ["pine", "oak"];

  // Grupowanie wierszy
  const groupOrder = ["Rama", "Wydruk", "Opakowanie", "Robocizna"];
  const grouped = {};
  for (const [key, meta] of Object.entries(COST_LABELS)) {
    if (!grouped[meta.group]) grouped[meta.group] = [];
    grouped[meta.group].push({ key, label: meta.name });
  }

  let html = "";
  for (const groupName of groupOrder) {
    const items = grouped[groupName] || [];
    if (!items.length) continue;
    html += `<tr class="cost-group-row"><td colspan="7"><strong>${groupName}</strong></td></tr>`;
    for (const item of items) {
      html += `<tr><td>${item.label}</td>`;
      for (const size of sizes) {
        for (const wood of woods) {
          const v = ACTIVE_COSTS[item.key][size][wood];
          html += `<td class="ta-r"><input type="number" step="0.01" min="0"
            class="cost-input" data-key="${item.key}" data-size="${size}" data-wood="${wood}"
            value="${v.toFixed(2)}" /></td>`;
        }
      }
      html += "</tr>";
    }
  }
  // Wiersze sumy
  html += `<tr class="cost-sum-row"><td><strong>SUMA</strong></td>`;
  for (const size of sizes) {
    for (const wood of woods) {
      html += `<td class="ta-r"><strong id="cost-sum-${size}-${wood}">—</strong></td>`;
    }
  }
  html += "</tr>";

  // Markup (do najtańszej ceny aktualnej strategii)
  html += `<tr class="cost-markup-row"><td><small style="color:var(--muted)">cena aktualnej strategii</small></td>`;
  for (const size of sizes) {
    for (const wood of woods) {
      html += `<td class="ta-r"><span id="cost-price-${size}-${wood}" style="color:var(--muted);font-size:12px">—</span></td>`;
    }
  }
  html += "</tr>";

  html += `<tr class="cost-margin-row"><td><strong>Marża %</strong></td>`;
  for (const size of sizes) {
    for (const wood of woods) {
      html += `<td class="ta-r"><strong id="cost-margin-${size}-${wood}" style="color:var(--success)">—</strong></td>`;
    }
  }
  html += "</tr>";

  tbody.innerHTML = html;

  // Listenery na inputy
  tbody.querySelectorAll(".cost-input").forEach((inp) => {
    inp.addEventListener("input", onCostInputChange);
  });

  recomputeCostSums();
}

function onCostInputChange(e) {
  const inp = e.target;
  const key = inp.dataset.key;
  const size = inp.dataset.size;
  const wood = inp.dataset.wood;
  const value = parseFloat(inp.value);
  if (isNaN(value) || value < 0) return;
  ACTIVE_COSTS[key][size][wood] = value;
  recomputeCostSums();
}

function recomputeCostSums() {
  for (const size of ["M", "L", "XL"]) {
    for (const wood of ["pine", "oak"]) {
      const sum = calcCost(size, wood);
      const sumEl = document.getElementById(`cost-sum-${size}-${wood}`);
      if (sumEl) sumEl.textContent = sum.toFixed(2) + " zł";

      // Aktualna cena ze strategii
      const price = STRATEGY_PRICES[currentStrategy][size][wood].price;
      const priceEl = document.getElementById(`cost-price-${size}-${wood}`);
      if (priceEl) priceEl.textContent = price + " zł";

      // Marża %
      const margin = ((price - sum) / price) * 100;
      const marginEl = document.getElementById(`cost-margin-${size}-${wood}`);
      if (marginEl) {
        marginEl.textContent = margin.toFixed(0) + "%";
        marginEl.style.color = margin >= 70 ? "var(--success)" : margin >= 50 ? "var(--gold)" : "var(--danger)";
      }
    }
  }
}

function applyCosts() {
  localStorage.setItem("cwm-costs-v1", JSON.stringify(ACTIVE_COSTS));
  refreshAllPrices();
  recomputeCostSums();

  const btn = document.getElementById("cost-apply");
  if (btn) {
    const orig = btn.textContent;
    btn.textContent = "✓ Zapisano i przeliczono";
    btn.style.background = "var(--success)";
    setTimeout(() => {
      btn.textContent = orig;
      btn.style.background = "";
    }, 1800);
  }
}

function resetCosts() {
  if (!confirm("Przywrócić domyślne wartości kosztów (z analizy GicleeArt)?")) return;
  ACTIVE_COSTS = JSON.parse(JSON.stringify(COST_BREAKDOWN_DEFAULT));
  localStorage.removeItem("cwm-costs-v1");
  renderCostEditor();
  refreshAllPrices();
}

function exportCostsJSON() {
  const blob = new Blob([JSON.stringify(ACTIVE_COSTS, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "ceny-marketing-koszty-" + new Date().toISOString().slice(0, 10) + ".json";
  a.click();
  URL.revokeObjectURL(url);
}

function initCostEditor() {
  renderCostEditor();
  const btnApply = document.getElementById("cost-apply");
  const btnReset = document.getElementById("cost-reset");
  const btnExport = document.getElementById("cost-export");
  if (btnApply) btnApply.addEventListener("click", applyCosts);
  if (btnReset) btnReset.addEventListener("click", resetCosts);
  if (btnExport) btnExport.addEventListener("click", exportCostsJSON);
}

// ============================================================
// INIT
// ============================================================
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initStrategy();
  renderProductCards();
  initCalculator();
  renderMarginTable();
  renderMarginChart();
  renderPricingTable();
  renderStrategyCompare();
  initSalesSim();
  initWhatIf();
  initLtvCac();
  renderBundles();
  initCostEditor();
});
