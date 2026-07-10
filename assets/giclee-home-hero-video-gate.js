/* Hold the live Hero collage on frame one, then ask whether it should begin with sound. */
(function () {
  'use strict';

  var SCRUB_ROOT_ID = 'giclee-prehero-video-scrub';
  var HERO_CLASS = 'giclee-prehero-hero-rise';
  var PROMPT_CLASS = 'giclee-hero-sound-consent';
  var VIDEO_SELECTOR =
    '.giclee-video-collage video, .giclee-collage__stage video, video.giclee-collage__video';
  var CENTER_TOLERANCE_PX = 2;
  var AUTO_MUTED_HOLD_FRACTION = 0.35;

  var root = document.documentElement;
  var scrubRoot = null;
  var hero = null;
  var videos = [];
  var audioMaster = null;
  var playbackAllowed = false;
  var hasStarted = false;
  var choiceResolved = false;
  var soundEnabled = false;
  var choiceMode = 'pending';
  var mutationObserver = null;
  var stateObserver = null;
  var rafId = 0;
  var prompt = null;
  var toggle = null;
  var toggleState = null;
  var startButton = null;
  var promptVisible = false;

  function findHero() {
    var map = window.GICLEE_HOME_SECTIONS || {};
    var heroId = map.hero || 'slideshow_4LMfx7';
    return (
      document.getElementById('shopify-section-' + heroId) ||
      document.querySelector('[id$="__' + heroId + '"]') ||
      document.querySelector('.shopify-section.' + HERO_CLASS)
    );
  }

  function safeSeekStart(video) {
    if (!video || (!Number.isFinite(video.duration) && video.readyState < 1)) return;
    try {
      if (Math.abs(video.currentTime) > 0.025) video.currentTime = 0;
    } catch (error) {
      /* Metadata may not be available yet. */
    }
  }

  function pauseAndReset(video) {
    if (!video) return;
    try {
      video.pause();
    } catch (error) {}
    safeSeekStart(video);
  }

  function onPrematurePlay(event) {
    if (playbackAllowed) return;
    pauseAndReset(event.currentTarget);
  }

  function applyVideoSound(video, index) {
    if (!video) return;
    var audible = soundEnabled && video === audioMaster && index === 0;

    video.muted = !audible;
    video.defaultMuted = !audible;
    video.playsInline = true;
    video.setAttribute('playsinline', '');

    if (audible) {
      video.removeAttribute('muted');
    } else {
      video.setAttribute('muted', '');
    }
  }

  function playVideo(video, index) {
    if (!video) return;
    applyVideoSound(video, index);

    var promise;
    try {
      promise = video.play();
    } catch (error) {
      return;
    }

    if (promise && typeof promise.catch === 'function') {
      promise.catch(function () {});
    }
  }

  function prepareVideo(video) {
    if (!video || video.dataset.gicleeHeroVideoGate === '1') return;

    video.dataset.gicleeHeroVideoGate = '1';
    video.autoplay = false;
    video.removeAttribute('autoplay');
    video.muted = true;
    video.defaultMuted = true;
    video.playsInline = true;
    video.setAttribute('muted', '');
    video.setAttribute('playsinline', '');
    video.preload = 'auto';

    video.addEventListener('play', onPrematurePlay);
    video.addEventListener('playing', onPrematurePlay);
    video.addEventListener('loadedmetadata', function () {
      if (!playbackAllowed) pauseAndReset(video);
    });
    video.addEventListener('canplay', function () {
      if (playbackAllowed && hasStarted && video.paused) {
        playVideo(video, videos.indexOf(video));
      }
    });

    if (playbackAllowed && hasStarted) {
      safeSeekStart(video);
      window.requestAnimationFrame(function () {
        if (playbackAllowed) playVideo(video, videos.indexOf(video));
      });
    } else {
      pauseAndReset(video);
    }
  }

  function collectVideos() {
    if (!hero) return videos;

    var found = Array.prototype.slice.call(hero.querySelectorAll(VIDEO_SELECTOR));
    if (!found.length) found = Array.prototype.slice.call(hero.querySelectorAll('video'));

    found.forEach(prepareVideo);
    videos = found;
    audioMaster = videos[0] || null;
    return videos;
  }

  function horizontalStatus() {
    if (typeof window.GICLEE_HERO_HORIZONTAL_CURTAIN_STATUS !== 'function') return null;
    try {
      return window.GICLEE_HERO_HORIZONTAL_CURTAIN_STATUS();
    } catch (error) {
      return null;
    }
  }

  function curtainComplete() {
    return root.getAttribute('data-giclee-hero-horizontal-curtain-complete') === 'true';
  }

  function heroIsSettled() {
    if (!scrubRoot || !hero) return false;
    if (scrubRoot.getAttribute('data-hero-rise-complete') !== 'true') return false;

    var rect = hero.getBoundingClientRect();
    return Math.abs(rect.top) <= CENTER_TOLERANCE_PX;
  }

  function heroIsPlayable() {
    return heroIsSettled() && !curtainComplete();
  }

  function decisionWindowExpired() {
    var status = horizontalStatus();
    if (!status || !status.active || !status.holdTravel) return false;
    return status.localScroll >= status.holdTravel * AUTO_MUTED_HOLD_FRACTION;
  }

  function updateToggleCopy() {
    if (!toggleState || !toggle) return;
    toggleState.textContent = toggle.checked ? 'Włączony' : 'Wyłączony';
  }

  function setPromptVisible(visible) {
    promptVisible = !!visible;
    root.setAttribute('data-giclee-hero-sound-prompt', visible ? 'visible' : 'hidden');

    if (!prompt) return;
    prompt.setAttribute('aria-hidden', visible ? 'false' : 'true');
    if ('inert' in prompt) prompt.inert = !visible;
  }

  function createPrompt() {
    var existing = document.querySelector('.' + PROMPT_CLASS);
    if (existing) existing.remove();

    prompt = document.createElement('div');
    prompt.className = PROMPT_CLASS;
    prompt.setAttribute('aria-hidden', 'true');

    var inner = document.createElement('div');
    inner.className = PROMPT_CLASS + '__inner';

    var question = document.createElement('p');
    question.className = PROMPT_CLASS + '__question';
    question.textContent = 'Doświadczyć tej sceny z dźwiękiem?';

    var label = document.createElement('label');
    label.className = PROMPT_CLASS + '__toggle';

    var labelText = document.createElement('span');
    labelText.className = PROMPT_CLASS + '__toggle-label';
    labelText.textContent = 'Dźwięk';

    toggle = document.createElement('input');
    toggle.className = PROMPT_CLASS + '__input';
    toggle.type = 'checkbox';
    toggle.checked = false;
    toggle.setAttribute('aria-label', 'Włącz dźwięk w filmie');

    var switchVisual = document.createElement('span');
    switchVisual.className = PROMPT_CLASS + '__switch';
    switchVisual.setAttribute('aria-hidden', 'true');

    toggleState = document.createElement('span');
    toggleState.className = PROMPT_CLASS + '__toggle-state';

    label.appendChild(labelText);
    label.appendChild(toggle);
    label.appendChild(switchVisual);
    label.appendChild(toggleState);

    startButton = document.createElement('button');
    startButton.className = PROMPT_CLASS + '__start';
    startButton.type = 'button';
    startButton.textContent = 'Rozpocznij';

    inner.appendChild(question);
    inner.appendChild(label);
    inner.appendChild(startButton);
    prompt.appendChild(inner);
    document.body.appendChild(prompt);

    toggle.addEventListener('change', updateToggleCopy);
    startButton.addEventListener('click', function () {
      if (!heroIsPlayable() || choiceResolved) return;
      resolveChoice(!!toggle.checked, 'user');
    });

    updateToggleCopy();
    setPromptVisible(false);
  }

  function startPlayback(withSound, directFromGesture) {
    collectVideos();
    if (!videos.length || !heroIsPlayable()) return;

    soundEnabled = !!withSound;
    playbackAllowed = true;
    hasStarted = true;

    videos.forEach(function (video, index) {
      pauseAndReset(video);
      applyVideoSound(video, index);
    });

    var begin = function () {
      if (!playbackAllowed || !heroIsPlayable()) return;
      videos.forEach(playVideo);
      hero.setAttribute('data-giclee-hero-video-playback', 'playing');
      hero.setAttribute('data-giclee-hero-video-sound', soundEnabled ? 'on' : 'off');
      window.dispatchEvent(
        new CustomEvent('giclee:hero-video-start', {
          detail: { soundEnabled: soundEnabled, choiceMode: choiceMode },
        })
      );
    };

    /* Unmuted playback must be invoked inside the click gesture. */
    if (directFromGesture) begin();
    else window.requestAnimationFrame(begin);
  }

  function stopPlayback() {
    playbackAllowed = false;
    hasStarted = false;
    collectVideos().forEach(pauseAndReset);
    if (hero) hero.setAttribute('data-giclee-hero-video-playback', 'waiting');
  }

  function resolveChoice(withSound, mode) {
    if (choiceResolved) return;
    choiceResolved = true;
    soundEnabled = !!withSound;
    choiceMode = mode || 'user';
    setPromptVisible(false);
    startPlayback(soundEnabled, choiceMode === 'user');
  }

  function syncGate() {
    rafId = 0;
    var playable = heroIsPlayable();

    if (!playable) {
      setPromptVisible(false);
      if (playbackAllowed) stopPlayback();
      else {
        collectVideos().forEach(function (video) {
          if (!video.paused || video.currentTime > 0.025) pauseAndReset(video);
        });
      }
      return;
    }

    if (!choiceResolved) {
      if (decisionWindowExpired()) {
        resolveChoice(false, 'auto-muted');
      } else {
        setPromptVisible(true);
        collectVideos().forEach(function (video) {
          if (!video.paused || video.currentTime > 0.025) pauseAndReset(video);
        });
      }
      return;
    }

    setPromptVisible(false);
    if (!playbackAllowed) startPlayback(soundEnabled, false);
  }

  function requestSync() {
    if (!rafId) rafId = window.requestAnimationFrame(syncGate);
  }

  function boot() {
    scrubRoot = document.getElementById(SCRUB_ROOT_ID);
    hero = findHero();
    if (!scrubRoot || !hero || !document.body) return;

    createPrompt();
    collectVideos();
    stopPlayback();

    if (window.MutationObserver) {
      mutationObserver = new MutationObserver(function () {
        collectVideos();
        requestSync();
      });
      mutationObserver.observe(hero, { childList: true, subtree: true });

      stateObserver = new MutationObserver(requestSync);
      stateObserver.observe(scrubRoot, {
        attributes: true,
        attributeFilter: ['data-hero-rise-complete', 'data-hero-rise-progress'],
      });
    }

    window.addEventListener('scroll', requestSync, { passive: true });
    window.addEventListener('resize', requestSync, { passive: true });
    window.addEventListener('orientationchange', requestSync, { passive: true });
    window.addEventListener('pageshow', requestSync, { passive: true });

    requestSync();

    window.GICLEE_HERO_VIDEO_GATE_STATUS = function () {
      var rect = hero.getBoundingClientRect();
      var status = horizontalStatus();
      var promptRect = prompt ? prompt.getBoundingClientRect() : null;

      return {
        ready: true,
        settled: heroIsSettled(),
        playable: heroIsPlayable(),
        playbackAllowed: playbackAllowed,
        hasStarted: hasStarted,
        choiceResolved: choiceResolved,
        choiceMode: choiceMode,
        soundEnabled: soundEnabled,
        promptVisible: promptVisible,
        heroRiseComplete:
          scrubRoot.getAttribute('data-hero-rise-complete') === 'true',
        heroTop: Math.round(rect.top * 100) / 100,
        holdFraction:
          status && status.holdTravel
            ? Math.round((status.localScroll / status.holdTravel) * 1000) / 1000
            : null,
        autoMutedAtFraction: AUTO_MUTED_HOLD_FRACTION,
        promptRect: promptRect
          ? {
              top: Math.round(promptRect.top),
              bottom: Math.round(promptRect.bottom),
              height: Math.round(promptRect.height),
            }
          : null,
        videoCount: videos.length,
        videos: videos.map(function (video) {
          return {
            audioMaster: video === audioMaster,
            muted: video.muted,
            paused: video.paused,
            currentTime: Math.round(video.currentTime * 1000) / 1000,
            readyState: video.readyState,
            ended: video.ended,
          };
        }),
      };
    };
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})();
