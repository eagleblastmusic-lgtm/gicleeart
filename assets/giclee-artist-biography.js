(function () {
  "use strict";

  if (window.__gicleeArtistBiographyLoaded) return;
  window.__gicleeArtistBiographyLoaded = true;

  var GAB_MS = 880;
  var GAB_SHOWCASE_ENTER_MAX_AGE = 800;
  var panelRegistry = [];
  var showcaseTextEnterBound = false;
  var scrollShiftRegistry = [];
  var scrollShiftRafPending = false;
  var scrollShiftListenersBound = false;

  function getScrollShiftMaxPx() {
    var w = window.innerWidth || document.documentElement.clientWidth || 0;
    if (w <= 749) return 0;
    if (w < 990) return 96;
    return 160;
  }

  function getScrollShiftMaxBlur() {
    var w = window.innerWidth || document.documentElement.clientWidth || 0;
    if (w <= 749) return 0;
    if (w < 990) return 3;
    return 5.5;
  }

  function getScrollBgMaxZoom() {
    var w = window.innerWidth || document.documentElement.clientWidth || 0;
    if (w <= 749) return 0;
    if (w < 990) return 0.08;
    return 0.12;
  }

  function getScrollBgCoverBaseline(sectionHost) {
    if (
      sectionHost &&
      sectionHost.querySelector(
        "[data-gab-custom-bg] .giclee-artist-bio-bg__image--cover-scale"
      )
    ) {
      return 1.04;
    }
    return 1;
  }

  function getScrollBgStackScale(progress, sectionHost) {
    var baseline = getScrollBgCoverBaseline(sectionHost);
    return baseline * (1 + getScrollBgMaxZoom() * progress);
  }

  function scheduleScrollShiftUpdate() {
    if (scrollShiftRafPending) return;
    scrollShiftRafPending = true;
    window.requestAnimationFrame(function () {
      scrollShiftRafPending = false;
      scrollShiftRegistry.forEach(function (inst) {
        inst.tick();
      });
      updateHeaderScrollFade();
    });
  }

  function isArtistCollectionPage() {
    return (
      document.querySelector(".giclee-artist-biography-section") &&
      document.querySelector(".giclee-artist-collection-showcase-section")
    );
  }

  function getHeaderFadeRange() {
    var raw = getComputedStyle(document.body).getPropertyValue("--header-group-height");
    var h = parseFloat(raw) || 72;
    return Math.max(Math.round(h * 1.08), 64);
  }

  function getHeaderFadeTarget() {
    return document.getElementById("header-component");
  }

  function getHeaderFadeAnchorScroll() {
    var vh = window.innerHeight || document.documentElement.clientHeight || 800;
    return Math.max(Math.round(vh * 0.06), Math.round(getHeaderFadeRange() * 0.85), 48);
  }

  function stabilizeCollectionHeaderSticky(header, scrollY) {
    if (!header || header.getAttribute("sticky") !== "scroll-up") return;
    if (scrollY <= 1) {
      header.dataset.stickyState = "inactive";
      header.dataset.scrollDirection = "none";
      return;
    }
    if (header.dataset.stickyState === "idle") {
      header.dataset.stickyState = "active";
      header.dataset.scrollDirection = "none";
    }
  }

  function getHeaderFadeOpacity(scrollY) {
    var DIMMED = 0.1;
    if (scrollY <= 0) return 1;

    var anchor = getHeaderFadeAnchorScroll();
    var t = Math.min(1, scrollY / anchor);
    t = Math.pow(t, 0.35);

    if (scrollY <= anchor) {
      return 1 - (1 - DIMMED) * t;
    }

    var tailRange = Math.max(getHeaderFadeRange() * 0.32, 28);
    var beyond = scrollY - anchor;
    return Math.max(0, DIMMED * (1 - Math.min(1, beyond / tailRange)));
  }

  function updateHeaderScrollFade() {
    var header = getHeaderFadeTarget();
    if (!header || !isArtistCollectionPage()) return;

    if (prefersReducedMotion()) {
      header.classList.remove("giclee-header-scroll-fade");
      header.style.removeProperty("--gab-header-fade-opacity");
      header.style.removeProperty("pointer-events");
      return;
    }

    var scrollY = window.scrollY || window.pageYOffset || 0;
    stabilizeCollectionHeaderSticky(header, scrollY);
    var opacity = getHeaderFadeOpacity(scrollY);

    header.classList.add("giclee-header-scroll-fade");
    header.style.setProperty("--gab-header-fade-opacity", opacity.toFixed(3));
    header.style.pointerEvents = opacity < 0.12 ? "none" : "";
  }

  function initCollectionPageScrollChrome() {
    if (!isArtistCollectionPage()) return;
    bindScrollShiftListeners();
    scheduleScrollShiftUpdate();
  }

  function bindScrollShiftListeners() {
    if (scrollShiftListenersBound) return;
    scrollShiftListenersBound = true;
    window.addEventListener("scroll", scheduleScrollShiftUpdate, { passive: true });
    window.addEventListener("resize", scheduleScrollShiftUpdate, { passive: true });
    if (window.matchMedia) {
      var motionMq = window.matchMedia("(prefers-reduced-motion: reduce)");
      if (motionMq.addEventListener) {
        motionMq.addEventListener("change", scheduleScrollShiftUpdate);
      } else if (motionMq.addListener) {
        motionMq.addListener(scheduleScrollShiftUpdate);
      }
    }
  }

  function getPageScrollRange() {
    var docEl = document.documentElement;
    var body = document.body;
    var scrollHeight = Math.max(
      docEl.scrollHeight || 0,
      body ? body.scrollHeight : 0
    );
    var vh = window.innerHeight || docEl.clientHeight || 1;
    return Math.max(scrollHeight - vh, 1);
  }

  function easeScrollShiftProgress(linear) {
    var t = Math.min(1, Math.max(0, linear));
    return Math.pow(t, 1.4);
  }

  function GicleeArtistBioScrollShift(panel) {
    this.panel = panel;
    this.bioRoot = panel.root;
    this.sectionHost =
      panel.root.closest(".giclee-artist-biography-section") ||
      panel.root.closest(".shopify-section");

    if (!this.sectionHost || !this.bioRoot) return;

    this.sectionHost.classList.add("giclee-artist-bio--scroll-shift-host");
    this.resetShifts();
    bindScrollShiftListeners();
    scheduleScrollShiftUpdate();
  }

  GicleeArtistBioScrollShift.prototype.getProgress = function () {
    var scrollY = window.scrollY || window.pageYOffset || 0;
    if (scrollY <= 0) return 0;
    return Math.min(1, scrollY / getPageScrollRange());
  };

  GicleeArtistBioScrollShift.prototype.resetShifts = function () {
    if (!this.sectionHost) return;
    var bgBaseline = getScrollBgCoverBaseline(this.sectionHost);
    this.sectionHost.style.setProperty("--gab-scroll-title-x", "0px");
    this.sectionHost.style.setProperty("--gab-scroll-body-x", "0px");
    this.sectionHost.style.setProperty("--gab-scroll-shift-blur", "0px");
    this.sectionHost.style.setProperty("--gab-scroll-shift-opacity", "1");
    this.sectionHost.style.setProperty("--gab-scroll-bg-scale", "1");
    this.sectionHost.style.setProperty("--gab-scroll-bg-stack-scale", bgBaseline.toFixed(4));
  };

  GicleeArtistBioScrollShift.prototype.tick = function () {
    if (!this.sectionHost) return;

    var maxPx = getScrollShiftMaxPx();

    if (
      maxPx <= 0 ||
      prefersReducedMotion() ||
      (this.panel && this.panel.root && this.panel.root.classList.contains("is-transitioning"))
    ) {
      this.resetShifts();
      return;
    }

    var progress = easeScrollShiftProgress(this.getProgress());
    if (progress <= 0) {
      this.resetShifts();
      return;
    }

    var left = -maxPx * progress;
    var right = maxPx * progress;
    var blurPx = getScrollShiftMaxBlur() * progress;
    var opacity = Math.max(0, 1 - progress);
    var bgStackScale = getScrollBgStackScale(progress, this.sectionHost);

    this.sectionHost.style.setProperty("--gab-scroll-title-x", left.toFixed(2) + "px");
    this.sectionHost.style.setProperty("--gab-scroll-body-x", right.toFixed(2) + "px");
    this.sectionHost.style.setProperty("--gab-scroll-shift-blur", blurPx.toFixed(2) + "px");
    this.sectionHost.style.setProperty("--gab-scroll-shift-opacity", opacity.toFixed(3));
    this.sectionHost.style.setProperty(
      "--gab-scroll-bg-scale",
      (1 + getScrollBgMaxZoom() * progress).toFixed(4)
    );
    this.sectionHost.style.setProperty("--gab-scroll-bg-stack-scale", bgStackScale.toFixed(4));
  };

  GicleeArtistBioScrollShift.prototype.destroy = function () {
    if (this.sectionHost) {
      this.sectionHost.classList.remove("giclee-artist-bio--scroll-shift-host");
      this.resetShifts();
    }
  };

  function markBioScrollTargets(root) {
    if (!root) return;
    var bodyInner = root.querySelector(".giclee-artist-bio__body-inner");
    if (!bodyInner) return;

    bodyInner.removeAttribute("data-gab-scroll");
    bodyInner.querySelectorAll("[data-gab-scroll]").forEach(function (el) {
      el.removeAttribute("data-gab-scroll");
    });

    /* Szablon kolekcji (GicleeApp): h4 = daty życia — lewo; img = portret — prawo */
    bodyInner.querySelectorAll("h4").forEach(function (el) {
      el.setAttribute("data-gab-scroll", "left");
    });
    bodyInner.querySelectorAll("img").forEach(function (img) {
      img.setAttribute("data-gab-scroll", "right");
    });
    bodyInner
      .querySelectorAll("p, ul, ol, blockquote, h2, h3, h5, h6, table, pre, dl")
      .forEach(function (el) {
        el.setAttribute("data-gab-scroll", "right");
      });
  }

  function attachScrollShift(panel, instance) {
    if (!panel || !panel.root || !instance || !instance.bodyEl) return;
    var host =
      panel.root.closest(".giclee-artist-biography-section") ||
      panel.root.closest(".shopify-section");
    if (!host) return;

    for (var i = 0; i < scrollShiftRegistry.length; i++) {
      if (scrollShiftRegistry[i].sectionHost === host) return;
    }

    var shift = new GicleeArtistBioScrollShift(instance);
    if (shift.sectionHost) {
      scrollShiftRegistry.push(shift);
    }
  }

  function getExhibitionRoot() {
    return document.querySelector("[data-gacs-exhibition]");
  }

  function bindShowcaseTextEnterBridge() {
    if (showcaseTextEnterBound) return;
    var exhibition = getExhibitionRoot();
    if (!exhibition) return;
    showcaseTextEnterBound = true;
    exhibition.addEventListener("giclee:artist-showcase-enter", function (e) {
      var detail = e && e.detail;
      if (!detail || !detail.handle) return;
      panelRegistry.forEach(function (inst) {
        inst.onShowcaseTextEnter(detail);
      });
    });
  }

  function prefersReducedMotion() {
    return (
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    );
  }

  function getHandleFromPath() {
    var match = String(window.location.pathname).match(/\/collections\/([^/?#]+)/i);
    return match ? match[1] : "";
  }

  function findLegacyBioSection() {
    var exhibition = document.querySelector("[data-gacs-exhibition]");
    if (!exhibition) return null;

    var gallerySection = exhibition.closest(".shopify-section");
    if (!gallerySection) return null;

    var el = gallerySection.previousElementSibling;
    while (el) {
      if (!el.classList || !el.classList.contains("shopify-section")) {
        el = el.previousElementSibling;
        continue;
      }

      var title = el.querySelector("h1");
      var body = el.querySelector("rte-formatter") || el.querySelector(".rte");
      if (title && body) {
        return {
          root: el,
          titleEl: title,
          bodyEl: body,
          bodyInner: body.querySelector("div") || body,
          isLegacy: true,
        };
      }
      break;
    }
    return null;
  }

  function resolveBioPanels() {
    var panels = [];

    document.querySelectorAll("[data-giclee-artist-bio]").forEach(function (root) {
      panels.push({
        root: root,
        titleEl: root.querySelector('[data-gab-field="title"]'),
        bodyEl: root.querySelector('[data-gab-field="body"]'),
        bodyInner: root.querySelector(".giclee-artist-bio__body-inner"),
        isLegacy: false,
      });
    });

    if (!panels.length) {
      var legacy = findLegacyBioSection();
      if (legacy) panels.push(legacy);
    }

    return panels;
  }

  function GicleeArtistBiography(panel) {
    this.root = panel.root;
    this.titleEl = panel.titleEl;
    this.bodyEl = panel.bodyEl;
    this.bodyInner = panel.bodyInner;
    this.isLegacy = !!panel.isLegacy;
    this.state = null;
    this.inView = false;
    this.transitioning = false;
    this.transitionSeq = 0;
    this.transitionPhase = "idle";
    this.targetArtist = null;
    this.targetDirection = 1;
    this.unsub = null;
    this.io = null;

    if (!this.bodyEl) return;

    if (!this.root.getAttribute("data-gab-handle")) {
      this.root.setAttribute("data-gab-handle", getHandleFromPath());
    }

    if (this.isLegacy) {
      this.root.classList.add("giclee-artist-bio", "giclee-artist-bio--legacy");
    }

    this.onChange = this.onAuthorChange.bind(this);
    this.resetLayoutLock();
    this.bindVisibility();
    this.bindState();
    var section = this.getBioSection();
    if (section && this.root.getAttribute("data-gab-menu-gradient")) {
      applyBioMenuGradientShell(
        section,
        this.root.getAttribute("data-gab-menu-gradient")
      );
    }
    if (section && this.root.getAttribute("data-gab-has-custom-bg") === "true") {
      syncBioSchemeBackground(section, true);
      var heroImg = section.querySelector("[data-gab-bg-image]:not([hidden])");
      if (
        heroImg &&
        section.classList.contains("giclee-artist-biography-section--bg-pending")
      ) {
        revealBioBgWhenReady(section, heroImg);
      }
    }
    markBioScrollTargets(this.root);
  }

  GicleeArtistBiography.prototype.bindState = function () {
    var self = this;
    var attempts = 0;

    function attach() {
      if (!window.GicleeActiveAuthor) {
        attempts += 1;
        if (attempts < 80) {
          window.setTimeout(attach, 50);
        }
        return;
      }
      if (self.unsub) {
        self.unsub();
        self.unsub = null;
      }
      self.state = window.GicleeActiveAuthor;
      self.unsub = self.state.subscribe(self.onChange);
      window.requestAnimationFrame(function () {
        self.syncInitialBioBackground();
      });
    }

    attach();
  };

  GicleeArtistBiography.prototype.bindVisibility = function () {
    var self = this;
    var observeTarget = this.isLegacy
      ? this.root.querySelector(".section") || this.root
      : this.root;

    if (!("IntersectionObserver" in window)) {
      this.inView = false;
      return;
    }

    this.io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          self.inView = entry.isIntersecting;
          self.root.classList.toggle("is-in-view", self.inView);
        });
      },
      { root: null, threshold: 0.08 }
    );
    this.io.observe(observeTarget);
  };

  GicleeArtistBiography.prototype.clearStates = function () {
    this.root.classList.remove(
      "is-transitioning",
      "is-exiting-next",
      "is-exiting-prev",
      "is-entering-next",
      "is-entering-prev"
    );
    this.transitionPhase = "idle";
  };

  GicleeArtistBiography.prototype.setExitPhase = function () {
    var dir = this.targetDirection;
    this.transitionPhase = "exit";
    this.beginBgCrossfade();
    this.root.classList.remove("is-entering-next", "is-entering-prev");
    this.root.classList.add("is-transitioning");
    this.root.classList.remove("is-exiting-next", "is-exiting-prev");
    this.root.classList.add(dir > 0 ? "is-exiting-next" : "is-exiting-prev");
  };

  GicleeArtistBiography.prototype.swapAndEnter = function (seq) {
    this.enterTextNormal(seq);
  };

  GicleeArtistBiography.prototype.clearTextEnterWait = function () {
    if (this._textEnterFallbackTimer) {
      window.clearTimeout(this._textEnterFallbackTimer);
      this._textEnterFallbackTimer = null;
    }
  };

  GicleeArtistBiography.prototype.shouldSyncTextWithShowcase = function () {
    return !!getExhibitionRoot() && this.inView && !prefersReducedMotion();
  };

  GicleeArtistBiography.prototype.onShowcaseTextEnter = function (detail) {
    if (!this.pendingTextEnterSeq) return;
    if (this.transitionSeq !== this.pendingTextEnterSeq) return;
    if (!this.targetArtist || !detail || detail.handle !== this.targetArtist.handle) {
      return;
    }
    this.enterTextWithShowcase(this.pendingTextEnterSeq);
  };

  GicleeArtistBiography.prototype.queueTextEnterAfterShowcase = function (seq) {
    var self = this;
    self.pendingTextEnterSeq = seq;
    bindShowcaseTextEnterBridge();

    var exhibition = getExhibitionRoot();
    var last = exhibition && exhibition._gacsLastShowcaseEnter;
    if (
      last &&
      self.targetArtist &&
      last.handle === self.targetArtist.handle &&
      Date.now() - last.time < GAB_SHOWCASE_ENTER_MAX_AGE
    ) {
      self.enterTextWithShowcase(seq);
      return;
    }

    self.clearTextEnterWait();
    self._textEnterFallbackTimer = window.setTimeout(function () {
      if (self.pendingTextEnterSeq !== seq || self.transitionSeq !== seq) return;
      self.enterTextNormal(seq);
    }, GAB_MS + 400);
  };

  GicleeArtistBiography.prototype.applyTextContent = function (artist) {
    if (!artist) return;

    var html = artist.bioHtml || "";
    if (!html) return;

    if (this.titleEl) {
      this.titleEl.textContent = artist.artistName || "";
    }

    if (this.isLegacy) {
      if (this.bodyInner) {
        this.bodyInner.innerHTML = html;
      } else if (this.bodyEl) {
        this.bodyEl.innerHTML = html;
      }
    } else if (this.bodyInner) {
      this.bodyInner.innerHTML = html;
    } else if (this.bodyEl) {
      this.bodyEl.innerHTML =
        '<div class="giclee-artist-bio__body-inner">' + html + "</div>";
      this.bodyInner = this.bodyEl.querySelector(".giclee-artist-bio__body-inner");
    }

    markBioScrollTargets(this.root);
    this.root.setAttribute("data-gab-handle", artist.handle || "");
    this.resetLayoutLock();
  };

  GicleeArtistBiography.prototype.enterTextWithShowcase = function (seq) {
    var self = this;
    self.clearTextEnterWait();
    self.pendingTextEnterSeq = null;

    var activeArtist = self.targetArtist;
    if (!activeArtist || !activeArtist.bioHtml) {
      self.clearStates();
      self.transitioning = false;
      return;
    }

    var enterDir = self.targetDirection;
    self.applyTextContent(activeArtist);
    self.transitionPhase = "enter";
    self.root.classList.add(enterDir > 0 ? "is-entering-next" : "is-entering-prev");
    self.root.classList.remove("is-exiting-next", "is-exiting-prev");

    void self.root.offsetHeight;

    window.requestAnimationFrame(function () {
      window.requestAnimationFrame(function () {
        if (seq !== self.transitionSeq) return;
        self.root.classList.remove("is-entering-next", "is-entering-prev");
        self.transitionPhase = "enter-fade";
        self.waitTransition(function () {
          if (seq !== self.transitionSeq) return;
          self.finishBioTransition();
        });
      });
    });
  };

  GicleeArtistBiography.prototype.enterTextNormal = function (seq) {
    var self = this;
    self.clearTextEnterWait();
    self.pendingTextEnterSeq = null;

    var activeArtist = self.targetArtist;
    if (!activeArtist || !activeArtist.bioHtml) {
      self.clearStates();
      self.transitioning = false;
      return;
    }

    var enterDir = self.targetDirection;
    self.applyContent(activeArtist);
    self.transitionPhase = "enter";
    self.root.classList.add(enterDir > 0 ? "is-entering-next" : "is-entering-prev");
    self.root.classList.remove("is-exiting-next", "is-exiting-prev");

    void self.root.offsetHeight;

    window.requestAnimationFrame(function () {
      window.requestAnimationFrame(function () {
        if (seq !== self.transitionSeq) return;
        self.root.classList.remove("is-entering-next", "is-entering-prev");
        self.transitionPhase = "enter-fade";
        self.waitTransition(function () {
          if (seq !== self.transitionSeq) return;
          self.finishBioTransition();
        });
      });
    });
  };

  GicleeArtistBiography.prototype.finishExitPhase = function (seq) {
    this.commitBgCrossfade();
    if (
      this.targetArtist &&
      this.root.getAttribute("data-gab-handle") === this.targetArtist.handle
    ) {
      return;
    }
    if (this.shouldSyncTextWithShowcase()) {
      this.queueTextEnterAfterShowcase(seq);
      return;
    }
    this.enterTextNormal(seq);
  };

  GicleeArtistBiography.prototype.runExitThenEnter = function (seq) {
    var self = this;
    self.clearTextEnterWait();
    self.pendingTextEnterSeq = null;
    if (self.shouldSyncTextWithShowcase()) {
      self.pendingTextEnterSeq = seq;
      bindShowcaseTextEnterBridge();
    }
    self.setExitPhase();
    self.waitTransition(function () {
      if (seq !== self.transitionSeq) return;
      self.finishExitPhase(seq);
    });
  };

  GicleeArtistBiography.prototype.resetLayoutLock = function () {
    var node = this.root;
    while (node) {
      if (node.style) {
        node.style.height = "";
        node.style.overflow = "";
        node.style.minHeight = "";
        node.style.maxHeight = "";
      }
      if (node.dataset) {
        delete node.dataset.gacsLayoutLocked;
      }
      if (
        node.classList &&
        (node.classList.contains("giclee-artist-biography-section") ||
          node.classList.contains("shopify-section"))
      ) {
        break;
      }
      node = node.parentElement;
    }

    var bioSection = this.root.closest(".giclee-artist-biography-section");
    if (bioSection) {
      var bg = bioSection.querySelector(".custom-section-background");
      if (bg && bg.style) {
        bg.style.height = "";
        bg.style.minHeight = "";
        bg.style.maxHeight = "";
        bg.style.bottom = "";
      }
    }

    if (window.GicleeArtistLayoutSync && window.GicleeArtistLayoutSync.releaseBioLayoutLocks) {
      window.GicleeArtistLayoutSync.releaseBioLayoutLocks(this.root);
    }
  };

  GicleeArtistBiography.prototype.applyContent = function (artist) {
    if (!artist) return;

    var html = artist.bioHtml || "";
    if (!html) return;

    if (this.titleEl) {
      this.titleEl.textContent = artist.artistName || "";
    }

    if (this.isLegacy) {
      if (this.bodyInner) {
        this.bodyInner.innerHTML = html;
      } else if (this.bodyEl) {
        this.bodyEl.innerHTML = html;
      }
    } else if (this.bodyInner) {
      this.bodyInner.innerHTML = html;
    } else if (this.bodyEl) {
      this.bodyEl.innerHTML =
        '<div class="giclee-artist-bio__body-inner">' + html + "</div>";
      this.bodyInner = this.bodyEl.querySelector(".giclee-artist-bio__body-inner");
    }

    markBioScrollTargets(this.root);
    this.root.setAttribute("data-gab-handle", artist.handle || "");
    this.applyBackground(artist);
    this.syncBioBackgroundShell();
    this.resetLayoutLock();
  };

  GicleeArtistBiography.prototype.getBioSection = function () {
    return this.root.closest(".giclee-artist-biography-section");
  };

  GicleeArtistBiography.prototype.ensureBgStack = function (section) {
    var wrap = section.querySelector("[data-gab-bg-wrap]");
    if (!wrap) return null;

    var customBg = wrap.querySelector("[data-gab-custom-bg]");
    if (!customBg) return null;

    if (!this.bgStack || this.bgStack.customBg !== customBg) {
      var stackEl = customBg.querySelector("[data-gab-bg-stack]");
      var layers = [];

      if (stackEl) {
        layers = Array.prototype.slice.call(
          stackEl.querySelectorAll("[data-gab-bg-layer]")
        );
      } else {
        var legacyImg = customBg.querySelector("[data-gab-bg-image]");
        if (!legacyImg) return null;

        stackEl = document.createElement("div");
        stackEl.className = "giclee-artist-bio-bg__stack";
        stackEl.setAttribute("data-gab-bg-stack", "");
        legacyImg.classList.add("giclee-artist-bio-bg__layer");
        if (!legacyImg.getAttribute("data-gab-bg-layer")) {
          legacyImg.setAttribute("data-gab-bg-layer", "0");
        }
        customBg.insertBefore(stackEl, legacyImg);
        stackEl.appendChild(legacyImg);

        var altImg = document.createElement("img");
        altImg.className = "giclee-artist-bio-bg__layer giclee-artist-bio-bg__image";
        altImg.setAttribute("data-gab-bg-layer", "1");
        altImg.alt = "";
        altImg.decoding = "async";
        altImg.hidden = true;
        stackEl.appendChild(altImg);
        layers = [legacyImg, altImg];
      }

      if (layers.length < 2) return null;

      this.bgStack = {
        wrap: wrap,
        customBg: customBg,
        stackEl: stackEl,
        layers: layers,
        activeIndex: 0,
      };
      this.syncBgLayerState(section);
    }

    return this.bgStack;
  };

  GicleeArtistBiography.prototype.getBgLayerPair = function (section) {
    var stack = this.ensureBgStack(section);
    if (!stack) return null;

    var active = stack.layers[stack.activeIndex];
    var incoming = stack.layers[1 - stack.activeIndex];
    return { stack: stack, active: active, incoming: incoming };
  };

  function normalizeBioBgUrl(url) {
    if (!url) return "";
    try {
      var anchor = document.createElement("a");
      anchor.href = String(url).trim();
      return anchor.href;
    } catch (_err) {
      return String(url).trim();
    }
  }

  function shopifyBioBgBaseUrl(url) {
    if (!url) return "";
    try {
      var parsed = new URL(String(url).trim(), window.location.origin);
      parsed.searchParams.delete("width");
      parsed.searchParams.delete("height");
      parsed.searchParams.delete("crop");
      return parsed.toString();
    } catch (_err) {
      return String(url).trim();
    }
  }

  function bioBackgroundDisplayUrl(url) {
    var base = shopifyBioBgBaseUrl(url);
    if (!base) return "";
    if (base.indexOf("cdn.shopify.com") === -1 && base.indexOf("/cdn/") === -1) {
      return base;
    }
    if (/[?&]width=\d+/i.test(base)) return base;
    var sep = base.indexOf("?") === -1 ? "?" : "&";
    return base + sep + "width=3840";
  }

  function normalizeBioMenuGradient(raw) {
    if (raw == null || raw === "") return "wide";
    var text = String(raw).trim().toLowerCase();
    if (
      text === "none" ||
      text === "off" ||
      text === "0" ||
      text === "false" ||
      text === "nie" ||
      text === "bez gradientu"
    ) {
      return "none";
    }
    if (
      text === "narrow" ||
      text === "waski" ||
      text === "wąski" ||
      text === "gradient wąski" ||
      text === "was"
    ) {
      return "narrow";
    }
    if (
      text === "wide_v2" ||
      text === "wide-v2" ||
      text === "widev2" ||
      text === "gradient szeroki v2" ||
      text === "szeroki v2"
    ) {
      return "wide_v2";
    }
    if (
      text === "wide_v3" ||
      text === "wide-v3" ||
      text === "widev3" ||
      text === "gradient szeroki v3" ||
      text === "szeroki v3"
    ) {
      return "wide_v3";
    }
    if (
      text === "wide_v3_bottom" ||
      text === "wide-v3-bottom" ||
      text === "widev3bottom" ||
      text === "wide_v3_dol" ||
      text === "wide_v3_dół" ||
      text === "gradient szeroki v3 + dół" ||
      text === "gradient szeroki v3 + dol" ||
      text === "szeroki v3 + dół" ||
      text === "szeroki v3 + dol"
    ) {
      return "wide_v3_bottom";
    }
    if (
      text === "wide_bottom" ||
      text === "wide-bottom" ||
      text === "widebottom" ||
      text === "wide_dol" ||
      text === "wide_dół" ||
      text === "gradient szeroki + dół" ||
      text === "gradient szeroki + dol" ||
      text === "szeroki + dół" ||
      text === "szeroki + dol"
    ) {
      return "wide_bottom";
    }
    return "wide";
  }

  function applyBioMenuGradientShell(section, value) {
    if (!section) return;
    var normalized = normalizeBioMenuGradient(value);
    var targets = [];
    var inner = section.querySelector(".section");
    if (inner) targets.push(inner);
    if (targets.indexOf(section) === -1) targets.push(section);
    targets.forEach(function (el) {
      el.classList.remove("giclee-artist-biography-section--menu-gradient-wide");
      el.classList.remove("giclee-artist-biography-section--menu-gradient-wide-bottom");
      el.classList.remove("giclee-artist-biography-section--menu-gradient-wide-v2");
      el.classList.remove("giclee-artist-biography-section--menu-gradient-wide-v3");
      el.classList.remove("giclee-artist-biography-section--menu-gradient-wide-v3-bottom");
      el.classList.remove("giclee-artist-biography-section--menu-gradient-narrow");
      if (normalized === "wide_v3_bottom") {
        el.classList.add("giclee-artist-biography-section--menu-gradient-wide-v3-bottom");
      } else if (normalized === "wide_v3") {
        el.classList.add("giclee-artist-biography-section--menu-gradient-wide-v3");
      } else if (normalized === "wide_v2") {
        el.classList.add("giclee-artist-biography-section--menu-gradient-wide-v2");
      } else if (normalized === "wide_bottom") {
        el.classList.add("giclee-artist-biography-section--menu-gradient-wide-bottom");
      } else if (normalized === "wide") {
        el.classList.add("giclee-artist-biography-section--menu-gradient-wide");
      } else if (normalized === "narrow") {
        el.classList.add("giclee-artist-biography-section--menu-gradient-narrow");
      }
    });
  }

  function syncBioSchemeBackground(section, hasCustomBg) {
    if (!section) return;
    var schemeBg = section.querySelector(":scope > .section-background");
    if (schemeBg) schemeBg.hidden = !!hasCustomBg;
    var innerSection = section.querySelector(":scope > .section");
    if (innerSection) {
      innerSection.classList.toggle(
        "giclee-artist-biography-section--custom-bg",
        !!hasCustomBg
      );
    }
  }

  function setBioBgPending(section, pending) {
    if (!section) return;
    var innerSection = section.querySelector(":scope > .section");
    section.classList.toggle("giclee-artist-biography-section--bg-pending", !!pending);
    if (innerSection) {
      innerSection.classList.toggle("giclee-artist-biography-section--bg-pending", !!pending);
    }
    if (!pending) {
      section.classList.add("giclee-artist-biography-section--bg-ready");
      if (innerSection) {
        innerSection.classList.add("giclee-artist-biography-section--bg-ready");
      }
    }
  }

  function revealBioBgWhenReady(section, img) {
    if (!section) return;
    function ready() {
      setBioBgPending(section, false);
    }
    if (!img || !img.getAttribute("src") || img.hidden) {
      ready();
      return;
    }
    if (img.complete && img.naturalWidth > 0) {
      ready();
      return;
    }
    setBioBgPending(section, true);
    img.addEventListener("load", ready, { once: true });
    img.addEventListener("error", ready, { once: true });
    window.setTimeout(ready, 6000);
  }

  GicleeArtistBiography.prototype.parseBackgroundMeta = function (artist) {
    var url =
      artist && artist.bioBackgroundUrl
        ? String(artist.bioBackgroundUrl).trim()
        : "";
    var posX = 50;
    if (artist && artist.bioBackgroundPosX != null && artist.bioBackgroundPosX !== "") {
      posX = parseInt(artist.bioBackgroundPosX, 10);
      if (!isFinite(posX)) posX = 50;
      if (posX < 0) posX = 0;
      if (posX > 100) posX = 100;
    }
    var overlayPct = 100;
    if (
      artist &&
      artist.bioBackgroundOverlayPct != null &&
      artist.bioBackgroundOverlayPct !== ""
    ) {
      overlayPct = parseInt(artist.bioBackgroundOverlayPct, 10);
      if (!isFinite(overlayPct)) overlayPct = 100;
      if (overlayPct < 0) overlayPct = 0;
      if (overlayPct > 100) overlayPct = 100;
    }
    var coverScale = false;
    if (
      artist &&
      artist.bioBackgroundCoverScale != null &&
      artist.bioBackgroundCoverScale !== ""
    ) {
      coverScale =
        artist.bioBackgroundCoverScale === true ||
        artist.bioBackgroundCoverScale === "true" ||
        artist.bioBackgroundCoverScale === 1 ||
        artist.bioBackgroundCoverScale === "1";
    }

    var radialMask = parseBioRadialMask(
      artist && artist.bioBackgroundRadialMask
    );

    var menuGradient = normalizeBioMenuGradient(
      artist && artist.bioBackgroundMenuGradient
    );

    return {
      url: url,
      posX: posX,
      overlayPct: overlayPct,
      coverScale: coverScale,
      radialMask: radialMask,
      menuGradient: menuGradient,
    };
  };

  function parseBioRadialMask(raw) {
    var defaults = {
      enabled: false,
      cx: 35,
      cy: 50,
      rx: 55,
      ry: 85,
      feather: 50,
      exposure: 50,
    };
    if (raw == null || raw === "") {
      return defaults;
    }
    var parsed = raw;
    if (typeof raw === "string") {
      try {
        parsed = JSON.parse(raw);
      } catch (_err) {
        return defaults;
      }
    }
    if (!parsed || typeof parsed !== "object") {
      return defaults;
    }
    function clampInt(value, fallback, min, max) {
      var n = parseInt(value, 10);
      if (!isFinite(n)) n = fallback;
      if (n < min) n = min;
      if (n > max) n = max;
      return n;
    }
    var enabled =
      parsed.enabled === true ||
      parsed.enabled === "true" ||
      parsed.enabled === 1 ||
      parsed.enabled === "1";
    return {
      enabled: enabled,
      cx: clampInt(parsed.cx, defaults.cx, 0, 100),
      cy: clampInt(parsed.cy, defaults.cy, 0, 100),
      rx: clampInt(parsed.rx, defaults.rx, 10, 150),
      ry: clampInt(parsed.ry, defaults.ry, 10, 150),
      feather: clampInt(parsed.feather, defaults.feather, 0, 100),
      exposure: clampInt(parsed.exposure, defaults.exposure, 0, 100),
    };
  }

  function applyBioRadialMaskEl(el, mask) {
    if (!el || !mask) return;
    if (!mask.enabled || mask.exposure <= 0) {
      el.hidden = true;
      return;
    }
    el.hidden = false;
    el.style.setProperty("--gab-radial-cx", String(mask.cx) + "%");
    el.style.setProperty("--gab-radial-cy", String(mask.cy) + "%");
    el.style.setProperty("--gab-radial-rx", String(mask.rx) + "%");
    el.style.setProperty("--gab-radial-ry", String(mask.ry) + "%");
    el.style.setProperty("--gab-radial-feather", String(mask.feather));
    el.style.setProperty("--gab-radial-exposure", String(mask.exposure));
  }

  GicleeArtistBiography.prototype.applyBackgroundMeta = function (section, artist, wrap) {
    if (!wrap) {
      wrap = section.querySelector("[data-gab-bg-wrap]");
    }
    if (!wrap) return false;

    var meta = this.parseBackgroundMeta(artist);
    applyBioMenuGradientShell(section, meta.menuGradient);
    var customBg = wrap.querySelector("[data-gab-custom-bg]");
    var defaultBg = wrap.querySelector("[data-gab-default-bg]");
    var overlayEl = customBg
      ? customBg.querySelector("[data-gab-bg-overlay]")
      : null;
    var radialEl = customBg
      ? customBg.querySelector("[data-gab-bg-radial-mask]")
      : null;

    if (meta.url) {
      section.classList.add("giclee-artist-biography-section--custom-bg");
      syncBioSchemeBackground(section, true);
      section.style.setProperty(
        "--gab-bg-overlay-opacity",
        String(meta.overlayPct / 100)
      );
      if (customBg) customBg.hidden = false;
      if (overlayEl) {
        overlayEl.style.opacity = String(meta.overlayPct / 100);
      }
      applyBioRadialMaskEl(radialEl, meta.radialMask);
      if (defaultBg) defaultBg.hidden = true;
      return true;
    }

    section.classList.remove("giclee-artist-biography-section--custom-bg");
    syncBioSchemeBackground(section, false);
    if (customBg) customBg.hidden = true;
    if (radialEl) radialEl.hidden = true;
    if (defaultBg) defaultBg.hidden = false;
    return false;
  };

  GicleeArtistBiography.prototype.applyBackgroundLayer = function (img, artist, opts) {
    if (!img || !artist) return;

    opts = opts || {};
    var meta = this.parseBackgroundMeta(artist);
    if (!meta.url) {
      img.hidden = true;
      return;
    }

    img.hidden = false;
    img.style.objectPosition = meta.posX + "% center";
    img.classList.toggle("giclee-artist-bio-bg__image--cover-scale", meta.coverScale);
    img.setAttribute("data-gab-cover-scale", meta.coverScale ? "true" : "false");

    var nextUrl = bioBackgroundDisplayUrl(meta.url);
    var currentBase = shopifyBioBgBaseUrl(img.getAttribute("src") || img.src || "");
    var nextBase = shopifyBioBgBaseUrl(nextUrl);

    function finishSwap() {
      img.classList.remove("is-swapping");
      img.onload = null;
      img.onerror = null;
    }

    if (currentBase && nextBase && currentBase === nextBase) {
      finishSwap();
      revealBioBgWhenReady(this.getBioSection(), img);
      return;
    }

    var section = this.getBioSection();

    if (opts.instant) {
      finishSwap();
      img.setAttribute("src", nextUrl);
      revealBioBgWhenReady(section, img);
      return;
    }

    var finalized = false;
    var done = function () {
      if (finalized) return;
      finalized = true;
      finishSwap();
      revealBioBgWhenReady(section, img);
    };

    setBioBgPending(section, true);
    img.classList.add("is-swapping");
    img.onload = done;
    img.onerror = done;
    img.setAttribute("src", nextUrl);
    if (img.complete) {
      done();
    } else {
      window.setTimeout(done, 4000);
    }
  };

  GicleeArtistBiography.prototype.syncBioBackgroundShell = function () {
    var section = this.getBioSection();
    if (!section || !section.classList.contains("giclee-artist-biography-section--custom-bg")) {
      return;
    }

    var wrap = section.querySelector("[data-gab-bg-wrap]");
    var heroHeight = this.root ? this.root.offsetHeight : 0;
    if (wrap && heroHeight > 0) {
      wrap.style.minHeight = heroHeight + "px";
    }

    if (this.bgStack) {
      this.bgStack.customBg.classList.remove("is-bg-crossfading");
      this.bgStack.layers.forEach(function (layer, index) {
        layer.classList.remove("is-bg-outgoing", "is-bg-incoming");
        if (index !== this.bgStack.activeIndex) {
          layer.hidden = true;
          layer.classList.add("is-bg-inactive");
        }
      }, this);
      this.syncBgLayerState(section);
    }

    var activeImg = section.querySelector("[data-gab-bg-image]");
    if (activeImg) {
      activeImg.classList.remove("is-swapping");
    }
  };

  GicleeArtistBiography.prototype.syncInitialBioBackground = function () {
    if (!this.state || !this.state.activeAuthor) return;
    var artist = this.state.activeAuthor;
    if (!artist || !artist.bioBackgroundUrl) return;
    if (this.root.getAttribute("data-gab-handle") !== artist.handle) return;

    this.applyBackground(artist, { forceActiveLayer: true, instant: true });
    this.syncBioBackgroundShell();
  };

  GicleeArtistBiography.prototype.syncBgLayerState = function (section) {
    var pair = this.getBgLayerPair(section);
    if (!pair) return;

    pair.stack.layers.forEach(function (layer, index) {
      layer.classList.toggle("is-bg-inactive", index !== pair.stack.activeIndex);
    });
  };

  GicleeArtistBiography.prototype.beginBgCrossfade = function () {
    if (!this.inView || prefersReducedMotion() || !this.targetArtist) return;

    var section = this.getBioSection();
    if (!section) return;

    var meta = this.parseBackgroundMeta(this.targetArtist);
    if (!meta.url) return;

    var pair = this.getBgLayerPair(section);
    if (!pair) return;

    if (pair.stack.customBg.classList.contains("is-bg-crossfading")) {
      pair.stack.layers.forEach(function (layer) {
        layer.classList.remove("is-bg-outgoing", "is-bg-incoming");
      });
      pair.stack.customBg.classList.remove("is-bg-crossfading");
    }

    this.applyBackgroundMeta(section, this.targetArtist, pair.stack.wrap);
    this.applyBackgroundLayer(pair.incoming, this.targetArtist, { instant: true });

    pair.incoming.hidden = false;
    pair.incoming.classList.remove("is-bg-inactive");
    pair.active.classList.remove("is-bg-inactive");
    pair.active.classList.add("is-bg-outgoing");
    pair.incoming.classList.add("is-bg-incoming");
    pair.stack.customBg.classList.add("is-bg-crossfading");
  };

  GicleeArtistBiography.prototype.commitBgCrossfade = function () {
    var section = this.getBioSection();
    if (!section || !this.bgStack) return;

    var stack = this.bgStack;
    if (!stack.customBg.classList.contains("is-bg-crossfading")) return;

    stack.layers.forEach(function (layer) {
      layer.classList.remove("is-bg-outgoing", "is-bg-incoming");
    });
    stack.customBg.classList.remove("is-bg-crossfading");
    stack.activeIndex = 1 - stack.activeIndex;

    var inactive = stack.layers[1 - stack.activeIndex];
    if (inactive) inactive.hidden = true;

    this.syncBgLayerState(section);
  };

  GicleeArtistBiography.prototype.applyBackground = function (artist, opts) {
    opts = opts || {};
    var section = this.getBioSection();
    if (!section) return;

    var wrap = section.querySelector("[data-gab-bg-wrap]");
    if (!wrap) return;

    var hasCustom = this.applyBackgroundMeta(section, artist, wrap);
    if (!hasCustom) return;

    if (this.root.classList.contains("is-transitioning") && !opts.forceActiveLayer) {
      return;
    }

    var pair = this.getBgLayerPair(section);
    if (!pair) return;

    this.applyBackgroundLayer(pair.active, artist, opts);
    this.syncBgLayerState(section);
  };

  GicleeArtistBiography.prototype.waitTransition = function (callback) {
    var target = this.bodyInner || this.bodyEl;
    if (!target || !this.inView || prefersReducedMotion()) {
      callback();
      return;
    }

    var finished = false;
    var done = function () {
      if (finished) return;
      finished = true;
      target.removeEventListener("transitionend", onEnd);
      callback();
    };
    var onEnd = function (e) {
      if (e.target !== target) return;
      if (e.propertyName !== "opacity" && e.propertyName !== "transform") return;
      done();
    };

    target.addEventListener("transitionend", onEnd);
    window.setTimeout(done, GAB_MS + 120);
  };

  GicleeArtistBiography.prototype.reconcileBioTarget = function () {
    var artist = this.targetArtist;
    if (!artist || !artist.bioHtml) return;
    if (this.root.getAttribute("data-gab-handle") === artist.handle) return;

    if (this.inView && !prefersReducedMotion()) {
      if (!this.transitioning) {
        this.runAnimatedChange();
      }
      return;
    }

    this.clearStates();
    this.root.classList.remove("is-transitioning");
    this.transitioning = false;
    this.applyContent(artist);
    if (window.GicleeArtistLayoutSync && !document.querySelector(".gacs-end-page-wrap")) {
      window.GicleeArtistLayoutSync.refreshScrollPanels();
    }
  };

  GicleeArtistBiography.prototype.runAnimatedChange = function () {
    var self = this;
    var artist = this.targetArtist;
    if (!artist || !artist.bioHtml) return;

    if (!this.inView || prefersReducedMotion()) {
      this.clearStates();
      this.applyContent(artist);
      this.transitioning = false;
      if (
        this.targetArtist &&
        this.root.getAttribute("data-gab-handle") !== this.targetArtist.handle
      ) {
        this.reconcileBioTarget();
      }
      if (window.GicleeArtistLayoutSync && !document.querySelector(".gacs-end-page-wrap")) {
        window.GicleeArtistLayoutSync.refreshScrollPanels();
      }
      return;
    }

    this.transitionSeq = (this.transitionSeq || 0) + 1;
    var seq = this.transitionSeq;
    this.transitioning = true;
    this.runExitThenEnter(seq);
  };

  GicleeArtistBiography.prototype.finishBioTransition = function () {
    var artist = this.targetArtist;
    if (
      artist &&
      artist.bioHtml &&
      this.root.getAttribute("data-gab-handle") !== artist.handle
    ) {
      this.transitionSeq = (this.transitionSeq || 0) + 1;
      this.transitioning = true;
      this.runExitThenEnter(this.transitionSeq);
      return;
    }

    this.clearTextEnterWait();
    this.pendingTextEnterSeq = null;
    this.root.classList.remove("is-transitioning");
    this.transitionPhase = "idle";
    this.transitioning = false;
    if (window.GicleeArtistLayoutSync && !document.querySelector(".gacs-end-page-wrap")) {
      window.GicleeArtistLayoutSync.refreshScrollPanels();
    }
  };

  GicleeArtistBiography.prototype.onAuthorChange = function (evt) {
    if (!evt || !evt.artist) return;
    if (!evt.artist.bioHtml) return;

    this.targetArtist = evt.artist;
    this.targetDirection = evt.direction >= 0 ? 1 : -1;

    if (
      this.root.getAttribute("data-gab-handle") === evt.artist.handle &&
      !this.transitioning
    ) {
      return;
    }

    /* Kolejne kliknięcie w trakcie animacji — aktualizuj cel; w fazie wejścia wróć do wyjścia */
    if (this.transitioning) {
      if (this.transitionPhase === "enter" || this.transitionPhase === "enter-fade") {
        this.transitionSeq = (this.transitionSeq || 0) + 1;
        this.runExitThenEnter(this.transitionSeq);
      }
      return;
    }

    this.runAnimatedChange();
  };

  GicleeArtistBiography.prototype.destroy = function () {
    this.clearTextEnterWait();
    this.pendingTextEnterSeq = null;
    if (this.unsub) this.unsub();
    if (this.io) this.io.disconnect();
    for (var i = scrollShiftRegistry.length - 1; i >= 0; i--) {
      if (scrollShiftRegistry[i].panel === this) {
        scrollShiftRegistry[i].destroy();
        scrollShiftRegistry.splice(i, 1);
      }
    }
  };

  function boot() {
    if (window.GicleeArtistLayoutSync && window.GicleeArtistLayoutSync.releaseBioSectionsIfIdle) {
      window.GicleeArtistLayoutSync.releaseBioSectionsIfIdle();
    }

    resolveBioPanels().forEach(function (panelConfig) {
      var root = panelConfig.root;
      var existing = null;
      for (var i = 0; i < panelRegistry.length; i++) {
        if (panelRegistry[i].root === root) {
          existing = panelRegistry[i];
          break;
        }
      }
      if (existing) {
        existing.bindState();
        return;
      }
      var instance = new GicleeArtistBiography(panelConfig);
      if (instance.bodyEl) {
        panelRegistry.push(instance);
        attachScrollShift(panelConfig, instance);
      }
    });

    initCollectionPageScrollChrome();
  }

  window.GicleeArtistBiographyBoot = boot;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  document.addEventListener("shopify:section:load", boot);
})();
