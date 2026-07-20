"""Single-source desktop version contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import giclee_app
from giclee_app.version import __version__ as canonical_version
from tools.sync_desktop_version import read_canonical_version, sync_package_json

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_FILE = ROOT / "package.json"
INIT_FILE = ROOT / "giclee_app" / "__init__.py"
VERSION_FILE = ROOT / "giclee_app" / "version.py"


def test_python_package_reexports_canonical_version() -> None:
    assert canonical_version == "1.6.0"
    assert giclee_app.__version__ == canonical_version
    assert read_canonical_version(VERSION_FILE) == canonical_version


def test_package_json_version_matches_canonical_source() -> None:
    package = json.loads(PACKAGE_FILE.read_text(encoding="utf-8"))
    assert package["version"] == canonical_version


def test_init_module_does_not_define_an_independent_literal_version() -> None:
    source = INIT_FILE.read_text(encoding="utf-8")
    assert "from .version import __version__" in source
    assert '__version__ = "' not in source
    assert "__version__ = '" not in source


def test_sync_tool_updates_then_becomes_idempotent(tmp_path: Path) -> None:
    package_path = tmp_path / "package.json"
    package_path.write_text(
        json.dumps({"name": "test", "version": "0.0.0"}, indent=2) + "\n",
        encoding="utf-8",
    )

    assert sync_package_json(package_path, version_file=VERSION_FILE) is True
    first = package_path.read_text(encoding="utf-8")
    assert json.loads(first)["version"] == canonical_version

    assert sync_package_json(package_path, version_file=VERSION_FILE) is False
    assert package_path.read_text(encoding="utf-8") == first


def test_read_canonical_version_rejects_nonliteral_assignment(tmp_path: Path) -> None:
    bad = tmp_path / "version.py"
    bad.write_text("__version__ = make_version()\n", encoding="utf-8")

    try:
        read_canonical_version(bad)
    except ValueError as exc:
        assert "string literal" in str(exc)
    else:
        raise AssertionError("non-literal version must be rejected")
