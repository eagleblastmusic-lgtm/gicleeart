from __future__ import annotations

import json
from pathlib import Path

import pytest

from Komponenty.dodajobraz import description_update as du
from tools.repository_safety.runtime_writes import scan_python_source


def test_mark_store_resolves_current_monkeypatched_constant(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    override = tmp_path / "override" / "description_pl_pending_marks.json"
    monkeypatch.setattr(du, "_DESCRIPTION_PL_PENDING_MARKS_FILE", override)

    du.save_description_pl_pending_marks({31, 32})

    assert json.loads(override.read_text(encoding="utf-8")) == [31, 32]
    assert du.load_description_pl_pending_marks() == {31, 32}
    assert not list(override.parent.glob(f".{override.name}.*.tmp"))


def test_mark_store_rejects_invalid_constant_name() -> None:
    with pytest.raises(ValueError, match="Unsafe description runtime file constant"):
        du._runtime_data_file_for_constant("../description.json")


def test_runtime_write_inventory_no_longer_flags_description_mark_helpers() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    relative = "Komponenty/dodajobraz/description_update.py"
    source_path = repo_root / relative

    findings, error = scan_python_source(
        relative,
        source_path.read_text(encoding="utf-8"),
    )

    assert error == ""
    assert findings == []
