/* Blog — GSAP: wejście kart wpisów (ScrollTrigger stagger). */
(function () {
  if (window.__GICLEE_BLOG_POSTS_ENTRANCE__) return;
  window.__GICLEE_BLOG_POSTS_ENTRANCE__ = true;

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

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

  function run() {
    whenReady(runCardsEntrance);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})();
