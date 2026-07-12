from __future__ import annotations

import json
from pathlib import Path

import pytest


def _set_roots(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, Path]:
    local = tmp_path / "local"
    roaming = tmp_path / "roaming"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local))
    monkeypatch.setenv("GICLEEAPP_ROAMING_ROOT", str(roaming))
    return local, roaming


def _write_json(path: Path, payload: object) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    path.write_bytes(raw)
    return raw


def test_description_runtime_state_reads_legacy_and_writes_local_appdata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from Komponenty.dodajobraz import description_update as du

    local, _ = _set_roots(monkeypatch, tmp_path)
    legacy = tmp_path / "legacy-description"
    legacy.mkdir()

    names = {
        "_DESCRIPTION_UPDATE_MARKS_FILE": "description_update_marks.json",
        "_DESCRIPTION_PL_PENDING_MARKS_FILE": "description_pl_pending_marks.json",
        "_DESCRIPTION_GPT_TRANSLATION_MARKS_FILE": "description_gpt_translation_marks.json",
        "_DESCRIPTION_SONNET_TRANSLATION_MARKS_FILE": "description_sonnet_translation_marks.json",
        "_DESCRIPTION_FROM_IMAGE_MARKS_FILE": "description_from_image_marks.json",
        "_DESCRIPTION_DO_TLUMACZENIA_MARKS_FILE": "description_do_tlumaczenia_marks.json",
        "_DESCRIPTION_TRANSLATIONS_SENT_MARKS_FILE": "description_translations_sent_marks.json",
        "_DESCRIPTION_BEZ_16_MARKS_FILE": "description_bez_16_marks.json",
        "_TITLE_UPDATE_MARKS_FILE": "title_update_marks.json",
        "_DESCRIPTION_RESUME_FLAG_FILE": "description_resume_flag.json",
        "_COMPARE_VERSIONS_FILE": "compare_versions.json",
        "_DESCRIPTION_COMPARE_LLM_FILE": "description_compare_llm.json",
        "_DESCRIPTION_UPDATE_PREFS_FILE": "description_update_prefs.json",
    }
    monkeypatch.setattr(du, "_LEGACY_DATA_DIR", legacy)
    for attr, filename in names.items():
        monkeypatch.setattr(du, attr, legacy / filename)

    legacy_update = _write_json(legacy / "description_update_marks.json", [11])
    legacy_resume = _write_json(legacy / "description_resume_flag.json", 12)
    legacy_compare = _write_json(
        legacy / "compare_versions.json",
        {"13": {"pl": {"versions": {"0": ["legacy"]}, "working": {}}}},
    )
    legacy_llm = _write_json(legacy / "description_compare_llm.json", {"provider": "gpt"})
    legacy_prefs = _write_json(legacy / "description_update_prefs.json", {"auto_copy_prompt": False})
    legacy_sent = _write_json(legacy / "description_translations_sent_marks.json", [999])

    assert du.load_description_update_marks() == {11}
    assert du.load_description_resume_flag() == 12
    assert du.load_compare_versions()[13]["pl"]["versions"][0][0] == "legacy"
    assert du.load_description_compare_llm() == "gpt"
    assert du.load_description_auto_copy_prompt() is False

    du.save_description_update_marks({21})
    du.save_description_pl_pending_marks({22})
    du.save_description_gpt_translation_marks({23})
    du.save_description_sonnet_translation_marks({24})
    du.save_description_from_image_marks({25})
    du.save_description_do_tlumaczenia_marks({26})
    du.save_description_bez_16_marks({27})
    du.save_title_update_marks({28})
    du.set_description_resume_flag(29)
    du.save_compare_versions({30: {"pl": {"versions": {0: ["external"]}, "working": {}}}})
    du.save_description_compare_llm("sonnet")
    du.save_description_auto_copy_prompt(True)

    target_root = local / "data/Komponenty/dodajobraz/data"
    expected = {
        "description_update_marks.json",
        "description_pl_pending_marks.json",
        "description_gpt_translation_marks.json",
        "description_sonnet_translation_marks.json",
        "description_from_image_marks.json",
        "description_do_tlumaczenia_marks.json",
        "description_bez_16_marks.json",
        "title_update_marks.json",
        "description_resume_flag.json",
        "compare_versions.json",
        "description_compare_llm.json",
        "description_update_prefs.json",
    }
    assert {path.name for path in target_root.iterdir()} == expected
    assert du.load_description_update_marks() == {21}
    assert du.load_description_resume_flag() == 29
    assert du.load_description_compare_llm() == "sonnet"
    assert du.load_description_auto_copy_prompt() is True

    assert (legacy / "description_update_marks.json").read_bytes() == legacy_update
    assert (legacy / "description_resume_flag.json").read_bytes() == legacy_resume
    assert (legacy / "compare_versions.json").read_bytes() == legacy_compare
    assert (legacy / "description_compare_llm.json").read_bytes() == legacy_llm
    assert (legacy / "description_update_prefs.json").read_bytes() == legacy_prefs
    assert (legacy / "description_translations_sent_marks.json").read_bytes() == legacy_sent
    assert not (target_root / "description_translations_sent_marks.json").exists()


def test_variant_templates_read_legacy_and_write_roaming_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from Komponenty.dodajobraz import templates

    _, roaming = _set_roots(monkeypatch, tmp_path)
    legacy_dir = tmp_path / "legacy-templates"
    legacy_file = legacy_dir / "variant_templates.json"
    legacy_bytes = _write_json(
        legacy_file,
        {
            "templates": [
                {
                    "id": "legacy",
                    "name": "Legacy",
                    "is_default": True,
                    "source": "manual",
                    "options": [],
                    "variants": [],
                    "created_at": "",
                    "updated_at": "",
                }
            ]
        },
    )

    monkeypatch.setattr(templates, "_LEGACY_DATA_DIR", legacy_dir)
    monkeypatch.setattr(templates, "_LEGACY_TEMPLATES_FILE", legacy_file)
    monkeypatch.setattr(templates, "_DATA_DIR", legacy_dir)
    monkeypatch.setattr(templates, "_TEMPLATES_FILE", legacy_file)

    assert templates.load_templates()[0].name == "Legacy"
    templates.save_templates([templates.VariantTemplate.new(name="External", is_default=True)])

    target = roaming / "config/Komponenty/dodajobraz/data/variant_templates.json"
    assert json.loads(target.read_text(encoding="utf-8"))["templates"][0]["name"] == "External"
    assert templates.load_templates()[0].name == "External"
    assert legacy_file.read_bytes() == legacy_bytes


def test_product_assignments_read_legacy_and_write_local_appdata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from Komponenty.dodajobraz import product_template_assignments as assignments

    local, _ = _set_roots(monkeypatch, tmp_path)
    legacy_dir = tmp_path / "legacy-assignments"
    legacy_file = legacy_dir / "product_template_assignments.json"
    legacy_bytes = _write_json(legacy_file, {"assignments": {"101": "legacy"}})

    monkeypatch.setattr(assignments, "_LEGACY_DATA_DIR", legacy_dir)
    monkeypatch.setattr(assignments, "_LEGACY_ASSIGNMENTS_FILE", legacy_file)
    monkeypatch.setattr(assignments, "_DATA_DIR", legacy_dir)
    monkeypatch.setattr(assignments, "_ASSIGNMENTS_FILE", legacy_file)

    assert assignments.get_assigned_template_id(101) == "legacy"
    assignments.set_product_template_assignment(102, "external")

    target = local / "data/Komponenty/dodajobraz/data/product_template_assignments.json"
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["assignments"] == {"101": "legacy", "102": "external"}
    assert legacy_file.read_bytes() == legacy_bytes


def test_market_configuration_and_prices_write_roaming_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from Komponenty.dodajobraz import market_variant_prices as prices
    from Komponenty.dodajobraz import markets

    _, roaming = _set_roots(monkeypatch, tmp_path)

    legacy_markets = tmp_path / "legacy-markets.json"
    legacy_market_bytes = _write_json(
        legacy_markets,
        {
            "base_market": "pl",
            "markets": [
                {
                    "code": "pl",
                    "name_pl": "Polska",
                    "locale": "pl",
                    "currency": "PLN",
                    "url_prefix": "",
                    "markup_percent": 0,
                    "is_base": True,
                },
                {
                    "code": "de",
                    "name_pl": "Niemcy",
                    "locale": "de",
                    "currency": "EUR",
                    "url_prefix": "/de",
                    "markup_percent": 10,
                },
            ],
        },
    )
    monkeypatch.setattr(markets, "_LEGACY_CONFIG_PATH", legacy_markets)
    monkeypatch.setattr(markets, "CONFIG_PATH", legacy_markets)
    assert markets.get_market("de").markup_percent == 10
    markets.update_market_markup("de", 15)

    markets_target = roaming / "config/Komponenty/dodajobraz/markets_config.json"
    assert json.loads(markets_target.read_text(encoding="utf-8"))["markets"][1]["markup_percent"] == 15
    assert legacy_markets.read_bytes() == legacy_market_bytes

    legacy_prices_dir = tmp_path / "legacy-prices"
    legacy_prices_file = legacy_prices_dir / "market_variant_prices.json"
    legacy_price_bytes = _write_json(legacy_prices_file, {"markets": {"de": {"Dąb|A4": "99.00"}}})
    monkeypatch.setattr(prices, "_LEGACY_DATA_DIR", legacy_prices_dir)
    monkeypatch.setattr(prices, "_LEGACY_PRICES_FILE", legacy_prices_file)
    monkeypatch.setattr(prices, "_DATA_DIR", legacy_prices_dir)
    monkeypatch.setattr(prices, "_PRICES_FILE", legacy_prices_file)
    assert prices.get_market_variant_price("de", "Dąb", "A4") == "99.00"
    prices.set_market_variant_price("de", "Dąb", "A3", "129.00")

    prices_target = roaming / "config/Komponenty/dodajobraz/data/market_variant_prices.json"
    saved = json.loads(prices_target.read_text(encoding="utf-8"))
    assert saved["markets"]["de"]["Dąb|A4"] == "99.00"
    assert saved["markets"]["de"]["Dąb|A3"] == "129.00"
    assert legacy_prices_file.read_bytes() == legacy_price_bytes


def test_r2_history_seeds_legacy_rows_and_appends_only_to_local_appdata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from Komponenty.dodajobraz import r2_usage

    local, _ = _set_roots(monkeypatch, tmp_path)
    legacy_file = tmp_path / "legacy-r2" / "zoom_upload_history.json"
    legacy_bytes = _write_json(legacy_file, [{"bytes": 100, "handle": "legacy", "at": "2026-01-01T00:00:00+00:00"}])
    monkeypatch.setattr(r2_usage, "_LEGACY_ZOOM_HISTORY_FILE", legacy_file)
    monkeypatch.setattr(r2_usage, "_ZOOM_HISTORY_FILE", legacy_file)

    assert r2_usage._load_recent_upload_byte_sizes() == [100]
    r2_usage.record_zoom_upload(total_bytes=200, handle="external")

    target = local / "data/Komponenty/dodajobraz/data/zoom_upload_history.json"
    rows = json.loads(target.read_text(encoding="utf-8"))
    assert [row["bytes"] for row in rows] == [100, 200]
    assert r2_usage._load_recent_upload_byte_sizes() == [100, 200]
    assert legacy_file.read_bytes() == legacy_bytes
