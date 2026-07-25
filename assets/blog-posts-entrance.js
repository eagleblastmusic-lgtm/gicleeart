/* Blog — GSAP: wejście kart wpisów (ScrollTrigger stagger). */
(function () {
  if (window.__GICLEE_BLOG_POSTS_ENTRANCE__) return;
  window.__GICLEE_BLOG_POSTS_ENTRANCE__ = true;

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  var currentScript = /** @type {HTMLScriptElement | null} */ (document.currentScript);
  var sb3CurtainUrl =
    currentScript && currentScript.src
      ? currentScript.src.replace(
          /blog-posts-entrance\.js(?:\?.*)?$/,
          'blog-sb3-hero-curtain.js'
        )
      : '';

  function getGsap() {
    return window.gsap || (typeof gsap !== 'undefined' ? gsap : undefined);
  }

  function getScrollTrigger() {
    return (
      window.ScrollTrigger ||
      (typeof ScrollTrigger !== 'undefined' ? ScrollTrigger : undefined)
    );
  }

  /**
   * @param {(api: { gsap: GsapStatic, ScrollTrigger: object }) => void} callback
   */
  function whenReady(callback) {
    var tween = getGsap();
    var st = getScrollTrigger();
    if (tween && st) {
      callback({ gsap: tween, ScrollTrigger: st });
      return;
    }

    var attempts = 0;
    var timer = window.setInterval(function () {
      attempts += 1;
      var nextTween = getGsap();
      var nextSt = getScrollTrigger();
      if (nextTween && nextSt) {
        window.clearInterval(timer);
        callback({ gsap: nextTween, ScrollTrigger: nextSt });
        return;
      }
      if (attempts >= 40) window.clearInterval(timer);
    }, 50);
  }

  function runCardsEntrance(apis) {
    var tween = apis.gsap;
    var ScrollTriggerPlugin = apis.ScrollTrigger;

    var container = document.querySelector('.blog-posts-container');
    if (!container) return;

    var items = container.querySelectorAll('.blog-post-item');
    if (!items.length) return;

    container.classList.add('cards');
    items.forEach(function (el) {
      el.classList.add('card');
    });

    tween.registerPlugin(ScrollTriggerPlugin);

    tween.from('.blog-posts .card', {
      scrollTrigger: { trigger: '.blog-posts .cards', start: 'top 80%' },
      y: 50,
      opacity: 0,
      stagger: 0.1,
      duration: 1,
      ease: 'power3.out',
    });
  }

  function loadSb3HeroCurtain() {
    var config = window.GICLEE_PAGE_SECTION_EFFECTS;
    if (!config || config.page !== 'blog' || config.variant !== 'sb3') return;
    if (!sb3CurtainUrl) return;
    if (document.querySelector('script[data-giclee-blog-sb3-curtain="true"]')) return;

    var script = document.createElement('script');
    script.src = sb3CurtainUrl;
    script.defer = true;
    script.dataset.gicleeBlogSb3Curtain = 'true';
    document.head.appendChild(script);
  }

  function run() {
    whenReady(runCardsEntrance);
    loadSb3HeroCurtain();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})();
