"""Repository-history guard for oversized tracked files."""

from __future__ import annotations

from pathlib import Path

from tools import audit_tracked_file_sizes as audit

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_repository_has_no_non_lfs_tracked_file_over_25_mib() -> None:
    findings = audit.audit_tracked_files(REPO_ROOT)
    blocking = [item for item in findings if not item.is_lfs_pointer]
    assert blocking == [], "oversized tracked files: " + ", ".join(
        f"{item.path} ({audit.format_bytes(item.size_bytes)})"
        for item in blocking
    )


def test_audit_reports_oversized_file_and_marks_lfs_pointer(
    monkeypatch,
    tmp_path: Path,
) -> None:
    regular = tmp_path / "regular.bin"
    regular.write_bytes(b"x" * 32)
    pointer = tmp_path / "pointer.dat"
    pointer.write_bytes(
        b"version https://git-lfs.github.com/spec/v1\n"
        b"oid sha256:0000000000000000000000000000000000000000000000000000000000000000\n"
        b"size 99999999\n"
    )

    monkeypatch.setattr(audit, "tracked_paths", lambda _root: [regular, pointer])
    findings = audit.audit_tracked_files(tmp_path, max_bytes=1)

    assert [(item.path, item.is_lfs_pointer) for item in findings] == [
        ("pointer.dat", True),
        ("regular.bin", False),
    ]


def test_format_bytes_is_stable() -> None:
    assert audit.format_bytes(25 * 1024 * 1024) == "25.00 MiB"
