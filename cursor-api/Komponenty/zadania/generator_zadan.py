"""Okno 'Generator zadan' - toplevel dialog.

Flow:
1. Przy otwarciu: pobieramy w tle sygnaly z Shopify (nowe produkty/autorzy/kolekcje)
   + sygnaly z kalendarza swiat (z holidays.py). Pokazujemy ich podsumowanie.
2. Uzytkownik wybiera dlugosc planowania (7/30/90 dni) i ile zadan wygenerowac.
3. Klik 'Prompt dla Opus / GPT' - buduje prompt z wszystkim kontekstem i kopiuje do schowka.
4. Uzytkownik wkleja do Opus/GPT, kopiuje JSON z zadaniami.
5. 'Wklej odpowiedz' -> 'Zapisz zadania' -> parsuje + dedup + zapisuje do tasks.json.
"""

from __future__ import annotations

import threading
import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk
from typing import Any

from Komponenty._shared.toast import show_toast

from . import holidays, prompts, shopify_signals, storage


def open_tasks_generator(
    parent: tk.Misc,
    *,
    on_saved: Callable[[int], None] | None = None,
) -> tk.Toplevel:
    dlg = tk.Toplevel(parent)
    dlg.title("Zadania - Generator planu marketingowego")
    dlg.geometry("1100x820")
    dlg.minsize(900, 700)
    try:
        dlg.transient(parent.winfo_toplevel())
    except (tk.TclError, AttributeError):
        pass

    state: dict[str, Any] = {
        "signals": {},
        "signals_text": "",
        "holidays_text": "",
    }

    root = ttk.Frame(dlg, padding=(10, 8))
    root.pack(fill="both", expand=True)

    # ---------- Parametry ----------
    params = ttk.LabelFrame(root, text="1. Parametry planu", padding=8)
    params.pack(fill="x", pady=(0, 6))

    grid = ttk.Frame(params)
    grid.pack(fill="x")
    grid.columnconfigure(1, weight=0)
    grid.columnconfigure(3, weight=0)

    ttk.Label(grid, text="Okres planowania:").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=3)
    period_var = tk.StringVar(value="miesiac (30 dni)")
    ttk.Combobox(
        grid, textvariable=period_var,
        values=["tydzien (7 dni)", "miesiac (30 dni)", "kwartal (90 dni)"],
        state="readonly", width=22,
    ).grid(row=0, column=1, sticky="w", pady=3)

    ttk.Label(grid, text="Liczba zadan:").grid(row=0, column=2, sticky="w", padx=(18, 6), pady=3)
    count_var = tk.IntVar(value=18)
    ttk.Spinbox(grid, from_=5, to=40, width=6, textvariable=count_var).grid(row=0, column=3, sticky="w", pady=3)

    ttk.Label(grid, text="Shopify look-back:").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=3)
    lookback_var = tk.IntVar(value=14)
    ttk.Spinbox(grid, from_=3, to=90, width=6, textvariable=lookback_var).grid(row=1, column=1, sticky="w", pady=3)
    ttk.Label(grid, text="dni (ile wstecz szukamy sygnalow)", foreground="#666").grid(row=1, column=2, columnspan=2, sticky="w")

    # ---------- Sygnaly ----------
    sig_frame = ttk.LabelFrame(root, text="2. Sygnaly (Shopify + kalendarz)", padding=8)
    sig_frame.pack(fill="both", expand=True, pady=(0, 6))

    status_var = tk.StringVar(value="Ladowanie sygnalow...")
    status_lbl = ttk.Label(sig_frame, textvariable=status_var, foreground="#1976d2")
    status_lbl.pack(anchor="w", pady=(0, 4))

    btn_row = ttk.Frame(sig_frame)
    btn_row.pack(fill="x", pady=(0, 4))
    ttk.Button(
        btn_row, text="🔄 Odswiez sygnaly",
        command=lambda: _reload_signals(dlg, state, status_var, status_lbl, summary_text, lookback_var.get(), period_var.get()),
    ).pack(side="left")

    sc = ttk.Frame(sig_frame)
    sc.pack(fill="both", expand=True)
    summary_text = tk.Text(sc, wrap="word", height=10, font=("Consolas", 9))
    ssb = ttk.Scrollbar(sc, orient="vertical", command=summary_text.yview)
    summary_text.configure(yscrollcommand=ssb.set)
    summary_text.pack(side="left", fill="both", expand=True)
    ssb.pack(side="right", fill="y")

    # ---------- Prompt ----------
    prompt_frame = ttk.LabelFrame(
        root, text="3. Prompt - klik kopiuje do schowka, wklej do Opus/GPT", padding=8,
    )
    prompt_frame.pack(fill="both", expand=True, pady=(0, 6))

    pbtn = ttk.Frame(prompt_frame)
    pbtn.pack(fill="x", pady=(0, 6))

    def _build_prompt(variant: str) -> None:
        if not state.get("signals_text") or not state.get("holidays_text"):
            messagebox.showwarning(
                "Brak sygnalow",
                "Nie pobrano jeszcze sygnalow. Poczekaj az ladowanie sie zakonczy lub kliknij 'Odswiez sygnaly'.",
                parent=dlg,
            )
            return
        planned_tasks = storage.load_tasks()
        planned_text = "\n".join(
            f"- {t.due_date or '(bez daty)'} | {t.channel} | {t.title}"
            for t in planned_tasks[-30:]  # ostatnie 30 zeby nie zapchac prompta
        )
        builder = prompts.build_tasks_prompt_opus if variant == "opus" else prompts.build_tasks_prompt_gpt
        text = builder(
            signals_text=state["signals_text"],
            holidays_text=state["holidays_text"],
            planned_text=planned_text,
            target_count=int(count_var.get()),
            period_label=period_var.get(),
        )
        prompt_text.delete("1.0", "end")
        prompt_text.insert("1.0", text)
        _copy_clipboard(dlg, text)

    ttk.Button(pbtn, text="📋 Prompt dla Claude Opus", command=lambda: _build_prompt("opus")).pack(side="left")
    ttk.Button(pbtn, text="📋 Prompt dla GPT", command=lambda: _build_prompt("gpt")).pack(side="left", padx=(6, 0))
    ttk.Button(
        pbtn, text="Kopiuj ponownie",
        command=lambda: _copy_clipboard(dlg, prompt_text.get("1.0", "end-1c")),
    ).pack(side="left", padx=(16, 0))

    pc = ttk.Frame(prompt_frame)
    pc.pack(fill="both", expand=True)
    prompt_text = tk.Text(pc, wrap="word", height=8, font=("Consolas", 9))
    psb = ttk.Scrollbar(pc, orient="vertical", command=prompt_text.yview)
    prompt_text.configure(yscrollcommand=psb.set)
    prompt_text.pack(side="left", fill="both", expand=True)
    psb.pack(side="right", fill="y")

    # ---------- Odpowiedz ----------
    resp_frame = ttk.LabelFrame(root, text="4. Odpowiedz z LLM (JSON z zadaniami)", padding=8)
    resp_frame.pack(fill="both", expand=True, pady=(0, 6))

    rbtn = ttk.Frame(resp_frame)
    rbtn.pack(fill="x", pady=(0, 6))
    ttk.Button(
        rbtn, text="📥 Wklej odpowiedz ze schowka",
        command=lambda: _paste(dlg, response_text),
    ).pack(side="left")
    ttk.Button(rbtn, text="Wyczysc", command=lambda: response_text.delete("1.0", "end")).pack(
        side="left", padx=(6, 0)
    )
    ttk.Button(
        rbtn, text="💾 Zapisz zadania",
        command=lambda: _save_tasks(dlg, response_text, on_saved),
    ).pack(side="right")

    rc = ttk.Frame(resp_frame)
    rc.pack(fill="both", expand=True)
    response_text = tk.Text(rc, wrap="word", height=8, font=("Consolas", 9))
    rsb = ttk.Scrollbar(rc, orient="vertical", command=response_text.yview)
    response_text.configure(yscrollcommand=rsb.set)
    response_text.pack(side="left", fill="both", expand=True)
    rsb.pack(side="right", fill="y")

    # ---------- Bottom ----------
    bottom = ttk.Frame(root)
    bottom.pack(fill="x", pady=(6, 0))
    ttk.Button(bottom, text="Zamknij", command=dlg.destroy).pack(side="right")
    dlg.bind("<Escape>", lambda _e: dlg.destroy())

    # Auto-load sygnaly przy starcie
    _reload_signals(dlg, state, status_var, status_lbl, summary_text, lookback_var.get(), period_var.get())
    return dlg


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _days_for_period_label(label: str) -> int:
    if "7" in label:
        return 7
    if "90" in label or "kwartal" in label.lower():
        return 90
    return 30


def _reload_signals(
    dlg: tk.Toplevel,
    state: dict[str, Any],
    status_var: tk.StringVar,
    status_lbl: ttk.Label,
    summary_text: tk.Text,
    lookback_days: int,
    period_label: str,
) -> None:
    status_var.set("Ladowanie sygnalow z Shopify...")
    status_lbl.configure(foreground="#1976d2")

    days_ahead = _days_for_period_label(period_label)
    upcoming = holidays.events_upcoming(days_ahead=days_ahead + 14)  # +14 dla lead_time
    holidays_text = holidays.format_events_for_prompt(upcoming)

    def _worker() -> None:
        try:
            signals = shopify_signals.aggregate_signals(days=int(lookback_days))
            signals_text = shopify_signals.format_signals_for_prompt(signals)
            storage.save_signals_cache(signals)

            def _ok() -> None:
                state["signals"] = signals
                state["signals_text"] = signals_text
                state["holidays_text"] = holidays_text
                summary_text.delete("1.0", "end")
                summary_text.insert(
                    "1.0",
                    f"=== SHOPIFY (ostatnie {lookback_days} dni) ===\n"
                    f"{signals_text}\n\n"
                    f"=== KALENDARZ (nadchodzace {days_ahead + 14} dni) ===\n"
                    f"{holidays_text}\n",
                )
                status_var.set(
                    f"✓ Sygnaly zaladowane: {len(signals.get('new_products') or [])} nowych produktow, "
                    f"{len(signals.get('new_artists') or [])} nowych autorow, {len(upcoming)} wydarzen."
                )
                status_lbl.configure(foreground="#1b5e20")

            dlg.after(0, _ok)
        except Exception as e:  # noqa: BLE001
            err = str(e)
            # Fallback: cache lokalny
            cache = storage.load_signals_cache()
            signals = cache.get("signals") or {}
            signals_text = shopify_signals.format_signals_for_prompt(signals) if signals else "(brak cache)"

            def _warn() -> None:
                state["signals"] = signals
                state["signals_text"] = signals_text
                state["holidays_text"] = holidays_text
                summary_text.delete("1.0", "end")
                summary_text.insert(
                    "1.0",
                    f"(Shopify nie odpowiada - uzyto cache)\n\n"
                    f"=== SHOPIFY (cache) ===\n{signals_text}\n\n"
                    f"=== KALENDARZ ===\n{holidays_text}\n",
                )
                status_var.set(f"⚠ Shopify niedostepny ({err[:60]}...). Uzyto cache.")
                status_lbl.configure(foreground="#ef6c00")

            dlg.after(0, _warn)

    threading.Thread(target=_worker, daemon=True).start()


def _copy_clipboard(dlg: tk.Toplevel, content: str) -> None:
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
        messagebox.showwarning("Pusty schowek", "Schowek pusty lub niedostepny.", parent=dlg)
        return
    target.delete("1.0", "end")
    target.insert("1.0", content)
    show_toast(dlg, "Wklejono ze schowka", duration_ms=1000)


def _save_tasks(
    dlg: tk.Toplevel,
    response_text: tk.Text,
    on_saved: Callable[[int], None] | None,
) -> None:
    raw = response_text.get("1.0", "end-1c").strip()
    if not raw:
        messagebox.showwarning("Brak odpowiedzi", "Wklej odpowiedz z LLM.", parent=dlg)
        return
    try:
        parsed = prompts.parse_tasks_response(raw)
    except ValueError as e:
        messagebox.showerror("Blad parsowania", str(e), parent=dlg)
        return

    new_tasks = [
        storage.Task.new(
            title=x["title"],
            description=x.get("description", ""),
            description_translations=x.get("description_translations") or {},
            channels=x.get("channels") or None,
            languages=x.get("languages") or None,
            target_markets=x.get("target_markets") or None,
            due_date=x.get("due_date", ""),
            priority=x.get("priority", "normal"),
            source=x.get("source", "llm"),
            source_ref=x.get("source_ref", ""),
            suggested_topic=x.get("suggested_topic", ""),
        )
        for x in parsed
    ]
    added = storage.add_tasks(new_tasks, dedup_key="title+due")
    total = len(storage.load_tasks())
    messagebox.showinfo(
        "Zapisano",
        f"Dodano {added} nowych zadan (pominieto duplikaty).\n"
        f"Lacznie w bazie: {total}.",
        parent=dlg,
    )
    if on_saved:
        try:
            on_saved(added)
        except Exception:  # noqa: BLE001
            pass
