import { Component } from '@theme/component';
import { debounce, fetchConfig } from '@theme/utilities';

const ATTR_REQUESTED = '_Invoice requested';
const ATTR_TYPE = '_Invoice type';
const ATTR_COMPANY = '_Company name';
const ATTR_TAX_ID = '_Tax ID';

/**
 * Prośba o fakturę w koszyku — osoba prywatna / firma, atrybuty cart → note_attributes.
 */
class CartInvoiceRequest extends Component {
  /** @type {AbortController | null} */
  #activeFetch = null;

  connectedCallback() {
    super.connectedCallback();
    this.#bindInputs();
    this.#syncVisibility();
    this.#bindCheckoutGuard();
  }

  #bindInputs() {
    const cb = this.querySelector('[data-invoice-requested]');
    cb?.addEventListener('change', () => this.onToggleRequested());
    this.querySelectorAll('[data-invoice-type]').forEach((el) => {
      el.addEventListener('change', () => this.onTypeChange());
    });
    this.querySelector('[data-invoice-company]')?.addEventListener('input', this.onFieldInput);
    this.querySelector('[data-invoice-tax-id]')?.addEventListener('input', this.onFieldInput);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.#checkoutButton?.removeEventListener('click', this.#onCheckoutClick, true);
  }

  /** @type {HTMLButtonElement | null} */
  #checkoutButton = null;

  #bindCheckoutGuard() {
    const root = this.closest('.cart-summary') || this.closest('.cart-drawer__dialog') || document;
    this.#checkoutButton = root.querySelector('#checkout');
    this.#checkoutButton?.addEventListener('click', this.#onCheckoutClick, true);
  }

  #onCheckoutClick = (event) => {
    if (!this.validate()) {
      event.preventDefault();
      event.stopPropagation();
    }
  };

  /**
   * @returns {boolean}
   */
  validate() {
    const { error } = this.refs;
    const requested = this.#isRequested();
    if (!requested) {
      error?.classList.add('hidden');
      return true;
    }
    if (this.#invoiceType() !== 'company') {
      error?.classList.add('hidden');
      return true;
    }
    const company = this.#companyInput()?.value.trim() || '';
    const taxId = this.#taxIdInput()?.value.trim() || '';
    if (!company || !taxId) {
      if (error) {
        error.textContent = this.dataset.errorCompany || 'Fill in company details.';
        error.classList.remove('hidden');
      }
      this.#companyFields()?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      return false;
    }
    error?.classList.add('hidden');
    return true;
  }

  #isRequested() {
    const cb = this.querySelector('[data-invoice-requested]');
    return cb instanceof HTMLInputElement && cb.checked;
  }

  #invoiceType() {
    const checked = this.querySelector('[data-invoice-type]:checked');
    return checked instanceof HTMLInputElement ? checked.value : 'private';
  }

  #companyInput() {
    const el = this.querySelector('[data-invoice-company]');
    return el instanceof HTMLInputElement ? el : null;
  }

  #taxIdInput() {
    const el = this.querySelector('[data-invoice-tax-id]');
    return el instanceof HTMLInputElement ? el : null;
  }

  #companyFields() {
    return this.querySelector('[data-invoice-company-fields]');
  }

  #syncVisibility() {
    const panel = this.querySelector('[data-invoice-panel]');
    const companyFields = this.#companyFields();
    const requested = this.#isRequested();
    const isCompany = this.#invoiceType() === 'company';
    if (panel) {
      panel.hidden = !requested;
    }
    if (companyFields) {
      companyFields.hidden = !requested || !isCompany;
    }
    this.refs.error?.classList.add('hidden');
  }

  onToggleRequested = () => {
    this.#syncVisibility();
    this.#pushAttributes();
  };

  onTypeChange = () => {
    this.#syncVisibility();
    this.#pushAttributes();
  };

  onFieldInput = debounce(() => {
    this.#pushAttributes();
  }, 300);

  #buildAttributes() {
    if (!this.#isRequested()) {
      return {
        [ATTR_REQUESTED]: '',
        [ATTR_TYPE]: '',
        [ATTR_COMPANY]: '',
        [ATTR_TAX_ID]: '',
      };
    }
    const attrs = {
      [ATTR_REQUESTED]: 'yes',
      [ATTR_TYPE]: this.#invoiceType(),
      [ATTR_COMPANY]: '',
      [ATTR_TAX_ID]: '',
    };
    if (attrs[ATTR_TYPE] === 'company') {
      attrs[ATTR_COMPANY] = this.#companyInput()?.value.trim() || '';
      attrs[ATTR_TAX_ID] = this.#taxIdInput()?.value.trim() || '';
    }
    return attrs;
  }

  #pushAttributes = debounce(async () => {
    if (this.#activeFetch) {
      this.#activeFetch.abort();
    }
    const abortController = new AbortController();
    this.#activeFetch = abortController;

    try {
      const config = fetchConfig('json', {
        body: JSON.stringify({ attributes: this.#buildAttributes() }),
      });
      await fetch(Theme.routes.cart_update_url, {
        ...config,
        signal: abortController.signal,
      });
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return;
    } finally {
      this.#activeFetch = null;
    }
  }, 200);
}

if (!customElements.get('cart-invoice-request')) {
  customElements.define('cart-invoice-request', CartInvoiceRequest);
}
