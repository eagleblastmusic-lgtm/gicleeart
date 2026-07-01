"""Widok inline — podgląd poczty Gmail."""

from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from collections.abc import Callable
from tkinter import messagebox, scrolledtext, ttk

from .env_config import client_orders_base_dir, credentials_configured, gmail_imap_user
from .client_order_processor import scan_and_process_inbox
from .imap_client import (
    ImapConfigError,
    ImapFetchError,
    MailMessage,
    delete_inbox_messages,
    fetch_inbox_overview,
    fetch_message_body,
)

REFRESH_MS = 180_000  # 3 min


def build_view(parent: tk.Widget, on_back: Callable[[], None]) -> tk.Widget:
    root = ttk.Frame(parent)
    root.pack(fill="both", expand=True)

    state: dict[str, object] = {
        "messages": [],
        "refresh_job": None,
        "busy": False,
    }

    header = ttk.Frame(root, padding=(12, 10, 12, 6))
    header.pack(fill="x")
    ttk.Button(header, text="← Wróć", command=on_back).pack(side="left")
    ttk.Label(
        header,
        text="Poczta firmowa",
        font=("Segoe UI", 14, "bold"),
    ).pack(side="left", padx=(12, 0))

    account_var = tk.StringVar(value=gmail_imap_user())
    status_var = tk.StringVar(value="Kliknij Odśwież, aby pobrać wiadomości.")
    ttk.Label(header, textvariable=account_var, foreground="#555").pack(side="right")

    toolbar = ttk.Frame(root, padding=(12, 0, 12, 8))
    toolbar.pack(fill="x")
    ttk.Label(toolbar, textvariable=status_var, foreground="#444", wraplength=720).pack(
        side="left", anchor="w"
    )

    btn_row = ttk.Frame(toolbar)
    btn_row.pack(side="right")
    unseen_var = tk.BooleanVar(value=False)

    def open_gmail() -> None:
        webbrowser.open("https://mail.google.com/mail/u/0/#inbox")

    def show_setup_help() -> None:
        messagebox.showinfo(
            "Konfiguracja Gmail IMAP",
            "1. Konto Google → Bezpieczeństwo → weryfikacja 2-etapowa (włączona).\n"
            "2. Hasła aplikacji → wygeneruj hasło dla «Poczta».\n"
            "3. W pliku cursor-api/.env dodaj:\n\n"
            "   GMAIL_IMAP_USER=gicleeartpl@gmail.com\n"
            "   GMAIL_IMAP_APP_PASSWORD=xxxx xxxx xxxx xxxx\n"
            "   CLIENT_ORDERS_DIR=E:\\Firma\\1. Obrazy\\3. Klienci\n\n"
            "(spacje w haśle aplikacji są opcjonalne)\n\n"
            "Auto-pobieranie: maile „własna fotografia” → folder z plikami R2 + dane_klienta.txt\n\n"
            "Usuwanie przenosi wiadomości do Kosza Gmail (można odzyskać w Gmail).",
        )

    refresh_btn = ttk.Button(btn_row, text="Odśwież")
    refresh_btn.pack(side="left", padx=(0, 6))
    delete_btn = ttk.Button(btn_row, text="Usuń zaznaczone")
    delete_btn.pack(side="left", padx=(0, 6))
    ttk.Button(btn_row, text="Otwórz Gmail", command=open_gmail).pack(side="left", padx=(0, 6))
    ttk.Button(btn_row, text="Konfiguracja", command=show_setup_help).pack(side="left")

    ttk.Checkbutton(
        toolbar,
        text="Tylko nieprzeczytane",
        variable=unseen_var,
        command=lambda: refresh(),
    ).pack(anchor="w", padx=12, pady=(4, 0))

    auto_orders_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(
        toolbar,
        text="Auto-pobieraj „Własna fotografia” do folderu klientów",
        variable=auto_orders_var,
    ).pack(anchor="w", padx=12, pady=(0, 0))
    ttk.Label(
        toolbar,
        text=f"Folder: {client_orders_base_dir()}",
        foreground="#888",
        font=("Segoe UI", 8),
    ).pack(anchor="w", padx=12, pady=(0, 4))

    paned = ttk.Panedwindow(root, orient="horizontal")
    paned.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    left = ttk.Frame(paned)
    right = ttk.Frame(paned)
    paned.add(left, weight=2)
    paned.add(right, weight=3)

    cols = ("date", "from", "subject")
    tree = ttk.Treeview(left, columns=cols, show="headings", height=18, selectmode="extended")
    tree.heading("date", text="Data")
    tree.heading("from", text="Od")
    tree.heading("subject", text="Temat")
    tree.column("date", width=120, stretch=False)
    tree.column("from", width=180, stretch=False)
    tree.column("subject", width=320, stretch=True)
    tree.tag_configure("unread", font=("Segoe UI", 9, "bold"))

    tree_scroll = ttk.Scrollbar(left, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=tree_scroll.set)
    tree.pack(side="left", fill="both", expand=True)
    tree_scroll.pack(side="right", fill="y")

    meta_var = tk.StringVar(value="")
    ttk.Label(right, textvariable=meta_var, wraplength=480, justify="left").pack(
        anchor="w", padx=8, pady=(8, 4)
    )
    body = scrolledtext.ScrolledText(
        right, wrap="word", font=("Segoe UI", 10), height=20, state="disabled"
    )
    body.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    preview_actions = ttk.Frame(right)
    preview_actions.pack(fill="x", padx=8, pady=(0, 4))
    delete_one_btn = ttk.Button(preview_actions, text="Usuń tę wiadomość")
    delete_one_btn.pack(side="right")

    uid_to_msg: dict[str, MailMessage] = {}
    body_cache: dict[str, str] = {}
    body_load_uid: list[str | None] = [None]

    def show_message(msg: MailMessage | None, *, body_text: str | None = None) -> None:
        body.configure(state="normal")
        body.delete("1.0", "end")
        if msg is None:
            meta_var.set("")
            body.configure(state="disabled")
            return
        unread = " · NIEPRZECZYTANY" if msg.is_unseen else ""
        meta_var.set(f"{msg.from_addr}\n{msg.subject}\n{msg.date_display}{unread}")
        text = body_text if body_text is not None else msg.body_preview
        if not text:
            text = "Ładowanie treści…"
        body.insert("1.0", text)
        body.configure(state="disabled")

    def load_body_for_uid(uid: str) -> None:
        if uid in body_cache:
            msg = uid_to_msg.get(uid)
            if msg and tree.selection() and tree.selection()[0] == uid:
                show_message(msg, body_text=body_cache[uid])
            return
        body_load_uid[0] = uid
        msg = uid_to_msg.get(uid)
        if msg and tree.selection() and tree.selection()[0] == uid:
            show_message(msg, body_text="Ładowanie treści…")

        def worker() -> None:
            try:
                text = fetch_message_body(uid)
            except ImapFetchError as exc:
                text = str(exc)

            def done() -> None:
                body_cache[uid] = text
                if body_load_uid[0] == uid and tree.selection() and tree.selection()[0] == uid:
                    msg2 = uid_to_msg.get(uid)
                    if msg2:
                        show_message(msg2, body_text=text)

            root.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    def populate_tree(messages: list[MailMessage]) -> None:
        uid_to_msg.clear()
        for item in tree.get_children():
            tree.delete(item)
        for msg in messages:
            uid_to_msg[msg.uid] = msg
            from_short = msg.from_addr
            if len(from_short) > 36:
                from_short = from_short[:33] + "…"
            subj = msg.subject
            if len(subj) > 60:
                subj = subj[:57] + "…"
            tags = ("unread",) if msg.is_unseen else ()
            tree.insert("", "end", iid=msg.uid, values=(msg.date_display, from_short, subj), tags=tags)
        if messages:
            first = messages[0].uid
            tree.selection_set(first)
            tree.focus(first)
            show_message(messages[0])
            load_body_for_uid(first)
        else:
            show_message(None)

    def refresh() -> None:
        if state["busy"]:
            return
        if not credentials_configured():
            status_var.set("Brak GMAIL_IMAP_APP_PASSWORD w .env — kliknij Konfiguracja.")
            populate_tree([])
            return

        state["busy"] = True
        refresh_btn.configure(state="disabled")
        status_var.set("Pobieram wiadomości…")

        def worker() -> None:
            try:
                stats, messages = fetch_inbox_overview(unseen_only=unseen_var.get())
                order_results: list = []
                if auto_orders_var.get():
                    _, scan_msgs = fetch_inbox_overview(limit=80, unseen_only=False)
                    order_results = scan_and_process_inbox(scan_msgs)
                text = (
                    f"Nieprzeczytane: {stats['unseen']} · "
                    f"Wszystkich w INBOX: {stats['total']} · "
                    f"Pokazano: {len(messages)}"
                )
                new_orders = [
                    r for r in order_results
                    if r.ok and r.folder and "Już przetworzone" not in r.message
                ]
                if new_orders:
                    text += f" · Pobrano {len(new_orders)} zamówienie(a)"
                    text += f" → {new_orders[-1].folder}"

                def done() -> None:
                    state["busy"] = False
                    refresh_btn.configure(state="normal")
                    status_var.set(text)
                    state["messages"] = messages
                    body_cache.clear()
                    populate_tree(messages)
                    if new_orders:
                        messagebox.showinfo(
                            "Zamówienie klienta",
                            "\n".join(r.message for r in new_orders[-3:]),
                            parent=root,
                        )

                root.after(0, done)
            except (ImapConfigError, ImapFetchError) as exc:
                def err() -> None:
                    state["busy"] = False
                    refresh_btn.configure(state="normal")
                    status_var.set(str(exc))
                    populate_tree([])

                root.after(0, err)

        threading.Thread(target=worker, daemon=True).start()

    refresh_btn.configure(command=refresh)

    def selected_uids() -> list[str]:
        return list(tree.selection())

    def confirm_delete(uids: list[str]) -> bool:
        if not uids:
            messagebox.showinfo("Usuń", "Zaznacz co najmniej jedną wiadomość na liście.")
            return False
        subjects: list[str] = []
        for uid in uids[:5]:
            msg = uid_to_msg.get(uid)
            if msg:
                subjects.append(f"• {msg.subject}")
        extra = f"\n… i {len(uids) - 5} kolejnych" if len(uids) > 5 else ""
        body_text = "\n".join(subjects) + extra if subjects else ""
        n = len(uids)
        word = "wiadomość" if n == 1 else "wiadomości"
        prompt = f"Przenieść {n} {word} do Kosza Gmail?\n\n{body_text}\n\n(Można odzyskać w Gmail przez 30 dni.)"
        return messagebox.askyesno("Usuń wiadomości", prompt.strip(), icon="warning")

    def delete_messages(uids: list[str]) -> None:
        if state["busy"]:
            return
        if not credentials_configured():
            status_var.set("Brak GMAIL_IMAP_APP_PASSWORD w .env.")
            return
        if not confirm_delete(uids):
            return

        state["busy"] = True
        refresh_btn.configure(state="disabled")
        delete_btn.configure(state="disabled")
        delete_one_btn.configure(state="disabled")
        status_var.set(f"Usuwam {len(uids)} wiadomości…")

        def worker() -> None:
            try:
                deleted = delete_inbox_messages(uids)

                def done() -> None:
                    state["busy"] = False
                    refresh_btn.configure(state="normal")
                    delete_btn.configure(state="normal")
                    delete_one_btn.configure(state="normal")
                    if deleted < len(uids):
                        status_var.set(
                            f"Usunięto {deleted} z {len(uids)} — część mogła się nie udać. Odświeżam…"
                        )
                    else:
                        status_var.set(f"Usunięto {deleted} wiadomości. Odświeżam…")
                    refresh()

                root.after(0, done)
            except (ImapConfigError, ImapFetchError) as exc:
                def err() -> None:
                    state["busy"] = False
                    refresh_btn.configure(state="normal")
                    delete_btn.configure(state="normal")
                    delete_one_btn.configure(state="normal")
                    status_var.set(str(exc))

                root.after(0, err)

        threading.Thread(target=worker, daemon=True).start()

    def delete_selected() -> None:
        delete_messages(selected_uids())

    def delete_current() -> None:
        delete_messages(selected_uids())

    delete_btn.configure(command=delete_selected)
    delete_one_btn.configure(command=delete_current)

    def on_select(_event: object = None) -> None:
        sel = tree.selection()
        if not sel:
            return
        msg = uid_to_msg.get(sel[0])
        show_message(msg)
        load_body_for_uid(sel[0])

    tree.bind("<<TreeviewSelect>>", on_select)
    tree.bind("<Double-1>", lambda _e: open_gmail())
    tree.bind("<Delete>", lambda _e: delete_selected())

    def schedule_refresh() -> None:
        job = root.after(REFRESH_MS, auto_refresh)
        state["refresh_job"] = job

    def auto_refresh() -> None:
        refresh()
        schedule_refresh()

    def on_destroy(_event: object = None) -> None:
        job = state.get("refresh_job")
        if job:
            try:
                root.after_cancel(str(job))
            except tk.TclError:
                pass

    root.bind("<Destroy>", on_destroy, add="+")

    if credentials_configured():
        root.after(50, refresh)
        schedule_refresh()
    else:
        status_var.set("Skonfiguruj GMAIL_IMAP_APP_PASSWORD w .env (przycisk Konfiguracja).")

    return root
