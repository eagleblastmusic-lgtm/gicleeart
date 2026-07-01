/**
 * Karuzela — router wersji «Wybrane dzieła»:
 * - Karuzela1 / Karuzela2 (zachowanie JS + tło produktu)
 * - V1 / V2 / V3 (wygląd tła sekcji karuzeli)
 *
 * Persystencja: localStorage + opcjonalne parametry URL.
 */
(function () {
  "use strict";

  var STORAGE_KEY = "giclee-carousel-version";
  var LOOK_STORAGE_KEY = "giclee-showcase-look";
  var VALID = { Karuzela1: true, Karuzela2: true };
  var LOOK_VALID = { V1: true, V2: true, V3: true };

  function readUrlParams() {
    try {
      var params = new URLSearchParams(window.location.search);
      var version = params.get("giclee_karuzela");
      var look = params.get("giclee_showcase_look");
      var changed = false;

      if (VALID[version]) {
        try {
          localStorage.setItem(STORAGE_KEY, version);
        } catch (_e) {}
        params.delete("giclee_karuzela");
        changed = true;
      }

      if (LOOK_VALID[look]) {
        try {
          localStorage.setItem(LOOK_STORAGE_KEY, look);
        } catch (_e) {}
        params.delete("giclee_showcase_look");
        changed = true;
      }

      if (changed) {
        var qs = params.toString();
        var clean =
          window.location.pathname +
          (qs ? "?" + qs : "") +
          window.location.hash;
        window.history.replaceState({}, "", clean);
      }

      return {
        version: VALID[version] ? version : null,
        look: LOOK_VALID[look] ? look : null,
      };
    } catch (_e) {
      return { version: null, look: null };
    }
  }

  function readConfigDefault() {
    try {
      var fromConfig = window.__GICLEE_CAROUSEL_DEFAULT;
      if (VALID[fromConfig]) return fromConfig;
    } catch (_e) {}
    return null;
  }

  function readLookConfigDefault() {
    try {
      var fromConfig = window.__GICLEE_SHOWCASE_LOOK_DEFAULT;
      if (LOOK_VALID[fromConfig]) return fromConfig;
    } catch (_e) {}
    return null;
  }

  function readStoredVersion() {
    try {
      var saved = localStorage.getItem(STORAGE_KEY);
      if (VALID[saved]) return saved;
    } catch (_e) {}
    return null;
  }

  function readStoredLook() {
    try {
      var saved = localStorage.getItem(LOOK_STORAGE_KEY);
      if (LOOK_VALID[saved]) return saved;
    } catch (_e) {}
    return null;
  }

  function resolveVersion(fromUrl) {
    if (fromUrl) return fromUrl;
    var fromStorage = readStoredVersion();
    if (fromStorage) return fromStorage;
    var fromConfig = readConfigDefault();
    if (fromConfig) return fromConfig;
    return "Karuzela1";
  }

  function resolveShowcaseLook(fromUrl) {
    if (fromUrl) return fromUrl;
    var fromStorage = readStoredLook();
    if (fromStorage) return fromStorage;
    var fromConfig = readLookConfigDefault();
    if (fromConfig) return fromConfig;
    return "V2";
  }

  function applyShowcaseLook(look) {
    try {
      document.documentElement.setAttribute("data-giclee-showcase-look", look);
    } catch (_e) {}
  }

  function assetConfig() {
    return (
      window.__GICLEE_KARUZELA_ASSETS || {
        karuzela1: "",
        karuzela2: "",
        karuzela2Css: "",
      }
    );
  }

  function loadStylesheet(href) {
    if (!href) return;
    var existing = document.querySelector(
      'link[data-giclee-karuzela-css="Karuzela2"]'
    );
    if (existing) return;
    var bust =
      href.indexOf("?") === -1
        ? "?v=karuzela2-css-nozoom-20260628"
        : "&v=karuzela2-css-nozoom-20260628";
    var link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = href + bust;
    link.setAttribute("data-giclee-karuzela-css", "Karuzela2");
    document.head.appendChild(link);
  }

  function loadScript(src, onLoad) {
    var bust =
      src.indexOf("?") === -1
        ? "?v=karuzela2-text-header-sync-20260628"
        : "&v=karuzela2-text-header-sync-20260628";
    var script = document.createElement("script");
    script.src = src + bust;
    script.defer = true;
    script.onload = function () {
      if (onLoad) onLoad();
    };
    script.onerror = function () {
      console.warn("[Karuzela] Nie udało się załadować skryptu:", src);
    };
    document.head.appendChild(script);
  }

  var urlParams = readUrlParams();
  var version = resolveVersion(urlParams.version);
  var showcaseLook = resolveShowcaseLook(urlParams.look);
  var assets = assetConfig();

  try {
    document.documentElement.setAttribute("data-giclee-karuzela-version", version);
  } catch (_e) {}

  applyShowcaseLook(showcaseLook);

  window.__GICLEE_KARUZELA_VERSION = version;
  window.__GICLEE_SHOWCASE_LOOK = showcaseLook;

  window.GicleeKaruzela = {
    STORAGE_KEY: STORAGE_KEY,
    LOOK_STORAGE_KEY: LOOK_STORAGE_KEY,
    getVersion: function () {
      return window.__GICLEE_KARUZELA_VERSION || resolveVersion(null);
    },
    getShowcaseLook: function () {
      return window.__GICLEE_SHOWCASE_LOOK || resolveShowcaseLook(null);
    },
    setVersion: function (next) {
      if (!VALID[next]) return;
      try {
        localStorage.setItem(STORAGE_KEY, next);
      } catch (_e) {}
      window.location.reload();
    },
    setShowcaseLook: function (next) {
      if (!LOOK_VALID[next]) return;
      try {
        localStorage.setItem(LOOK_STORAGE_KEY, next);
      } catch (_e) {}
      window.location.reload();
    },
  };

  if (version === "Karuzela2") {
    loadStylesheet(assets.karuzela2Css);
    loadScript(assets.karuzela2);
  } else {
    loadScript(assets.karuzela1);
  }
})();
