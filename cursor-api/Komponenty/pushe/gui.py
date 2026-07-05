"""GUI: Pushe — Shopify dev/live + bezpieczny push gicleeart.git."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .config import GITHUB_DEFAULT_BRANCH, GITHUB_REMOTE_URL, SHOPIFY_DEV, SHOPIFY_LIVE
from .service import (
    commit_and_push_github,
    dry_run_github_push,
    push_shopify_dev,
    push_shopify_live,
    read_git_status,
    repo_root,
)

APP_TITLE = "Pushe"


def main() -> None:
    root = tk.Tk()
    root.title(APP_TITLE)
    position_toplevel_screen_center(root, 720, 640)
    root.minsize(560, 480)
    _build_ui(root)
    root.mainloop()


def _build_ui(host: tk.Misc) -> None:
    state: dict[str, object] = {"busy": False, "github_audit": None}

    header = ttk.Frame(host, padding=(14, 12, 14, 0))
    header.pack(fill="x")
    ttk.Label(header, text=APP_TITLE, font=("Segoe UI", 16, "bold")).pack(side="left")
    ttk.Label(
        header,
        text=f"Repo: {repo_root()}",
        foreground="#666",
        wraplength=420,
    ).pack(side="right")

    ttk.Label(
        host,
        text=(
            "Wdrażaj lokalny motyw na Shopify (dev = piaskownica, live = produkcja) "
            "albo bezpiecznie synchronizuj główne monorepo na GitHub."
        ),
        wraplength=660,
        justify="left",
        foreground="#555",
        padding=(14, 8, 14, 10),
    ).pack(fill="x")

    cards = ttk.Frame(host, padding=(14, 0, 14, 8))
    cards.pack(fill="x")

    def _card(parent: tk.Misc, title: str, hint: str, btn_text: str, command) -> ttk.Button:
        frame = ttk.LabelFrame(parent, text=title, padding=10)
        frame.pack(side="left", fill="both", expand=True, padx=(0, 6))
        ttk.Label(frame, text=hint, wraplength=200, foreground="#555", justify="left").pack(
            anchor="w", pady=(0, 8)
        )
        btn = ttk.Button(frame, text=btn_text, command=command)
        btn.pack(anchor="w")
        return btn

    github_frame = ttk.LabelFrame(host, text="Główne repo gicleeart", padding=10)
    github_frame.pack(fill="x", padx=14, pady=(0, 8))
    ttk.Label(
        github_frame,
        text=(
            f"Monorepo: motyw Shopify + cursor-api → {GITHUB_REMOTE_URL} "
            f"(branch: {GITHUB_DEFAULT_BRANCH})"
        ),
        foreground="#555",
        wraplength=640,
    ).pack(anchor="w", pady=(0, 4))
    ttk.Label(
        github_frame,
        text=(
            "Nie dotyczy: gicleeart-gpt ani gicleeapp. "
            "Snapshoty review dla ChatGPT wykonuj w komponencie Integracja z GPT."
        ),
        foreground="#666",
        wraplength=640,
        justify="left",
    ).pack(anchor="w", pady=(0, 6))

    msg_row = ttk.Frame(github_frame)
    msg_row.pack(fill="x", pady=(0, 8))
    ttk.Label(msg_row, text="Commit:", width=10).pack(side="left")
    commit_var = tk.StringVar(value="")
    ttk.Entry(msg_row, textvariable=commit_var).pack(side="left", fill="x", expand=True)

    log = scrolledtext.ScrolledText(host, height=14, wrap="word", font=("Consolas", 9))
    log.pack(fill="both", expand=True, padx=14, pady=(0, 8))

    status_var = tk.StringVar(value="Gotowy.")
    ttk.Label(host, textvariable=status_var, padding=(14, 0, 14, 4), foreground="#444").pack(
        anchor="w"
    )

    bottom = ttk.Frame(host, padding=(14, 0, 14, 12))
    bottom.pack(fill="x")
    refresh_btn = ttk.Button(bottom, text="Odśwież status git")
    refresh_btn.pack(side="left")
    ttk.Button(bottom, text="Zamknij", command=host.destroy).pack(side="right")

    buttons: list[ttk.Button] = []

    def _log(line: str) -> None:
        def append() -> None:
            log.insert("end", line + "\n")
            log.see("end")

        host.after(0, append)

    def _set_busy(busy: bool) -> None:
        state["busy"] = busy

        def apply() -> None:
            for btn in buttons:
                btn.configure(state="disabled" if busy else "normal")

        host.after(0, apply)

    def _finish_push(outcome, *, toast_ok: str = "") -> None:
        def done() -> None:
            _set_busy(False)
            if outcome.message:
                _log(outcome.message)
            if outcome.ok and getattr(outcome, "committed_files", None):
                for path in outcome.committed_files[:30]:
                    _log(f"  · {path}")
                if len(outcome.committed_files) > 30:
                    _log(f"  … i {len(outcome.committed_files) - 30} więcej")
            status_var.set(outcome.message or ("OK" if outcome.ok else "Błąd"))
            if outcome.ok and toast_ok:
                show_toast(host, toast_ok)
            elif not outcome.ok:
                messagebox.showerror(APP_TITLE, outcome.message or "Operacja nie powiodła się.", parent=host)

        host.after(0, done)

    def _run_task(worker, *, toast_ok: str = "") -> None:
        if state["busy"]:
            return
        _set_busy(True)
        status_var.set("Trwa…")
        threading.Thread(
            target=lambda: _finish_push(worker(), toast_ok=toast_ok),
            daemon=True,
        ).start()

    def _refresh_git() -> None:
        log.delete("1.0", "end")
        st = read_git_status(on_line=_log)
        if st.error:
            status_var.set(st.error)
            return
        status_var.set(
            f"Branch {st.branch} · origin {st.remote_url or '(brak)'} · "
            + ("zmiany lokalne" if st.dirty else "czysto")
        )

    refresh_btn.configure(command=_refresh_git)

    def _shopify_dev() -> None:
        _run_task(lambda: push_shopify_dev(on_line=_log), toast_ok="Dev theme push OK")

    def _shopify_live() -> None:
        if not messagebox.askyesno(
            APP_TITLE,
            "Wysłać motyw na LIVE (opublikowany sklep)?\n\n"
            "To nadpisze pliki na produkcyjnym motywie Shopify.",
            parent=host,
        ):
            return
        _run_task(lambda: push_shopify_live(on_line=_log), toast_ok="Live theme push OK")

    def _finish_github_dry_run(report) -> None:
        for line in report.format_report():
            _log(line)
        state["github_audit"] = report
        _set_busy(False)

        if report.blocked:
            status_var.set("Push gicleeart: zablokowany")
            messagebox.showerror(
                APP_TITLE,
                report.error or "Audyt zablokowany — sprawdź log.",
                parent=host,
            )
            return

        if report.no_changes:
            status_var.set("Brak zmian do bezpiecznego commita")
            messagebox.showinfo(
                APP_TITLE,
                "Brak zmian do bezpiecznego commita.\n"
                "Pliki runtime mogą pozostać lokalnie jako dirty — są pomijane.",
                parent=host,
            )
            return

        if not report.commit_candidates and not report.deletable_files:
            status_var.set("Brak zmian")
            messagebox.showinfo(APP_TITLE, "Brak zmian do commita.", parent=host)
            return

        preview_lines: list[str] = []
        if report.new_files:
            preview_lines.append(f"Nowe ({len(report.new_files)}):")
            for path in report.new_files[:15]:
                preview_lines.append(f"  + {path}")
            if len(report.new_files) > 15:
                preview_lines.append(f"  … i {len(report.new_files) - 15} więcej")
        if report.modified_files:
            preview_lines.append(f"Zmienione ({len(report.modified_files)}):")
            for path in report.modified_files[:15]:
                preview_lines.append(f"  M {path}")
            if len(report.modified_files) > 15:
                preview_lines.append(f"  … i {len(report.modified_files) - 15} więcej")
        if report.deletable_files:
            preview_lines.append(f"Usunięte ({len(report.deletable_files)}):")
            for path in report.deletable_files[:15]:
                preview_lines.append(f"  D {path}")
            if len(report.deletable_files) > 15:
                preview_lines.append(f"  … i {len(report.deletable_files) - 15} więcej")

        include_deletions = False
        if report.deletable_files:
            include_deletions = messagebox.askyesno(
                APP_TITLE,
                f"Wykryto {len(report.deletable_files)} usuniętych plików.\n\n"
                "Uwzględnić je w commicie?",
                parent=host,
            )

        if not report.commit_candidates and not include_deletions:
            status_var.set("Brak plików do commita")
            messagebox.showinfo(APP_TITLE, "Brak plików do commita (bez usunięć).", parent=host)
            return

        if not messagebox.askyesno(
            APP_TITLE,
            "Commit + push głównego repo gicleeart?\n\n"
            f"Repo: eagleblastmusic-lgtm/gicleeart ({report.branch})\n"
            f"Commit: {report.commit_message}\n"
            f"Pliki: {len(report.commit_candidates)}"
            + (f" + {len(report.deletable_files)} usunięć" if include_deletions else "")
            + "\n\n"
            + "\n".join(preview_lines),
            parent=host,
        ):
            status_var.set("Push gicleeart anulowany.")
            return

        _run_github_commit_push(include_deletions)

    def _run_github_commit_push(include_deletions: bool) -> None:
        report = state.get("github_audit")
        if report is None:
            return
        _set_busy(True)
        status_var.set("Commit + push gicleeart…")

        def work():
            return commit_and_push_github(report, include_deletions=include_deletions, on_line=_log)

        threading.Thread(
            target=lambda: _finish_push(work(), toast_ok="Główne repo gicleeart OK"),
            daemon=True,
            name="pushe-github-push",
        ).start()

    def _github() -> None:
        if state["busy"]:
            return
        state["github_audit"] = None
        _set_busy(True)
        status_var.set("Sprawdzam główne repo gicleeart…")
        log.delete("1.0", "end")
        msg = commit_var.get().strip()

        def run() -> None:
            report = dry_run_github_push(commit_message=msg or None, on_line=_log)
            host.after(0, lambda: _finish_github_dry_run(report))

        threading.Thread(target=run, daemon=True, name="pushe-github-dry-run").start()

    btn_dev = _card(
        cards,
        str(SHOPIFY_DEV["label"]),
        str(SHOPIFY_DEV["hint"]),
        "Push dev…",
        _shopify_dev,
    )
    btn_live = _card(
        cards,
        str(SHOPIFY_LIVE["label"]),
        str(SHOPIFY_LIVE["hint"]),
        "Push live…",
        _shopify_live,
    )
    buttons.extend([btn_dev, btn_live])

    gh_btn = ttk.Button(
        github_frame,
        text="Sprawdź i push główne repo…",
        command=_github,
    )
    gh_btn.pack(anchor="w")
    buttons.append(gh_btn)

    host.after(120, _refresh_git)


if __name__ == "__main__":
    main()
