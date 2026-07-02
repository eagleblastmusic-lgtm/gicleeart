(function () {
  var root = document.getElementById('giclee-site-notice');
  if (!root) return;

  try {
    var skip = new URLSearchParams(window.location.search).get('giclee_skip_notice');
    if (skip === '1') return;
  } catch (e) {}

  var btn = root.querySelector('[data-giclee-site-notice-accept]');
  var isClosing = false;
  var isOpen = false;
  var FADE_MS = 450;
  var SPLASH_FALLBACK_MS = 4500;

  try {
    var version = root.dataset.version || '1';
    localStorage.removeItem('giclee-site-notice-dismissed-' + version);
    Object.keys(localStorage).forEach(function (key) {
      if (key.indexOf('giclee-site-notice-dismissed-') === 0) {
        localStorage.removeItem(key);
      }
    });
  } catch (e) {}

  function resetNotice() {
    root.hidden = true;
    root.classList.remove('is-visible', 'is-closing');
    document.documentElement.classList.remove('giclee-site-notice-open');
    isClosing = false;
    isOpen = false;
  }

  function finishClose() {
    resetNotice();
  }

  function closeNotice() {
    if (isClosing || root.hidden || !root.classList.contains('is-visible')) return;
    isClosing = true;
    isOpen = false;
    document.documentElement.classList.remove('giclee-site-notice-open');
    root.classList.remove('is-visible');
    root.classList.add('is-closing');

    var done = false;
    function onTransitionEnd(event) {
      if (done || event.target !== root || event.propertyName !== 'opacity') return;
      done = true;
      root.removeEventListener('transitionend', onTransitionEnd);
      finishClose();
    }

    root.addEventListener('transitionend', onTransitionEnd);
    window.setTimeout(function () {
      if (!done) {
        root.removeEventListener('transitionend', onTransitionEnd);
        finishClose();
      }
    }, FADE_MS + 80);
  }

  function openNotice() {
    if (isClosing) return;
    isOpen = true;
    document.documentElement.classList.add('giclee-site-notice-open');
    root.hidden = false;
    root.classList.remove('is-closing');
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        root.classList.add('is-visible');
      });
    });
  }

  function scheduleOpen() {
    var html = document.documentElement;
    var waitForSplash =
      root.dataset.homepage === 'true' &&
      (html.classList.contains('splash-pending') || html.classList.contains('splash-reveal'));

    if (!waitForSplash) {
      resetNotice();
      openNotice();
      return;
    }

    var opened = false;
    function go() {
      if (opened) return;
      opened = true;
      resetNotice();
      openNotice();
    }

    window.addEventListener('giclee:splash-done', go, { once: true });
    window.setTimeout(go, SPLASH_FALLBACK_MS);
  }

  if (btn) {
    btn.addEventListener('click', closeNotice);
  }

  root.addEventListener('click', function (event) {
    if (event.target === root) {
      closeNotice();
    }
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && root.classList.contains('is-visible') && !isClosing) {
      closeNotice();
    }
  });

  window.addEventListener('pageshow', function (event) {
    if (!event.persisted) return;
    scheduleOpen();
  });

  scheduleOpen();
})();
