(function () {
  "use strict";

  function trim(value) {
    return String(value || "").trim();
  }

  function formatDate(value) {
    var text = trim(value);
    if (!text) return "";
    text = text.toUpperCase();
    if (text.slice(-1) !== "—" && text.slice(-1) !== "-") {
      text += " —";
    }
    return text;
  }

  function formatLine(value) {
    var text = trim(value);
    return text ? text.toUpperCase() : "";
  }

  function normalizeQuoteText(value) {
    return trim(value).replace(/^[„"\u201C\u201E\u00AB\u00BB]+\s*/u, "");
  }

  function withOpeningQuoteMark(formatted) {
    if (!formatted) return "";
    var lines = formatted.split("\n");
    if (!lines.length) return formatted;
    var first = trim(lines[0]);
    if (!first) return formatted;
    if (!/^[„"\u201C]/.test(first)) {
      lines[0] = "„" + first;
    }
    return lines.join("\n");
  }

  /** Estetyczne łamanie cytatu — preferuj 3 linie; respektuj \\n z GicleeApp. */
  function formatQuoteLines(text) {
    text = trim(text);
    if (!text) return "";

    if (/\n/.test(text)) {
      var hardLines = text.split(/\n+/).map(trim).filter(Boolean);
      if (hardLines.length >= 1 && hardLines.length <= 4) {
        return withOpeningQuoteMark(
          hardLines
            .map(function (line) {
              return normalizeQuoteText(line).toUpperCase();
            })
            .join("\n")
        );
      }
    }

    text = text.replace(/\s+/g, " ");
    var upper = normalizeQuoteText(text).toUpperCase();
    if (!upper) return "";

    var endPunct = "";
    if (/[.!?…]$/.test(upper)) {
      endPunct = upper.slice(-1);
      upper = upper.slice(0, -1).trim();
    }

    var body = "";
    var commaIdx = upper.indexOf(",");
    if (commaIdx !== -1) {
      var beforeComma = trim(upper.slice(0, commaIdx));
      var afterComma = trim(upper.slice(commaIdx + 1));
      var beforeWords = beforeComma.split(/\s+/);
      var afterWords = afterComma ? afterComma.split(/\s+/) : [];

      if (beforeWords.length >= 2 && afterWords.length >= 1) {
        var line1 = beforeWords.slice(0, -1).join(" ");
        var bridge = beforeWords[beforeWords.length - 1];
        if (afterWords.length >= 2) {
          body =
            line1 +
            "\n" +
            bridge +
            ", " +
            afterWords[0] +
            "\n" +
            afterWords.slice(1).join(" ") +
            endPunct;
        } else {
          body = line1 + "\n" + bridge + ", " + afterWords.join(" ") + endPunct;
        }
      }
    }

    if (!body) {
      var words = upper.split(/\s+/);
      if (words.length <= 3) {
        var shortLines = words.slice();
        if (endPunct && shortLines.length) {
          shortLines[shortLines.length - 1] += endPunct;
        }
        body = shortLines.join("\n");
      } else {
        var targetLines = 3;
        var lines = [];
        var remaining = words.slice();
        while (lines.length < targetLines - 1 && remaining.length > 1) {
          var chunkSize = Math.ceil(remaining.length / (targetLines - lines.length));
          lines.push(remaining.splice(0, chunkSize).join(" "));
        }
        if (remaining.length) {
          lines.push(remaining.join(" "));
        }
        if (endPunct && lines.length) {
          lines[lines.length - 1] += endPunct;
        }
        body = lines.join("\n");
      }
    }

    return withOpeningQuoteMark(body);
  }

  function readQuoteAuthor(root, overlay, ctx) {
    var eyebrowEl = root.querySelector('[data-gacs-field="eyebrow"]');
    return trim(
      (ctx && (ctx.artistName || ctx.eyebrow)) ||
        overlay.getAttribute("data-gacs-quote-author") ||
        (eyebrowEl && eyebrowEl.textContent)
    );
  }

  function getActiveSlide(root) {
    var track = root.querySelector("[data-gacs-track]");
    if (!track) return null;
    return (
      track.querySelector(".giclee-artist-showcase__slide.is-active") ||
      track.querySelector(".giclee-artist-showcase__slide")
    );
  }

  function readSlideMeta(slide) {
    if (!slide) {
      return { date: "", technique: "", genre: "" };
    }
    return {
      date: slide.getAttribute("data-gacs-created") || "",
      technique: slide.getAttribute("data-gacs-technique") || "",
      genre: slide.getAttribute("data-gacs-genre") || "",
    };
  }

  function getArtists(root) {
    var el = root.querySelector("[data-gacs-artists-json]");
    if (!el) return null;
    try {
      return JSON.parse(el.textContent || "[]");
    } catch (_err) {
      return null;
    }
  }

  function getArtistContext(root, overlay) {
    var artists = getArtists(root);
    if (artists && artists.length) {
      var idx = parseInt(root.getAttribute("data-artist-index"), 10);
      if (!isFinite(idx) || idx < 0) idx = 0;
      return artists[idx] || artists[0] || null;
    }
    return {
      collectionQuote: overlay.getAttribute("data-gacs-collection-quote") || "",
      collectionQuotes: parseCollectionQuotesAttr(overlay),
      artistName: overlay.getAttribute("data-gacs-quote-author") || "",
    };
  }

  function parseCollectionQuotesAttr(overlay) {
    if (!overlay) return [];
    var raw = overlay.getAttribute("data-gacs-collection-quotes");
    if (raw) {
      try {
        var parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) {
          return parsed.map(function (q) {
            return trim(String(q || ""));
          }).filter(Boolean);
        }
      } catch (_e) {
        /* fallback poniżej */
      }
    }
    var single = trim(overlay.getAttribute("data-gacs-collection-quote") || "");
    return single ? [single] : [];
  }

  function getArtistQuotes(ctx, overlay) {
    var list = [];
    if (ctx && ctx.collectionQuotes && ctx.collectionQuotes.length) {
      ctx.collectionQuotes.forEach(function (q) {
        q = trim(String(q || ""));
        if (q) list.push(q);
      });
    }
    if (!list.length && ctx && ctx.collectionQuote) {
      var single = trim(ctx.collectionQuote);
      if (single) list.push(single);
    }
    if (!list.length) {
      list = parseCollectionQuotesAttr(overlay);
    }
    return list;
  }

  var SEEN_QUOTES_STORAGE_KEY = "giclee-gacs-seen-quotes";
  var SEEN_QUOTES_MAX_COLLECTIONS = 80;

  function quoteStorageId(quote) {
    return trim(String(quote || "")).replace(/\s+/g, " ");
  }

  function getCollectionQuoteKey(ctx, artistKey) {
    if (ctx && ctx.handle) return String(ctx.handle);
    if (ctx && ctx.id != null && ctx.id !== "") return "id-" + ctx.id;
    return "idx-" + artistKey;
  }

  function readSeenQuotesStore() {
    try {
      var raw = localStorage.getItem(SEEN_QUOTES_STORAGE_KEY);
      if (!raw) return {};
      var parsed = JSON.parse(raw);
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch (_e) {
      return {};
    }
  }

  function writeSeenQuotesStore(store) {
    try {
      var keys = Object.keys(store);
      if (keys.length > SEEN_QUOTES_MAX_COLLECTIONS) {
        keys.slice(0, keys.length - SEEN_QUOTES_MAX_COLLECTIONS).forEach(function (key) {
          delete store[key];
        });
      }
      localStorage.setItem(SEEN_QUOTES_STORAGE_KEY, JSON.stringify(store));
    } catch (_e) {
      /* prywatny tryb / quota — ignoruj */
    }
  }

  function pruneSeenQuoteIds(seen, quotes) {
    if (!seen || !seen.length) return [];
    var valid = {};
    quotes.forEach(function (quote) {
      valid[quoteStorageId(quote)] = true;
    });
    return seen.filter(function (id) {
      return valid[id];
    });
  }

  function getSeenQuoteIds(collectionKey, quotes) {
    var store = readSeenQuotesStore();
    var seen = store[collectionKey];
    if (!Array.isArray(seen)) return [];
    return pruneSeenQuoteIds(seen, quotes);
  }

  function markQuoteSeen(collectionKey, quoteId) {
    if (!collectionKey || !quoteId) return;
    var store = readSeenQuotesStore();
    var seen = Array.isArray(store[collectionKey]) ? store[collectionKey].slice() : [];
    if (seen.indexOf(quoteId) === -1) seen.push(quoteId);
    store[collectionKey] = seen;
    writeSeenQuotesStore(store);
  }

  function clearSeenQuotes(collectionKey) {
    if (!collectionKey) return;
    var store = readSeenQuotesStore();
    if (!store[collectionKey]) return;
    delete store[collectionKey];
    writeSeenQuotesStore(store);
  }

  function pickRandomFromList(items) {
    if (!items || !items.length) return "";
    if (items.length === 1) return items[0];
    return items[Math.floor(Math.random() * items.length)];
  }

  /** Preferuje cytaty, których użytkownik jeszcze nie widział (localStorage). */
  function pickPreferredQuote(quotes, collectionKey) {
    if (!quotes || !quotes.length) return "";
    if (quotes.length === 1) {
      markQuoteSeen(collectionKey, quoteStorageId(quotes[0]));
      return quotes[0];
    }

    var seen = getSeenQuoteIds(collectionKey, quotes);
    var unseen = quotes.filter(function (quote) {
      return seen.indexOf(quoteStorageId(quote)) === -1;
    });

    if (!unseen.length) {
      clearSeenQuotes(collectionKey);
      unseen = quotes.slice();
    }

    var picked = pickRandomFromList(unseen);
    markQuoteSeen(collectionKey, quoteStorageId(picked));
    return picked;
  }

  function resolveArtistQuote(root, overlay, ctx) {
    var quotes = getArtistQuotes(ctx, overlay);
    if (!quotes.length) return "";
    var artistKey = String(root.getAttribute("data-artist-index") || "0");
    var collectionKey = getCollectionQuoteKey(ctx, artistKey);
    if (
      !root._gacsQuotePick ||
      root._gacsQuotePick.artistKey !== artistKey ||
      !root._gacsQuotePick.quote
    ) {
      root._gacsQuotePick = {
        artistKey: artistKey,
        quote: pickPreferredQuote(quotes, collectionKey),
      };
    }
    return root._gacsQuotePick.quote;
  }

  function updateMeta(overlay, slide) {
    var wrap = overlay.querySelector("[data-gacs-overlay-meta]");
    if (!wrap) return;
    var meta = readSlideMeta(slide);
    var dateEl = wrap.querySelector("[data-gacs-overlay-date]");
    var techEl = wrap.querySelector("[data-gacs-overlay-technique]");
    var genreEl = wrap.querySelector("[data-gacs-overlay-genre]");
    var date = formatDate(meta.date);
    var technique = formatLine(meta.technique);
    var genre = formatLine(meta.genre);

    if (dateEl) {
      dateEl.textContent = date;
      dateEl.hidden = !date;
    }
    if (techEl) {
      techEl.textContent = technique;
      techEl.hidden = !technique;
    }
    if (genreEl) {
      genreEl.textContent = genre;
      genreEl.hidden = !genre;
    }
    wrap.hidden = !(date || technique || genre);
  }

  function updateQuote(overlay, root) {
    var block = overlay.querySelector("[data-gacs-overlay-quote]");
    if (!block) return;
    var ctx = getArtistContext(root, overlay) || {};
    var quoteRaw = resolveArtistQuote(root, overlay, ctx);
    var quote = normalizeQuoteText(quoteRaw);
    var author = readQuoteAuthor(root, overlay, ctx);
    var textEl = block.querySelector(".carousel-quote__text");
    var authorEl = block.querySelector(".carousel-quote__author");

    if (!quote) {
      block.hidden = true;
      if (textEl) textEl.textContent = "";
      if (authorEl) {
        authorEl.textContent = "";
        authorEl.hidden = true;
      }
      return;
    }

    block.hidden = false;
    if (textEl) textEl.textContent = formatQuoteLines(quoteRaw);
    if (authorEl) {
      if (author) {
        authorEl.textContent = "— " + author.toUpperCase();
        authorEl.hidden = false;
      } else {
        authorEl.textContent = "";
        authorEl.hidden = true;
      }
    }
    overlay.setAttribute("data-gacs-collection-quote", quote);
    if (author) overlay.setAttribute("data-gacs-quote-author", author);
  }

  var OVERLAY_HIDE_MS = 680;

  function prefersReducedMotion() {
    return (
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    );
  }

  function isKaruzela2Active() {
    return (
      document.documentElement.getAttribute("data-giclee-karuzela-version") ===
      "Karuzela2"
    );
  }

  function isArtistTransitioning(root) {
    return (
      root.classList.contains("is-artist-transitioning") ||
      root.classList.contains("is-artist-exiting-next") ||
      root.classList.contains("is-artist-exiting-prev") ||
      root.classList.contains("is-artist-entering-next") ||
      root.classList.contains("is-artist-entering-prev")
    );
  }

  function queueOverlayRevealAfterHide(root) {
    root._gacsOverlayRevealQueued = true;
  }

  function tryFinishOverlayArtistTransition(root) {
    if (!root._gacsOverlayRevealQueued) return;
    if (root._gacsOverlayHideInProgress) return;
    root._gacsOverlayRevealQueued = false;
    scheduleOverlayGalleryReveal(root);
  }

  function beginOverlayGalleryHide(root, onComplete) {
    var overlay = root.querySelector("[data-gacs-showcase-overlay]");
    if (!overlay || prefersReducedMotion()) {
      if (onComplete) onComplete();
      return;
    }

    overlay.classList.remove("is-gacs-overlay-reveal-armed");
    if (overlay.classList.contains("is-gacs-overlay-hide-armed")) {
      if (onComplete) onComplete();
      return;
    }

    root._gacsOverlayHideInProgress = true;
    overlay.classList.add("is-gacs-overlay-hide-armed");

    window.setTimeout(function () {
      root._gacsOverlayHideInProgress = false;
      if (onComplete) onComplete();
      tryFinishOverlayArtistTransition(root);
    }, OVERLAY_HIDE_MS);
  }

  function onOverlayArtistGallerySwap(root) {
    if (prefersReducedMotion()) {
      syncOverlay(root);
      return;
    }

    queueOverlayRevealAfterHide(root);

    if (isKaruzela2Active()) {
      if (root._gacsOverlayBgFallbackTimer) {
        window.clearTimeout(root._gacsOverlayBgFallbackTimer);
      }
      root._gacsOverlayBgFallbackTimer = window.setTimeout(function () {
        root._gacsOverlayBgFallbackTimer = 0;
        if (!root._gacsOverlayRevealQueued) return;
        var overlay = root.querySelector("[data-gacs-showcase-overlay]");
        if (
          overlay &&
          !root._gacsOverlayHideInProgress &&
          !overlay.classList.contains("is-gacs-overlay-hide-armed")
        ) {
          beginOverlayGalleryHide(root);
        }
      }, 150);
      return;
    }

    if (!root._gacsOverlayHideInProgress) {
      beginOverlayGalleryHide(root);
    }
  }

  function onKaruzela2ArtistBgEnter(root) {
    if (prefersReducedMotion()) {
      syncOverlay(root);
      return;
    }
    if (root._gacsOverlayBgFallbackTimer) {
      window.clearTimeout(root._gacsOverlayBgFallbackTimer);
      root._gacsOverlayBgFallbackTimer = 0;
    }
    if (root._gacsOverlayHideInProgress) return;

    queueOverlayRevealAfterHide(root);
    beginOverlayGalleryHide(root);
  }

  function clearOverlayTransitionClasses(root, force) {
    if (
      !force &&
      (root._gacsOverlayHideInProgress || root._gacsOverlayRevealQueued)
    ) {
      return;
    }

    var overlay = root.querySelector("[data-gacs-showcase-overlay]");
    if (!overlay) return;
    overlay.classList.remove("is-gacs-overlay-hide-armed", "is-gacs-overlay-reveal-armed");
    root._gacsOverlayRevealQueued = false;
    root._gacsOverlayHideInProgress = false;
  }

  function handleArtistTransitionClasses(root) {
    if (prefersReducedMotion()) return;
    finishOverlayTransitionIfIdle(root);
  }

  function finishOverlayTransitionIfIdle(root) {
    if (isArtistTransitioning(root)) return;
    if (root._gacsOverlayRevealFrame) return;
    if (root._gacsOverlayHideInProgress) return;
    if (root._gacsOverlayRevealQueued) return;

    var overlay = root.querySelector("[data-gacs-showcase-overlay]");
    if (!overlay || overlay.classList.contains("is-gacs-overlay-reveal-armed")) return;

    clearOverlayTransitionClasses(root, true);
  }

  function beginOverlayGalleryReveal(root) {
    var overlay = root.querySelector("[data-gacs-showcase-overlay]");
    if (!overlay || prefersReducedMotion()) {
      syncOverlay(root);
      return;
    }

    overlay.classList.remove("is-gacs-overlay-hide-armed");
    overlay.classList.add("is-gacs-overlay-reveal-armed");
    syncOverlay(root);

    void overlay.offsetHeight;

    window.requestAnimationFrame(function () {
      window.requestAnimationFrame(function () {
        overlay.classList.remove("is-gacs-overlay-reveal-armed");
        finishOverlayTransitionIfIdle(root);
      });
    });
  }

  function scheduleOverlayGalleryReveal(root) {
    if (prefersReducedMotion()) {
      syncOverlay(root);
      return;
    }
    if (root._gacsOverlayRevealFrame) return;
    root._gacsOverlayRevealFrame = window.requestAnimationFrame(function () {
      root._gacsOverlayRevealFrame = 0;
      beginOverlayGalleryReveal(root);
    });
  }

  function syncOverlay(root) {
    var overlay = root.querySelector("[data-gacs-showcase-overlay]");
    if (!overlay) return;
    var slide = getActiveSlide(root);
    updateMeta(overlay, slide);
    updateQuote(overlay, root);

    var meta = overlay.querySelector("[data-gacs-overlay-meta]");
    var quote = overlay.querySelector("[data-gacs-overlay-quote]");
    var showMeta = meta && !meta.hidden;
    var showQuote = quote && !quote.hidden;
    overlay.hidden = !(showMeta || showQuote);
  }

  function bind(root) {
    if (root._gacsOverlayBound) return;
    root._gacsOverlayBound = true;

    var lastArtistIndex = root.getAttribute("data-artist-index");

    var track = root.querySelector("[data-gacs-track]");
    if (track) {
      new MutationObserver(function () {
        if (isArtistTransitioning(root)) {
          onOverlayArtistGallerySwap(root);
          return;
        }
        syncOverlay(root);
      }).observe(track, {
        attributes: true,
        subtree: true,
        attributeFilter: ["class"],
        childList: true,
      });
    }

    new MutationObserver(function () {
      var nextIndex = root.getAttribute("data-artist-index");
      if (nextIndex === lastArtistIndex) return;
      lastArtistIndex = nextIndex;

      if (isArtistTransitioning(root)) {
        onOverlayArtistGallerySwap(root);
        return;
      }

      syncOverlay(root);
    }).observe(root, {
      attributes: true,
      attributeFilter: ["data-artist-index"],
    });

    var eyebrowEl = root.querySelector('[data-gacs-field="eyebrow"]');
    if (eyebrowEl) {
      new MutationObserver(function () {
        if (isArtistTransitioning(root)) return;
        syncOverlay(root);
      }).observe(eyebrowEl, {
        characterData: true,
        childList: true,
        subtree: true,
      });
    }

    root.addEventListener("giclee:karuzela2-artist-bg-enter", function () {
      onKaruzela2ArtistBgEnter(root);
    });

    new MutationObserver(function () {
      handleArtistTransitionClasses(root);
    }).observe(root, {
      attributes: true,
      attributeFilter: ["class"],
    });

    handleArtistTransitionClasses(root);
    syncOverlay(root);
  }

  function init() {
    document.querySelectorAll("[data-gacs-exhibition]").forEach(bind);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
