"""Testy wersji przezroczystych mockupow."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from Komponenty.dodajobraz.parser import MOCKUP_DISPLAY_ORIGINAL, MOCKUP_DISPLAY_TRANSPARENT
from Komponenty.mockup.transparent import (
    ProductMockupImage,
    delete_product_mockup,
    find_mockup_pair,
    list_product_mockups,
    upload_transparent_mockup_file,
)


def test_list_and_pair_mockups() -> None:
    images = [
        {
            "id": 1,
            "position": 1,
            "alt": "Artist - Title - (mockup) - CZB",
            "src": "https://cdn.shopify.com/files/title_-_mockup_-_czb.webp",
            "width": 1000,
            "height": 1200,
        },
        {
            "id": 2,
            "position": 2,
            "alt": "Artist - Title - (mockup) - CZB - (przezroczysty)",
            "src": "https://cdn.shopify.com/files/title_-_mockup_-_czb_-_przezroczysty.webp",
            "width": 1000,
            "height": 1200,
        },
    ]
    mockups = list_product_mockups(images)
    assert len(mockups) == 2
    original = mockups[0]
    o, t = find_mockup_pair(mockups, source=original)
    assert o is not None and o.image_id == 1
    assert t is not None and t.image_id == 2
    assert isinstance(original, ProductMockupImage)


def test_delete_transparent_resets_display_pref() -> None:
    transparent = ProductMockupImage(
        image_id=2,
        position=2,
        alt="Artist - Title - (mockup) - CZB - (przezroczysty)",
        src="https://cdn.shopify.com/x.webp",
        variant="CZB",
        is_transparent=True,
        width=100,
        height=100,
    )
    prefs = {"CZB": MOCKUP_DISPLAY_TRANSPARENT}

    with patch("Komponenty.mockup.transparent.sc.delete_product_image") as delete_mock, patch(
        "Komponenty.mockup.transparent.save_mockup_display_pref",
        return_value={"CZB": MOCKUP_DISPLAY_ORIGINAL},
    ) as save_mock:
        out = delete_product_mockup("shop", "token", 123, transparent, display_prefs=prefs)

    delete_mock.assert_called_once_with("shop", "token", 123, 2)
    save_mock.assert_called_once()
    assert out["CZB"] == MOCKUP_DISPLAY_ORIGINAL


def test_upload_transparent_from_disk(tmp_path: Path) -> None:
    file_path = tmp_path / "mock.webp"
    file_path.write_bytes(b"x")
    source = ProductMockupImage(
        image_id=1,
        position=1,
        alt="Artist - Title - (mockup) - CZB",
        src="https://cdn.shopify.com/x.webp",
        variant="CZB",
        is_transparent=False,
        width=100,
        height=100,
    )

    with patch("Komponenty.mockup.transparent.sc.load_session", return_value=("shop", "token")), patch(
        "Komponenty.mockup.transparent.sc.list_product_images", return_value=[]
    ), patch(
        "Komponenty.mockup.transparent.sc.upload_image", return_value={"id": 99}
    ) as upload_mock, patch(
        "Komponenty.mockup.transparent.load_mockup_display_prefs", return_value={}
    ):
        res = upload_transparent_mockup_file(
            product_id=123,
            source=source,
            file_path=file_path,
        )

    upload_mock.assert_called_once()
    assert res["image_id"] == 99
    assert "(przezroczysty)" in res["alt"]
