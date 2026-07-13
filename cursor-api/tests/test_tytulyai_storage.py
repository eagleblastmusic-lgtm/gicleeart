"""Testy trwalego zapisu roboczych tytulow/opisow."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_title_drafts_roundtrip(tmp_path, monkeypatch) -> None:
    from Komponenty.tytulyai.batch import BatchItemResult
    from Komponenty.tytulyai import storage as st

    monkeypatch.setattr(st, "DATA_DIR", tmp_path)
    monkeypatch.setattr(st, "TITLE_DRAFTS_FILE", tmp_path / "title_drafts.json")

    drafts = {
        101: BatchItemResult(
            product_id=101,
            artist="Monet",
            painting_title="Impresja",
            model_used="gemini-3.5-flash",
            raw_response='{"pl":"X"}',
            cursor_prompt="prompt-cursor",
            generated_at="2026-06-18 12:00 UTC",
        ),
    }
    st.save_title_drafts(drafts)
    loaded = st.load_title_drafts()
    assert loaded[101].cursor_prompt == "prompt-cursor"
    assert loaded[101].artist == "Monet"


def test_description_drafts_v1_v2_roundtrip(tmp_path, monkeypatch) -> None:
    from Komponenty.tytulyai.descriptions import DescriptionVariant, ProductDescriptionDrafts
    from Komponenty.tytulyai import storage as st

    monkeypatch.setattr(st, "DATA_DIR", tmp_path)
    monkeypatch.setattr(st, "DESCRIPTION_DRAFTS_FILE", tmp_path / "description_drafts.json")

    drafts = {
        55: ProductDescriptionDrafts(
            product_id=55,
            artist="Canaletto",
            painting_title="Wenecja",
            v1=DescriptionVariant(
                model_used="gemini-3.5-flash",
                akapity=["A1", "A2", "A3"],
                generated_at="2026-06-18 12:00 UTC",
            ),
            v2=DescriptionVariant(
                model_used="gemini-3.5-flash",
                akapity=["B1", "B2", "B3"],
                generated_at="2026-06-18 12:05 UTC",
            ),
        ),
    }
    st.save_description_drafts(drafts)
    loaded = st.load_description_drafts()
    assert loaded[55].v1.ok
    assert loaded[55].v2.ok
    assert loaded[55].v2.akapity[0] == "B1"


def test_description_drafts_legacy_format(tmp_path, monkeypatch) -> None:
    from Komponenty.tytulyai import storage as st

    monkeypatch.setattr(st, "DATA_DIR", tmp_path)
    path = tmp_path / "description_drafts.json"
    monkeypatch.setattr(st, "DESCRIPTION_DRAFTS_FILE", path)

    path.write_text(
        """
{
  "version": 1,
  "drafts": {
    "77": {
      "product_id": 77,
      "artist": "Monet",
      "painting_title": "Stara wersja",
      "akapity": ["X1", "X2"],
      "model_used": "gemini-test",
      "generated_at": "2026-01-01"
    }
  }
}
""".strip(),
        encoding="utf-8",
    )
    loaded = st.load_description_drafts()
    assert loaded[77].v1.ok
    assert loaded[77].v1.akapity == ["X1", "X2"]
    assert not loaded[77].v2.ok


def test_title_draft_store_resolves_current_monkeypatched_constant(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from Komponenty.tytulyai import storage as st
    from Komponenty.tytulyai.batch import BatchItemResult

    override = tmp_path / "override" / "title_drafts.json"
    monkeypatch.setattr(st, "TITLE_DRAFTS_FILE", override)

    st.save_title_drafts(
        {
            31: BatchItemResult(
                product_id=31,
                artist="Monet",
                painting_title="Impresja",
                model_used="gemini-test",
                raw_response='{"title":"Impresja"}',
                cursor_prompt="prompt-test",
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
    from Komponenty.tytulyai import storage as st
    from Komponenty.tytulyai.descriptions import DescriptionVariant, ProductDescriptionDrafts

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
    from Komponenty.tytulyai import storage as st

    with pytest.raises(ValueError, match="Unsafe Tytuly AI draft file constant"):
        st._resolved_draft_path_for_constant("../drafts.json", for_write=True)


def test_runtime_write_inventory_no_longer_flags_tytulyai_draft_helpers() -> None:
    from tools.repository_safety.runtime_writes import scan_python_source

    repo_root = Path(__file__).resolve().parents[1]
    relative = "Komponenty/tytulyai/storage.py"
    source_path = repo_root / relative

    findings, error = scan_python_source(
        relative,
        source_path.read_text(encoding="utf-8"),
    )

    assert error == ""
    assert findings == []
