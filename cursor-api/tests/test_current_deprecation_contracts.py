"""Regression coverage for deprecations exercised by the full baseline."""

from __future__ import annotations

import warnings
from datetime import datetime

from PIL import Image


def test_blog_topic_timestamp_preserves_historical_iso_shape_without_warning() -> None:
    from Komponenty.blog.storage import TopicProposal

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        proposal = TopicProposal.new("Temat")

    parsed = datetime.fromisoformat(proposal.created_at)
    assert parsed.tzinfo is None
    assert proposal.created_at == parsed.isoformat(timespec="seconds")


def test_visual_hash_uses_nondeprecated_pixel_api_when_available() -> None:
    from Komponenty.stronyzobrazami.search.visual_hash import dhash

    image = Image.new("RGB", (16, 16), color=(120, 80, 40))
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        value = dhash(image)

    assert isinstance(value, int)
    assert value >= 0
