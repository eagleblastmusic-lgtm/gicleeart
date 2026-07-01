"""GUI: komponent «Aktualizuj opis» — okno z dodajobraz/description_update_dialog."""

from __future__ import annotations

import tkinter as tk

from Komponenty.dodajobraz.description_update_dialog import open_description_update_dialog


def main() -> None:
    root = tk.Tk()

    def enqueue_log(msg: str) -> None:
        print(msg, flush=True)

    def set_status(_msg: str) -> None:
        pass

    open_description_update_dialog(
        root,
        enqueue_log=enqueue_log,
        set_status=set_status,
        standalone=True,
    )
    root.mainloop()


if __name__ == "__main__":
    main()
