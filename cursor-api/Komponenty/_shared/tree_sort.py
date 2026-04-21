"""Helper: sortowanie Treeview po kliknieciu naglowka kolumny.

Uzycie:

    from Komponenty._shared.tree_sort import attach_sortable_headings

    tree = ttk.Treeview(parent, columns=("name", "date", "count"), show="headings")
    tree.heading("name", text="Nazwa")
    tree.heading("date", text="Data")
    tree.heading("count", text="Licznik")

    attach_sortable_headings(
        tree,
        columns={
            "name": ("Nazwa", "text"),     # string compare
            "date": ("Data", "date"),      # ISO YYYY-MM-DD (string compare OK)
            "count": ("Licznik", "int"),   # int compare
        },
    )

Po kliknieciu naglowka sortuje ASC, drugi klik DESC, w naglowku pojawia sie
▲ / ▼ (zachowujemy oryginalny label i doklejamy wskaznik).

Tylko wiersze bez rodzica (top-level) sa sortowane - nested drzewa nie sa wspierane.
"""

from __future__ import annotations

from tkinter import ttk
from typing import Callable, Literal

SortKind = Literal["text", "int", "float", "date"]


def _as_key(value: str, kind: SortKind) -> object:
    v = (value or "").strip()
    if kind == "int":
        try:
            # Usuwaj znaki dekoracyjne (np. '⚠')
            return int("".join(ch for ch in v if ch.isdigit() or ch == "-") or 0)
        except ValueError:
            return 0
    if kind == "float":
        try:
            return float("".join(ch for ch in v if ch.isdigit() or ch in ".-") or 0)
        except ValueError:
            return 0.0
    if kind == "date":
        # ISO 'YYYY-MM-DD' albo 'YYYY-MM-DDTHH:MM:SS' - string compare OK
        return v or "9999-99-99"  # puste na koniec przy ASC
    return v.lower()


def attach_sortable_headings(
    tree: ttk.Treeview,
    columns: dict[str, tuple[str, SortKind]],
    *,
    default_col: str | None = None,
    default_desc: bool = False,
    on_sort: Callable[[str, bool], None] | None = None,
) -> None:
    """Przypisuje sortowanie do naglowkow podanych kolumn.

    Args:
        tree: widget ttk.Treeview.
        columns: dict {col_id: (label, kind)} - label to nazwa kolumny, kind to typ sortowania.
        default_col: opcjonalnie id kolumny po ktorej sortujemy domyslnie.
        default_desc: czy default sort ma byc malejacy.
        on_sort: callback wolany po kazdym sortowaniu (dla refresh outside).
    """
    # Stan per tree (przechowujemy na widgecie)
    tree._sort_state: dict[str, object] = {  # type: ignore[attr-defined]
        "col": default_col,
        "desc": default_desc,
    }

    def _update_headings() -> None:
        state = tree._sort_state  # type: ignore[attr-defined]
        active_col = state["col"]
        active_desc = state["desc"]
        for col_id, (label, _kind) in columns.items():
            if col_id == active_col:
                arrow = " ▼" if active_desc else " ▲"
                tree.heading(col_id, text=label + arrow)
            else:
                tree.heading(col_id, text=label)

    def _do_sort(col_id: str, kind: SortKind) -> None:
        state = tree._sort_state  # type: ignore[attr-defined]
        if state["col"] == col_id:
            state["desc"] = not bool(state["desc"])
        else:
            state["col"] = col_id
            state["desc"] = False

        items = [(tree.set(k, col_id), k) for k in tree.get_children("")]
        items.sort(
            key=lambda pair: _as_key(pair[0], kind),
            reverse=bool(state["desc"]),
        )
        for index, (_val, k) in enumerate(items):
            tree.move(k, "", index)

        _update_headings()
        if on_sort:
            try:
                on_sort(col_id, bool(state["desc"]))
            except Exception:  # noqa: BLE001
                pass

    for col_id, (label, kind) in columns.items():
        tree.heading(
            col_id, text=label,
            command=lambda c=col_id, k=kind: _do_sort(c, k),
        )

    _update_headings()
    if default_col:
        # Zaaplikuj domyslne sortowanie
        kind = columns[default_col][1]
        # _do_sort odwraca desc, wiec zresetujmy state:
        tree._sort_state["col"] = None  # type: ignore[attr-defined]
        _do_sort(default_col, kind)
        tree._sort_state["desc"] = default_desc  # type: ignore[attr-defined]
        if default_desc:
            _do_sort(default_col, kind)  # drugi klik -> odwraca
