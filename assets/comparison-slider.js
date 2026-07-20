import { Component } from '@theme/component';
import { oncePerEditorSession } from '@theme/utilities';

/**
 * Comparison slider component for comparing two images
 *
 * @typedef {object} ComparisonSliderRefs
 * @property {HTMLElement} mediaWrapper - The container for the images
 * @property {HTMLInputElement} slider - The range input element
 * @property {HTMLElement} afterImage - The image that gets revealed
 *
 * @extends {Component<ComparisonSliderRefs>}
 *
 * @property {string[]} requiredRefs - Required refs: 'mediaWrapper', 'slider', and 'afterImage'
 */
export class ComparisonSliderComponent extends Component {
  requiredRefs = ['mediaWrapper', 'slider', 'afterImage'];

  constructor() {
    super();
    this.hasAnimated = false;
    this.boundHandleIntersection = this.handleIntersection.bind(this);
  }

  /**
   * Called when component is added to DOM
   */
  connectedCallback() {
    super.connectedCallback();

    const { mediaWrapper } = this.refs;

    // Get orientation from media wrapper
    this.orientation = mediaWrapper.dataset.orientation || 'horizontal';

    // Initialize the position
    this.sync();

    // Native v2 already animates the document for every wheel impulse. Running the
    // 1.6 s comparison-slider hint while sticky sections are moving causes large
    // clip-path repaints, so keep the slider interactive but skip only the hint.
    if (this.nativeV2AutoHintDisabled()) {
      this.hasAnimated = true;
      mediaWrapper.style.setProperty('--transition-duration', '0s');
      this.dataset.gicleeNativeV2Hint = 'disabled';
      return;
    }

    // Set up intersection observer for animation
    this.setupIntersectionObserver();
  }

  /**
   * Disable only the automatic hint on the homepage cinematic wheel profile.
   * Manual input remains fully functional.
   */
  nativeV2AutoHintDisabled() {
    const config = window.GICLEE_PREHERO_CONFIG || {};
    const mode = String(config.smoothScrollMode || '').trim().toLowerCase();
    return mode === 'native-v2' || document.documentElement.classList.contains('giclee-native-v2');
  }

  /**
   * Sync the CSS custom property with the input value
   */
  sync() {
    const { mediaWrapper, slider } = this.refs;
    // Skip sync during animation to prevent lag
    if (this.isAnimating) return;

    const val = (Number(slider.value) - Number(slider.min)) / (Number(slider.max) - Number(slider.min));
    const compareValue = Math.round(val * 100);

    // Set the CSS custom property on the media wrapper
    mediaWrapper.style.setProperty('--compare', String(compareValue));
  }

  /**
   * Clean up when component is removed
   */
  disconnectedCallback() {
    // Clean up intersection observer
    if (this.intersectionObserver) {
      this.intersectionObserver.disconnect();
    }
  }

  /**
   * Set the slider value and update display
   * @param {number} value - Value between 0-100 (0 = all after, 100 = all before)
   */
  setValue(value) {
    const { slider } = this.refs;
    if (!slider) return;

    slider.value = String(value);
    this.sync();
  }

  /**
   * Animate the slider handle to give users a hint about the interaction
   */
  animateSlider() {
    const { mediaWrapper, slider } = this.refs;
    if (this.hasAnimated) return;

    this.hasAnimated = true;
    this.isAnimating = true;

    // Enable transition for smooth animation
    mediaWrapper.style.setProperty('--transition-duration', '0.5s');

    // Create a subtle sliding animation by only setting CSS property
    setTimeout(() => {
      mediaWrapper.style.setProperty('--compare', '40');
    }, 100);

    setTimeout(() => {
      mediaWrapper.style.setProperty('--compare', '60');
    }, 600);

    setTimeout(() => {
      mediaWrapper.style.setProperty('--compare', '50');
    }, 1100);

    setTimeout(() => {
      // Remove transition after animation and sync slider value
      mediaWrapper.style.setProperty('--transition-duration', '0s');
      // Sync the slider value to match the final position
      slider.value = '50';
      this.isAnimating = false;
    }, 1600);
  }

  /**
   * Set up intersection observer to detect when section comes into view
   */
  setupIntersectionObserver() {
    if (!window.IntersectionObserver) return;

    const options = {
      root: null,
      rootMargin: '0px',
      threshold: 0.5, // Trigger when 50% of the component is visible
    };

    this.intersectionObserver = new IntersectionObserver(this.boundHandleIntersection, options);
    this.intersectionObserver.observe(this);
  }

  /**
   * Handle intersection observer callback
   * @param {IntersectionObserverEntry[]} entries
   */
  handleIntersection(entries) {
    entries.forEach((entry) => {
      if (entry.isIntersecting && !this.hasAnimated) {
        // Add a small delay to ensure everything is rendered
        setTimeout(() => {
          oncePerEditorSession(this, `comparison-slider-animated`, () => {
            this.animateSlider();
          });
        }, 300);

        // Disconnect observer after first animation
        if (this.intersectionObserver) {
          this.intersectionObserver.disconnect();
        }
      }
    });
  }
}

// Register the custom element
if (!customElements.get('comparison-slider-component')) {
  customElements.define('comparison-slider-component', ComparisonSliderComponent);
}
