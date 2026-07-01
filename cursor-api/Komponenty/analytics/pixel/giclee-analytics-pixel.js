/**

 * GicleeArt — Custom Pixel (Shopify Customer Events)

 *

 * INSTALACJA:

 * 1. Shopify Admin → Ustawienia → Dane klienta → Pixeli klienta → Dodaj pixel niestandardowy

 * 2. Skopiuj kod z zakładki Konfiguracja w dashboardzie (URL + secret z .env)

 * 3. Zapisz pixel — po każdej aktualizacji kodu wklej ponownie w Shopify

 *

 * Custom Pixel działa w sandboxie Shopify: używamy event.context (nie window.location)

 * oraz fetch + keepalive (sendBeacon z JSON często nie wysyła cross-origin).

 */

(function () {

  "use strict";



  // === KONFIGURACJA — wklej z dashboardu (Konfiguracja) ===

  var COLLECT_URL = "https://giclee-mockup-orders.eagleblastmusic.workers.dev/api/analytics/collect";

  var COLLECT_SECRET = "TWOJ_ANALYTICS_COLLECT_SECRET";

  var SHOP_DOMAIN = "gicleeart.eu";



  var SESSION_KEY = "giclee_sid";

  var VISITOR_KEY = "giclee_vid";

  var _sessionId = "";



  function uuid() {

    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {

      var r = (Math.random() * 16) | 0;

      var v = c === "x" ? r : (r & 0x3) | 0x8;

      return v.toString(16);

    });

  }



  function eventContext(event) {

    return (event && event.context) || {};

  }



  function pageUrl(event) {

    var ctx = eventContext(event);

    var doc = ctx.document || {};

    var loc = doc.location || {};

    if (loc.href) return String(loc.href);

    try {

      if (typeof window !== "undefined" && window.location && window.location.href) {

        return String(window.location.href);

      }

    } catch (e) {}

    return "https://" + SHOP_DOMAIN + "/";

  }



  function pagePath(url) {

    try {

      return new URL(url).pathname || "/";

    } catch (e) {

      return "/";

    }

  }



  function getVisitorId(event) {

    if (event && event.clientId) return String(event.clientId);

    try {

      var v = localStorage.getItem(VISITOR_KEY);

      if (!v) {

        v = uuid();

        localStorage.setItem(VISITOR_KEY, v);

      }

      return v;

    } catch (e) {

      return uuid();

    }

  }



  function getSessionId(event) {

    if (_sessionId) return _sessionId;

    try {

      var s = sessionStorage.getItem(SESSION_KEY);

      if (!s) {

        s = uuid();

        sessionStorage.setItem(SESSION_KEY, s);

      }

      _sessionId = s;

      return s;

    } catch (e) {

      _sessionId = uuid();

      return _sessionId;

    }

  }



  function parseUtm(url) {

    try {

      var u = new URL(url);

      return {

        utm_source: u.searchParams.get("utm_source") || "",

        utm_medium: u.searchParams.get("utm_medium") || "",

        utm_campaign: u.searchParams.get("utm_campaign") || "",

        utm_content: u.searchParams.get("utm_content") || "",

        utm_term: u.searchParams.get("utm_term") || "",

      };

    } catch (e) {

      return {};

    }

  }



  function consentStatus() {

    try {

      if (typeof init !== "undefined" && init.customerPrivacy) {

        var cp = init.customerPrivacy;

        if (cp.analyticsProcessingAllowed && !cp.analyticsProcessingAllowed()) {

          return "denied";

        }

        return "granted";

      }

      if (typeof window !== "undefined" && window.Shopify && window.Shopify.customerPrivacy) {

        var wcp = window.Shopify.customerPrivacy;

        if (wcp.analyticsProcessingAllowed && !wcp.analyticsProcessingAllowed()) {

          return "denied";

        }

      }

    } catch (e) {}

    return "granted";

  }



  function deviceType(event) {

    var ctx = eventContext(event);

    var w = 0;

    try {

      w =

        (ctx.window && ctx.window.innerWidth) ||

        (typeof window !== "undefined" && window.innerWidth) ||

        0;

    } catch (e) {}

    if (w < 768) return "mobile";

    if (w < 1024) return "tablet";

    return "desktop";

  }



  function userAgent(event) {

    var ctx = eventContext(event);

    try {

      return (

        (ctx.navigator && ctx.navigator.userAgent) ||

        (typeof navigator !== "undefined" && navigator.userAgent) ||

        ""

      );

    } catch (e) {

      return "";

    }

  }



  function language(event) {

    var ctx = eventContext(event);

    try {

      return (

        (ctx.navigator && ctx.navigator.language) ||

        (typeof navigator !== "undefined" && navigator.language) ||

        ""

      );

    } catch (e) {

      return "";

    }

  }



  function normalizeProductId(raw) {

    if (!raw) return "";

    var s = String(raw);

    var m = s.match(/Product\/(\d+)/i);

    if (m) return m[1];

    return s.replace(/\D/g, "") || s;

  }



  function sendEvent(payload) {

    if (!COLLECT_URL || COLLECT_URL.indexOf("TWOJ-") >= 0) return;

    if (!COLLECT_SECRET || COLLECT_SECRET.indexOf("TWOJ") >= 0) return;

    payload.secret = COLLECT_SECRET;

    var body = JSON.stringify(payload);

    fetch(COLLECT_URL, {

      method: "POST",

      headers: {

        "Content-Type": "application/json",

        "X-Analytics-Secret": COLLECT_SECRET,

      },

      body: body,

      keepalive: true,

      mode: "cors",

    }).catch(function () {});

  }



  function basePayload(eventName, event) {

    var url = pageUrl(event);

    var utm = parseUtm(url);

    var ctx = eventContext(event);

    var doc = ctx.document || {};

    return {

      event_id: (event && event.id) || uuid(),

      event_name: eventName,

      timestamp: (event && event.timestamp) || new Date().toISOString(),

      visitor_id: getVisitorId(event),

      session_id: getSessionId(event),

      url: url,

      path: pagePath(url),

      page_title: (doc.title || "") + "",

      referrer: (doc.referrer || "") + "",

      utm_source: utm.utm_source,

      utm_medium: utm.utm_medium,

      utm_campaign: utm.utm_campaign,

      utm_content: utm.utm_content,

      utm_term: utm.utm_term,

      shop_domain: SHOP_DOMAIN,

      device_type: deviceType(event),

      user_agent: userAgent(event),

      language: language(event),

      consent_status: consentStatus(),

    };

  }



  function mapShopifyEvent(event) {

    if (!event || !event.name) return;

    var name = event.name;

    var data = event.data || {};

    var payload = basePayload(name, event);

    payload.metadata = { shopify_event_id: event.id };



    if (data.productVariant) {

      var pv = data.productVariant;

      payload.shopify_product_id = normalizeProductId(

        (pv.product && pv.product.id) || pv.productId || ""

      );

      payload.shopify_variant_id = normalizeProductId(pv.id || "");

      payload.product_title = (pv.product && pv.product.title) || pv.title || "";

    }

    if (data.cartLine) {

      var cl = data.cartLine;

      payload.shopify_variant_id = normalizeProductId(cl.merchandise && cl.merchandise.id);

      payload.shopify_product_id = normalizeProductId(

        cl.merchandise && cl.merchandise.product && cl.merchandise.product.id

      );

      payload.quantity = cl.quantity;

    }

    if (data.checkout) {

      var co = data.checkout;

      payload.checkout_value = co.totalPrice && co.totalPrice.amount;

      payload.currency = co.currencyCode || (co.totalPrice && co.totalPrice.currencyCode);

      payload.shopify_order_id = co.order && co.order.id;

    }

    if (data.collection) {

      payload.collection_id = String(data.collection.id || "");

    }

    if (data.searchResult) {

      payload.metadata.search_query = data.searchResult.query || "";

    }

    sendEvent(payload);

  }



  var STANDARD = [

    "page_viewed",

    "product_viewed",

    "collection_viewed",

    "search_submitted",

    "product_added_to_cart",

    "product_removed_from_cart",

    "cart_viewed",

    "checkout_started",

    "checkout_contact_info_submitted",

    "checkout_shipping_info_submitted",

    "payment_info_submitted",

    "checkout_completed",

  ];



  STANDARD.forEach(function (ev) {

    analytics.subscribe(ev, function (event) {

      try {

        mapShopifyEvent(event);

      } catch (e) {}

    });

  });



  var CUSTOM = [

    "giclee_app:frame_config_started",

    "giclee_app:frame_size_selected",

    "giclee_app:frame_color_selected",

    "giclee_app:passepartout_selected",

    "giclee_app:print_size_selected",

    "giclee_app:product_customized",

    "giclee_app:price_calculated",

    "giclee_app:cta_clicked",

  ];



  CUSTOM.forEach(function (ev) {

    analytics.subscribe(ev, function (event) {

      try {

        mapShopifyEvent(event);

      } catch (e) {}

    });

  });

})();


