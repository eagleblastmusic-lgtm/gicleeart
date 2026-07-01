/**
 * Wspólny stan activeAuthor — kolekcja autora (bio + galeria + SEO + URL).
 */
(function (global) {
  "use strict";

  if (global.GicleeActiveAuthor) return;

  var SHOP_TITLE_SUFFIX = " – Giclee Art";
  var listeners = [];
  var artists = [];
  var index = 0;
  var popstateBound = false;

  function getArtist(i) {
    return artists[i] || null;
  }

  function getHandleFromPath(path) {
    var match = String(path || "").match(/\/collections\/([^/?#]+)/i);
    return match ? match[1] : "";
  }

  function titleCaseWords(str) {
    return String(str || "")
      .split(/\s+/)
      .filter(Boolean)
      .map(function (w) {
        return w.charAt(0).toUpperCase() + w.slice(1);
      })
      .join(" ");
  }

  var SURNAME_PARTICLES = {
    da: 1,
    de: 1,
    del: 1,
    della: 1,
    di: 1,
    du: 1,
    van: 1,
    von: 1,
    der: 1,
    den: 1,
    ten: 1,
    ter: 1,
    af: 1,
    av: 1,
    la: 1,
    le: 1,
  };

  function formatCatalogArtistName(raw) {
    var text = String(raw || "").trim();
    if (!text || text.indexOf(", ") === -1) return text;

    var comma = text.indexOf(", ");
    var surname = text.slice(0, comma).trim();
    var rest = text.slice(comma + 2).trim();
    if (!surname || !rest) return text;

    var givenTokens = rest.split(/\s+/).filter(Boolean);
    while (givenTokens.length > 1) {
      var last = givenTokens[givenTokens.length - 1].toLowerCase().replace(/\.$/, "");
      if (!SURNAME_PARTICLES[last]) break;
      surname = givenTokens.pop() + " " + surname;
    }

    return titleCaseWords(surname) + ", " + titleCaseWords(givenTokens.join(" "));
  }

  function normalizeArtist(artist) {
    if (!artist) return artist;
    if (artist.artistName) {
      artist.artistName = formatCatalogArtistName(artist.artistName);
    }
    if (artist.eyebrow && artist.eyebrow.indexOf(", ") >= 0) {
      artist.eyebrow = formatCatalogArtistName(artist.eyebrow);
    }
    return artist;
  }

  function setMeta(attr, name, value) {
    if (value == null || value === "") return;
    var el = document.querySelector('meta[' + attr + '="' + name + '"]');
    if (!el) return;
    el.setAttribute("content", value);
  }

  function updateSeo(artist) {
    if (!artist) return;

    var title = artist.seoTitle || artist.artistName || "";
    if (title) {
      document.title = title + SHOP_TITLE_SUFFIX;
    }

    var desc = artist.seoDescription || "";
    setMeta("name", "description", desc);
    setMeta("property", "og:title", artist.artistName || title);
    setMeta("property", "og:description", desc);

    if (artist.url) {
      var absolute = artist.url.indexOf("http") === 0 ? artist.url : global.location.origin + artist.url;
      setMeta("property", "og:url", absolute);
      var canonical = document.querySelector('link[rel="canonical"]');
      if (canonical) canonical.href = absolute;
    }
  }

  function notify(evt) {
    listeners.forEach(function (fn) {
      try {
        fn(evt);
      } catch (err) {}
    });
  }

  function bindPopstate() {
    if (popstateBound) return;
    popstateBound = true;
    global.addEventListener("popstate", function () {
      if (!artists.length) return;
      var handle = getHandleFromPath(global.location.pathname);
      if (!handle) return;
      var idx = -1;
      for (var i = 0; i < artists.length; i++) {
        if (artists[i].handle === handle) {
          idx = i;
          break;
        }
      }
      if (idx >= 0 && idx !== index) {
        setIndex(idx, {
          direction: index < idx ? 1 : -1,
          pushState: false,
          source: "popstate",
        });
      }
    });
  }

  function setIndex(newIndex, opts) {
    opts = opts || {};
    if (newIndex < 0 || newIndex >= artists.length) return false;
    if (newIndex === index) return false;

    var prev = index;
    var direction =
      opts.direction != null ? (opts.direction >= 0 ? 1 : -1) : newIndex > prev ? 1 : -1;

    index = newIndex;
    var artist = getArtist(index);

    updateSeo(artist);

    if (opts.pushState && artist && artist.url) {
      global.history.pushState({ gacsArtist: index }, "", artist.url);
    }

    notify({
      artist: artist,
      index: index,
      prevIndex: prev,
      direction: direction,
      source: opts.source || "setIndex",
      pushState: !!opts.pushState,
    });

    return true;
  }

  global.GicleeActiveAuthor = {
    init: function (list, startIndex) {
      artists = (list || []).map(function (a) {
        return normalizeArtist(Object.assign({}, a));
      });
      index = Math.max(0, Math.min(startIndex || 0, artists.length - 1));
      bindPopstate();
    },

    subscribe: function (fn) {
      listeners.push(fn);
      return function () {
        var pos = listeners.indexOf(fn);
        if (pos >= 0) listeners.splice(pos, 1);
      };
    },

    setIndex: setIndex,

    findIndexByHandle: function (handle) {
      for (var i = 0; i < artists.length; i++) {
        if (artists[i].handle === handle) return i;
      }
      return -1;
    },

    getHandleFromPath: getHandleFromPath,

    get index() {
      return index;
    },

    get artists() {
      return artists;
    },

    get activeAuthor() {
      return getArtist(index);
    },

    formatCatalogArtistName: formatCatalogArtistName,
  };
})(window);
