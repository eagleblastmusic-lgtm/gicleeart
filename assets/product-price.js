import { ThemeEvents, VariantUpdateEvent } from '@theme/events';
import { Component } from '@theme/component';

/**
 * @typedef {Object} ProductPriceRefs
 * @property {HTMLElement} priceContainer
 * @property {HTMLElement} [volumePricingNote]
 */

/**
 * A custom element that displays a product price.
 * This component listens for variant update events and updates the price display accordingly.
 * It handles price updates from two different sources:
 * 1. Variant picker (in quick add modal or product page)
 * 2. Swatches variant picker (in product cards)
 *
 * @extends {Component<ProductPriceRefs>}
 */
class ProductPrice extends Component {
  connectedCallback() {
    super.connectedCallback();
    const closestSection = this.closest('.shopify-section, dialog');
    if (!closestSection) return;
    closestSection.addEventListener(ThemeEvents.variantUpdate, this.updatePrice);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    const closestSection = this.closest('.shopify-section, dialog');
    if (!closestSection) return;
    closestSection.removeEventListener(ThemeEvents.variantUpdate, this.updatePrice);
  }

  /**
   * @param {number} cents
   * @returns {string}
   */
  #formatVariantMoney(cents) {
    if (cents == null || !Number.isFinite(cents)) return '';
    if (typeof Shopify !== 'undefined' && typeof Shopify.formatMoney === 'function') {
      return Shopify.formatMoney(cents);
    }
    return (cents / 100).toLocaleString('pl-PL', {
      style: 'currency',
      currency: 'PLN',
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    });
  }

  /**
   * @param {import('@theme/events').VariantUpdateEvent['detail']['resource']} variant
   */
  #updatePriceFromVariant(variant) {
    const { priceContainer } = this.refs;
    if (!priceContainer || variant?.price == null) return;

    const formatted = this.#formatVariantMoney(variant.price);
    const hasCompare = variant.compare_at_price && variant.compare_at_price > variant.price;
    const regularWrap = priceContainer.querySelector('.price__regular');
    const saleWrap = priceContainer.querySelector('.price__sale');

    if (hasCompare) {
      regularWrap?.classList.add('price__hidden');
      saleWrap?.classList.remove('price__hidden');
      const salePrice = priceContainer.querySelector('.price-item--sale.price');
      const comparePrice = priceContainer.querySelector('.compare-at-price');
      if (salePrice) salePrice.textContent = formatted;
      if (comparePrice) comparePrice.textContent = this.#formatVariantMoney(variant.compare_at_price);
    } else {
      regularWrap?.classList.remove('price__hidden');
      saleWrap?.classList.add('price__hidden');
      const regular = priceContainer.querySelector('.price__regular .price');
      if (regular) regular.textContent = formatted;
    }
  }

  /**
   * @param {Document} html
   * @returns {Element | null}
   */
  #findNewProductPrice(html) {
    const blockId = this.dataset.blockId;
    if (blockId) {
      const byBlock = html.querySelector(`product-price[data-block-id="${blockId}"]`);
      if (byBlock) return byBlock;
    }

    const productId = this.dataset.productId;
    if (productId) {
      const matches = html.querySelectorAll(`product-price[data-product-id="${productId}"]`);
      if (matches.length === 1) return matches[0];
      for (const candidate of matches) {
        if (candidate.getAttribute('data-block-id') === blockId) return candidate;
      }
    }

    return null;
  }

  /**
   * Updates the price and volume pricing note.
   * @param {VariantUpdateEvent} event - The variant update event.
   */
  updatePrice = (event) => {
    if (event.detail.data.newProduct) {
      this.dataset.productId = event.detail.data.newProduct.id;
    } else if (event.target instanceof HTMLElement && event.target.dataset.productId !== this.dataset.productId) {
      return;
    }

    const { priceContainer, volumePricingNote } = this.refs;
    const newProductPrice = this.#findNewProductPrice(event.detail.data.html);

    if (newProductPrice) {
      const newPrice = newProductPrice.querySelector('[ref="priceContainer"]');
      if (newPrice && priceContainer) {
        priceContainer.replaceWith(newPrice);
      }

      const newNote = newProductPrice.querySelector('[ref="volumePricingNote"]');

      if (!newNote) {
        volumePricingNote?.remove();
      } else if (!volumePricingNote) {
        newPrice?.insertAdjacentElement('afterend', /** @type {Element} */ (newNote.cloneNode(true)));
      } else {
        volumePricingNote.replaceWith(newNote);
      }
    } else if (event.detail.resource) {
      this.#updatePriceFromVariant(event.detail.resource);
    }

    const input_selector = `#product-form-installment-${this.dataset.blockId} input[name="id"]`;
    const installmentsInput = /** @type {HTMLInputElement|null} */ (this.querySelector(input_selector));
    if (installmentsInput) {
      installmentsInput.value = event.detail.resource?.id ?? '';
      installmentsInput.dispatchEvent(new Event('change', { bubbles: true }));
    }
  };
}

if (!customElements.get('product-price')) {
  customElements.define('product-price', ProductPrice);
}
