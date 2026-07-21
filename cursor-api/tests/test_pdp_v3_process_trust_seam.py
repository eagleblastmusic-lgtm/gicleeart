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


def test_pdp_v3_process_and_trust_share_one_static_viewport() -> None:
    source = TRUST_SNIPPET.read_text(encoding="utf-8")

    assert ".pdp-v3-pt-wrap {" in source
    assert "grid-template-rows: minmax(0, 58fr) minmax(0, 42fr);" in source
    assert "height: 100dvh;" in source
    assert "min-height: 100dvh;" in source
    assert "> .giclee-process" in source
    assert "> .giclee-trust" in source
    assert "position: relative;" in source
    assert "min-height: 0;" in source
    assert "min-height: 200dvh;" not in source
    assert ".pdp-v3-pt-stage" not in source


def test_pdp_v3_static_viewport_is_true_full_bleed() -> None:
    source = TRUST_SNIPPET.read_text(encoding="utf-8")

    assert "grid-column: 1 / -1;" in source
    assert "width: 100vw;" in source
    assert "min-width: 100vw;" in source
    assert "max-width: none;" in source
    assert "margin-left: calc(50% - 50vw);" in source
    assert "clamp(1.25rem, 4vw, 5rem)" in source


def test_pdp_v3_static_section_uses_only_the_wrapper_background() -> None:
    source = TRUST_SNIPPET.read_text(encoding="utf-8")

    assert "var(--pdp-v3-pt-image)" not in source
    assert "background-attachment: fixed" not in source
    assert "is-covering-process" not in source
    assert "--pdp-v3-process-opacity" not in source
    assert "--pdp-v3-trust-opacity" not in source
    assert "background-color: transparent;" in source


def test_pdp_v3_process_script_only_reveals_static_content() -> None:
    source = PROCESS_SCRIPT.read_text(encoding="utf-8")

    assert "IntersectionObserver" in source
    assert "section.classList.add('is-revealed');" in source
    assert "document.createElement('div')" not in source
    assert "requestAnimationFrame" not in source
    assert "data-pdp-v3-pt-scene" not in source
    assert "--pdp-v3-process-opacity" not in source
    assert "--pdp-v3-trust-opacity" not in source
