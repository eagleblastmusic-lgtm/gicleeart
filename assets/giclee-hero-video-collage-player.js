/* global window, document */
(function () {
  'use strict';

  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    return;
  }

  function wait(ms) {
    return new Promise(function (resolve) {
      setTimeout(resolve, ms);
    });
  }

  function clampMs(raw) {
    return Math.max(150, Math.min(4000, raw || 800));
  }

  function nextFrame() {
    return new Promise(function (resolve) {
      requestAnimationFrame(function () {
        requestAnimationFrame(resolve);
      });
    });
  }

  function loadVideo(video, url) {
    return new Promise(function (resolve, reject) {
      function cleanup() {
        video.removeEventListener('canplay', onReady);
        video.removeEventListener('error', onError);
      }
      function onReady() {
        cleanup();
        resolve();
      }
      function onError() {
        cleanup();
        reject(new Error('Video load failed'));
      }
      video.addEventListener('canplay', onReady, { once: true });
      video.addEventListener('error', onError, { once: true });
      video.src = url;
      video.load();
    });
  }

  function seekStart(video) {
    try {
      video.currentTime = 0;
    } catch (err) {
      /* ignore */
    }
  }

  function playVideo(video, opts) {
    opts = opts || {};
    video.muted = true;
    video.playsInline = true;
    if (opts.restart !== false) {
      seekStart(video);
    }
    var p = video.play();
    if (p && typeof p.catch === 'function') {
      return p.catch(function () {});
    }
    return Promise.resolve();
  }

  function resetVideoStyle(video) {
    video.style.opacity = '';
    video.style.transform = '';
  }

  function CollagePlayer(root, config) {
    this.root = root;
    this.clips = (config && config.clips) || [];
    this.loop = !config || config.loop !== false;
    this.index = 0;
    this.busy = false;

    this.stage = document.createElement('div');
    this.stage.className = 'giclee-collage__stage';
    this.stage.dataset.gicleeCollageBooting = '1';
    this.videoA = document.createElement('video');
    this.videoB = document.createElement('video');
    this.dip = document.createElement('div');
    this.dip.className = 'giclee-collage__dip';

    [this.videoA, this.videoB].forEach(function (v) {
      v.className = 'giclee-collage__video slide__video';
      v.muted = true;
      v.playsInline = true;
      v.preload = 'auto';
      v.setAttribute('aria-hidden', 'true');
    });

    this.stage.appendChild(this.videoA);
    this.stage.appendChild(this.videoB);
    this.stage.appendChild(this.dip);
    root.appendChild(this.stage);

    this.active = this.videoA;
    this.idle = this.videoB;
  }

  CollagePlayer.prototype.setTop = function (video) {
    this.active.classList.remove('giclee-collage__video--top');
    this.idle.classList.remove('giclee-collage__video--top');
    video.classList.add('giclee-collage__video--top');
    if (video === this.videoA) {
      this.active = this.videoA;
      this.idle = this.videoB;
    } else {
      this.active = this.videoB;
      this.idle = this.videoA;
    }
  };

  CollagePlayer.prototype.animate = function (el, keyframes, ms) {
    if (typeof el.animate === 'function') {
      return el.animate(keyframes, { duration: ms, fill: 'forwards', easing: 'ease-in-out' }).finished.catch(function () {});
    }
    return wait(ms);
  };

  CollagePlayer.prototype.runFadeIn = function (video, ms) {
    video.style.opacity = '0';
    return this.animate(video, [{ opacity: 0 }, { opacity: 1 }], ms).then(function () {
      resetVideoStyle(video);
    });
  };

  CollagePlayer.prototype.runFadeOut = function (video, ms) {
    video.style.opacity = '1';
    return this.animate(video, [{ opacity: 1 }, { opacity: 0 }], ms).then(function () {
      resetVideoStyle(video);
    });
  };

  CollagePlayer.prototype.runPushIn = function (video, fx, ms) {
    var fromX = fx === 'push_left' ? '100%' : '-100%';
    video.style.transform = 'translateX(' + fromX + ')';
    return this.animate(video, [{ transform: 'translateX(' + fromX + ')' }, { transform: 'translateX(0)' }], ms).then(function () {
      resetVideoStyle(video);
    });
  };

  CollagePlayer.prototype.runPushOut = function (video, fx, ms) {
    var toX = fx === 'push_left' ? '-100%' : '100%';
    video.style.transform = 'translateX(0)';
    return this.animate(video, [{ transform: 'translateX(0)' }, { transform: 'translateX(' + toX + ')' }], ms).then(function () {
      resetVideoStyle(video);
    });
  };

  CollagePlayer.prototype.runDipFrom = function (color, ms) {
    var self = this;
    self.dip.style.background = color;
    self.dip.style.opacity = '1';
    return self.animate(self.dip, [{ opacity: 1 }, { opacity: 0 }], ms).then(function () {
      self.dip.style.opacity = '0';
    });
  };

  CollagePlayer.prototype.runDipTo = function (color, ms) {
    var self = this;
    self.dip.style.background = color;
    self.dip.style.opacity = '0';
    return self.animate(self.dip, [{ opacity: 0 }, { opacity: 1 }], ms);
  };

  CollagePlayer.prototype.dipColor = function (fx) {
    return fx === 'dip_white' ? '#fff' : '#000';
  };

  CollagePlayer.prototype.isDip = function (fx) {
    return fx === 'dip_black' || fx === 'dip_white';
  };

  CollagePlayer.prototype.runEntry = function (video, fx, ms) {
    if (!fx || fx === 'none') {
      return Promise.resolve();
    }
    if (fx === 'fade_in') {
      return this.runFadeIn(video, ms);
    }
    if (this.isDip(fx)) {
      return this.runDipFrom(this.dipColor(fx), ms);
    }
    if (fx === 'push_left' || fx === 'push_right') {
      return this.runPushIn(video, fx, ms);
    }
    return Promise.resolve();
  };

  CollagePlayer.prototype.runExit = function (video, fx, ms) {
    if (!fx || fx === 'none') {
      return Promise.resolve();
    }
    if (fx === 'fade_out') {
      return this.runFadeOut(video, ms);
    }
    if (this.isDip(fx)) {
      return this.runDipTo(this.dipColor(fx), ms);
    }
    if (fx === 'push_left' || fx === 'push_right') {
      return this.runPushOut(video, fx, ms);
    }
    return Promise.resolve();
  };

  CollagePlayer.prototype.clipInMs = function (clip) {
    if (!clip) {
      return 800;
    }
    if (clip.transition_in_ms != null && clip.transition_in_ms !== '') {
      return clampMs(clip.transition_in_ms);
    }
    return clampMs(clip.transition_ms);
  };

  CollagePlayer.prototype.clipOutMs = function (clip) {
    if (!clip) {
      return 800;
    }
    if (clip.transition_out_ms != null && clip.transition_out_ms !== '') {
      return clampMs(clip.transition_out_ms);
    }
    return clampMs(clip.transition_ms);
  };

  CollagePlayer.prototype.getTransitionLead = function (nextIndex) {
    var nextClip = this.clips[nextIndex];
    var prevClip = this.clips[this.index];
    if (!nextClip || !prevClip) {
      return 0.12;
    }
    var outMs = this.clipOutMs(prevClip);
    var outFx = prevClip.transition_out || 'none';
    var inFx = nextClip.transition_in || 'none';
    if (nextClip.cross_effect || outFx !== 'none' || inFx !== 'none') {
      return outMs / 1000;
    }
    return 0.12;
  };

  CollagePlayer.prototype.prepareIncoming = function (nextClip) {
    var self = this;
    return loadVideo(self.idle, nextClip.url).then(function () {
      resetVideoStyle(self.idle);
      self.idle.pause();
      seekStart(self.idle);
      self.idle.style.opacity = '0';
    });
  };

  CollagePlayer.prototype.beginIncomingPlayback = function (video) {
    video.style.opacity = '0';
    return playVideo(video, { restart: true }).then(function () {
      return nextFrame();
    });
  };

  CollagePlayer.prototype.clearDip = function () {
    this.dip.style.opacity = '0';
  };

  CollagePlayer.prototype.fadeDipOut = function (ms) {
    var self = this;
    if (parseFloat(self.dip.style.opacity || '0') <= 0) {
      return Promise.resolve();
    }
    return self.animate(self.dip, [{ opacity: 1 }, { opacity: 0 }], ms).then(function () {
      self.clearDip();
    });
  };

  CollagePlayer.prototype.swapToIncoming = function (nextIndex, incoming) {
    incoming = incoming || this.idle;
    this.active.pause();
    resetVideoStyle(this.active);
    this.setTop(incoming);
    incoming.style.opacity = '';
    playVideo(incoming, { restart: true });
    this.index = nextIndex;
  };

  CollagePlayer.prototype.finishOutgoing = function () {
    this.active.pause();
    resetVideoStyle(this.active);
  };

  CollagePlayer.prototype.preloadNext = function (nextIndex) {
    var clip = this.clips[nextIndex];
    if (!clip || !clip.url) {
      return;
    }
    var self = this;
    loadVideo(self.idle, clip.url).catch(function () {});
  };

  CollagePlayer.prototype.runCrossTransition = function (prevClip, nextClip, nextIndex) {
    var self = this;
    var outFx = (prevClip && prevClip.transition_out) || 'fade_out';
    var inFx = (nextClip && nextClip.transition_in) || 'fade_in';
    var outMs = self.clipOutMs(prevClip);
    var inMs = self.clipInMs(nextClip);
    var outgoing = self.active;
    var incoming = self.idle;

    return self.prepareIncoming(nextClip).then(function () {
      if (outFx === 'none' && inFx === 'none') {
        self.swapToIncoming(nextIndex, incoming);
        return;
      }

      if (self.isDip(outFx) || self.isDip(inFx)) {
        return self
          .runExit(outgoing, outFx, outMs)
          .then(function () {
            self.finishOutgoing();
            self.setTop(incoming);
            return self.beginIncomingPlayback(incoming).then(function () {
              var tasks = [self.runEntry(incoming, inFx, inMs)];
              if (self.isDip(outFx) && !self.isDip(inFx)) {
                tasks.push(self.fadeDipOut(inMs));
              }
              return Promise.all(tasks);
            });
          })
          .then(function () {
            self.index = nextIndex;
            resetVideoStyle(incoming);
            self.preloadNextAfter(self.index);
          });
      }

      self.setTop(incoming);
      return self.beginIncomingPlayback(incoming).then(function () {
        var tasks = [];
        if (outFx && outFx !== 'none') {
          tasks.push(self.runExit(outgoing, outFx, outMs));
        }
        if (inFx && inFx !== 'none') {
          tasks.push(self.runEntry(incoming, inFx, inMs));
        }
        return Promise.all(tasks).then(function () {
          self.finishOutgoing();
          self.index = nextIndex;
          resetVideoStyle(incoming);
          self.preloadNextAfter(self.index);
        });
      });
    });
  };

  CollagePlayer.prototype.preloadNextAfter = function (currentIndex) {
    var preloadIdx = currentIndex + 1;
    if (preloadIdx >= this.clips.length) {
      preloadIdx = this.loop ? 0 : -1;
    }
    if (preloadIdx >= 0) {
      this.preloadNext(preloadIdx);
    }
  };

  CollagePlayer.prototype.runSequentialTransition = function (prevClip, nextClip, nextIndex) {
    var self = this;
    var outFx = (prevClip && prevClip.transition_out) || 'none';
    var inFx = (nextClip && nextClip.transition_in) || 'none';
    var outMs = self.clipOutMs(prevClip);
    var inMs = self.clipInMs(nextClip);
    var outgoing = self.active;
    var incoming = self.idle;

    return self.prepareIncoming(nextClip).then(function () {
      if (outFx === 'none' && inFx === 'none') {
        self.swapToIncoming(nextIndex, incoming);
        return;
      }

      if (self.isDip(outFx) && self.isDip(inFx)) {
        return self
          .runExit(outgoing, outFx, outMs)
          .then(function () {
            self.finishOutgoing();
            self.setTop(incoming);
            return self.beginIncomingPlayback(incoming).then(function () {
              return self.runEntry(incoming, inFx, inMs);
            });
          })
          .then(function () {
            self.index = nextIndex;
            resetVideoStyle(incoming);
            self.preloadNextAfter(self.index);
          });
      }

      var chain = Promise.resolve();
      if (outFx && outFx !== 'none') {
        chain = chain.then(function () {
          return self.runExit(outgoing, outFx, outMs);
        });
      }
      return chain
        .then(function () {
          self.finishOutgoing();
          self.setTop(incoming);
          if (inFx && inFx !== 'none') {
            return self.beginIncomingPlayback(incoming).then(function () {
              var tasks = [self.runEntry(incoming, inFx, inMs)];
              if (self.isDip(outFx) && !self.isDip(inFx)) {
                tasks.push(self.fadeDipOut(inMs));
              }
              return Promise.all(tasks);
            });
          }
          self.clearDip();
          self.swapToIncoming(nextIndex, incoming);
        })
        .then(function () {
          if (inFx && inFx !== 'none') {
            self.index = nextIndex;
            resetVideoStyle(incoming);
          }
          self.preloadNextAfter(self.index);
        });
    });
  };

  CollagePlayer.prototype.runTransition = function (nextIndex) {
    var self = this;
    var nextClip = this.clips[nextIndex];
    var prevClip = this.clips[this.index];
    if (!nextClip) {
      return Promise.resolve();
    }

    if (nextClip.cross_effect) {
      return self.runCrossTransition(prevClip, nextClip, nextIndex);
    }
    return self.runSequentialTransition(prevClip, nextClip, nextIndex);
  };

  CollagePlayer.prototype.onEnded = function () {
    var self = this;
    if (self.busy || !self.clips.length) {
      return;
    }
    var next = self.index + 1;
    if (next >= self.clips.length) {
      if (!self.loop) {
        return;
      }
      next = 0;
    }
    self.busy = true;
    self.runTransition(next)
      .catch(function () {})
      .finally(function () {
        self.busy = false;
      });
  };

  CollagePlayer.prototype.bindClipEnd = function (video) {
    var self = this;
    if (video.dataset.gicleeCollageBound === '1') {
      return;
    }
    video.dataset.gicleeCollageBound = '1';
    video.addEventListener('ended', function () {
      if (video === self.active && !self.busy) {
        self.onEnded();
      }
    });
    video.addEventListener('timeupdate', function () {
      if (video !== self.active || self.busy) {
        return;
      }
      var d = video.duration;
      if (!d || !isFinite(d) || d < 0.25) {
        return;
      }
      var next = self.index + 1;
      if (next >= self.clips.length) {
        if (!self.loop) {
          return;
        }
        next = 0;
      }
      var lead = self.getTransitionLead(next);
      if (video.currentTime >= d - lead) {
        self.onEnded();
      }
    });
  };

  CollagePlayer.prototype.start = function () {
    var self = this;
    if (!self.clips.length) {
      return;
    }
    var first = self.clips[0];
    var enter = first.transition_in || first.transition || 'none';
    var inMs = self.clipInMs(first);

    loadVideo(self.active, first.url)
      .then(function () {
        self.setTop(self.active);
        seekStart(self.active);
        self.active.pause();

        if (enter === 'fade_in') {
          self.active.style.opacity = '0';
          return playVideo(self.active, { restart: true })
            .then(function () {
              return nextFrame();
            })
            .then(function () {
              delete self.stage.dataset.gicleeCollageBooting;
              return self.runFadeIn(self.active, inMs);
            });
        }

        if (self.isDip(enter)) {
          self.dip.style.background = self.dipColor(enter);
          self.dip.style.opacity = '1';
          delete self.stage.dataset.gicleeCollageBooting;
          return playVideo(self.active, { restart: true }).then(function () {
            return self.runDipFrom(self.dipColor(enter), inMs);
          });
        }

        if (enter === 'push_left' || enter === 'push_right') {
          self.active.style.transform = 'translateX(' + (enter === 'push_left' ? '100%' : '-100%') + ')';
          delete self.stage.dataset.gicleeCollageBooting;
          return playVideo(self.active, { restart: true }).then(function () {
            return self.runPushIn(self.active, enter, inMs);
          });
        }

        delete self.stage.dataset.gicleeCollageBooting;
        return playVideo(self.active, { restart: true });
      })
      .catch(function () {
        delete self.stage.dataset.gicleeCollageBooting;
      })
      .then(function () {
        if (self.clips.length > 1) {
          self.preloadNext(1);
        }
      });

    self.bindClipEnd(self.videoA);
    self.bindClipEnd(self.videoB);
  };

  function init() {
    var config = window.GICLEE_HERO_VIDEO_COLLAGE;
    if (!config || !config.clips || !config.clips.length) {
      return;
    }
    document.querySelectorAll('[data-giclee-video-collage]').forEach(function (root) {
      if (root.dataset.gicleeCollageInit === '1') {
        return;
      }
      root.dataset.gicleeCollageInit = '1';
      new CollagePlayer(root, config).start();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  document.addEventListener('shopify:section:load', init);
})();
