"""Pobieranie wielu wynikow wyszukiwania."""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

from .search.download import download_hit
from .search.download.engine import png_option_applies
from .search.download.resolvers import resolve_hit
from .search.download.types import DownloadProgress
from .search.types import ArtworkHit


def run_batch_download(
    root,
    hits: list[ArtworkHit],
    dest_dir: Path,
    *,
    workers: int = 8,
    force_png: bool = False,
    log: Callable[[str], None] | None = None,
    cancel_event: threading.Event | None = None,
    on_done: Callable[[], None] | None = None,
) -> None:
    cancel = cancel_event or threading.Event()
    total = len(hits)

    def work() -> None:
        ok = 0
        fail = 0
        for idx, hit in enumerate(hits, start=1):
            if cancel.is_set():
                if log:
                    log(f"Anulowano po {ok} sukcesach, {fail} bledach.")
                break
            label = f"{hit.artist} — {hit.title}".strip(" —") or hit.title or hit.object_url
            if log:
                log(f"[{idx}/{total}] {label}")

            def _progress(prog: DownloadProgress, *, n=idx) -> None:
                if not log or not prog.message:
                    return
                log(f"[{n}/{total}] {prog.message}")

            spec = resolve_hit(hit)
            use_png = force_png and png_option_applies(spec)
            result = download_hit(
                hit,
                dest_dir,
                workers=workers,
                force_png=use_png,
                on_progress=_progress,
                cancel_check=cancel.is_set,
            )
            if result.ok:
                ok += 1
                if log:
                    log(f"[{idx}/{total}] OK: {result.path}")
            else:
                fail += 1
                if log:
                    log(f"[{idx}/{total}] BLAD: {result.error}")

        summary = f"Zakonczono: {ok} pobrano, {fail} bledow (z {total})."
        if log:
            log(summary)

        def ui() -> None:
            if on_done:
                on_done()

        root.after(0, ui)

    threading.Thread(target=work, daemon=True, name="stronyzobrazami-batch-dl").start()
