(function () {
  "use strict";

  var API = "";
  var charts = {};
  var secret = "";
  var autoSyncMs = 300000;
  var lastCloudSync = null;
  var autoSyncTimer = null;
  var myIpTogglePending = false;
  var lastAnalyticsSettings = {};
  var lastExclusionImpact = {};

  function qs(sel) { return document.querySelector(sel); }
  function qsa(sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); }

  function preset() { return qs("#preset").value; }
  function countryFilter() { return qs("#country-filter").value; }
  function deviceFilter() { return qs("#device-filter").value; }
  function sourceFilter() { return qs("#source-filter").value; }

  function apiUrl(path, extra) {
    var p = preset();
    var c = countryFilter();
    var d = deviceFilter();
    var s = sourceFilter();
    var url = API + path + "?preset=" + encodeURIComponent(p);
    if (c) url += "&country=" + encodeURIComponent(c);
    if (d) url += "&device=" + encodeURIComponent(d);
    if (s) url += "&source=" + encodeURIComponent(s);
    if (extra) url += "&" + extra;
    return url;
  }

  function deltaArrow(deltaVal) {
    if (deltaVal == null || isNaN(deltaVal)) return "";
    var pct = (deltaVal * 100).toFixed(0);
    var cls = deltaVal >= 0 ? "up" : "down";
    var arrow = deltaVal >= 0 ? "↑" : "↓";
    return ' <span class="delta-inline ' + cls + '">' + arrow + " " + Math.abs(pct) + "%</span>";
  }

  function formatSyncTime(d) {
    if (!d) return "";
    return d.toLocaleTimeString("pl-PL", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  }

  async function pullFromWorker(opts) {
    opts = opts || {};
    try {
      var res = await fetch(API + "/api/analytics/pull-worker", { method: "POST" });
      var data = await res.json();
      if (!res.ok || !data.ok) {
        if (opts.alertOnError) {
          alert("Sync z chmury: " + (data.error || "błąd HTTP " + res.status));
        }
        return null;
      }
      lastCloudSync = new Date();
      if (opts.alertOnSuccess) {
        alert(
          "Sync z chmury:\n• pobrano: " + (data.fetched || 0) +
          "\n• nowe lokalnie: " + (data.inserted || 0) +
          "\n• pominięte (duplikaty): " + (data.skipped || 0)
        );
      }
      return data;
    } catch (e) {
      if (opts.alertOnError) {
        alert("Sync z chmury nie powiódł się: " + e.message);
      }
      return null;
    }
  }

  function startAutoSyncTimer() {
    if (autoSyncTimer) clearInterval(autoSyncTimer);
    autoSyncTimer = null;
    if (!autoSyncMs || autoSyncMs < 1000) return;
    autoSyncTimer = setInterval(function () {
      pullFromWorker({}).then(function (data) {
        if (data) loadAll();
      });
    }, autoSyncMs);
  }

  function footerSyncNote() {
    return lastCloudSync ? " · sync chmury: " + formatSyncTime(lastCloudSync) : "";
  }

  function showLoading(on) {
    qs("#loading").classList.toggle("hidden", !on);
  }

  function fmt(n, dec) {
    if (n == null || isNaN(n)) return "—";
    return Number(n).toLocaleString("pl-PL", {
      minimumFractionDigits: dec || 0,
      maximumFractionDigits: dec || 0,
    });
  }

  function pct(n) {
    if (n == null || isNaN(n)) return "—";
    return (n * 100).toFixed(1) + "%";
  }

  function delta(cur, prev) {
    if (!prev) return { cls: "", text: "" };
    var d = cur - prev;
    var p = prev ? (d / prev) * 100 : 0;
    return {
      cls: d >= 0 ? "up" : "down",
      text: (d >= 0 ? "+" : "") + p.toFixed(1) + "% vs poprzedni okres",
    };
  }

  var EXPECTED_API_VERSION = 2;

  var DEFAULT_UTM_TEMPLATES = [
    { name: "Instagram — launch", utm_source: "instagram", utm_medium: "social", utm_campaign: "launch", path: "/products/" },
    { name: "Facebook — reklama", utm_source: "facebook", utm_medium: "paid", utm_campaign: "prospecting", path: "/products/" },
    { name: "Newsletter", utm_source: "newsletter", utm_medium: "email", utm_campaign: "weekly", path: "/" },
    { name: "Google Ads", utm_source: "google", utm_medium: "cpc", utm_campaign: "brand", path: "/collections/" },
  ];

  function buildUtmUrlClient(path, source, medium, campaign) {
    var domain = "https://gicleeart.eu";
    var p = path.indexOf("/") === 0 ? path : "/" + path;
    var q = "utm_source=" + encodeURIComponent(source || "") +
      "&utm_medium=" + encodeURIComponent(medium || "") +
      "&utm_campaign=" + encodeURIComponent(campaign || "");
    return domain + p + "?" + q;
  }

  function populateUtmTemplates(templates) {
    var list = templates && templates.length ? templates : DEFAULT_UTM_TEMPLATES;
    var tplSel = qs("#utm-template");
    if (!tplSel) return list;
    tplSel.innerHTML = list.map(function (t, i) {
      return '<option value="' + i + '">' + (t.name || "Szablon " + (i + 1)) + "</option>";
    }).join("");
    applyUtmTemplate(list[0]);
    return list;
  }

  async function fetchJson(url, opts) {
    var res = await fetch(url, opts || {});
    if (!res.ok) {
      var path = String(url).replace(API, "");
      throw new Error("HTTP " + res.status + " · " + path);
    }
    return res.json();
  }

  async function fetchJsonOptional(url, fallback) {
    try {
      return await fetchJson(url);
    } catch (e) {
      if (String(e.message).indexOf("HTTP 404") >= 0) return fallback;
      throw e;
    }
  }

  function destroyChart(id) {
    if (charts[id]) { charts[id].destroy(); delete charts[id]; }
  }

  function chartColors() {
    var dark = document.documentElement.getAttribute("data-theme") === "dark";
    return {
      text: dark ? "#a89f94" : "#6b635a",
      grid: dark ? "#332c26" : "#e8e0d6",
      accent: dark ? "#d4a574" : "#5c3d2e",
      gold: "#b8956a",
    };
  }

  function renderKpis(current, previous) {
    var items = [
      ["Wejścia", current.entrances, previous.entrances],
      ["Użytkownicy", current.visitors, previous.visitors],
      ["Sesje", current.sessions, previous.sessions],
      ["Odsłony", current.pageviews, previous.pageviews],
      ["Oglądane produkty", current.product_views, previous.product_views],
      ["Dodania do koszyka", current.add_to_carts, previous.add_to_carts],
      ["Checkouty", current.checkouts_started, previous.checkouts_started],
      ["Zakupy", current.purchases, previous.purchases],
      ["Przychód", current.revenue, previous.revenue, 2],
      ["Konwersja", pct(current.conversion_rate), pct(previous.conversion_rate)],
      ["Add-to-cart rate", pct(current.add_to_cart_rate), pct(previous.add_to_cart_rate)],
      ["AOV", current.average_order_value, previous.average_order_value, 2],
      ["Bounce rate", pct(current.bounce_rate), pct(previous.bounce_rate)],
    ];
    qs("#kpi-grid").innerHTML = items.map(function (row) {
      var label = row[0], cur = row[1], prev = row[2], dec = row[3];
      var d = typeof cur === "number" ? delta(cur, prev) : { cls: "", text: "" };
      var val = typeof cur === "number" ? fmt(cur, dec) : cur;
      return '<div class="kpi"><div class="kpi__label">' + label + '</div>' +
        '<div class="kpi__value">' + val + '</div>' +
        (d.text ? '<div class="kpi__delta ' + d.cls + '">' + d.text + '</div>' : '') +
        '</div>';
    }).join("");
    qs("#quality-score").textContent = current.quality_score != null ? current.quality_score : "—";
  }

  function renderTimelineCharts(timeline) {
    var labels = timeline.map(function (t) { return t.date; });
    var c = chartColors();
    var trafficOpts = {
      responsive: true,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: true, labels: { color: c.text, boxWidth: 12 } },
        tooltip: { mode: "index" },
      },
      scales: {
        x: { ticks: { color: c.text }, grid: { color: c.grid } },
        y: { ticks: { color: c.text }, grid: { color: c.grid }, beginAtZero: true },
      },
    };

    destroyChart("traffic");
    charts.traffic = new Chart(qs("#chart-traffic"), {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          { label: "Sesje", data: timeline.map(function (t) { return t.sessions || 0; }), borderColor: c.accent, backgroundColor: c.accent + "22", tension: 0.3, fill: false },
          { label: "Unikalni/dzień", data: timeline.map(function (t) { return t.unique_visitors != null ? t.unique_visitors : 0; }), borderColor: "#6b9bd1", backgroundColor: "#6b9bd122", tension: 0.3, borderDash: [4, 2], fill: false },
          { label: "Odsłony", data: timeline.map(function (t) { return t.pageviews || 0; }), borderColor: c.gold, backgroundColor: c.gold + "22", tension: 0.3, fill: false },
        ],
      },
      options: trafficOpts,
    });

    var opts = {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: c.text }, grid: { color: c.grid } },
        y: { ticks: { color: c.text }, grid: { color: c.grid } },
      },
    };

    destroyChart("revenue");
    charts.revenue = new Chart(qs("#chart-revenue"), {
      type: "bar",
      data: {
        labels: labels,
        datasets: [{ label: "Przychód", data: timeline.map(function (t) { return t.revenue; }), backgroundColor: c.accent }],
      },
      options: opts,
    });

    destroyChart("conversion");
    charts.conversion = new Chart(qs("#chart-conversion"), {
      type: "line",
      data: {
        labels: labels,
        datasets: [{ label: "Konwersja", data: timeline.map(function (t) { return (t.conversion_rate || 0) * 100; }), borderColor: c.gold, tension: 0.3 }],
      },
      options: Object.assign({}, opts, { scales: { y: { ticks: { callback: function (v) { return v + "%"; }, color: c.text }, grid: { color: c.grid } }, x: opts.scales.x } }),
    });
  }

  function renderCountries(data) {
    var rows = data.countries || [];
    var pf = data.poland_vs_foreign || {};
    qs("#pl-vs-foreign").innerHTML =
      '<div class="kpi"><div class="kpi__label">Polska — sesje</div><div class="kpi__value">' + fmt(pf.poland_sessions) + '</div></div>' +
      '<div class="kpi"><div class="kpi__label">Zagranica — sesje</div><div class="kpi__value">' + fmt(pf.foreign_sessions) + '</div></div>' +
      '<div class="kpi"><div class="kpi__label">Udział PL</div><div class="kpi__value">' + pct(pf.poland_share) + '</div></div>';

    var top = rows.slice(0, 12);
    var c = chartColors();
    destroyChart("countries");
    charts.countries = new Chart(qs("#chart-countries"), {
      type: "bar",
      data: {
        labels: top.map(function (r) { return r.country; }),
        datasets: [{ data: top.map(function (r) { return r.sessions; }), backgroundColor: c.accent }],
      },
      options: { indexAxis: "y", plugins: { legend: { display: false } }, scales: { x: { ticks: { color: c.text }, grid: { color: c.grid } }, y: { ticks: { color: c.text }, grid: { display: false } } } },
    });

    destroyChart("countryRev");
    charts.countryRev = new Chart(qs("#chart-country-revenue"), {
      type: "bar",
      data: {
        labels: top.map(function (r) { return r.country; }),
        datasets: [{ data: top.map(function (r) { return r.revenue; }), backgroundColor: c.gold }],
      },
      options: { indexAxis: "y", plugins: { legend: { display: false } }, scales: { x: { ticks: { color: c.text }, grid: { color: c.grid } }, y: { ticks: { color: c.text }, grid: { display: false } } } },
    });

    var cols = ["country", "visitors", "sessions", "pageviews", "product_views", "add_to_carts", "checkouts_started", "purchases", "revenue", "conversion_rate", "average_order_value"];
    var thead = qs("#table-countries thead");
    thead.innerHTML = "<tr>" + cols.map(function (h) { return "<th>" + h + "</th>"; }).join("") + "</tr>";
    qs("#table-countries tbody").innerHTML = rows.map(function (r) {
      return "<tr><td>" + r.country + "</td><td>" + r.visitors + "</td><td>" + r.sessions + "</td><td>" + r.pageviews + "</td><td>" + r.product_views + "</td><td>" + r.add_to_carts + "</td><td>" + r.checkouts_started + "</td><td>" + r.purchases + "</td><td>" + fmt(r.revenue, 2) + "</td><td>" + pct(r.conversion_rate) + "</td><td>" + fmt(r.average_order_value, 2) + "</td></tr>";
    }).join("");

    var sel = qs("#country-filter");
    var cur = sel.value;
    sel.innerHTML = '<option value="">Wszystkie kraje</option>' +
      rows.slice(0, 30).map(function (r) {
        return '<option value="' + r.country + '"' + (r.country === cur ? " selected" : "") + ">" + r.country + "</option>";
      }).join("");
  }

  function renderFunnel(data) {
    var stages = data.stages || [];
    var maxUsers = stages[0] && stages[0].users || 1;
    qs("#funnel-viz").innerHTML = stages.map(function (s) {
      var w = Math.max(20, (s.users / maxUsers) * 100);
      return '<div class="funnel__step" style="width:' + w + '%"><span>' + s.stage.replace(/_/g, " ") + '</span><span class="funnel__meta">' +
        s.users + " użytk." + deltaArrow(s.users_delta) + " · drop " + pct(s.drop_off_rate) + "</span></div>";
    }).join("");

    var c = chartColors();
    destroyChart("funnel");
    charts.funnel = new Chart(qs("#chart-funnel"), {
      type: "bar",
      data: {
        labels: stages.map(function (s) { return s.stage; }),
        datasets: [{ data: stages.map(function (s) { return s.users; }), backgroundColor: c.accent }],
      },
      options: { plugins: { legend: { display: false } }, scales: { x: { ticks: { color: c.text, maxRotation: 45 } }, y: { ticks: { color: c.text }, grid: { color: c.grid } } } },
    });
  }

  function renderProducts(data) {
    var products = data.products || [];
    var headers = [
      ["product_title", "Produkt"],
      ["unique_viewers", "Unikalni"],
      ["avg_daily_unique", "Śr. unikalni/dzień"],
      ["views", "Wyświetlenia"],
      ["add_to_carts", "Do koszyka"],
      ["add_to_cart_rate", "Add-to-cart"],
      ["checkouts", "Checkouty"],
      ["purchases", "Zakupy"],
      ["revenue", "Przychód"],
      ["conversion_rate", "Konwersja"],
      ["alert", "Alert"],
    ];
    qs("#table-products thead").innerHTML = "<tr>" + headers.map(function (h) {
      return "<th>" + h[1] + "</th>";
    }).join("") + "</tr>";
    qs("#table-products tbody").innerHTML = products.map(function (p) {
      var alert = p.high_traffic_low_conversion ? '<span class="alert-badge">duży ruch, mało zakupów</span>' : "";
      return "<tr><td>" + (p.product_title || p.shopify_product_id) + "</td><td>" +
        (p.unique_viewers != null ? p.unique_viewers + deltaArrow(p.unique_delta) : "—") + "</td><td>" +
        (typeof p.avg_daily_unique === "number" ? p.avg_daily_unique : "—") + "</td><td>" + p.views + deltaArrow(p.views_delta) + "</td><td>" +
        p.add_to_carts + "</td><td>" + pct(p.add_to_cart_rate) + "</td><td>" + p.checkouts + "</td><td>" + p.purchases + "</td><td>" +
        fmt(p.revenue, 2) + "</td><td>" + pct(p.conversion_rate) + "</td><td>" + alert + "</td></tr>";
    }).join("") || "<tr><td colspan='11'>Brak danych produktowych</td></tr>";
  }

  function renderFrameFunnel(data) {
    var stages = data.stages || [];
    var maxUsers = stages[0] && stages[0].users || 1;
    qs("#frame-funnel-viz").innerHTML = stages.length ? stages.map(function (s) {
      var w = Math.max(20, (s.users / maxUsers) * 100);
      return '<div class="funnel__step" style="width:' + w + '%"><span>' + s.stage.replace(/_/g, " ") + '</span><span class="funnel__meta">' +
        s.users + " użytk. · drop " + pct(s.drop_off_rate) + "</span></div>";
    }).join("") : "<p>Brak eventów konfiguratora — użytkownicy muszą otworzyć konfigurator ram na stronie produktu.</p>";

    var counts = data.event_counts || {};
    var rows = Object.keys(counts).map(function (k) {
      return { event: k.replace("giclee_app:", ""), count: counts[k] };
    }).sort(function (a, b) { return b.count - a.count; });
    qs("#table-frames thead").innerHTML = "<tr><th>Event</th><th>Liczba</th></tr>";
    qs("#table-frames tbody").innerHTML = rows.map(function (r) {
      return "<tr><td>" + r.event + "</td><td>" + r.count + "</td></tr>";
    }).join("") || "<tr><td colspan='2'>Brak danych</td></tr>";
  }

  function renderStatusBar(status) {
    var pixelEl = qs("#status-pixel");
    var syncEl = qs("#status-sync");
    var countsEl = qs("#status-counts");
    if (!pixelEl) return;

    var connected = status.pixel_connected;
    var lastEv = status.pixel_last_event_at || "—";
    pixelEl.innerHTML = connected
      ? '<span class="status-ok">● Pixel połączony</span> · ostatni event: ' + lastEv
      : '<span class="status-warn">○ Pixel — brak eventów w chmurze</span>';

    var syncAt = status.last_worker_sync_at;
    syncEl.textContent = syncAt
      ? "Ostatni sync: " + syncAt.replace("T", " ").replace("Z", " UTC")
      : "Sync: jeszcze nie wykonano";

    var cloud = status.cloud_events != null ? status.cloud_events : "—";
    var local = status.local_events != null ? status.local_events : (status.stats && status.stats.total_events);
    countsEl.textContent = "Chmura: " + cloud + " eventów · lokalnie: " + (local != null ? local : "—");

    var exEl = qs("#status-exclusions");
    if (exEl) {
      var impact = status.exclusion_impact || {};
      lastExclusionImpact = impact;
      if (!impact.enabled) {
        exEl.textContent = "Wykluczenia: wyłączone (suwak)";
        exEl.className = "";
      } else if (!impact.events) {
        exEl.textContent = "Wykluczenia: 0 dopasowań w bazie";
        exEl.className = "status-warn";
      } else {
        exEl.textContent = "Wykluczenia: −" + impact.events + " eventów · " + impact.visitors + " visitorów";
        exEl.className = "";
      }
    }
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderExcludeList(settings) {
    settings = settings || {};
    var listEl = qs("#exclude-list");
    if (!listEl) return;
    var labels = settings.exclude_labels || {};
    var exVis = settings.exclude_visitor_hashes || [];
    var exIp = settings.exclude_ip_hashes || [];
    var parts = [];
    exVis.forEach(function (h) {
      var label = labels[h] || h.slice(0, 20) + "…";
      parts.push(
        '<div class="exclude-item" role="listitem" data-kind="visitor" data-hash="' + escapeHtml(h) + '">' +
        '<div class="exclude-item__meta"><strong>Visitor</strong><span>' + escapeHtml(label) + "</span>" +
        '<code>' + escapeHtml(h.slice(0, 22)) + "…</code></div>" +
        '<button type="button" class="exclude-item__remove">Usuń</button></div>'
      );
    });
    exIp.forEach(function (h) {
      var label = labels[h] || h.slice(0, 20) + "…";
      parts.push(
        '<div class="exclude-item" role="listitem" data-kind="ip" data-hash="' + escapeHtml(h) + '">' +
        '<div class="exclude-item__meta"><strong>IP</strong><span>' + escapeHtml(label) + "</span>" +
        '<code>' + escapeHtml(h.slice(0, 22)) + "…</code></div>" +
        '<button type="button" class="exclude-item__remove">Usuń</button></div>'
      );
    });
    if (!parts.length) {
      listEl.innerHTML = '<p class="exclude-list__empty">Brak wykluczeń — wpisz Visitor ID lub IP i kliknij „Dodaj wykluczenie”.</p>';
    } else {
      listEl.innerHTML = parts.join("");
    }
  }

  function syncMyIpToggle(settings) {
    if (myIpTogglePending) return;
    var toggle = qs("#toggle-my-ip");
    if (!toggle) return;
    settings = settings || {};
    lastAnalyticsSettings = settings;
    toggle.checked = !!settings.exclude_my_ip;
    var label = qs("#toggle-my-ip-label");
    if (label) {
      var ip = settings.my_ip || "";
      if (ip && settings.exclude_my_ip) {
        var noIpInDb = lastExclusionImpact && !lastExclusionImpact.events_with_ip;
        label.textContent = "Moje IP (" + ip + ")" + (noIpInDb ? " · sesje testowe" : "");
      } else {
        label.textContent = "Wyklucz moje IP";
      }
    }
    var ipInput = qs("#exclude-ip");
    if (ipInput && settings.my_ip && !ipInput.value) {
      ipInput.value = settings.my_ip;
    }
  }

  async function toggleMyIp(enabled) {
    var ip = "";
    if (enabled) {
      ip = (qs("#exclude-ip") && qs("#exclude-ip").value || "").trim();
      if (!ip) {
        ip = await detectPublicIp();
      }
      if (!ip) {
        throw new Error("Nie udało się ustalić publicznego IP — wpisz ręcznie w Konfiguracja");
      }
    } else {
      ip = (lastAnalyticsSettings.my_ip || (qs("#exclude-ip") && qs("#exclude-ip").value) || "").trim();
    }
    myIpTogglePending = true;
    try {
      var res = await fetch(API + "/api/analytics/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "toggle_my_ip", ip: ip, enabled: enabled }),
      });
      var data = {};
      try {
        data = await res.json();
      } catch (parseErr) {
        throw new Error("HTTP " + res.status + " — zrestartuj serwer analityki (GicleeApp → Uruchom i otwórz dashboard)");
      }
      if (!res.ok || !data.ok) {
        throw new Error(data.error || ("HTTP " + res.status));
      }
      var settings = data.settings || {};
      syncMyIpToggle(settings);
      syncExclusionsToggle(settings);
      renderExcludeList(settings);
      if (settings.my_ip && qs("#exclude-ip")) {
        qs("#exclude-ip").value = settings.my_ip;
      }
      await loadSetup();
      await loadAll();
      return settings;
    } finally {
      myIpTogglePending = false;
    }
  }

  function syncExclusionsToggle(settings, impact) {
    var toggle = qs("#toggle-exclusions");
    if (!toggle) return;
    var enabled = settings.exclusions_enabled !== false;
    toggle.checked = enabled;
    var count = (settings.exclude_visitor_hashes || []).length + (settings.exclude_ip_hashes || []).length;
    var label = qs(".exclude-toggle__label");
    if (label) {
      if (!enabled) {
        label.textContent = "Wykluczenia (off)";
      } else if (impact && impact.events) {
        label.textContent = "Wykluczenia (−" + impact.events + ")";
      } else if (enabled && count) {
        label.textContent = "Wykluczenia (0 efekt)";
      } else {
        label.textContent = "Wykluczenia";
      }
    }
  }

  function renderExclusionImpact(impact, settings) {
    var el = qs("#exclude-impact");
    if (!el) return;
    impact = impact || {};
    settings = settings || {};
    var ipCount = (settings.exclude_ip_hashes || []).length;
    if (!impact.enabled) {
      el.textContent = "Filtrowanie wyłączone — KPI pokazują pełny ruch.";
      el.className = "exclude-impact";
      return;
    }
    if (impact.events) {
      el.textContent = "Aktywne wykluczenia ukrywają " + impact.events + " eventów (" +
        impact.visitors + " visitorów, " + impact.sessions + " sesji).";
      el.className = "exclude-impact";
      return;
    }
    if (ipCount && !impact.events_with_ip) {
      el.textContent = "Żaden event w bazie nie ma zapisanego IP — wykluczenie IP działa dopiero na nowy ruch (po wdrożeniu Workera). Wybierz swój Visitor z listy poniżej.";
      el.className = "exclude-impact exclude-impact--warn";
      return;
    }
    if (ipCount || (settings.exclude_visitor_hashes || []).length) {
      el.textContent = "Wykluczenia są zapisane, ale żaden event w bazie nie pasuje — sprawdź listę visitorów poniżej.";
      el.className = "exclude-impact exclude-impact--warn";
      return;
    }
    el.textContent = "";
    el.className = "exclude-impact";
  }

  function renderRecentVisitors(visitors) {
    var el = qs("#recent-visitors");
    if (!el) return;
    visitors = visitors || [];
    if (!visitors.length) {
      el.innerHTML = "<p class=\"exclude-list__empty\">Brak visitorów w ostatnich 14 dniach.</p>";
      return;
    }
    el.innerHTML = visitors.map(function (v) {
      var cls = "recent-visitor" + (v.excluded ? " recent-visitor--excluded" : "");
      return '<div class="' + cls + '" data-hash="' + escapeHtml(v.visitor_id_hash) + '">' +
        '<div class="recent-visitor__meta"><code>' + escapeHtml(v.visitor_id_hash) + "</code>" +
        '<div class="recent-visitor__stats">' + v.events + " eventów · " +
        (v.country || "?") + " · " + (v.device_type || "?") + " · " + (v.last_seen || "").replace("T", " ").replace("Z", "") +
        "</div></div>" +
        '<button type="button" class="recent-visitor__add">' + (v.excluded ? "Wykluczony" : "Wyklucz") + "</button></div>";
    }).join("");
  }

  async function excludeVisitorHash(hash) {
    var res = await fetch(API + "/api/analytics/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "exclude", visitor_hash: hash }),
    });
    var data = {};
    try {
      data = await res.json();
    } catch (parseErr) {
      throw new Error("HTTP " + res.status);
    }
    if (!res.ok || !data.ok) {
      throw new Error(data.error || ("HTTP " + res.status));
    }
    return data.settings || {};
  }

  async function saveExclusionsEnabled(enabled) {
    var res = await fetch(API + "/api/analytics/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ exclusions_enabled: enabled }),
    });
    var data = {};
    try {
      data = await res.json();
    } catch (parseErr) {
      throw new Error("HTTP " + res.status);
    }
    if (!res.ok || !data.ok) {
      throw new Error(data.error || ("HTTP " + res.status));
    }
    syncExclusionsToggle(data.settings || {});
    await loadAll();
  }

  async function removeExclusion(kind, hash) {
    var res = await fetch(API + "/api/analytics/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "remove_exclusion", kind: kind, hash: hash }),
    });
    var data = {};
    try {
      data = await res.json();
    } catch (parseErr) {
      throw new Error("HTTP " + res.status);
    }
    if (!res.ok || !data.ok) {
      throw new Error(data.error || ("HTTP " + res.status));
    }
    renderExcludeList(data.settings || {});
    syncExclusionsToggle(data.settings || {});
    await loadAll();
  }

  function renderSources(data) {
    var rows = data.sources || [];
    var c = chartColors();
    destroyChart("sources");
    charts.sources = new Chart(qs("#chart-sources"), {
      type: "doughnut",
      data: {
        labels: rows.map(function (r) { return r.source; }),
        datasets: [{ data: rows.map(function (r) { return r.sessions; }), backgroundColor: [c.accent, c.gold, "#8b7355", "#6b635a", "#a89f94", "#2e7d52", "#c47a20"] }],
      },
      options: { plugins: { legend: { position: "right", labels: { color: c.text } } } },
    });

    qs("#utm-list").innerHTML = (data.utm_campaigns || []).map(function (u) {
      return '<div class="utm-item"><strong>' + (u.utm_campaign || "(none)") + '</strong> · ' + u.utm_source + " / " + u.utm_medium + " · sesje: " + u.sessions + " · zakupy: " + u.purchases + "</div>";
    }).join("") || "<p>Brak kampanii UTM</p>";

    var cols = ["source", "sessions", "product_views", "add_to_carts", "checkouts_started", "purchases", "revenue", "conversion_rate", "average_order_value"];
    qs("#table-sources thead").innerHTML = "<tr>" + cols.map(function (h) { return "<th>" + h + "</th>"; }).join("") + "</tr>";
    qs("#table-sources tbody").innerHTML = rows.map(function (r) {
      return "<tr><td>" + r.source + "</td><td>" + r.sessions + "</td><td>" + r.product_views + "</td><td>" + r.add_to_carts + "</td><td>" + r.checkouts_started + "</td><td>" + r.purchases + "</td><td>" + fmt(r.revenue, 2) + "</td><td>" + pct(r.conversion_rate) + "</td><td>" + fmt(r.average_order_value, 2) + "</td></tr>";
    }).join("");
  }

  function renderSessions(data) {
    var sessions = data.sessions || [];
    qs("#table-sessions thead").innerHTML = "<tr><th>session_id</th><th>kraj</th><th>odsłony</th><th>ATC</th><th>checkout</th><th>zakup</th><th>przychód</th><th>landing</th></tr>";
    qs("#table-sessions tbody").innerHTML = sessions.map(function (s) {
      return '<tr data-sid="' + s.session_id + '" style="cursor:pointer"><td>' + s.session_id.slice(0, 12) + "…</td><td>" + (s.country || "?") + "</td><td>" + s.pageviews_count + "</td><td>" + s.add_to_cart_count + "</td><td>" + (s.checkout_started ? "✓" : "") + "</td><td>" + (s.purchase_completed ? "✓" : "") + "</td><td>" + fmt(s.revenue, 2) + "</td><td>" + (s.landing_page || "") + "</td></tr>";
    }).join("") || "<tr><td colspan='8'>Brak sesji — kliknij <strong>Sync z chmury</strong> u góry. W stopce sprawdź „sesji: N”. Jeśli eventów &gt; 0 a sesji = 0, zrestartuj serwer analityki i sync ponownie.</td></tr>";

    qsa("#table-sessions tbody tr[data-sid]").forEach(function (tr) {
      tr.addEventListener("click", function () {
        loadSessionTimeline(tr.getAttribute("data-sid"));
      });
    });
  }

  async function loadSessionTimeline(sid) {
    var data = await fetchJson(apiUrl("/api/analytics/sessions", "session_id=" + encodeURIComponent(sid)));
    qs("#session-timeline").classList.remove("hidden");
    qs("#timeline-events").innerHTML = (data.events || []).map(function (e) {
      return "<li><strong>" + e.event_name + "</strong> · " + (e.created_at || "") + " · " + (e.path || "") + "</li>";
    }).join("");
  }

  function renderRealtime(data) {
    qs("#realtime-kpi").innerHTML =
      '<div class="kpi"><div class="kpi__label">Aktywni (15 min)</div><div class="kpi__value">' + data.active_visitors + "</div></div>";
    function list(id, items) {
      qs(id).innerHTML = (items || []).map(function (pair) {
        return "<li><span>" + pair[0] + '</span><span>' + pair[1] + "</span></li>";
      }).join("") || "<li>Brak danych</li>";
    }
    list("#rt-pages", data.top_pages);
    list("#rt-products", data.top_products);
    qs("#rt-events").innerHTML = (data.recent_events || []).map(function (e) {
      return "<li><span>" + e.event_name + " · " + (e.path || e.product_title || "") + '</span><span>' + (e.country || "") + "</span></li>";
    }).join("");
  }

  function renderInsights(data) {
    qs("#insights-list").innerHTML = (data.insights || []).map(function (i) {
      return '<div class="insight insight--' + (i.type || "info") + '"><strong>' + i.title + "</strong><p>" + i.body + "</p></div>";
    }).join("") || "<p>Brak insightów — zbierz więcej danych.</p>";
  }

  async function loadSetup() {
    var status = await fetchJson(API + "/api/analytics/status");
    renderStatusBar(status);
    var worker = status.worker || {};
    var settings = status.settings || {};
    qs("#setup-collect-url").textContent = status.collect_url || "—";
    qs("#setup-status").innerHTML =
      "<dt>Secret w .env</dt><dd>" + (status.collect_secret_configured ? "✓ ustawiony" : "✗ brak") + "</dd>" +
      "<dt>Collect URL (pixel)</dt><dd>" + (status.collect_url || "—") + "</dd>" +
      "<dt>Lokalny URL (tylko test)</dt><dd>" + (status.local_collect_url || "—") + "</dd>" +
      "<dt>Eventów lokalnie</dt><dd>" + (status.stats && status.stats.total_events || 0) + "</dd>" +
      "<dt>Sesji lokalnie</dt><dd>" + (status.stats && status.stats.total_sessions || 0) + "</dd>" +
      "<dt>Eventów w chmurze</dt><dd>" + (worker.total_events != null ? worker.total_events : (worker.error || "—")) + "</dd>" +
      "<dt>Pixel — ostatni event</dt><dd>" + (status.pixel_last_event_at || "—") + "</dd>" +
      "<dt>Auto-sync z chmury</dt><dd>przy otwarciu dashboardu + co " +
      Math.round((status.auto_sync_interval_seconds || 300) / 60) +
      " min (serwer w tle robi to samo)</dd>";

    renderExcludeList(settings);
    syncExclusionsToggle(settings, status.exclusion_impact);
    syncMyIpToggle(settings);
    renderExclusionImpact(status.exclusion_impact, settings);
    renderRecentVisitors(status.recent_visitors);

    var tplSel = qs("#utm-template");
    var templates = settings.utm_templates || [];
    populateUtmTemplates(templates);

    try {
      var snip = await fetchJson(API + "/api/analytics/pixel-snippet");
      qs("#pixel-code").textContent = snip.snippet || "Brak kodu";
    } catch (e) {
      qs("#pixel-code").textContent = "Odśwież stronę lub zrestartuj GicleeApp. " + e.message;
    }
  }

  function applyUtmTemplate(t) {
    if (!t) return;
    qs("#utm-path").value = t.path || "/products/";
    qs("#utm-source").value = t.utm_source || "";
    qs("#utm-medium").value = t.utm_medium || "";
    qs("#utm-campaign").value = t.utm_campaign || "";
    refreshUtmPreview();
  }

  async function refreshUtmPreview() {
    var path = qs("#utm-path").value;
    var source = qs("#utm-source").value;
    var medium = qs("#utm-medium").value;
    var campaign = qs("#utm-campaign").value;
    var fallback = buildUtmUrlClient(path, source, medium, campaign);
    var q = "path=" + encodeURIComponent(path) +
      "&utm_source=" + encodeURIComponent(source) +
      "&utm_medium=" + encodeURIComponent(medium) +
      "&utm_campaign=" + encodeURIComponent(campaign);
    try {
      var data = await fetchJsonOptional(API + "/api/analytics/utm-preview?" + q, { url: fallback });
      qs("#utm-preview").textContent = (data && data.url) || fallback;
    } catch (e) {
      qs("#utm-preview").textContent = fallback;
    }
  }

  async function loadAll() {
    showLoading(true);
    try {
      var overview = await fetchJson(apiUrl("/api/analytics/overview"));
      var stats = overview.current || {};
      var empty = !stats.sessions && !stats.pageviews;
      qs("#empty-state").classList.toggle("hidden", !empty);
      qs("#main-content").classList.toggle("hidden", empty);

      renderKpis(overview.current, overview.previous);
      renderTimelineCharts(overview.timeline || []);

      var countries = await fetchJson(apiUrl("/api/analytics/countries"));
      renderCountries(countries);

      var funnel = await fetchJson(apiUrl("/api/analytics/funnel"));
      renderFunnel(funnel);

      var products = await fetchJson(apiUrl("/api/analytics/products"));
      renderProducts(products);

      var sources = await fetchJson(apiUrl("/api/analytics/sources"));
      renderSources(sources);

      var sessions = await fetchJson(apiUrl("/api/analytics/sessions"));
      renderSessions(sessions);

      var realtime = await fetchJson(API + "/api/analytics/realtime?minutes=15");
      renderRealtime(realtime);

      var insights = await fetchJson(apiUrl("/api/analytics/insights"));
      renderInsights(insights);

      var frames = await fetchJsonOptional(
        apiUrl("/api/analytics/frame-funnel"),
        { stages: [], event_counts: {}, total_custom_events: 0 }
      );
      renderFrameFunnel(frames);

      var status = await fetchJson(API + "/api/analytics/status");
      renderStatusBar(status);
      syncExclusionsToggle(status.settings || {}, status.exclusion_impact);
      syncMyIpToggle(status.settings || {});

      var footer = "Zakres: " + preset() + " · eventów: " +
        ((status.stats && status.stats.total_events) || 0) +
        " · sesji: " + ((status.stats && status.stats.total_sessions) || 0) +
        footerSyncNote();
      if (status.api_version != null && status.api_version < EXPECTED_API_VERSION) {
        footer += " · ⚠ stary serwer — w GicleeApp: Uruchom i otwórz dashboard";
      }
      qs("#footer-status").textContent = footer;
    } catch (e) {
      var hint = String(e.message).indexOf("404") >= 0
        ? " (zrestartuj serwer: GicleeApp → Analiza ruchu → Uruchom i otwórz dashboard)"
        : "";
      qs("#footer-status").textContent = "Błąd ładowania: " + e.message + hint;
    } finally {
      showLoading(false);
    }
  }

  async function postTestEvent() {
    if (!secret) { alert("Ustaw ANALYTICS_COLLECT_SECRET w .env"); return; }
    await fetch(API + "/api/analytics/test-event", {
      method: "POST",
      headers: { "X-Analytics-Secret": secret },
    });
    await loadAll();
  }

  function initTabs() {
    qsa(".tabs__btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var tab = btn.getAttribute("data-tab");
        qsa(".tabs__btn").forEach(function (b) { b.classList.remove("is-active"); });
        qsa(".panel").forEach(function (p) { p.classList.remove("is-active"); });
        btn.classList.add("is-active");
        qs('[data-panel="' + tab + '"]').classList.add("is-active");
        if (tab === "setup") loadSetup();
      });
    });
    qsa("[data-tab-jump]").forEach(function (el) {
      el.addEventListener("click", function () {
        qs('[data-tab="setup"]').click();
      });
    });
  }

  function initTheme() {
    qsa(".theme-toggle button").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var t = btn.getAttribute("data-theme");
        document.documentElement.setAttribute("data-theme", t);
        qsa(".theme-toggle button").forEach(function (b) { b.classList.remove("is-active"); });
        btn.classList.add("is-active");
        loadAll();
      });
    });
    qs('.theme-toggle button[data-theme="dark"]').classList.add("is-active");
  }

  function detectPublicIp() {
    var btn = qs("#btn-detect-ip");
    if (btn) {
      btn.disabled = true;
      btn.textContent = "Pobieranie…";
    }
    return fetch("https://api.ipify.org?format=json")
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (data && data.ip) {
          qs("#exclude-ip").value = data.ip;
          return data.ip;
        }
        throw new Error("empty");
      })
      .catch(function () {
        alert("Nie udało się — wpisz ręcznie publiczne IP z https://ifconfig.me");
        return null;
      })
      .finally(function () {
        if (btn) {
          btn.disabled = false;
          btn.textContent = "Pobierz moje IP";
        }
      });
  }

  function upgradeExcludeUi() {
    var ipInput = qs("#exclude-ip");
    if (!ipInput) return;
    ipInput.placeholder = "np. 85.123.45.67";
    if (qs("#btn-detect-ip")) return;

    var row = document.createElement("span");
    row.className = "ip-row";
    ipInput.parentNode.insertBefore(row, ipInput);
    row.appendChild(ipInput);
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn btn--ghost";
    btn.id = "btn-detect-ip";
    btn.textContent = "Pobierz moje IP";
    row.appendChild(btn);
    btn.addEventListener("click", detectPublicIp);

    var card = ipInput.closest(".setup-card");
    if (card) {
      var intro = card.querySelector(".panel-intro");
      if (!intro) {
        var p = document.createElement("p");
        p.className = "panel-intro";
        p.innerHTML = "Wyklucz testy z KPI. <strong>IP</strong> = publiczny (nie 192.168…). <strong>Visitor ID</strong> = pewniejsze.";
        card.insertBefore(p, card.querySelector("label"));
      }
    }
  }

  async function submitExclude() {
    var statusEl = qs("#exclude-status");
    var btn = qs("#btn-exclude");
    var vid = (qs("#exclude-visitor") && qs("#exclude-visitor").value || "").trim();
    var ip = (qs("#exclude-ip") && qs("#exclude-ip").value || "").trim();

    function setStatus(msg, ok) {
      if (statusEl) {
        statusEl.textContent = msg;
        statusEl.className = "exclude-status " + (ok ? "exclude-status--ok" : "exclude-status--err");
      }
    }

    if (!vid && !ip) {
      setStatus("Wpisz Visitor ID lub publiczne IP (przycisk „Pobierz moje IP”).", false);
      alert("Wpisz Visitor ID lub publiczne IP.");
      return;
    }

    if (btn) {
      btn.disabled = true;
      btn.textContent = "Zapisywanie…";
    }
    setStatus("Zapisywanie wykluczenia…", true);

    try {
      var res = await fetch(API + "/api/analytics/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "exclude", visitor_id: vid, ip: ip }),
      });
      var data = {};
      try {
        data = await res.json();
      } catch (parseErr) {
        throw new Error("HTTP " + res.status + " — zrestartuj serwer analityki (GicleeApp → Uruchom i otwórz dashboard)");
      }
      if (!res.ok || !data.ok) {
        throw new Error(data.error || ("HTTP " + res.status));
      }
      if (qs("#exclude-visitor")) qs("#exclude-visitor").value = "";
      if (qs("#exclude-ip")) qs("#exclude-ip").value = "";
      setStatus("✓ Wykluczenie zapisane. Odświeżam KPI…", true);
      renderExcludeList(data.settings || {});
      syncExclusionsToggle(data.settings || {});
      await loadSetup();
      await loadAll();
    } catch (e) {
      var msg = e.message || String(e);
      if (/failed to fetch|networkerror|load failed/i.test(msg)) {
        msg = "Serwer analityki nie odpowiada (127.0.0.1:5100). "
          + "GicleeApp → Marketing → Analiza ruchu → „Uruchom i otwórz dashboard”, "
          + "potem odśwież stronę (F5) i spróbuj ponownie.";
      }
      setStatus("✗ " + msg, false);
      alert("Nie udało się dodać wykluczenia:\n" + msg);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = "Dodaj wykluczenie";
      }
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    API = window.location.origin;
    upgradeExcludeUi();
    initTabs();
    initTheme();

    qs("#preset").addEventListener("change", loadAll);
    qs("#country-filter").addEventListener("change", loadAll);
    qs("#device-filter").addEventListener("change", loadAll);
    qs("#source-filter").addEventListener("change", loadAll);
    qs("#btn-test").addEventListener("click", postTestEvent);
    qs("#empty-test").addEventListener("click", postTestEvent);
    qs("#btn-export").addEventListener("click", function () {
      window.open(apiUrl("/api/analytics/export", "format=csv"), "_blank");
    });
    qs("#btn-report").addEventListener("click", function () {
      window.open(apiUrl("/api/analytics/export", "format=weekly_report&download=1"), "_blank");
    });
    qs("#btn-pull").addEventListener("click", async function () {
      var data = await pullFromWorker({ alertOnError: true, alertOnSuccess: true });
      if (data) loadAll();
    });
    qs("#btn-sync").addEventListener("click", async function () {
      try {
        var res = await fetch(API + "/api/analytics/sync-shopify?days=365", { method: "POST" });
        var data = await res.json();
        if (!res.ok || !data.ok) {
          alert("Sync Shopify: " + (data.error || "błąd HTTP " + res.status));
          return;
        }
        var msg = "Sync Shopify:\n• pobrano zamówień: " + (data.orders_fetched || 0) +
          "\n• nowe zakupy w bazie: " + (data.checkout_events_created || 0);
        if (!data.orders_fetched) {
          msg += "\n\nShopify API zwróciło 0 zamówień — sprawdź opłacone zamówienia oraz OAuth z scope read_orders (npm run oauth).";
          if (data.oauth_scopes && data.oauth_scopes.indexOf("read_orders") < 0) {
            msg += "\n\nBrak read_orders w sesji: " + (data.oauth_scopes || []).join(", ");
          }
        }
        alert(msg);
        loadAll();
      } catch (e) {
        alert("Sync Shopify nie powiódł się: " + e.message);
      }
    });
    qs("#btn-copy-pixel").addEventListener("click", function () {
      navigator.clipboard.writeText(qs("#pixel-code").textContent);
    });
    var btnExclude = qs("#btn-exclude");
    if (btnExclude) {
      btnExclude.addEventListener("click", function (e) {
        e.preventDefault();
        submitExclude();
      });
    }
    var excludeList = qs("#exclude-list");
    if (excludeList) {
      excludeList.addEventListener("click", function (e) {
        var btn = e.target.closest(".exclude-item__remove");
        if (!btn) return;
        var item = btn.closest(".exclude-item");
        if (!item) return;
        var kind = item.getAttribute("data-kind");
        var hash = item.getAttribute("data-hash");
        if (!kind || !hash) return;
        if (!confirm("Usunąć to wykluczenie z listy?")) return;
        btn.disabled = true;
        removeExclusion(kind, hash).catch(function (err) {
          alert("Nie udało się usunąć wykluczenia:\n" + err.message);
        }).finally(function () {
          btn.disabled = false;
        });
      });
    }
    var recentVisitors = qs("#recent-visitors");
    if (recentVisitors) {
      recentVisitors.addEventListener("click", function (e) {
        var btn = e.target.closest(".recent-visitor__add");
        if (!btn) return;
        var row = btn.closest(".recent-visitor");
        if (!row || row.classList.contains("recent-visitor--excluded")) return;
        var hash = row.getAttribute("data-hash");
        if (!hash) return;
        btn.disabled = true;
        btn.textContent = "…";
        excludeVisitorHash(hash).then(function () {
          return loadSetup();
        }).then(function () {
          return loadAll();
        }).catch(function (err) {
          alert("Nie udało się wykluczyć visitora:\n" + err.message);
          btn.disabled = false;
          btn.textContent = "Wyklucz";
        });
      });
    }
    var toggleMyIpEl = qs("#toggle-my-ip");
    if (toggleMyIpEl) {
      toggleMyIpEl.addEventListener("change", function () {
        var enabled = toggleMyIpEl.checked;
        toggleMyIpEl.disabled = true;
        toggleMyIp(enabled).catch(function (err) {
          var msg = err.message || String(err);
          if (/failed to fetch|networkerror|load failed/i.test(msg)) {
            msg = "Serwer analityki nie odpowiada — GicleeApp → Uruchom i otwórz dashboard, potem F5.";
          }
          toggleMyIpEl.checked = !enabled;
          alert("Wykluczenie IP:\n" + msg);
        }).finally(function () {
          toggleMyIpEl.disabled = false;
        });
      });
    }
    var toggleExclusions = qs("#toggle-exclusions");
    if (toggleExclusions) {
      toggleExclusions.addEventListener("change", function () {
        var enabled = toggleExclusions.checked;
        toggleExclusions.disabled = true;
        saveExclusionsEnabled(enabled).catch(function (err) {
          toggleExclusions.checked = !enabled;
          alert("Nie udało się zmienić wykluczeń:\n" + err.message);
        }).finally(function () {
          toggleExclusions.disabled = false;
        });
      });
    }
    qs("#btn-detect-ip") && qs("#btn-detect-ip").addEventListener("click", detectPublicIp);
    qs("#btn-copy-utm").addEventListener("click", function () {
      navigator.clipboard.writeText(qs("#utm-preview").textContent);
    });
    qs("#btn-purge-d1").addEventListener("click", async function () {
      if (!confirm("Usunąć eventy starsze niż 90 dni z D1 w chmurze?")) return;
      var res = await fetch(API + "/api/analytics/purge-worker?days=90", { method: "POST" });
      var data = await res.json();
      alert(data.ok ? "Usunięto: " + (data.deleted || 0) + " eventów" : (data.error || "Błąd"));
    });
    ["#utm-path", "#utm-source", "#utm-medium", "#utm-campaign"].forEach(function (sel) {
      qs(sel).addEventListener("input", refreshUtmPreview);
    });
    qs("#utm-template").addEventListener("change", function () {
      var i = parseInt(qs("#utm-template").value, 10);
      var fromStatus = DEFAULT_UTM_TEMPLATES;
      fetchJsonOptional(API + "/api/analytics/settings", {}).then(function (s) {
        var list = (s && s.utm_templates && s.utm_templates.length) ? s.utm_templates : DEFAULT_UTM_TEMPLATES;
        applyUtmTemplate(list[i] || fromStatus[i]);
      });
    });

    populateUtmTemplates([]);

    fetchJson(API + "/api/analytics/status").then(function (s) {
      secret = s.collect_secret_configured ? "configured" : "";
      autoSyncMs = (s.auto_sync_interval_seconds || 300) * 1000;
      syncExclusionsToggle(s.settings || {}, s.exclusion_impact);
      syncMyIpToggle(s.settings || {});
      startAutoSyncTimer();
    }).catch(function () {
      startAutoSyncTimer();
    });

    pullFromWorker({}).then(function () {
      loadAll();
    });

    setInterval(function () {
      if (qs('[data-panel="realtime"]').classList.contains("is-active")) {
        fetchJson(API + "/api/analytics/realtime?minutes=15").then(renderRealtime);
      }
      fetchJson(API + "/api/analytics/status").then(renderStatusBar).catch(function () {});
    }, 30000);
  });
})();
