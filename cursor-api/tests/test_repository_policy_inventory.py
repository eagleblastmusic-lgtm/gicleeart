from __future__ import annotations

from tools.repository_safety.policy import DataClass, classify_path


def test_verified_project_paths_are_explicit_source() -> None:
    paths = (
        ".graphqlrc.js",
        ".vscode/extensions.json",
        ".vscode/mcp.json",
        "Produkcja - serwer web.cmd",
        "SHOP_KNOWLEDGE.md",
        "workers/__init__.py",
        "workers/bridge_runner.py",
    )

    for path in paths:
        decision = classify_path(path)
        assert decision.classification is DataClass.SOURCE, path
        assert decision.tracked_allowed, path
        assert decision.sync_allowed, path


def test_generated_artifacts_win_over_broad_cache_and_backup_patterns() -> None:
    paths = (
        ".pytest_cache/v/cache/nodeids",
        "node_modules/.cache/wrangler/state.json",
        "Komponenty/stronaglowna/data/backups/.gitkeep",
        "Komponenty/print_optimize/data/ww_pairs/_smoke/index.json",
        "Komponenty/stronaglowna/data/tmp/clip.mp4",
        ".shopify/dev-bundle/manifest.json",
        "_dup_result.txt",
    )

    for path in paths:
        decision = classify_path(path)
        assert decision.classification is DataClass.GENERATED, path
        assert not decision.tracked_allowed, path
        assert not decision.sync_allowed, path
        assert decision.migration_bucket is None, path


def test_document_sales_exports_are_private_migration_data() -> None:
    decision = classify_path(
        "Komponenty/dokumentysprzedazy/dane/exports/sales_2026_06.csv"
    )

    assert decision.classification is DataClass.PRIVATE
    assert not decision.tracked_allowed
    assert not decision.sync_allowed
    assert decision.migration_bucket == "data"


def test_local_authored_and_accounting_data_are_private() -> None:
    paths = (
        "Komponenty/bazapromptow/data/prompts.json",
        "Komponenty/bazapromptow/data/context_images/abc/image.png",
        "Komponenty/blog/data/topics.json",
        "Komponenty/dokumentysprzedazy/dane/invoice_events.jsonl",
        "Komponenty/dnr/dane/dnr.json",
        "Komponenty/kalkulacja/data/materials.json",
        "Komponenty/kalkulacja/data/helpers.json",
        "Komponenty/kalkulacja/data/price_table.json",
        "Komponenty/kalkulacja/data/cost_lines.json",
        "Komponenty/kalkulacja/data/sales_mix.json",
        "Komponenty/kpir/dane/kpir.json",
        "Komponenty/planer/dane/2026-07-11.json",
        "Komponenty/poczta/data/processed_client_orders.json",
        "Komponenty/segregatorplikow/data/tiles.json",
        "Komponenty/socialmedia/data/cykl/Obrazy/artist/title/main.jpg",
        "Komponenty/tytulyai/data/title_drafts.json",
        "Komponenty/zadania/data/tasks.json",
    )

    for path in paths:
        decision = classify_path(path)
        assert decision.classification is DataClass.PRIVATE, path
        assert not decision.tracked_allowed, path
        assert not decision.sync_allowed, path
        assert decision.migration_bucket == "data", path


def test_mutable_component_configuration_is_not_source() -> None:
    paths = (
        "Komponenty/dnr/dane/dnr_settings.json",
        "Komponenty/dodajobraz/data/variant_templates.json",
        "Komponenty/kalkulacja/data/settings.json",
        "Komponenty/kalkulacja/data/wood_defaults.json",
        "Komponenty/karuzela/settings.json",
        "Komponenty/produkcja/dane/package_templates.json",
        "Komponenty/socialmedia/data/cykl/config.json",
        "Komponenty/stronyzobrazami/data/settings.json",
        "giclee_app/data/launcher_shortcuts.json",
        "giclee_app/data/studio_categories.json",
    )

    for path in paths:
        decision = classify_path(path)
        assert decision.classification is DataClass.RUNTIME, path
        assert not decision.tracked_allowed, path
        assert not decision.sync_allowed, path
        assert decision.migration_bucket == "config", path


def test_mutable_workflow_state_and_performance_reports_are_not_source() -> None:
    data_paths = (
        "Komponenty/_shared/data/recent_images.json",
        "Komponenty/dodajobraz/data/description_update_marks.json",
        "Komponenty/dodajobraz/data/zoom_upload_history.json",
        "Komponenty/socialmedia/data/cykl/generation_state.json",
        "Komponenty/socialmedia/data/cykl/queue.json",
        "Komponenty/stronydozycia/data/pages.json",
        "Komponenty/stronyzobrazami/data/sites.json",
    )
    log_paths = (
        "_push_live.log",
        "reports/performance/20260707-153837_giclee_studio/report.md",
        "reports/performance/20260707-153837_giclee_studio/events.jsonl",
    )

    for path in data_paths:
        decision = classify_path(path)
        assert decision.classification is DataClass.RUNTIME, path
        assert decision.migration_bucket == "data", path
        assert not decision.tracked_allowed, path
        assert not decision.sync_allowed, path

    for path in log_paths:
        decision = classify_path(path)
        assert decision.classification is DataClass.RUNTIME, path
        assert decision.migration_bucket == "logs", path
        assert not decision.tracked_allowed, path
        assert not decision.sync_allowed, path


def test_regenerable_shopify_cache_is_not_source() -> None:
    decision = classify_path("Komponenty/karuzela/data/collection_quotes.json")

    assert decision.classification is DataClass.CACHE
    assert decision.migration_bucket == "data"
    assert not decision.tracked_allowed
    assert not decision.sync_allowed


def test_known_static_assets_and_definitions_remain_source() -> None:
    paths = (
        "Komponenty/mockup/data/templates.json",
        "Komponenty/print_optimize/data/test_photos/README.txt",
        "Komponenty/wybortrybu/data/work_modes.json",
        "Komponenty/wybortrybu/data/combinations.json",
    )

    for path in paths:
        decision = classify_path(path)
        assert decision.classification is DataClass.SOURCE, path
        assert decision.tracked_allowed, path
        assert decision.sync_allowed, path
