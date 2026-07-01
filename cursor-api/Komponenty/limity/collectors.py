"""Zbieranie zużycia i limitów z API oraz znanych progów (USLUGI.md)."""

from __future__ import annotations

import json
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from Komponenty.dodajobraz.r2_usage import (
    collect_r2_usage,
    enrich_snapshot_with_uploads,
    format_bytes,
    usage_percent,
    usage_status,
    _fmt_int,
)

from .env_config import (
    resend_api_key,
    resend_daily_quota,
    resend_monthly_quota,
    serpapi_key,
    serpapi_monthly_quota,
)


@dataclass
class MeterRow:
    title: str
    used: int | None
    quota: int
    unit_hint: str = ""
    missing_hint: str = ""


@dataclass
class ServiceSection:
    key: str
    title: str
    subtitle: str = ""
    status: str = "Info"
    status_color: str = "#666"
    meters: list[MeterRow] = field(default_factory=list)
    info_lines: list[str] = field(default_factory=list)
    panel_url: str = ""
    error: str | None = None


USER_AGENT = "GicleeApp/1.0 (limity)"
HTTP_TIMEOUT_SEC = 22
SECTION_CACHE_TTL_SEC = 180
WORKER_DAILY_REQUEST_QUOTA = 100_000
_resend_count_cache: tuple[str, float, int, int, str] | None = None
_section_cache: dict[str, tuple[float, ServiceSection]] = {}
_cache_lock = threading.Lock()


def clear_section_cache() -> None:
    """Wymusza pełne odświeżenie API (przycisk Odśwież)."""
    global _resend_count_cache
    with _cache_lock:
        _section_cache.clear()
        _resend_count_cache = None


def _http_get_json(url: str, *, headers: dict[str, str] | None = None) -> tuple[dict, dict[str, str]]:
    hdrs = {"User-Agent": USER_AGENT}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(
        url,
        headers=hdrs,
        method="GET",
    )
    with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=HTTP_TIMEOUT_SEC) as resp:
        body = resp.read().decode("utf-8")
        hdrs = {k.lower(): v for k, v in resp.headers.items()}
        data = json.loads(body) if body.strip() else {}
        if not isinstance(data, dict):
            data = {}
        return data, hdrs


def _section_status_from_pct(pct: float) -> tuple[str, str]:
    label, color = usage_status(pct)
    return label, color


def _analytics_usage_from_worker_stats(stats: dict) -> tuple[MeterRow | None, list[str]]:
    """Meter + linie info z GET /api/analytics/stats (Worker D1)."""
    lines: list[str] = []
    if not stats.get("ok"):
        err = stats.get("error") or "brak połączenia"
        lines.append(
            f"Analityka (Worker): {err} — ustaw ANALYTICS_COLLECT_URL i ANALYTICS_COLLECT_SECRET w .env"
        )
        return None, lines
    if not stats.get("analytics"):
        msg = stats.get("message") or "D1 nie podpięte"
        lines.append(f"Analityka: {msg}")
        return None, lines

    total = int(stats.get("total_events") or 0)
    bots = int(stats.get("bot_events") or 0)
    lines.append(f"Analityka D1 — łącznie: {_fmt_int(total)} eventów (boty: {_fmt_int(bots)})")
    last = stats.get("last_event_at")
    if last:
        lines.append(f"Ostatni event w chmurze: {last}")

    meter: MeterRow | None = None
    today_raw = stats.get("events_today")
    if today_raw is not None:
        today_n = int(today_raw)
        meter = MeterRow(
            title=f"Worker — eventy analityki dziś (limit ~{WORKER_DAILY_REQUEST_QUOTA // 1000}k/d Free)",
            used=today_n,
            quota=WORKER_DAILY_REQUEST_QUOTA,
            unit_hint="eventów",
            missing_hint="ANALYTICS_COLLECT_URL + ANALYTICS_COLLECT_SECRET w .env",
        )
        remaining = max(0, WORKER_DAILY_REQUEST_QUOTA - today_n)
        lines.append(
            f"Szac. pozostało dziś (analityka): ~{_fmt_int(remaining)} requestów · "
            "mockup upload też liczy się do tego samego limitu konta"
        )
    else:
        lines.append(
            "Eventów dziś: brak w API — wdróż Worker (wrangler deploy) po aktualizacji analityki"
        )

    return meter, lines


def _worst_status(sections: list[ServiceSection]) -> tuple[str, str]:
    order = {"Krytycznie": 4, "PRZEKROCZONY": 5, "Uwaga": 3, "OK": 2, "Info": 1, "Błąd": 4}
    worst = ("Info", "#666")
    worst_rank = 0
    for sec in sections:
        if sec.error:
            rank = order.get("Błąd", 0)
            if rank >= worst_rank:
                worst_rank = rank
                worst = ("Błąd", "#c62828")
            continue
        rank = order.get(sec.status, 0)
        if rank >= worst_rank:
            worst_rank = rank
            worst = (sec.status, sec.status_color)
    return worst


def collect_cloudflare() -> ServiceSection:
    sec = ServiceSection(
        key="cloudflare",
        title="Cloudflare — R2 i Worker",
        subtitle="Bucket giclee-zoom · plan Free",
        panel_url="https://dash.cloudflare.com",
    )
    try:
        snap = collect_r2_usage()
        extra = enrich_snapshot_with_uploads(snap)
        quota_gb = snap.storage_quota_bytes / (1024**3)
        sec.meters.append(
            MeterRow(
                title=f"Magazyn R2 ({quota_gb:.0f} GB / mc)",
                used=snap.storage_bytes,
                quota=snap.storage_quota_bytes,
                unit_hint="B",
            )
        )
        sec.meters.append(
            MeterRow(
                title="Operacje Class A — zapisy, listy (1 000 000 / mc)",
                used=snap.class_a_used,
                quota=snap.class_a_quota,
                unit_hint="oper.",
                missing_hint="CLOUDFLARE_API_TOKEN w .env",
            )
        )
        sec.meters.append(
            MeterRow(
                title="Operacje Class B — odczyty (10 000 000 / mc)",
                used=snap.class_b_used,
                quota=snap.class_b_quota,
                unit_hint="oper.",
                missing_hint="CLOUDFLARE_API_TOKEN w .env",
            )
        )
        sec.info_lines = [
            f"Bucket: {snap.bucket} · źródło: {snap.source}",
            f"Plików: {_fmt_int(snap.object_count)} · zoom/: {format_bytes(snap.zoom_bytes)}",
            (
                f"customer-uploads/: {format_bytes(extra['customer_uploads_bytes'])} "
                f"({_fmt_int(extra['customer_uploads_count'])} pl.)"
            ),
            "Egress R2 → internet: bez limitu (Cloudflare Free)",
            "Worker giclee-mockup-orders: mockup upload + pixel analityki (wspólny limit konta)",
            "Max upload pliku w Workerze: 50 MB",
        ]
        try:
            from Komponenty.analytics.worker_sync import worker_stats

            a_meter, a_lines = _analytics_usage_from_worker_stats(worker_stats())
            if a_meter:
                sec.meters.append(a_meter)
            sec.info_lines.extend(a_lines)
        except Exception as exc:
            sec.info_lines.append(f"Analityka: {exc}")

        if snap.zoom_estimate_count is not None and snap.zoom_estimate_avg_bytes:
            sec.info_lines.append(
                f"Szac. kolejnych zoomów HD: ~{_fmt_int(snap.zoom_estimate_count)} "
                f"(śr. {format_bytes(snap.zoom_estimate_avg_bytes)})"
            )
        if snap.error:
            sec.info_lines.append(f"Uwaga API: {snap.error}")

        pcts = [usage_percent(snap.storage_bytes, snap.storage_quota_bytes)]
        if snap.class_a_used is not None:
            pcts.append(usage_percent(snap.class_a_used, snap.class_a_quota))
        if snap.class_b_used is not None:
            pcts.append(usage_percent(snap.class_b_used or 0, snap.class_b_quota))
        for m in sec.meters:
            if m.quota and m.used is not None and "analityki dziś" in m.title:
                pcts.append(usage_percent(m.used, m.quota))
        sec.status, sec.status_color = _section_status_from_pct(max(pcts) if pcts else 0.0)
    except Exception as exc:
        sec.error = str(exc)
        sec.status, sec.status_color = "Błąd", "#c62828"
        sec.info_lines = [
            "Sprawdź R2_* w .env oraz dostęp do bucketu giclee-zoom.",
            "Szczegóły: USLUGI.md · dodajobraz → Cloudflare",
        ]
    return sec


def _parse_quota_header(raw: str | None) -> int | None:
    if raw is None or not str(raw).strip():
        return None
    text = str(raw).strip()
    if "/" in text:
        text = text.split("/", 1)[0].strip()
    try:
        return max(0, int(text))
    except ValueError:
        return None


def _parse_resend_created_at(raw: str | None) -> datetime | None:
    if not raw:
        return None
    text = str(raw).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _count_resend_emails_from_list(api_key: str) -> tuple[int, int, str]:
    """Liczy wysłane maile w bieżącym mc/dniu (paginacja GET /emails)."""
    global _resend_count_cache
    now_ts = time.time()
    with _cache_lock:
        cached = _resend_count_cache
        if cached and cached[0] == api_key and now_ts - cached[1] < SECTION_CACHE_TTL_SEC:
            return cached[2], cached[3], cached[4] + " · cache"

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    monthly = 0
    daily = 0
    after: str | None = None
    pages = 0
    max_pages = 40

    while pages < max_pages:
        url = "https://api.resend.com/emails?limit=100"
        if after:
            url += f"&after={urllib.parse.quote(after)}"
        data, _ = _http_get_json(url, headers={"Authorization": f"Bearer {api_key}"})
        items = data.get("data") or []
        if not isinstance(items, list) or not items:
            break

        oldest_on_page: datetime | None = None
        for item in items:
            if not isinstance(item, dict):
                continue
            created = _parse_resend_created_at(str(item.get("created_at") or ""))
            if created is None:
                continue
            if oldest_on_page is None or created < oldest_on_page:
                oldest_on_page = created
            if created >= month_start:
                monthly += 1
            if created >= day_start:
                daily += 1

        pages += 1
        if not data.get("has_more"):
            break
        if oldest_on_page is not None and oldest_on_page < month_start:
            break
        after = str(items[-1].get("id") or "")
        if not after:
            break

    note = "Policzone z listy wysłanych (Resend API)"
    if pages > 1:
        note += f" · {pages} stron"
    with _cache_lock:
        _resend_count_cache = (api_key, now_ts, monthly, daily, note)
    return monthly, daily, note


def collect_resend() -> ServiceSection:
    monthly_q = resend_monthly_quota()
    daily_q = resend_daily_quota()
    sec = ServiceSection(
        key="resend",
        title="Resend — maile transakcyjne",
        subtitle="Po opłaceniu zamówienia mockup → gicleeartpl@gmail.com",
        panel_url="https://resend.com/overview",
    )
    api_key = resend_api_key()
    if not api_key:
        sec.error = "Brak RESEND_API_KEY w cursor-api/.env"
        sec.status, sec.status_color = "Info", "#666"
        sec.info_lines = [
            f"Plan Free (typowo): {daily_q} maili / dobę, {monthly_q} / mc",
            "Klucz ten sam co w Workerze (wrangler secret) — możesz skopiować do .env",
            "From: zamowienia@gicleeart.eu · Enable Receiving: OFF",
        ]
        sec.meters.append(
            MeterRow(
                title=f"Maile / mc (limit {monthly_q})",
                used=None,
                quota=monthly_q,
                unit_hint="maili",
                missing_hint="RESEND_API_KEY",
            )
        )
        return sec

    try:
        _, hdrs = _http_get_json(
            "https://api.resend.com/emails?limit=1",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        monthly_used = _parse_quota_header(hdrs.get("x-resend-monthly-quota"))
        daily_used = _parse_quota_header(hdrs.get("x-resend-daily-quota"))
        count_note = ""
        if monthly_used is None and daily_used is None:
            monthly_used, daily_used, count_note = _count_resend_emails_from_list(api_key)

        sec.meters.append(
            MeterRow(
                title=f"Maile / mc (limit {monthly_q})",
                used=monthly_used,
                quota=monthly_q,
                unit_hint="maili",
            )
        )
        if daily_used is not None or daily_q > 0:
            sec.meters.append(
                MeterRow(
                    title=f"Maile / dobę (limit {daily_q}, plan Free)",
                    used=daily_used,
                    quota=daily_q,
                    unit_hint="maili",
                )
            )
        sec.info_lines = [
            count_note or "Nagłówki x-resend-* z API (gdy dostępne)",
            "From PL: zamowienia@gicleeart.eu · intl: orders@gicleeart.eu",
            "Odbiorca merchant: gicleeartpl@gmail.com",
        ]
        pcts: list[float] = []
        if monthly_used is not None:
            pcts.append(usage_percent(monthly_used, monthly_q))
        if daily_used is not None and daily_q:
            pcts.append(usage_percent(daily_used, daily_q))
        if pcts:
            sec.status, sec.status_color = _section_status_from_pct(max(pcts))
        else:
            sec.status, sec.status_color = "OK", "#2e7d32"
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:400]
        if exc.code == 403 and "1010" in body:
            sec.error = "HTTP 403 — brak nagłówka User-Agent (wymagany przez Resend)"
            sec.status, sec.status_color = "Błąd", "#c62828"
        elif exc.code == 401 and "restricted" in body.lower():
            sec.error = None
            sec.status, sec.status_color = "Info", "#666"
            sec.meters.append(
                MeterRow(
                    title=f"Maile / mc (limit {monthly_q})",
                    used=None,
                    quota=monthly_q,
                    unit_hint="maili",
                    missing_hint="klucz Send-only — utwórz Full access (patrz niżej)",
                )
            )
            sec.info_lines = [
                "Twój klucz działa do WYSYŁKI (Worker mockup) — to dobrze.",
                "Limity nie mogą odczytać statystyk z klucza «Sending access only».",
                "Rozwiązanie: resend.com/api-keys → Create API Key → Full access",
                "→ wklej TYLKO do cursor-api/.env (RESEND_API_KEY).",
                "Worker może zostać na starym kluczu send-only (bezpieczniej).",
                f"Plan Free: {daily_q}/dobę, {monthly_q}/mc — licznik w panelu Resend.",
            ]
        elif exc.code == 401:
            sec.error = "HTTP 401 — nieprawidłowy RESEND_API_KEY (skopiuj ponownie z resend.com/api-keys)"
            sec.status, sec.status_color = "Błąd", "#c62828"
        else:
            sec.error = f"HTTP {exc.code}: {exc.reason}"
            if body:
                sec.error += f" — {body}"
            sec.status, sec.status_color = "Błąd", "#c62828"
    except Exception as exc:
        sec.error = str(exc)
        sec.status, sec.status_color = "Błąd", "#c62828"
    return sec


def collect_meta() -> ServiceSection:
    """Meta Graph API — dni do wygaśnięcia tokenów (Cykl / socialmedia)."""
    try:
        from Komponenty.socialmedia.cykl.meta_token_status import (
            analyze_meta_tokens,
            status_label_and_color,
        )
    except ImportError:
        return ServiceSection(
            key="meta",
            title="Meta — Social Media / Cykl",
            subtitle="Facebook + Instagram (4 kanały)",
            panel_url="https://developers.facebook.com",
            error="Nie można załadować modułu socialmedia/cykl",
        )

    report = analyze_meta_tokens(live_debug=False)
    status, color = status_label_and_color(report)
    sec = ServiceSection(
        key="meta",
        title="Meta — Social Media / Cykl",
        subtitle="Facebook + Instagram (4 kanały)",
        panel_url="https://developers.facebook.com",
        status=status,
        status_color=color,
    )

    if report.any_missing:
        sec.error = "Brak tokenów w data/cykl/meta_credentials.json — użyj «Odnów tokeny» lub Cykl → Ustawienia Meta API"
    elif report.any_expired:
        sec.error = "Co najmniej jeden token wygasł — użyj «Odnów tokeny»"

    quota_days = 60
    if report.days_left_min is not None:
        elapsed = max(0, quota_days - report.days_left_min)
        sec.meters.append(
            MeterRow(
                title=f"Pozostało {report.days_left_min} dni do wygaśnięcia",
                used=elapsed,
                quota=quota_days,
                unit_hint="dni",
            )
        )
        sec.info_lines.append(
            f"Od ostatniej odnowy minęło {elapsed} dni · limit long-lived: {quota_days} dni"
        )
    else:
        sec.meters.append(
            MeterRow(
                title="Pozostało dni do wygaśnięcia",
                used=None,
                quota=quota_days,
                unit_hint="dni",
                missing_hint="brak daty odnowy — użyj «Odnów tokeny»",
            )
        )

    for ch in report.channels:
        sec.info_lines.append(f"{ch.label}: {ch.detail}")

    sec.info_lines.append("Graph API: ~200 wywołań / h · Caption IG ~2200 znaków")
    if report.note:
        sec.info_lines.append(report.note)

    if report.days_left_min is not None and report.days_left_min <= 14:
        sec.status, sec.status_color = (
            ("Wygasły", "#c62828") if report.days_left_min <= 0 else ("Uwaga", "#f57f17")
        )

    return sec


def collect_serpapi() -> ServiceSection:
    sec = ServiceSection(
        key="serpapi",
        title="SerpAPI — Nazwij obraz",
        subtitle="Google Lens i wyszukiwania tekstowe",
        panel_url="https://serpapi.com/dashboard",
    )
    key = serpapi_key()
    fallback_q = serpapi_monthly_quota()
    if not key:
        sec.error = "Brak SERPAPI_KEY w .env"
        sec.status, sec.status_color = "Info", "#666"
        sec.meters.append(
            MeterRow(
                title=f"Zapytania / mc (plan Free ~{fallback_q})",
                used=None,
                quota=fallback_q,
                unit_hint="zapytań",
                missing_hint="SERPAPI_KEY",
            )
        )
        sec.info_lines = ["Account API jest darmowe — nie zużywa limitu wyszukiwań"]
        return sec

    try:
        qs = urllib.parse.urlencode({"api_key": key})
        data, _ = _http_get_json(f"https://serpapi.com/account.json?{qs}")
        monthly_q = int(data.get("searches_per_month") or fallback_q)
        used = int(data.get("this_month_usage") or 0)
        left = data.get("plan_searches_left")
        plan = str(data.get("plan_name") or data.get("plan_id") or "—")
        hourly = data.get("account_rate_limit_per_hour")
        last_hour = data.get("last_hour_searches")

        sec.meters.append(
            MeterRow(
                title=f"Zapytania / mc ({plan})",
                used=used,
                quota=monthly_q,
                unit_hint="zapytań",
            )
        )
        sec.info_lines = [
            f"Pozostało w planie: {_fmt_int(int(left))}" if left is not None else "",
            f"Limit godzinowy: {_fmt_int(int(hourly))} / h" if hourly else "",
            f"Ostatnia godzina: {_fmt_int(int(last_hour))} zapytań" if last_hour is not None else "",
            "Account API nie liczy się do limitu wyszukiwań",
        ]
        sec.info_lines = [ln for ln in sec.info_lines if ln]
        sec.status, sec.status_color = _section_status_from_pct(usage_percent(used, monthly_q))
    except Exception as exc:
        sec.error = str(exc)
        sec.status, sec.status_color = "Błąd", "#c62828"
    return sec


def collect_static_services() -> list[ServiceSection]:
    """Usługi bez API w .env — znane progi z USLUGI.md."""
    return [
        ServiceSection(
            key="shopify",
            title="Shopify",
            subtitle="Sklep gicleeart.eu · plan Standardowy",
            panel_url="https://admin.shopify.com",
            status="Info",
            status_color="#666",
            info_lines=[
                "Limity API: throttle Shopify (REST/GraphQL) — przy masowych operacjach w dodajobraz",
                "Markets: 7 rynków · webhook orders/paid → Worker",
                "Abonament i opłaty transakcyjne: uzupełnij w USLUGI.md",
            ],
        ),
        ServiceSection(
            key="nbp",
            title="NBP API",
            subtitle="Kursy walut w dodajobraz → Rynki",
            panel_url="https://api.nbp.pl",
            status="OK",
            status_color="#2e7d32",
            info_lines=[
                "Darmowe, bez klucza · cache lokalny 24 h",
                "Brak miesięcznego limitu w typowym użyciu sklepu",
            ],
        ),
        ServiceSection(
            key="vercel",
            title="Vercel — GicleeLab",
            subtitle="kalkulator1-henna.vercel.app",
            panel_url="https://vercel.com/dashboard",
            status="Info",
            status_color="#666",
            info_lines=[
                "Iframe kalkulatora PPI na stronie fotografia-obraz",
                "Logika skopiowana lokalnie do lib/giclee-print-analysis/",
                "Plan i limity: panel Vercel · uzupełnij w USLUGI.md",
            ],
        ),
    ]


def _cached_section(key: str, builder: Callable[[], ServiceSection]) -> ServiceSection:
    now = time.time()
    with _cache_lock:
        hit = _section_cache.get(key)
        if hit and now - hit[0] < SECTION_CACHE_TTL_SEC:
            return hit[1]
    sec = builder()
    with _cache_lock:
        _section_cache[key] = (time.time(), sec)
    return sec


def collect_all(*, use_cache: bool = True) -> tuple[list[ServiceSection], tuple[str, str]]:
    """Zbiera wszystkie sekcje równolegle; zwraca (lista, globalny status)."""
    api_collectors: list[tuple[str, Callable[[], ServiceSection]]] = [
        ("cloudflare", collect_cloudflare),
        ("resend", collect_resend),
        ("serpapi", collect_serpapi),
        ("meta", collect_meta),
    ]
    static = collect_static_services()
    meta_sec = _cached_section("meta", collect_meta) if use_cache else collect_meta()
    by_key: dict[str, ServiceSection] = {"meta": meta_sec}

    def _run(key: str, fn: Callable[[], ServiceSection]) -> ServiceSection:
        if key == "meta":
            return meta_sec
        if use_cache:
            return _cached_section(key, fn)
        return fn()

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(_run, key, fn): key for key, fn in api_collectors if key != "meta"
        }
        for fut in as_completed(futures):
            key = futures[fut]
            by_key[key] = fut.result()

    order = ("cloudflare", "resend", "serpapi", "meta")
    sections = [by_key[k] for k in order if k in by_key] + static
    return sections, _worst_status(sections)


def collect_all_progressive(
    on_section: Callable[[ServiceSection], None],
    *,
    use_cache: bool = True,
) -> tuple[list[ServiceSection], tuple[str, str]]:
    """Jak collect_all, ale wywołuje on_section zaraz po każdej gotowej sekcji API."""
    static = collect_static_services()
    meta_sec = _cached_section("meta", collect_meta) if use_cache else collect_meta()
    on_section(meta_sec)
    by_key: dict[str, ServiceSection] = {"meta": meta_sec}

    api_collectors: list[tuple[str, Callable[[], ServiceSection]]] = [
        ("cloudflare", collect_cloudflare),
        ("resend", collect_resend),
        ("serpapi", collect_serpapi),
    ]

    def _run(key: str, fn: Callable[[], ServiceSection]) -> ServiceSection:
        sec = _cached_section(key, fn) if use_cache else fn()
        on_section(sec)
        return sec

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(_run, key, fn): key for key, fn in api_collectors}
        for fut in as_completed(futures):
            key = futures[fut]
            by_key[key] = fut.result()

    order = ("cloudflare", "resend", "serpapi", "meta")
    sections = [by_key[k] for k in order if k in by_key] + static
    return sections, _worst_status(sections)
