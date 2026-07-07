"""Analyze studio_perf.log for PERF-A report."""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

LOG = Path(__file__).resolve().parents[1] / "giclee_app" / "logs" / "studio_perf.log"

SECRET_PATTERNS = [
    re.compile(p, re.I)
    for p in [
        r"api[_-]?key",
        r"secret",
        r"password",
        r"token",
        r"shpat_",
        r"Bearer\s+",
        r"private_key",
        r"access_token",
    ]
]

KEY_EVENTS = [
    "studio.component_index.build",
    "studio.state.load",
    "studio.state.prune",
    "studio.show_view.deferred_factory",
    "studio.gicleeframe.factory",
    "studio.gicleeframe.init",
    "studio.gicleeframe.build_shell",
    "studio.gicleeframe.init_refresh.light",
    "studio.gicleeframe.visual.perceived_ready",
    "studio.gicleeframe.visual.visible_ready",
    "studio.katalog.refresh_pipeline.start",
    "studio.katalog.refresh.inventory",
    "studio.katalog.refresh.data_map",
    "studio.katalog.refresh.inventory_rows.batch",
    "studio.katalog.refresh.inventory_rows.done",
    "studio.katalog.refresh.data_map_rows.batch",
    "studio.katalog.refresh.data_map_rows.done",
    "studio.katalog.refresh.finalize",
    "studio.katalog.refresh_pipeline.done",
    "studio.hub.visual.first_cards_ready",
    "studio.hub.visual.full_ready",
]

SELECTION_EVENTS = [
    "studio.gicleeframe.selection.click",
    "studio.gicleeframe.select_element.immediate_ready",
    "studio.gicleeframe.selection.immediate_highlight_done",
    "studio.gicleeframe.populate_editor.deferred",
    "studio.gicleeframe.page_context.stable",
]


def load_rows() -> list[dict]:
    rows = []
    for line in LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def main() -> None:
    if not LOG.exists():
        print(f"Missing log: {LOG}", file=sys.stderr)
        sys.exit(1)

    rows = load_rows()
    print(f"Total events: {len(rows)}")

    # Secrets scan
    raw = LOG.read_text(encoding="utf-8")
    hits = []
    for pat in SECRET_PATTERNS:
        if pat.search(raw):
            hits.append(pat.pattern)
    print(f"Secret pattern hits: {hits or 'none'}")

    # Top 20 by elapsed_ms
    with_ms = [r for r in rows if "elapsed_ms" in r]
    top = sorted(with_ms, key=lambda r: r["elapsed_ms"], reverse=True)[:20]
    print("\n=== TOP 20 elapsed_ms ===")
    for r in top:
        extra = {k: v for k, v in r.items() if k not in {"event", "elapsed_ms", "ts"}}
        print(
            f"{r['elapsed_ms']:>10.2f}  {r['event']}"
            + (f"  {extra}" if extra else "")
        )

    # Key events summary (all occurrences, cold vs cache)
    print("\n=== KEY EVENTS ===")
    for ev in KEY_EVENTS + SELECTION_EVENTS:
        matches = [r for r in rows if r.get("event") == ev]
        if not matches:
            continue
        cold = [r for r in matches if r.get("cache_hit") is False]
        cache = [r for r in matches if r.get("cache_hit") is True]
        neutral = [r for r in matches if "cache_hit" not in r]
        def stats(group):
            if not group:
                return "—"
            ms = [r["elapsed_ms"] for r in group if "elapsed_ms" in r]
            if not ms:
                return f"n={len(group)} (no elapsed_ms)"
            return f"n={len(group)} min={min(ms):.2f} avg={sum(ms)/len(ms):.2f} max={max(ms):.2f}"
        print(f"{ev}:")
        print(f"  all: {stats(matches)}")
        if cold:
            print(f"  cold: {stats(cold)}")
        if cache:
            print(f"  cache: {stats(cache)}")
        if neutral and not cold and not cache:
            pass

    # deferred_factory for gicleeframe
    gf_def = [
        r
        for r in rows
        if r.get("event") == "studio.show_view.deferred_factory" and r.get("key") == "gicleeframe"
    ]
    if gf_def:
        print("\n=== studio.show_view.deferred_factory (gicleeframe) ===")
        for r in gf_def:
            print(r)

    # katalog paths
    print("\n=== KATALOG ===")
    for ev in [
        "studio.katalog.open",
        "studio.katalog.refresh_pipeline.start",
        "studio.katalog.refresh.inventory_rows.batch",
        "studio.katalog.refresh.inventory_rows.done",
        "studio.katalog.refresh.data_map_rows.batch",
        "studio.katalog.refresh.data_map_rows.done",
        "studio.katalog.refresh_pipeline.done",
        "studio.katalog.refresh.skipped_cache_fresh",
        "studio.katalog.visual.ready",
        "studio.katalog.build_shell",
    ]:
        for r in rows:
            if r.get("event") == ev:
                print(r)

    # Hub
    print("\n=== HUB theme ===")
    hub_events = [r for r in rows if "hub" in r.get("event", "")]
    for r in hub_events:
        if r.get("category") in (None, "theme") or "hub:" in str(r.get("key", "")):
            if r.get("event", "").startswith("studio.hub") or r.get("key") == "hub:theme":
                print(r)

    # GF perceived/visible timeline
    print("\n=== GF visual timeline ===")
    for r in rows:
        ev = r.get("event", "")
        if ev.startswith("studio.gicleeframe.") and (
            "visual" in ev or ev.endswith(".init") or ev.endswith("build_shell")
            or "factory" in ev or "open" in ev
        ):
            if "elapsed_ms" in r or "cache_hit" in r or "perceived" in ev or "visible_ready" in ev:
                print(r)

    # after() / update_idletasks signals
    print("\n=== update_idletasks ===")
    skipped = sum(1 for r in rows if r.get("event") == "studio.show_view.update_idletasks.skipped")
    ran = sum(1 for r in rows if r.get("event") == "studio.show_view.update_idletasks.ran")
    print(f"skipped={skipped} ran={ran}")

    # Selection clicks
    print("\n=== SELECTION CLICKS ===")
    for r in rows:
        if r.get("event") in SELECTION_EVENTS or "selection" in r.get("event", ""):
            if "click" in r.get("event", "") or "immediate_ready" in r.get("event", ""):
                print(r)


if __name__ == "__main__":
    main()
