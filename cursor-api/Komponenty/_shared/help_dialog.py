"""Wspolny dialog "Instrukcja" uzywany przez wszystkie aplikacje GicleeApp.

Pozwala wyswietlic markdown-podobna instrukcje obslugi w osobnym oknie -
bez ladowania ciezkich bibliotek (czyste Tk + minimalny formatter).

Uzycie:
    from Komponenty._shared.help_dialog import show_help

    show_help(parent, title="Instrukcja - dodajobraz", text=INSTRUKCJA_MD)

Format markdown obslugiwany:
    # Naglowek 1
    ## Naglowek 2
    ### Naglowek 3
    **bold**
    `code`
    - bullet point
    1. numbered list
    > quote
    --- horyzontalna linia
    [link text](url) - klikalny
"""

from __future__ import annotations

import re
import tkinter as tk
import webbrowser
from tkinter import ttk

# Globalna lista otwartych okien zeby nie zostaly garbage-collected
_open_windows: list[tk.Toplevel] = []


def show_help(parent: tk.Misc, *, title: str, text: str) -> tk.Toplevel:
    """Pokazuje dialog Instrukcja w osobnym oknie. Zwraca utworzony Toplevel."""
    win = tk.Toplevel(parent)
    win.title(title)
    win.geometry("780x640")
    win.minsize(560, 420)

    try:
        win.transient(parent.winfo_toplevel())
    except (tk.TclError, AttributeError):
        pass

    # Glowny kontener z paddingiem
    container = ttk.Frame(win, padding=(12, 10, 12, 10))
    container.pack(fill="both", expand=True)

    # Tytul nad scrollowanym tekstem
    header = ttk.Label(
        container, text=title,
        font=("Segoe UI", 14, "bold"),
        anchor="w",
    )
    header.pack(fill="x", pady=(0, 8))

    # Text widget + scrollbar - pokazujemy markdown jako sformatowany tekst
    text_frame = ttk.Frame(container)
    text_frame.pack(fill="both", expand=True)

    txt = tk.Text(
        text_frame, wrap="word", padx=10, pady=10,
        bg="#fdfdfd", relief="flat", borderwidth=0,
        font=("Segoe UI", 10),
        cursor="arrow",
    )
    sb = ttk.Scrollbar(text_frame, orient="vertical", command=txt.yview)
    txt.configure(yscrollcommand=sb.set)
    txt.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    _setup_tags(txt)
    _render_markdown(txt, text)
    txt.configure(state="disabled")

    # Przyciski na dole
    btn_row = ttk.Frame(container)
    btn_row.pack(fill="x", pady=(8, 0))
    ttk.Button(btn_row, text="Zamknij", command=win.destroy).pack(side="right")

    # Esc zamyka
    win.bind("<Escape>", lambda _e: win.destroy())

    _open_windows.append(win)

    def _on_close() -> None:
        try:
            _open_windows.remove(win)
        except ValueError:
            pass
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", _on_close)

    # Wycentruj wzgledem rodzica
    try:
        win.update_idletasks()
        parent_root = parent.winfo_toplevel()
        px = parent_root.winfo_rootx()
        py = parent_root.winfo_rooty()
        pw = parent_root.winfo_width()
        ph = parent_root.winfo_height()
        ww = win.winfo_width()
        wh = win.winfo_height()
        x = px + max(0, (pw - ww) // 2)
        y = py + max(0, (ph - wh) // 2)
        win.geometry(f"+{x}+{y}")
    except tk.TclError:
        pass

    return win


def _setup_tags(txt: tk.Text) -> None:
    """Definiuje tagi formatujace dla naglowkow, code, link, etc."""
    txt.tag_configure("h1", font=("Segoe UI", 16, "bold"), foreground="#1a1a1a",
                      spacing1=12, spacing3=6)
    txt.tag_configure("h2", font=("Segoe UI", 13, "bold"), foreground="#222",
                      spacing1=10, spacing3=4)
    txt.tag_configure("h3", font=("Segoe UI", 11, "bold"), foreground="#333",
                      spacing1=6, spacing3=2)
    txt.tag_configure("bold", font=("Segoe UI", 10, "bold"))
    txt.tag_configure("italic", font=("Segoe UI", 10, "italic"))
    txt.tag_configure("code", font=("Consolas", 10), background="#f0f0f4",
                      relief="solid", borderwidth=0)
    txt.tag_configure("codeblock", font=("Consolas", 9), background="#f5f5f8",
                      lmargin1=20, lmargin2=20, spacing1=4, spacing3=4)
    txt.tag_configure("bullet", lmargin1=18, lmargin2=32, spacing3=2)
    txt.tag_configure("number", lmargin1=18, lmargin2=32, spacing3=2)
    txt.tag_configure("quote", lmargin1=18, lmargin2=18, foreground="#555",
                      font=("Segoe UI", 10, "italic"))
    txt.tag_configure("hr", foreground="#cccccc", justify="center")
    txt.tag_configure("link", foreground="#1a73e8", underline=True)


def _render_markdown(txt: tk.Text, content: str) -> None:
    """Bardzo prosty parser markdown - line-by-line. Niedoskonaly ale wystarczy."""
    lines = content.splitlines()
    in_codeblock = False

    for raw in lines:
        line = raw.rstrip()

        # Code block ```
        if line.strip().startswith("```"):
            in_codeblock = not in_codeblock
            txt.insert("end", "\n")
            continue
        if in_codeblock:
            txt.insert("end", line + "\n", "codeblock")
            continue

        # Naglowki
        if line.startswith("### "):
            txt.insert("end", line[4:] + "\n", "h3")
            continue
        if line.startswith("## "):
            txt.insert("end", line[3:] + "\n", "h2")
            continue
        if line.startswith("# "):
            txt.insert("end", line[2:] + "\n", "h1")
            continue

        # Horyzontalna linia
        if line.strip() in ("---", "***", "___"):
            txt.insert("end", "─" * 60 + "\n", "hr")
            continue

        # Quote
        if line.startswith("> "):
            txt.insert("end", line[2:] + "\n", "quote")
            continue

        # Bullet list
        m = re.match(r"^\s*[-*]\s+(.*)$", line)
        if m:
            _insert_inline(txt, "  •  " + m.group(1) + "\n", base_tag="bullet")
            continue

        # Numbered list
        m = re.match(r"^\s*(\d+)\.\s+(.*)$", line)
        if m:
            _insert_inline(txt, f"  {m.group(1)}.  {m.group(2)}\n", base_tag="number")
            continue

        # Pusta linia
        if not line:
            txt.insert("end", "\n")
            continue

        # Zwykly paragraf z inline formatting
        _insert_inline(txt, line + "\n")


# Inline regex - kolejnosc ma znaczenie (najpierw code, potem bold, link)
_INLINE_RE = re.compile(
    r"(`[^`]+`)|(\*\*[^*]+\*\*)|(\[[^\]]+\]\([^)]+\))",
)


def _insert_inline(txt: tk.Text, line: str, base_tag: str | None = None) -> None:
    """Wstawia jedna linie z obsluga inline `code`, **bold**, [link](url)."""
    pos = 0
    base_tags = (base_tag,) if base_tag else ()
    for m in _INLINE_RE.finditer(line):
        if m.start() > pos:
            txt.insert("end", line[pos:m.start()], base_tags)
        token = m.group(0)
        if token.startswith("`"):
            txt.insert("end", token[1:-1], (*base_tags, "code"))
        elif token.startswith("**"):
            txt.insert("end", token[2:-2], (*base_tags, "bold"))
        elif token.startswith("["):
            link_m = re.match(r"\[([^\]]+)\]\(([^)]+)\)", token)
            if link_m:
                label, url = link_m.group(1), link_m.group(2)
                tag_name = f"link_{id(label)}_{m.start()}"
                txt.insert("end", label, (*base_tags, "link", tag_name))
                txt.tag_bind(tag_name, "<Button-1>", lambda _e, u=url: webbrowser.open(u))
                txt.tag_bind(tag_name, "<Enter>", lambda _e, t=txt: t.configure(cursor="hand2"))
                txt.tag_bind(tag_name, "<Leave>", lambda _e, t=txt: t.configure(cursor="arrow"))
        pos = m.end()
    if pos < len(line):
        txt.insert("end", line[pos:], base_tags)
