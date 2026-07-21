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


def test_pdp_v3_trust_layer_masks_process_only_in_covering_state() -> None:
    source = TRUST_SNIPPET.read_text(encoding="utf-8")
    selector = (
        "main[data-template='product.szablon-produktu-v3']\n"
        "    .pdp-v3-pt-wrap.has-bg\n"
        "    .giclee-trust.is-covering-process::before"
    )

    assert selector in source
    assert "var(--pdp-v3-pt-image);" in source
    assert "background-attachment: fixed;" in source
    assert "background-size: cover;" in source
    assert "linear-gradient(rgb(0 0 0 / 0.45)" in source
    assert "filter: blur(var(--pdp-v3-pt-blur, 0px))" in source
    assert "transform: translateX(-50%) scale(1.03);" in source
    assert ".giclee-trust::before {" not in source


def test_pdp_v3_trust_cover_state_is_reversible() -> None:
    source = PROCESS_SCRIPT.read_text(encoding="utf-8")

    assert "var covering = entry.isIntersecting && entry.intersectionRatio >= 0.18;" in source
    assert "section.classList.toggle('is-covering-process', covering);" in source
    assert "threshold: [0, 0.18]" in source
    assert "trustObserver.unobserve" not in source
