"""Testy local-first podglądów obrazów (F4.1.1)."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Komponenty.stronaglowna import service


def test_resolve_local_shopify_image_path_assets(tmp_path: Path) -> None:
    assets = tmp_path / "assets"
    assets.mkdir()
    img = assets / "hero.webp"
    img.write_bytes(b"webp-bytes")

    with patch.object(service, "theme_root", return_value=tmp_path):
        found = service.resolve_local_shopify_image_path("shopify://shop_images/hero.webp")

    assert found == img


def test_fetch_thumbnail_bytes_uses_local_file(tmp_path: Path) -> None:
    assets = tmp_path / "assets"
    assets.mkdir()
    img = assets / "bio.jpg"
    img.write_bytes(b"jpeg-bytes")

    with patch.object(service, "theme_root", return_value=tmp_path):
        raw = service.fetch_thumbnail_bytes(shopify_ref="shopify://shop_images/bio.jpg")

    assert raw == b"jpeg-bytes"


def test_fetch_thumbnail_bytes_skips_remote_in_studio_inline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GICLEE_STUDIO_INLINE", "1")
    urlopen = MagicMock()

    with patch.object(service, "resolve_shopify_image_url", return_value="https://cdn.example/x.jpg"):
        with patch.object(service, "urlopen", urlopen):
            raw = service.fetch_thumbnail_bytes(shopify_ref="shopify://shop_images/missing.jpg")

    assert raw is None
    urlopen.assert_not_called()


def test_fetch_thumbnail_bytes_remote_outside_studio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GICLEE_STUDIO_INLINE", raising=False)
    response = MagicMock()
    response.read.return_value = b"remote"
    response.__enter__ = MagicMock(return_value=response)
    response.__exit__ = MagicMock(return_value=False)

    with patch.object(service, "resolve_local_shopify_image_path", return_value=None):
        with patch.object(service, "resolve_shopify_image_url", return_value="https://cdn.example/x.jpg"):
            with patch.object(service, "urlopen", return_value=response) as urlopen:
                raw = service.fetch_thumbnail_bytes(shopify_ref="shopify://shop_images/x.jpg")

    assert raw == b"remote"
    urlopen.assert_called_once()
