"""Test wykluczajacej flagi domyslnego szablonu."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Komponenty.dodajobraz.templates import (  # noqa: E402
    VariantTemplate,
    apply_default_flag,
    save_templates,
)


def test_apply_default_flag_true_clears_others() -> None:
    a = VariantTemplate.new(name="A", is_default=True)
    b = VariantTemplate.new(name="B", is_default=False)
    templates = [a, b]
    apply_default_flag(templates, b.id, is_default=True)
    assert a.is_default is False
    assert b.is_default is True


def test_apply_default_flag_false_only_touches_one() -> None:
    a = VariantTemplate.new(name="A", is_default=True)
    b = VariantTemplate.new(name="B", is_default=False)
    templates = [a, b]
    apply_default_flag(templates, a.id, is_default=False)
    assert a.is_default is False
    assert b.is_default is False


def test_save_templates_normalizes_two_trues(tmp_path, monkeypatch) -> None:
    """Regresja: przy dwoch True zostaje pierwszy (kolejnosc listy) — nie ruszac data/ usera."""
    import Komponenty.dodajobraz.templates as vt

    monkeypatch.setattr(vt, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(vt, "_TEMPLATES_FILE", tmp_path / "variant_templates.json")
    a = VariantTemplate.new(name="A", is_default=True)
    b = VariantTemplate.new(name="B", is_default=True)
    save_templates([a, b])
    assert a.is_default is True
    assert b.is_default is False
