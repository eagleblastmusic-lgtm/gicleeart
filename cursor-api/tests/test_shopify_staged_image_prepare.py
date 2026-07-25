from __future__ import annotations

from pathlib import Path

from PIL import Image

from Komponenty.dodajobraz.shopify_client import (
    _STAGED_IMAGE_MAX_BYTES,
    _prepare_image_for_staged_upload,
)


def test_prepare_keeps_small_jpeg(tmp_path: Path) -> None:
    path = tmp_path / "small.jpg"
    Image.new("RGB", (200, 120), color=(20, 20, 20)).save(path, format="JPEG", quality=90)
    raw, name, mime = _prepare_image_for_staged_upload(path)
    assert name == "small.jpg"
    assert mime == "image/jpeg"
    assert raw == path.read_bytes()


def test_prepare_compresses_huge_png(tmp_path: Path) -> None:
    import os

    path = tmp_path / "huge.png"
    # Szum + PNG bez kompresji → plik powyżej limitu staged upload.
    img = Image.frombytes("RGB", (3600, 2800), os.urandom(3600 * 2800 * 3))
    img.save(path, format="PNG", compress_level=0)
    assert path.stat().st_size > _STAGED_IMAGE_MAX_BYTES
    raw, name, mime = _prepare_image_for_staged_upload(path)
    assert name.endswith(".jpg")
    assert mime == "image/jpeg"
    assert len(raw) <= _STAGED_IMAGE_MAX_BYTES
    assert len(raw) < path.stat().st_size


def test_entity_too_large_message_is_human() -> None:
    from Komponenty.dodajobraz import shopify_client as sc

    source = Path(sc.__file__).read_text(encoding="utf-8")
    assert "Plik jest za duży dla uploadu do Shopify Files" in source
    assert "_STAGED_MULTIPART_HEADROOM" in source
