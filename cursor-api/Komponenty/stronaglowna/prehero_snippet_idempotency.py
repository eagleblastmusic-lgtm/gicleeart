"""Deterministyczne składanie bloków pre-Hero w wygenerowanym snippecie.

Moduł stanowi mały hotfix do czasu scalenia logiki bezpośrednio z
``prehero_integration.py``. Normalizuje białe znaki wokół ``</script>`` oraz
bloków oznaczonych markerami, dzięki czemu wielokrotne generowanie daje
identyczny wynik bajt w bajt.
"""

from __future__ import annotations

import json
from typing import Any

from . import prehero_integration as _base


def inject_prehero_into_snippet(
    text: str,
    config: dict[str, Any] | None = None,
) -> str:
    clean = _base._remove_marked_block(text, _base._SCRIPT_BEGIN, _base._SCRIPT_END)
    clean = _base._remove_marked_block(clean, _base._ASSETS_BEGIN, _base._ASSETS_END)
    cfg = dict(config or _base.export_prehero_config(None))

    if "window.GICLEE_HOME_STACK = true;" not in clean or not cfg.get("enabled", True):
        return clean.rstrip() + "\n"

    close_index = clean.find("</script>")
    if close_index < 0:
        return clean

    before_script = clean[:close_index].rstrip()
    after_script = clean[close_index + len("</script>") :].lstrip("\r\n")
    public_cfg = {key: value for key, value in cfg.items() if key != "videoRef"}

    script_block = "\n".join(
        (
            _base._SCRIPT_BEGIN,
            "window.GICLEE_HOME_SECTION_SCROLL_DISABLED = true;",
            "window.GICLEE_HOME_SCROLL_CONFIG = Object.assign({}, window.GICLEE_HOME_SCROLL_CONFIG || {}, { enabled: false });",
            "window.GICLEE_PREHERO_CONFIG = " + json.dumps(public_cfg, ensure_ascii=False) + ";",
            "window.GICLEE_PREHERO_SCRUB_VIDEO_URL = " + _base._video_liquid(cfg) + ";",
            "window.GICLEE_PREHERO_PORTAL_VIDEO_URL = " + _base._portal_video_liquid() + ";",
            "(function () {",
            "  function disableHomeSectionScroll() {",
            "    var api = window.GICLEE_HOME_SECTION_SCROLL;",
            "    if (api && typeof api.destroy === 'function') api.destroy();",
            "    document.documentElement.removeAttribute('data-giclee-home-section-scroll');",
            "    document.documentElement.classList.remove('giclee-home-section-scroll');",
            "  }",
            "  if (document.readyState === 'loading') {",
            "    document.addEventListener('DOMContentLoaded', function () { requestAnimationFrame(disableHomeSectionScroll); }, { once: true });",
            "  } else { requestAnimationFrame(disableHomeSectionScroll); }",
            "  window.addEventListener('load', disableHomeSectionScroll, { once: true });",
            "})();",
            _base._SCRIPT_END,
        )
    )

    asset_block = "\n".join(
        (
            _base._ASSETS_BEGIN,
            "{{ 'giclee-home-prehero-scrub.css' | asset_url | stylesheet_tag }}",
            "{{ 'giclee-home-prehero-chrome.css' | asset_url | stylesheet_tag }}",
            "{{ 'giclee-home-prehero-reveal.css' | asset_url | stylesheet_tag }}",
            "{{ 'giclee-home-hero-horizontal-curtain.css' | asset_url | stylesheet_tag }}",
            "<script src=\"{{ 'giclee-home-prehero-scrub.js' | asset_url }}\" defer></script>",
            "<script src=\"{{ 'giclee-home-prehero-chrome.js' | asset_url }}\" defer></script>",
            "<script src=\"{{ 'giclee-home-prehero-reveal.js' | asset_url }}\" defer></script>",
            "<script src=\"{{ 'giclee-home-hero-horizontal-curtain.js' | asset_url }}\" defer></script>",
            _base._ASSETS_END,
        )
    )

    parts = [
        before_script,
        "",
        script_block,
        "</script>",
        asset_block,
    ]
    if after_script.strip():
        parts.append(after_script.rstrip())
    return "\n".join(parts).rstrip() + "\n"


def install_prehero_snippet_idempotency_fix() -> None:
    if getattr(_base.inject_prehero_into_snippet, "_giclee_idempotent", False):
        return
    setattr(inject_prehero_into_snippet, "_giclee_idempotent", True)
    _base.inject_prehero_into_snippet = inject_prehero_into_snippet
