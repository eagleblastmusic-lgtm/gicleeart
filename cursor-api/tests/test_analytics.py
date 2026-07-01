"""Testy modułu Analiza ruchu."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from Komponenty.analytics import aggregations, collect, storage
from Komponenty.analytics.bots import is_bot_user_agent
from Komponenty.analytics.models import CollectPayload
from Komponenty.analytics.privacy import hash_identifier, sanitize_metadata
from Komponenty.analytics.sources import classify_source, parse_utm_from_url


@pytest.fixture()
def analytics_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db = tmp_path / "test_analytics.db"
    monkeypatch.setattr("Komponenty.analytics.env_config.db_path", lambda: db)
    monkeypatch.setenv("ANALYTICS_COLLECT_SECRET", "test-secret-123")
    monkeypatch.setenv("ANALYTICS_ALLOWED_SHOP_DOMAIN", "gicleeart.eu")
    storage.init_db()
    return db


def test_hash_identifier_stable(analytics_db: Path) -> None:
    a = hash_identifier("visitor-abc")
    b = hash_identifier("visitor-abc")
    assert a == b
    assert a.startswith("v_")


def test_classify_source_organic() -> None:
    assert classify_source(referrer="https://www.google.com/search?q=giclee") == "organic_search"
    assert classify_source(utm_medium="cpc", utm_source="google") == "paid"
    assert classify_source() == "direct"


def test_parse_utm() -> None:
    u = parse_utm_from_url("https://gicleeart.eu/pl-pl?utm_source=instagram&utm_campaign=spring")
    assert u["utm_source"] == "instagram"
    assert u["utm_campaign"] == "spring"


def test_bot_user_agent() -> None:
    assert is_bot_user_agent("Mozilla/5.0 Googlebot/2.1")
    assert not is_bot_user_agent("Mozilla/5.0 Chrome/120.0.0.0 Safari/537.36")


def test_collect_dedup(analytics_db: Path) -> None:
    payload = collect.make_test_event()
    payload["secret"] = "test-secret-123"
    r1 = collect.ingest_event(payload)
    r2 = collect.ingest_event(payload)
    assert r1.get("event_id")
    assert r2.get("duplicate") is True


def test_collect_invalid_secret(analytics_db: Path) -> None:
    payload = collect.make_test_event()
    payload["secret"] = "wrong"
    with pytest.raises(collect.CollectError) as exc:
        collect.ingest_event(payload)
    assert exc.value.status == 401


def test_sanitize_metadata_strips_pii() -> None:
    raw = sanitize_metadata({"email": "a@b.c", "frame": "oak"})
    assert "email" not in raw
    assert "frame" in raw


def test_conversion_rate(analytics_db: Path) -> None:
    base = collect.make_test_event()
    base["secret"] = "test-secret-123"
    for i in range(3):
        ev = dict(base)
        ev["event_id"] = f"pv_{i}"
        ev["event_name"] = "page_viewed"
        ev["session_id"] = f"s{i}"
        ev["visitor_id"] = f"v{i}"
        collect.ingest_event(ev)
    purch = dict(base)
    purch["event_id"] = "purchase_1"
    purch["event_name"] = "checkout_completed"
    purch["order_value"] = 100.0
    purch["session_id"] = "s0"
    purch["visitor_id"] = "v0"
    collect.ingest_event(purch)

    df = "1970-01-01T00:00:00Z"
    dt = "9999-12-31T23:59:59Z"
    overview = aggregations.compute_overview(df, dt)
    assert overview["purchases"] >= 1
    assert overview["conversion_rate"] > 0


def test_funnel_stages(analytics_db: Path) -> None:
    funnel = aggregations.compute_funnel("1970-01-01T00:00:00Z", "9999-12-31T23:59:59Z")
    assert len(funnel["stages"]) == 5


def test_country_aggregation(analytics_db: Path) -> None:
    ev = collect.make_test_event()
    ev["secret"] = "test-secret-123"
    ev["country"] = "PL"
    collect.ingest_event(ev)
    data = aggregations.compute_countries("1970-01-01T00:00:00Z", "9999-12-31T23:59:59Z")
    countries = {r["country"] for r in data["countries"]}
    assert "PL" in countries


def test_collect_payload_from_dict() -> None:
    p = CollectPayload.from_dict({"event_name": "page_viewed", "event_id": "x", "timestamp": "2026-01-01T00:00:00Z"})
    assert p.event_name == "page_viewed"


def test_product_unique_viewers(analytics_db: Path) -> None:
    base = collect.make_test_event()
    base["secret"] = "test-secret-123"
    base["event_name"] = "product_viewed"
    base["shopify_product_id"] = "111"
    base["product_title"] = "Obraz A"
    for i in range(5):
        ev = dict(base)
        ev["event_id"] = f"pv_a_{i}"
        ev["visitor_id"] = "same_visitor"
        ev["session_id"] = f"s{i}"
        collect.ingest_event(ev)
    ev_b = dict(base)
    ev_b["event_id"] = "pv_b_1"
    ev_b["shopify_product_id"] = "222"
    ev_b["product_title"] = "Obraz B"
    ev_b["visitor_id"] = "visitor_b"
    collect.ingest_event(ev_b)

    data = aggregations.compute_products("1970-01-01T00:00:00Z", "9999-12-31T23:59:59Z")
    by_title = {p["product_title"]: p for p in data["products"]}
    assert by_title["Obraz A"]["views"] == 5
    assert by_title["Obraz A"]["unique_viewers"] == 1
    assert by_title["Obraz B"]["unique_viewers"] == 1
    assert data["products"][0]["product_title"] == "Obraz A"
    assert data["products"][0]["unique_viewers"] == 1


def test_session_rebuild_from_events(analytics_db: Path) -> None:
    from Komponenty.analytics import sessions as sess_mod

    base = collect.make_test_event()
    base["secret"] = "test-secret-123"
    base["session_id"] = "rebuild_sess_1"
    for i, ename in enumerate(["page_viewed", "product_viewed", "product_added_to_cart"]):
        ev = dict(base)
        ev["event_id"] = f"rebuild_{i}"
        ev["event_name"] = ename
        ev["shopify_product_id"] = "999"
        collect.ingest_event(ev)

    with storage.connect() as conn:
        conn.execute("DELETE FROM analytics_sessions WHERE session_id = ?", ("rebuild_sess_1",))

    count = sess_mod.rebuild_sessions(since="1970-01-01T00:00:00Z")
    assert count >= 1
    sess = storage.get_session("rebuild_sess_1")
    assert sess is not None
    assert int(sess.get("pageviews_count") or 0) >= 1
    assert int(sess.get("add_to_cart_count") or 0) >= 1


def test_schema_migration_adds_ip_hash(analytics_db: Path) -> None:
    """Stara baza bez kolumny ip_hash — init_db musi ją dodać (bez błędu CREATE INDEX)."""
    with storage.connect() as conn:
        conn.execute("DROP INDEX IF EXISTS idx_events_ip_hash")
        conn.execute("ALTER TABLE analytics_events DROP COLUMN ip_hash")

    storage.init_db()

    with storage.connect() as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(analytics_events)")}
    assert "ip_hash" in cols


def test_exclusion_settings(analytics_db: Path) -> None:
    from Komponenty.analytics import settings as sett

    sett.add_exclusion(visitor_id="my_test_visitor")
    vis, _ = sett.get_exclusions()
    assert len(vis) == 1

    base = collect.make_test_event()
    base["secret"] = "test-secret-123"
    base["visitor_id"] = "my_test_visitor"
    base["event_id"] = "excluded_event_1"
    result = collect.ingest_event(base)
    assert result.get("skipped") is True


def test_ip_exclusion_hash_matches_worker(analytics_db: Path) -> None:
    from Komponenty.analytics import settings as sett
    from Komponenty.analytics.privacy import hash_identifier

    sett.add_exclusion(ip="203.0.113.50")
    _, ips = sett.get_exclusions()
    assert ips == [hash_identifier("203.0.113.50", prefix="ip")]


def test_exclusions_toggle_and_remove(analytics_db: Path) -> None:
    from Komponenty.analytics import settings as sett

    sett.add_exclusion(ip="1.2.3.4")
    settings = sett.get_settings()
    assert settings["exclude_labels"]

    sett.save_settings({"exclusions_enabled": False})
    vis, ips = sett.get_exclusions()
    assert vis == [] and ips == []

    sett.save_settings({"exclusions_enabled": True})
    _, ips = sett.get_exclusions()
    assert len(ips) == 1

    sett.remove_exclusion(kind="ip", hash_value=ips[0])
    _, ips = sett.get_exclusions()
    assert ips == []


def test_toggle_my_ip(analytics_db: Path) -> None:
    from Komponenty.analytics import settings as sett

    sett.add_exclusion(ip="46.205.210.77")
    saved = sett.get_settings()
    assert saved["exclude_my_ip"] is True

    saved = sett.toggle_my_ip(enabled=False)
    assert saved["exclude_my_ip"] is False
    _, ips = sett.get_exclusions()
    assert ips == []

    saved = sett.toggle_my_ip(ip="46.205.210.77", enabled=True)
    assert saved["exclude_my_ip"] is True
    _, ips = sett.get_exclusions()
    assert len(ips) == 1
    vis, _ = sett.get_exclusions()
    assert len(vis) >= 0


def test_auto_exclude_recent_visitors(analytics_db: Path) -> None:
    from Komponenty.analytics import settings as sett, collect

    for i in range(3):
        ev = collect.make_test_event()
        ev["secret"] = "test-secret-123"
        ev["visitor_id"] = f"heavy_visitor_{i}"
        ev["event_id"] = f"auto_ex_{i}"
        collect.ingest_event(ev)

    cur = sett._load_raw()
    added = sett._auto_exclude_recent_test_visitors(cur, min_events=2, limit=5)
    assert added == 0

    ev = collect.make_test_event()
    ev["secret"] = "test-secret-123"
    ev["visitor_id"] = "heavy_visitor_x"
    ev["event_id"] = "auto_ex_x1"
    collect.ingest_event(ev)
    ev["event_id"] = "auto_ex_x2"
    collect.ingest_event(ev)

    cur = sett._load_raw()
    added = sett._auto_exclude_recent_test_visitors(cur, min_events=2, limit=5)
    assert added >= 1


def test_exclusion_impact_by_visitor_hash(analytics_db: Path) -> None:
    from Komponenty.analytics import settings as sett

    base = collect.make_test_event()
    base["secret"] = "test-secret-123"
    base["visitor_id"] = "impact_visitor"
    base["event_id"] = "impact_ev_1"
    collect.ingest_event(base)

    sett.add_exclusion(visitor_hash="v_nonexistent")
    impact = storage.count_exclusion_impact()
    assert impact["events"] == 0

    vh = storage.suggest_recent_visitors(limit=1)[0]["visitor_id_hash"]
    sett.add_exclusion(visitor_hash=vh)
    impact = storage.count_exclusion_impact()
    assert impact["events"] >= 1


def test_timeline_unique_visitors(analytics_db: Path) -> None:
    base = collect.make_test_event()
    base["secret"] = "test-secret-123"
    for i in range(2):
        ev = dict(base)
        ev["event_id"] = f"tl_{i}"
        ev["visitor_id"] = f"v{i}"
        collect.ingest_event(ev)
    tl = aggregations.compute_timeline("1970-01-01T00:00:00Z", "9999-12-31T23:59:59Z")
    assert tl
    assert tl[0].get("unique_visitors", 0) >= 2
