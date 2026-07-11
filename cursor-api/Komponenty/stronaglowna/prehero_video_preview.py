"""Podgląd aktywnego filmu Pre-Hero w edytorze GICLÉE HOME FLOW.

Puste pole ``prehero_video`` oznacza działający lokalny asset MP4, a nie brak filmu.
Moduł pokazuje jego klatkę w GUI i pozwala pobierać miniatury filmów Shopify także
w trybie inline, w którym zwykłe zdalne miniatury są celowo ograniczone.
"""

from __future__ import annotations

import io
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Any, Iterable
from urllib.error import URLError
from urllib.request import Request, urlopen

from PIL import Image, ImageTk

from . import home_flow_gui as base_gui
from . import service
from .prehero_integration import PREHERO_VIDEO_ASSET

_VIDEO_SUFFIXES = {".mp4", ".webm", ".mov", ".m4v"}
_FRAME_CACHE: dict[tuple[str, int, int], bytes | None] = {}


def _walk(widget: tk.Misc) -> Iterable[tk.Misc]:
    for child in widget.winfo_children():
        yield child
        yield from _walk(child)


def _widget_text(widget: tk.Misc) -> str:
    try:
        return str(widget.cget("text") or "")
    except (tk.TclError, AttributeError):
        return ""


def _is_video_ref(ref: str) -> bool:
    text = str(ref or "").strip()
    return text.startswith("shopify://files/videos/") or text.startswith(
        "gid://shopify/Video/"
    )


def prehero_fallback_path() -> Path:
    return service.theme_root() / "assets" / PREHERO_VIDEO_ASSET


def _video_frame_bytes(path: Path) -> bytes | None:
    path = Path(path)
    if not path.is_file() or path.suffix.lower() not in _VIDEO_SUFFIXES:
        return None
    try:
        stat = path.stat()
    except OSError:
        return None
    key = (str(path.resolve()), int(stat.st_mtime_ns), int(stat.st_size))
    if key in _FRAME_CACHE:
        return _FRAME_CACHE[key]

    try:
        ffmpeg = service.resolve_ffmpeg_exe()
        proc = subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                "0.35",
                "-i",
                str(path),
                "-frames:v",
                "1",
                "-vf",
                "scale=480:-2",
                "-f",
                "image2pipe",
                "-vcodec",
                "png",
                "pipe:1",
            ],
            capture_output=True,
            timeout=45,
            check=False,
        )
        raw = bytes(proc.stdout or b"") if proc.returncode == 0 else b""
    except (OSError, subprocess.SubprocessError, RuntimeError):
        raw = b""

    result = raw or None
    _FRAME_CACHE[key] = result
    return result


def _download_video_preview(ref: str) -> bytes | None:
    url = service.resolve_shopify_image_url(ref)
    if not url:
        return None
    try:
        request = Request(url, headers={"User-Agent": "GicleeApp/1.50"})
        with urlopen(request, timeout=35) as response:
            return response.read()
    except (URLError, OSError, TimeoutError):
        return None


def install_video_thumbnail_service() -> None:
    current = service.fetch_thumbnail_bytes
    if getattr(current, "_giclee_video_preview", False):
        return

    def fetch_thumbnail_with_video(
        *,
        shopify_ref: str = "",
        local_path: Path | None = None,
    ) -> bytes | None:
        if local_path is not None and Path(local_path).suffix.lower() in _VIDEO_SUFFIXES:
            frame = _video_frame_bytes(Path(local_path))
            if frame is not None:
                return frame

        ref = str(shopify_ref or "").strip()
        if _is_video_ref(ref):
            # Najpierw sprawdzamy plik o tej samej nazwie w lokalnym motywie.
            if ref.startswith("shopify://files/videos/"):
                local = service.theme_root() / "assets" / ref.rsplit("/", 1)[-1]
                frame = _video_frame_bytes(local)
                if frame is not None:
                    return frame
            # Zdalny poster wideo jest pobierany w wątku GUI, więc jest bezpieczny
            # również dla launchera inline.
            remote = _download_video_preview(ref)
            if remote is not None:
                return remote

        return current(shopify_ref=shopify_ref, local_path=local_path)

    setattr(fetch_thumbnail_with_video, "_giclee_video_preview", True)
    setattr(fetch_thumbnail_with_video, "__wrapped__", current)
    service.fetch_thumbnail_bytes = fetch_thumbnail_with_video

    # gui.py importuje funkcję bezpośrednio, więc aktualizujemy również jego alias.
    from . import gui

    gui.fetch_thumbnail_bytes = fetch_thumbnail_with_video


def _find_main_tree(host: tk.Misc) -> ttk.Treeview | None:
    for widget in _walk(host):
        if not isinstance(widget, ttk.Treeview):
            continue
        try:
            if "headings" not in str(widget.cget("show")):
                return widget
        except tk.TclError:
            continue
    return None


def _set_textvariable(widget: ttk.Label, value: str) -> bool:
    try:
        name = str(widget.cget("textvariable") or "")
        if not name:
            return False
        widget.setvar(name, value)
        return True
    except tk.TclError:
        return False


def _patch_local_fallback_preview(host: tk.Misc) -> None:
    tree = _find_main_tree(host)
    selected = str(tree.selection()[0]) if tree is not None and tree.selection() else ""
    if selected != "section:prehero":
        return

    field_label = next(
        (
            widget
            for widget in _walk(host)
            if isinstance(widget, ttk.Label)
            and _widget_text(widget) == "Film do scrollowania:"
        ),
        None,
    )
    if field_label is None:
        return

    row = field_label.master
    thumb = next((widget for widget in _walk(row) if isinstance(widget, tk.Label)), None)
    value_label = next(
        (
            widget
            for widget in _walk(row)
            if isinstance(widget, ttk.Label)
            and str(widget.cget("textvariable") or "")
            and str(widget.getvar(widget.cget("textvariable")) or "") == "(brak)"
        ),
        None,
    )

    # Gdy ustawiono film Shopify, zwykły renderer zajął się już jego posterem.
    if value_label is None or thumb is None:
        return

    path = prehero_fallback_path()
    if not path.is_file():
        _set_textvariable(value_label, f"{PREHERO_VIDEO_ASSET} — brak pliku w assets")
        thumb.configure(image="", text="brak\npliku")
        return

    _set_textvariable(value_label, f"{PREHERO_VIDEO_ASSET}  ·  aktywny asset lokalny")
    thumb.configure(image="", text="ładowanie…")

    token = object()
    thumb._giclee_preview_token = token  # type: ignore[attr-defined]

    def worker() -> None:
        raw = service.fetch_thumbnail_bytes(local_path=path)

        def done() -> None:
            if getattr(thumb, "_giclee_preview_token", None) is not token:
                return
            if raw is None:
                thumb.configure(image="", text="brak\npodglądu")
                return
            try:
                image = Image.open(io.BytesIO(raw))
                image.thumbnail((128, 96), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(image)
            except OSError:
                thumb.configure(image="", text="błąd\npodglądu")
                return
            refs = list(getattr(host, "_giclee_prehero_preview_refs", ()) or ())
            refs.append(photo)
            host._giclee_prehero_preview_refs = refs[-8:]  # type: ignore[attr-defined]
            thumb.configure(image=photo, text="")

        try:
            host.after(0, done)
        except tk.TclError:
            return

    threading.Thread(
        target=worker,
        daemon=True,
        name="giclee-prehero-preview",
    ).start()


def _decorate_preview(host: tk.Misc) -> None:
    tree = _find_main_tree(host)
    if tree is None or getattr(tree, "_giclee_prehero_preview_bound", False):
        return
    tree._giclee_prehero_preview_bound = True  # type: ignore[attr-defined]

    def schedule(_event=None) -> None:
        host.after(180, lambda: _patch_local_fallback_preview(host))

    tree.bind("<<TreeviewSelect>>", schedule, add="+")
    schedule()


def install_prehero_video_preview() -> None:
    install_video_thumbnail_service()

    current = base_gui._decorate_home_editor
    if getattr(current, "_giclee_prehero_preview", False):
        return

    def decorate_with_preview(host: tk.Misc) -> None:
        current(host)
        host.after_idle(lambda: _decorate_preview(host))

    setattr(decorate_with_preview, "_giclee_prehero_preview", True)
    setattr(decorate_with_preview, "__wrapped__", current)
    base_gui._decorate_home_editor = decorate_with_preview
