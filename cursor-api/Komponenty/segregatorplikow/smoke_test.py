"""Smoke-check segregatorplikow — tylko tymczasowy katalog testowy."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

# cursor-api na sciezce
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Komponenty.segregatorplikow.move_service import (  # noqa: E402
    DuplicatePolicy,
    has_name_conflicts,
    auto_rename_path,
    execute_moves,
    filter_file_paths,
    plan_moves,
)
from Komponenty.segregatorplikow.storage import (  # noqa: E402
    TileEntry,
    TileStore,
    load_tiles,
    save_tiles,
    TILES_FILE,
)


def main() -> int:
    errors: list[str] = []
    tmp = Path(tempfile.mkdtemp(prefix="segregator_smoke_"))
    try:
        src_dir = tmp / "zrodlo"
        dest_a = tmp / "cel_a"
        dest_b = tmp / "cel_b"
        src_dir.mkdir()
        dest_a.mkdir()
        dest_b.mkdir()

        f1 = src_dir / "test1.txt"
        f2 = src_dir / "test2.txt"
        f1.write_text("smoke 1", encoding="utf-8")
        f2.write_text("smoke 2", encoding="utf-8")
        (dest_a / "test1.txt").write_text("existing", encoding="utf-8")

        # filter_file_paths
        sub = src_dir / "podfolder"
        sub.mkdir()
        files, dirs = filter_file_paths([f1, f2, sub])
        if len(files) != 2 or len(dirs) != 1:
            errors.append(f"filter_file_paths: files={len(files)} dirs={len(dirs)}")

        # auto_rename
        renamed = auto_rename_path(dest_a, "test1.txt")
        if renamed.name != "test1 (1).txt":
            errors.append(f"auto_rename: {renamed.name}")

        # has_name_conflicts
        if has_name_conflicts([f2], dest_a):
            errors.append("has_name_conflicts: nieoczekiwany konflikt dla test2")
        if not has_name_conflicts([f1], dest_a):
            errors.append("has_name_conflicts: powinien byc konflikt dla test1")

        # plan + execute (rename policy)
        plan = plan_moves([f1, f2], dest_a, duplicate_policy=DuplicatePolicy.RENAME)
        if plan.movable_count != 2:
            errors.append(f"plan movable: {plan.movable_count}")
        results = execute_moves(plan)
        if sum(1 for r in results if r.success) != 2:
            errors.append(f"execute rename: {results}")
        if not (dest_a / "test1 (1).txt").is_file():
            errors.append("brak test1 (1).txt po rename")
        if not (dest_a / "test2.txt").is_file():
            errors.append("brak test2.txt")

        # skip policy
        f3 = src_dir / "test3.txt"
        f3.write_text("smoke 3", encoding="utf-8")
        (dest_b / "test3.txt").write_text("dup", encoding="utf-8")
        plan_skip = plan_moves([f3], dest_b, duplicate_policy=DuplicatePolicy.SKIP)
        execute_moves(plan_skip)
        if not f3.is_file():
            errors.append("skip: zrodlo zniknelo")

        # cancel policy — nic nie przenosi
        f4 = src_dir / "test4.txt"
        f4.write_text("smoke 4", encoding="utf-8")
        plan_cancel = plan_moves([f4], dest_b, duplicate_policy=DuplicatePolicy.CANCEL)
        execute_moves(plan_cancel)
        if not f4.is_file():
            errors.append("cancel: zrodlo zniknelo")

        # storage roundtrip (osobny plik w tmp)
        orig_tiles = TILES_FILE
        test_tiles = tmp / "tiles_test.json"
        import Komponenty.segregatorplikow.storage as st  # noqa: E402

        st.TILES_FILE = test_tiles
        store = TileStore(
            tiles=[
                TileEntry(
                    id="p1",
                    name="Parent",
                    path=str(dest_a),
                    children=[
                        TileEntry(id="c1", name="Child", path=str(dest_b), children=[]),
                    ],
                )
            ]
        )
        save_tiles(store)
        loaded = load_tiles()
        if len(loaded.tiles) != 1 or len(loaded.tiles[0].children) != 1:
            errors.append("storage roundtrip")
        st.TILES_FILE = orig_tiles

        # import gui (bez uruchamiania mainloop)
        from Komponenty.segregatorplikow import gui  # noqa: E402

        if not hasattr(gui, "main"):
            errors.append("gui.main brak")

        # discovery
        from giclee_app.component_loader import discover_components  # noqa: E402

        comps = discover_components(ROOT / "Komponenty")
        names = [c.folder_name for c in comps]
        if "segregatorplikow" not in names:
            errors.append("discovery: brak segregatorplikow")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if errors:
        print("SMOKE FAIL:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("SMOKE OK — wszystkie testy na katalogu tymczasowym")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
