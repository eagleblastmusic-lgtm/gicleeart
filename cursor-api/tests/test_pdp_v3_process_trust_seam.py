from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TRUST_CSS = ROOT / "assets" / "giclee-product-trust.css"
TRUST_SNIPPET = ROOT / "snippets" / "giclee-product-trust.liquid"


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


def test_pdp_v3_without_before_after_has_no_phantom_separator_rows() -> None:
    source = TRUST_SNIPPET.read_text(encoding="utf-8")

    assert ".giclee-before-after-target:empty" in source
    assert "display: none;" in source
    assert "+ .pdp-v3-pt-wrap" in source
    assert "margin-top: calc(-1 * var(--gap, 48px));" in source
    assert "clip-path: inset(0);" in source
    assert "scaleX(1.03)" in source
    assert "top: 0;" in source
    assert "background: rgb(0 0 0 / 0.45);" in source
