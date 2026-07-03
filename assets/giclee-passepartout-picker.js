/**
 * Passepartout — line item property z animacją pill jak variant-picker.
 */
(function () {
  const PROPERTY_KEY = "Passepartout";
  const DEFAULT_VALUE = "Białe";

  window.GICLEE_PASSEPARTOUT = {
    propertyKey: PROPERTY_KEY,
    defaultValue: DEFAULT_VALUE,
    normalize(value) {
      const v = String(value || "")
        .normalize("NFC")
        .trim()
        .toLowerCase()
        .replace("ą", "a")
        .replace("ę", "e");
      if (v === "czarny" || v === "czarne") return "Czarne";
      return DEFAULT_VALUE;
    },
  };

  /** @type {WeakMap<HTMLElement, number[]>} */
  const checkedIndicesByRoot = new WeakMap();

  function getRadios(root) {
    return Array.from(
      root.querySelectorAll('input[type="radio"][data-giclee-pp-value]')
    );
  }

  function applyFieldsetMeasurements(root, currentIndex, previousIndex) {
    const radios = getRadios(root);
    const currentWidth =
      currentIndex !== undefined
        ? radios[currentIndex]?.parentElement?.offsetWidth
        : undefined;
    const previousWidth =
      previousIndex !== undefined
        ? radios[previousIndex]?.parentElement?.offsetWidth
        : undefined;

    if (currentWidth) {
      root.style.setProperty("--pill-width-current", currentWidth + "px");
    } else if (currentIndex !== undefined) {
      root.style.removeProperty("--pill-width-current");
    }

    if (previousWidth) {
      root.style.setProperty("--pill-width-previous", previousWidth + "px");
    } else if (previousIndex !== undefined) {
      root.style.removeProperty("--pill-width-previous");
    }
  }

  function updateFieldsetCss(root) {
    const checkedIndices = checkedIndicesByRoot.get(root) || [];
    const currentIndex = checkedIndices[0];
    const previousIndex = checkedIndices[1];
    applyFieldsetMeasurements(root, currentIndex, previousIndex);
  }

  function updateSelectedOption(root, inputIndex) {
    const radios = getRadios(root);
    let checkedIndices = checkedIndicesByRoot.get(root);
    if (!checkedIndices) {
      checkedIndices = [];
      checkedIndicesByRoot.set(root, checkedIndices);
    }

    const currentIndex = checkedIndices[0];
    const previousIndex = checkedIndices[1];

    if (currentIndex !== undefined && radios[currentIndex]) {
      radios[currentIndex].dataset.previousChecked = "false";
    }
    if (previousIndex !== undefined && radios[previousIndex]) {
      radios[previousIndex].dataset.previousChecked = "false";
    }

    checkedIndices.unshift(inputIndex);
    checkedIndices.length = Math.min(checkedIndices.length, 2);

    const newCurrent = checkedIndices[0];
    const newPrevious = checkedIndices[1];

    if (newCurrent !== undefined && radios[newCurrent]) {
      radios[newCurrent].dataset.currentChecked = "true";
    }
    if (newPrevious !== undefined && radios[newPrevious]) {
      radios[newPrevious].dataset.previousChecked = "true";
      radios[newPrevious].dataset.currentChecked = "false";
    }

    updateFieldsetCss(root);
  }

  function syncHiddenInput(root, label) {
    const formId = root.getAttribute("data-product-form-id") || "";
    let input = root.querySelector("input[data-giclee-passepartout-input]");
    if (!input) {
      input = document.createElement("input");
      input.type = "hidden";
      input.name = "properties[" + PROPERTY_KEY + "]";
      input.setAttribute("data-giclee-passepartout-input", "1");
      root.appendChild(input);
    }
    if (formId) input.setAttribute("form", formId);
    input.value = window.GICLEE_PASSEPARTOUT.normalize(label || DEFAULT_VALUE);
  }

  function initRoot(root) {
    if (!root || root.dataset.gicleePpInit === "1") return;
    root.dataset.gicleePpInit = "1";

    const radios = getRadios(root);
    const initial = window.GICLEE_PASSEPARTOUT.normalize(
      root.getAttribute("data-initial-value") || DEFAULT_VALUE
    );

    let initialIndex = radios.findIndex(function (radio) {
      const label = radio.getAttribute("data-giclee-pp-value") || radio.value;
      return window.GICLEE_PASSEPARTOUT.normalize(label) === initial;
    });
    if (initialIndex < 0) initialIndex = 0;

    radios.forEach(function (radio, index) {
      radio.dataset.inputIndex = String(index);
      radio.dataset.currentChecked = index === initialIndex ? "true" : "false";
      radio.dataset.previousChecked = "false";
      radio.checked = index === initialIndex;

      radio.addEventListener("change", function () {
        if (!radio.checked) return;
        const inputIndex = Number.parseInt(radio.dataset.inputIndex || "0", 10);
        updateSelectedOption(root, inputIndex);
        const label = radio.getAttribute("data-giclee-pp-value") || radio.value;
        syncHiddenInput(root, label);
        root.dispatchEvent(
          new CustomEvent("giclee:passepartout-change", {
            bubbles: true,
            detail: {
              value: window.GICLEE_PASSEPARTOUT.normalize(label),
              mockupVariant:
                radio.getAttribute("data-giclee-mockup-variant") ||
                (window.GICLEE_PASSEPARTOUT.normalize(label) === "Czarne"
                  ? "CZCZ"
                  : "CZB"),
            },
          })
        );
      });
    });

    checkedIndicesByRoot.set(root, [initialIndex]);
    updateFieldsetCss(root);
    syncHiddenInput(
      root,
      radios[initialIndex]?.getAttribute("data-giclee-pp-value") || DEFAULT_VALUE
    );

    if (typeof ResizeObserver !== "undefined") {
      const ro = new ResizeObserver(function () {
        updateFieldsetCss(root);
      });
      ro.observe(root);
    }
  }

  function boot() {
    document.querySelectorAll("[data-giclee-passepartout-picker]").forEach(initRoot);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  document.addEventListener("shopify:section:load", boot);
})();
