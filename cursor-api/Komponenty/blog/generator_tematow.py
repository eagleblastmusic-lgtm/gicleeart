"""Okno 'Generator tematow' - toplevel dialog.

Flow:
1. Przy otwarciu: zaciagamy obecne tytuly z Shopify (background thread) + lista obecnych propozycji.
2. Klikniecie "Prompt Opus" / "Prompt GPT":
   - buduje prompt uwzgledniajacy obecne tytuly + dotychczasowe propozycje,
   - AUTOKOPIUJE prompt do schowka,
   - pokazuje w textarea.
3. Uzytkownik wkleja do Cursor/Claude/GPT, kopiuje odpowiedz.
4. "Wklej odpowiedz ze schowka" (autowklejanie).
5. "Zapisz propozycje" - parsuje JSON, dopisuje do topics.json (pomijajac duplikaty).
"""

from __future__ import annotations

import threading
import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from Komponenty._shared.toast import show_toast

from . import prompts, shopify_blog, storage


def open_topics_generator(
    parent: tk.Misc,
    *,
    on_saved: Callable[[int], None] | None = None,
) -> tk.Toplevel:
    dlg = tk.Toplevel(parent)
    dlg.title("Blog - Generator tematow")
    dlg.geometry("1000x720")
    dlg.minsize(820, 600)
    try:
        dlg.transient(parent.winfo_toplevel())
    except (tk.TclError, AttributeError):
        pass

    status_var = tk.StringVar(value="Ladowanie obecnych tytulow...")
    existing_titles: list[str] = []

    # ---------- layout ----------
    root = ttk.Frame(dlg, padding=(10, 8))
    root.pack(fill="both", expand=True)

    info = ttk.Frame(root)
    info.pack(fill="x", pady=(0, 6))
    ttk.Label(info, text="Status:").pack(side="left")
    status_label = ttk.Label(info, textvariable=status_var, foreground="#1976d2")
    status_label.pack(side="left", padx=(6, 0))
    ttk.Button(
        info, text="🔄 Odswiez liste z Shopify",
        command=lambda: _reload_titles(dlg, status_var, status_label, existing_titles),
    ).pack(side="right")

    # Prompt section
    prompt_frame = ttk.LabelFrame(
        root, text="1. Prompt - klik kopiuje do schowka, wklej do Opus/GPT", padding=8,
    )
    prompt_frame.pack(fill="both", expand=True, pady=(0, 6))

    btn_row = ttk.Frame(prompt_frame)
    btn_row.pack(fill="x", pady=(0, 6))
    ttk.Button(
        btn_row, text="📋 Prompt dla Claude Opus",
        command=lambda: _build_copy(dlg, prompt_text, existing_titles, variant="opus"),
    ).pack(side="left")
    ttk.Button(
        btn_row, text="📋 Prompt dla GPT",
        command=lambda: _build_copy(dlg, prompt_text, existing_titles, variant="gpt"),
    ).pack(side="left", padx=(6, 0))
    ttk.Button(
        btn_row, text="Kopiuj ponownie",
        command=lambda: _copy(dlg, prompt_text.get("1.0", "end-1c")),
    ).pack(side="left", padx=(16, 0))

    pc = ttk.Frame(prompt_frame)
    pc.pack(fill="both", expand=True)
    prompt_text = tk.Text(pc, wrap="word", height=9, font=("Consolas", 9))
    prompt_sb = ttk.Scrollbar(pc, orient="vertical", command=prompt_text.yview)
    prompt_text.configure(yscrollcommand=prompt_sb.set)
    prompt_text.pack(side="left", fill="both", expand=True)
    prompt_sb.pack(side="right", fill="y")

    # Response section
    resp_frame = ttk.LabelFrame(
        root, text="2. Odpowiedz z LLM (JSON z 10 propozycjami)", padding=8,
    )
    resp_frame.pack(fill="both", expand=True, pady=6)

    resp_btn_row = ttk.Frame(resp_frame)
    resp_btn_row.pack(fill="x", pady=(0, 6))
    ttk.Button(
        resp_btn_row, text="📥 Wklej odpowiedz ze schowka",
        command=lambda: _paste(dlg, response_text),
    ).pack(side="left")
    ttk.Button(
        resp_btn_row, text="Wyczysc",
        command=lambda: response_text.delete("1.0", "end"),
    ).pack(side="left", padx=(6, 0))
    ttk.Button(
        resp_btn_row, text="💾 Zapisz propozycje",
        command=lambda: _save_proposals(dlg, response_text, on_saved),
    ).pack(side="right")

    rc = ttk.Frame(resp_frame)
    rc.pack(fill="both", expand=True)
    response_text = tk.Text(rc, wrap="word", height=9, font=("Consolas", 9))
    rsb = ttk.Scrollbar(rc, orient="vertical", command=response_text.yview)
    response_text.configure(yscrollcommand=rsb.set)
    response_text.pack(side="left", fill="both", expand=True)
    rsb.pack(side="right", fill="y")

    btm = ttk.Frame(root)
    btm.pack(fill="x", pady=(6, 0))
    ttk.Button(btm, text="Zamknij", command=dlg.destroy).pack(side="right")

    dlg.bind("<Escape>", lambda _e: dlg.destroy())

    # Start ladowania obecnych tytulow w tle
    _reload_titles(dlg, status_var, status_label, existing_titles)

    return dlg


# ---------------------------------------------------------------------------

def _reload_titles(
    dlg: tk.Toplevel,
    status_var: tk.StringVar,
    status_label: ttk.Label,
    existing_titles: list[str],
) -> None:
    status_var.set("Ladowanie obecnych tytulow z Shopify...")
    status_label.configure(foreground="#1976d2")

    def _worker() -> None:
        try:
            shop, token = shopify_blog.load_session()
            articles = shopify_blog.list_all_articles(shop, token)
            storage.save_articles_cache(articles)
            titles = [str(a.get("title") or "") for a in articles if a.get("title")]

            def _ok() -> None:
                existing_titles.clear()
                existing_titles.extend(titles)
                status_var.set(f"Zaladowano {len(titles)} obecnych tytulow.")
                status_label.configure(foreground="#1b5e20")

            dlg.after(0, _ok)
        except Exception as e:  # noqa: BLE001
            # Fallback: cache lokalny
            cache = storage.load_articles_cache()
            titles = [str(a.get("title") or "") for a in (cache.get("articles") or []) if a.get("title")]
            err = str(e)

            def _warn() -> None:
                existing_titles.clear()
                existing_titles.extend(titles)
                if titles:
                    status_var.set(
                        f"⚠ Nie udalo sie pobrac z Shopify ({err[:50]}...). Uzyto cache: {len(titles)} tytulow."
                    )
                    status_label.configure(foreground="#ef6c00")
                else:
                    status_var.set(f"⚠ Brak polaczenia z Shopify: {err[:80]}")
                    status_label.configure(foreground="#c62828")

            dlg.after(0, _warn)

    threading.Thread(target=_worker, daemon=True).start()


def _build_copy(
    dlg: tk.Toplevel,
    prompt_text: tk.Text,
    existing_titles: list[str],
    *,
    variant: str,
) -> None:
    planned = [t.title for t in storage.load_topics()]
    if variant == "opus":
        prompt = prompts.build_topics_prompt_opus(existing_titles, planned)
    else:
        prompt = prompts.build_topics_prompt_gpt(existing_titles, planned)
    prompt_text.delete("1.0", "end")
    prompt_text.insert("1.0", prompt)
    _copy(dlg, prompt)


def _copy(dlg: tk.Toplevel, content: str) -> None:
    if not content.strip():
        return
    try:
        dlg.clipboard_clear()
        dlg.clipboard_append(content)
        dlg.update()
    except tk.TclError:
        return
    show_toast(dlg, "Skopiowano do schowka", duration_ms=1200)


def _paste(dlg: tk.Toplevel, target: tk.Text) -> None:
    try:
        content = dlg.clipboard_get()
    except tk.TclError:
        messagebox.showwarning("Pusty schowek", "Schowek jest pusty lub niedostepny.", parent=dlg)
        return
    target.delete("1.0", "end")
    target.insert("1.0", content)
    show_toast(dlg, "Wklejono ze schowka", duration_ms=1000)


def _save_proposals(
    dlg: tk.Toplevel,
    response_text: tk.Text,
    on_saved: Callable[[int], None] | None,
) -> None:
    raw = response_text.get("1.0", "end-1c").strip()
    if not raw:
        messagebox.showwarning("Brak odpowiedzi", "Wklej odpowiedz z LLM.", parent=dlg)
        return
    try:
        proposals = prompts.parse_topics_response(raw)
    except ValueError as e:
        messagebox.showerror("Blad parsowania", str(e), parent=dlg)
        return

    new_topics = [
        storage.TopicProposal.new(
            title=p["title"],
            reason=p.get("reason", ""),
            keywords=p.get("keywords", []),
        )
        for p in proposals
    ]
    added = storage.add_topics(new_topics)
    total = len(storage.load_topics())
    messagebox.showinfo(
        "Zapisano",
        f"Dodano {added} nowych propozycji (pominieto duplikaty).\nLacznie w bazie: {total}.",
        parent=dlg,
    )
    if on_saved:
        try:
            on_saved(added)
        except Exception:  # noqa: BLE001
            pass
