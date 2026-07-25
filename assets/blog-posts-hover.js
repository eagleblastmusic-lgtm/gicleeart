/* Blog — GSAP hover wpisów (bez filter i bez overlay — unika szarego błysku). */
(() => {
  const initializeBlogPostHover = () => {
    if (typeof gsap === 'undefined') {
      console.warn('[Blog hover] Biblioteka GSAP nie została załadowana.');
      return;
    }

    const posts = document.querySelectorAll('.blog-post');

    if (!posts.length) {
      console.warn(
        '[Blog hover] Nie znaleziono elementów .blog-post. Dopasuj selektor do istniejącej klasy wpisu.'
      );
      return;
    }

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    posts.forEach((post) => {
      if (post.dataset.gsapHoverInitialized === 'true') return;

      post.dataset.gsapHoverInitialized = 'true';

      const image = post.querySelector('img');
      /* Tytuł w motywie to często .text-block (preset h4), nie <h1–h3>. */
      const title = post.querySelector(
        '.blog-post__title, [data-testid="blog-post-link"] .text-block, h1, h2, h3, h4, h5, h6'
      );
      const date = post.querySelector('.blog-post__date, time, .blog-post-details');
      /* Excerpt to kontener tekstu, nie zawsze <p>. */
      const excerpt = post.querySelector(
        '.blog-post__excerpt, .blog-post-card__content-text, p'
      );
      /* Pierwsze <a> to często link obrazka — preferuj „Czytaj dalej”. */
      const link =
        post.querySelector('.blog-post__link, .blog-post-card__content-text a') ||
        post.querySelector('[data-testid="blog-post-link"]');

      if (image && image.parentElement) {
        const imageWrapper = image.parentElement;
        imageWrapper.classList.add('blog-post__gsap-image-wrapper');

        const imageRadius = window.getComputedStyle(image).borderRadius;
        if (imageRadius && imageRadius !== '0px') {
          imageWrapper.style.borderRadius = imageRadius;
        }
      }

      gsap.set(post, {
        x: 0,
        y: 0,
        scale: 1,
        force3D: true,
      });

      if (image) {
        gsap.set(image, {
          x: 0,
          y: 0,
          scale: 1,
          force3D: true,
        });
      }

      [title, date, excerpt, link].forEach((element) => {
        if (!element) return;

        gsap.set(element, {
          x: 0,
          force3D: true,
        });
      });

      if (reducedMotion) return;

      const timeline = gsap.timeline({
        paused: true,
        defaults: {
          ease: 'power3.out',
          overwrite: 'auto',
        },
      });

      timeline.to(
        post,
        {
          y: -7,
          scale: 1.006,
          duration: 0.48,
        },
        0
      );

      if (image) {
        timeline.to(
          image,
          {
            scale: 1.05,
            duration: 0.85,
            ease: 'power2.out',
          },
          0
        );
      }

      if (title) {
        timeline.to(
          title,
          {
            x: 5,
            duration: 0.42,
          },
          0.03
        );
      }

      if (date) {
        timeline.to(
          date,
          {
            x: 3,
            duration: 0.4,
          },
          0.05
        );
      }

      if (excerpt) {
        timeline.to(
          excerpt,
          {
            x: 4,
            duration: 0.42,
          },
          0.07
        );
      }

      /* Link w motywie siedzi w excerpt — osobne x dublowałoby przesunięcie. */
      if (link && !(excerpt && excerpt.contains(link))) {
        timeline.to(
          link,
          {
            x: 7,
            duration: 0.42,
          },
          0.09
        );
      }

      const playHover = () => {
        timeline.timeScale(1).play();
      };

      const reverseHover = (event) => {
        if (event && event.type === 'focusout') {
          const next = event.relatedTarget;
          if (next && post.contains(next)) return;
        }
        timeline.timeScale(1.15).reverse();
      };

      post.addEventListener('pointerenter', playHover);
      post.addEventListener('pointerleave', reverseHover);
      post.addEventListener('focusin', playHover);
      post.addEventListener('focusout', reverseHover);
    });
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeBlogPostHover, { once: true });
  } else {
    initializeBlogPostHover();
  }
})();
