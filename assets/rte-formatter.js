import { Component } from '@theme/component';

/**
 * A custom element that formats rte content for easier styling
 */
class RTEFormatter extends Component {
  connectedCallback() {
    super.connectedCallback();
    this.#decodeEscapedHtml();
    this.querySelectorAll('table').forEach(this.#formatTable);
  }

  /**
   * Theme locale | t strings are HTML-escaped when output from Liquid variables.
   * Decode entity-encoded markup so headings and paragraphs render correctly.
   */
  #decodeEscapedHtml() {
    const html = this.innerHTML;
    if (!html.includes('&lt;') && !html.includes('&amp;lt;')) return;

    const textarea = document.createElement('textarea');
    textarea.innerHTML = html;
    this.innerHTML = textarea.value;
  }

  /**
   * Formats a table for easier styling
   * @param {HTMLTableElement} table
   */
  #formatTable(table) {
    const wrapper = document.createElement('div');
    wrapper.classList.add('rte-table-wrapper');
    const parent = table.parentNode;
    if (parent) {
      parent.insertBefore(wrapper, table);
      wrapper.appendChild(table);
    }
  }
}

if (!customElements.get('rte-formatter')) {
  customElements.define('rte-formatter', RTEFormatter);
}
