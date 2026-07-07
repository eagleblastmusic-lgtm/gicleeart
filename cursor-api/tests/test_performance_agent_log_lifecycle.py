from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.performance_agent.log_lifecycle import apply_log_lifecycle, archive_root


def test_clear_archives_and_removes_log(tmp_path: Path) -> None:
    log = tmp_path / "studio_perf.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text('{"event":"test"}\n', encoding="utf-8")
    archive_dir = archive_root(tmp_path / "reports")

    result = apply_log_lifecycle(log, "clear", archive_dir=archive_dir)

    assert result.mode == "clear"
    assert result.original_log_existed is True
    assert result.archived_to is not None
    assert result.archived_to.exists()
    assert not log.exists()
    assert result.cleared is True
    assert result.archived_to.read_text(encoding="utf-8") == '{"event":"test"}\n'


def test_keep_leaves_log_untouched(tmp_path: Path) -> None:
    log = tmp_path / "studio_perf.log"
    log.write_text("line\n", encoding="utf-8")
    archive_dir = archive_root(tmp_path / "reports")

    result = apply_log_lifecycle(log, "keep", archive_dir=archive_dir)

    assert result.original_log_existed is True
    assert result.archived_to is None
    assert log.exists()
    assert result.cleared is False


def test_copy_only_archives_without_removing(tmp_path: Path) -> None:
    log = tmp_path / "studio_perf.log"
    log.write_text("line\n", encoding="utf-8")
    archive_dir = archive_root(tmp_path / "reports")

    result = apply_log_lifecycle(log, "copy_only", archive_dir=archive_dir)

    assert result.original_log_existed is True
    assert result.archived_to is not None
    assert result.archived_to.exists()
    assert log.exists()
    assert result.cleared is False


def test_clear_without_existing_log(tmp_path: Path) -> None:
    log = tmp_path / "studio_perf.log"
    archive_dir = archive_root(tmp_path / "reports")

    result = apply_log_lifecycle(log, "clear", archive_dir=archive_dir)

    assert result.original_log_existed is False
    assert result.archived_to is None
    assert result.cleared is False
