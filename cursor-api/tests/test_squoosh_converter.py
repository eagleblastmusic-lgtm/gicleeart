"""Testy konwertera WebP (Squoosh)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PIL")

from Komponenty.squoosh.converter import (
    OVERSIZED_JPEG_FULL,
    OVERSIZED_SCALE_WEBP,
    WEBP_MAX_DIMENSION,
    convert_to_webp,
    exceeds_webp_limit,
    fit_image_for_webp,
    is_image_path,
    output_path_for,
)
from Komponenty.squoosh.squoosh_cli import build_webp_config, squoosh_cli_available


def test_output_path_same_folder(tmp_path: Path) -> None:
    src = tmp_path / "a.jpg"
    src.write_bytes(b"x")
    assert output_path_for(src, None) == tmp_path / "a.webp"


def test_output_path_custom_dir(tmp_path: Path) -> None:
    src = tmp_path / "in" / "b.png"
    src.parent.mkdir()
    src.write_bytes(b"x")
    out = tmp_path / "out"
    assert output_path_for(src, out) == out / "b.webp"


def test_output_path_name_suffix(tmp_path: Path) -> None:
    from Komponenty.squoosh.converter import normalize_name_suffix

    assert normalize_name_suffix("Full") == " - Full"
    assert normalize_name_suffix("-KK") == " - KK"
    assert normalize_name_suffix(" - Full") == " - Full"
    src = tmp_path / "Obraz.jpg"
    src.write_bytes(b"x")
    assert output_path_for(src, None, name_suffix="Full") == tmp_path / "Obraz - Full.webp"
    assert output_path_for(src, None, name_suffix="-KK") == tmp_path / "Obraz - KK.webp"
    assert output_path_for(src, None, name_suffix="") == tmp_path / "Obraz.webp"


def test_fit_image_for_webp_scales_down() -> None:
    from PIL import Image

    im = Image.new("RGB", (20000, 800), (10, 20, 30))
    out, note = fit_image_for_webp(im)
    assert max(out.size) <= WEBP_MAX_DIMENSION
    assert note is not None
    assert "20000x800" in note


def test_exceeds_webp_limit(tmp_path: Path) -> None:
    from PIL import Image

    big = tmp_path / "big.jpg"
    Image.new("RGB", (17000, 400), (1, 2, 3)).save(big, format="JPEG")
    assert exceeds_webp_limit(big) is True
    ok = tmp_path / "ok.jpg"
    Image.new("RGB", (1000, 800), (1, 2, 3)).save(ok, format="JPEG")
    assert exceeds_webp_limit(ok) is False


def test_convert_oversized_scale_webp(tmp_path: Path) -> None:
    from PIL import Image

    src = tmp_path / "huge.jpg"
    Image.new("RGB", (17000, 400), (50, 60, 70)).save(src, format="JPEG", quality=85)
    dest = tmp_path / "huge.webp"
    res = convert_to_webp(
        src,
        dest,
        quality=80,
        method=4,
        engine="pillow",
        oversized_mode=OVERSIZED_SCALE_WEBP,
    )
    assert dest.is_file()
    assert res.get("format") == "webp"
    with Image.open(dest) as im:
        assert max(im.size) <= WEBP_MAX_DIMENSION


def test_convert_oversized_jpeg_full(tmp_path: Path) -> None:
    from PIL import Image

    src = tmp_path / "huge.jpg"
    Image.new("RGB", (17000, 400), (50, 60, 70)).save(src, format="JPEG", quality=85)
    dest = tmp_path / "huge.webp"
    res = convert_to_webp(
        src,
        dest,
        quality=80,
        method=4,
        engine="pillow",
        oversized_mode=OVERSIZED_JPEG_FULL,
    )
    out = Path(res["dest"])
    assert out.suffix.lower() == ".jpg"
    assert out.is_file()
    with Image.open(out) as im:
        assert im.size == (17000, 400)


def test_convert_jpg_to_webp(tmp_path: Path) -> None:
    from PIL import Image

    src = tmp_path / "test.jpg"
    Image.new("RGB", (64, 48), (120, 80, 40)).save(src, format="JPEG")
    dest = tmp_path / "test.webp"
    res = convert_to_webp(src, dest, quality=80, method=4)
    assert dest.is_file()
    assert dest.stat().st_size > 0
    assert res["dst_bytes"] > 0


def test_build_webp_config_defaults() -> None:
    cfg = build_webp_config(quality=80, method=4, lossless=False, preserve_alpha=False)
    assert "'quality':80" in cfg
    assert "'method':4" in cfg
    assert "'lossless':0" in cfg
    assert "'alpha_compression':0" in cfg


def test_squoosh_cli_available() -> None:
    ok, _msg = squoosh_cli_available()
    assert isinstance(ok, bool)


@pytest.mark.skipif(not squoosh_cli_available()[0], reason="brak Squoosh CLI")
def test_convert_jpg_squoosh_cli(tmp_path: Path) -> None:
    from PIL import Image

    src = tmp_path / "test.jpg"
    Image.new("RGB", (120, 90), (200, 100, 50)).save(src, format="JPEG")
    dest = tmp_path / "test.webp"
    convert_to_webp(src, dest, quality=80, method=4, engine="squoosh")
    assert dest.is_file()
    assert dest.stat().st_size > 0
