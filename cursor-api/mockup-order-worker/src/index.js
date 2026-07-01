/**
 * Cloudflare Worker: upload zdjęć z mockupu (R2) + mail z linkami po opłaceniu zamówienia
 * + analityka ruchu (D1 collect/export).
 */

import {
  handleAnalyticsCollect,
  handleAnalyticsExport,
  handleAnalyticsStats,
  handleAnalyticsPurge,
  analyticsCors,
} from "./analytics.js";

const MAX_ORIGINAL_BYTES = 50 * 1024 * 1024;
const MAX_ORIGINAL_FULL_BYTES = 50 * 1024 * 1024;
const MAX_PREVIEW_BYTES = 8 * 1024 * 1024;

function corsHeaders(origin, env) {
  const allowed = (env.ALLOWED_ORIGINS || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  const ok = origin && allowed.includes(origin);
  return {
    "Access-Control-Allow-Origin": ok ? origin : allowed[0] || "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
  };
}

function json(data, status, extraHeaders) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      ...(extraHeaders || {}),
    },
  });
}

function publicUrl(env, key) {
  const base = (env.PUBLIC_BASE_URL || "").replace(/\/$/, "");
  const encoded = key
    .split("/")
    .map((part) => encodeURIComponent(part))
    .join("/");
  return `${base}/${encoded}`;
}

function extFromType(type, fallback) {
  const map = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/heic": "heic",
    "image/heif": "heif",
  };
  return map[(type || "").toLowerCase()] || fallback || "jpg";
}

function isUuid(s) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
    String(s || "")
  );
}

function pickBestOriginal(meta) {
  if (!meta) return { url: null, label: "Oryginał zdjęcia klienta (max. jakość)" };
  const fullUrl = meta.originalFullUrl || null;
  const rawUrl = meta.originalUrl || null;
  const fullBytes = meta.originalFullBytes || 0;
  const rawBytes = meta.originalBytes || 0;

  if (fullUrl && rawUrl) {
    if (fullBytes > rawBytes * 1.05) {
      return { url: fullUrl, label: "Oryginał zdjęcia klienta (max. jakość, JPEG pełna rozdz.)" };
    }
    if (rawBytes > fullBytes * 1.05) {
      return {
        url: rawUrl,
        label: `Plik źródłowy od klienta (${meta.originalName || "bez kompresji w przeglądarce"})`,
      };
    }
    if (/heic|heif/i.test(meta.originalName || "") || /heic|heif/i.test(dims.originalType || "")) {
      return { url: fullUrl, label: "Oryginał zdjęcia klienta (max. jakość, z HEIC)" };
    }
    return { url: fullUrl || rawUrl, label: "Oryginał zdjęcia klienta (max. jakość)" };
  }
  return {
    url: fullUrl || rawUrl,
    label: "Oryginał zdjęcia klienta (max. jakość)",
  };
}

async function verifyShopifyHmac(request, secret, rawBody) {
  if (!secret) return false;
  const hmac = request.headers.get("X-Shopify-Hmac-Sha256") || "";
  if (!hmac) return false;
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(rawBody));
  const computed = btoa(String.fromCharCode(...new Uint8Array(sig)));
  return computed === hmac;
}

function escapeHtml(s) {
  return String(s || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function isPolishOrder(order) {
  const locale = (order.customer_locale || order.client_details?.accept_language || "")
    .toLowerCase()
    .split(",")[0]
    .trim();
  if (locale.startsWith("pl")) return true;

  const countries = [
    order.shipping_address?.country_code,
    order.shipping_address?.country,
    order.billing_address?.country_code,
    order.billing_address?.country,
  ]
    .filter(Boolean)
    .map((c) => String(c).toUpperCase());

  if (countries.some((c) => c === "PL" || c === "POLAND" || c === "POLSKA")) return true;
  if (countries.length) return false;

  return true;
}

function resolveResendFrom(order, env) {
  const pl = (env.RESEND_FROM_PL || "Giclee Art <zamowienia@gicleeart.eu>").trim();
  const intl = (env.RESEND_FROM_INTL || "Giclee Art <orders@gicleeart.eu>").trim();
  const fallback = (env.RESEND_FROM || pl).trim();
  if (isPolishOrder(order)) return pl;
  return intl || fallback;
}

async function sendMerchantEmail(env, { subject, html, from }) {
  const apiKey = env.RESEND_API_KEY;
  if (!apiKey) {
    return { ok: false, error: "Brak RESEND_API_KEY w Workerze (wrangler secret put RESEND_API_KEY)" };
  }
  const to = (env.MERCHANT_EMAIL || "gicleeartpl@gmail.com").trim();
  const fromAddr = (from || env.RESEND_FROM || "Giclee Art <zamowienia@gicleeart.eu>").trim();
  const res = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: fromAddr,
      to: [to],
      subject,
      html,
    }),
  });
  const text = await res.text();
  if (!res.ok) {
    console.error("Resend error", res.status, text);
    let hint = "";
    if (
      fromAddr.includes("onboarding@resend.dev") &&
      (text.includes("only send testing emails") || text.includes("verify a domain"))
    ) {
      hint =
        " Z onboarding@resend.dev Resend wysyla tylko na e-mail konta Resend. Zweryfikuj domene (np. gicleeart.eu) albo zaloz konto Resend na gicleeartpl@gmail.com.";
    }
    return { ok: false, error: `Resend HTTP ${res.status}: ${text.slice(0, 400)}${hint}` };
  }
  return { ok: true };
}

async function handleUpload(request, env, cors) {
  const form = await request.formData();
  const original = form.get("original");
  const originalFull = form.get("original_full");
  const preview = form.get("preview");
  const cropRaw = form.get("crop");
  const configRaw = form.get("config");
  const metaExtraRaw = form.get("meta_extra");
  const stageOnly = form.get("stage_only") === "1";
  const completeStaged = form.get("complete_staged") === "1";
  const uploadIdParam = form.get("upload_id");

  if (stageOnly) {
    if (!(original instanceof File) || original.size <= 0) {
      return json({ error: "Brak pliku original" }, 400, cors);
    }
    if (original.size > MAX_ORIGINAL_BYTES) {
      return json({ error: "Plik za duży (max 50 MB)" }, 413, cors);
    }
    let metaExtra = null;
    try {
      if (typeof metaExtraRaw === "string" && metaExtraRaw.trim()) {
        metaExtra = JSON.parse(metaExtraRaw);
      }
    } catch (_) {
      return json({ error: "Nieprawidłowy JSON meta_extra" }, 400, cors);
    }
    const uploadId = crypto.randomUUID();
    const prefix = `customer-uploads/${uploadId}`;
    const origExt = extFromType(original.type, "jpg");
    await env.UPLOADS.put(`${prefix}/original.${origExt}`, original.stream(), {
      httpMetadata: { contentType: original.type || "application/octet-stream" },
    });
    const originalUrl = publicUrl(env, `${prefix}/original.${origExt}`);
    const meta = {
      v: 1,
      uploadId,
      createdAt: new Date().toISOString(),
      staged: true,
      originalUrl,
      originalFullUrl: null,
      previewUrl: null,
      cropUrl: null,
      config: null,
      orientation: null,
      originalName: original.name || null,
      originalBytes: original.size,
      originalFullBytes: null,
      dimensions: metaExtra?.dimensions || null,
    };
    await env.UPLOADS.put(`${prefix}/meta.json`, JSON.stringify(meta, null, 2), {
      httpMetadata: { contentType: "application/json; charset=utf-8" },
    });
    return json({ uploadId, staged: true }, 200, cors);
  }

  const reuseId =
    completeStaged && typeof uploadIdParam === "string" && isUuid(uploadIdParam)
      ? uploadIdParam
      : null;

  if (!(original instanceof File) || original.size <= 0) {
    if (!reuseId) {
      return json({ error: "Brak pliku original" }, 400, cors);
    }
  } else if (original.size > MAX_ORIGINAL_BYTES) {
    return json({ error: "Plik za duży (max 50 MB)" }, 413, cors);
  }
  if (originalFull instanceof File && originalFull.size > MAX_ORIGINAL_FULL_BYTES) {
    return json({ error: "Plik original_full za duży (max 50 MB)" }, 413, cors);
  }
  if (preview instanceof File && preview.size > MAX_PREVIEW_BYTES) {
    return json({ error: "Podgląd za duży" }, 413, cors);
  }

  let crop = null;
  let config = null;
  try {
    if (typeof cropRaw === "string" && cropRaw.trim()) crop = JSON.parse(cropRaw);
  } catch (_) {
    return json({ error: "Nieprawidłowy JSON crop" }, 400, cors);
  }
  try {
    if (typeof configRaw === "string" && configRaw.trim()) config = JSON.parse(configRaw);
  } catch (_) {
    return json({ error: "Nieprawidłowy JSON config" }, 400, cors);
  }

  let metaExtra = null;
  try {
    if (typeof metaExtraRaw === "string" && metaExtraRaw.trim()) {
      metaExtra = JSON.parse(metaExtraRaw);
    }
  } catch (_) {
    return json({ error: "Nieprawidłowy JSON meta_extra" }, 400, cors);
  }

  const uploadId = reuseId || crypto.randomUUID();
  const prefix = `customer-uploads/${uploadId}`;
  let existingMeta = null;
  if (reuseId) {
    existingMeta = await fetchMeta(env, uploadId);
    if (!existingMeta || !existingMeta.originalUrl) {
      return json({ error: "Nie znaleziono wstępnego uploadu (upload_id)" }, 400, cors);
    }
  }

  let originalUrl = existingMeta?.originalUrl || null;
  let originalBytes = existingMeta?.originalBytes || null;
  let originalName = existingMeta?.originalName || null;

  if (original instanceof File && original.size > 0) {
    const origExt = extFromType(original.type, "jpg");
    await env.UPLOADS.put(`${prefix}/original.${origExt}`, original.stream(), {
      httpMetadata: { contentType: original.type || "application/octet-stream" },
    });
    originalUrl = publicUrl(env, `${prefix}/original.${origExt}`);
    originalBytes = original.size;
    originalName = original.name || null;
  } else if (!originalUrl) {
    return json({ error: "Brak pliku original" }, 400, cors);
  }

  let originalFullUrl = null;
  if (originalFull instanceof File && originalFull.size > 0) {
    await env.UPLOADS.put(`${prefix}/original-full.jpg`, originalFull.stream(), {
      httpMetadata: { contentType: "image/jpeg" },
    });
    originalFullUrl = publicUrl(env, `${prefix}/original-full.jpg`);
  }

  let previewKey = null;
  if (preview instanceof File && preview.size > 0) {
    previewKey = `${prefix}/preview.jpg`;
    await env.UPLOADS.put(previewKey, preview.stream(), {
      httpMetadata: { contentType: "image/jpeg" },
    });
  }

  if (crop) {
    await env.UPLOADS.put(`${prefix}/crop.json`, JSON.stringify(crop, null, 2), {
      httpMetadata: { contentType: "application/json; charset=utf-8" },
    });
  }

  const originalUrlFinal = originalUrl;
  const previewUrl = previewKey ? publicUrl(env, previewKey) : null;
  const cropUrl = crop ? publicUrl(env, `${prefix}/crop.json`) : null;

  const meta = {
    v: 1,
    uploadId,
    createdAt: existingMeta?.createdAt || new Date().toISOString(),
    staged: false,
    originalUrl: originalUrlFinal,
    originalFullUrl,
    previewUrl,
    cropUrl,
    config: config || null,
    orientation: crop?.orientation || null,
    originalName: originalName || null,
    originalBytes: originalBytes,
    originalFullBytes: originalFull instanceof File ? originalFull.size : null,
    dimensions: metaExtra?.dimensions || existingMeta?.dimensions || null,
  };

  await env.UPLOADS.put(`${prefix}/meta.json`, JSON.stringify(meta, null, 2), {
    httpMetadata: { contentType: "application/json; charset=utf-8" },
  });

  const metaUrl = publicUrl(env, `${prefix}/meta.json`);

  return json(
    {
      uploadId,
      originalUrl,
      originalFullUrl,
      previewUrl,
      cropUrl,
      metaUrl,
    },
    200,
    cors
  );
}

function extractUploadId(line) {
  const props = line.properties || [];
  for (const p of props) {
    const name = (p.name || "").trim();
    const val = (p.value || "").trim();
    if (!val) continue;
    if (name === "_Upload ID" || name === "Upload ID" || name === "_pm_upload_id") {
      return val;
    }
  }
  return null;
}

async function fetchMeta(env, uploadId) {
  const key = `customer-uploads/${uploadId}/meta.json`;
  const obj = await env.UPLOADS.get(key);
  if (!obj) return null;
  try {
    return JSON.parse(await obj.text());
  } catch (_) {
    return null;
  }
}

function formatOrientation(o) {
  if (o === "landscape") return "Pozioma";
  if (o === "portrait") return "Pionowa";
  return o || "—";
}

function extractLineProperty(line, key) {
  const props = line?.properties || [];
  for (const p of props) {
    const name = (p.name || "").trim();
    const val = (p.value || "").trim();
    if (name === key && val) return val;
  }
  return "";
}

function resolvePassepartout(meta, line) {
  const cfg = meta?.config || {};
  const fromCfg = cfg.passepartout || cfg.passe_partout || "";
  if (fromCfg) return fromCfg;
  return extractLineProperty(line, "Passepartout") || "—";
}

function formatFrameBlock(meta, line) {
  const cfg = meta?.config || {};
  const wood = cfg.wood || cfg.drewno || "";
  const color = cfg.color || cfg.kolor || "";
  const size = cfg.size || cfg.rozmiar || "";
  const passepartout = resolvePassepartout(meta, line);
  const hasCfg = wood || color || size || (passepartout && passepartout !== "—");

  let rows = "";
  if (hasCfg) {
    rows += `<tr><td style="padding:4px 12px 4px 0;color:#555">Drewno</td><td><strong>${escapeHtml(wood || "—")}</strong></td></tr>`;
    rows += `<tr><td style="padding:4px 12px 4px 0;color:#555">Kolor ramy</td><td><strong>${escapeHtml(color || "—")}</strong></td></tr>`;
    rows += `<tr><td style="padding:4px 12px 4px 0;color:#555">Passepartout</td><td><strong>${escapeHtml(passepartout || "—")}</strong></td></tr>`;
    rows += `<tr><td style="padding:4px 12px 4px 0;color:#555">Rozmiar</td><td><strong>${escapeHtml(size || "—")}</strong></td></tr>`;
  }
  const orient = meta?.orientation;
  if (orient) {
    rows += `<tr><td style="padding:4px 12px 4px 0;color:#555">Orientacja zdjęcia</td><td><strong>${escapeHtml(formatOrientation(orient))}</strong></td></tr>`;
  }
  if (line?.variant_title && !hasCfg) {
    rows += `<tr><td style="padding:4px 12px 4px 0;color:#555">Wariant Shopify</td><td><strong>${escapeHtml(line.variant_title)}</strong></td></tr>`;
  } else if (line?.variant_title && hasCfg) {
    rows += `<tr><td style="padding:4px 12px 4px 0;color:#555">Wariant (Shopify)</td><td>${escapeHtml(line.variant_title)}</td></tr>`;
  }
  if (!rows) return "";
  return `<table style="border-collapse:collapse;margin:8px 0 12px;font-size:15px">${rows}</table>`;
}

async function handleShopifyWebhook(request, env) {
  const rawBody = await request.text();
  const ok = await verifyShopifyHmac(request, env.SHOPIFY_WEBHOOK_SECRET, rawBody);
  if (!ok) {
    return new Response("Unauthorized", { status: 401 });
  }

  let order;
  try {
    order = JSON.parse(rawBody);
  } catch (_) {
    return new Response("Bad JSON", { status: 400 });
  }

  const orderName = order.name || ("#" + (order.order_number || order.id || "?"));
  const orderId = order.id || "";
  const lines = order.line_items || [];
  const hits = [];

  for (const line of lines) {
    const uploadId = extractUploadId(line);
    if (!uploadId) continue;
    const meta = await fetchMeta(env, uploadId);
    hits.push({ line, uploadId, meta });
  }

  if (!hits.length) {
    return new Response("OK (no mockup lines)", { status: 200 });
  }

  const customer = [order.customer?.first_name, order.customer?.last_name]
    .filter(Boolean)
    .join(" ");
  const email = order.email || order.customer?.email || "";

  let bodyHtml = `<h2 style="margin:0 0 8px">Własna fotografia — nowe zamówienie</h2>`;
  bodyHtml += `<p style="font-size:17px;margin:0 0 4px"><strong>Numer zamówienia:</strong> ${escapeHtml(orderName)}</p>`;
  if (orderId) {
    bodyHtml += `<p style="margin:0 0 12px;color:#555;font-size:13px">ID Shopify: ${escapeHtml(String(orderId))}</p>`;
  }
  if (customer || email) {
    bodyHtml += `<p style="margin:0 0 16px">`;
    if (customer) bodyHtml += `<strong>Klient:</strong> ${escapeHtml(customer)}`;
    if (customer && email) bodyHtml += `<br>`;
    if (email) bodyHtml += `<strong>E-mail:</strong> ${escapeHtml(email)}`;
    bodyHtml += `</p>`;
  }

  for (const { line, uploadId, meta } of hits) {
    bodyHtml += `<hr style="border:none;border-top:1px solid #ddd;margin:16px 0">`;
    bodyHtml += `<h3 style="margin:0 0 8px">${escapeHtml(line.title || "Własna fotografia")}</h3>`;
    bodyHtml += `<p style="margin:0 0 4px"><strong>Ilość:</strong> ${line.quantity || 1}</p>`;
    bodyHtml += `<h4 style="margin:12px 0 6px;font-size:14px;text-transform:uppercase;letter-spacing:0.04em;color:#555">Ramka</h4>`;
    bodyHtml += formatFrameBlock(meta, line);
    bodyHtml += `<h4 style="margin:12px 0 6px;font-size:14px;text-transform:uppercase;letter-spacing:0.04em;color:#555">Pliki</h4>`;
    bodyHtml += `<p style="margin:0 0 4px;font-size:13px;color:#666">Upload ID: ${escapeHtml(uploadId)}</p>`;
    if (meta) {
      const best = pickBestOriginal(meta);
      if (best.url) {
        bodyHtml += `<p><a href="${escapeHtml(best.url)}">📷 ${escapeHtml(best.label)}</a></p>`;
        if (
          meta.originalFullUrl &&
          meta.originalUrl &&
          meta.originalUrl !== meta.originalFullUrl &&
          best.url !== meta.originalUrl
        ) {
          bodyHtml += `<p style="font-size:13px;margin:0 0 4px"><a href="${escapeHtml(meta.originalUrl)}">Plik źródłowy od klienta (${escapeHtml(meta.originalName || "surowy upload")})</a></p>`;
        } else if (
          meta.originalFullUrl &&
          meta.originalUrl &&
          meta.originalUrl !== meta.originalFullUrl &&
          best.url !== meta.originalFullUrl
        ) {
          bodyHtml += `<p style="font-size:13px;margin:0 0 4px"><a href="${escapeHtml(meta.originalFullUrl)}">Wersja JPEG pełnej rozdzielczości</a></p>`;
        }
        const dims = meta.dimensions;
        if (dims && dims.decodeWidth && dims.decodeHeight) {
          bodyHtml += `<p style="font-size:12px;color:#666;margin:0 0 8px">${escapeHtml(String(dims.decodeWidth))}×${escapeHtml(String(dims.decodeHeight))} px`;
          if (dims.originalBytes) {
            bodyHtml += ` · ${escapeHtml(String(Math.round(dims.originalBytes / 1024)))} KB`;
          }
          bodyHtml += `</p>`;
        }
      }
      if (meta.previewUrl) {
        bodyHtml += `<p><a href="${escapeHtml(meta.previewUrl)}">🖼 Podgląd mockupu (kadrowanie)</a></p>`;
      }
      if (meta.cropUrl) {
        bodyHtml += `<p><a href="${escapeHtml(meta.cropUrl)}">📐 Dane kadrowania (JSON)</a></p>`;
      }
      bodyHtml += `<p style="font-size:13px"><a href="${escapeHtml(publicUrl(env, `customer-uploads/${uploadId}/meta.json`))}">meta.json</a></p>`;
    } else {
      bodyHtml += `<p style="color:#c00">Nie znaleziono plików w R2 dla uploadId ${escapeHtml(uploadId)}</p>`;
    }
  }

  bodyHtml += `<p style="color:#666;font-size:12px;margin-top:20px">Powiadomienie z Giclee mockup worker → ${escapeHtml(env.MERCHANT_EMAIL || "gicleeartpl@gmail.com")}</p>`;

  const mail = await sendMerchantEmail(env, {
    from: resolveResendFrom(order, env),
    subject: `Giclée — zamówienie ${orderName} — własna fotografia`,
    html: bodyHtml,
  });

  if (!mail.ok) {
    return new Response(mail.error || "Email send failed", { status: 502 });
  }

  return new Response("OK", { status: 200 });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const origin = request.headers.get("Origin") || "";
    const cors = corsHeaders(origin, env);

    // Preflight analityki — przed ogólnym OPTIONS (wymaga X-Analytics-Secret)
    if (url.pathname.startsWith("/api/analytics/") && request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: analyticsCors(origin, env) });
    }

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors });
    }

    if (url.pathname === "/api/mockup-upload" && request.method === "POST") {
      try {
        return await handleUpload(request, env, cors);
      } catch (err) {
        console.error(err);
        return json({ error: "Upload failed" }, 500, cors);
      }
    }

    if (url.pathname === "/webhooks/shopify/orders-paid" && request.method === "POST") {
      try {
        return await handleShopifyWebhook(request, env);
      } catch (err) {
        console.error(err);
        return new Response("Error", { status: 500 });
      }
    }

    if (url.pathname === "/health") {
      return json({ ok: true, analytics: Boolean(env.ANALYTICS_DB) }, 200, cors);
    }

    if (url.pathname === "/api/analytics/collect" && (request.method === "POST" || request.method === "OPTIONS")) {
      try {
        return await handleAnalyticsCollect(request, env);
      } catch (err) {
        console.error("analytics collect", err);
        return json({ ok: false, error: "Collect failed" }, 500, analyticsCorsFallback());
      }
    }

    if (url.pathname === "/api/analytics/export" && request.method === "GET") {
      try {
        return await handleAnalyticsExport(request, env);
      } catch (err) {
        console.error("analytics export", err);
        return json({ ok: false, error: "Export failed" }, 500);
      }
    }

    if (url.pathname === "/api/analytics/stats" && request.method === "GET") {
      try {
        return await handleAnalyticsStats(request, env);
      } catch (err) {
        console.error("analytics stats", err);
        return json({ ok: false, error: "Stats failed" }, 500);
      }
    }

    if (url.pathname === "/api/analytics/purge" && request.method === "POST") {
      try {
        return await handleAnalyticsPurge(request, env);
      } catch (err) {
        console.error("analytics purge", err);
        return json({ ok: false, error: "Purge failed" }, 500);
      }
    }

    return json({ error: "Not found" }, 404, cors);
  },
};

function analyticsCorsFallback() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-Analytics-Secret",
  };
}
