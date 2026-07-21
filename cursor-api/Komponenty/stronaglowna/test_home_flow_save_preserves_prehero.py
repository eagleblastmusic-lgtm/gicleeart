from __future__ import annotations

from pathlib import Path

from Komponenty.stronaglowna import (
    home_features,
    homepage_variants,
    prehero_full_generator,
    section_effects_storage,
    service,
)


ROOT = Path(__file__).resolve().parents[3]
PRODUCTION_SCRUB = ROOT / "assets" / "giclee-home-prehero-scrub.js"


def test_home_flow_save_preserves_complete_prehero_runtime(
    monkeypatch,
    tmp_path: Path,
) -> None:
    theme = tmp_path / "theme"
    assets = theme / "assets"
    snippets = theme / "snippets"
    assets.mkdir(parents=True)
    snippets.mkdir(parents=True)

    for name in prehero_full_generator.FULL_PREHERO_CODE_ASSETS:
        source = ROOT / "assets" / name
        target = assets / name
        if source.is_file():
            target.write_bytes(source.read_bytes())
        else:
            target.write_text(f"/* test placeholder: {name} */\n", encoding="utf-8")

    (assets / "giclee-home-prehero-scrub.mp4").write_bytes(b"test-mp4")
    (snippets / prehero_full_generator.FRAME_MANIFEST_SNIPPET).write_text(
        "window.GICLEE_PREHERO_FRAME_SEQUENCE = {enabled: false, urls: []};\n",
        encoding="utf-8",
    )

    scrub_path = assets / "giclee-home-prehero-scrub.js"
    before = scrub_path.read_bytes()
    assert before == PRODUCTION_SCRUB.read_bytes()

    settings = {
        "current": {
            "prehero_enabled": True,
            "home_flow_scroll_mode": "native-v2",
        }
    }

    monkeypatch.setattr(service, "theme_root", lambda: theme)
    monkeypatch.setattr(service, "load_theme_settings", lambda: settings)
    monkeypatch.setattr(home_features, "theme_root", lambda: theme)
    monkeypatch.setattr(home_features, "mobile_hero_path", lambda: assets / "missing-mobile.webp")
    monkeypatch.setattr(homepage_variants, "active_variant_id", lambda: "home12")
    monkeypatch.setattr(
        section_effects_storage,
        "export_section_effects_config",
        lambda _variant_id: {},
    )

    home_features.write_home_assets(
        {"sections": {}},
        stack_enabled=True,
        scroll_config={},
        final_difference_config={},
        studio_reveal_config={},
        section_bg_effects_config={},
    )

    assert scrub_path.read_bytes() == before

    snippet = (snippets / "giclee-home-stack-critical.liquid").read_text(
        encoding="utf-8"
    )
    assert "GICLEE_PREHERO_CONFIG_BEGIN" in snippet
    assert '"smoothScrollMode": "native-v2"' in snippet
    assert "giclee-home-prehero-frames.js" in snippet
    assert "giclee-home-prehero-scrub.js" in snippet

    source = scrub_path.read_text(encoding="utf-8")
    assert "configNumber('scrubSeekFps', 60, 12, 60)" in source
    assert "Math.round(progress * maxMp4Frame())" in source
    assert "allFramesRendered:" in source
