"""GUI: komponent «Wybór szablonu produktu»."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from Komponenty.dodajobraz.product_template_dialog import open_product_template_dialog


def main() -> None:
    root = tk.Tk()
    status_var = tk.StringVar(value="Gotowy.")

    status = ttk.Frame(root)
    status.pack(side="bottom", fill="x", padx=12, pady=6)
    ttk.Label(status, textvariable=status_var, foreground="#444").pack(side="left")

    def enqueue_log(msg: str) -> None:
        print(msg, flush=True)

    open_product_template_dialog(
        root,
        enqueue_log=enqueue_log,
        set_status=status_var.set,
        standalone=True,
    )
    root.mainloop()


if __name__ == "__main__":
    main()
