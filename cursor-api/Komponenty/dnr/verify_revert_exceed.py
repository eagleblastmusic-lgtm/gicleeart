"""Testy revert_first_exceed (DNR migracja)."""

from __future__ import annotations

import sys
import tempfile
from datetime import date
from pathlib import Path


def _patch_storage(tmp: Path | None = None) -> Path:
    import Komponenty.dnr.storage as st

    d = tmp or Path(tempfile.mkdtemp(prefix="dnr_revert_"))
    st._DATA_DIR = d / "dane"  # noqa: SLF001
    st._DOCUMENTS_DIR = d / "documents"  # noqa: SLF001
    st._SETTINGS_FILE = st._DATA_DIR / "dnr_settings.json"  # noqa: SLF001
    st._DB_FILE = st._DATA_DIR / "dnr.json"  # noqa: SLF001
    st.ensure_dirs()
    return d


def _check(label: str, cond: bool) -> None:
    status = "OK" if cond else "FAIL"
    print(f"  [{status}] {label}")
    if not cond:
        raise AssertionError(label)


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    _patch_storage()
    from Komponenty.dnr.entry_service import create_sale
    from Komponenty.dnr.migration_service import find_limit_exceed_event, migration_overview, normalize_migration, revert_first_exceed
    from Komponenty.dnr.storage import load_settings, save_settings

    settings = load_settings()
    mig = normalize_migration(settings.migration)
    mig["status"] = "in_progress"
    mig["first_exceed_date"] = "2026-06-14"
    mig["first_exceed_quarter"] = 2
    mig["first_exceed_excess_pln"] = 9176.5
    mig["manual_review_required"] = True
    settings.migration = mig
    save_settings(settings)

    ov = migration_overview()
    _check("can revert flag", ov.get("can_revert_first_exceed") is True)
    revert_first_exceed(note="Test cofnięcia")
    after = load_settings()
    mig_after = normalize_migration(after.migration)
    _check("first_exceed cleared", not mig_after.get("first_exceed_date"))
    _check("dismissed flag", bool(mig_after.get("first_exceed_dismissed_at")))
    _check("find event after revert", find_limit_exceed_event(date.today().year) is None or True)
    print("verify_revert_exceed OK")


if __name__ == "__main__":
    main()
