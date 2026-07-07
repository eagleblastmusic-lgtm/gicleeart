"""One-off PERF-A scenario driver — not part of production app."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["GICLEE_STUDIO_PERF"] = "1"
# Disable idle prewarm noise during scripted run
os.environ.setdefault("GICLEE_STUDIO_IDLE_PREWARM", "0")

LOG_PATH = ROOT / "giclee_app" / "logs" / "studio_perf.log"

if LOG_PATH.exists():
    archive = LOG_PATH.with_suffix(f".arch-{int(time.time())}.log")
    LOG_PATH.rename(archive)
    print(f"Archived old log -> {archive.name}")

import customtkinter as ctk  # noqa: E402

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

from giclee_app.launcher_studio import GicleeAppStudio  # noqa: E402


def _find_gf_elements(view) -> dict[str, str | None]:
    """Return element_ids for separator, media_section, media_child."""
    out: dict[str, str | None] = {
        "separator": None,
        "media_section": None,
        "media_child": None,
    }
    merged = getattr(view, "_merged", []) or []
    by_id = getattr(view, "_merged_by_id", {}) or {}

    for m in merged:
        et = getattr(m, "element_type", "")
        eid = getattr(m, "element_id", "")
        if et == "divider" and out["separator"] is None:
            out["separator"] = eid
        elif et == "media_section" and out["media_section"] is None:
            out["media_section"] = eid

    if out["media_section"]:
        parent = by_id.get(out["media_section"])
        sk = getattr(parent, "section_key", None) if parent else None
        if sk:
            for m in merged:
                if (
                    getattr(m, "section_key", None) == sk
                    and getattr(m, "element_id", "") != out["media_section"]
                    and getattr(m, "element_type", "") in ("jumbo", "body", "image")
                ):
                    out["media_child"] = m.element_id
                    break
    return out


def _wait_and(app: GicleeAppStudio, step_fn, delay_ms: int = 800) -> None:
    app.after(delay_ms, step_fn)


def main() -> None:
    app = GicleeAppStudio()
    state = {"step": 0}

    def finish() -> None:
        print("PERF-A scenarios complete.")
        app.after(300, app.destroy)

    def step_gf_selections() -> None:
        view = app._view_cache.get("gicleeframe")
        if view is None:
            print("WARN: gicleeframe not in cache")
            _wait_and(app, step_return_hub_from_gf, 500)
            return
        ids = _find_gf_elements(view)
        print("GF elements:", ids)

        def click_seq(idx: int = 0, targets: list[tuple[str, str | None]] | None = None) -> None:
            if targets is None:
                targets = [
                    ("separator", ids["separator"]),
                    ("media_section", ids["media_section"]),
                    ("media_child", ids["media_child"]),
                ]
                targets = [(k, v) for k, v in targets if v]

            if idx >= len(targets):
                _wait_and(app, step_return_hub_from_gf, 1200)
                return
            label, eid = targets[idx]
            print(f"  click {label}: {eid}")
            view._on_section_row_click(eid)
            app.update_idletasks()
            app.after(600, lambda: click_seq(idx + 1, targets))

        click_seq()

    def step_return_hub_from_gf() -> None:
        print("E: return from GF to hub")
        app._return_from_gicleeframe()
        app.update_idletasks()
        _wait_and(app, step_gf_cache_reentry, 1000)

    def step_gf_cache_reentry() -> None:
        print("F: re-enter GF (cache)")
        app._show_gicleeframe_shell("theme")
        app.update_idletasks()
        _wait_and(app, step_katalog_cold, 1500)

    def step_katalog_cold() -> None:
        print("G: katalog cold")
        app._show_katalog()
        app.update_idletasks()
        _wait_and(app, step_katalog_return, 2000)

    def step_katalog_return() -> None:
        print("return from katalog")
        app._show_hub("theme")
        app.update_idletasks()
        _wait_and(app, step_katalog_cache, 800)

    def step_katalog_cache() -> None:
        print("H: katalog cache")
        app._show_katalog()
        app.update_idletasks()
        _wait_and(app, finish, 2000)

    def step_open_gf() -> None:
        print("D: open GICLEE FRAME")
        app._show_gicleeframe_shell("theme")
        app.update_idletasks()
        _wait_and(app, step_gf_selections, 2500)

    def step_open_hub() -> None:
        print("B: hub Strona / Motyw")
        app._show_hub("theme")
        app.update_idletasks()
        _wait_and(app, step_open_gf, 2000)

    def step_start() -> None:
        print("A: cold start done (dashboard shown)")
        _wait_and(app, step_open_hub, 1200)

    app.after(500, step_start)
    app.mainloop()

    if LOG_PATH.exists():
        lines = LOG_PATH.read_text(encoding="utf-8").splitlines()
        print(f"Log written: {LOG_PATH} ({len(lines)} events)")
    else:
        print("ERROR: no perf log produced")


if __name__ == "__main__":
    main()
