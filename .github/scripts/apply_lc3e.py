from __future__ import annotations

from pathlib import Path


APP = Path("cursor-api/giclee_app")


def replace_exact(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one replacement, found {count}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def main() -> None:
    dragdrop = APP / "dragdrop_category_launcher.py"

    replace_exact(
        dragdrop,
        "from .launcher_drag_geometry import (\n"
        "    DragPoint,\n"
        "    DragRect,\n"
        "    drag_threshold_reached,\n"
        "    drop_after,\n"
        "    nearest_rect_index,\n"
        "    point_inside,\n"
        ")\n",
        "from .launcher_drag_geometry import (\n"
        "    DragPoint,\n"
        "    DragRect,\n"
        "    drag_threshold_reached,\n"
        "    drop_after,\n"
        "    nearest_rect_index,\n"
        "    point_inside,\n"
        ")\n"
        "from .launcher_drag_gesture import (\n"
        "    DragMotionKind,\n"
        "    DragReleaseKind,\n"
        "    resolve_drag_motion,\n"
        "    resolve_drag_release,\n"
        ")\n",
    )
    replace_exact(
        dragdrop,
        '''        threshold_reached = drag_threshold_reached(
            DragPoint(state.start_x_root, state.start_y_root),
            DragPoint(int(event.x_root), int(event.y_root)),
            _DRAG_THRESHOLD_PX,
        )
        if not state.dragging and not threshold_reached:
            return None

        if not state.dragging:
            state.dragging = True
            self._set_tile_border(state.source, _BORDER_DRAG_SOURCE)
            try:
                self.root.configure(cursor="fleur")
            except tk.TclError:
                pass
''',
        '''        threshold_reached = drag_threshold_reached(
            DragPoint(state.start_x_root, state.start_y_root),
            DragPoint(int(event.x_root), int(event.y_root)),
            _DRAG_THRESHOLD_PX,
        )
        motion = resolve_drag_motion(
            dragging=state.dragging,
            threshold_reached=threshold_reached,
        )
        if motion is DragMotionKind.WAITING:
            return None

        if motion is DragMotionKind.START:
            state.dragging = True
            self._set_tile_border(state.source, _BORDER_DRAG_SOURCE)
            try:
                self.root.configure(cursor="fleur")
            except tk.TclError:
                pass
''',
    )
    replace_exact(
        dragdrop,
        '''        if not state.dragging:
            self._drag_state = None
            state.activate()
            return "break"

        target = state.target or self._find_drop_target(
            state.kind,
            int(event.x_root),
            int(event.y_root),
            exclude=state.source,
        )
        after = state.after
        if target is not None and state.target is None:
            after = self._drop_after(target, int(event.x_root), int(event.y_root))

        source_key = state.key
        target_key = str(getattr(target, "_launcher_dnd_key", "")) if target is not None else ""
        kind = state.kind
        self._clear_drag_state()

        if target_key and target_key != source_key:
            if kind == "category":
                self._reorder_category(source_key, target_key, after=after)
            elif kind == "component":
                self._reorder_component(source_key, target_key, after=after)
        return "break"
''',
        '''        if not state.dragging:
            decision = resolve_drag_release(
                dragging=False,
                drag_kind=state.kind,
                source_key=state.key,
                target_key="",
                after=False,
            )
            self._drag_state = None
            if decision.kind is DragReleaseKind.ACTIVATE:
                state.activate()
            return "break"

        target = state.target or self._find_drop_target(
            state.kind,
            int(event.x_root),
            int(event.y_root),
            exclude=state.source,
        )
        after = state.after
        if target is not None and state.target is None:
            after = self._drop_after(target, int(event.x_root), int(event.y_root))

        target_key = str(getattr(target, "_launcher_dnd_key", "")) if target is not None else ""
        decision = resolve_drag_release(
            dragging=True,
            drag_kind=state.kind,
            source_key=state.key,
            target_key=target_key,
            after=after,
        )
        self._clear_drag_state()

        if decision.kind is DragReleaseKind.REORDER:
            if decision.drag_kind == "category":
                self._reorder_category(
                    decision.source_key,
                    decision.target_key,
                    after=decision.after,
                )
            elif decision.drag_kind == "component":
                self._reorder_component(
                    decision.source_key,
                    decision.target_key,
                    after=decision.after,
                )
        return "break"
''',
    )

    replace_exact(
        APP / "docs" / "launcher.md",
        "**LC-3D pure drag geometry:** `launcher_drag_geometry.py` izoluje próg ruchu, prostokąty, hit-testing, `drop_after` i wybór najbliższego celu. Stan gestu, eventy Tk, feedback, auto-scroll i zapis pozostają w `DragDropCategoryGicleeApp`.\n\n---\n",
        "**LC-3D pure drag geometry:** `launcher_drag_geometry.py` izoluje próg ruchu, prostokąty, hit-testing, `drop_after` i wybór najbliższego celu. Stan gestu, eventy Tk, feedback, auto-scroll i zapis pozostają w `DragDropCategoryGicleeApp`.\n\n"
        "**LC-3E drag gesture decisions:** `launcher_drag_gesture.py` rozstrzyga `WAITING / START / CONTINUE` dla motion oraz `ACTIVATE / REORDER / NOOP` dla release. Mutable state, widgety, feedback, auto-scroll i persistence pozostają w `DragDropCategoryGicleeApp`.\n\n---\n",
    )
    replace_exact(
        APP / "docs" / "launcher-composition-lc3e-contract.md",
        "**Status:** fresh reconnaissance · contract freeze  ",
        "**Status:** LC-3E implemented",
    )


if __name__ == "__main__":
    main()
