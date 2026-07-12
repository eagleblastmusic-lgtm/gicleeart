from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest


def _bytes(path: Path) -> bytes | None:
    return path.read_bytes() if path.is_file() else None


def _assert_unchanged(path: Path, before: bytes | None) -> None:
    after = path.read_bytes() if path.is_file() else None
    assert after == before


def test_kpir_writes_data_config_documents_and_append_log_outside_repo(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(tmp_path / "local"))
    monkeypatch.setenv("GICLEEAPP_ROAMING_ROOT", str(tmp_path / "roaming"))

    from Komponenty.kpir import storage as st
    from Komponenty.kpir.models import ChangeLogEntry, KpirSettings

    legacy_db = st._DB.legacy_path
    legacy_settings = st._SETTINGS.legacy_path
    legacy_log = st._CHANGELOG.legacy_path
    assert legacy_db is not None and legacy_settings is not None and legacy_log is not None
    before_db = _bytes(legacy_db)
    before_settings = _bytes(legacy_settings)
    before_log = _bytes(legacy_log)

    payload = {"next_entry_id": 4, "entries": [], "costs": []}
    st.save_db(payload)
    st.save_settings(KpirSettings(seller_name="Stage 1E"))
    st.append_changelog(
        ChangeLogEntry(
            id="change-1",
            entry_id="KPIR-000001",
            field_name="description",
            old_value="old",
            new_value="new",
            changed_at="2026-07-12T00:00:00",
        )
    )
    documents = st.documents_dir_for("exports", 2026, 7)

    expected_data = tmp_path / "local" / "data" / "Komponenty" / "kpir"
    expected_config = tmp_path / "roaming" / "config" / "Komponenty" / "kpir"
    assert st._DB.write_path == expected_data / "dane" / "kpir.json"
    assert st._CHANGELOG.write_path == expected_data / "dane" / "kpir_changelog.jsonl"
    assert st._SETTINGS.write_path == expected_config / "dane" / "kpir_settings.json"
    assert documents == expected_data / "documents" / "exports" / "2026" / "07"
    assert st.load_db()["next_entry_id"] == 4
    assert st.list_changelog_for_entry("KPIR-000001")[0].new_value == "new"

    _assert_unchanged(legacy_db, before_db)
    _assert_unchanged(legacy_settings, before_settings)
    _assert_unchanged(legacy_log, before_log)


def test_kpir_existing_temp_override_contract_is_preserved(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from Komponenty.kpir import storage as st
    from Komponenty.kpir.models import ChangeLogEntry, KpirSettings

    data = tmp_path / "dane"
    docs = tmp_path / "documents"
    monkeypatch.setattr(st, "_DATA_DIR", data)
    monkeypatch.setattr(st, "_DOCUMENTS_DIR", docs)
    monkeypatch.setattr(st, "_SETTINGS_FILE", data / "kpir_settings.json")
    monkeypatch.setattr(st, "_DB_FILE", data / "kpir.json")
    monkeypatch.setattr(st, "_CHANGELOG_FILE", data / "kpir_changelog.jsonl")

    st.save_db({"next_entry_id": 2, "entries": []})
    st.save_settings(KpirSettings(seller_name="Override"))
    st.append_changelog(
        ChangeLogEntry(
            id="c2",
            entry_id="KPIR-OVERRIDE",
            field_name="x",
            old_value="",
            new_value="1",
            changed_at="2026-07-12T00:00:00",
        )
    )

    assert (data / "kpir.json").is_file()
    assert (data / "kpir_settings.json").is_file()
    assert (data / "kpir_changelog.jsonl").is_file()
    assert st.documents_dir_for("exports", 2026, 1) == docs / "exports" / "2026" / "01"


def test_kalkulacja_splits_private_data_and_mutable_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(tmp_path / "local"))
    monkeypatch.setenv("GICLEEAPP_ROAMING_ROOT", str(tmp_path / "roaming"))

    from Komponenty.kalkulacja import store

    legacy_materials = store._DATA_FILES["materials.json"].legacy_path
    legacy_settings = store._DATA_FILES["settings.json"].legacy_path
    assert legacy_materials is not None and legacy_settings is not None
    before_materials = _bytes(legacy_materials)
    before_settings = _bytes(legacy_settings)

    store.save_materials([{"id": "MAT-1", "price": 12.5}])
    store.save_helpers({"paper": {"A4": 1.0}})
    store.save_price_table([{"id_full": "A4", "cost": 2.0}])
    store.save_cost_lines([{"name": "wood"}])
    store.save_sales_mix([])
    store.save_settings({"profile": "20X20"})
    store.save_wood_defaults({"price_per_meter": 9.5})

    data_dir = tmp_path / "local" / "data" / "Komponenty" / "kalkulacja" / "data"
    config_dir = tmp_path / "roaming" / "config" / "Komponenty" / "kalkulacja" / "data"
    for name in ("materials.json", "helpers.json", "price_table.json", "cost_lines.json", "sales_mix.json"):
        assert (data_dir / name).is_file()
    for name in ("settings.json", "wood_defaults.json"):
        assert (config_dir / name).is_file()
    assert store.load_materials()[0]["id"] == "MAT-1"
    assert store.load_settings()["profile"] == "20X20"

    _assert_unchanged(legacy_materials, before_materials)
    _assert_unchanged(legacy_settings, before_settings)


def test_kalkulacja_direct_data_dir_override_remains_supported(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from Komponenty.kalkulacja import store

    monkeypatch.setattr(store, "_DATA_DIR", tmp_path)
    store.save_materials([{"id": "TEMP"}])
    store.save_settings({"profile": "TEMP"})

    assert (tmp_path / "materials.json").is_file()
    assert (tmp_path / "settings.json").is_file()
    assert store.load_materials()[0]["id"] == "TEMP"


def test_prompt_store_and_context_import_write_only_to_local_appdata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(tmp_path / "local"))

    from Komponenty.bazapromptow import storage as st

    legacy_prompts = st._PROMPTS.legacy_path
    assert legacy_prompts is not None
    before_prompts = _bytes(legacy_prompts)

    prompt = st.PromptEntry(id="p1", label="Stage 1E", text="Prompt")
    st.save_prompts(st.PromptStore(prompts=[prompt]))
    source = tmp_path / "source.png"
    source.write_bytes(b"image")
    rel = st.import_context_image("p1", source)

    expected = tmp_path / "local" / "data" / "Komponenty" / "bazapromptow" / "data"
    assert st._PROMPTS.write_path == expected / "prompts.json"
    assert (expected / rel).is_file()
    assert st.context_image_path(rel) == expected / rel
    assert st.load_prompts().prompts[0].label == "Stage 1E"
    _assert_unchanged(legacy_prompts, before_prompts)


def test_prompt_legacy_attachment_is_readable_but_never_deleted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(tmp_path / "local"))

    from Komponenty.bazapromptow import storage as st

    legacy_root = tmp_path / "legacy-data"
    legacy_image = legacy_root / "context_images" / "p1" / "legacy.png"
    legacy_image.parent.mkdir(parents=True)
    legacy_image.write_bytes(b"legacy")

    monkeypatch.setattr(st, "_LEGACY_DATA_DIR", legacy_root)
    monkeypatch.setattr(st, "DATA_DIR", legacy_root)
    monkeypatch.setattr(st, "_DEFAULT_CONTEXT_IMAGES_DIR", legacy_root / "context_images")
    monkeypatch.setattr(st, "_DEFAULT_CONTEXT_FILES_DIR", legacy_root / "context_files")
    monkeypatch.setattr(st, "_DEFAULT_CONTEXT_VIDEOS_DIR", legacy_root / "context_videos")
    monkeypatch.setattr(st, "CONTEXT_IMAGES_DIR", legacy_root / "context_images")
    monkeypatch.setattr(st, "CONTEXT_FILES_DIR", legacy_root / "context_files")
    monkeypatch.setattr(st, "CONTEXT_VIDEOS_DIR", legacy_root / "context_videos")

    rel = "context_images/p1/legacy.png"
    assert st.context_image_path(rel) == legacy_image
    st.delete_context_image_file(rel)
    assert legacy_image.read_bytes() == b"legacy"

    with pytest.raises(ValueError):
        st.context_image_path("../outside.png")


def test_integracja_gpt_config_is_roaming_and_runtime_data_is_local(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(tmp_path / "local"))
    monkeypatch.setenv("GICLEEAPP_ROAMING_ROOT", str(tmp_path / "roaming"))

    from Komponenty.integracjagpt import config as cfg

    legacy = cfg._CONFIG.legacy_path
    assert legacy is not None
    before = _bytes(legacy)

    cfg.save_config(cfg.GptConfig(branch="stage1e"))

    expected_config = (
        tmp_path
        / "roaming"
        / "config"
        / "Komponenty"
        / "integracjagpt"
        / "data"
        / "gpt_config.json"
    )
    expected_data = tmp_path / "local" / "data" / "Komponenty" / "integracjagpt" / "data"
    assert cfg._CONFIG.write_path == expected_config
    assert cfg._RUNTIME_DATA.write_path.parent == expected_data
    assert cfg.load_config().branch == "stage1e"
    _assert_unchanged(legacy, before)


def test_integracja_gpt_direct_config_file_override_remains_supported(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from Komponenty.integracjagpt import config as cfg

    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path)
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "gpt_config.json")
    cfg.save_config(cfg.GptConfig(branch="override"))

    assert (tmp_path / "gpt_config.json").is_file()
    assert cfg.load_config().branch == "override"
