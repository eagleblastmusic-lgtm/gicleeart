// @ts-nocheck
(function () {
  if (window.__GICLEE_PDP_EMERGENCY_FIX__) return;
  window.__GICLEE_PDP_EMERGENCY_FIX__ = true;

  const STRIKE =
    '<svg viewBox="0 0 100 46" preserveAspectRatio="xMidYMid slice" class="variant-option__strikethrough" aria-hidden="true"><line x1="100" y1="0" x2="0" y2="46" vector-effect="non-scaling-stroke"></line><line x1="100" y1="0" x2="0" y2="46" vector-effect="non-scaling-stroke"></line></svg>';

  let productPromise = null;

  function norm(value) {
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

  function kind(name) {
    const n = norm(name);
    if (n.includes("passe")) return "skip";
    if (n.includes("kolor")) return "color";
    if (n.includes("rozmiar")) return "size";
    if (n.includes("drewn")) return "wood";
    return "other";
  }

  function productHandlePath() {
    const match = window.location.pathname.match(/^(.*\/products\/[^/?#]+)\/?$/);
    return match ? match[1] : null;
  }

  async function loadProduct() {
    if (window.__GICLEE_PDP_PRODUCT__?.variants?.length) return window.__GICLEE_PDP_PRODUCT__;
    if (productPromise) return productPromise;

    const path = productHandlePath();
    if (!path) return null;

    productPromise = fetch(path + ".js", { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error("Product JSON unavailable");
        return response.json();
      })
      .then((product) => {
        const normalized = {
          id: product.id,
          optionNames: product.options || [],
          variants: (product.variants || []).map((variant) => ({
            id: variant.id,
            available: variant.available,
            price: variant.price,
            compare_at_price: variant.compare_at_price,
            options: [variant.option1, variant.option2, variant.option3].filter(Boolean),
          })),
        };
        window.__GICLEE_PDP_PRODUCT__ = normalized;
        return normalized;
      })
      .catch((err) => {
        console.warn("giclee emergency PDP fix: product fetch failed", err);
        return null;
      });

    return productPromise;
  }

  function patchVariantPickerClass() {
    const VariantPicker = customElements.get("variant-picker");
    if (!VariantPicker || VariantPicker.prototype.__gicleePatched) return;

    Object.defineProperty(VariantPicker.prototype, "__gicleePatched", { value: true });
    Object.defineProperty(VariantPicker.prototype, "selectedOption", {
      get() {
        const selected = this.querySelector(
          'select option[selected], fieldset[data-fieldset-index] input:checked'
        );
        return selected instanceof HTMLInputElement || selected instanceof HTMLOptionElement ? selected : undefined;
      },
    });
    Object.defineProperty(VariantPicker.prototype, "selectedOptionId", {
      get() {
        return this.selectedOption?.dataset?.optionValueId;
      },
    });
    Object.defineProperty(VariantPicker.prototype, "selectedOptionsValues", {
      get() {
        return Array.from(
          this.querySelectorAll('select option[selected], fieldset[data-fieldset-index] input:checked')
        )
          .map((option) => option.dataset.optionValueId)
          .filter(Boolean);
      },
    });
  }

  function optionKindForFieldset(fieldset, data) {
    const index = Number.parseInt(fieldset.getAttribute("data-fieldset-index") || "", 10);
    const byIndex = Number.isNaN(index) ? "" : data.optionNames?.[index] || "";
    const legend = fieldset.querySelector("legend")?.textContent || "";
    return kind(byIndex || legend);
  }

  function readSelection(picker, data) {
    const out = { color: null, size: null, wood: null };
    picker.querySelectorAll("fieldset[data-fieldset-index]").forEach((fieldset) => {
      const k = optionKindForFieldset(fieldset, data);
      const checked = fieldset.querySelector("input[type='radio']:checked");
      if (!checked || k === "skip" || k === "other") return;
      out[k] = checked.value;
    });
    return out;
  }

  function resolveVariant(data, selected) {
    if (!selected.color || !selected.size || !selected.wood) return null;
    return data.variants.find((variant) => {
      if (variant.available === false) return false;
      return (variant.options || []).every((value, index) => {
        const k = kind(data.optionNames?.[index] || "");
        if (k === "skip" || k === "other") return true;
        if (k === "color") return norm(value) === norm(selected.color);
        if (k === "size") return norm(value) === norm(selected.size);
        if (k === "wood") return norm(value) === norm(selected.wood);
        return true;
      });
    });
  }

  function setAvailable(input, available) {
    const label = input.closest("label");
    input.dataset.optionAvailable = available ? "true" : "false";
    if (available) {
      input.removeAttribute("aria-disabled");
      label?.style.removeProperty("pointer-events");
      label?.querySelector(".variant-option__strikethrough")?.remove();
      return;
    }

    input.setAttribute("aria-disabled", "true");
    if (label) {
      label.style.pointerEvents = "none";
      if (!label.querySelector(".variant-option__strikethrough")) {
        label.insertAdjacentHTML("beforeend", STRIKE);
      }
    }
    input.checked = false;
  }

  function syncColors(picker, data, selected) {
    const colorFieldset = Array.from(picker.querySelectorAll("fieldset[data-fieldset-index]")).find(
      (fieldset) => optionKindForFieldset(fieldset, data) === "color"
    );
    if (!colorFieldset) return selected;

    const pine = norm(selected.wood).includes("sosna");
    colorFieldset.querySelectorAll("input[type='radio']").forEach((input) => {
      const available = pine
        ? norm(input.value) === "czarny"
        : Boolean(resolveVariant(data, { color: input.value, size: selected.size, wood: selected.wood }));
      setAvailable(input, available);
    });

    if (pine && norm(selected.color) !== "czarny") {
      const black = colorFieldset.querySelector("input[value='Czarny'], input[value='czarny']");
      if (black) {
        black.checked = true;
        selected = { ...selected, color: black.value };
      }
    }

    return selected;
  }

  function money(cents) {
    if (cents == null || !Number.isFinite(cents)) return "";
    if (window.Shopify?.formatMoney) return window.Shopify.formatMoney(cents);
    return (cents / 100).toLocaleString("pl-PL", {
      style: "currency",
      currency: "PLN",
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    });
  }

  function updatePrice(variant, productId) {
    const formatted = money(variant.price);
    const roots = document.querySelectorAll(
      `product-price[data-product-id="${productId}"] [ref="priceContainer"], .product-details [ref="priceContainer"]`
    );
    roots.forEach((container) => {
      const regular = container.querySelector(".price__regular .price");
      if (regular) regular.textContent = formatted;
      const lone = container.querySelector(":scope > .price");
      if (lone && !regular) lone.textContent = formatted;
    });
  }

  function updateVariantId(variant) {
    document.querySelectorAll('product-form-component input[name="id"], form input[name="id"]').forEach((input) => {
      input.value = String(variant.id);
    });
  }

  async function syncPicker(picker) {
    const data = await loadProduct();
    if (!data?.variants?.length) return;

    let selected = readSelection(picker, data);
    selected = syncColors(picker, data, selected);
    const variant = resolveVariant(data, selected);
    if (!variant) return;

    updatePrice(variant, data.id);
    updateVariantId(variant);
    const url = new URL(window.location.href);
    url.searchParams.set("variant", String(variant.id));
    if (url.href !== window.location.href) history.replaceState({}, "", url.toString());
  }

  function bind() {
    patchVariantPickerClass();
    document.querySelectorAll("variant-picker").forEach((picker) => syncPicker(picker));
  }

  customElements.whenDefined("variant-picker").then(bind).catch(function () {});
  document.addEventListener(
    "change",
    (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      if (target.closest("[data-giclee-passepartout-picker]")) return;
      const picker = target.closest("variant-picker");
      if (picker) requestAnimationFrame(() => syncPicker(picker));
    },
    true
  );

  document.addEventListener(
    "click",
    (event) => {
      const label = event.target instanceof Element ? event.target.closest("label") : null;
      const input = label?.querySelector("input[type='radio']");
      if (input?.getAttribute("aria-disabled") === "true") {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
      }
    },
    true
  );
  window.addEventListener("load", bind);
})();
