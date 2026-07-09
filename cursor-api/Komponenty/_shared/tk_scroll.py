"""Wspólne przewijanie kółkiem myszy dla Canvas + dzieci (Windows / touchpad)."""

from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk


_WHEEL_BIND_ATTR = "_giclee_canvas_wheel_bound"


def _widget_in_tree(widget: tk.Misc | None, *roots: tk.Misc) -> bool:
    if widget is None or not roots:
        return False
    targets = set(roots)
    w: tk.Misc | None = widget
    while w is not None:
        if w in targets:
            return True
        try:
            w = w.master
        except tk.TclError:
            break
    return False


def bind_mousewheel_to_canvas(
    canvas: tk.Canvas,
    root: tk.Misc,
    *,
    include_text: bool = False,
) -> None:
    """Kółko nad canvasem i zawartością przewija canvas (bind_all + hit-test, bez unbind_all)."""
    if getattr(canvas, _WHEEL_BIND_ATTR, False):
        return

    toplevel = canvas.winfo_toplevel()
    hover_roots: list[tk.Misc] = [canvas, root]
    try:
        host = canvas.master
        if host is not None:
            hover_roots.append(host)
    except tk.TclError:
        pass

    acc: list[int] = [0]
    job: list[str | None] = [None]

    def _flush() -> None:
        job[0] = None
        d = acc[0]
        acc[0] = 0
        if not d:
            return
        step = -d / 120.0
        if -1 < step < 1 and step != 0:
            step = math.copysign(1.0, float(-d))
        canvas.yview_scroll(int(step), "units")

    def _queue_wheel(delta: int) -> None:
        acc[0] += delta
        jid = job[0]
        if jid is not None:
            try:
                canvas.after_cancel(jid)
            except (tk.TclError, ValueError):
                pass
        job[0] = canvas.after_idle(_flush)

    def _excluded_target(widget: tk.Misc | None) -> bool:
        if widget is None:
            return False
        if isinstance(widget, tk.Text) and not include_text:
            return True
        if isinstance(widget, tk.Listbox):
            return True
        return isinstance(widget, ttk.Treeview)

    def _over_canvas_viewport(evt: tk.Event) -> bool:
        try:
            x = canvas.winfo_rootx()
            y = canvas.winfo_rooty()
            w = max(canvas.winfo_width(), 1)
            h = max(canvas.winfo_height(), 1)
            return x <= evt.x_root < x + w and y <= evt.y_root < y + h
        except tk.TclError:
            return False

    def _over_host_viewport(evt: tk.Event) -> bool:
        host = hover_roots[-1] if len(hover_roots) > 2 else None
        if host is None or host is canvas:
            return False
        try:
            x = host.winfo_rootx()
            y = host.winfo_rooty()
            w = max(host.winfo_width(), 1)
            h = max(host.winfo_height(), 1)
            return x <= evt.x_root < x + w and y <= evt.y_root < y + h
        except tk.TclError:
            return False

    def _should_scroll(evt: tk.Event) -> bool:
        try:
            if canvas.winfo_toplevel() is not toplevel:
                return False
        except tk.TclError:
            return False

        pointer: tk.Misc | None
        try:
            pointer = canvas.winfo_containing(evt.x_root, evt.y_root)
        except tk.TclError:
            pointer = evt.widget

        if _excluded_target(pointer):
            return False

        if _over_canvas_viewport(evt):
            return True

        if _over_host_viewport(evt) and _widget_in_tree(pointer, *hover_roots):
            return True

        return _widget_in_tree(pointer, *hover_roots) or _widget_in_tree(evt.widget, *hover_roots)

    def _wheel(evt: tk.Event) -> str | None:
        if not _should_scroll(evt):
            return None
        if evt.delta:
            _queue_wheel(int(evt.delta))
            return "break"
        if evt.num == 4:
            canvas.yview_scroll(-1, "units")
            return "break"
        if evt.num == 5:
            canvas.yview_scroll(1, "units")
            return "break"
        return None

    toplevel.bind_all("<MouseWheel>", _wheel, add="+")
    toplevel.bind_all("<Button-4>", _wheel, add="+")
    toplevel.bind_all("<Button-5>", _wheel, add="+")
    setattr(canvas, _WHEEL_BIND_ATTR, True)
