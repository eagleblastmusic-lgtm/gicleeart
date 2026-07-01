"""Obliczenia KPI, lejka i agregacji."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any

from .models import FUNNEL_STAGES
from . import storage


def _safe_div(num: float, den: float) -> float:
    if not den:
        return 0.0
    return round(num / den, 4)


def _delta_pct(current: float, previous: float) -> float | None:
    if not previous:
        return None
    return round((current - previous) / previous, 4)


def parse_date_range(
    preset: str = "7d",
    date_from: str | None = None,
    date_to: str | None = None,
) -> tuple[str, str, str, str]:
    """Zwraca (from_iso, to_iso, prev_from_iso, prev_to_iso)."""
    now = datetime.now(timezone.utc)
    today = now.date()

    if date_from and date_to:
        start = datetime.fromisoformat(date_from[:10]).replace(tzinfo=timezone.utc)
        end = datetime.fromisoformat(date_to[:10]).replace(tzinfo=timezone.utc) + timedelta(days=1)
        span = (end - start).days
        prev_end = start
        prev_start = prev_end - timedelta(days=span)
        return (
            start.strftime("%Y-%m-%dT00:00:00Z"),
            end.strftime("%Y-%m-%dT00:00:00Z"),
            prev_start.strftime("%Y-%m-%dT00:00:00Z"),
            prev_end.strftime("%Y-%m-%dT00:00:00Z"),
        )

    presets = {
        "today": 1,
        "yesterday": 1,
        "7d": 7,
        "30d": 30,
        "month": today.day,
        "prev_month": 30,
    }
    days = presets.get(preset, 7)
    if preset == "yesterday":
        end_d = today
        start_d = today - timedelta(days=1)
    elif preset == "month":
        start_d = today.replace(day=1)
        end_d = today + timedelta(days=1)
    elif preset == "prev_month":
        first_this = today.replace(day=1)
        end_d = first_this
        start_d = (first_this - timedelta(days=1)).replace(day=1)
    else:
        end_d = today + timedelta(days=1)
        start_d = end_d - timedelta(days=days)

    span = (end_d - start_d).days or 1
    prev_end = start_d
    prev_start = prev_end - timedelta(days=span)

    return (
        datetime.combine(start_d, datetime.min.time(), tzinfo=timezone.utc).strftime(
            "%Y-%m-%dT00:00:00Z"
        ),
        datetime.combine(end_d, datetime.min.time(), tzinfo=timezone.utc).strftime(
            "%Y-%m-%dT00:00:00Z"
        ),
        datetime.combine(prev_start, datetime.min.time(), tzinfo=timezone.utc).strftime(
            "%Y-%m-%dT00:00:00Z"
        ),
        datetime.combine(prev_end, datetime.min.time(), tzinfo=timezone.utc).strftime(
            "%Y-%m-%dT00:00:00Z"
        ),
    )


def _load_events_range(
    date_from: str,
    date_to: str,
    *,
    country: str | None = None,
    device: str | None = None,
    source: str | None = None,
) -> list[dict[str, Any]]:
    return storage.query_events(
        date_from=date_from,
        date_to=date_to,
        country=country,
        device=device,
        source=source,
        exclude_bots=True,
        limit=100_000,
    )


def _sessions_range(date_from: str, date_to: str) -> list[dict[str, Any]]:
    return storage.query_sessions(date_from=date_from, date_to=date_to, limit=50_000)


def compute_overview(
    date_from: str,
    date_to: str,
    *,
    country: str | None = None,
    device: str | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    events = _load_events_range(date_from, date_to, country=country, device=device, source=source)
    sessions = _sessions_range(date_from, date_to)
    if country:
        cc = country.upper()
        sessions = [s for s in sessions if (s.get("country") or "").upper() == cc]
    if device:
        sessions = [s for s in sessions if (s.get("device_type") or "") == device]
    if source:
        sessions = [s for s in sessions if (s.get("source_bucket") or "") == source]

    visitors = len({e["visitor_id_hash"] for e in events if e.get("visitor_id_hash")})
    session_ids = {e["session_id"] for e in events if e.get("session_id")}
    sessions_count = len(session_ids) or len(sessions)

    pageviews = sum(1 for e in events if e["event_name"] == "page_viewed")
    product_views = sum(1 for e in events if e["event_name"] == "product_viewed")
    add_to_carts = sum(1 for e in events if e["event_name"] == "product_added_to_cart")
    checkouts = sum(1 for e in events if e["event_name"] == "checkout_started")
    purchases = sum(1 for e in events if e["event_name"] == "checkout_completed")

    revenue = sum(
        float(e.get("order_value") or e.get("checkout_value") or 0)
        for e in events
        if e["event_name"] == "checkout_completed"
    )

    bounce_sessions = sum(
        1 for s in sessions
        if int(s.get("pageviews_count") or 0) <= 1
    )
    bounce_rate = _safe_div(bounce_sessions, len(sessions) or sessions_count)

    avg_duration = _avg_session_duration(events)

    return {
        "entrances": pageviews,
        "visitors": visitors,
        "sessions": sessions_count,
        "pageviews": pageviews,
        "product_views": product_views,
        "add_to_carts": add_to_carts,
        "checkouts_started": checkouts,
        "purchases": purchases,
        "revenue": round(revenue, 2),
        "conversion_rate": _safe_div(purchases, sessions_count),
        "add_to_cart_rate": _safe_div(add_to_carts, product_views),
        "checkout_start_rate": _safe_div(checkouts, add_to_carts),
        "checkout_completion_rate": _safe_div(purchases, checkouts),
        "average_order_value": _safe_div(revenue, purchases),
        "revenue_per_visitor": _safe_div(revenue, visitors),
        "bounce_rate": bounce_rate,
        "avg_session_seconds": avg_duration,
        "quality_score": traffic_quality_score(
            conversion_rate=_safe_div(purchases, sessions_count),
            add_to_cart_rate=_safe_div(add_to_carts, product_views),
            bounce_rate=bounce_rate,
            revenue_per_visitor=_safe_div(revenue, visitors),
        ),
    }


def traffic_quality_score(
    *,
    conversion_rate: float,
    add_to_cart_rate: float,
    bounce_rate: float,
    revenue_per_visitor: float,
) -> int:
    score = 0.0
    score += min(conversion_rate * 2000, 30)
    score += min(add_to_cart_rate * 100, 25)
    score += max(0, 25 - bounce_rate * 25)
    score += min(revenue_per_visitor * 2, 20)
    return int(max(0, min(100, round(score))))


def _avg_session_duration(events: list[dict[str, Any]]) -> float:
    by_session: dict[str, list[str]] = defaultdict(list)
    for e in events:
        sid = e.get("session_id")
        ts = e.get("created_at")
        if sid and ts:
            by_session[sid].append(ts)
    durations: list[float] = []
    for times in by_session.values():
        if len(times) < 2:
            continue
        try:
            start = datetime.fromisoformat(min(times).replace("Z", "+00:00"))
            end = datetime.fromisoformat(max(times).replace("Z", "+00:00"))
            durations.append((end - start).total_seconds())
        except ValueError:
            continue
    if not durations:
        return 0.0
    return round(sum(durations) / len(durations), 1)


def compute_countries(date_from: str, date_to: str) -> dict[str, Any]:
    events = _load_events_range(date_from, date_to)
    by_country: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "country": "",
        "visitors": set(),
        "sessions": set(),
        "pageviews": 0,
        "product_views": 0,
        "add_to_carts": 0,
        "checkouts_started": 0,
        "purchases": 0,
        "revenue": 0.0,
    })

    for e in events:
        cc = (e.get("country") or "unknown").upper()
        row = by_country[cc]
        row["country"] = cc
        if e.get("visitor_id_hash"):
            row["visitors"].add(e["visitor_id_hash"])
        if e.get("session_id"):
            row["sessions"].add(e["session_id"])
        name = e["event_name"]
        if name == "page_viewed":
            row["pageviews"] += 1
        elif name == "product_viewed":
            row["product_views"] += 1
        elif name == "product_added_to_cart":
            row["add_to_carts"] += 1
        elif name == "checkout_started":
            row["checkouts_started"] += 1
        elif name == "checkout_completed":
            row["purchases"] += 1
            row["revenue"] += float(e.get("order_value") or e.get("checkout_value") or 0)

    total_sessions = sum(len(r["sessions"]) for r in by_country.values()) or 1
    total_revenue = sum(r["revenue"] for r in by_country.values()) or 1

    rows = []
    for cc, r in sorted(by_country.items(), key=lambda x: len(x[1]["sessions"]), reverse=True):
        sess = len(r["sessions"])
        purch = r["purchases"]
        rev = round(r["revenue"], 2)
        rows.append({
            "country": cc,
            "visitors": len(r["visitors"]),
            "sessions": sess,
            "pageviews": r["pageviews"],
            "product_views": r["product_views"],
            "add_to_carts": r["add_to_carts"],
            "checkouts_started": r["checkouts_started"],
            "purchases": purch,
            "revenue": rev,
            "conversion_rate": _safe_div(purch, sess),
            "average_order_value": _safe_div(rev, purch),
            "traffic_share": _safe_div(sess, total_sessions),
            "revenue_share": _safe_div(rev, total_revenue),
        })

    pl_sessions = sum(r["sessions"] for r in rows if r["country"] == "PL")
    foreign_sessions = sum(r["sessions"] for r in rows if r["country"] not in ("PL", "unknown"))

    return {
        "countries": rows,
        "poland_vs_foreign": {
            "poland_sessions": pl_sessions,
            "foreign_sessions": foreign_sessions,
            "poland_share": _safe_div(pl_sessions, total_sessions),
        },
    }


def compute_funnel(
    date_from: str,
    date_to: str,
    *,
    country: str | None = None,
    device: str | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    events = _load_events_range(date_from, date_to, country=country, device=device, source=source)
    return {"stages": _funnel_stages_from_events(events)}


def _funnel_stages_from_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stages: list[dict[str, Any]] = []
    prev_users = 0

    for stage in FUNNEL_STAGES:
        users = {
            e["visitor_id_hash"]
            for e in events
            if e["event_name"] == stage and e.get("visitor_id_hash")
        }
        sessions = {
            e["session_id"]
            for e in events
            if e["event_name"] == stage and e.get("session_id")
        }
        count_users = len(users)
        count_sessions = len(sessions)
        step_rate = _safe_div(count_users, prev_users) if prev_users else 1.0
        drop_off = round(1.0 - step_rate, 4) if prev_users else 0.0

        lost_revenue = 0.0
        if stage == "checkout_started" and count_sessions:
            avg_order = _avg_order_value(events)
            completed = sum(1 for e in events if e["event_name"] == "checkout_completed")
            lost_revenue = round(max(0, count_sessions - completed) * avg_order * 0.3, 2)

        stages.append({
            "stage": stage,
            "users": count_users,
            "sessions": count_sessions,
            "step_rate": step_rate if prev_users else 1.0,
            "drop_off_rate": drop_off,
            "estimated_lost_revenue": lost_revenue,
        })
        prev_users = count_users or prev_users

    return stages


def compute_funnel_compare(
    date_from: str,
    date_to: str,
    prev_from: str,
    prev_to: str,
    *,
    country: str | None = None,
    device: str | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    current = compute_funnel(date_from, date_to, country=country, device=device, source=source)
    previous = compute_funnel(prev_from, prev_to, country=country, device=device, source=source)
    prev_by_stage = {s["stage"]: s for s in previous["stages"]}
    stages = []
    for s in current["stages"]:
        p = prev_by_stage.get(s["stage"], {})
        stages.append({
            **s,
            "prev_users": p.get("users", 0),
            "users_delta": _delta_pct(s["users"], p.get("users", 0)),
        })
    return {"stages": stages, "previous": previous["stages"]}


def _avg_order_value(events: list[dict[str, Any]]) -> float:
    vals = [
        float(e.get("order_value") or e.get("checkout_value") or 0)
        for e in events
        if e["event_name"] == "checkout_completed"
    ]
    return _safe_div(sum(vals), len(vals))


def compute_products(
    date_from: str,
    date_to: str,
    *,
    country: str | None = None,
    device: str | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    events = _load_events_range(date_from, date_to, country=country, device=device, source=source)
    return {"products": _products_from_events(events)}


def _products_from_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_product: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "shopify_product_id": "",
        "product_title": "",
        "views": 0,
        "unique_viewers": set(),
        "unique_by_day": defaultdict(set),
        "add_to_carts": 0,
        "checkouts": 0,
        "purchases": 0,
        "revenue": 0.0,
        "countries": set(),
        "sources": set(),
    })

    for e in events:
        pid = e.get("shopify_product_id")
        if not pid:
            continue
        row = by_product[str(pid)]
        row["shopify_product_id"] = str(pid)
        if e.get("product_title"):
            row["product_title"] = e["product_title"]
        if e.get("country"):
            row["countries"].add(e["country"])
        if e.get("source_bucket"):
            row["sources"].add(e["source_bucket"])
        name = e["event_name"]
        if name == "product_viewed":
            row["views"] += 1
            vhash = e.get("visitor_id_hash") or e.get("session_id")
            if vhash:
                row["unique_viewers"].add(str(vhash))
                day = (e.get("created_at") or "")[:10]
                if day:
                    row["unique_by_day"][day].add(str(vhash))
        elif name == "product_added_to_cart":
            row["add_to_carts"] += 1
        elif name == "checkout_started":
            row["checkouts"] += 1
        elif name == "checkout_completed":
            row["purchases"] += 1
            row["revenue"] += float(e.get("order_value") or 0)

    products = []
    for pid, r in sorted(
        by_product.items(),
        key=lambda x: (len(x[1]["unique_viewers"]), x[1]["views"]),
        reverse=True,
    ):
        views = r["views"]
        unique = len(r["unique_viewers"])
        daily_uniques = [len(v) for v in r["unique_by_day"].values()]
        if daily_uniques:
            avg_daily_unique = round(sum(daily_uniques) / len(daily_uniques), 1)
        elif unique:
            avg_daily_unique = float(unique)
        else:
            avg_daily_unique = 0.0
        atc = r["add_to_carts"]
        purch = r["purchases"]
        rev = round(r["revenue"], 2)
        conv = _safe_div(purch, unique or views)
        alert = unique >= 5 and conv < 0.02 and atc < unique * 0.05
        products.append({
            "shopify_product_id": pid,
            "product_title": r["product_title"] or pid,
            "views": views,
            "unique_viewers": unique,
            "avg_daily_unique": avg_daily_unique,
            "add_to_carts": atc,
            "add_to_cart_rate": _safe_div(atc, unique or views),
            "checkouts": r["checkouts"],
            "purchases": purch,
            "revenue": rev,
            "conversion_rate": conv,
            "average_order_value": _safe_div(rev, purch),
            "countries": sorted(r["countries"]),
            "sources": sorted(r["sources"]),
            "high_traffic_low_conversion": alert,
        })

    return products


def compute_products_compare(
    date_from: str,
    date_to: str,
    prev_from: str,
    prev_to: str,
    *,
    country: str | None = None,
    device: str | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    cur_events = _load_events_range(date_from, date_to, country=country, device=device, source=source)
    prev_events = _load_events_range(prev_from, prev_to, country=country, device=device, source=source)
    current = _products_from_events(cur_events)
    previous = {p["shopify_product_id"]: p for p in _products_from_events(prev_events)}
    out = []
    for p in current:
        prev = previous.get(p["shopify_product_id"], {})
        out.append({
            **p,
            "prev_unique_viewers": prev.get("unique_viewers", 0),
            "unique_delta": _delta_pct(p["unique_viewers"], prev.get("unique_viewers", 0)),
            "prev_views": prev.get("views", 0),
            "views_delta": _delta_pct(p["views"], prev.get("views", 0)),
        })
    return {"products": out}


def compute_sources(date_from: str, date_to: str) -> dict[str, Any]:
    events = _load_events_range(date_from, date_to)
    by_src: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "source": "",
        "visitors": set(),
        "sessions": set(),
        "pageviews": 0,
        "product_views": 0,
        "add_to_carts": 0,
        "checkouts_started": 0,
        "purchases": 0,
        "revenue": 0.0,
    })

    for e in events:
        src = e.get("source_bucket") or "unknown"
        row = by_src[src]
        row["source"] = src
        if e.get("visitor_id_hash"):
            row["visitors"].add(e["visitor_id_hash"])
        if e.get("session_id"):
            row["sessions"].add(e["session_id"])
        name = e["event_name"]
        if name == "page_viewed":
            row["pageviews"] += 1
        elif name == "product_viewed":
            row["product_views"] += 1
        elif name == "product_added_to_cart":
            row["add_to_carts"] += 1
        elif name == "checkout_started":
            row["checkouts_started"] += 1
        elif name == "checkout_completed":
            row["purchases"] += 1
            row["revenue"] += float(e.get("order_value") or 0)

    rows = []
    for src, r in sorted(by_src.items(), key=lambda x: len(x[1]["sessions"]), reverse=True):
        sess = len(r["sessions"])
        purch = r["purchases"]
        rev = round(r["revenue"], 2)
        rows.append({
            "source": src,
            "visitors": len(r["visitors"]),
            "sessions": sess,
            "pageviews": r["pageviews"],
            "product_views": r["product_views"],
            "add_to_carts": r["add_to_carts"],
            "checkouts_started": r["checkouts_started"],
            "purchases": purch,
            "revenue": rev,
            "conversion_rate": _safe_div(purch, sess),
            "average_order_value": _safe_div(rev, purch),
        })

    utm_rows = _utm_breakdown(events)
    return {"sources": rows, "utm_campaigns": utm_rows}


def _utm_breakdown(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_camp: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "utm_source": "",
        "utm_medium": "",
        "utm_campaign": "",
        "sessions": set(),
        "purchases": 0,
        "revenue": 0.0,
    })
    for e in events:
        camp = e.get("utm_campaign") or "(none)"
        key = f"{e.get('utm_source')}|{e.get('utm_medium')}|{camp}"
        row = by_camp[key]
        row["utm_source"] = e.get("utm_source") or ""
        row["utm_medium"] = e.get("utm_medium") or ""
        row["utm_campaign"] = camp
        if e.get("session_id"):
            row["sessions"].add(e["session_id"])
        if e["event_name"] == "checkout_completed":
            row["purchases"] += 1
            row["revenue"] += float(e.get("order_value") or 0)

    out = []
    for _, r in sorted(by_camp.items(), key=lambda x: len(x[1]["sessions"]), reverse=True)[:50]:
        out.append({
            "utm_source": r["utm_source"],
            "utm_medium": r["utm_medium"],
            "utm_campaign": r["utm_campaign"],
            "sessions": len(r["sessions"]),
            "purchases": r["purchases"],
            "revenue": round(r["revenue"], 2),
        })
    return out


def compute_realtime(minutes: int = 15) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    start = (now - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    events = storage.query_events(date_from=start, date_to=end, limit=2000)

    active_visitors = len({e["visitor_id_hash"] for e in events if e.get("visitor_id_hash")})
    pages: dict[str, int] = defaultdict(int)
    products: dict[str, int] = defaultdict(int)
    countries: dict[str, int] = defaultdict(int)
    recent: list[dict[str, Any]] = []

    for e in sorted(events, key=lambda x: x.get("created_at") or "", reverse=True)[:30]:
        recent.append({
            "event_name": e["event_name"],
            "path": e.get("path") or "",
            "product_title": e.get("product_title") or "",
            "country": e.get("country") or "",
            "created_at": e.get("created_at") or "",
        })

    for e in events:
        if e["event_name"] == "page_viewed" and e.get("path"):
            pages[e["path"]] += 1
        if e["event_name"] == "product_viewed":
            title = e.get("product_title") or e.get("shopify_product_id") or "?"
            products[str(title)] += 1
        cc = e.get("country") or "unknown"
        countries[cc] += 1

    return {
        "active_visitors": active_visitors,
        "window_minutes": minutes,
        "top_pages": sorted(pages.items(), key=lambda x: -x[1])[:10],
        "top_products": sorted(products.items(), key=lambda x: -x[1])[:10],
        "countries": sorted(countries.items(), key=lambda x: -x[1])[:10],
        "recent_events": recent,
        "recent_add_to_cart": [
            r for r in recent if r["event_name"] == "product_added_to_cart"
        ][:5],
        "recent_checkouts": [
            r for r in recent if r["event_name"] == "checkout_started"
        ][:5],
        "recent_purchases": [
            r for r in recent if r["event_name"] == "checkout_completed"
        ][:5],
    }


def compute_timeline(date_from: str, date_to: str, **filters: Any) -> list[dict[str, Any]]:
    events = _load_events_range(date_from, date_to, **filters)
    by_day: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "date": "",
        "sessions": set(),
        "visitors": set(),
        "pageviews": 0,
        "purchases": 0,
        "revenue": 0.0,
    })
    for e in events:
        day = (e.get("created_at") or "")[:10]
        if not day:
            continue
        row = by_day[day]
        row["date"] = day
        if e.get("session_id"):
            row["sessions"].add(e["session_id"])
        if e.get("visitor_id_hash"):
            row["visitors"].add(e["visitor_id_hash"])
        if e["event_name"] == "page_viewed":
            row["pageviews"] += 1
        if e["event_name"] == "checkout_completed":
            row["purchases"] += 1
            row["revenue"] += float(e.get("order_value") or 0)

    return [
        {
            "date": r["date"],
            "sessions": len(r["sessions"]),
            "unique_visitors": len(r["visitors"]),
            "pageviews": r["pageviews"],
            "purchases": r["purchases"],
            "revenue": round(r["revenue"], 2),
            "conversion_rate": _safe_div(r["purchases"], len(r["sessions"])),
        }
        for _, r in sorted(by_day.items())
    ]


def compute_insights(
    current: dict[str, Any],
    previous: dict[str, Any],
    countries: dict[str, Any],
    products: dict[str, Any],
    funnel: dict[str, Any],
) -> list[dict[str, str]]:
    insights: list[dict[str, str]] = []
    total_events = current.get("pageviews", 0) + current.get("product_views", 0)

    if total_events >= 5:
        top = (products.get("products") or [])[:3]
        if top:
            names = ", ".join(
                f"{p['product_title']} ({p.get('unique_viewers', p['views'])} unikalnych)"
                for p in top
            )
            insights.append({
                "type": "info",
                "title": "Top 3 obrazy po unikalnych",
                "body": names,
            })

        if current.get("sessions", 0) >= 3:
            avg_prod = _safe_div(current.get("product_views", 0), current.get("sessions", 0))
            insights.append({
                "type": "info",
                "title": "Produkty na sesję",
                "body": f"Średnio {avg_prod:.1f} wyświetleń produktu na sesję.",
            })

        pf = countries.get("poland_vs_foreign") or {}
        pl_share = pf.get("poland_share", 0)
        if pl_share:
            insights.append({
                "type": "info",
                "title": "Geografia ruchu",
                "body": f"{pl_share * 100:.0f}% sesji z Polski (PL: {pf.get('poland_sessions', 0)}, zagranica: {pf.get('foreign_sessions', 0)}).",
            })

    if current.get("purchases", 0) >= 1 and previous.get("conversion_rate", 0) > 0:
        if current["conversion_rate"] < previous.get("conversion_rate", 0) * 0.85:
            insights.append({
                "type": "warn",
                "title": "Spadek konwersji",
                "body": "Konwersja spadła względem poprzedniego okresu.",
            })

    for p in products.get("products", [])[:20]:
        if p.get("high_traffic_low_conversion"):
            insights.append({
                "type": "alert",
                "title": "Duży ruch, słaba konwersja",
                "body": f"{p['product_title']}: {p['views']} wyświetleń, konwersja {p['conversion_rate']:.1%}.",
            })

    for c in countries.get("countries", [])[:10]:
        if c["sessions"] >= 20 and c["conversion_rate"] < 0.005:
            insights.append({
                "type": "info",
                "title": f"Kraj {c['country']}: ruch bez sprzedaży",
                "body": f"{c['sessions']} sesji, {c['purchases']} zakupów.",
            })
        if c["sessions"] >= 2 and c.get("average_order_value", 0) > current.get("average_order_value", 0) * 1.5:
            insights.append({
                "type": "success",
                "title": f"Kraj {c['country']}: wysoki AOV",
                "body": f"Mały ruch, ale wysoka wartość koszyka.",
            })

    stages = {s["stage"]: s for s in funnel.get("stages", [])}
    atc = stages.get("product_added_to_cart", {})
    chk = stages.get("checkout_started", {})
    if atc.get("sessions", 0) > 2 and chk.get("drop_off_rate", 0) > 0.6:
        insights.append({
            "type": "warn",
            "title": "Porzucenia koszyk → checkout",
            "body": "Duży odpad między dodaniem do koszyka a checkoutem.",
        })

    if total_events < 50:
        insights.append({
            "type": "info",
            "title": "Mała próbka danych",
            "body": "Pełne alerty konwersji pojawią się przy większym ruchu sklepu.",
        })

    return insights[:15]


FRAME_FUNNEL_STAGES = (
    "giclee_app:frame_config_started",
    "giclee_app:frame_size_selected",
    "giclee_app:frame_color_selected",
    "giclee_app:price_calculated",
    "giclee_app:cta_clicked",
)


def compute_frame_funnel(
    date_from: str,
    date_to: str,
    **filters: Any,
) -> dict[str, Any]:
    events = _load_events_range(date_from, date_to, **filters)
    frame_events = [e for e in events if str(e.get("event_name", "")).startswith("giclee_app:")]
    stages: list[dict[str, Any]] = []
    prev_users = 0

    for stage in FRAME_FUNNEL_STAGES:
        users = {
            e["visitor_id_hash"]
            for e in frame_events
            if e["event_name"] == stage and e.get("visitor_id_hash")
        }
        count = len(users)
        step_rate = _safe_div(count, prev_users) if prev_users else 1.0
        stages.append({
            "stage": stage.replace("giclee_app:", ""),
            "users": count,
            "step_rate": step_rate if prev_users else 1.0,
            "drop_off_rate": round(1.0 - step_rate, 4) if prev_users else 0.0,
        })
        prev_users = count or prev_users

    by_event: dict[str, int] = defaultdict(int)
    for e in frame_events:
        by_event[e["event_name"]] += 1

    return {
        "stages": stages,
        "event_counts": dict(sorted(by_event.items(), key=lambda x: -x[1])),
        "total_custom_events": len(frame_events),
    }


def build_weekly_report(date_from: str, date_to: str, **filters: Any) -> dict[str, Any]:
    overview = compute_overview(date_from, date_to, **filters)
    products = compute_products(date_from, date_to, **filters)
    countries = compute_countries(date_from, date_to)
    funnel = compute_funnel(date_from, date_to, **filters)
    sources = compute_sources(date_from, date_to)
    timeline = compute_timeline(date_from, date_to, **filters)
    return {
        "generated_at": storage.utc_now_iso(),
        "range": {"from": date_from, "to": date_to},
        "overview": overview,
        "timeline": timeline,
        "top_products": (products.get("products") or [])[:10],
        "top_countries": (countries.get("countries") or [])[:5],
        "funnel": funnel.get("stages"),
        "sources": (sources.get("sources") or [])[:5],
    }


def session_timeline(session_id: str) -> dict[str, Any]:
    events = storage.query_events(
        date_from="1970-01-01T00:00:00Z",
        date_to="9999-12-31T23:59:59Z",
        limit=500,
    )
    sess_events = [e for e in events if e.get("session_id") == session_id]
    sess_events.sort(key=lambda x: x.get("created_at") or "")
    return {
        "session_id": session_id,
        "events": [
            {
                "event_name": e["event_name"],
                "created_at": e.get("created_at"),
                "path": e.get("path"),
                "product_title": e.get("product_title"),
            }
            for e in sess_events
        ],
    }
