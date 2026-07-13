from __future__ import annotations

import json
from pathlib import Path

import pytest

from Komponenty.tytulyai import storage as st
from Komponenty.tytulyai.batch import BatchItemResult
from Komponenty.tytulyai.descriptions import DescriptionVariant, ProductDescriptionDrafts
from tools.repository_safety.runtime_writes import scan_python_source


def test_title_draft_store_resolves_current_monkeypatched_constant(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    override = tmp_path / "override" / "title_drafts.json"
    monkeypatch.setattr(st, "TITLE_DRAFTS_FILE", override)

    st.save_title_drafts(
        {
            31: BatchItemResult(
                product_id=31,
                artist="Monet",
                painting_title="Impresja",
                generated_at="2026-07-13",
            )
        }
    )

    assert json.loads(override.read_text(encoding="utf-8"))["drafts"]["31"][
        "painting_title"
    ] == "Impresja"
    assert st.load_title_drafts()[31].artist == "Monet"
    assert not list(override.parent.glob(f".{override.name}.*.tmp"))


def test_description_draft_store_resolves_current_monkeypatched_constant(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    override = tmp_path / "override" / "description_drafts.json"
    monkeypatch.setattr(st, "DESCRIPTION_DRAFTS_FILE", override)

    st.save_description_drafts(
        {
            44: ProductDescriptionDrafts(
                product_id=44,
                artist="Canaletto",
                painting_title="Wenecja",
                v1=DescriptionVariant(akapity=["A1", "A2"]),
            )
        }
    )

    loaded = st.load_description_drafts()
    assert loaded[44].painting_title == "Wenecja"
    assert loaded[44].v1.akapity == ["A1", "A2"]
    assert not list(override.parent.glob(f".{override.name}.*.tmp"))


def test_draft_store_rejects_unknown_constant_name() -> None:
    with pytest.raises(ValueError, match="Unsafe Tytuly AI draft file constant"):
        st._resolved_draft_path_for_constant("../drafts.json", for_write=True)


def test_runtime_write_inventory_no_longer_flags_tytulyai_draft_helpers() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    relative = "Komponenty/tytulyai/storage.py"
    source_path = repo_root / relative

    findings, error = scan_python_source(
        relative,
        source_path.read_text(encoding="utf-8"),
    )

    assert error == ""
    assert findings == []
