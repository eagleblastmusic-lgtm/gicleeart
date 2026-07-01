// @ts-nocheck
/**
 * PDP reprodukcje — cena i dostępność wariantów (klient), reguła: sosna → tylko czarny.
 */
(function () {
  const STRIKETHROUGH_SVG =
    '<svg viewBox="0 0 100 46" preserveAspectRatio="xMidYMid slice" class="variant-option__strikethrough" aria-hidden="true">' +
    '<line x1="100" y1="0" x2="0" y2="46" vector-effect="non-scaling-stroke"></line>' +
    '<line x1="100" y1="0" x2="0" y2="46" vector-effect="non-scaling-stroke"></line>' +
    "</svg>";

  /** @type {Set<HTMLElement>} */
  const boundPickers = new Set();
  /** @type {Promise<object | null> | null} */
  let productDataPromise = null;

  function normalize(value) {
    return String(value || "")
      .normalize("NFC")
      .trim()
      .toLowerCase()
      .replace(/ą/g, "a")
      .replace(/ę/g, "e")
      .replace(/ó/g, "o")
      .replace(/ł/g, "l")
      .replace(/ń/g, "n")
      .replace(/ś/g, "s")
      .replace(/ź/g, "z")
      .replace(/ż/g, "z");
  }

  function isBlackColor(value) {
    return normalize(value) === "czarny";
  }

  function isPineWood(value) {
    return normalize(value).indexOf("sosna") >= 0;
  }

  function getProductData() {
    if (window.__GICLEE_PDP_PRODUCT__) return window.__GICLEE_PDP_PRODUCT__;
    const el = document.querySelector("[data-giclee-pdp-product-data]");
    if (!el) return null;
    try {
      return JSON.parse(el.textContent || "");
    } catch (err) {
      console.warn("giclee-pdp-variant-sync: parse failed", err);
      return null;
    }
  }

  async function loadProductData() {
    const existing = getProductData();
    if (existing?.variants?.length) return existing;
    if (productDataPromise) return productDataPromise;

    productDataPromise = fetch(window.location.pathname.replace(/\/$/, "") + ".js", {
      headers: { Accept: "application/json" },
    })
      .then(function (response) {
        if (!response.ok) throw new Error("Product JSON unavailable");
        return response.json();
      })
      .then(function (product) {
        const optionNames = product.options || [];
        const normalized = {
          id: product.id,
          optionNames,
          variants: (product.variants || []).map(function (variant) {
            return {
              id: variant.id,
              available: variant.available,
              price: variant.price,
              compare_at_price: variant.compare_at_price,
              options: [variant.option1, variant.option2, variant.option3].filter(function (value) {
                return value != null && value !== "";
              }),
            };
          }),
        };
        window.__GICLEE_PDP_PRODUCT__ = normalized;
        return normalized;
      })
      .catch(function (err) {
        console.warn("giclee-pdp-variant-sync: product JSON fetch failed", err);
        return null;
      });

    return productDataPromise;
  }

  function optionKind(optionName) {
    const n = normalize(optionName);
    if (n.indexOf("passe") >= 0) return "skip";
    if (n.indexOf("kolor") >= 0) return "color";
    if (n.indexOf("rozmiar") >= 0) return "size";
    if (n.indexOf("drewn") >= 0) return "wood";
    return "other";
  }

  /**
   * @param {HTMLElement} picker
   * @param {object} productData
   */
  function readSelections(picker, productData) {
    /** @type {{ color: string | null, size: string | null, wood: string | null }} */
    const out = { color: null, size: null, wood: null };
    const names = productData.optionNames || [];

    picker.querySelectorAll("fieldset[data-fieldset-index]").forEach(function (fieldset) {
      const idx = Number.parseInt(fieldset.getAttribute("data-fieldset-index") || "", 10);
      const optionName = Number.isNaN(idx) ? "" : names[idx] || "";
      const legendText = fieldset.querySelector("legend")?.textContent || "";
      const kind = optionKind(optionName || legendText);
      const checked = /** @type {HTMLInputElement | null} */ (
        fieldset.querySelector("input[type='radio']:checked")
      );
      if (!checked || kind === "skip" || kind === "other") return;
      out[kind] = checked.value;
    });

    return out;
  }

  /**
   * @param {object} productData
   * @param {{ color: string | null, size: string | null, wood: string | null }} selections
   */
  function resolveVariant(productData, selections) {
    if (!selections.color || !selections.size || !selections.wood) return null;
    const names = productData.optionNames || [];

    for (let i = 0; i < productData.variants.length; i++) {
      const variant = productData.variants[i];
      if (variant.available === false) continue;
      const opts = variant.options || [];
      let matched = true;

      for (let j = 0; j < opts.length; j++) {
        const kind = optionKind(names[j] || "");
        if (kind === "skip" || kind === "other") continue;
        const optVal = normalize(opts[j]);
        if (kind === "color" && optVal !== normalize(selections.color)) matched = false;
        if (kind === "size" && optVal !== normalize(selections.size)) matched = false;
        if (kind === "wood" && optVal !== normalize(selections.wood)) matched = false;
      }

      if (matched) return variant;
    }
    return null;
  }

  /**
   * @param {HTMLInputElement} input
   * @param {boolean} available
   */
  function setInputAvailable(input, available) {
    const label = input.closest("label");
    input.dataset.optionAvailable = available ? "true" : "false";

    if (available) {
      input.removeAttribute("aria-disabled");
      if (label) label.style.removeProperty("pointer-events");
      label?.querySelector(".variant-option__strikethrough")?.remove();
      return;
    }

    input.setAttribute("aria-disabled", "true");
    if (label) {
      label.style.pointerEvents = "none";
      if (!label.querySelector(".variant-option__strikethrough")) {
        label.insertAdjacentHTML("beforeend", STRIKETHROUGH_SVG);
      }
    }
    if (input.checked) input.checked = false;
  }

  function findColorFieldset(picker, productData) {
    const names = productData.optionNames || [];
    return Array.from(picker.querySelectorAll("fieldset[data-fieldset-index]")).find(function (fs) {
      const idx = Number.parseInt(fs.getAttribute("data-fieldset-index") || "", 10);
      const optionName = Number.isNaN(idx) ? "" : names[idx] || "";
      const legendText = fs.querySelector("legend")?.textContent || "";
      return optionKind(optionName || legendText) === "color";
    });
  }

  /**
   * @param {HTMLElement} picker
   * @param {object} productData
   * @param {{ color: string | null, size: string | null, wood: string | null }} selections
   */
  function syncColorAvailability(picker, productData, selections) {
    const colorFieldset = findColorFieldset(picker, productData);
    if (!colorFieldset) return false;

    const pineOnly = isPineWood(selections.wood);
    let forcedBlack = false;

    colorFieldset.querySelectorAll("input[type='radio']").forEach(function (input) {
      const inputEl = /** @type {HTMLInputElement} */ (input);
      let available = true;
      if (pineOnly) {
        available = isBlackColor(inputEl.value);
      } else {
        available = !!resolveVariant(productData, {
          color: inputEl.value,
          size: selections.size,
          wood: selections.wood,
        });
      }
      setInputAvailable(inputEl, available);
    });

    if (pineOnly && !isBlackColor(selections.color)) {
      colorFieldset.querySelectorAll("input[type='radio']").forEach(function (input) {
        const inputEl = /** @type {HTMLInputElement} */ (input);
        if (isBlackColor(inputEl.value)) {
          inputEl.checked = true;
          forcedBlack = true;
        }
      });
    }

    return forcedBlack;
  }

  function formatMoney(cents) {
    if (cents == null || !isFinite(cents)) return "";
    if (typeof Shopify !== "undefined" && typeof Shopify.formatMoney === "function") {
      return Shopify.formatMoney(cents);
    }
    return (cents / 100).toLocaleString("pl-PL", {
      style: "currency",
      currency: "PLN",
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    });
  }

  /**
   * @param {object} variant
   * @param {string | number} productId
   */
  function updatePriceDisplay(variant, productId) {
    const formatted = formatMoney(variant.price);
    const hasCompare = variant.compare_at_price && variant.compare_at_price > variant.price;

    function applyToContainer(container) {
      if (!container) return;
      const regularWrap = container.querySelector(".price__regular");
      const saleWrap = container.querySelector(".price__sale");

      if (hasCompare) {
        regularWrap?.classList.add("price__hidden");
        saleWrap?.classList.remove("price__hidden");
        const salePrice = container.querySelector(".price-item--sale.price");
        const comparePrice = container.querySelector(".compare-at-price");
        if (salePrice) salePrice.textContent = formatted;
        if (comparePrice) comparePrice.textContent = formatMoney(variant.compare_at_price);
      } else {
        regularWrap?.classList.remove("price__hidden");
        saleWrap?.classList.add("price__hidden");
        const regular = container.querySelector(".price__regular .price");
        if (regular) regular.textContent = formatted;
        const lonePrice = container.querySelector(":scope > .price");
        if (lonePrice && !regular) lonePrice.textContent = formatted;
      }
    }

    document
      .querySelectorAll('product-price[data-product-id="' + productId + '"] [ref="priceContainer"]')
      .forEach(applyToContainer);

    document
      .querySelectorAll(".product-details [ref='priceContainer']")
      .forEach(applyToContainer);
  }

  /**
   * @param {object} variant
   */
  function updateVariantIdInputs(variant) {
    document.querySelectorAll('input[name="id"]').forEach(function (input) {
      const form = input.closest("form");
      if (!form) return;
      if (!form.closest("product-form-component, .product-details, .shopify-section")) return;
      /** @type {HTMLInputElement} */ (input).value = String(variant.id);
    });
  }

  /**
   * @param {HTMLElement} picker
   * @param {object} variant
   * @param {object} productData
   */
  function dispatchVariantUpdate(picker, variant, productData) {
    picker.dispatchEvent(
      new CustomEvent("variant:update", {
        bubbles: true,
        detail: {
          resource: variant,
          sourceId: String(variant.id),
          data: {
            html: document,
            productId: String(productData.id || ""),
          },
        },
      })
    );
  }

  /**
   * @param {HTMLElement} picker
   */
  async function syncPicker(picker) {
    const productData = await loadProductData();
    if (!productData?.variants?.length) return;

    let selections = readSelections(picker, productData);
    if (syncColorAvailability(picker, productData, selections)) {
      selections = readSelections(picker, productData);
    }

    const variant = resolveVariant(productData, selections);
    if (!variant) return;

    updatePriceDisplay(variant, productData.id);
    updateVariantIdInputs(variant);
    dispatchVariantUpdate(picker, variant, productData);

    const url = new URL(window.location.href);
    url.searchParams.set("variant", String(variant.id));
    if (url.href !== window.location.href) {
      history.replaceState({}, "", url.toString());
    }
  }

  /**
   * @param {HTMLElement} picker
   */
  function bindPicker(picker) {
    if (!(picker instanceof HTMLElement) || boundPickers.has(picker)) return;
    boundPickers.add(picker);
    syncPicker(picker);
  }

  function onPickerChange(event) {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    if (target.closest("[data-giclee-passepartout-picker]")) return;

    const picker = target.closest('variant-picker[data-giclee-variant-sync="true"]');
    if (!picker) return;

    window.requestAnimationFrame(function () {
      syncPicker(/** @type {HTMLElement} */ (picker));
    });
  }

  function onPickerClick(event) {
    const label = event.target instanceof Element ? event.target.closest("label") : null;
    const input = label?.querySelector("input[type='radio']");
    if (input?.getAttribute("aria-disabled") === "true") {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
    }
  }

  function boot() {
    document
      .querySelectorAll('variant-picker[data-giclee-variant-sync="true"]')
      .forEach(function (picker) {
        bindPicker(/** @type {HTMLElement} */ (picker));
      });
  }

  document.addEventListener("change", onPickerChange, true);
  document.addEventListener("click", onPickerClick, true);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  window.addEventListener("load", boot);
  document.addEventListener("shopify:section:load", boot);
})();
