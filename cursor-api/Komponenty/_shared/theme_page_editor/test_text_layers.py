from __future__ import annotations

import json
from pathlib import Path

from .config import PageEditorConfig
from .text_code_importer import adapt_code
from .text_layers import (
    effective_device_layout,
    load_document,
    new_layer,
    normalize_document,
    save_document,
    set_section_layers,
    shared_variant_path,
    validate_document,
)
from .text_layers_export import (
    asset_basename_for_template,
    export_document,
    payload_bytes,
)
from .variants import duplicate_variant


def _config(tmp_path: Path) -> PageEditorConfig:
    return PageEditorConfig(
        component_id="test-page",
        component_dir=tmp_path,
        app_title="Test",
        intro_title="Test",
        intro_body="Test",
        template_rel="templates/page.test.json",
        preview_path="/pages/test",
        variant_id_prefix="test",
        zones=(),
    )


def test_normalization_keeps_stable_ids_order_and_clamps_pin() -> None:
    first = new_layer(name="Pierwsza", layer_id="text_stable_first")
    second = new_layer(name="Druga", layer_id="text_stable_second")
    first["order"] = 9
    second["order"] = 1
    first["pin"]["desktop"]["durationVh"] = 5000

    document = normalize_document(
        {"schemaVersion": 0, "sections": {"hero": [first, second]}}
    )

    rows = document["sections"]["hero"]
    assert [row["id"] for row in rows] == [
        "text_stable_second",
        "text_stable_first",
    ]
    assert [row["order"] for row in rows] == [0, 1]
    assert rows[1]["pin"]["desktop"]["durationVh"] == 1000


def test_breakpoint_layout_inherits_nearest_override() -> None:
    layer = new_layer(layer_id="text_inheritance")
    layer["layout"]["desktop"]["align"] = "left"
    layer["layout"]["tablet"] = dict(layer["layout"]["desktop"])
    layer["layout"]["tablet"]["align"] = "center"
    layer["layout"]["mobile"] = None

    assert effective_device_layout(layer, "desktop")["align"] == "left"
    assert effective_device_layout(layer, "tablet")["align"] == "center"
    assert effective_device_layout(layer, "mobile")["align"] == "center"


def test_explicit_order_change_is_preserved() -> None:
    first = new_layer(name="Pierwsza", layer_id="text_order_first")
    second = new_layer(name="Druga", layer_id="text_order_second")
    first["order"] = 0
    second["order"] = 1
    document = {"sections": {"hero": [first, second]}}
    moved = [second, first]
    for index, layer in enumerate(moved):
        layer["order"] = index

    result = set_section_layers(document, "hero", moved)

    assert [layer["id"] for layer in result["sections"]["hero"]] == [
        "text_order_second",
        "text_order_first",
    ]


def test_sidecar_save_is_atomic_compatible_and_missing_file_is_empty(
    tmp_path: Path,
) -> None:
    path = tmp_path / "variant" / "text-layers.json"
    assert load_document(path)["sections"] == {}
    layer = new_layer(layer_id="text_saved_layer")
    layer["content"]["text"] = "Treść"

    saved = save_document(path, {"sections": {"hero": [layer]}})

    assert load_document(path) == saved
    assert not path.with_suffix(path.suffix + ".tmp").exists()


def test_duplicate_variant_copies_text_layers_sidecar(tmp_path: Path) -> None:
    config = _config(tmp_path)
    source_dir = tmp_path / "data" / "variants" / "test1"
    source_dir.mkdir(parents=True)
    (source_dir / "page.test.json").write_text(
        json.dumps({"sections": {}, "order": []}),
        encoding="utf-8",
    )
    source = shared_variant_path(config, "test1")
    layer = new_layer(layer_id="text_copied_layer")
    layer["content"]["text"] = "Kopiuj mnie"
    save_document(source, {"sections": {"hero": [layer]}})

    duplicate_variant(config, "test1", "test2", label="Kopia")

    copied = load_document(shared_variant_path(config, "test2"))
    assert copied["sections"]["hero"][0]["id"] == "text_copied_layer"
    assert copied["sections"]["hero"][0]["content"]["text"] == "Kopiuj mnie"


def test_validation_preserves_orphans_and_warns_about_multiple_h1() -> None:
    one = new_layer(name="H1 A", layer_id="text_heading_one")
    two = new_layer(name="H1 B", layer_id="text_heading_two")
    for layer in (one, two):
        layer["content"]["kind"] = "h1"
        layer["content"]["text"] = layer["name"]
    document = {"sections": {"missing-section": [one, two]}}

    issues = validate_document(document, known_section_keys=("hero",))

    assert "missing-section" in normalize_document(document)["sections"]
    assert any("której nie ma" in issue["message"] for issue in issues)
    assert any("warstwy H1" in issue["message"] for issue in issues)


def test_code_importer_removes_script_events_urls_and_scopes_css() -> None:
    result = adapt_code(
        """
        <link href="https://fonts.googleapis.com/css2?family=Manrope" rel="stylesheet">
        <div onclick="steal()" style="position:fixed">
          <a href="javascript:steal()">Tekst</a>
          <script>window.bad = true</script>
        </div>
        <style>
          @import url("https://evil.example/x.css");
          body, .copy { color: white; background:url(https://evil.example/x); }
          .safe { opacity: 0; transform: translateY(20px); position: fixed; }
          .safe.is-visible { opacity: 1; }
        </style>
        """,
        layer_id="text_safe_layer",
    )

    combined = result["html"] + result["scopedCss"]
    assert "<script" not in combined
    assert "onclick" not in combined
    assert "javascript:" not in combined
    assert "@import" not in combined
    assert "url(" not in combined
    assert "position: fixed" not in combined
    assert '[data-giclee-text-layer-id="text_safe_layer"]' in result["scopedCss"]
    assert '[data-giclee-text-layer-id="text_safe_layer"].is-entered' in (
        result["scopedCss"]
    )
    assert result["fontUrls"] == [
        "https://fonts.googleapis.com/css2?family=Manrope"
    ]
    assert result["suggestedEnterPreset"] == "none"
    assert any(".is-visible" in line for line in result["report"])
    assert result["componentMode"] is True
    assert result["ownsMotion"] is True


def test_full_component_keeps_decorations_svg_ids_keyframes_and_observer() -> None:
    result = adapt_code(
        """
        <section id="museum" class="museum" data-museum>
          <svg viewBox="0 0 20 20" aria-hidden="true">
            <defs>
              <linearGradient id="gold"><stop offset="0" stop-color="#fff"></stop></linearGradient>
            </defs>
            <circle cx="10" cy="10" r="8" fill="url(#gold)"></circle>
            <circle cx="2" cy="2" r="1" stroke="url(https://evil.example/paint)"></circle>
          </svg>
          <div class="rail" style="position:absolute;inset:0">01</div>
          <p class="copy">Treść</p>
        </section>
        <style>
          @keyframes glow { from { opacity: 0; } to { opacity: 1; } }
          #museum { position: absolute; animation: glow 1s ease; }
          .museum::before { content: "I"; }
          .museum.is-visible .rail { transform: scaleY(1); }
          @media (max-width: 749px) { .museum { inset: 10px; } }
        </style>
        <script>
          const observer = new IntersectionObserver(() => {}, {
            threshold: 0.28,
            rootMargin: "0px 0px -7% 0px"
          });
          observer.unobserve(document.body);
        </script>
        """,
        layer_id="text_museum",
    )

    assert 'id="text_museum--museum"' in result["html"]
    assert 'data-museum=""' in result["html"]
    assert "<svg" in result["html"]
    assert "<circle" in result["html"]
    assert 'id="text_museum--gold"' in result["html"]
    assert 'fill="url(#text_museum--gold)"' in result["html"]
    assert "evil.example" not in result["html"]
    assert "text_museum--kf--glow" in result["scopedCss"]
    assert "#text_museum--museum" in result["scopedCss"]
    assert ".museum::before" in result["scopedCss"]
    assert "@media (max-width: 749px)" in result["scopedCss"]
    assert ".is-entered" in result["scopedCss"]
    assert result["behavior"] == {
        "trigger": "intersection",
        "threshold": 0.28,
        "rootMargin": "0px 0px -7% 0px",
        "once": True,
    }


def test_export_contains_only_enabled_layers_and_template_specific_asset() -> None:
    enabled = new_layer(layer_id="text_enabled")
    disabled = new_layer(layer_id="text_disabled")
    enabled["content"]["text"] = "Widoczny"
    disabled["enabled"] = False
    payload = export_document(
        {"sections": {"hero": [enabled, disabled]}},
        page="page-test",
        variant_id="test1",
    )

    assert [row["id"] for row in payload["sections"]["hero"]] == [
        "text_enabled"
    ]
    assert asset_basename_for_template("templates/page.test.json") == (
        "giclee-text-layers-page-test.js"
    )
    assert payload_bytes(payload).startswith(
        b"window.GICLEE_TEXT_LAYERS = "
    )


def test_all_three_editor_surfaces_use_the_shared_add_text_module() -> None:
    root = Path(__file__).resolve().parents[4]
    common = (
        root
        / "cursor-api"
        / "Komponenty"
        / "_shared"
        / "theme_page_editor"
        / "gui_shell.py"
    ).read_text(encoding="utf-8")
    home = (
        root / "cursor-api" / "Komponenty" / "stronaglowna" / "gui.py"
    ).read_text(encoding="utf-8")
    frame = (
        root
        / "cursor-api"
        / "giclee_app"
        / "ui"
        / "gicleeframe_view_section_list_shell.py"
    ).read_text(encoding="utf-8")

    assert "build_text_layers_panel(" in common
    assert "build_text_layers_panel(" in home
    assert "open_persistent_text_layer_editor" in frame
    assert 'text="Dodaj tekst…"' in common
    assert 'text="Dodaj tekst…"' in home
    assert 'text="Dodaj tekst…"' in frame
