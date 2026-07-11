from __future__ import annotations

from pathlib import Path

from . import prehero_video_preview as preview
from . import service


def test_video_ref_detection() -> None:
    assert preview._is_video_ref("shopify://files/videos/prehero.mp4") is True
    assert preview._is_video_ref("gid://shopify/Video/123") is True
    assert preview._is_video_ref("shopify://shop_images/poster.webp") is False
    assert preview._is_video_ref("") is False


def test_prehero_fallback_path_uses_theme_assets(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(service, "theme_root", lambda: tmp_path)
    assert preview.prehero_fallback_path() == tmp_path / "assets" / "giclee-home-prehero-scrub.mp4"


def test_video_thumbnail_wrapper_uses_remote_poster(monkeypatch) -> None:
    monkeypatch.setattr(preview, "_download_video_preview", lambda _ref: b"poster-bytes")
    result = service.fetch_thumbnail_bytes(
        shopify_ref="shopify://files/videos/current-prehero.mp4"
    )
    assert result == b"poster-bytes"


def test_missing_local_video_has_no_frame(tmp_path: Path) -> None:
    assert preview._video_frame_bytes(tmp_path / "missing.mp4") is None
