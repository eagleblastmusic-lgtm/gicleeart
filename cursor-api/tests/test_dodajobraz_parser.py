"""Testy parsowania nazw plikow i metadanych tytulu (dodajobraz)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestParseFilename:
    def test_basic_dash(self) -> None:
        from Komponenty.dodajobraz.parser import parse_filename

        a, t = parse_filename("Hans Dahl - Babie lato.jpg")
        assert a == "Hans Dahl"
        assert t == "Babie lato"

    def test_underscore_like_spaces(self) -> None:
        from Komponenty.dodajobraz.parser import parse_filename

        a, t = parse_filename("Jan_Matejko_-_Bitwa.jpg")
        assert "Matejko" in a
        assert "Bitwa" in t

    def test_en_dash_separator(self) -> None:
        from Komponenty.dodajobraz.parser import parse_filename

        a, t = parse_filename("A - B \u2013 C.jpg")
        assert a == "A"
        assert "B" in t and "C" in t


class TestParseTitleMetadata:
    def test_plain(self) -> None:
        from Komponenty.dodajobraz.parser import parse_title_metadata

        base, fu, cor, role, fkind = parse_title_metadata("Babie lato")
        assert base == "Babie lato"
        assert fu is None
        assert cor is None
        assert role is None
        assert fkind is None

    def test_follow_up_and_correction(self) -> None:
        from Komponenty.dodajobraz.parser import FOLLOW_UP_KIND_F, parse_title_metadata

        base, fu, cor, role, fkind = parse_title_metadata("Babie lato F2 KK")
        assert base == "Babie lato"
        assert fu == 2
        assert cor == "KK"
        assert role is None
        assert fkind == FOLLOW_UP_KIND_F

    def test_preview_suffix(self) -> None:
        from Komponenty.dodajobraz.parser import (
            IMAGE_ROLE_PREVIEW,
            parse_title_metadata,
            preview_alt_text,
        )

        base, fu, cor, role, fkind = parse_title_metadata("Babie lato - (preview)")
        assert base == "Babie lato"
        assert fu is None
        assert cor is None
        assert role == IMAGE_ROLE_PREVIEW
        assert fkind is None
        assert preview_alt_text("Hans Dahl", "Babie lato") == "Hans Dahl - Babie lato (preview)"

    def test_full_suffix(self) -> None:
        from Komponenty.dodajobraz.parser import IMAGE_ROLE_FULL, parse_title_metadata

        base, fu, cor, role, fkind = parse_title_metadata("Babie lato - Full")
        assert base == "Babie lato"
        assert role == IMAGE_ROLE_FULL
        assert fkind is None

    def test_mockup_suffix(self) -> None:
        from Komponenty.dodajobraz.parser import IMAGE_ROLE_MOCKUP, parse_title_metadata

        base, fu, cor, role, fkind = parse_title_metadata("Babie lato - (mockup)")
        assert base == "Babie lato"
        assert role == IMAGE_ROLE_MOCKUP
        assert fu is None

    def test_mockup_variant_czb(self) -> None:
        from Komponenty.dodajobraz.parser import IMAGE_ROLE_MOCKUP, parse_title_metadata

        base, fu, cor, role, fkind = parse_title_metadata("Babie lato - (mockup) - CZB")
        assert base == "Babie lato"
        assert role == IMAGE_ROLE_MOCKUP
        assert fu is None

    def test_mockup_variant_czcz(self) -> None:
        from Komponenty.dodajobraz.parser import IMAGE_ROLE_MOCKUP, parse_title_metadata

        base, fu, cor, role, fkind = parse_title_metadata("Babie lato - (mockup) - CZCZ")
        assert base == "Babie lato"
        assert role == IMAGE_ROLE_MOCKUP


class TestMockupImageRefs:
    def test_cdn_url_without_parentheses(self) -> None:
        from Komponenty.dodajobraz.parser import (
            image_ref_is_mockup,
            mockup_suffixes_in_image_refs,
        )

        url = (
            "https://cdn.shopify.com/s/files/1/1/files/"
            "abraham_hulk_-_shipping_at_sunset_-_mockup_-_czb.webp?v=1"
        )
        assert image_ref_is_mockup(url)
        assert mockup_suffixes_in_image_refs([url]) == {"CZB"}

    def test_alt_with_suffix(self) -> None:
        from Komponenty.dodajobraz.parser import mockup_suffixes_in_image_refs

        alt = "Van Gogh - Starry Night - (mockup) - CZCZ"
        assert mockup_suffixes_in_image_refs([alt]) == {"CZCZ"}

    def test_plain_title_alt_not_mockup(self) -> None:
        from Komponenty.dodajobraz.parser import (
            image_ref_is_mockup,
            mockup_suffixes_in_image_refs,
        )

        alt = "Van Gogh - Starry Night"
        assert not image_ref_is_mockup(alt)
        assert mockup_suffixes_in_image_refs([alt]) == set()

    def test_product_images_mixed(self) -> None:
        from Komponenty.dodajobraz.parser import mockup_suffixes_in_product_images

        images = [
            {
                "alt": "Artist - Title",
                "src": "https://cdn.shopify.com/files/title_-_mockup_-_czb.webp",
            },
            {
                "alt": "Artist - Title - (mockup) - CZCZ",
                "src": "https://cdn.shopify.com/files/title_-_mockup_-_czcz.webp",
            },
        ]
        assert mockup_suffixes_in_product_images(images) == {"CZB", "CZCZ"}

    def test_mockup_transparent_alt(self) -> None:
        from Komponenty.dodajobraz.parser import (
            alt_is_mockup_transparent,
            mockup_transparent_alt_text,
            mockup_variant_from_ref,
        )

        alt = mockup_transparent_alt_text("Van Gogh", "Starry Night", name_suffix="CZB")
        assert alt == "Van Gogh - Starry Night - (mockup) - CZB - (przezroczysty)"
        assert alt_is_mockup_transparent(alt)
        assert mockup_variant_from_ref(alt) == "CZB"

    def test_installment_suffix(self) -> None:
        from Komponenty.dodajobraz.parser import FOLLOW_UP_KIND_I, parse_title_metadata

        base, fu, cor, role, fkind = parse_title_metadata("Babie lato I3")
        assert base == "Babie lato"
        assert fu == 3
        assert fkind == FOLLOW_UP_KIND_I
        assert role is None


class TestParseFollowUp:
    def test_f2(self) -> None:
        from Komponenty.dodajobraz.parser import parse_follow_up

        base, n = parse_follow_up("Tytul F3")
        assert base == "Tytul"
        assert n == 3

    def test_no_suffix(self) -> None:
        from Komponenty.dodajobraz.parser import parse_follow_up

        base, n = parse_follow_up("Tytul")
        assert n is None


class TestArtistCollectionTitle:
    def test_bruegel_starszy(self) -> None:
        from Komponenty.dodajobraz.parser import artist_collection_title

        assert artist_collection_title("Pieter Bruegel (starszy)") == "Bruegel, Pieter (starszy)"

    def test_van_gogh(self) -> None:
        from Komponenty.dodajobraz.parser import artist_collection_title

        assert artist_collection_title("Vincent van Gogh") == "van Gogh, Vincent"


class TestCatalogArtistSort:
    def test_van_gogh_particle_in_given(self) -> None:
        from Komponenty.dodajobraz.parser import (
            catalog_artist_sort_key,
            format_catalog_artist_title,
            normalize_catalog_artist_title,
        )

        assert normalize_catalog_artist_title("Gogh, Vincent van") == ("Van Gogh", "Vincent")
        assert format_catalog_artist_title("Gogh, Vincent van") == "Van Gogh, Vincent"
        gogh_key = catalog_artist_sort_key("Gogh, Vincent van")
        gierymski_key = catalog_artist_sort_key("Gierymski, Aleksander")
        velde_key = catalog_artist_sort_key("Velde, Willem")
        assert gogh_key > gierymski_key
        assert velde_key > gogh_key

    def test_van_ruisdael(self) -> None:
        from Komponenty.dodajobraz.parser import catalog_artist_sort_key

        assert catalog_artist_sort_key("Van Ruisdael, Jacob") < catalog_artist_sort_key(
            "Velde, Willem"
        )


class TestComputeSourceKey:
    def test_slug_shape(self) -> None:
        from Komponenty.dodajobraz.parser import compute_source_key

        k = compute_source_key("Hans Dahl", "Girl beside a fjord")
        assert k == "hans-dahl__girl-beside-a-fjord"
        k2 = compute_source_key("Hans Dahl", "Girl beside a fjord")
        assert k == k2


class TestParseBatchResponseJson:
    def test_polish_typographic_quotes_in_akapit(self) -> None:
        from Komponenty.dodajobraz.prompt_builder import parse_batch_response_json

        blob = """[
  {
    "plik": "test.webp",
    "tytul_polski": "Tytul",
    "tytul_orginalny": "Title",
    "akapity": [
      "Niebo, ów ukochany „kluczowy element nastroju", piętrzy się tu.",
      "Drugi akapit opisujacy scene parku i spokojna atmosfere.",
      "Trzeci akapit o harmonii czlowieka z natura w stylu Constable."
    ],
    "data_powstania": "1816",
    "miejsce_powstania": "Anglia",
    "technika": "Olej",
    "gatunek": "Pejzaż",
    "nurt": "Romantyzm",
    "forma": "Malarstwo",
    "tagi": ["a"],
    "kategoria": "Obrazy"
  }
]"""
        items = parse_batch_response_json(blob)
        assert len(items) == 1
        assert "„kluczowy" in items[0]["akapity"][0]
