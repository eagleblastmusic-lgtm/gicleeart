from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def test_component_card_shell_exists() -> None:
    path = ROOT / "giclee_app" / "ui" / "widgets.py"
    text = path.read_text(encoding="utf-8")

    assert "class ComponentCardShell" in text


def test_component_hub_uses_shell_before_full_card() -> None:
    path = ROOT / "giclee_app" / "ui" / "component_hub.py"
    text = path.read_text(encoding="utf-8")

    assert "ComponentCardShell" in text
    assert "_hydrate_queue" in text
    assert "_create_shell_for_component" in text


def test_component_hub_has_hydration_logs() -> None:
    path = ROOT / "giclee_app" / "ui" / "component_hub.py"
    text = path.read_text(encoding="utf-8")

    assert "hub.card.shell_created" in text
    assert "hub.card.hydrate" in text


def test_component_shell_clicks_before_hydration() -> None:
    path = ROOT / "giclee_app" / "ui" / "widgets.py"
    text = path.read_text(encoding="utf-8")

    shell_block = text.split("class ComponentCardShell", 1)[1].split("\nclass ", 1)[0]
    assert "_on_click" in shell_block
    assert "bind" in shell_block


def test_component_shell_uses_stable_height_and_no_loading_copy() -> None:
    path = ROOT / "giclee_app" / "ui" / "widgets.py"
    text = path.read_text(encoding="utf-8")

    assert "_CARD_STABLE_HEIGHT" in text
    assert "Ładowanie…" not in text
    assert "Gotowe" in text


def test_component_shell_has_hydration_request_callback() -> None:
    path = ROOT / "giclee_app" / "ui" / "widgets.py"
    text = path.read_text(encoding="utf-8")

    block = text.split("class ComponentCardShell", 1)[1]
    assert "on_request_hydration" in block
    assert "_handle_enter" in block
    assert "_bind_shell_target" in block


def test_component_shell_does_not_destroy_status_on_hydration() -> None:
    path = ROOT / "giclee_app" / "ui" / "widgets.py"
    text = path.read_text(encoding="utf-8")

    block = text.split("def hydrate_stage_3", 1)[1].split("\n    def ", 1)[0]
    assert ".destroy()" not in block
    assert "configure" in block


def test_component_card_lazy_no_writer_or_shopify_sync() -> None:
    paths = [
        ROOT / "giclee_app" / "ui" / "widgets.py",
        ROOT / "giclee_app" / "ui" / "component_hub.py",
    ]

    forbidden = [
        "write_text(",
        "deploy(",
        "Shopify API",
    ]

    for path in paths:
        text = path.read_text(encoding="utf-8")
        for item in forbidden:
            assert item not in text
