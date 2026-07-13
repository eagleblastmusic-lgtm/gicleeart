from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_exact(path: Path, old: str, new: str, *, count: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    found = text.count(old)
    if found != count:
        raise RuntimeError(f"{path}: expected {count} occurrences, found {found}: {old[:80]!r}")
    path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")


# ---------------------------------------------------------------------------
# orders_sync.py
# ---------------------------------------------------------------------------
path = ROOT / "cursor-api/Komponenty/produkcja/orders_sync.py"
replace_exact(
    path,
    "from pathlib import Path\nfrom typing import Any\n\nfrom Komponenty.dodajobraz import shopify_client as sc\n",
    "from pathlib import Path\nfrom typing import Any\n\nfrom giclee_app.app_paths import atomic_write_text\n\nfrom Komponenty.dodajobraz import shopify_client as sc\nfrom Komponenty.produkcja import production_store\n",
)
replace_exact(
    path,
    "_COMPONENT_DIR = Path(__file__).resolve().parent\n_DATA_DIR = _COMPONENT_DIR / \"dane\"\n_ORDERS_FILE = _DATA_DIR / \"zamowienia.json\"\n_SYNC_STATE_FILE = _DATA_DIR / \"sync_state.json\"\n",
    """_COMPONENT_DIR = Path(__file__).resolve().parent
_LEGACY_DATA_DIR = _COMPONENT_DIR / "dane"
_DATA_DIR = _LEGACY_DATA_DIR
_LEGACY_ORDERS_FILE = _LEGACY_DATA_DIR / "zamowienia.json"
_ORDERS_FILE = _LEGACY_ORDERS_FILE
_LEGACY_SYNC_STATE_FILE = _LEGACY_DATA_DIR / "sync_state.json"
_SYNC_STATE_FILE = _LEGACY_SYNC_STATE_FILE


def _data_dir_override() -> Path | None:
    current = Path(_DATA_DIR)
    return current if current != _LEGACY_DATA_DIR else None


def _orders_path(*, for_write: bool) -> Path:
    explicit = Path(_ORDERS_FILE)
    if explicit != _LEGACY_ORDERS_FILE:
        return explicit
    override = _data_dir_override()
    if override is not None:
        return override / "zamowienia.json"
    return production_store.orders_write_path() if for_write else production_store.orders_read_path()


def _sync_state_path(*, for_write: bool) -> Path:
    explicit = Path(_SYNC_STATE_FILE)
    if explicit != _LEGACY_SYNC_STATE_FILE:
        return explicit
    override = _data_dir_override()
    if override is not None:
        return override / "sync_state.json"
    return (
        production_store.sync_state_write_path()
        if for_write
        else production_store.sync_state_read_path()
    )
""",
)
replace_exact(
    path,
    """def _ensure_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


""",
    "",
)
replace_exact(
    path,
    """def _load_db() -> dict[str, Any]:
    _ensure_dir()
    if not _ORDERS_FILE.is_file():
        return {"next_id": 1, "orders": []}
    try:
        return json.loads(_ORDERS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"next_id": 1, "orders": []}


def _save_db(db: dict[str, Any]) -> None:
    _ensure_dir()
    _ORDERS_FILE.write_text(
        json.dumps(db, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _load_sync_state() -> dict[str, Any]:
    _ensure_dir()
    if not _SYNC_STATE_FILE.is_file():
        return {}
    try:
        return json.loads(_SYNC_STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_sync_state(state: dict[str, Any]) -> None:
    _ensure_dir()
    _SYNC_STATE_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
""",
    """def _load_db() -> dict[str, Any]:
    path = _orders_path(for_write=False)
    if not path.is_file():
        return {"next_id": 1, "orders": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"next_id": 1, "orders": []}


def _save_db(db: dict[str, Any]) -> None:
    atomic_write_text(
        _orders_path(for_write=True),
        json.dumps(db, indent=2, ensure_ascii=False) + "\\n",
    )


def _load_sync_state() -> dict[str, Any]:
    path = _sync_state_path(for_write=False)
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_sync_state(state: dict[str, Any]) -> None:
    atomic_write_text(
        _sync_state_path(for_write=True),
        json.dumps(state, indent=2, ensure_ascii=False) + "\\n",
    )
""",
)
replace_exact(
    path,
    """def reset_sync_state() -> None:
    \"\"\"Kasuje state - przy nastepnej sync pobierzemy cala historie (since_days).\"\"\"
    if _SYNC_STATE_FILE.is_file():
        _SYNC_STATE_FILE.unlink()
""",
    """def reset_sync_state() -> None:
    \"\"\"Resetuje state bez ponownego odslaniania legacy fallbacku.\"\"\"
    atomic_write_text(_sync_state_path(for_write=True), "{}\\n")
""",
)

# ---------------------------------------------------------------------------
# retention.py
# ---------------------------------------------------------------------------
path = ROOT / "cursor-api/Komponenty/produkcja/retention.py"
replace_exact(
    path,
    "from pathlib import Path\nfrom typing import Any, Callable\n\n_DATA_DIR = Path(__file__).resolve().parent / \"dane\"\n_ORDERS_FILE = _DATA_DIR / \"zamowienia.json\"\n",
    """from pathlib import Path
from typing import Any, Callable

from giclee_app.app_paths import atomic_write_text

from Komponenty.produkcja import production_store

_COMPONENT_DIR = Path(__file__).resolve().parent
_LEGACY_DATA_DIR = _COMPONENT_DIR / "dane"
_DATA_DIR = _LEGACY_DATA_DIR
_LEGACY_ORDERS_FILE = _LEGACY_DATA_DIR / "zamowienia.json"
_ORDERS_FILE = _LEGACY_ORDERS_FILE


def _data_dir_override() -> Path | None:
    current = Path(_DATA_DIR)
    return current if current != _LEGACY_DATA_DIR else None


def _orders_path(*, for_write: bool) -> Path:
    explicit = Path(_ORDERS_FILE)
    if explicit != _LEGACY_ORDERS_FILE:
        return explicit
    override = _data_dir_override()
    if override is not None:
        return override / "zamowienia.json"
    return production_store.orders_write_path() if for_write else production_store.orders_read_path()
""",
)
replace_exact(
    path,
    """def _load_orders() -> dict:
    if not _ORDERS_FILE.is_file():
        return {"next_id": 1, "orders": []}
    try:
        return json.loads(_ORDERS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"next_id": 1, "orders": []}


def _save_orders(db: dict) -> None:
    _ORDERS_FILE.write_text(
        json.dumps(db, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _archive_file_for_year(year: int) -> Path:
    return _DATA_DIR / f"archive_{year}.json"


def _load_archive(year: int) -> dict:
    p = _archive_file_for_year(year)
    if not p.is_file():
        return {"year": year, "orders": []}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"year": year, "orders": []}


def _save_archive(year: int, data: dict) -> None:
    p = _archive_file_for_year(year)
    p.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
""",
    """def _load_orders() -> dict:
    path = _orders_path(for_write=False)
    if not path.is_file():
        return {"next_id": 1, "orders": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"next_id": 1, "orders": []}


def _save_orders(db: dict) -> None:
    atomic_write_text(
        _orders_path(for_write=True),
        json.dumps(db, indent=2, ensure_ascii=False) + "\\n",
    )


def _archive_file_for_year(year: int, *, for_write: bool = False) -> Path:
    override = _data_dir_override()
    if override is not None:
        return override / f"archive_{int(year)}.json"
    return (
        production_store.archive_write_path(year)
        if for_write
        else production_store.archive_read_path(year)
    )


def _load_archive(year: int) -> dict:
    path = _archive_file_for_year(year)
    if not path.is_file():
        return {"year": year, "orders": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"year": year, "orders": []}


def _save_archive(year: int, data: dict) -> None:
    atomic_write_text(
        _archive_file_for_year(year, for_write=True),
        json.dumps(data, indent=2, ensure_ascii=False) + "\\n",
    )
""",
)
replace_exact(
    path,
    """    out: list[dict[str, Any]] = []
    if not _DATA_DIR.is_dir():
        return out
    for p in sorted(_DATA_DIR.glob("archive_*.json")):
""",
    """    out: list[dict[str, Any]] = []
    override = _data_dir_override()
    if override is not None:
        paths = sorted(override.glob("archive_*.json")) if override.is_dir() else []
    else:
        paths = production_store.archive_read_paths()
    for p in paths:
""",
)

# ---------------------------------------------------------------------------
# view.py
# ---------------------------------------------------------------------------
path = ROOT / "cursor-api/Komponenty/produkcja/view.py"
replace_exact(
    path,
    "from pathlib import Path\nfrom tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk\nfrom typing import Any\n\ntry:\n",
    "from pathlib import Path\nfrom tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk\nfrom typing import Any\n\nfrom giclee_app.app_paths import atomic_write_text\n\ntry:\n",
)
replace_exact(
    path,
    "from Komponenty._shared.window_geometry import position_toplevel_screen_center\nfrom Komponenty.produkcja.frame_variant import (\n",
    "from Komponenty._shared.window_geometry import position_toplevel_screen_center\nfrom Komponenty.produkcja import production_store\nfrom Komponenty.produkcja.frame_variant import (\n",
)
replace_exact(
    path,
    "_COMPONENT_DIR = Path(__file__).resolve().parent\n_DATA_DIR = _COMPONENT_DIR / \"dane\"\n_ORDERS_FILE = _DATA_DIR / \"zamowienia.json\"\n",
    """_COMPONENT_DIR = Path(__file__).resolve().parent
_LEGACY_DATA_DIR = _COMPONENT_DIR / "dane"
_DATA_DIR = _LEGACY_DATA_DIR
_LEGACY_ORDERS_FILE = _LEGACY_DATA_DIR / "zamowienia.json"
_ORDERS_FILE = _LEGACY_ORDERS_FILE


def _data_dir_path() -> Path:
    current = Path(_DATA_DIR)
    if current != _LEGACY_DATA_DIR:
        return current
    return production_store.data_directory()


def _orders_path(*, for_write: bool) -> Path:
    explicit = Path(_ORDERS_FILE)
    if explicit != _LEGACY_ORDERS_FILE:
        return explicit
    current_dir = Path(_DATA_DIR)
    if current_dir != _LEGACY_DATA_DIR:
        return current_dir / "zamowienia.json"
    return production_store.orders_write_path() if for_write else production_store.orders_read_path()
""",
)
replace_exact(
    path,
    """def _ensure_storage() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not _ORDERS_FILE.exists():
        _ORDERS_FILE.write_text(
            json.dumps({"next_id": 1, "orders": []}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def _load_db() -> dict[str, Any]:
    _ensure_storage()
    try:
        data = json.loads(_ORDERS_FILE.read_text(encoding="utf-8"))
""",
    """def _ensure_storage() -> None:
    if not _orders_path(for_write=False).exists():
        atomic_write_text(
            _orders_path(for_write=True),
            json.dumps({"next_id": 1, "orders": []}, indent=2, ensure_ascii=False) + "\\n",
        )


def _load_db() -> dict[str, Any]:
    _ensure_storage()
    try:
        data = json.loads(_orders_path(for_write=False).read_text(encoding="utf-8"))
""",
)
replace_exact(
    path,
    """def _save_db(db: dict[str, Any]) -> None:
    _ensure_storage()
    try:
        _ORDERS_FILE.write_text(
            json.dumps(db, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as e:
""",
    """def _save_db(db: dict[str, Any]) -> None:
    try:
        atomic_write_text(
            _orders_path(for_write=True),
            json.dumps(db, indent=2, ensure_ascii=False) + "\\n",
        )
    except OSError as e:
""",
)
replace_exact(path, "_os.startfile(str(_DATA_DIR))", "_os.startfile(str(_data_dir_path()))")
replace_exact(path, "_sp.Popen([\"open\", str(_DATA_DIR)])", "_sp.Popen([\"open\", str(_data_dir_path())])")
replace_exact(path, "_sp.Popen([\"xdg-open\", str(_DATA_DIR)])", "_sp.Popen([\"xdg-open\", str(_data_dir_path())])")
replace_exact(
    path,
    "- Single-source-of-truth: `Komponenty/produkcja/dane/zamowienia.json`.",
    "- Single-source-of-truth: Local AppData `Komponenty/produkcja/dane/zamowienia.json`.",
)
replace_exact(
    path,
    'f"Archiwa sa w Komponenty/produkcja/dane/archive_YYYY.json.",',
    'f"Archiwa sa w: {_data_dir_path()}\\archive_YYYY.json.",',
)
replace_exact(
    path,
    "- Wszystkie zamowienia: `Komponenty/produkcja/dane/zamowienia.json`.",
    "- Wszystkie zamowienia: Local AppData `Komponenty/produkcja/dane/zamowienia.json`.",
)

# ---------------------------------------------------------------------------
# web_server.py
# ---------------------------------------------------------------------------
path = ROOT / "cursor-api/Komponenty/produkcja/web_server.py"
replace_exact(
    path,
    "sys.path.insert(0, str(_CURSOR_API))\n\nfrom Komponenty._shared import auth  # noqa: E402\n",
    "sys.path.insert(0, str(_CURSOR_API))\n\nfrom giclee_app.app_paths import atomic_write_text  # noqa: E402\n\nfrom Komponenty._shared import auth  # noqa: E402\nfrom Komponenty.produkcja import production_store  # noqa: E402\n",
)
replace_exact(
    path,
    "_ORDERS_FILE = _CURSOR_API / \"Komponenty\" / \"produkcja\" / \"dane\" / \"zamowienia.json\"\n_SESSION_FILE = _CURSOR_API / \".shopify_session.json\"\n",
    """_LEGACY_DATA_DIR = _CURSOR_API / "Komponenty" / "produkcja" / "dane"
_DATA_DIR = _LEGACY_DATA_DIR
_LEGACY_ORDERS_FILE = _LEGACY_DATA_DIR / "zamowienia.json"
_ORDERS_FILE = _LEGACY_ORDERS_FILE
_SESSION_FILE = _CURSOR_API / ".shopify_session.json"


def _orders_path(*, for_write: bool) -> Path:
    explicit = Path(_ORDERS_FILE)
    if explicit != _LEGACY_ORDERS_FILE:
        return explicit
    current_dir = Path(_DATA_DIR)
    if current_dir != _LEGACY_DATA_DIR:
        return current_dir / "zamowienia.json"
    return production_store.orders_write_path() if for_write else production_store.orders_read_path()
""",
)
replace_exact(
    path,
    """def _load_db() -> dict:
    if not _ORDERS_FILE.is_file():
        return {"next_id": 1, "orders": []}
    try:
        db = json.loads(_ORDERS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"next_id": 1, "orders": []}
    for o in db.get("orders") or []:
        migrate_order_frame_fields(o)
    return db


def _save_db(db: dict) -> None:
    _ORDERS_FILE.write_text(
        json.dumps(db, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
""",
    """def _load_db() -> dict:
    path = _orders_path(for_write=False)
    if not path.is_file():
        return {"next_id": 1, "orders": []}
    try:
        db = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"next_id": 1, "orders": []}
    for o in db.get("orders") or []:
        migrate_order_frame_fields(o)
    return db


def _save_db(db: dict) -> None:
    atomic_write_text(
        _orders_path(for_write=True),
        json.dumps(db, indent=2, ensure_ascii=False) + "\\n",
    )
""",
)

print("Applied exact production-store integration patch.")
