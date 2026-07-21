"""Atomic homepage writes and a Theme Dev revision barrier.

The legacy editors write several theme files during one user action. This module keeps
those individual replacements atomic, validates JSON readback, stamps the final generated
asset with a revision, and opens Theme Dev only after that revision is observable.
"""

from __future__ import annotations

import json
import re
import threading
import time
import webbrowser
from pathlib import Path
from tkinter import messagebox
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from giclee_app.app_paths import atomic_write_text
from Komponenty._shared.toast import show_toast

_BUILD_MARKER_RE = re.compile(
    r"^\s*window\.GICLEE_HOME_BUILD_REVISION\s*=\s*[^;]+;\s*$",
    flags=re.MULTILINE,
)
_LAST_BUILD_REVISION = ""
_WRITES_INSTALLED = False
_GUI_GUARD_INSTALLED = False


def _validate_json_file(path: Path, *, strip_header) -> dict[str, Any]:
    parsed = json.loads(strip_header(path.read_text(encoding="utf-8")))
    if not isinstance(parsed, dict):
        raise ValueError(f"Readback zapisu nie zwrócił obiektu JSON: {path}")
    return parsed


def _stamp_build_revision(path: Path, revision: str | None = None) -> str:
    global _LAST_BUILD_REVISION

    if not path.is_file():
        raise FileNotFoundError(f"Brak wygenerowanego assetu rewizji: {path}")

    token = revision or f"{time.time_ns():x}"
    current = path.read_text(encoding="utf-8")
    clean = _BUILD_MARKER_RE.sub("", current).rstrip()
    updated = (
        clean
        + "\nwindow.GICLEE_HOME_BUILD_REVISION = "
        + json.dumps(token)
        + ";\n"
    )
    atomic_write_text(path, updated)
    if token not in path.read_text(encoding="utf-8"):
        raise OSError(f"Readback assetu nie zawiera rewizji {token}: {path}")
    _LAST_BUILD_REVISION = token
    return token


def last_build_revision() -> str:
    return _LAST_BUILD_REVISION


def wait_for_theme_dev_revision(
    revision: str,
    *,
    timeout_sec: float = 12.0,
    poll_sec: float = 0.35,
) -> bool | None:
    """Return True when Theme Dev serves revision, False on timeout, None if not running."""

    from . import service

    if not revision or not service.theme_dev_port_open():
        return None

    deadline = time.monotonic() + max(0.5, timeout_sec)
    url = (
        "http://127.0.0.1:9292/assets/giclee-home-sections.js"
        f"?giclee_revision={revision}"
    )
    while time.monotonic() < deadline:
        try:
            request = Request(
                url,
                headers={
                    "Cache-Control": "no-cache, no-store, max-age=0",
                    "Pragma": "no-cache",
                },
            )
            with urlopen(request, timeout=2.0) as response:
                body = response.read(512_000).decode("utf-8", errors="replace")
            if revision in body:
                return True
        except (URLError, OSError, TimeoutError, ValueError):
            pass
        time.sleep(max(0.05, poll_sec))
    return False


def install_safe_theme_writes() -> None:
    """Patch legacy homepage writers before the GUI binds their functions."""

    global _WRITES_INSTALLED
    if _WRITES_INSTALLED:
        return

    from . import home_features, homepage_variants, prehero_integration, service

    def save_index_template(template: dict[str, Any], *, logger=None) -> None:
        service.repair_color_correction_cta_blocks(template)
        path = service.index_template_path()
        body = json.dumps(template, ensure_ascii=False, indent=2) + "\n"
        atomic_write_text(path, service.INDEX_HEADER + body)
        _validate_json_file(path, strip_header=service._strip_json_header)
        service._log(logger, f"[strona główna] Zapisano {path.name}.")

    def save_theme_settings(data: dict[str, Any], *, logger=None) -> None:
        path = service.settings_data_path()
        body = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        atomic_write_text(path, service.SETTINGS_HEADER + body)
        _validate_json_file(path, strip_header=service._strip_json_header)
        service._log(logger, f"[strona główna] Zapisano {path.name}.")

    def write_text_if_changed(path: Path, content: str) -> None:
        if path.is_file():
            try:
                if path.read_text(encoding="utf-8") == content:
                    return
            except OSError:
                pass
        atomic_write_text(path, content)
        if path.read_text(encoding="utf-8") != content:
            raise OSError(f"Readback nie zgadza się z zapisem: {path}")

    def patch_generated_prehero_snippet(config: dict[str, Any] | None = None) -> bool:
        cfg = config or prehero_integration.export_prehero_config(None)
        path = service.theme_root() / "snippets" / "giclee-home-stack-critical.liquid"
        if not path.is_file():
            return False
        original = path.read_text(encoding="utf-8")
        if cfg.get("enabled", True) and not prehero_integration.prehero_assets_ready(cfg):
            return False
        updated = prehero_integration.inject_prehero_into_snippet(original, cfg)
        if updated == original:
            return False
        atomic_write_text(path, updated)
        if path.read_text(encoding="utf-8") != updated:
            raise OSError(f"Readback snippetu nie zgadza się z zapisem: {path}")
        return True

    current_writer = home_features.write_home_assets

    def write_home_assets_safely(*args: Any, **kwargs: Any) -> Any:
        result = current_writer(*args, **kwargs)

        # The older pre-Hero wrapper intentionally swallowed write errors. Repeat the
        # final patch with the strict atomic writer so the Save action can report failure.
        cfg = prehero_integration.export_prehero_config(service.load_theme_settings())
        patch_generated_prehero_snippet(cfg)

        revision_path = service.theme_root() / "assets" / "giclee-home-sections.js"
        _stamp_build_revision(revision_path)
        return result

    service.save_index_template = save_index_template
    service.save_theme_settings = save_theme_settings
    homepage_variants.save_index_template = save_index_template
    homepage_variants.save_theme_settings = save_theme_settings
    home_features._write_text_if_changed = write_text_if_changed
    prehero_integration.patch_generated_prehero_snippet = patch_generated_prehero_snippet
    home_features.write_home_assets = write_home_assets_safely
    _WRITES_INSTALLED = True


def install_theme_dev_revision_guard() -> None:
    """Replace the scroll selector callback with a synchronized, non-stale preview flow."""

    global _GUI_GUARD_INSTALLED
    if _GUI_GUARD_INSTALLED:
        return

    from . import home_features, home_flow_gui, home_scroll_mode, homepage_variants

    current_decorator = home_flow_gui._decorate_home_editor
    if getattr(current_decorator, "_giclee_theme_dev_revision_guard", False):
        _GUI_GUARD_INSTALLED = True
        return

    def decorate_with_revision_guard(host) -> None:
        current_decorator(host)
        if getattr(host, "_giclee_theme_dev_revision_guarded", False):
            return

        combo = getattr(host, "_giclee_scroll_mode_combo", None)
        mode_var = getattr(host, "_giclee_scroll_mode_var", None)
        if combo is None or mode_var is None:
            return

        host._giclee_theme_dev_revision_guarded = True  # type: ignore[attr-defined]
        try:
            combo.unbind("<<ComboboxSelected>>")
        except Exception:
            pass

        def refresh_mode() -> None:
            mode = home_scroll_mode.load_scroll_mode(homepage_variants.active_variant_id())
            mode_var.set(home_scroll_mode.SCROLL_MODE_LABELS[mode])

        def selected_mode(_event=None) -> None:
            selected = home_scroll_mode._LABEL_TO_MODE.get(
                mode_var.get(),
                home_scroll_mode.SCROLL_MODE_NATIVE,
            )
            variant_id = homepage_variants.active_variant_id()
            try:
                combo.configure(state="disabled")
            except Exception:
                pass

            def worker() -> None:
                try:
                    applied = home_scroll_mode.apply_scroll_mode_to_live_theme(
                        variant_id,
                        selected,
                    )
                    revision = last_build_revision()
                    synchronized = wait_for_theme_dev_revision(revision)
                except Exception as exc:
                    error = str(exc)

                    def fail() -> None:
                        try:
                            combo.configure(state="readonly")
                        except Exception:
                            pass
                        refresh_mode()
                        messagebox.showerror(
                            "GICLÉE HOME FLOW",
                            f"Nie udało się zastosować trybu scrolla:\n{error}",
                            parent=host,
                        )

                    host.after(0, fail)
                    return

                def finish() -> None:
                    try:
                        combo.configure(state="readonly")
                    except Exception:
                        pass
                    label = home_scroll_mode.SCROLL_MODE_LABELS[applied]
                    if synchronized is True:
                        preview = (
                            home_features.preview_url(local=True)
                            + f"&giclee_revision={revision}"
                        )
                        webbrowser.open(preview)
                        show_toast(
                            host,
                            f"Zastosowano: {label}. Theme Dev ma nową rewizję.",
                            duration_ms=3200,
                        )
                    elif synchronized is None:
                        show_toast(
                            host,
                            f"Zastosowano: {label}. Uruchom Theme Dev, aby zobaczyć zmianę.",
                            duration_ms=3200,
                        )
                    else:
                        show_toast(
                            host,
                            f"Zapisano: {label}, ale Theme Dev nie potwierdził synchronizacji.",
                            duration_ms=3600,
                        )
                        messagebox.showwarning(
                            "GICLÉE HOME FLOW",
                            "Pliki zapisano atomowo, ale lokalny Theme Dev nie podał "
                            "najnowszej rewizji w wyznaczonym czasie. Uruchom ponownie "
                            "Theme Dev zamiast wielokrotnie odświeżać starą kartę.",
                            parent=host,
                        )

                host.after(0, finish)

            threading.Thread(
                target=worker,
                daemon=True,
                name="giclee-scroll-mode-sync",
            ).start()

        combo.bind("<<ComboboxSelected>>", selected_mode)

    setattr(decorate_with_revision_guard, "_giclee_theme_dev_revision_guard", True)
    setattr(decorate_with_revision_guard, "__wrapped__", current_decorator)
    home_flow_gui._decorate_home_editor = decorate_with_revision_guard
    _GUI_GUARD_INSTALLED = True


__all__ = [
    "install_safe_theme_writes",
    "install_theme_dev_revision_guard",
    "last_build_revision",
    "wait_for_theme_dev_revision",
]
