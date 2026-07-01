"""Budowa i aktualizacja sesji z eventów (collect + sync z chmury)."""

from __future__ import annotations

from typing import Any

from . import storage


def apply_event_to_session(row: dict[str, Any]) -> None:
    """Aktualizuje analytics_sessions na podstawie wiersza z analytics_events."""
    if int(row.get("bot_suspected") or 0):
        return

    session_id = str(row.get("session_id") or "").strip()
    if not session_id:
        return

    event_name = str(row.get("event_name") or "")
    created_at = str(row.get("created_at") or "")
    visitor_hash = str(row.get("visitor_id_hash") or "")
    path = row.get("path") or row.get("url")
    country = row.get("country") or "unknown"
    source_bucket = row.get("source_bucket") or "unknown"

    cur = storage.get_session(session_id) or {}
    patch: dict[str, Any] = {
        "visitor_id_hash": visitor_hash,
        "last_seen_at": created_at,
        "country": country,
        "source_bucket": source_bucket,
    }

    if not cur:
        patch.update({
            "first_seen_at": created_at,
            "landing_page": path,
            "referrer": row.get("referrer"),
            "utm_source": row.get("utm_source"),
            "utm_medium": row.get("utm_medium"),
            "utm_campaign": row.get("utm_campaign"),
            "device_type": row.get("device_type"),
            "pageviews_count": 0,
            "events_count": 0,
            "products_viewed_count": 0,
            "add_to_cart_count": 0,
            "checkout_started": 0,
            "purchase_completed": 0,
            "revenue": 0.0,
        })

    patch["exit_page"] = path
    patch["events_count"] = int(cur.get("events_count") or 0) + 1

    if event_name == "page_viewed":
        patch["pageviews_count"] = int(cur.get("pageviews_count") or 0) + 1
    if event_name == "product_viewed":
        patch["products_viewed_count"] = int(cur.get("products_viewed_count") or 0) + 1
    if event_name == "product_added_to_cart":
        patch["add_to_cart_count"] = int(cur.get("add_to_cart_count") or 0) + 1
    if event_name == "checkout_started":
        patch["checkout_started"] = 1
    if event_name == "checkout_completed":
        patch["purchase_completed"] = 1
        rev = float(row.get("order_value") or row.get("checkout_value") or 0)
        patch["revenue"] = float(cur.get("revenue") or 0) + rev
        patch["order_id"] = row.get("shopify_order_id")

    if "first_seen_at" not in patch:
        patch["first_seen_at"] = cur.get("first_seen_at") or created_at

    storage.upsert_session(session_id, patch)


def rebuild_sessions(*, since: str | None = None) -> int:
    """Przebudowuje sesje z eventów (chronologicznie). Zwraca liczbę sesji."""
    sql = """
        SELECT * FROM analytics_events
        WHERE bot_suspected = 0
    """
    params: list[Any] = []
    if since:
        sql += " AND created_at >= ?"
        params.append(since)
    sql += " ORDER BY created_at ASC"

    with storage.connect() as conn:
        rows = conn.execute(sql, params).fetchall()
        events = [dict(r) for r in rows]

    by_session: dict[str, list[dict[str, Any]]] = {}
    for ev in events:
        sid = str(ev.get("session_id") or "")
        if sid:
            by_session.setdefault(sid, []).append(ev)

    with storage.connect() as conn:
        if since:
            conn.execute(
                """
                DELETE FROM analytics_sessions
                WHERE session_id IN (
                    SELECT DISTINCT session_id FROM analytics_events
                    WHERE created_at >= ? AND bot_suspected = 0
                )
                """,
                (since,),
            )
        else:
            conn.execute("DELETE FROM analytics_sessions")

    for sess_events in by_session.values():
        for ev in sess_events:
            apply_event_to_session(ev)

    return len(by_session)


def rebuild_sessions_for_new_events(event_rows: list[dict[str, Any]]) -> int:
    """Po imporcie z Workera — aktualizuje sesje dla nowych eventów."""
    count = 0
    for row in event_rows:
        if int(row.get("bot_suspected") or 0):
            continue
        apply_event_to_session(row)
        count += 1
    return count
