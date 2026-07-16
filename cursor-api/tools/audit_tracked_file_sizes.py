"""Audit tracked files before they become repository-history liabilities."""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MAX_BYTES = 25 * 1024 * 1024
_LFS_HEADER = b"version https://git-lfs.github.com/spec/v1\n"


@dataclass(frozen=True)
class LargeTrackedFile:
    path: str
    size_bytes: int
    is_lfs_pointer: bool


def tracked_paths(repo_root: Path) -> list[Path]:
    """Return files tracked by Git, independent of ignored/untracked runtime data."""

    completed = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    return [
        repo_root / raw.decode("utf-8", errors="surrogateescape")
        for raw in completed.stdout.split(b"\0")
        if raw
    ]


def is_lfs_pointer(path: Path) -> bool:
    """Recognize a Git LFS pointer without loading the tracked asset into memory."""

    try:
        with path.open("rb") as handle:
            return handle.read(len(_LFS_HEADER)) == _LFS_HEADER
    except OSError:
        return False


def audit_tracked_files(
    repo_root: Path,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> list[LargeTrackedFile]:
    """Return oversized tracked regular files; LFS pointers are marked explicitly."""

    findings: list[LargeTrackedFile] = []
    root = repo_root.resolve()
    for path in tracked_paths(root):
        try:
            if not path.is_file():
                continue
            size = path.stat().st_size
        except OSError:
            continue
        if size <= max_bytes:
            continue
        findings.append(
            LargeTrackedFile(
                path=path.relative_to(root).as_posix(),
                size_bytes=size,
                is_lfs_pointer=is_lfs_pointer(path),
            )
        )
    findings.sort(key=lambda item: (-item.size_bytes, item.path))
    return findings


def format_bytes(size: int) -> str:
    return f"{size / (1024 * 1024):.2f} MiB"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    args = parser.parse_args(argv)

    findings = audit_tracked_files(args.repo_root, max_bytes=args.max_bytes)
    blocking = [item for item in findings if not item.is_lfs_pointer]

    if not findings:
        print(f"tracked-large-file audit: PASS (limit={format_bytes(args.max_bytes)})")
        return 0

    for item in findings:
        status = "LFS pointer" if item.is_lfs_pointer else "tracked binary/content"
        print(f"{item.path}\t{format_bytes(item.size_bytes)}\t{status}")

    if blocking:
        print(
            f"tracked-large-file audit: FAIL ({len(blocking)} non-LFS file(s) exceed the limit)"
        )
        return 1

    print("tracked-large-file audit: PASS (all oversized entries are LFS pointers)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
