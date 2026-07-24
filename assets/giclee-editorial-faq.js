(() => {
  'use strict';

  const TAG_NAME = 'giclee-editorial-faq';
  const DESKTOP_QUERY = '(min-width: 960px)';
  const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)';
  const OPENING_MS = 880;
  const SWITCH_MS = 430;

  if (customElements.get(TAG_NAME)) return;

  class GicleeEditorialFaq extends HTMLElement {
    connectedCallback() {
      if (this.controllerReady) return;
      this.controllerReady = true;
      this.abortController = new AbortController();
      this.cleanupTimers = new Set();
      this.activeAnimations = new Set();
      this.transitionVersion = 0;
      this.activeItem = null;
      this.movedAnswer = null;
      this.morphClone = null;

      this.items = Array.from(this.querySelectorAll('[data-faq-item]'));
      this.index = this.querySelector('[data-faq-index]');
      this.marker = this.querySelector('[data-faq-marker]');
      this.panel = this.querySelector('[data-faq-panel]');
      this.panelInner = this.querySelector('[data-faq-panel-inner]');
      this.panelNumber = this.querySelector('[data-faq-panel-number]');
      this.panelTitle = this.querySelector('[data-faq-panel-title]');
      this.panelBody = this.querySelector('[data-faq-panel-body]');
      this.liveRegion = this.querySelector('[data-faq-live]');
      this.desktopMedia = window.matchMedia(DESKTOP_QUERY);
      this.reducedMotionMedia = window.matchMedia(REDUCED_MOTION_QUERY);

      if (!this.items.length || !this.index || !this.panel || !this.panelBody) return;

      this.normalizeAnchors();
      this.bindEvents();
      this.dataset.enhanced = 'true';
      this.applyMode({ initial: true });

      const hashItem = this.itemFromHash();
      const openItem = this.items.find((item) => item.open);
      const initialItem = hashItem || openItem || (this.dataset.openFirst === 'true' ? this.items[0] : null);
      if (initialItem) {
        this.activate(initialItem, {
          firstOpen: true,
          updateHistory: false,
          scroll: Boolean(hashItem),
          source: hashItem ? 'hash' : 'initial',
        });
      }
    }

    disconnectedCallback() {
      this.destroy();
    }

    bindEvents() {
      const signal = this.abortController.signal;

      this.items.forEach((item) => {
        const trigger = this.triggerFor(item);
        if (!trigger) return;
        trigger.addEventListener('click', (event) => this.onTriggerClick(event, item), { signal });
      });

      window.addEventListener('hashchange', () => this.onHistoryNavigation(), { signal });
      window.addEventListener('popstate', () => this.onHistoryNavigation(), { signal });
      document.addEventListener('shopify:block:select', (event) => this.onBlockSelect(event), { signal });
      document.addEventListener('shopify:section:unload', (event) => this.onSectionUnload(event), { signal });

      this.onMediaChange = () => this.applyMode({ initial: false });
      this.desktopMedia.addEventListener?.('change', this.onMediaChange);
      this.reducedMotionMedia.addEventListener?.('change', this.onMediaChange);

      this.onWindowResize = () => this.scheduleMarkerUpdate();
      window.addEventListener('resize', this.onWindowResize, { passive: true, signal });

      if ('ResizeObserver' in window) {
        this.resizeObserver = new ResizeObserver(() => this.scheduleMarkerUpdate());
        this.resizeObserver.observe(this.index);
      }
    }

    normalizeAnchors() {
      const seen = new Map();
      this.anchorMap = new Map();

      this.items.forEach((item, index) => {
        const trigger = this.triggerFor(item);
        const question = trigger?.querySelector('[data-faq-question]')?.textContent || '';
        const base = this.slugify(item.dataset.faqAnchor || question) || `pytanie-${index + 1}`;
        const count = (seen.get(base) || 0) + 1;
        seen.set(base, count);
        const anchor = count === 1 ? base : `${base}-${count}`;
        item.dataset.faqAnchor = anchor;
        item.id = `${this.id || 'editorial-faq'}-${anchor}`;
        trigger?.setAttribute('aria-expanded', String(item.open));
        this.anchorMap.set(anchor, item);
      });
    }

    slugify(value) {
      return String(value || '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/ł/g, 'l')
        .replace(/Ł/g, 'L')
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '')
        .replace(/-{2,}/g, '-');
    }

    triggerFor(item) {
      return item?.querySelector('[data-faq-trigger]') || null;
    }

    answerFor(item) {
      return item?.querySelector('[data-faq-answer]') || null;
    }

    homeFor(item) {
      return item?.querySelector('[data-faq-answer-home]') || null;
    }

    isDesktop() {
      return this.desktopMedia.matches;
    }

    premiumMotionEnabled() {
      return this.dataset.premiumMotion !== 'false' && !this.reducedMotionMedia.matches;
    }

    onTriggerClick(event, item) {
      event.preventDefault();
      const shouldClose = !this.isDesktop() && item === this.activeItem && item.open;

      if (shouldClose) {
        this.closeMobileItem(item, { updateHistory: true });
        return;
      }

      this.activate(item, {
        firstOpen: !this.activeItem,
        updateHistory: true,
        scroll: false,
        source: 'user',
      });
    }

    activate(item, options = {}) {
      if (!item || !this.items.includes(item)) return;
      const wasOpen = Boolean(this.activeItem);
      const previousItem = this.activeItem;
      const previousPanelHeight = this.panelBody?.getBoundingClientRect().height || 0;
      const version = ++this.transitionVersion;

      this.cancelTransientWork();
      this.restoreMovedAnswer();
      this.activeItem = item;

      this.items.forEach((candidate) => {
        const active = candidate === item;
        candidate.open = active;
        candidate.classList.toggle('is-active', active);
        this.triggerFor(candidate)?.setAttribute('aria-expanded', String(active));
      });
      this.classList.add('has-active-item');

      if (this.isDesktop()) {
        this.activateDesktop(item, {
          firstOpen: options.firstOpen ?? !wasOpen,
          previousItem,
          previousPanelHeight,
          version,
        });
      } else {
        this.activateMobile(item, { firstOpen: options.firstOpen ?? !wasOpen });
      }

      this.updateMarker();
      if (options.updateHistory) this.writeHash(item.dataset.faqAnchor);
      if (options.scroll) this.scrollItemIntoView(item);
      if (this.liveRegion) {
        this.liveRegion.textContent = `Otwarto odpowiedź: ${this.questionText(item)}`;
      }
    }

    activateDesktop(item, { firstOpen, previousItem, previousPanelHeight = 0, version }) {
      const answer = this.answerFor(item);
      const trigger = this.triggerFor(item);
      const questionNode = trigger?.querySelector('[data-faq-question]');
      if (!answer || !questionNode) return;

      this.panel.hidden = false;
      this.panel.setAttribute('aria-hidden', 'false');
      this.classList.add('is-open');
      this.classList.toggle('is-opening', Boolean(firstOpen && this.premiumMotionEnabled()));
      this.classList.toggle('is-switching', Boolean(!firstOpen && previousItem && this.premiumMotionEnabled()));

      this.panelNumber.textContent = `${this.numberText(item)} / ${String(this.items.length).padStart(2, '0')}`;
      this.panelTitle.textContent = this.questionText(item);
      this.panelBody.replaceChildren(answer);
      answer.removeAttribute('aria-hidden');
      this.movedAnswer = { item, answer };

      this.animatePanelHeight(previousPanelHeight, firstOpen);

      if (this.premiumMotionEnabled()) {
        this.morphFrame = requestAnimationFrame(() => {
          this.morphFrame = 0;
          if (version !== this.transitionVersion || !this.isConnected) return;
          this.morphQuestion(questionNode, this.panelTitle, firstOpen);
        });
      }

      this.setCleanupTimer(() => {
        if (version !== this.transitionVersion) return;
        this.classList.remove('is-opening', 'is-switching');
      }, firstOpen ? OPENING_MS : SWITCH_MS);
    }

    activateMobile(item, { firstOpen }) {
      this.panel.hidden = true;
      this.panel.setAttribute('aria-hidden', 'true');
      this.classList.remove('is-open', 'is-opening', 'is-switching');
      item.classList.add('is-revealing');
      this.setCleanupTimer(() => item.classList.remove('is-revealing'), firstOpen ? 600 : 400);
    }

    closeMobileItem(item, { updateHistory }) {
      if (!item) return;
      this.closeActiveItem({ updateHistory });
    }

    closeActiveItem({ updateHistory }) {
      const item = this.activeItem;
      if (!item) return;
      ++this.transitionVersion;
      this.cancelTransientWork();
      this.restoreMovedAnswer();
      item.open = false;
      item.classList.remove('is-active', 'is-revealing');
      this.triggerFor(item)?.setAttribute('aria-expanded', 'false');
      this.activeItem = null;
      this.panel.hidden = true;
      this.panel.setAttribute('aria-hidden', 'true');
      this.panelBody.replaceChildren();
      this.classList.remove('has-active-item', 'is-open', 'is-opening', 'is-switching');
      this.marker?.classList.remove('is-visible');
      if (updateHistory) this.clearHash();
    }

    restoreMovedAnswer() {
      if (!this.movedAnswer) return;
      const { item, answer } = this.movedAnswer;
      const home = this.homeFor(item);
      if (home?.isConnected && answer) home.after(answer);
      this.movedAnswer = null;
    }

    applyMode({ initial }) {
      const previousPanelHeight = this.panelBody?.getBoundingClientRect().height || 0;
      const version = ++this.transitionVersion;
      this.cancelTransientWork();
      this.restoreMovedAnswer();
      this.classList.toggle('is-desktop', this.isDesktop());
      this.classList.toggle('is-mobile', !this.isDesktop());

      if (!this.activeItem) {
        this.panel.hidden = true;
        this.panel.setAttribute('aria-hidden', 'true');
        return;
      }

      if (this.isDesktop()) {
        this.activateDesktop(this.activeItem, {
          firstOpen: Boolean(initial),
          previousItem: this.activeItem,
          previousPanelHeight,
          version,
        });
      } else {
        this.panel.hidden = true;
        this.panel.setAttribute('aria-hidden', 'true');
        this.activeItem.open = true;
      }
      this.updateMarker();
    }

    animatePanelHeight(previousHeight, firstOpen) {
      if (!this.premiumMotionEnabled() || firstOpen || !previousHeight) {
        this.panelBody.style.removeProperty('height');
        this.panelBody.style.removeProperty('overflow');
        return;
      }

      const targetHeight = this.panelBody.scrollHeight;
      this.panelBody.style.height = `${previousHeight}px`;
      this.panelBody.style.overflow = 'clip';
      requestAnimationFrame(() => {
        this.panelBody.style.height = `${targetHeight}px`;
      });
      this.setCleanupTimer(() => {
        this.panelBody.style.removeProperty('height');
        this.panelBody.style.removeProperty('overflow');
      }, SWITCH_MS + 60);
    }

    morphQuestion(source, target, firstOpen) {
      if (!source || !target || !this.premiumMotionEnabled()) return;
      this.removeMorphClone();

      const sourceRect = source.getBoundingClientRect();
      const targetRect = target.getBoundingClientRect();
      if (!sourceRect.width || !targetRect.width) return;

      const clone = document.createElement('span');
      clone.className = 'giclee-editorial-faq__morph-clone';
      clone.setAttribute('aria-hidden', 'true');
      clone.textContent = source.textContent?.trim() || '';
      Object.assign(clone.style, {
        left: `${sourceRect.left}px`,
        top: `${sourceRect.top}px`,
        width: `${sourceRect.width}px`,
        fontSize: window.getComputedStyle(source).fontSize,
      });
      document.body.appendChild(clone);
      this.morphClone = clone;

      const dx = targetRect.left - sourceRect.left;
      const dy = targetRect.top - sourceRect.top;
      const scale = Math.max(0.65, Math.min(2.8, targetRect.width / sourceRect.width));
      target.style.opacity = '0';

      const animation = clone.animate(
        [
          { transform: 'translate3d(0, 0, 0) scale(1)', opacity: 1 },
          { transform: `translate3d(${dx}px, ${dy}px, 0) scale(${scale})`, opacity: 0.18 },
        ],
        {
          duration: firstOpen ? 780 : 390,
          easing: 'cubic-bezier(0.22, 1, 0.36, 1)',
          fill: 'forwards',
        },
      );
      this.activeAnimations.add(animation);

      const finish = () => {
        this.activeAnimations.delete(animation);
        target.style.removeProperty('opacity');
        this.removeMorphClone();
      };
      animation.addEventListener('finish', finish, { once: true });
      animation.addEventListener('cancel', finish, { once: true });
    }

    removeMorphClone() {
      this.morphClone?.remove();
      this.morphClone = null;
      this.panelTitle?.style.removeProperty('opacity');
    }

    updateMarker() {
      if (!this.marker || !this.activeItem || !this.index) return;
      const trigger = this.triggerFor(this.activeItem);
      if (!trigger) return;
      const indexRect = this.index.getBoundingClientRect();
      const triggerRect = trigger.getBoundingClientRect();
      const markerY = triggerRect.top - indexRect.top + (triggerRect.height - 42) / 2;
      this.style.setProperty('--gef-marker-y', `${Math.max(0, markerY).toFixed(2)}px`);
      this.marker.classList.add('is-visible');
    }

    scheduleMarkerUpdate() {
      if (this.markerFrame) cancelAnimationFrame(this.markerFrame);
      this.markerFrame = requestAnimationFrame(() => {
        this.markerFrame = 0;
        this.updateMarker();
      });
    }

    writeHash(anchor) {
      if (!anchor || window.location.hash === `#${anchor}`) return;
      const nextUrl = `${window.location.pathname}${window.location.search}#${encodeURIComponent(anchor)}`;
      window.history.pushState({ editorialFaq: anchor }, '', nextUrl);
    }

    clearHash() {
      if (!window.location.hash) return;
      window.history.pushState({}, '', `${window.location.pathname}${window.location.search}`);
    }

    itemFromHash() {
      const rawHash = decodeURIComponent(window.location.hash.replace(/^#/, ''));
      return this.anchorMap?.get(this.slugify(rawHash)) || null;
    }

    onHistoryNavigation() {
      const item = this.itemFromHash();
      if (item) {
        if (item === this.activeItem) return;
        this.activate(item, { firstOpen: !this.activeItem, updateHistory: false, scroll: false, source: 'history' });
      } else if (this.activeItem) {
        this.closeActiveItem({ updateHistory: false });
      }
    }

    onBlockSelect(event) {
      const blockId = event.detail?.blockId;
      if (!blockId) return;
      const item = this.items.find((candidate) => {
        const editorData = candidate.getAttribute('data-shopify-editor-block') || '';
        return editorData.includes(blockId);
      });
      if (item) this.activate(item, { firstOpen: !this.activeItem, updateHistory: false, scroll: false, source: 'editor' });
    }

    onSectionUnload(event) {
      if (event.detail?.sectionId === this.dataset.sectionId) this.destroy();
    }

    questionText(item) {
      return this.triggerFor(item)?.querySelector('[data-faq-question]')?.textContent?.trim() || '';
    }

    numberText(item) {
      return this.triggerFor(item)?.querySelector('.giclee-editorial-faq__number')?.textContent?.trim() || '01';
    }

    scrollItemIntoView(item) {
      requestAnimationFrame(() => {
        item.scrollIntoView({ behavior: this.premiumMotionEnabled() ? 'smooth' : 'auto', block: 'start' });
      });
    }

    setCleanupTimer(callback, delay) {
      const timer = window.setTimeout(() => {
        this.cleanupTimers.delete(timer);
        callback();
      }, delay);
      this.cleanupTimers.add(timer);
      return timer;
    }

    cancelTransientWork() {
      this.cleanupTimers.forEach((timer) => clearTimeout(timer));
      this.cleanupTimers.clear();
      this.activeAnimations.forEach((animation) => animation.cancel());
      this.activeAnimations.clear();
      if (this.morphFrame) cancelAnimationFrame(this.morphFrame);
      this.morphFrame = 0;
      this.removeMorphClone();
      this.classList.remove('is-opening', 'is-switching');
      this.panelBody?.style.removeProperty('height');
      this.panelBody?.style.removeProperty('overflow');
    }

    destroy() {
      if (!this.controllerReady) return;
      this.cancelTransientWork();
      this.restoreMovedAnswer();
      this.abortController?.abort();
      this.resizeObserver?.disconnect();
      this.desktopMedia?.removeEventListener?.('change', this.onMediaChange);
      this.reducedMotionMedia?.removeEventListener?.('change', this.onMediaChange);
      if (this.markerFrame) cancelAnimationFrame(this.markerFrame);
      this.markerFrame = 0;
      this.controllerReady = false;
      delete this.dataset.enhanced;
    }
  }

  customElements.define(TAG_NAME, GicleeEditorialFaq);
})();
