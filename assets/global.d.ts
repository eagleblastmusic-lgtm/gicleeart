export {};

declare global {
  interface Shopify {
    country: string;
    currency: {
      active: string;
      rate: string;
    };
    designMode: boolean;
    locale: string;
    shop: string;
    loadFeatures(features: ShopifyFeature[], callback?: LoadCallback): void;
    ModelViewerUI?: ModelViewer;
    visualPreviewMode: boolean;
  }

  interface Theme {
    translations: Record<string, string>;
    routes: {
      cart_add_url: string;
      cart_change_url: string;
      cart_update_url: string;
      cart_url: string;
      predictive_search_url: string;
      search_url: string;
    };
    utilities: {
      scheduler: {
        schedule: (task: () => void) => void;
      };
    };
    template: {
      name: string;
    };
  }

  /** Minimal GSAP surface used by FAQ scripts (CDN global). */
  type GsapTweenTarget = string | Element | Element[] | NodeListOf<Element> | object;

  interface GsapScrollTriggerVars {
    trigger?: Element | string;
    start?: string;
    end?: string;
    scrub?: boolean | number;
    markers?: boolean;
  }

  interface GsapTweenVars {
    duration?: number;
    delay?: number;
    x?: number;
    y?: number;
    yPercent?: number;
    opacity?: number;
    scale?: number;
    stagger?: number | object;
    ease?: string;
    transformOrigin?: string;
    display?: string;
    filter?: string;
    clearProps?: string;
    overwrite?: boolean | string;
    scrollTrigger?: GsapScrollTriggerVars;
    onComplete?: () => void;
    onStart?: () => void;
  }

  interface GsapTimeline {
    to(
      targets: GsapTweenTarget,
      vars: GsapTweenVars,
      position?: string | number
    ): GsapTimeline;
    from(
      targets: GsapTweenTarget,
      vars: GsapTweenVars,
      position?: string | number
    ): GsapTimeline;
    fromTo(
      targets: GsapTweenTarget,
      fromVars: GsapTweenVars,
      toVars: GsapTweenVars,
      position?: string | number
    ): GsapTimeline;
    set(
      targets: GsapTweenTarget,
      vars: GsapTweenVars,
      position?: string | number
    ): GsapTimeline;
    kill(): void;
  }

  interface GsapTween {
    kill(): void;
  }

  interface GsapStatic {
    from(targets: GsapTweenTarget, vars: GsapTweenVars): GsapTween;
    to(targets: GsapTweenTarget, vars: GsapTweenVars): GsapTween;
    fromTo(
      targets: GsapTweenTarget,
      fromVars: GsapTweenVars,
      toVars: GsapTweenVars
    ): GsapTween;
    set(targets: GsapTweenTarget, vars: GsapTweenVars): GsapTween;
    timeline(vars?: GsapTweenVars): GsapTimeline;
    delayedCall(delay: number, callback: () => void): GsapTween;
    registerPlugin(...plugins: object[]): void;
  }

  /** ScrollTrigger plugin (CDN global / window.ScrollTrigger). */
  interface ScrollTriggerStatic {
    create?(vars: GsapScrollTriggerVars): unknown;
    refresh?(safe?: boolean): void;
  }

  interface Window {
    Shopify: Shopify;
    /** FAQ accordion entrance (assets/faq-accordion-entrance.js) */
    __GICLEE_FAQ_ACCORDION_ENTRANCE__?: boolean;
    /** Hero text hover on FAQ / Blog (assets/giclee-hero-text-hover.js) */
    __GICLEE_HERO_TEXT_HOVER__?: boolean;
    /** GSAP from CDN (jsDelivr); present on FAQ / Blog after script load. */
    gsap?: GsapStatic;
    /** GSAP ScrollTrigger from CDN. */
    ScrollTrigger?: ScrollTriggerStatic;
  }

  var Shopify: Shopify;
  var Theme: Theme;
  /** GSAP CDN global (same as window.gsap). */
  var gsap: GsapStatic | undefined;
  /** ScrollTrigger CDN global (same as window.ScrollTrigger). */
  var ScrollTrigger: ScrollTriggerStatic | undefined;

  type LoadCallback = (error: Error | undefined) => void;

  // Refer to https://github.com/Shopify/shopify/blob/main/areas/core/shopify/app/assets/javascripts/storefront/load_feature/load_features.js
  interface ShopifyFeature {
    name: string;
    version: string;
    onLoad?: LoadCallback;
  }

  // Refer to https://github.com/Shopify/model-viewer-ui/blob/main/src/js/model-viewer-ui.js
  interface ModelViewer {
    new (
      element: Element,
      options?: {
        focusOnPlay?: boolean;
      }
    ): ModelViewer;
    play(): void;
    pause(): void;
    toggleFullscreen(): void;
    zoom(amount: number): void;
    destroy(): void;
  }

  // Device Memory API - https://developer.mozilla.org/en-US/docs/Web/API/Navigator/deviceMemory
  interface Navigator {
    readonly deviceMemory?: number;
  }
}
