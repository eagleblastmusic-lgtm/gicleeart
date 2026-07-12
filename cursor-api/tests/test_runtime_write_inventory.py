from __future__ import annotations

from tools.repository_safety.runtime_writes import scan_python_source


def _rules(source: str) -> list[tuple[str, str]]:
    findings, error = scan_python_source("Komponenty/example/storage.py", source)
    assert error == ""
    return [(item.rule_id, item.call) for item in findings]


def test_direct_path_write_derived_from_file_is_reported() -> None:
    source = """
from pathlib import Path
ROOT = Path(__file__).resolve().parent
STORE = ROOT / "data" / "state.json"

def save(text: str) -> None:
    STORE.write_text(text, encoding="utf-8")
"""
    assert _rules(source) == [("DIRECT_SOURCE_PATH_WRITE", "STORE.write_text")]


def test_writable_open_and_read_only_open_are_distinguished() -> None:
    source = """
from pathlib import Path
ROOT = Path(__file__).resolve().parent
STORE = ROOT / "state.json"

def load() -> str:
    with open(STORE, "r", encoding="utf-8") as handle:
        return handle.read()

def save() -> None:
    with open(STORE, "w", encoding="utf-8") as handle:
        handle.write("x")
"""
    assert _rules(source) == [("DIRECT_SOURCE_PATH_WRITE", "open")]


def test_path_open_write_mode_is_reported() -> None:
    source = """
from pathlib import Path
STORE = Path(__file__).resolve().parent / "state.json"

def save() -> None:
    with STORE.open("w", encoding="utf-8") as handle:
        handle.write("x")
"""
    assert _rules(source) == [("DIRECT_SOURCE_PATH_WRITE", "STORE.open")]


def test_app_path_factory_breaks_legacy_source_propagation() -> None:
    source = """
from pathlib import Path
from giclee_app.app_paths import atomic_write_text, data_path

LEGACY = Path(__file__).resolve().parent / "data" / "state.json"
STORE = data_path("Komponenty/example/data/state.json", legacy=LEGACY)

def save() -> None:
    atomic_write_text(STORE.write_path, "{}")
"""
    assert _rules(source) == []


def test_source_path_passed_to_write_like_helper_is_reported() -> None:
    source = """
from pathlib import Path
STORE = Path(__file__).resolve().parent / "state.json"

def save_json(path, payload) -> None:
    pass

def save() -> None:
    save_json(STORE, {})
"""
    assert _rules(source) == [("SOURCE_PATH_PASSED_TO_WRITER", "save_json")]


def test_in_memory_append_is_not_treated_as_writer() -> None:
    source = """
from pathlib import Path
ROOT = Path(__file__).resolve().parent

def collect() -> list[str]:
    rows = []
    rows.append(str(ROOT))
    return rows
"""
    assert _rules(source) == []


def test_reader_result_does_not_propagate_path_taint() -> None:
    source = """
from pathlib import Path
STORE = Path(__file__).resolve().parent / "state.json"

def load_json(path):
    return {}

def save_payload(payload):
    pass

data = load_json(STORE)
save_payload(data)
"""
    assert _rules(source) == []


def test_nested_safe_factory_write_path_is_not_reported() -> None:
    source = """
from pathlib import Path
from giclee_app.app_paths import atomic_write_text, log_path

LEGACY = Path(__file__).resolve().parent / "activity.jsonl"
TARGET = log_path("logs/activity.jsonl", legacy=LEGACY).write_path

def save() -> None:
    atomic_write_text(TARGET, "x")
"""
    assert _rules(source) == []


def test_dynamic_safe_factory_alias_is_not_reported() -> None:
    source = """
from pathlib import Path
from giclee_app.app_paths import config_path, data_path

LEGACY = Path(__file__).resolve().parent / "state.json"
factory = config_path if True else data_path
STORE = factory("state.json", legacy=LEGACY).write_path

def save() -> None:
    STORE.write_text("x", encoding="utf-8")
"""
    assert _rules(source) == []


def test_user_selected_path_is_not_reported() -> None:
    source = """
from pathlib import Path

def export(target: str) -> None:
    Path(target).write_text("payload", encoding="utf-8")
"""
    assert _rules(source) == []


def test_nested_function_inherits_module_source_symbols() -> None:
    source = """
from pathlib import Path
ROOT = Path(__file__).resolve().parent

class Store:
    def save(self) -> None:
        target = ROOT / "state.json"
        target.write_bytes(b"x")
"""
    assert _rules(source) == [("DIRECT_SOURCE_PATH_WRITE", "target.write_bytes")]


def test_repository_runtime_write_inventory_is_parseable_and_emits_ci_evidence() -> None:
    import os
    from pathlib import Path

    from tools.repository_safety.runtime_writes import (
        audit_runtime_writes,
        write_runtime_write_json,
    )

    root = Path(__file__).resolve().parents[1]
    report = audit_runtime_writes(root)

    assert report.scanned_files > 0
    assert report.parse_errors == []

    runner_temp = os.environ.get("RUNNER_TEMP", "").strip()
    if runner_temp:
        candidates = (
            Path(runner_temp) / "stage2-smoke-reports",
            Path(runner_temp) / "stage2-full-baseline-reports",
        )
        for report_dir in candidates:
            if report_dir.is_dir():
                write_runtime_write_json(
                    report,
                    report_dir / "runtime-write-inventory.json",
                )
                (report_dir / "runtime-write-inventory.txt").write_text(
                    report.format_text(),
                    encoding="utf-8",
                )
