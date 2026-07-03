/**
 * <giclee-gallery> — galeria PDP (lewa kolumna) dla product.nowy-szblon-produktu.
 * Crossfade miedzy zdjeciami, miniatury, strzalki, klawiatura, swipe, lightbox.
 * Bez zaleznosci zewnetrznych.
 */
(function () {
  function passepartoutToMockupVariant(value) {
    const norm =
      (window.GICLEE_PASSEPARTOUT && window.GICLEE_PASSEPARTOUT.normalize(value)) ||
      String(value || '').trim();
    return norm === 'Czarne' ? 'CZCZ' : 'CZB';
  }

  function mockupVariantToPassepartout(variant) {
    return String(variant || '').toUpperCase() === 'CZCZ' ? 'Czarne' : 'Białe';
  }

  class GicleeGallery extends HTMLElement {
    connectedCallback() {
      this.index = 0;
      this.slides = Array.from(this.querySelectorAll('[data-gg-slide]'));
      this.thumbs = Array.from(this.querySelectorAll('[data-gg-thumb]'));
      this.lbSlides = Array.from(this.querySelectorAll('[data-gg-lb-slide]'));
      this.counters = Array.from(this.querySelectorAll('[data-gg-current]'));
      this.count = this.slides.length;
      this.lightbox = this.querySelector('[data-gg-lightbox]');
      this.stage = this.querySelector('[data-gg-stage]');
      this._passepartoutHandler = (event) => {
        const detail = event.detail || {};
        const variant =
          detail.mockupVariant || passepartoutToMockupVariant(detail.value);
        this.goToMockupVariant(variant, { syncPassepartout: false });
      };

      if (this.count === 0) return;

      this.thumbs.forEach((thumb) => {
        thumb.addEventListener('click', () => {
          this.goTo(parseInt(thumb.dataset.ggThumb, 10));
        });
      });

      this.querySelectorAll('[data-gg-prev]').forEach((btn) =>
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          this.step(-1);
        })
      );
      this.querySelectorAll('[data-gg-next]').forEach((btn) =>
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          this.step(1);
        })
      );

      this.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowLeft') {
          this.step(-1);
        } else if (e.key === 'ArrowRight') {
          this.step(1);
        }
      });

      // Powiekszenie -> lightbox
      this.querySelectorAll('[data-gg-zoom]').forEach((btn) =>
        btn.addEventListener('click', () => this.openLightbox())
      );

      if (this.lightbox) {
        const closeBtn = this.lightbox.querySelector('[data-gg-lb-close]');
        if (closeBtn) closeBtn.addEventListener('click', () => this.closeLightbox());
        // klik na tlo (poza zdjeciem) zamyka
        this.lightbox.addEventListener('click', (e) => {
          if (e.target === this.lightbox) this.closeLightbox();
        });
        this.lightbox.addEventListener('cancel', (e) => {
          e.preventDefault();
          this.closeLightbox();
        });
        this.initSwipe(this.lightbox);
      }

      this.initSwipe(this.stage);

      const initialIndex = this.findSlideIndexForVariant('CZB');
      if (initialIndex >= 0) {
        this.index = initialIndex;
      }

      document.addEventListener('giclee:passepartout-change', this._passepartoutHandler);
      this.sync(true);
    }

    disconnectedCallback() {
      if (this._passepartoutHandler) {
        document.removeEventListener('giclee:passepartout-change', this._passepartoutHandler);
      }
    }

    findSlideIndexForVariant(variant) {
      const target = String(variant || '').toUpperCase();
      if (!target) return -1;
      return this.slides.findIndex(
        (slide) => String(slide.dataset.ggMockupVariant || '').toUpperCase() === target
      );
    }

    goToMockupVariant(variant, options = {}) {
      const idx = this.findSlideIndexForVariant(variant);
      if (idx < 0) return;
      this.goTo(idx, options);
    }

    syncPassepartoutFromActiveSlide() {
      const activeSlide = this.slides[this.index];
      if (!activeSlide) return;
      const variant = activeSlide.dataset.ggMockupVariant;
      if (!variant) return;

      const target = mockupVariantToPassepartout(variant);
      document.querySelectorAll('[data-giclee-passepartout-picker]').forEach((root) => {
        const radios = root.querySelectorAll('input[data-giclee-pp-value]');
        radios.forEach((radio) => {
          const label = radio.getAttribute('data-giclee-pp-value') || radio.value;
          const norm =
            (window.GICLEE_PASSEPARTOUT && window.GICLEE_PASSEPARTOUT.normalize(label)) ||
            String(label || '').trim();
          if (norm === target && !radio.checked) {
            radio.checked = true;
            radio.dispatchEvent(new Event('change', { bubbles: true }));
          }
        });
      });
    }

    step(delta) {
      this.goTo(this.index + delta);
    }

    goTo(i, options = {}) {
      const syncPassepartout = options.syncPassepartout !== false;
      if (this.count <= 0) return;
      this.index = ((i % this.count) + this.count) % this.count;
      this.sync(undefined, syncPassepartout);
    }

    sync(immediate, syncPassepartout = true) {
      this.slides.forEach((s, idx) => s.classList.toggle('is-active', idx === this.index));
      this.lbSlides.forEach((s, idx) => s.classList.toggle('is-active', idx === this.index));
      this.thumbs.forEach((t, idx) => {
        const active = idx === this.index;
        t.classList.toggle('is-active', active);
        t.setAttribute('aria-selected', active ? 'true' : 'false');
        if (active && !immediate) {
          t.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'smooth' });
        }
      });
      this.counters.forEach((c) => {
        c.textContent = String(this.index + 1);
      });
      this.syncStageRatio();
      if (syncPassepartout && !immediate) {
        this.syncPassepartoutFromActiveSlide();
      }
    }

    syncStageRatio() {
      if (!this.stage || this.count === 0) return;
      const activeSlide = this.slides[this.index];
      if (!activeSlide) return;

      const ratio = parseFloat(
        getComputedStyle(activeSlide).getPropertyValue('--gg-ratio')
      );
      if (!ratio || !isFinite(ratio) || ratio <= 0) return;

      this.stage.style.setProperty('--gg-stage-ratio', String(ratio));
    }

    openLightbox() {
      if (!this.lightbox) return;
      if (typeof this.lightbox.showModal === 'function') {
        this.lightbox.showModal();
      } else {
        this.lightbox.setAttribute('open', '');
      }
      document.documentElement.style.overflow = 'hidden';
    }

    closeLightbox() {
      if (!this.lightbox) return;
      if (typeof this.lightbox.close === 'function' && this.lightbox.open) {
        this.lightbox.close();
      } else {
        this.lightbox.removeAttribute('open');
      }
      document.documentElement.style.overflow = '';
    }

    initSwipe(el) {
      if (!el) return;
      let startX = 0;
      let startY = 0;
      let tracking = false;

      el.addEventListener(
        'touchstart',
        (e) => {
          if (e.touches.length !== 1) return;
          tracking = true;
          startX = e.touches[0].clientX;
          startY = e.touches[0].clientY;
        },
        { passive: true }
      );

      el.addEventListener(
        'touchend',
        (e) => {
          if (!tracking) return;
          tracking = false;
          const touch = e.changedTouches[0];
          const dx = touch.clientX - startX;
          const dy = touch.clientY - startY;
          if (Math.abs(dx) > 45 && Math.abs(dx) > Math.abs(dy) * 1.5) {
            this.step(dx < 0 ? 1 : -1);
          }
        },
        { passive: true }
      );
    }
  }

  if (!customElements.get('giclee-gallery')) {
    customElements.define('giclee-gallery', GicleeGallery);
  }
})();
