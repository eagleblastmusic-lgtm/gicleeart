/**
 * Analityka ruchu — collect (pixel) + export (sync do GicleeApp).
 */

const STANDARD_EVENTS = new Set([
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
  "giclee_app:frame_config_started",
  "giclee_app:frame_size_selected",
  "giclee_app:frame_color_selected",
  "giclee_app:passepartout_selected",
  "giclee_app:print_size_selected",
  "giclee_app:product_customized",
  "giclee_app:price_calculated",
  "giclee_app:cta_clicked",
]);

const BOT_UA =
  /googlebot|bingbot|yandex|baiduspider|duckduckbot|slurp|facebot|facebookexternalhit|twitterbot|linkedinbot|pinterest|semrush|ahrefs|petalbot|bytespider|gptbot|claudebot|headlesschrome|lighthouse|chrome-lighthouse|pagespeed|pingdom|uptimerobot|bot|crawler|spider|preview|prerender|phantomjs|selenium/i;

const PAID_MEDIUMS = /cpc|ppc|paid|ads|display|retarget/i;
const EMAIL_MEDIUMS = /email|newsletter|mail/i;
const SOCIAL_HOSTS =
  /facebook\.com|fb\.com|instagram\.com|tiktok\.com|twitter\.com|x\.com|linkedin\.com|pinterest\.|youtube\.com|t\.co/i;
const SEARCH_HOSTS =
  /google\.|bing\.com|duckduckgo\.|yahoo\.|ecosia\.|yandex\./i;

const rateBuckets = new Map();
const RATE_LIMIT = 120;

function json(data, status, extraHeaders) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      ...(extraHeaders || {}),
    },
  });
}

function analyticsCors(origin, env, extraHeaders) {
  // Secret w nagłówku (nie cookies) — * dla sandboxu Shopify (origin często null/inny)
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-Analytics-Secret",
    "Access-Control-Max-Age": "86400",
    ...(extraHeaders || {}),
  };
}

export { analyticsCors };

function timingSafeEqual(a, b) {
  a = String(a || "");
  b = String(b || "");
  if (a.length !== b.length) return false;
  let out = 0;
  for (let i = 0; i < a.length; i++) out |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return out === 0;
}

function getSecret(request, body) {
  return (
    request.headers.get("X-Analytics-Secret") ||
    request.headers.get("x-analytics-secret") ||
    (body && body.secret) ||
    ""
  ).trim();
}

function verifySecret(provided, env) {
  const expected = (env.ANALYTICS_COLLECT_SECRET || "").trim();
  if (!expected) return { ok: false, error: "ANALYTICS_COLLECT_SECRET not configured on Worker" };
  if (!timingSafeEqual(provided, expected)) return { ok: false, error: "Invalid secret" };
  return { ok: true };
}

async function hashId(value, env, prefix = "v") {
  const salt = (env.ANALYTICS_HASH_SALT || "giclee-analytics").trim();
  const data = new TextEncoder().encode(salt + String(value || ""));
  const buf = await crypto.subtle.digest("SHA-256", data);
  const hex = [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
  return `${prefix}_${hex.slice(0, 32)}`;
}

function classifySource(referrer = "", utmSource = "", utmMedium = "") {
  const medium = (utmMedium || "").toLowerCase();
  const source = (utmSource || "").toLowerCase();
  const ref = (referrer || "").trim();
  if (medium && PAID_MEDIUMS.test(medium)) return "paid";
  if (medium && EMAIL_MEDIUMS.test(medium)) return "email";
  if (medium === "social" || (source && SOCIAL_HOSTS.test(source))) return "social";
  if (medium === "organic" || medium === "seo") return "organic_search";
  if (ref) {
    try {
      const host = new URL(ref).hostname.toLowerCase();
      if (!host) return "direct";
      if (SEARCH_HOSTS.test(host)) return "organic_search";
      if (SOCIAL_HOSTS.test(host)) return "social";
      if (host.includes("gicleeart")) return "direct";
      return "referral";
    } catch (_) {
      return "direct";
    }
  }
  if (!source && !medium) return "direct";
  if (source && SEARCH_HOSTS.test(source)) return "organic_search";
  if (source) return "referral";
  return "unknown";
}

function isBotUA(ua) {
  ua = (ua || "").trim();
  if (!ua || ua.length < 12) return true;
  return BOT_UA.test(ua);
}

function consentOk(status) {
  const s = (status || "").toLowerCase();
  if (!s) return true;
  if (["denied", "reject", "rejected", "opt_out", "no"].includes(s)) return false;
  return true;
}

function checkRate(ipKey) {
  const now = Date.now();
  const window = rateBuckets.get(ipKey) || [];
  const fresh = window.filter((t) => now - t < 60000);
  if (fresh.length >= RATE_LIMIT) return false;
  fresh.push(now);
  rateBuckets.set(ipKey, fresh);
  return true;
}

function shopAllowed(payload, env, origin) {
  const allowed = (env.ANALYTICS_ALLOWED_SHOP_DOMAIN || "gicleeart.eu").toLowerCase();
  const candidates = new Set();
  if (payload.shop_domain) candidates.add(String(payload.shop_domain).toLowerCase());
  if (payload.url) {
    try {
      candidates.add(new URL(payload.url).hostname.toLowerCase());
    } catch (_) {}
  }
  if (origin) {
    try {
      candidates.add(new URL(origin).hostname.toLowerCase());
    } catch (_) {}
  }
  for (const c of candidates) {
    if (!c) continue;
    if (c.includes(allowed) || c.endsWith(".myshopify.com")) return true;
  }
  return candidates.size === 0;
}

function sanitizeMeta(meta) {
  if (!meta || typeof meta !== "object") return "{}";
  const blocked = /email|phone|address|password|token|secret/i;
  const out = {};
  for (const [k, v] of Object.entries(meta)) {
    if (blocked.test(k)) continue;
    if (typeof v === "string" || typeof v === "number" || typeof v === "boolean" || v === null) {
      out[String(k).slice(0, 64)] = v;
    }
  }
  let raw = JSON.stringify(out);
  if (raw.length > 4096) raw = raw.slice(0, 4096);
  return raw;
}

function uuid() {
  return crypto.randomUUID();
}

function normalizeTs(ts) {
  if (!ts) return new Date().toISOString();
  try {
    const d = new Date(ts);
    if (Number.isNaN(d.getTime())) return new Date().toISOString();
    return d.toISOString();
  } catch (_) {
    return new Date().toISOString();
  }
}

function optFloat(v) {
  if (v === null || v === undefined || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

export async function handleAnalyticsCollect(request, env, ctx) {
  const origin = request.headers.get("Origin") || "";
  const cors = analyticsCors(origin, env);

  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: cors });
  }

  if (!env.ANALYTICS_DB) {
    return json({ ok: false, error: "D1 ANALYTICS_DB not bound" }, 503, cors);
  }

  let body;
  try {
    body = await request.json();
  } catch (_) {
    return json({ ok: false, error: "Invalid JSON" }, 400, cors);
  }

  const secretCheck = verifySecret(getSecret(request, body), env);
  if (!secretCheck.ok) {
    return json({ ok: false, error: secretCheck.error }, secretCheck.error.includes("not configured") ? 503 : 401, cors);
  }

  const eventName = String(body.event_name || "").trim();
  if (!eventName) return json({ ok: false, error: "event_name required" }, 400, cors);
  if (!STANDARD_EVENTS.has(eventName)) {
    return json({ ok: false, error: `Unknown event: ${eventName}` }, 400, cors);
  }

  if (!consentOk(body.consent_status)) {
    return json({ ok: true, skipped: true, reason: "consent_denied" }, 200, cors);
  }

  if (!shopAllowed(body, env, origin)) {
    return json({ ok: false, error: "Shop domain not allowed" }, 403, cors);
  }

  const ip = request.headers.get("CF-Connecting-IP") || "";
  const ipKey = ip ? await hashId(ip, env, "ip") : "unknown";
  if (!checkRate(ipKey)) {
    return json({ ok: false, error: "Rate limit exceeded" }, 429, cors);
  }

  const eventId = String(body.event_id || uuid()).trim();
  const existing = await env.ANALYTICS_DB.prepare(
    "SELECT 1 FROM analytics_events WHERE event_id = ? LIMIT 1"
  )
    .bind(eventId)
    .first();
  if (existing) {
    return json({ ok: true, duplicate: true, event_id: eventId }, 200, cors);
  }

  const visitorRaw = String(body.visitor_id || body.client_id || uuid()).trim();
  const sessionId = String(body.session_id || visitorRaw).trim();
  const visitorHash = await hashId(visitorRaw, env, "v");
  const ua = String(body.user_agent || request.headers.get("User-Agent") || "");
  const bot = isBotUA(ua) || !eventName;

  let country = String(body.country || request.cf?.country || "").toUpperCase().slice(0, 2);
  if (!country || country === "XX") country = "unknown";

  let path = String(body.path || "").trim();
  if (!path && body.url) {
    try {
      path = new URL(body.url).pathname;
    } catch (_) {}
  }

  const utmSource = String(body.utm_source || "").trim();
  const utmMedium = String(body.utm_medium || "").trim();
  const sourceBucket = classifySource(body.referrer || "", utmSource, utmMedium);
  const createdAt = normalizeTs(body.timestamp);
  const meta = body.metadata && typeof body.metadata === "object" ? { ...body.metadata } : {};
  if (ipKey && ipKey !== "unknown") meta.ip_hash = ipKey;
  const eventType = eventName.startsWith("giclee_app:") ? "custom" : "standard";

  await env.ANALYTICS_DB.prepare(
    `INSERT INTO analytics_events (
      event_id, event_name, event_type, shopify_event_id,
      visitor_id_hash, session_id, customer_id_hash, shopify_customer_id_hash,
      shopify_order_id, shopify_product_id, shopify_variant_id, product_title,
      collection_id, url, path, page_title, referrer,
      utm_source, utm_medium, utm_campaign, utm_content, utm_term,
      device_type, browser, os, country, region, language, currency,
      cart_value, checkout_value, order_value, quantity, metadata_json,
      consent_status, bot_suspected, source_bucket, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
  )
    .bind(
      eventId,
      eventName,
      eventType,
      meta.shopify_event_id || null,
      visitorHash,
      sessionId,
      null,
      null,
      body.shopify_order_id || body.order_id || null,
      body.shopify_product_id || body.product_id || null,
      body.shopify_variant_id || body.variant_id || null,
      body.product_title || null,
      body.collection_id || null,
      body.url || null,
      path || null,
      body.page_title || null,
      body.referrer || null,
      utmSource || null,
      utmMedium || null,
      body.utm_campaign || null,
      body.utm_content || null,
      body.utm_term || null,
      body.device_type || null,
      body.browser || null,
      body.os || null,
      country,
      body.region || null,
      body.language || null,
      body.currency || null,
      optFloat(body.cart_value),
      optFloat(body.checkout_value),
      optFloat(body.order_value),
      meta.quantity != null ? Number(meta.quantity) : null,
      sanitizeMeta(meta),
      body.consent_status || null,
      bot ? 1 : 0,
      sourceBucket,
      createdAt
    )
    .run();

  return json({ ok: true, event_id: eventId, bot_suspected: bot }, 200, cors);
}

export async function handleAnalyticsExport(request, env) {
  const cors = analyticsCors(request.headers.get("Origin") || "", env);
  if (!env.ANALYTICS_DB) {
    return json({ ok: false, error: "D1 not configured" }, 503, cors);
  }

  const secretCheck = verifySecret(getSecret(request, null), env);
  if (!secretCheck.ok) {
    return json({ ok: false, error: secretCheck.error }, 401, cors);
  }

  const url = new URL(request.url);
  const since = url.searchParams.get("since") || "1970-01-01T00:00:00.000Z";
  const limit = Math.min(parseInt(url.searchParams.get("limit") || "5000", 10), 10000);

  const { results } = await env.ANALYTICS_DB.prepare(
    `SELECT * FROM analytics_events
     WHERE created_at >= ? AND bot_suspected = 0
     ORDER BY created_at ASC LIMIT ?`
  )
    .bind(since, limit)
    .all();

  return json({ ok: true, events: results || [], count: (results || []).length }, 200, cors);
}

export async function handleAnalyticsPurge(request, env) {
  const cors = analyticsCors(request.headers.get("Origin") || "", env);
  if (!env.ANALYTICS_DB) {
    return json({ ok: false, error: "D1 not configured" }, 503, cors);
  }

  const secretCheck = verifySecret(getSecret(request, null), env);
  if (!secretCheck.ok) {
    return json({ ok: false, error: secretCheck.error }, 401, cors);
  }

  const url = new URL(request.url);
  const days = Math.max(30, parseInt(url.searchParams.get("days") || "90", 10));
  const cutoff = new Date(Date.now() - days * 86400000).toISOString();

  const result = await env.ANALYTICS_DB.prepare(
    "DELETE FROM analytics_events WHERE created_at < ?"
  )
    .bind(cutoff)
    .run();

  return json(
    {
      ok: true,
      deleted: result.meta?.changes || 0,
      cutoff,
      retention_days: days,
    },
    200,
    cors
  );
}

export async function handleAnalyticsStats(request, env) {
  const cors = analyticsCors(request.headers.get("Origin") || "", env);
  if (!env.ANALYTICS_DB) {
    return json({ ok: true, analytics: false, message: "D1 not bound" }, 200, cors);
  }

  const total = await env.ANALYTICS_DB.prepare(
    "SELECT COUNT(1) AS c FROM analytics_events"
  ).first();
  const last = await env.ANALYTICS_DB.prepare(
    "SELECT MAX(created_at) AS m FROM analytics_events"
  ).first();
  const bots = await env.ANALYTICS_DB.prepare(
    "SELECT COUNT(1) AS c FROM analytics_events WHERE bot_suspected = 1"
  ).first();

  const todayStart = new Date();
  todayStart.setUTCHours(0, 0, 0, 0);
  const todayEvents = await env.ANALYTICS_DB.prepare(
    "SELECT COUNT(1) AS c FROM analytics_events WHERE created_at >= ?"
  )
    .bind(todayStart.toISOString())
    .first();

  return json(
    {
      ok: true,
      analytics: true,
      total_events: total?.c || 0,
      events_today: todayEvents?.c || 0,
      bot_events: bots?.c || 0,
      last_event_at: last?.m || null,
      collect_url: `${new URL(request.url).origin}/api/analytics/collect`,
    },
    200,
    cors
  );
}
