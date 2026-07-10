/* Reuse the native footer utilities inside the FIRST pre-Hero lower curtain. */
(function () {
  'use strict';

  var BAND_SELECTOR = '.giclee-prehero-scrub__bottom-band';
  var BAR_CLASS = 'giclee-prehero-utility-bar';
  var LEGACY_BAR_CLASS = 'giclee-hero-utility-bar';
  var RETRY_LIMIT = 120;
  var RETRY_MS = 100;

  function findFooterUtilities() {
    return (
      document.querySelector('footer [data-testid="footer-utilities"]') ||
      document.querySelector('.footer-utilities [data-testid="footer-utilities"]') ||
      document.querySelector('[data-testid="footer-utilities"]') ||
      document.querySelector('.footer-utilities .utilities') ||
      document.querySelector('.utilities.utilities--blocks-3')
    );
  }

  function rewriteIds(node, prefix) {
    var replacements = [];

    if (node.id) {
      replacements.push({ oldId: node.id, newId: prefix + '-root' });
      node.id = prefix + '-root';
    }

    node.querySelectorAll('[id]').forEach(function (child, index) {
      var oldId = child.id;
      var newId = prefix + '-' + index;
      replacements.push({ oldId: oldId, newId: newId });
      child.id = newId;
    });

    node
      .querySelectorAll('[for], [aria-labelledby], [aria-describedby], [href^="#"], [popovertarget]')
      .forEach(function (child) {
        replacements.forEach(function (item) {
          ['for', 'aria-labelledby', 'aria-describedby', 'href', 'popovertarget'].forEach(
            function (attribute) {
              var value = child.getAttribute(attribute);
              if (!value) return;
              child.setAttribute(attribute, value.split(item.oldId).join(item.newId));
            }
          );
        });
      });
  }

  function sanitize(node) {
    if (!node) return;

    rewriteIds(node, 'giclee-prehero-footer-utilities');
    node.removeAttribute('data-testid');

    node
      .querySelectorAll('[data-shopify-editor-block], [data-shopify-section], [data-block-id]')
      .forEach(function (child) {
        child.removeAttribute('data-shopify-editor-block');
        child.removeAttribute('data-shopify-section');
        child.removeAttribute('data-block-id');
      });

    node.querySelectorAll('script, noscript').forEach(function (child) {
      child.remove();
    });
  }

  function removeStaleBars() {
    document
      .querySelectorAll('.' + BAR_CLASS + ', .' + LEGACY_BAR_CLASS)
      .forEach(function (node) {
        node.remove();
      });
  }

  function createNativeShell(source) {
    var sourceSection = source.closest('.section');
    var shell = sourceSection ? sourceSection.cloneNode(false) : document.createElement('div');

    shell.classList.add(BAR_CLASS);
    shell.removeAttribute('id');
    shell.removeAttribute('data-testid');
    shell.removeAttribute('data-shopify-editor-section');
    shell.removeAttribute('data-shopify-editor-block');
    shell.setAttribute('data-giclee-prehero-utility-bar', '');
    shell.setAttribute('aria-label', 'Informacje i odnośniki Giclée Art');

    /* Preserve the real footer section width and colour scheme, but fit it into the 60px rail. */
    shell.style.setProperty('--padding-block-start', '0px');
    shell.style.setProperty('--padding-block-end', '0px');

    var clone = source.cloneNode(true);
    sanitize(clone);
    shell.appendChild(clone);

    return { shell: shell, clone: clone };
  }

  function mount() {
    var band = document.querySelector(BAND_SELECTOR);
    var source = findFooterUtilities();

    if (!band || !source) return false;
    if (band.querySelector(':scope > .' + BAR_CLASS)) return true;

    removeStaleBars();

    var nativeBar = createNativeShell(source);
    var bar = nativeBar.shell;
    var clone = nativeBar.clone;

    band.removeAttribute('aria-hidden');
    band.setAttribute('data-giclee-prehero-utility-band', '');
    band.appendChild(bar);

    document.documentElement.setAttribute('data-giclee-prehero-utility-ready', 'true');

    window.GICLEE_PREHERO_UTILITY_BAR_STATUS = function () {
      var bandRect = band.getBoundingClientRect();
      var barRect = bar.getBoundingClientRect();
      var sourceRect = source.getBoundingClientRect();
      var style = getComputedStyle(bar);
      var cloneStyle = getComputedStyle(clone);

      return {
        ready: true,
        mode: 'native-footer-clone',
        text: bar.textContent.replace(/\s+/g, ' ').trim(),
        parent: bar.parentElement ? bar.parentElement.className : null,
        classes: bar.className,
        bandRect: {
          top: Math.round(bandRect.top),
          bottom: Math.round(bandRect.bottom),
          height: Math.round(bandRect.height),
        },
        rect: {
          top: Math.round(barRect.top),
          bottom: Math.round(barRect.bottom),
          height: Math.round(barRect.height),
        },
        sourceRect: {
          left: Math.round(sourceRect.left),
          right: Math.round(sourceRect.right),
          width: Math.round(sourceRect.width),
        },
        display: cloneStyle.display,
        gridTemplateColumns: cloneStyle.gridTemplateColumns,
        color: cloneStyle.color,
        opacity: style.opacity,
        visibility: style.visibility,
        transform: getComputedStyle(band).transform,
      };
    };

    window.GICLEE_HERO_UTILITY_BAR_STATUS = window.GICLEE_PREHERO_UTILITY_BAR_STATUS;
    return true;
  }

  function boot() {
    if (mount()) return;

    var attempts = 0;
    var retryId = window.setInterval(function () {
      attempts += 1;
      if (mount() || attempts >= RETRY_LIMIT) {
        window.clearInterval(retryId);
      }
    }, RETRY_MS);

    document.addEventListener('shopify:section:load', function () {
      removeStaleBars();
      mount();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})();