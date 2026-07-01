(function () {
  "use strict";

  /* Karuzela1 — zamrożona kopia oryginalnej karuzeli (bez dynamicznego tła). Nie modyfikuj. */

  function gicleeUi(key, fallback) {
    var bag = window.__gicleeI18n || {};
    return bag[key] || fallback;
  }

  function prefersReducedMotion() {
    return (
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    );
  }

  function isTouchLikeDevice() {
    return (
      (window.matchMedia &&
        window.matchMedia("(hover: none), (pointer: coarse), (max-width: 749px)").matches) ||
      ("ontouchstart" in window && navigator.maxTouchPoints > 0)
    );
  }

  function clamp(n, min, max) {
    return Math.max(min, Math.min(max, n));
  }

  function escapeHtml(str) {
    if (str == null) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function shopifyUrlRoot() {
    var root =
      (window.Shopify && window.Shopify.routes && window.Shopify.routes.root) || "/";
    if (root.length && root.charAt(root.length - 1) !== "/") root += "/";
    return root;
  }

  function productUrl(product) {
    if (!product) return "";
    if (product.handle) return shopifyUrlRoot() + "products/" + product.handle;
    return product.url || "";
  }

  function formatStorefrontPrice(variant) {
    if (!variant || variant.price == null) return "";
    var raw = parseFloat(variant.price);
    if (!isFinite(raw)) return "";
    return (
      raw.toLocaleString("pl-PL", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }) + " zł"
    );
  }

  var GACS_PRODUCT_CACHE = Object.create(null);

  function optimizeImageSrc(src, width) {
    if (!src) return "";
    width = width || 900;
    if (src.indexOf("width=") !== -1) return src;
    if (src.indexOf("cdn.shopify.com") === -1 && src.indexOf("/cdn/") === -1) return src;
    return src + (src.indexOf("?") === -1 ? "?" : "&") + "width=" + width;
  }

  var CAROUSEL_TITLE_PAREN_ALT_RE =
    /\s*\(\s*(?:lub|or|oder|ou|of|oppure|o)\b/i;
  var CAROUSEL_TITLE_BARE_ALT_RE =
    /\s+(?:lub|or|oder|ou|of|oppure|o)\s+/i;

  function shortCarouselTitle(title) {
    if (title == null) return "";
    var text = String(title).trim();
    var parenMatch = text.match(CAROUSEL_TITLE_PAREN_ALT_RE);
    if (parenMatch && parenMatch.index >= 0) {
      text = text.slice(0, parenMatch.index).trim();
    } else {
      var bareMatch = text.match(CAROUSEL_TITLE_BARE_ALT_RE);
      if (bareMatch && bareMatch.index > 0) {
        text = text.slice(0, bareMatch.index).trim();
      }
    }
    return text.replace(/\s*\(\s*$/, "").trim();
  }

  function navigateSlideLink(link) {
    if (!link || !link.href) return;
    var href = link.getAttribute("href");
    if (!href || href.charAt(0) === "#") return;
    window.location.assign(href);
  }

  function GicleeArtistShowcase(root) {
    this.root = root;
    this.layout = root.getAttribute("data-layout") || "coverflow";
    this.autoplay =
      root.getAttribute("data-autoplay") === "true" &&
      !prefersReducedMotion() &&
      !isTouchLikeDevice();
    this.autoplayMs = parseInt(root.getAttribute("data-autoplay-ms") || "7000", 10);
    this.viewport = root.querySelector(".giclee-artist-showcase__viewport");
    this.track = root.querySelector(".giclee-artist-showcase__track");
    this.slides = Array.prototype.slice.call(
      root.querySelectorAll(".giclee-artist-showcase__slide")
    );
    this.dotsWrap = root.querySelector(".giclee-artist-showcase__dots");
    this.prevBtn = root.querySelector(".giclee-artist-showcase__nav--prev");
    this.nextBtn = root.querySelector(".giclee-artist-showcase__nav--next");

    this.index = 0;
    this.count = this.slides.length;
    this.dragging = false;
    this.dragStartX = 0;
    this.dragStartY = 0;
    this.dragDelta = 0;
    this.dragAxis = null;
    this.gestureSwiped = false;
    this.autoplayTimer = null;
    this.paused = false;

    if (!this.count || !this.track) return;

    this.buildDots();
    this.bindEvents();
    this.goTo(0, false);
    if (this.layout === "coverflow") this.startAutoplay();
  }

  GicleeArtistShowcase.prototype.buildDots = function () {
    if (!this.dotsWrap || this.layout !== "coverflow") return;
    this.dotsWrap.innerHTML = "";
    for (var i = 0; i < this.count; i++) {
      var dot = document.createElement("button");
      dot.type = "button";
      dot.className = "giclee-artist-showcase__dot";
      dot.setAttribute("aria-label", gicleeUi("showcase_go_to_work", "Przejdź do dzieła {{ index }}").replace("{{ index }}", String(i + 1)));
      dot.dataset.index = String(i);
      this.dotsWrap.appendChild(dot);
    }
    this.dots = Array.prototype.slice.call(
      this.dotsWrap.querySelectorAll(".giclee-artist-showcase__dot")
    );
  };

  GicleeArtistShowcase.prototype.resolveLinkFromPoint = function (clientX, clientY) {
    var direct = document.elementFromPoint(clientX, clientY);
    var link = direct && direct.closest(".giclee-artist-showcase__slide-link");
    if (link) return link;

    for (var i = 0; i < this.slides.length; i++) {
      if (Math.abs(i - this.index) > 2) continue;
      var slide = this.slides[i];
      var rect = slide.getBoundingClientRect();
      if (
        clientX >= rect.left &&
        clientX <= rect.right &&
        clientY >= rect.top &&
        clientY <= rect.bottom
      ) {
        link = slide.querySelector(".giclee-artist-showcase__slide-link");
        if (link) return link;
      }
    }

    var active = this.slides[this.index];
    return active ? active.querySelector(".giclee-artist-showcase__slide-link") : null;
  };

  GicleeArtistShowcase.prototype.bindEvents = function () {
    var self = this;

    if (this.prevBtn) {
      this.prevBtn.addEventListener("click", function () {
        self.pauseAutoplay();
        self.prev();
      });
    }
    if (this.nextBtn) {
      this.nextBtn.addEventListener("click", function () {
        self.pauseAutoplay();
        self.next();
      });
    }

    if (this.dotsWrap) {
      this.dotsWrap.addEventListener("click", function (e) {
        var dot = e.target.closest(".giclee-artist-showcase__dot");
        if (!dot) return;
        self.pauseAutoplay();
        self.goTo(parseInt(dot.dataset.index, 10));
      });
    }

    this.slides.forEach(function (slide) {
      if (self.layout === "coverflow") {
        self.bindSlideHover(slide);
      }
    });

    if (this.viewport && this.layout === "coverflow") {
      function swipeThreshold(pointerType) {
        return pointerType === "touch" || isTouchLikeDevice() ? 28 : 48;
      }

      function resetGestureState(delayMs) {
        window.setTimeout(function () {
          self.dragDelta = 0;
          self.dragAxis = null;
          self.gestureSwiped = false;
        }, delayMs);
      }

      /* Only treat the gesture as a carousel swipe once the full threshold is met.
         A lower bar (previously 8px) blocked product links without changing slides. */
      function finishDrag(delta, pointerType) {
        var swiped = false;
        if (self.dragAxis === "x") {
          var threshold = swipeThreshold(pointerType);
          if (Math.abs(delta) > threshold) {
            swiped = true;
            if (delta < 0) self.next();
            else self.prev();
          }
        }
        self.gestureSwiped = swiped;
        resetGestureState(swiped ? 0 : 320);
        return swiped;
      }

      function followLinkAtPoint(clientX, clientY) {
        var link = self.resolveLinkFromPoint(clientX, clientY);
        navigateSlideLink(link);
      }

      this.viewport.addEventListener("click", function (e) {
        if (self.gestureSwiped) {
          e.preventDefault();
          return;
        }
        var link = e.target.closest(".giclee-artist-showcase__slide-link");
        if (!link) {
          link = self.resolveLinkFromPoint(e.clientX, e.clientY);
          if (link) {
            e.preventDefault();
            navigateSlideLink(link);
          }
        }
      });

      this.viewport.addEventListener("pointerdown", function (e) {
        if (e.button !== 0) return;
        if (e.target.closest(".giclee-artist-showcase__slide-link")) return;
        self.dragging = true;
        self.dragStartX = e.clientX;
        self.dragStartY = e.clientY;
        self.dragDelta = 0;
        self.dragAxis = null;
        self.gestureSwiped = false;
        self.viewport.classList.add("is-dragging");
        self.pauseAutoplay();
        if (e.pointerType !== "touch") {
          self.viewport.setPointerCapture(e.pointerId);
        }
      });

      this.viewport.addEventListener("keydown", function (e) {
        if (e.key === "ArrowLeft") {
          e.preventDefault();
          self.pauseAutoplay();
          self.prev();
        } else if (e.key === "ArrowRight") {
          e.preventDefault();
          self.pauseAutoplay();
          self.next();
        }
      });

      this.viewport.addEventListener("pointermove", function (e) {
        if (!self.dragging) return;
        var deltaX = e.clientX - self.dragStartX;
        var deltaY = e.clientY - self.dragStartY;
        var absX = Math.abs(deltaX);
        var absY = Math.abs(deltaY);
        self.dragDelta = deltaX;

        if (!self.dragAxis && (absX > 8 || absY > 8)) {
          if (absY > absX * 1.15) {
            self.dragging = false;
            self.dragAxis = null;
            self.dragDelta = 0;
            self.viewport.classList.remove("is-dragging");
            return;
          }
          if (absX > absY * 1.2) {
            self.dragAxis = "x";
          }
        }

        if (
          self.dragAxis === "x" &&
          absX >= swipeThreshold(e.pointerType) &&
          e.cancelable
        ) {
          e.preventDefault();
        }
      });

      this.viewport.addEventListener("pointerup", function (e) {
        if (!self.dragging) return;
        self.dragging = false;
        self.viewport.classList.remove("is-dragging");
        try {
          self.viewport.releasePointerCapture(e.pointerId);
        } catch (err) {}
        finishDrag(self.dragDelta, e.pointerType);
      });

      this.viewport.addEventListener("pointercancel", function () {
        self.dragging = false;
        self.viewport.classList.remove("is-dragging");
        self.dragDelta = 0;
        self.dragAxis = null;
        self.gestureSwiped = false;
      });

      this.viewport.addEventListener(
        "touchstart",
        function (e) {
          if (!e.touches || e.touches.length !== 1) return;
          if (e.target.closest(".giclee-artist-showcase__slide-link")) return;
          self.dragging = true;
          self.dragStartX = e.touches[0].clientX;
          self.dragStartY = e.touches[0].clientY;
          self.dragDelta = 0;
          self.dragAxis = null;
          self.gestureSwiped = false;
          self.viewport.classList.add("is-dragging");
          self.pauseAutoplay();
        },
        { passive: true }
      );

      this.viewport.addEventListener(
        "touchmove",
        function (e) {
          if (!self.dragging || !e.touches || e.touches.length !== 1) return;
          var deltaX = e.touches[0].clientX - self.dragStartX;
          var deltaY = e.touches[0].clientY - self.dragStartY;
          var absX = Math.abs(deltaX);
          var absY = Math.abs(deltaY);
          self.dragDelta = deltaX;

          if (!self.dragAxis && (absX > 8 || absY > 8)) {
            if (absY > absX * 1.15) {
              self.dragging = false;
              self.dragAxis = null;
              self.dragDelta = 0;
              self.viewport.classList.remove("is-dragging");
              return;
            }
            if (absX > absY * 1.2) {
              self.dragAxis = "x";
            }
          }

          if (self.dragAxis === "x" && absX >= swipeThreshold("touch") && e.cancelable) {
            e.preventDefault();
          }
        },
        { passive: false }
      );

      this.viewport.addEventListener("touchend", function (e) {
        if (!self.dragging) return;
        self.dragging = false;
        self.viewport.classList.remove("is-dragging");
        var swiped = finishDrag(self.dragDelta, "touch");
        if (!swiped && e.changedTouches && e.changedTouches[0]) {
          var touch = e.changedTouches[0];
          window.requestAnimationFrame(function () {
            followLinkAtPoint(touch.clientX, touch.clientY);
          });
        }
      });

      this.viewport.addEventListener("touchcancel", function () {
        self.dragging = false;
        self.viewport.classList.remove("is-dragging");
        self.dragDelta = 0;
        self.dragAxis = null;
        self.gestureSwiped = false;
      });
    }

    this.root.addEventListener("mouseenter", function () {
      self.pauseAutoplay();
    });
    this.root.addEventListener("mouseleave", function () {
      if (!self.paused) self.startAutoplay();
    });
    this.root.addEventListener("focusin", function () {
      self.pauseAutoplay();
    });
    this.root.addEventListener("focusout", function (e) {
      if (self.root.contains(e.relatedTarget)) return;
      if (!self.paused) self.startAutoplay();
    });

    window.addEventListener(
      "resize",
      function () {
        if (self.layout === "coverflow") self.layoutSlides();
      },
      { passive: true }
    );
  };

  GicleeArtistShowcase.prototype.bindSlideHover = function (slide) {
    var self = this;
    slide.onmousemove = function (e) {
      if (!slide.classList.contains("is-active") || prefersReducedMotion()) return;
      self.tiltSlide(slide, e);
    };
    slide.onmouseleave = function () {
      self.resetTilt(slide);
    };
  };

  GicleeArtistShowcase.prototype.tiltSlide = function (slide, e) {
    var card = slide.querySelector(".giclee-artist-showcase__slide-card");
    if (!card) return;
    var rect = card.getBoundingClientRect();
    var px = (e.clientX - rect.left) / rect.width - 0.5;
    var py = (e.clientY - rect.top) / rect.height - 0.5;
    var rotateY = px * 6;
    var rotateX = py * -4;
    card.style.transform =
      "rotateX(" + rotateX + "deg) rotateY(" + rotateY + "deg) translateY(-4px)";
  };

  GicleeArtistShowcase.prototype.resetTilt = function (slide) {
    var card = slide.querySelector(".giclee-artist-showcase__slide-card");
    if (card) card.style.transform = "";
  };

  GicleeArtistShowcase.prototype.layoutSlides = function () {
    if (this.layout !== "coverflow") return;
    var self = this;
    var isEndPage = this.root.classList.contains("gacs-end-page");
    /* Bufor animacji wejścia/wyjścia karty (offset 4); end_page: dalsze slajdy
       display:none — 3D bbox nie rozpycha scrollHeight na dole strony. */
    var layoutMax = 4;
    this.slides.forEach(function (slide, i) {
      var offset = i - self.index;
      var abs = Math.abs(offset);

      if (isEndPage && abs > layoutMax) {
        slide.classList.toggle("is-active", false);
        slide.style.display = "none";
        slide.style.pointerEvents = "none";
        slide.style.transform = "";
        slide.style.opacity = "0";
        self.resetTilt(slide);
        return;
      }

      var layoutOff = clamp(offset, -layoutMax, layoutMax);
      var layoutAbs = Math.abs(layoutOff);

      var x = layoutOff * clamp(window.innerWidth * 0.14, 88, 148);
      var rotateY = layoutOff * -32;
      var z = -layoutAbs * 90;
      var scale = 1 - layoutAbs * 0.1;
      var opacity = abs > 3 ? 0 : 1 - abs * 0.22;

      slide.style.display = "";
      slide.classList.toggle("is-active", offset === 0);
      slide.style.zIndex = String(100 - Math.min(abs, layoutMax));
      slide.style.opacity = String(opacity);
      slide.style.visibility = abs > layoutMax ? "hidden" : "visible";
      slide.style.pointerEvents = abs > 2 ? "none" : "auto";
      slide.style.transform =
        "translateX(" +
        x +
        "px) translateZ(" +
        z +
        "px) rotateY(" +
        rotateY +
        "deg) scale(" +
        scale +
        ")";
    });

    if (this.dots) {
      this.dots.forEach(function (dot, i) {
        dot.classList.toggle("is-active", i === self.index);
        dot.setAttribute("aria-current", i === self.index ? "true" : "false");
      });
    }

    if (this.prevBtn) this.prevBtn.disabled = this.index <= 0;
    if (this.nextBtn) this.nextBtn.disabled = this.index >= this.count - 1;

    var panel = this.root.closest("[data-gacs-scroll-panel]");
    if (
      panel &&
      !panel.classList.contains("gacs-panel-scroll--static") &&
      window.GicleeArtistLayoutSync
    ) {
      window.GicleeArtistLayoutSync.refreshScrollPanels();
    }
  };

  GicleeArtistShowcase.prototype.goTo = function (i) {
    this.index = clamp(i, 0, this.count - 1);
    if (this.layout === "coverflow") {
      this.layoutSlides();
    } else {
      this.slides.forEach(function (slide, idx) {
        slide.classList.toggle("is-active", idx === this.index);
      }, this);
    }
    if (this.viewport) {
      this.viewport.setAttribute(
        "aria-label",
        gicleeUi("showcase_gallery_position", "Galeria dzieł, pozycja {{ current }} z {{ total }}")
          .replace("{{ current }}", String(this.index + 1))
          .replace("{{ total }}", String(this.count))
      );
    }
  };

  GicleeArtistShowcase.prototype.prev = function () {
    this.goTo(this.index - 1);
  };

  GicleeArtistShowcase.prototype.next = function () {
    this.goTo(this.index + 1);
  };

  GicleeArtistShowcase.prototype.startAutoplay = function () {
    var self = this;
    if (!this.autoplay || this.layout !== "coverflow" || this.count < 2) return;
    this.stopAutoplay();
    this.autoplayTimer = window.setInterval(function () {
      if (self.index >= self.count - 1) self.goTo(0);
      else self.next();
    }, this.autoplayMs);
  };

  GicleeArtistShowcase.prototype.stopAutoplay = function () {
    if (this.autoplayTimer) {
      clearInterval(this.autoplayTimer);
      this.autoplayTimer = null;
    }
  };

  GicleeArtistShowcase.prototype.pauseAutoplay = function () {
    this.paused = true;
    this.stopAutoplay();
  };

  GicleeArtistShowcase.prototype.reinit = function () {
    this.stopAutoplay();
    this.slides = Array.prototype.slice.call(
      this.root.querySelectorAll(".giclee-artist-showcase__slide")
    );
    this.count = this.slides.length;
    this.index = 0;
    this.dragging = false;
    this.dragDelta = 0;
    this.gestureSwiped = false;
    var self = this;
    this.slides.forEach(function (slide) {
      if (self.layout === "coverflow") self.bindSlideHover(slide);
    });
    this.buildDots();
    this.goTo(0);
    if (this.layout === "coverflow") {
      var self = this;
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          self.layoutSlides();
        });
      });
    }
    if (this.layout === "coverflow" && !this.paused) this.startAutoplay();
  };

  var GACS_EXHIBITION_EASE = "cubic-bezier(0.22, 1, 0.36, 1)";
  var GACS_EXHIBITION_MS = 880;

  function dispatchArtistShowcaseEnter(root, artist, index) {
    if (!root || !artist || !artist.handle) return;
    root._gacsLastShowcaseEnter = {
      handle: artist.handle,
      index: index,
      time: Date.now(),
    };
    try {
      root.dispatchEvent(
        new CustomEvent("giclee:artist-showcase-enter", {
          bubbles: true,
          detail: {
            handle: artist.handle,
            index: index,
          },
        })
      );
    } catch (_err) {}
  }

  function notifyScrollPanels() {
    document.querySelectorAll("[data-gacs-scroll-panel]").forEach(function (el) {
      var panel = el._gacsScrollPanelInstance;
      if (panel && typeof panel.update === "function") {
        panel.update();
      }
    });
  }

  function isGalleryViewportLocked() {
    return !!document.querySelector("[data-gacs-scroll-panel].is-overlapping");
  }

  function lockSectionLayout(section) {
    if (!section || section.dataset.gacsLayoutLocked === "1") return;
    if (
      section.matches &&
      (section.matches("[data-giclee-artist-bio]") ||
        section.matches(".giclee-artist-biography-section, .giclee-artist-biography-section *"))
    ) {
      return;
    }
    if (section.closest && section.closest("[data-giclee-artist-bio], .giclee-artist-biography-section")) {
      return;
    }
    section.style.height = section.offsetHeight + "px";
    section.style.overflow = "hidden";
    section.dataset.gacsLayoutLocked = "1";
  }

  function releaseSectionLayout(section) {
    if (!section) return;
    if (section.dataset.gacsLayoutLocked !== "1") return;
    if (isGalleryViewportLocked()) return;
    section.style.height = "";
    section.style.overflow = "";
    delete section.dataset.gacsLayoutLocked;
    notifyScrollPanels();
  }

  function releaseBioLayoutLocks(root) {
    var el = root;
    while (el) {
      if (el.dataset && el.dataset.gacsLayoutLocked === "1") {
        el.style.height = "";
        el.style.overflow = "";
        delete el.dataset.gacsLayoutLocked;
      }
      if (
        el.classList &&
        (el.classList.contains("giclee-artist-biography-section") ||
          el.classList.contains("shopify-section"))
      ) {
        break;
      }
      el = el.parentElement;
    }
    notifyScrollPanels();
  }

  window.GicleeArtistLayoutSync = {
    lockSectionLayout: lockSectionLayout,
    releaseSectionLayout: releaseSectionLayout,
    releaseBioLayoutLocks: releaseBioLayoutLocks,
    releaseBioSectionsIfIdle: function () {
      document.querySelectorAll("[data-gacs-layout-locked='1']").forEach(function (el) {
        releaseSectionLayout(el);
      });
    },
    refreshScrollPanels: notifyScrollPanels,
    isGalleryViewportLocked: isGalleryViewportLocked,
  };

  function GicleeArtistExhibition(root) {
    this.root = root;
    this.jsonEl = root.querySelector("[data-gacs-artists-json]");
    this.track = root.querySelector("[data-gacs-track]");
    this.contentPanes = Array.prototype.slice.call(
      root.querySelectorAll("[data-gacs-exhibition-content]")
    );
    this.prevNav = root.querySelector('[data-gacs-artist-nav="prev"]');
    this.nextNav = root.querySelector('[data-gacs-artist-nav="next"]');
    this.showCta = root.getAttribute("data-show-cta") === "true";
    this.ctaLabel = root.getAttribute("data-cta-label") || gicleeUi("showcase_cta_default", "Zobacz całą kolekcję");
    this.fixedLead = root.getAttribute("data-gacs-fixed-lead") || "";
    this.artists = [];
    this.currentIndex = parseInt(root.getAttribute("data-artist-index") || "0", 10);
    this.targetArtistIndex = this.currentIndex;
    this.targetDirection = 1;
    this.productFetchSeq = 0;
    this.transitioning = false;
    this.transitionSeq = 0;
    this.transitionPhase = "idle";
    this.showcase = root._gacsShowcase || null;
    this.state = window.GicleeActiveAuthor;
    this.unsub = null;

    if (!this.jsonEl || !this.track) return;

    try {
      this.artists = JSON.parse(this.jsonEl.textContent || "[]");
    } catch (err) {
      this.artists = [];
    }

    if (this.artists.length < 2) return;

    if (this.state) {
      this.state.init(this.artists, this.currentIndex);
      this.unsub = this.state.subscribe(this.onActiveAuthorChange.bind(this));
    }

    this.updateNavLabels();
    this.bindNav();

    var bootArtist = this.getArtist(this.currentIndex);
    if (bootArtist) {
      var self = this;
      if (bootArtist.products && bootArtist.products.length > 0) {
        if (self.showcase) {
          self.showcase.reinit();
        }
      } else {
        this.refreshArtistProducts(bootArtist, function (products) {
          self.track.innerHTML = self.buildTrackHtml(products);
          if (self.showcase) {
            self.showcase.reinit();
          } else {
            self._pendingBootProducts = products;
          }
        });
      }
    }
  }

  GicleeArtistExhibition.prototype.waitPaneTransition = function (callback) {
    var panes = this.contentPanes;
    if (!panes.length || prefersReducedMotion()) {
      callback();
      return;
    }

    var finished = false;
    var done = function () {
      if (finished) return;
      finished = true;
      panes.forEach(function (pane) {
        pane.removeEventListener("transitionend", onEnd);
      });
      callback();
    };
    var onEnd = function (e) {
      if (panes.indexOf(e.target) === -1) return;
      if (e.propertyName !== "opacity" && e.propertyName !== "transform") return;
      done();
    };

    panes.forEach(function (pane) {
      pane.addEventListener("transitionend", onEnd);
    });
    window.setTimeout(done, GACS_EXHIBITION_MS + 120);
  };

  GicleeArtistExhibition.prototype.clearExhibitionStates = function () {
    this.root.classList.remove(
      "is-artist-transitioning",
      "is-artist-exiting-next",
      "is-artist-exiting-prev",
      "is-artist-entering-next",
      "is-artist-entering-prev"
    );
    this.transitionPhase = "idle";
  };

  GicleeArtistExhibition.prototype.setExitPhase = function () {
    var dir = this.targetDirection;
    this.transitionPhase = "exit";
    this.root.classList.remove("is-artist-entering-next", "is-artist-entering-prev");
    this.root.classList.add("is-artist-transitioning");
    this.root.classList.remove("is-artist-exiting-next", "is-artist-exiting-prev");
    this.root.classList.add(
      dir > 0 ? "is-artist-exiting-next" : "is-artist-exiting-prev"
    );
  };

  GicleeArtistExhibition.prototype.swapAndEnter = function (seq, pushState) {
    var self = this;
    var activeIndex = self.getTargetArtistIndex();
    var artist = self.getArtist(activeIndex);
    if (!artist) {
      self.clearExhibitionStates();
      self.transitioning = false;
      return;
    }

    var enterDir = self.targetDirection;
    self.currentIndex = activeIndex;
    self.applyArtist(artist);
    self.updateNavLabels();
    self.root.setAttribute("data-artist-index", String(activeIndex));
    dispatchArtistShowcaseEnter(self.root, artist, activeIndex);
    self.transitionPhase = "enter";
    self.root.classList.add(
      enterDir > 0 ? "is-artist-entering-next" : "is-artist-entering-prev"
    );
    self.root.classList.remove("is-artist-exiting-next", "is-artist-exiting-prev");

    void self.root.offsetHeight;

    window.requestAnimationFrame(function () {
      window.requestAnimationFrame(function () {
        if (seq !== self.transitionSeq) return;
        self.root.classList.remove(
          "is-artist-entering-next",
          "is-artist-entering-prev",
          "is-artist-transitioning"
        );
        self.transitionPhase = "enter-fade";
        self.waitPaneTransition(function () {
          if (seq !== self.transitionSeq) return;
          self.finishArtistTransition();
        });
      });
    });

    if (pushState && artist.url) {
      history.pushState({ gacsArtist: activeIndex }, "", artist.url);
    }
  };

  GicleeArtistExhibition.prototype.runExitThenEnter = function (seq, pushState) {
    var self = this;
    if (self.showcase) self.showcase.pauseAutoplay();
    self.setExitPhase();
    self.waitPaneTransition(function () {
      if (seq !== self.transitionSeq) return;
      self.swapAndEnter(seq, pushState);
    });
  };

  GicleeArtistExhibition.prototype.getArtist = function (index) {
    return this.artists[index] || null;
  };

  GicleeArtistExhibition.prototype.getTargetArtistIndex = function () {
    return this.targetArtistIndex != null ? this.targetArtistIndex : this.currentIndex;
  };

  GicleeArtistExhibition.prototype.isArtistFetchStale = function (artist) {
    if (!artist || !artist.handle) return true;
    var target = this.getArtist(this.getTargetArtistIndex());
    return !target || target.handle !== artist.handle;
  };

  GicleeArtistExhibition.prototype.reconcileArtistTarget = function () {
    var index = this.getTargetArtistIndex();
    if (index < 0 || index >= this.artists.length) return;
    if (index === this.currentIndex) return;

    if (!prefersReducedMotion()) {
      if (!this.transitioning) {
        this.runArtistTransition(false);
      }
      return;
    }

    this.clearExhibitionStates();
    this.root.classList.remove("is-artist-transitioning");
    this.transitioning = false;
    this.currentIndex = index;
    this.applyArtist(this.getArtist(index));
    this.updateNavLabels();
    this.root.setAttribute("data-artist-index", String(index));
    if (this.showcase && !this.showcase.paused) {
      this.showcase.startAutoplay();
    }

    if (this.getTargetArtistIndex() !== this.currentIndex) {
      this.reconcileArtistTarget();
    }
  };

  GicleeArtistExhibition.prototype.finishArtistTransition = function () {
    if (this.getTargetArtistIndex() !== this.currentIndex) {
      this.transitionSeq = (this.transitionSeq || 0) + 1;
      this.transitioning = true;
      this.runExitThenEnter(this.transitionSeq, false);
      return;
    }

    this.root.classList.remove("is-artist-transitioning");
    this.transitionPhase = "idle";
    this.transitioning = false;
    if (this.showcase && !this.showcase.paused) {
      this.showcase.startAutoplay();
    }
  };

  GicleeArtistExhibition.prototype.onActiveAuthorChange = function (evt) {
    if (!evt || evt.index == null) return;
    this.updateNavLabels(evt.index);
    this.animateToArtist(evt.index, evt.direction, false);
  };

  GicleeArtistExhibition.prototype.updateNavLabels = function (indexOverride) {
    var idx =
      indexOverride != null
        ? indexOverride
        : this.state
          ? this.state.index
          : this.currentIndex;
    var prev = this.getArtist(idx - 1);
    var next = this.getArtist(idx + 1);

    this.setNavButton(this.prevNav, prev);
    this.setNavButton(this.nextNav, next);
  };

  GicleeArtistExhibition.prototype.setNavButton = function (btn, artist) {
    if (!btn) return;
    var nameEl = btn.querySelector("[data-gacs-artist-nav-name]");
    var previewEl = btn.querySelector("[data-gacs-artist-nav-preview]");

    if (!artist) {
      btn.hidden = true;
      btn.disabled = true;
      return;
    }

    btn.hidden = false;
    btn.disabled = false;
    if (nameEl) nameEl.textContent = artist.artistName || artist.heading || "";
    if (previewEl) {
      if (artist.previewImage) {
        previewEl.innerHTML =
          '<img src="' +
          escapeHtml(artist.previewImage) +
          '" alt="" loading="lazy" decoding="async">';
      } else {
        previewEl.innerHTML = "";
      }
    }
  };

  GicleeArtistExhibition.prototype.bindNav = function () {
    var self = this;
    if (this.prevNav) {
      this.prevNav.addEventListener("click", function () {
        if (self.state) {
          self.state.setIndex(self.state.index - 1, {
            direction: -1,
            pushState: true,
            source: "gallery-nav",
          });
        } else {
          self.animateToArtist(self.currentIndex - 1, -1, true);
        }
      });
    }
    if (this.nextNav) {
      this.nextNav.addEventListener("click", function () {
        if (self.state) {
          self.state.setIndex(self.state.index + 1, {
            direction: 1,
            pushState: true,
            source: "gallery-nav",
          });
        } else {
          self.animateToArtist(self.currentIndex + 1, 1, true);
        }
      });
    }
  };

  GicleeArtistExhibition.prototype.refreshArtistProducts = function (artist, callback, opts) {
    var self = this;
    opts = opts || {};
    var limit = parseInt(self.root.getAttribute("data-max-products") || "50", 10);
    if (!artist || !artist.handle) {
      callback(artist ? artist.products : []);
      return;
    }

    if (!opts.force && artist.products && artist.products.length > 0) {
      GACS_PRODUCT_CACHE[artist.handle] = artist.products;
      callback(artist.products);
      return;
    }

    if (!opts.force && GACS_PRODUCT_CACHE[artist.handle]) {
      artist.products = GACS_PRODUCT_CACHE[artist.handle];
      callback(artist.products);
      return;
    }

    var url =
      shopifyUrlRoot() +
      "collections/" +
      encodeURIComponent(artist.handle) +
      "/products.json?limit=" +
      limit;

    var fetchSeq = ++self.productFetchSeq;

    fetch(url)
      .then(function (res) {
        if (!res.ok) throw new Error("products.json");
        return res.json();
      })
      .then(function (data) {
        if (fetchSeq !== self.productFetchSeq || self.isArtistFetchStale(artist)) return;
        var stale = artist.products || [];
        var products = (data.products || []).map(function (p, index) {
          var staleMatch =
            stale.find(function (s) {
              return s.handle && s.handle === p.handle;
            }) || stale[index] || {};
          var variant = p.variants && p.variants[0];
          var imageSrc =
            (p.images && p.images[0] && p.images[0].src) || staleMatch.imageSrc || "";
          return {
            title: p.title,
            handle: p.handle,
            url: shopifyUrlRoot() + "products/" + p.handle,
            priceFormatted:
              staleMatch.priceFormatted || formatStorefrontPrice(variant),
            imageSrc: imageSrc,
            imageAlt: p.title,
            createdDate: staleMatch.createdDate || "",
            technique: staleMatch.technique || "",
            genre: staleMatch.genre || "",
          };
        });
        artist.products = products;
        GACS_PRODUCT_CACHE[artist.handle] = products;
        callback(products);
      })
      .catch(function () {
        if (fetchSeq !== self.productFetchSeq || self.isArtistFetchStale(artist)) return;
        callback(artist.products || GACS_PRODUCT_CACHE[artist.handle] || []);
      });
  };

  GicleeArtistExhibition.prototype.buildTrackHtml = function (products) {
    if (!products || !products.length) {
      return (
        '<article class="giclee-artist-showcase__slide is-active" data-index="0">' +
        '<div class="giclee-artist-showcase__slide-card">' +
        '<div class="giclee-artist-showcase__slide-meta">' +
        '<h3 class="giclee-artist-showcase__slide-title">' + gicleeUi("showcase_no_works", "Brak dzieł") + "</h3>" +
        "</div></div></article>"
      );
    }

    return products
      .map(function (product, index) {
        var slideTitle = shortCarouselTitle(product.title);
        var imgSrc = optimizeImageSrc(product.imageSrc, 900);
        var created = product.createdDate || "";
        var technique = product.technique || "";
        var genre = product.genre || "";
        var media = imgSrc
          ? '<img src="' +
            escapeHtml(imgSrc) +
            '" alt="' +
            escapeHtml(product.imageAlt || slideTitle) +
            '" loading="' +
            (index === 0 ? "eager" : "lazy") +
            '" decoding="async"' +
            (index === 0 ? ' fetchpriority="high"' : "") +
            ">"
          : "";
        return (
          '<article class="giclee-artist-showcase__slide' +
          (index === 0 ? " is-active" : "") +
          '" data-index="' +
          index +
          '"' +
          (created ? ' data-gacs-created="' + escapeHtml(created) + '"' : "") +
          (technique ? ' data-gacs-technique="' + escapeHtml(technique) + '"' : "") +
          (genre ? ' data-gacs-genre="' + escapeHtml(genre) + '"' : "") +
          ">" +
          '<a class="giclee-artist-showcase__slide-link" href="' +
          escapeHtml(productUrl(product)) +
          '" aria-label="Zobacz: ' +
          escapeHtml(slideTitle) +
          '">' +
          '<div class="giclee-artist-showcase__slide-card">' +
          '<div class="giclee-artist-showcase__slide-media">' +
          media +
          "</div>" +
          '<div class="giclee-artist-showcase__slide-meta">' +
          '<h3 class="giclee-artist-showcase__slide-title">' +
          escapeHtml(slideTitle) +
          "</h3>" +
          "</div></div></a></article>"
        );
      })
      .join("");
  };

  GicleeArtistExhibition.prototype.updateHeader = function (artist) {
    var eyebrow = this.root.querySelector('[data-gacs-field="eyebrow"]');
    var heading = this.root.querySelector('[data-gacs-field="heading"]');
    var lead = this.root.querySelector('[data-gacs-field="lead"]');
    var cta = this.root.querySelector('[data-gacs-field="cta"]');

    if (eyebrow) eyebrow.textContent = artist.artistName || artist.eyebrow || "";
    if (heading) heading.textContent = artist.heading || "";
    if (lead) lead.textContent = this.fixedLead || artist.lead || "";
    if (cta) {
      if (this.showCta && artist.url) {
        cta.hidden = false;
        cta.textContent = this.ctaLabel;
        cta.href = artist.url;
      } else {
        cta.hidden = true;
      }
    }

    this.root.setAttribute("aria-label", artist.artistName || artist.heading || "");
  };

  GicleeArtistExhibition.prototype.applyArtist = function (artist) {
    if (!artist) return;
    var self = this;
    this.updateHeader(artist);

    function renderProducts(products) {
      self.track.innerHTML = self.buildTrackHtml(products);
      if (self.showcase) self.showcase.reinit();
      if (window.GicleeArtistLayoutSync) {
        window.GicleeArtistLayoutSync.refreshScrollPanels();
      }
    }

    if (artist.products && artist.products.length > 0) {
      renderProducts(artist.products);
      return;
    }

    this.refreshArtistProducts(artist, renderProducts);
  };

  GicleeArtistExhibition.prototype.runArtistTransition = function (pushState) {
    var self = this;
    var targetIndex = this.getTargetArtistIndex();
    if (targetIndex < 0 || targetIndex >= this.artists.length) return;

    if (prefersReducedMotion()) {
      this.currentIndex = targetIndex;
      this.applyArtist(this.getArtist(targetIndex));
      this.updateNavLabels();
      this.root.setAttribute("data-artist-index", String(targetIndex));
      if (this.getTargetArtistIndex() !== this.currentIndex) {
        this.reconcileArtistTarget();
        return;
      }
      if (pushState) {
        var reducedArtist = this.getArtist(targetIndex);
        if (reducedArtist && reducedArtist.url) {
          history.pushState({ gacsArtist: targetIndex }, "", reducedArtist.url);
        }
      }
      return;
    }

    this.transitionSeq = (this.transitionSeq || 0) + 1;
    var seq = this.transitionSeq;
    this.transitioning = true;
    this.runExitThenEnter(seq, pushState);
  };

  GicleeArtistExhibition.prototype.animateToArtist = function (index, direction, pushState) {
    if (index < 0 || index >= this.artists.length) return;

    this.targetArtistIndex = index;
    this.targetDirection = direction >= 0 ? 1 : -1;

    if (index === this.currentIndex && !this.transitioning) return;

    if (this.transitioning) {
      if (this.transitionPhase === "enter" || this.transitionPhase === "enter-fade") {
        this.transitionSeq = (this.transitionSeq || 0) + 1;
        this.runExitThenEnter(this.transitionSeq, false);
      }
      return;
    }

    this.runArtistTransition(pushState);
  };

  GicleeArtistExhibition.prototype.attachShowcase = function (showcase) {
    this.showcase = showcase;
    this.root._gacsShowcase = showcase;
    if (this._pendingBootProducts) {
      this.track.innerHTML = this.buildTrackHtml(this._pendingBootProducts);
      showcase.reinit();
      this._pendingBootProducts = null;
    }
  };

  function GicleeArtistScrollPanel(root) {
    this.root = root;
    this.sticky = root.querySelector(".gacs-panel-scroll__sticky");
    this.surface = root.querySelector(".gacs-panel-scroll__surface");
    this.sentinel = root.querySelector(".gacs-panel-scroll__sentinel");
    this.sectionEl = root.closest(".shopify-section");
    this.prevSection = this.findPrevOverlapSection();
    this.gap = 80;
    this.overlap = 120;
    this.restSentinelTop = 0;
    this.ticking = false;

    if (!this.sticky || !this.surface || !this.sentinel) return;

    this.root._gacsScrollPanelInstance = this;

    if (isTouchLikeDevice()) {
      root.classList.add("gacs-panel-scroll--static");
      root.setAttribute("data-gacs-touch-static", "true");
      this.clearScrollState();
      return;
    }

    if (prefersReducedMotion()) {
      root.classList.add("gacs-panel-scroll--static");
      this.clearScrollState();
      return;
    }

    this.measure();
    this.restSentinelTop = this.sentinel.getBoundingClientRect().top;
    this.bind();
    this.update();
  }

  GicleeArtistScrollPanel.prototype.isStatic = function () {
    return this.root.classList.contains("gacs-panel-scroll--static");
  };

  GicleeArtistScrollPanel.prototype.clearScrollState = function () {
    this.root.classList.remove("is-pinned-top", "is-overlapping");
    this.root.style.removeProperty("--gacs-progress");
    this.root.style.removeProperty("--gacs-translate-y");
    this.root.style.removeProperty("--gacs-layout-trim");
    this.root.style.removeProperty("--gacs-veil-alpha");
    this.root.style.removeProperty("--gacs-shadow-alpha");
    this.root.style.removeProperty("--gacs-shadow-blur");
    this.root.style.height = "";
    this.root.style.marginBottom = "";
    this._endPageBleedTrim = 0;
    this.root.style.overflow = "";
    this.root.style.boxSizing = "";
    if (this.sticky) this.sticky.style.marginBottom = "";
    if (this.surface) {
      this.surface.style.transform = "";
      this.surface.style.marginBottom = "";
    }
    if (this.sectionEl) {
      this.sectionEl.classList.remove("gacs-section-over-chrome");
      this.sectionEl.style.removeProperty("--gacs-layout-trim");
    }
    if (this.prevSection) {
      this.prevSection.classList.remove("gacs-under-panel");
      this.prevSection.style.removeProperty("--gacs-under-dim");
    }
    if (window.GicleeArtistLayoutSync) {
      window.GicleeArtistLayoutSync.releaseBioSectionsIfIdle();
    }
  };

  GicleeArtistScrollPanel.prototype.findPrevOverlapSection = function () {
    if (!this.sectionEl) return null;

    var el = this.sectionEl.previousElementSibling;
    var fallback = null;

    while (el) {
      if (!el.classList || !el.classList.contains("shopify-section")) {
        el = el.previousElementSibling;
        continue;
      }

      if (el.classList.contains("giclee-artist-biography-section")) {
        return el;
      }

      if (el.querySelector('[data-testid^="divider-"], .divider')) {
        el = el.previousElementSibling;
        continue;
      }

      if (!fallback) fallback = el;
      el = el.previousElementSibling;
    }

    return fallback;
  };

  GicleeArtistScrollPanel.prototype.readCssLength = function (varName) {
    var styles = getComputedStyle(this.root);
    var parsed = parseFloat(styles.getPropertyValue(varName));
    if (Number.isFinite(parsed) && parsed > 0) return parsed;

    var prevPaddingBottom = this.root.style.paddingBottom;
    this.root.style.paddingBottom = "var(" + varName + ")";
    parsed = parseFloat(getComputedStyle(this.root).paddingBottom);
    this.root.style.paddingBottom = prevPaddingBottom;
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
  };

  GicleeArtistScrollPanel.prototype.measure = function () {
    this.gap = this.readCssLength("--gacs-gap") || 80;
    this.overlap = this.readCssLength("--gacs-overlap") || 120;
  };

  GicleeArtistScrollPanel.prototype.syncPanelHeight = function (progress) {
    var showcase = this.root.querySelector(".giclee-artist-showcase");
    if (!showcase || progress <= 0.001) {
      this.root.style.height = "";
      this.root.style.marginBottom = "";
      this.root.style.overflow = "";
      this.root.style.boxSizing = "";
      return;
    }

    var targetHeight;
    var pinned = this.sticky && this.sticky.getBoundingClientRect().top <= 1;
    if (this.root.classList.contains("gacs-end-page-wrap")) {
      var panelTop = this.root.getBoundingClientRect().top;
      var inner = showcase.querySelector(".giclee-artist-showcase__inner");
      var dots = showcase.querySelector(".giclee-artist-showcase__dots");
      var viewport = showcase.querySelector(".giclee-artist-showcase__viewport");
      var stage = showcase.querySelector(".giclee-artist-showcase__stage");
      var contentEnd = inner || dots || viewport || stage || showcase;
      var contentBottom = contentEnd.getBoundingClientRect().bottom;
      /*
       * end_page: po przypięciu kończymy panel na realnej treści (bez +32px fudge —
       * to był „duchowy” scroll na dole). W trakcie overlapu zostawiamy lekki bufor.
       */
      if (pinned) {
        targetHeight = contentBottom - panelTop;
      } else {
        targetHeight = contentBottom - panelTop + 32 - this.overlap * progress;
      }
    } else if (showcase.classList.contains("gacs-fullscreen")) {
      targetHeight = this.gap + showcase.offsetHeight - this.overlap * progress;
    } else {
      var panelTop = this.root.getBoundingClientRect().top;
      var showcaseBottom = showcase.getBoundingClientRect().bottom;
      targetHeight = showcaseBottom - panelTop;
    }

    if (targetHeight > 0) {
      this.root.style.height = targetHeight.toFixed(2) + "px";
      this.root.style.overflow = "visible";
      this.root.style.marginBottom = "";
      this.root.style.boxSizing = "border-box";
    }
  };

  GicleeArtistScrollPanel.prototype.trimEndPageScrollBleed = function (pinned) {
    if (!this.root.classList.contains("gacs-end-page-wrap")) return;

    if (!pinned) {
      this._endPageBleedTrim = 0;
      return;
    }

    var showcase = this.root.querySelector(".giclee-artist-showcase");
    if (!showcase) return;

    var inner = showcase.querySelector(".giclee-artist-showcase__inner") || showcase;
    var contentBottom = inner.getBoundingClientRect().bottom;
    var scrollY = window.scrollY || document.documentElement.scrollTop;
    var docHeight = document.documentElement.scrollHeight;
    var viewH = window.innerHeight;
    var scrollRoom = docHeight - scrollY - viewH;

    /*
     * Przycinaj tylko gdy treść galerii już mieści się w viewport (widać pusty pas
     * pod kropkami), a dokument nadal ma „duchowy” zapas scrollHeight.
     */
    if (scrollRoom < 6 || contentBottom > viewH - 12) {
      if (this._endPageBleedTrim) {
        this.root.style.marginBottom = "";
        this._endPageBleedTrim = 0;
      }
      return;
    }

    var trim = Math.ceil(scrollRoom);
    if (trim !== this._endPageBleedTrim) {
      this.root.style.marginBottom = -trim + "px";
      this._endPageBleedTrim = trim;
    }
  };

  GicleeArtistScrollPanel.prototype.update = function () {
    if (this.isStatic()) {
      this.clearScrollState();
      return;
    }

    var sentinelTop = this.sentinel.getBoundingClientRect().top;
    var stickyTop = this.sticky.getBoundingClientRect().top;
    var pinned = stickyTop <= 1;

    if (!pinned && sentinelTop > 0) {
      this.restSentinelTop = Math.max(this.restSentinelTop, sentinelTop);
    }

    var travel = this.restSentinelTop || sentinelTop || window.innerHeight;
    if (travel < 1) travel = window.innerHeight;

    var progress = clamp(1 - sentinelTop / travel, 0, 1);
    var seamCover = overlapping ? 2 : 0;
    var translateY = -this.overlap * progress - seamCover;
    var layoutTrim = this.overlap * progress;
    var overlapping = progress > 0.001;

    this.root.style.setProperty("--gacs-progress", progress.toFixed(4));
    this.root.style.setProperty("--gacs-translate-y", translateY.toFixed(2) + "px");
    this.root.style.setProperty("--gacs-layout-trim", layoutTrim.toFixed(2) + "px");
    if (this.sticky) {
      this.sticky.style.marginBottom = (-layoutTrim).toFixed(2) + "px";
    }
    if (this.surface) {
      this.surface.style.transform = "";
      this.surface.style.marginBottom = "";
    }
    this.root.style.setProperty("--gacs-veil-alpha", (progress * 0.32).toFixed(4));
    this.root.style.setProperty(
      "--gacs-shadow-alpha",
      (0.1 + progress * 0.26).toFixed(3)
    );
    this.root.style.setProperty(
      "--gacs-shadow-blur",
      (20 + progress * 44).toFixed(1) + "px"
    );

    if (this.sectionEl) {
      this.sectionEl.style.setProperty("--gacs-layout-trim", layoutTrim.toFixed(2) + "px");
    }

    this.root.classList.toggle("is-overlapping", overlapping);
    this.root.classList.toggle("is-pinned-top", pinned);
    if (this.sectionEl) {
      this.sectionEl.classList.toggle("gacs-section-over-chrome", overlapping);
    }

    if (this.prevSection) {
      this.prevSection.style.setProperty("--gacs-under-dim", progress.toFixed(4));
      this.prevSection.classList.toggle("gacs-under-panel", overlapping);
    }

    if (overlapping) {
      this.syncPanelHeight(progress);
    } else {
      this.syncPanelHeight(0);
      if (window.GicleeArtistLayoutSync) {
        window.GicleeArtistLayoutSync.releaseBioSectionsIfIdle();
      }
    }

    if (this.root.classList.contains("gacs-end-page-wrap")) {
      this.trimEndPageScrollBleed(pinned);
    }
  };

  GicleeArtistScrollPanel.prototype.bind = function () {
    var self = this;

    function scheduleUpdate() {
      if (self.ticking) return;
      self.ticking = true;
      window.requestAnimationFrame(function () {
        self.ticking = false;
        self.update();
      });
    }

    window.addEventListener("scroll", scheduleUpdate, { passive: true });
    window.addEventListener("resize", function () {
      self.measure();
      self.restSentinelTop = self.sentinel.getBoundingClientRect().top;
      scheduleUpdate();
    }, { passive: true });
  };

  function bootEndPage() {
    var endSections = document.querySelectorAll(".giclee-artist-showcase.gacs-end-page");
    if (!endSections.length) return;

    document.body.classList.add("gacs-gallery-end-page");
    endSections.forEach(function (el) {
      var section = el.closest(".shopify-section");
      if (section) section.classList.add("gacs-section-end-page");
    });
  }

  function boot() {
    bootEndPage();

    document.querySelectorAll("[data-giclee-artist-showcase]").forEach(function (el) {
      if (el.dataset.gacsInit === "1") return;
      el.dataset.gacsInit = "1";
      var showcase = new GicleeArtistShowcase(el);
      el._gacsShowcase = showcase;

      if (el.hasAttribute("data-gacs-exhibition")) {
        var exhibition = new GicleeArtistExhibition(el);
        if (exhibition.artists && exhibition.artists.length > 1) {
          exhibition.attachShowcase(showcase);
          if (window.GicleeArtistBiographyBoot) {
            window.GicleeArtistBiographyBoot();
          }
        }
      }
    });

    document.querySelectorAll("[data-gacs-scroll-panel]").forEach(function (el) {
      if (el.dataset.gacsScrollInit === "1") return;
      el.dataset.gacsScrollInit = "1";
      new GicleeArtistScrollPanel(el);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  document.addEventListener("shopify:section:load", boot);
})();
