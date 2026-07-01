"""Gotowy kod Custom Pixel z URL i secret z .env."""

from __future__ import annotations

from pathlib import Path

from .env_config import allowed_shop_domain, collect_secret, effective_collect_url

_PIXEL_FILE = Path(__file__).resolve().parent / "pixel" / "giclee-analytics-pixel.js"


def build_pixel_snippet(*, port: int | None = None) -> str:
    raw = _PIXEL_FILE.read_text(encoding="utf-8")
    collect_url = effective_collect_url(port)
    secret = collect_secret()
    shop = allowed_shop_domain()

    import re

    raw = re.sub(
        r'var COLLECT_URL = "[^"]*";',
        f'var COLLECT_URL = "{collect_url}";',
        raw,
        count=1,
    )
    if secret:
        raw = re.sub(
            r'var COLLECT_SECRET = "[^"]*";',
            f'var COLLECT_SECRET = "{secret}";',
            raw,
            count=1,
        )
    raw = re.sub(
        r'var SHOP_DOMAIN = "[^"]*";',
        f'var SHOP_DOMAIN = "{shop}";',
        raw,
        count=1,
    )
    return raw
