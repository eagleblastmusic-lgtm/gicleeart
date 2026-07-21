from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TRUST_CSS = ROOT / "assets" / "giclee-product-trust.css"
TRUST_SNIPPET = ROOT / "snippets" / "giclee-product-trust.liquid"
PROCESS_SCRIPT = ROOT / "assets" / "giclee-product-process.js"


def test_pdp_v3_process_trust_overlay_covers_the_transition_gap() -> None:
    source = TRUST_CSS.read_text(encoding="utf-8")
    selector = (
        "main[data-template='product.szablon-produktu-v3'] "
        ".pdp-v3-pt-wrap.has-bg::after"
    )

    assert selector in source
    assert "bottom: 0;" in source
    assert "left: 50%;" in source
    assert "width: 100vw;" in source
    assert "transform: translateX(-50%) scale(1.03);" in source
    assert "pointer-events: none;" in source


def test_pdp_v3_process_and_trust_share_one_sticky_scene() -> None:
    source = TRUST_SNIPPET.read_text(encoding="utf-8")

    assert ".pdp-v3-pt-wrap[data-pdp-v3-pt-scene]" in source
    assert "min-height: 200dvh;" in source
    assert ".pdp-v3-pt-stage" in source
    assert "position: sticky;" in source
    assert "grid-area: 1 / 1;" in source
    assert "opacity: var(--pdp-v3-process-opacity);" in source
    assert "opacity: var(--pdp-v3-trust-opacity);" in source
    assert "background: transparent;" in source


def test_pdp_v3_shared_scene_does_not_duplicate_the_background() -> None:
    source = TRUST_SNIPPET.read_text(encoding="utf-8")

    assert "var(--pdp-v3-pt-image)" not in source
    assert "background-attachment: fixed" not in source
    assert "is-covering-process" not in source
    assert "margin-top: calc(-100dvh" not in source


def test_pdp_v3_scene_progress_is_scroll_driven_without_text_overlap() -> None:
    source = PROCESS_SCRIPT.read_text(encoding="utf-8")

    assert "document.createElement('div')" in source
    assert "stage.className = 'pdp-v3-pt-stage';" in source
    assert "scene.setAttribute('data-pdp-v3-pt-scene', '');" in source
    assert "separator.remove();" in source
    assert "var processExit = rangeProgress(progress, 0.32, 0.48);" in source
    assert "var trustEnter = rangeProgress(progress, 0.52, 0.68);" in source
    assert "--pdp-v3-process-opacity" in source
    assert "--pdp-v3-trust-opacity" in source
    assert "window.requestAnimationFrame(updateScene);" in source
    assert "is-covering-process" not in source
