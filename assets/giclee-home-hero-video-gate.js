/* Hold the live Hero collage on frame one, then ask whether it should begin with sound. */
(function () {
  'use strict';

  var CONFIG = window.GICLEE_PREHERO_CONFIG || {};
  var SCRUB_ROOT_ID = 'giclee-prehero-video-scrub';
  var HERO_CLASS = 'giclee-prehero-hero-rise';
  var PROMPT_CLASS = 'giclee-hero-sound-consent';
  var VIDEO_SELECTOR =
    '.giclee-video-collage video, .giclee-collage__stage video, video.giclee-collage__video';
  var CENTER_TOLERANCE_PX = 2;

  var SOUND_CONSENT_ENABLED = CONFIG.soundConsentEnabled !== false;
  var SOUND_QUESTION = textConfig(
    'soundConsentQuestion',
    'Doświadczyć tej sceny z dźwiękiem?'
  );
  var SOUND_TOGGLE_LABEL = textConfig('soundConsentToggleLabel', 'Dźwięk');
  var SOUND_START_LABEL = textConfig('soundConsentStartLabel', 'Rozpocznij');
  var SOUND_AUDIO_URL = textConfig('soundConsentAudioUrl', '');
  var SOUND_VOLUME = numberConfig('soundConsentVolume', 28, 0, 100) / 100;
  var AUTO_MUTED_HOLD_FRACTION = numberConfig(
    'soundConsentAutoMutedFraction',
    0.35,
    0,
    1
  );

  var root = document.documentElement;
  var scrubRoot = null;
  var hero = null;
  var heroDocumentTop = 0;
  var videos = [];
  var audioMaster = null;
  var ambientAudio = null;
  var playbackAllowed = false;
  var hasStarted = false;
  var choiceResolved = false;
  var soundEnabled = false;
  var choiceMode = 'pending';
  var mutationObserver = null;
  var stateObserver = null;
  var curtainObserver = null;
  var rafId = 0;
  var volumeRafId = 0;
  var currentAudioGain = 1;
  var appliedAudioGain = '';
  var prompt = null;
  var toggle = null;
  var toggleState = null;
  var promptVisible = false;
  var gateSyncCount = 0;
  var layoutReadCount = 0;
  var mediaResetCount = 0;
  var curtainRuntimeReadCount = 0;
  var curtainStatusFallbackCount = 0;

  function textConfig(key, fallback) {
    var value = String(CONFIG[key] == null ? '' : CONFIG[key]).trim();
    return value || fallback;
  }

  function numberConfig(key, fallback, min, max) {
    var value = Number(CONFIG[key]);
    if (!Number.isFinite(value)) value = fallback;
    return Math.min(max, Math.max(min, value));
  }

  function clamp01(value) {
    return Math.min(1, Math.max(0, value));
  }

  function scrollY() {
    return window.scrollY || window.pageYOffset || document.documentElement.scrollTop || 0;
  }

  function findHero() {
    var map = window.GICLEE_HOME_SECTIONS || {};
    var heroId = map.hero || 'slideshow_4LMfx7';
    return (
      document.getElementById('shopify-section-' + heroId) ||
      document.querySelector('[id$="__' + heroId + '"]') ||
      document.querySelector('.shopify-section.' + HERO_CLASS)
    );
  }

  function measureHeroDocumentTop() {
    if (!hero) return;
    var rect = hero.getBoundingClientRect();
    layoutReadCount += 1;
    heroDocumentTop = scrollY() + rect.top;
  }

  function estimatedHeroTop() {
    return Math.max(0, heroDocumentTop - scrollY());
  }

  function safeSeekStart(media) {
    if (!media || (!Number.isFinite(media.duration) && media.readyState < 1)) return;
    try {
      if (Math.abs(media.currentTime) > 0.025) {
        media.currentTime = 0;
        mediaResetCount += 1;
      }
    } catch (error) {}
  }

  function pauseAndReset(media) {
    if (!media) return;
    try {
      if (!media.paused) media.pause();
    } catch (error) {}
    safeSeekStart(media);
  }

  function onPrematurePlay(event) {
    if (playbackAllowed) return;
    pauseAndReset(event.currentTarget);
  }

  function usesAmbientAudio() {
    return !!(soundEnabled && ambientAudio && SOUND_AUDIO_URL);
  }

  function applyVideoSound(video, index) {
    if (!video) return;
    var audible =
      soundEnabled && !usesAmbientAudio() && video === audioMaster && index === 0;
    video.muted = !audible;
    video.defaultMuted = !audible;
    video.playsInline = true;
    video.setAttribute('playsinline', '');
    video.volume = audible ? currentAudioGain : 1;
    if (audible) video.removeAttribute('muted');
    else video.setAttribute('muted', '');
  }

  function playVideo(video, index) {
    if (!video) return;
    applyVideoSound(video, index);
    try {
      var promise = video.play();
      if (promise && typeof promise.catch === 'function') promise.catch(function () {});
    } catch (error) {}
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

  function createAmbientAudio() {
    if (!SOUND_AUDIO_URL || typeof window.Audio !== 'function') return null;
    ambientAudio = new Audio(SOUND_AUDIO_URL);
    ambientAudio.preload = 'auto';
    ambientAudio.loop = true;
    ambientAudio.volume = SOUND_VOLUME;
    ambientAudio.setAttribute('data-giclee-hero-ambient', '1');
    return ambientAudio;
  }

  function playAmbient() {
    if (!usesAmbientAudio()) return;
    ambientAudio.volume = SOUND_VOLUME * currentAudioGain;
    try {
      var promise = ambientAudio.play();
      if (promise && typeof promise.catch === 'function') promise.catch(function () {});
    } catch (error) {}
  }

  function stopAmbient() {
    if (ambientAudio) pauseAndReset(ambientAudio);
  }

  function curtainRuntime() {
    if (typeof window.GICLEE_HERO_HORIZONTAL_CURTAIN_RUNTIME === 'function') {
      curtainRuntimeReadCount += 1;
      try {
        return window.GICLEE_HERO_HORIZONTAL_CURTAIN_RUNTIME();
      } catch (error) {
        return null;
      }
    }
    if (typeof window.GICLEE_HERO_HORIZONTAL_CURTAIN_STATUS === 'function') {
      curtainStatusFallbackCount += 1;
      try {
        return window.GICLEE_HERO_HORIZONTAL_CURTAIN_STATUS();
      } catch (error) {
        return null;
      }
    }
    return null;
  }

  function heroRiseAudioGain() {
    if (!scrubRoot) return 1;
    var progress = Number(scrubRoot.getAttribute('data-hero-rise-progress'));
    return Number.isFinite(progress) ? clamp01(progress) : 1;
  }

  function curtainAudioGain(runtime) {
    var status = runtime || curtainRuntime();
    if (!status || !status.active) return 1;
    var progress = Number(status.easedProgress);
    if (!Number.isFinite(progress)) progress = Number(status.smoothedProgress);
    return Number.isFinite(progress) ? 1 - clamp01(progress) : 1;
  }

  function sceneAudioGain(runtime) {
    return Math.min(heroRiseAudioGain(), curtainAudioGain(runtime));
  }

  function applyPlaybackVolume(runtime) {
    var gain = sceneAudioGain(runtime);
    currentAudioGain = gain;
    var key = gain.toFixed(3);
    if (key === appliedAudioGain) return;
    appliedAudioGain = key;
    if (ambientAudio) ambientAudio.volume = SOUND_VOLUME * gain;
    if (audioMaster) audioMaster.volume = gain;
    if (hero) hero.style.setProperty('--giclee-hero-audio-gain', key);
  }

  function trackPlaybackVolume() {
    volumeRafId = 0;
    if (!playbackAllowed || !hasStarted || !soundEnabled) return;
    applyPlaybackVolume();
    volumeRafId = window.requestAnimationFrame(trackPlaybackVolume);
  }

  function startVolumeTracking() {
    if (volumeRafId) window.cancelAnimationFrame(volumeRafId);
    applyPlaybackVolume();
    if (soundEnabled) volumeRafId = window.requestAnimationFrame(trackPlaybackVolume);
  }

  function stopVolumeTracking() {
    if (volumeRafId) window.cancelAnimationFrame(volumeRafId);
    volumeRafId = 0;
    currentAudioGain = 1;
    appliedAudioGain = '';
    if (ambientAudio) ambientAudio.volume = SOUND_VOLUME;
    if (audioMaster) audioMaster.volume = 1;
    if (hero) hero.style.removeProperty('--giclee-hero-audio-gain');
  }

  function curtainComplete(runtime) {
    if (runtime && typeof runtime.complete === 'boolean') return runtime.complete;
    return root.getAttribute('data-giclee-hero-horizontal-curtain-complete') === 'true';
  }

  function heroIsSettled() {
    if (!scrubRoot || !hero) return false;
    if (scrubRoot.getAttribute('data-hero-rise-complete') !== 'true') return false;
    return estimatedHeroTop() <= CENTER_TOLERANCE_PX;
  }

  function heroIsPlayable(runtime) {
    return heroIsSettled() && !curtainComplete(runtime);
  }

  function shouldKeepSilentPlaybackForReverseScroll(runtime) {
    return !!(
      playbackAllowed &&
      hasStarted &&
      choiceResolved &&
      soundEnabled &&
      !curtainComplete(runtime)
    );
  }

  function decisionWindowExpired(runtime) {
    var status = runtime || curtainRuntime();
    if (!status || !status.active || !status.holdTravel) return false;
    if (AUTO_MUTED_HOLD_FRACTION <= 0) return true;
    return status.localScroll >= status.holdTravel * AUTO_MUTED_HOLD_FRACTION;
  }

  function updateToggleCopy() {
    if (toggleState && toggle) {
      toggleState.textContent = toggle.checked ? 'Włączony' : 'Wyłączony';
    }
  }

  function setPromptVisible(visible) {
    var nextVisible = !!visible && SOUND_CONSENT_ENABLED;
    var nextState = nextVisible ? 'visible' : 'hidden';
    if (
      promptVisible === nextVisible &&
      root.getAttribute('data-giclee-hero-sound-prompt') === nextState
    ) return;
    promptVisible = nextVisible;
    root.setAttribute('data-giclee-hero-sound-prompt', nextState);
    if (!prompt) return;
    prompt.setAttribute('aria-hidden', promptVisible ? 'false' : 'true');
    if ('inert' in prompt) prompt.inert = !promptVisible;
  }

  function createPrompt() {
    var existing = document.querySelector('.' + PROMPT_CLASS);
    if (existing) existing.remove();
    if (!SOUND_CONSENT_ENABLED) return null;
    prompt = document.createElement('div');
    prompt.className = PROMPT_CLASS;
    prompt.setAttribute('aria-hidden', 'true');
    var inner = document.createElement('div');
    inner.className = PROMPT_CLASS + '__inner';
    var question = document.createElement('p');
    question.className = PROMPT_CLASS + '__question';
    question.textContent = SOUND_QUESTION;
    var label = document.createElement('label');
    label.className = PROMPT_CLASS + '__toggle';
    var labelText = document.createElement('span');
    labelText.className = PROMPT_CLASS + '__toggle-label';
    labelText.textContent = SOUND_TOGGLE_LABEL;
    toggle = document.createElement('input');
    toggle.className = PROMPT_CLASS + '__input';
    toggle.type = 'checkbox';
    toggle.checked = false;
    toggle.setAttribute('aria-label', SOUND_TOGGLE_LABEL);
    var switchVisual = document.createElement('span');
    switchVisual.className = PROMPT_CLASS + '__switch';
    switchVisual.setAttribute('aria-hidden', 'true');
    toggleState = document.createElement('span');
    toggleState.className = PROMPT_CLASS + '__toggle-state';
    label.appendChild(labelText);
    label.appendChild(toggle);
    label.appendChild(switchVisual);
    label.appendChild(toggleState);
    var startButton = document.createElement('button');
    startButton.className = PROMPT_CLASS + '__start';
    startButton.type = 'button';
    startButton.textContent = SOUND_START_LABEL;
    inner.appendChild(question);
    inner.appendChild(label);
    inner.appendChild(startButton);
    prompt.appendChild(inner);
    document.body.appendChild(prompt);
    toggle.addEventListener('change', updateToggleCopy);
    startButton.addEventListener('click', function () {
      if (!heroIsPlayable(curtainRuntime()) || choiceResolved) return;
      resolveChoice(!!toggle.checked, 'user');
    });
    updateToggleCopy();
    return prompt;
  }

  function startPlayback(withSound, directFromGesture) {
    collectVideos();
    var runtime = curtainRuntime();
    if (!videos.length || !heroIsPlayable(runtime)) return;
    soundEnabled = !!withSound;
    playbackAllowed = true;
    hasStarted = true;
    currentAudioGain = sceneAudioGain(runtime);
    videos.forEach(function (video, index) {
      pauseAndReset(video);
      applyVideoSound(video, index);
    });
    stopAmbient();
    var begin = function () {
      if (!playbackAllowed || !heroIsPlayable(curtainRuntime())) return;
      startVolumeTracking();
      videos.forEach(playVideo);
      if (soundEnabled) playAmbient();
      hero.setAttribute('data-giclee-hero-video-playback', 'playing');
      hero.setAttribute('data-giclee-hero-video-sound', soundEnabled ? 'on' : 'off');
      window.dispatchEvent(
        new CustomEvent('giclee:hero-video-start', {
          detail: {
            soundEnabled: soundEnabled,
            choiceMode: choiceMode,
            ambient: usesAmbientAudio(),
            ambientUrl: SOUND_AUDIO_URL,
          },
        })
      );
    };
    if (directFromGesture) begin();
    else window.requestAnimationFrame(begin);
  }

  function stopPlayback() {
    playbackAllowed = false;
    hasStarted = false;
    videos.forEach(pauseAndReset);
    stopAmbient();
    stopVolumeTracking();
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
    gateSyncCount += 1;
    var runtime = curtainRuntime();
    var playable = heroIsPlayable(runtime);

    if (!playable) {
      setPromptVisible(false);
      if (shouldKeepSilentPlaybackForReverseScroll(runtime)) {
        applyPlaybackVolume(runtime);
        return;
      }
      if (playbackAllowed) stopPlayback();
      return;
    }

    if (!choiceResolved) {
      if (!SOUND_CONSENT_ENABLED) {
        resolveChoice(false, 'disabled');
      } else if (decisionWindowExpired(runtime)) {
        resolveChoice(false, 'auto-muted');
      } else {
        setPromptVisible(true);
      }
      return;
    }

    setPromptVisible(false);
    if (!playbackAllowed) startPlayback(soundEnabled, false);
    else if (soundEnabled) applyPlaybackVolume(runtime);
  }

  function requestSync() {
    if (!rafId) rafId = window.requestAnimationFrame(syncGate);
  }

  function refreshLayout() {
    measureHeroDocumentTop();
    requestSync();
  }

  function boot() {
    scrubRoot = document.getElementById(SCRUB_ROOT_ID);
    hero = findHero();
    if (!scrubRoot || !hero || !document.body) return;
    measureHeroDocumentTop();
    createAmbientAudio();
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

      curtainObserver = new MutationObserver(requestSync);
      curtainObserver.observe(root, {
        attributes: true,
        attributeFilter: [
          'data-giclee-hero-horizontal-curtain-active',
          'data-giclee-hero-horizontal-curtain-opening',
          'data-giclee-hero-horizontal-curtain-complete',
        ],
      });
    }

    window.addEventListener('scroll', requestSync, { passive: true });
    window.addEventListener('resize', refreshLayout, { passive: true });
    window.addEventListener('orientationchange', refreshLayout, { passive: true });
    window.addEventListener('pageshow', refreshLayout, { passive: true });
    window.addEventListener('giclee:home-stack-ready', refreshLayout, { passive: true });
    requestSync();

    window.GICLEE_HERO_VIDEO_GATE_STATUS = function () {
      var rect = hero.getBoundingClientRect();
      var status = curtainRuntime();
      var promptRect = prompt ? prompt.getBoundingClientRect() : null;
      return {
        ready: true,
        settled: heroIsSettled(),
        playable: heroIsPlayable(status),
        playbackAllowed: playbackAllowed,
        hasStarted: hasStarted,
        choiceResolved: choiceResolved,
        choiceMode: choiceMode,
        soundEnabled: soundEnabled,
        soundConsentEnabled: SOUND_CONSENT_ENABLED,
        promptVisible: promptVisible,
        ambientConfigured: !!SOUND_AUDIO_URL,
        ambientActive: !!(ambientAudio && !ambientAudio.paused),
        ambientVolume: SOUND_VOLUME,
        effectiveAmbientVolume: ambientAudio ? ambientAudio.volume : 0,
        audioGain: currentAudioGain,
        heroRiseAudioGain: heroRiseAudioGain(),
        curtainAudioGain: curtainAudioGain(status),
        heroRiseComplete:
          scrubRoot.getAttribute('data-hero-rise-complete') === 'true',
        heroTop: Math.round(rect.top * 100) / 100,
        estimatedHeroTop: Math.round(estimatedHeroTop() * 100) / 100,
        heroDocumentTop: heroDocumentTop,
        gateSyncCount: gateSyncCount,
        layoutReadCount: layoutReadCount,
        mediaResetCount: mediaResetCount,
        curtainRuntimeReadCount: curtainRuntimeReadCount,
        curtainStatusFallbackCount: curtainStatusFallbackCount,
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
            volume: video.volume,
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
