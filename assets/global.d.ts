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
  type GsapTweenTarget = string | Element | Element[] | NodeListOf<Element>;

  interface GsapTweenVars {
    duration?: number;
    delay?: number;
    y?: number;
    opacity?: number;
    scale?: number;
    stagger?: number;
    ease?: string;
    transformOrigin?: string;
    display?: string;
  }

  interface GsapStatic {
    from(targets: GsapTweenTarget, vars: GsapTweenVars): unknown;
    to(targets: GsapTweenTarget, vars: GsapTweenVars): unknown;
    set(targets: GsapTweenTarget, vars: GsapTweenVars): unknown;
  }

  interface Window {
    Shopify: Shopify;
    /** FAQ accordion entrance + heading hover (assets/faq-accordion-entrance.js) */
    __GICLEE_FAQ_ACCORDION_ENTRANCE__?: boolean;
    /** GSAP from CDN (jsDelivr); present on FAQ page after script load. */
    gsap?: GsapStatic;
  }

  declare const Shopify: Shopify;
  declare const Theme: Theme;
  /** GSAP CDN global (same as window.gsap). */
  declare const gsap: GsapStatic | undefined;

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
