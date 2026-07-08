(function () {
  'use strict';

  var SELECTOR = '.giclee-hero-sound-toggle';
  var STORAGE_KEY = 'gicleeHeroAudioWanted';
  var isDesignMode = !!(window.Shopify && window.Shopify.designMode);
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function clamp(n, min, max) {
    return Math.max(min, Math.min(max, n));
  }

  function fade(audio, from, to, duration, done, state) {
    if (state.fadeFrameId) {
      cancelAnimationFrame(state.fadeFrameId);
      state.fadeFrameId = 0;
    }

    if (prefersReducedMotion || duration <= 0) {
      audio.volume = to;
      if (done) done();
      return;
    }

    var start = performance.now();
    audio.volume = from;

    function tick(now) {
      var t = clamp((now - start) / duration, 0, 1);
      var eased = 1 - Math.pow(1 - t, 3);
      audio.volume = from + (to - from) * eased;

      if (t < 1) {
        state.fadeFrameId = requestAnimationFrame(tick);
      } else {
        state.fadeFrameId = 0;
        if (done) done();
      }
    }

    state.fadeFrameId = requestAnimationFrame(tick);
  }

  function initToggle(button) {
    var root =
      button.closest('.giclee-hero-audio-host') ||
      button.closest('section, .shopify-section, [data-section-id]') ||
      button.parentElement;
    var audio = root ? root.querySelector('.giclee-hero-audio') : null;
    var label = button.querySelector('.giclee-hero-sound-toggle__label');

    if (!audio || !root) return;

    var targetVolume = clamp(parseInt(button.dataset.audioVolume || '28', 10) / 100, 0, 1);
    var labelOn = button.dataset.audioLabelOn || 'Włącz dźwięk';
    var labelOff = button.dataset.audioLabelOff || 'Wycisz';
    var userWanted = !isDesignMode && sessionStorage.getItem(STORAGE_KEY) === '1';
    var userGestureUnlocked = false;
    var state = { fadeFrameId: 0 };

    audio.volume = 0;

    function setState(on) {
      button.classList.toggle('is-audio-on', on);
      root.classList.toggle('is-audio-on', on);
      button.setAttribute('aria-pressed', on ? 'true' : 'false');
      button.setAttribute('aria-label', on ? labelOff : labelOn);
      if (label) label.textContent = on ? labelOff : labelOn;
    }

    function playAudio(fromUserGesture) {
      if (fromUserGesture) {
        userGestureUnlocked = true;
        userWanted = true;
        if (!isDesignMode) {
          sessionStorage.setItem(STORAGE_KEY, '1');
        }
      } else if (!userWanted || !userGestureUnlocked) {
        return;
      }

      audio.volume = 0;
      var promise = audio.play();

      function onPlayStarted() {
        setState(true);
        fade(audio, 0, targetVolume, 1400, null, state);
      }

      if (promise && typeof promise.then === 'function') {
        promise.then(onPlayStarted).catch(function () {
          setState(false);
        });
      } else {
        onPlayStarted();
      }
    }

    function stopAudio(clearPreference) {
      if (clearPreference) {
        userWanted = false;
        userGestureUnlocked = false;
        if (!isDesignMode) {
          sessionStorage.setItem(STORAGE_KEY, '0');
        }
      }

      var fromVolume = audio.volume || targetVolume;

      fade(
        audio,
        fromVolume,
        0,
        700,
        function () {
          audio.pause();
          audio.currentTime = 0;
          setState(false);
        },
        state
      );
    }

    button.addEventListener('click', function () {
      if (audio.paused || audio.volume === 0) {
        playAudio(true);
      } else {
        stopAudio(true);
      }
    });

    if ('IntersectionObserver' in window) {
      var observer = new IntersectionObserver(
        function (entries) {
          var entry = entries[0];
          var inView = !!entry && entry.isIntersecting;

          if (!inView && !audio.paused) {
            fade(
              audio,
              audio.volume,
              0,
              650,
              function () {
                audio.pause();
                setState(false);
              },
              state
            );
          }

          if (inView && userWanted && userGestureUnlocked && audio.paused) {
            playAudio(false);
          }
        },
        { threshold: 0.25 }
      );

      observer.observe(root);
    }
  }

  function boot() {
    document.querySelectorAll(SELECTOR).forEach(initToggle);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
