from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from giclee_app.app_paths import cache_path, config_path, data_path


def _set_roots(monkeypatch, tmp_path: Path) -> tuple[Path, Path]:
    local = tmp_path / "local"
    roaming = tmp_path / "roaming"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local))
    monkeypatch.setenv("GICLEEAPP_ROAMING_ROOT", str(roaming))
    return local, roaming


def test_planer_reads_legacy_and_writes_external(monkeypatch, tmp_path: Path) -> None:
    from Komponenty.planer import view

    local, _ = _set_roots(monkeypatch, tmp_path)
    legacy_dir = tmp_path / "legacy-planer"
    legacy_dir.mkdir()
    legacy_file = legacy_dir / "2026-07-01.json"
    legacy_file.write_text(json.dumps({"tasks": [{"id": "a", "text": "legacy"}]}), encoding="utf-8")

    monkeypatch.setattr(view, "_LEGACY_DATA_DIR", legacy_dir)
    monkeypatch.setattr(view, "_DATA_DIR", legacy_dir)
    monkeypatch.setattr(view, "_DATA_ROOT", data_path("Komponenty/planer/dane/.path", legacy=legacy_dir / ".path"))

    assert view._load_tasks(date(2026, 7, 1))[0]["text"] == "legacy"
    before = legacy_file.read_bytes()
    view._save_tasks(date(2026, 7, 1), [{"id": "b", "text": "external"}])

    target = local / "data/Komponenty/planer/dane/2026-07-01.json"
    assert json.loads(target.read_text(encoding="utf-8"))["tasks"][0]["text"] == "external"
    assert legacy_file.read_bytes() == before


def test_tasks_reminders_and_cache_write_external(monkeypatch, tmp_path: Path) -> None:
    from Komponenty.zadania import storage

    local, _ = _set_roots(monkeypatch, tmp_path)
    legacy = tmp_path / "legacy-zadania"
    legacy.mkdir()
    tasks_file = legacy / "tasks.json"
    signals_file = legacy / "signals_cache.json"
    reminders_file = legacy / "reminders.json"
    tasks_file.write_text('{"tasks": []}', encoding="utf-8")

    monkeypatch.setattr(storage, "_LEGACY_DATA_DIR", legacy)
    monkeypatch.setattr(storage, "_DATA_DIR", legacy)
    monkeypatch.setattr(storage, "_TASKS_FILE", tasks_file)
    monkeypatch.setattr(storage, "_SIGNALS_FILE", signals_file)
    monkeypatch.setattr(storage, "_REMINDERS_FILE", reminders_file)
    monkeypatch.setattr(storage, "_TASKS", data_path("Komponenty/zadania/data/tasks.json", legacy=tasks_file))
    monkeypatch.setattr(storage, "_SIGNALS", cache_path("Komponenty/zadania/data/signals_cache.json", legacy=signals_file))
    monkeypatch.setattr(storage, "_REMINDERS", data_path("Komponenty/zadania/data/reminders.json", legacy=reminders_file))

    task = storage.Task.new(title="Test")
    storage.save_tasks([task])
    storage.save_signals_cache({"orders": 1})
    storage.save_reminders({"monthly": "2026-07"})

    assert (local / "data/Komponenty/zadania/data/tasks.json").is_file()
    assert (local / "data/Komponenty/zadania/data/signals_cache.json").is_file()
    assert (local / "data/Komponenty/zadania/data/reminders.json").is_file()
    assert tasks_file.read_text(encoding="utf-8") == '{"tasks": []}'


def test_title_drafts_write_external(monkeypatch, tmp_path: Path) -> None:
    import importlib
    import sys
    import types
    from dataclasses import dataclass, field

    batch_module = types.ModuleType("Komponenty.tytulyai.batch")

    @dataclass
    class BatchItemResult:
        product_id: int
        artist: str = ""
        painting_title: str = ""
        model_used: str = ""
        raw_response: str = ""
        cursor_prompt: str = ""
        error: str = ""
        warning: str = ""
        generated_at: str = ""

    descriptions_module = types.ModuleType("Komponenty.tytulyai.descriptions")

    @dataclass
    class DescriptionVariant:
        model_used: str = ""
        akapity: list[str] = field(default_factory=list)
        raw_response: str = ""
        error: str = ""
        generated_at: str = ""

    @dataclass
    class ProductDescriptionDrafts:
        product_id: int
        artist: str = ""
        painting_title: str = ""
        v1: DescriptionVariant = field(default_factory=DescriptionVariant)
        v2: DescriptionVariant = field(default_factory=DescriptionVariant)

    batch_module.BatchItemResult = BatchItemResult
    descriptions_module.DescriptionVariant = DescriptionVariant
    descriptions_module.ProductDescriptionDrafts = ProductDescriptionDrafts
    monkeypatch.setitem(sys.modules, "Komponenty.tytulyai.batch", batch_module)
    monkeypatch.setitem(sys.modules, "Komponenty.tytulyai.descriptions", descriptions_module)
    sys.modules.pop("Komponenty.tytulyai.storage", None)
    storage = importlib.import_module("Komponenty.tytulyai.storage")

    local, _ = _set_roots(monkeypatch, tmp_path)
    legacy = tmp_path / "legacy-titles"
    legacy.mkdir()
    title_file = legacy / "title_drafts.json"
    desc_file = legacy / "description_drafts.json"
    title_file.write_text('{"drafts": {}}', encoding="utf-8")

    monkeypatch.setattr(storage, "_LEGACY_DATA_DIR", legacy)
    monkeypatch.setattr(storage, "_DEFAULT_TITLE_DRAFTS_FILE", title_file)
    monkeypatch.setattr(storage, "_DEFAULT_DESCRIPTION_DRAFTS_FILE", desc_file)
    monkeypatch.setattr(storage, "TITLE_DRAFTS_FILE", title_file)
    monkeypatch.setattr(storage, "DESCRIPTION_DRAFTS_FILE", desc_file)
    monkeypatch.setattr(storage, "_TITLE_DRAFTS", data_path("Komponenty/tytulyai/data/title_drafts.json", legacy=title_file))
    monkeypatch.setattr(storage, "_DESCRIPTION_DRAFTS", data_path("Komponenty/tytulyai/data/description_drafts.json", legacy=desc_file))

    storage.save_title_drafts({1: BatchItemResult(product_id=1, painting_title="Nowy")})
    assert (local / "data/Komponenty/tytulyai/data/title_drafts.json").is_file()
    assert title_file.read_text(encoding="utf-8") == '{"drafts": {}}'


def test_small_component_stores_write_to_manifest_paths(monkeypatch, tmp_path: Path) -> None:
    from Komponenty.karuzela import service as carousel
    from Komponenty.poczta import client_order_processor as mail
    from Komponenty.produkcja import package_templates
    from Komponenty.stronydozycia import storage as life
    from Komponenty.stronyzobrazami import settings as image_settings
    from Komponenty.stronyzobrazami import storage as image_sites

    local, roaming = _set_roots(monkeypatch, tmp_path)

    carousel_legacy = tmp_path / "carousel.json"
    monkeypatch.setattr(carousel, "_LEGACY_SETTINGS_FILE", carousel_legacy)
    monkeypatch.setattr(carousel, "_SETTINGS_FILE", carousel_legacy)
    monkeypatch.setattr(carousel, "_SETTINGS", config_path("Komponenty/karuzela/settings.json", legacy=carousel_legacy))
    carousel.save_settings({"carousel_version": "Karuzela2"})

    mail_legacy_dir = tmp_path / "mail"
    mail_legacy = mail_legacy_dir / "processed_client_orders.json"
    monkeypatch.setattr(mail, "_LEGACY_DATA_DIR", mail_legacy_dir)
    monkeypatch.setattr(mail, "_PROCESSED_FILE", mail_legacy)
    monkeypatch.setattr(mail, "_PROCESSED", data_path("Komponenty/poczta/data/processed_client_orders.json", legacy=mail_legacy))
    mail._save_processed({"uids": ["1"], "orders": {}})

    packages_legacy_dir = tmp_path / "packages"
    packages_legacy = packages_legacy_dir / "package_templates.json"
    monkeypatch.setattr(package_templates, "_LEGACY_DATA_DIR", packages_legacy_dir)
    monkeypatch.setattr(package_templates, "_FILE", packages_legacy)
    monkeypatch.setattr(package_templates, "_TEMPLATES", config_path("Komponenty/produkcja/dane/package_templates.json", legacy=packages_legacy))
    package_templates.save_templates([package_templates.Template(key="DAB M", length_cm=1, width_cm=2, height_cm=3, weight_kg=4)])

    pages_legacy_dir = tmp_path / "pages"
    pages_legacy = pages_legacy_dir / "pages.json"
    monkeypatch.setattr(life, "_LEGACY_DATA_DIR", pages_legacy_dir)
    monkeypatch.setattr(life, "PAGES_FILE", pages_legacy)
    monkeypatch.setattr(life, "_STORE_PATH", data_path("Komponenty/stronydozycia/data/pages.json", legacy=pages_legacy))
    life.save_pages(life.PageStore())

    sites_legacy_dir = tmp_path / "sites"
    sites_legacy = sites_legacy_dir / "sites.json"
    monkeypatch.setattr(image_sites, "_LEGACY_DATA_DIR", sites_legacy_dir)
    monkeypatch.setattr(image_sites, "SITES_FILE", sites_legacy)
    monkeypatch.setattr(image_sites, "_STORE_PATH", data_path("Komponenty/stronyzobrazami/data/sites.json", legacy=sites_legacy))
    image_sites.save_sites(image_sites.SiteStore())

    settings_legacy = tmp_path / "image-settings.json"
    monkeypatch.setattr(image_settings, "_LEGACY_SETTINGS_PATH", settings_legacy)
    monkeypatch.setattr(image_settings, "_SETTINGS_PATH", settings_legacy)
    monkeypatch.setattr(image_settings, "_SETTINGS", config_path("Komponenty/stronyzobrazami/data/settings.json", legacy=settings_legacy))
    image_settings.save_settings(image_settings.ModuleSettings(download_dir="X"))

    assert (roaming / "config/Komponenty/karuzela/settings.json").is_file()
    assert (local / "data/Komponenty/poczta/data/processed_client_orders.json").is_file()
    assert (roaming / "config/Komponenty/produkcja/dane/package_templates.json").is_file()
    assert (local / "data/Komponenty/stronydozycia/data/pages.json").is_file()
    assert (local / "data/Komponenty/stronyzobrazami/data/sites.json").is_file()
    assert (roaming / "config/Komponenty/stronyzobrazami/data/settings.json").is_file()


def test_launcher_config_reads_legacy_and_writes_roaming(monkeypatch, tmp_path: Path) -> None:
    from giclee_app import launcher_layout, launcher_shortcuts
    from giclee_app.studio import categories

    _, roaming = _set_roots(monkeypatch, tmp_path)

    layout_legacy = tmp_path / "launcher_layout.json"
    layout_legacy.write_text('{"entries": {}, "section_order": []}', encoding="utf-8")
    monkeypatch.setattr(launcher_layout, "_LEGACY_LAYOUT_PATH", layout_legacy)
    monkeypatch.setattr(launcher_layout, "_LAYOUT", config_path("giclee_app/data/launcher_layout.json", legacy=layout_legacy))
    assert launcher_layout.load_layout().entries == {}
    launcher_layout.save_layout(launcher_layout.LauncherLayout())

    shortcuts_legacy = tmp_path / "launcher_shortcuts.json"
    shortcuts_legacy.write_text('{"shortcuts": {"a": "planer"}}', encoding="utf-8")
    monkeypatch.setattr(launcher_shortcuts, "_LEGACY_SHORTCUTS_PATH", shortcuts_legacy)
    monkeypatch.setattr(launcher_shortcuts, "_SHORTCUTS", config_path("giclee_app/data/launcher_shortcuts.json", legacy=shortcuts_legacy))
    assert launcher_shortcuts.load_launcher_shortcuts()["a"] == "planer"
    launcher_shortcuts.save_launcher_shortcuts({"b": "zadania"})

    categories_legacy = tmp_path / "studio_categories.json"
    categories_legacy.write_text('{"default_category":"content","categories":{}}', encoding="utf-8")
    monkeypatch.setattr(categories, "_LEGACY_CATEGORIES_PATH", categories_legacy)
    monkeypatch.setattr(categories, "_CATEGORIES_PATH", categories_legacy)
    monkeypatch.setattr(categories, "_CATEGORIES", config_path("giclee_app/data/studio_categories.json", legacy=categories_legacy))
    categories.clear_categories_cache()
    try:
        assert categories.category_for_folder("missing") == "content"
    finally:
        categories.clear_categories_cache()

    assert (roaming / "config/giclee_app/data/launcher_layout.json").is_file()
    assert (roaming / "config/giclee_app/data/launcher_shortcuts.json").is_file()
