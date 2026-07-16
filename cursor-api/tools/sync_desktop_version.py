"""Synchronize package.json with the canonical desktop version module."""

from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "giclee_app" / "version.py"
PACKAGE_FILE = ROOT / "package.json"


def read_canonical_version(path: Path = VERSION_FILE) -> str:
    """Read the literal ``__version__`` assignment without importing the app."""

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        target_name: str | None = None
        value_node: ast.expr | None = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                target_name = target.id
                value_node = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_name = node.target.id
            value_node = node.value

        if target_name != "__version__" or value_node is None:
            continue
        if isinstance(value_node, ast.Constant) and isinstance(value_node.value, str):
            version = value_node.value.strip()
            if version:
                return version
        raise ValueError(f"{path}: __version__ must be a non-empty string literal")

    raise ValueError(f"{path}: missing __version__ assignment")


def sync_package_json(
    package_path: Path = PACKAGE_FILE,
    *,
    version_file: Path = VERSION_FILE,
) -> bool:
    """Write the canonical version to package.json and return whether it changed."""

    version = read_canonical_version(version_file)
    raw = package_path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError(f"{package_path}: top-level JSON value must be an object")

    data["version"] = version
    rendered = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if raw == rendered:
        return False

    package_path.write_text(rendered, encoding="utf-8")
    return True


def main() -> int:
    changed = sync_package_json()
    version = read_canonical_version()
    status = "updated" if changed else "already synchronized"
    print(f"package.json {status}: {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
