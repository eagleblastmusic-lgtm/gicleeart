"""Testy przypisan produkt -> szablon wariantow."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from Komponenty.dodajobraz import product_template_assignments as pta
from Komponenty.dodajobraz import templates as variant_templates


@pytest.fixture()
def assignment_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "product_template_assignments.json"
    monkeypatch.setattr(pta, "_ASSIGNMENTS_FILE", path)
    return path


def test_assignments_roundtrip(assignment_file: Path) -> None:
    pta.set_product_template_assignment(101, "tpl_a")
    pta.set_product_template_assignments_batch([102, 103], "tpl_b")
    assert pta.get_assigned_template_id(101) == "tpl_a"
    assert pta.get_assigned_template_id(102) == "tpl_b"
    data = json.loads(assignment_file.read_text(encoding="utf-8"))
    assert data["assignments"]["101"] == "tpl_a"
    pta.clear_product_template_assignment(101)
    assert pta.get_assigned_template_id(101) is None


def test_infer_template_from_variants() -> None:
    template = variant_templates.VariantTemplate.new(
        name="Test",
        options=[{"name": "Rozmiar", "values": ["50x70"], "position": 1}],
        variants=[{"option1": "50x70", "price": "100.00"}],
    )
    inferred = pta.infer_template_id_from_variants(template.variants)
    assert inferred is None
    variant_templates.add_template(template)
    try:
        inferred = pta.infer_template_id_from_variants(template.variants)
        assert inferred == template.id
    finally:
        variant_templates.delete_template(template.id)
