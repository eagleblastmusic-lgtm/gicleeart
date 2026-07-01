/**
 * Przycisk BLIK (PL): dodaje bieżący wariant do koszyka i przechodzi do kasy.
 */
(function () {
  function initButton(button) {
    if (button.dataset.blikInit === '1') return;
    button.dataset.blikInit = '1';

    button.addEventListener('click', function () {
      if (button.disabled) return;

      const form = button.closest('form');
      if (!form) return;

      button.disabled = true;
      button.setAttribute('aria-busy', 'true');

      const formData = new FormData(form);

      fetch('/cart/add.js', {
        method: 'POST',
        body: formData,
        headers: { Accept: 'application/json' },
      })
        .then(function (response) {
          if (!response.ok) throw new Error('cart_add_failed');
          window.location.href = '/checkout';
        })
        .catch(function () {
          button.disabled = false;
          button.removeAttribute('aria-busy');
          form.requestSubmit();
        });
    });
  }

  function boot() {
    document.querySelectorAll('[data-blik-checkout]').forEach(initButton);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

  document.addEventListener('shopify:section:load', boot);
})();
