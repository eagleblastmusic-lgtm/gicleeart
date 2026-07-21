from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SECTION = ROOT / "sections" / "giclee-editorial-faq.liquid"
CSS = ROOT / "assets" / "giclee-editorial-faq.css"
JS = ROOT / "assets" / "giclee-editorial-faq.js"
TEMPLATE = ROOT / "templates" / "page.faq.json"
VARIANT = ROOT / "cursor-api" / "Komponenty" / "faq" / "data" / "variants" / "fq1" / "page.faq.json"
REGISTRY = ROOT / "cursor-api" / "Komponenty" / "faq" / "registry.py"


def load_template(path: Path) -> dict:
    source = path.read_text(encoding="utf-8")
    source = re.sub(r"^/\*.*?\*/\s*", "", source, flags=re.DOTALL)
    return json.loads(source)


def editorial_section(path: Path) -> dict:
    return load_template(path)["sections"]["section_9YgpHf"]


def test_faq_template_uses_isolated_editorial_section() -> None:
    section = editorial_section(TEMPLATE)
    assert section["type"] == "giclee-editorial-faq"
    assert section["block_order"] == list(section["blocks"])
    assert len(section["blocks"]) == 5
    assert all(block["type"] == "faq_item" for block in section["blocks"].values())
    assert "accordion_3BVjAx" not in TEMPLATE.read_text(encoding="utf-8")


def test_live_template_and_app_variant_share_the_same_faq_contract() -> None:
    assert editorial_section(TEMPLATE) == editorial_section(VARIANT)


def test_all_existing_questions_answers_and_order_are_preserved() -> None:
    blocks = editorial_section(TEMPLATE)["blocks"]
    questions = [block["settings"]["question"] for block in blocks.values()]
    assert questions == [
        "Jaki jest czas realizacji zamówienia?",
        "Jaki jest czas wysyłki?",
        "Czy jest możliwość kontaktu telefonicznego?",
        "Gdzie są produkowane wasze produkty?",
        "Ile kosztuje wysyłka?",
    ]
    answers = [block["settings"]["answer"] for block in blocks.values()]
    assert answers == [
        "<p>Czas realizacji zamówienia wynosi od 3 do 7 dni. Jest to związane z czasem dostawy drewna oraz materiałów potrzebnych do produkcji. Staram się zawsze trzymać minimalne zapasy drewna jednak przed wykończeniem, które impregnuje, drewno jest podatne na paczenie. Dlatego produkty od początku do końca realizuję z materiałów dostarczonych na świeżo.</p><p>Proces produkcji składa się z wielu różnych etapów, od cięcia drewna, przez nakładanie różnych warstw wykończenia, które schną dlatego trzeba liczyć 1 dzień cięcie i malowanie podkładem, 2 dzień olejowanie i drukowanie, kolejne 3 dni wstępnego schnięcia i utwardzania olejowosku, a także schnięcie papieru po zastosowaniu sprayu ochronnego</p>",
        "<p>Po ukończeniu produktu obraz jest bezzwłocznie pakowany oraz wysyłany bez względu na porę dnia i nocy przez paczkomat. Po wysłaniu zamówienia otrzymasz e-mail z dalszymi informacjami. Przesyłki z reguły dochodzą w 1-2 dni roboczych</p>",
        "<p>Niestety nie ma. Działalność prowadzę sam i nie jestem w stanie podczas pracy w ciągu dnia odbierać telefonów. Proszę o kontakt emailowy. Zazwyczaj wieczorem albo w nocy odpisuję.</p>",
        "<p>Moja pracownia mieści się w Pucku woj. Pomorskie, jednak brak możliwości jest odbiorów osobistych</p>",
        "<p>Wysyłka jest całkowicie darmowa</p>",
    ]


def test_section_has_no_js_fallback_and_accessible_controls() -> None:
    source = SECTION.read_text(encoding="utf-8")
    assert "<details" in source
    assert "<summary" in source
    assert "aria-controls" in source
    assert "aria-labelledby" in source
    assert "aria-expanded" not in source
    assert "data-faq-answer" in source
    assert "{{ block.settings.answer }}" in source
    assert "CTA" not in source


def test_runtime_covers_hash_history_morphing_reduced_motion_and_cleanup() -> None:
    source = JS.read_text(encoding="utf-8")
    for contract in [
        "normalizeAnchors()",
        "window.history.pushState",
        "hashchange",
        "popstate",
        "morphQuestion",
        "aria-hidden",
        "shopify:block:select",
        "shopify:section:unload",
        "ResizeObserver",
        "AbortController",
        "restoreMovedAnswer",
        "removeMorphClone",
        "closeActiveItem",
        "previousPanelHeight",
        "prefers-reduced-motion",
    ]:
        assert contract in source
    assert "pointermove" not in source
    assert "setInterval" not in source


def test_styles_are_editorial_not_dashboard_or_glass() -> None:
    source = CSS.read_text(encoding="utf-8")
    assert "grid-template-columns" in source
    assert "giclee-editorial-faq__panel-line" in source
    assert "prefers-reduced-motion" in source
    assert "backdrop-filter" not in source
    assert "box-shadow" not in source
    assert "border-radius: 16px" not in source


def test_registry_points_to_direct_faq_item_blocks() -> None:
    source = REGISTRY.read_text(encoding="utf-8")
    assert 'zone_id="faq_archive"' in source
    assert '"faq_mUQFCU", "settings", "question"' in source
    assert '"faq_7nCpLH", "settings", "answer"' in source
    assert "accordion_3BVjAx" not in source


def test_section_schema_is_valid_json_and_minimal() -> None:
    source = SECTION.read_text(encoding="utf-8")
    schema = source.split("{% schema %}", 1)[1].split("{% endschema %}", 1)[0]
    parsed = json.loads(schema)
    assert parsed["max_blocks"] == 30
    assert [setting["id"] for setting in parsed["blocks"][0]["settings"]] == [
        "question",
        "answer",
        "anchor",
    ]
    assert not any(setting.get("id") in {"duration", "blur", "offset", "flip"} for setting in parsed["settings"])


def test_runtime_avoids_continuous_or_pointer_driven_animation_work() -> None:
    source = JS.read_text(encoding="utf-8")
    forbidden = ["pointermove", "mousemove", "setInterval", "WebGL", "canvas", "gsap"]
    assert all(token not in source for token in forbidden)
    assert source.count("requestAnimationFrame") <= 5


def test_faq_markup_contains_no_marketing_actions() -> None:
    source = SECTION.read_text(encoding="utf-8").lower()
    for phrase in ["napisz do nas", "skontaktuj się", "dowiedz się więcej", "product_url", "button--primary"]:
        assert phrase not in source
