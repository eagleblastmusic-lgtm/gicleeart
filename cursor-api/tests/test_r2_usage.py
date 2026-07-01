"""Testy formatowania zużycia R2."""

from __future__ import annotations

from Komponenty.dodajobraz.r2_usage import (
    R2UsageSnapshot,
    estimate_zooms_remaining,
    format_bytes,
    format_usage_line,
    usage_percent,
    usage_status,
)


def test_format_bytes_gb_pl() -> None:
    assert "GB" in format_bytes(2 * 1024**3)
    assert "," in format_bytes(int(1.25 * 1024**3))


def test_format_usage_line_storage() -> None:
    snap = R2UsageSnapshot(
        bucket="giclee-zoom",
        storage_bytes=3 * 1024**3,
        object_count=120,
        zoom_bytes=2 * 1024**3,
        zoom_object_count=80,
        storage_quota_bytes=10 * 1024**3,
        class_a_used=None,
        class_a_quota=1_000_000,
        class_b_used=None,
        class_b_quota=10_000_000,
        source="bucket",
        note="",
    )
    line = format_usage_line(snap)
    assert "giclee-zoom" in line
    assert "wolne" in line
    assert "egress" in line
    assert "zoom" in line


def test_estimate_zooms_from_local_history() -> None:
    free = 5 * 1024**3
    local = [400 * 1024**2, 500 * 1024**2, 450 * 1024**2]
    count, avg, n, src = estimate_zooms_remaining(
        free,
        bucket_work_sizes=[],
        local_recent_sizes=local,
    )
    assert n == 3
    assert "aplikacji" in src
    assert avg and avg > 0
    assert count is not None and count >= 10


def test_format_usage_includes_zoom_estimate() -> None:
    snap = R2UsageSnapshot(
        bucket="giclee-zoom",
        storage_bytes=2 * 1024**3,
        object_count=50,
        zoom_bytes=1024**3,
        zoom_object_count=30,
        storage_quota_bytes=10 * 1024**3,
        class_a_used=None,
        class_a_quota=1_000_000,
        class_b_used=None,
        class_b_quota=10_000_000,
        source="bucket",
        note="",
        zoom_estimate_count=15,
        zoom_estimate_avg_bytes=500 * 1024**2,
        zoom_estimate_sample_n=5,
        zoom_estimate_source="5 dziel w R2",
    )
    line = format_usage_line(snap)
    assert "kolejnych zoomow" in line


def test_usage_percent_and_status() -> None:
    assert usage_percent(5, 10) == 50.0
    assert usage_percent(15, 10) == 100.0
    assert usage_status(50.0)[0] == "OK"
    assert usage_status(80.0)[0] == "Uwaga"
    assert usage_status(95.0)[0] == "Krytycznie"
