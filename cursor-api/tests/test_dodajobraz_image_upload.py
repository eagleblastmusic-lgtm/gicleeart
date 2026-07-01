"""Test skalowania obrazow pod limit Shopify 20 MP."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestShopifyImageUpload:
    def test_target_size_under_limit(self) -> None:
        from Komponenty.dodajobraz.image_upload import (
            SHOPIFY_SAFE_MAX_PIXELS,
            _target_size,
        )

        w, h = 8000, 3000
        tw, th = _target_size(w, h, SHOPIFY_SAFE_MAX_PIXELS)
        assert tw * th <= SHOPIFY_SAFE_MAX_PIXELS
        assert abs(tw / th - w / h) < 0.02

    def test_target_size_unchanged_when_small(self) -> None:
        from Komponenty.dodajobraz.image_upload import (
            SHOPIFY_SAFE_MAX_PIXELS,
            _target_size,
        )

        assert _target_size(4000, 3000, SHOPIFY_SAFE_MAX_PIXELS) == (4000, 3000)
