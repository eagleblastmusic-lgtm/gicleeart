from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TARGET = ROOT / "cursor-api/Komponenty/dodajobraz/description_update.py"


def replace_exact(text: str, old: str, new: str, *, expected: int = 1) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(
            f"Expected {expected} occurrence(s), found {count}: {old[:120]!r}"
        )
    return text.replace(old, new)


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")
    if "def _runtime_data_file_for_constant(" in text:
        print("Description mark boundary already applied.")
        return

    old_runtime = '''def _runtime_data_file(path: Path, *, for_write: bool = False) -> Path:
    """Resolve a DodajObraz mutable JSON path without writing to source.

    Existing tests and tools may monkeypatch a concrete file constant. Such an
    explicit override remains authoritative. In the default layout AppData wins
    for reads, while the source-tree file is a read-only legacy fallback.
    """

    current = Path(path)
    legacy = _LEGACY_DATA_DIR / current.name
    if current != legacy:
        return current
    app_path = data_path(
        f"Komponenty/dodajobraz/data/{current.name}",
        legacy=legacy,
    )
    return app_path.write_path if for_write else app_path.read_path()
'''
    new_runtime = old_runtime + '''\n\n_RUNTIME_FILE_CONSTANT_RE = re.compile(r"^_[A-Z0-9_]+_FILE$")


def _runtime_data_file_for_constant(
    constant_name: str,
    *,
    for_write: bool = False,
) -> Path:
    """Resolve the current value of a mutable-file module constant.

    The indirection keeps monkeypatched file constants authoritative without
    passing a source-derived ``Path`` into write-like helpers.
    """

    name = str(constant_name).strip()
    if not _RUNTIME_FILE_CONSTANT_RE.fullmatch(name):
        raise ValueError(f"Unsafe description runtime file constant: {constant_name!r}")
    try:
        configured = globals()[name]
    except KeyError as exc:
        raise KeyError(f"Unknown description runtime file constant: {name}") from exc
    return _runtime_data_file(Path(configured), for_write=for_write)
'''
    text = replace_exact(text, old_runtime, new_runtime)

    old_helpers = '''def _load_marks_file(path: Path) -> set[int]:
    path = _runtime_data_file(path)
    if not path.is_file():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    if not isinstance(data, list):
        return set()
    out: set[int] = set()
    for item in data:
        try:
            out.add(int(item))
        except (TypeError, ValueError):
            continue
    return out


def _save_marks_file(path: Path, product_ids: set[int]) -> None:
    path = _runtime_data_file(path, for_write=True)
    payload = sorted(product_ids)
    atomic_write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\\n")
'''
    new_helpers = '''def _load_marks_file(file_constant: str) -> set[int]:
    path = _runtime_data_file_for_constant(file_constant)
    if not path.is_file():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    if not isinstance(data, list):
        return set()
    out: set[int] = set()
    for item in data:
        try:
            out.add(int(item))
        except (TypeError, ValueError):
            continue
    return out


def _save_marks_file(file_constant: str, product_ids: set[int]) -> None:
    path = _runtime_data_file_for_constant(file_constant, for_write=True)
    payload = sorted(product_ids)
    atomic_write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\\n")
'''
    text = replace_exact(text, old_helpers, new_helpers)

    load_constants = [
        "_DESCRIPTION_PL_PENDING_MARKS_FILE",
        "_TITLE_UPDATE_MARKS_FILE",
        "_DESCRIPTION_GPT_TRANSLATION_MARKS_FILE",
        "_DESCRIPTION_SONNET_TRANSLATION_MARKS_FILE",
        "_DESCRIPTION_FROM_IMAGE_MARKS_FILE",
        "_DESCRIPTION_BEZ_16_MARKS_FILE",
    ]
    save_constants = [
        *load_constants,
        "_DESCRIPTION_DO_TLUMACZENIA_MARKS_FILE",
    ]

    for constant in load_constants:
        text = replace_exact(
            text,
            f"_load_marks_file({constant})",
            f'_load_marks_file("{constant}")',
        )
    for constant in save_constants:
        text = replace_exact(
            text,
            f"_save_marks_file({constant}, product_ids)",
            f'_save_marks_file("{constant}", product_ids)',
        )

    TARGET.write_text(text, encoding="utf-8", newline="\n")
    print(f"Patched {TARGET}")


if __name__ == "__main__":
    main()
