"""GUI: Integracja z GPT — sync lustra, nagrania, schowek wiadomości."""

from __future__ import annotations

import threading
import tkinter as tk
from datetime import UTC, datetime
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from Komponenty._shared.theme_dev_gui import open_theme_dev_preview
from Komponenty._shared.tk_scroll import bind_mousewheel_to_canvas
from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .config import GPT_KNOWLEDGE_PACK_VERSION, load_config, save_config
from .handoff import (
    build_conversation_start_prompt,
    build_plan_evaluation_message,
    build_review_request,
    build_zip_read_github_followup_message,
    build_confirmation_checklist_message,
)
from .mirror import build_review_package, sync_theme_to_mirror
from .record import record_preview, record_video_to_disk
from .review_session import ReviewSession
from .zip_knowledge import (
    build_starter_knowledge_zip,
    copy_knowledge_zip_to_clipboard,
    copy_zip_path_to_clipboard,
    gpt_starter_files_dir,
    import_knowledge_zip,
    knowledge_zip_path,
    list_starter_markdown_files,
    read_compact_instructions,
    read_start_message,
    read_start_message_draft,
    write_start_message,
)

APP_TITLE = "Integracja z GPT"


class IntegracjaGptApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        position_toplevel_screen_center(self.root, 960, 820)
        self.root.minsize(760, 620)

        self._cfg = load_config()
        self._busy = False
        self._full_cycle_prompt_ready = False
        self._obs_recording = False
        self._main_repo_audit = None
        self._gicleeart_audit = None
        self._gicleeart_full_cycle_on_success = None
        self._build_ui()
        self._load_cfg_into_form()

    def _build_scrollable_root(self) -> ttk.Frame:
        host = ttk.Frame(self.root)
        host.pack(fill="both", expand=True)

        canvas = tk.Canvas(
            host,
            highlightthickness=0,
            borderwidth=0,
            background=self.root.cget("background"),
        )
        scrollbar = ttk.Scrollbar(host, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        content = ttk.Frame(canvas)
        content_window = canvas.create_window((0, 0), window=content, anchor="nw")

        def update_scrollregion(_event=None) -> None:
            bounds = canvas.bbox("all")
            if bounds is not None:
                canvas.configure(scrollregion=bounds)

        def fit_content_width(event: tk.Event) -> None:
            canvas.itemconfigure(content_window, width=event.width)
            update_scrollregion()

        content.bind("<Configure>", update_scrollregion)
        canvas.bind("<Configure>", fit_content_width)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        bind_mousewheel_to_canvas(canvas, content)

        self._page_canvas = canvas
        self._page_content = content
        return content

    def _build_ui(self) -> None:
        page = self._build_scrollable_root()

        header = ttk.Frame(page, padding=(12, 10, 12, 0))
        header.pack(fill="x")
        ttk.Label(header, text=APP_TITLE, font=("Segoe UI", 16, "bold")).pack(side="left")

        hint = ttk.Label(
            page,
            text=(
                "Lustro motywu na osobne repo GitHub dla Custom GPT. "
                "Cursor wykonuje kod lokalnie; po sesji: nagraj podgląd → push → wklej wiadomość review do ChatGPT."
            ),
            padding=(12, 4, 12, 8),
            foreground="#555",
            wraplength=920,
        )
        hint.pack(fill="x")

        cfg_frame = ttk.LabelFrame(page, text="Konfiguracja repo GPT", padding=10)
        cfg_frame.pack(fill="x", padx=12, pady=(0, 8))

        row1 = ttk.Frame(cfg_frame)
        row1.pack(fill="x", pady=(0, 6))
        ttk.Label(row1, text="URL repo:", width=12).pack(side="left")
        self.remote_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.remote_var).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Label(row1, text="Branch:").pack(side="left")
        self.branch_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.branch_var, width=10).pack(side="left", padx=(4, 0))

        row2 = ttk.Frame(cfg_frame)
        row2.pack(fill="x", pady=(0, 6))
        self.prefer_local_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            row2,
            text="Nagrywaj z localhost (theme dev)",
            variable=self.prefer_local_var,
        ).pack(side="left")
        ttk.Label(row2, text="Scroll (s):").pack(side="left", padx=(16, 4))
        self.scroll_var = tk.StringVar(value="22")
        ttk.Entry(row2, textvariable=self.scroll_var, width=6).pack(side="left")

        row2b = ttk.Frame(cfg_frame)
        row2b.pack(fill="x", pady=(0, 6))
        ttk.Label(row2b, text="Hasło sklepu:", width=12).pack(side="left")
        self.store_password_var = tk.StringVar()
        ttk.Entry(row2b, textvariable=self.store_password_var, show="•").pack(
            side="left", fill="x", expand=True, padx=(0, 8)
        )
        ttk.Label(
            row2b,
            text="password page — dla theme dev (lokalnie, nie trafia do GPT repo)",
            foreground="#666",
        ).pack(side="left")

        row2c = ttk.Frame(cfg_frame)
        row2c.pack(fill="x", pady=(0, 6))
        ttk.Label(row2c, text="OBS WebSocket:", width=12).pack(side="left")
        self.obs_password_var = tk.StringVar()
        ttk.Entry(row2c, textvariable=self.obs_password_var, show="•", width=18).pack(side="left", padx=(0, 8))
        ttk.Label(row2c, text="Port:").pack(side="left")
        self.obs_port_var = tk.StringVar(value="")
        ttk.Entry(row2c, textvariable=self.obs_port_var, width=6).pack(side="left", padx=(4, 12))
        ttk.Label(
            row2c,
            text="Hasło auto z OBS (AppData) jeśli puste; port domyślnie 4455",
            foreground="#666",
        ).pack(side="left")

        session_frame = ttk.LabelFrame(page, text="Sesja review (Faza A)", padding=10)
        session_frame.pack(fill="x", padx=12, pady=(0, 8))

        goal_row = ttk.Frame(session_frame)
        goal_row.pack(fill="x", pady=(0, 6))
        ttk.Label(goal_row, text="Cel review / sesji:", width=18).pack(side="left", anchor="n")
        self.review_goal_var = tk.StringVar()
        ttk.Entry(goal_row, textvariable=self.review_goal_var).pack(side="left", fill="x", expand=True)

        issues_row = ttk.Frame(session_frame)
        issues_row.pack(fill="x", pady=(0, 6))
        ttk.Label(issues_row, text="Znane problemy:", width=18).pack(side="left", anchor="n")
        self.known_issues_var = tk.StringVar()
        ttk.Entry(
            issues_row,
            textvariable=self.known_issues_var,
        ).pack(side="left", fill="x", expand=True)
        ttk.Label(
            session_frame,
            text="Jedna linia = jeden punkt. Commit: review: <cel> <data> (lub fallback theme snapshot).",
            foreground="#666",
            wraplength=900,
        ).pack(anchor="w")

        row3 = ttk.Frame(cfg_frame)
        row3.pack(fill="x")
        ttk.Button(row3, text="Zapisz ustawienia", command=self._save_settings).pack(side="right")

        actions = ttk.LabelFrame(page, text="Akcje", padding=10)
        actions.pack(fill="x", padx=12, pady=(0, 8))

        btn_row1 = ttk.Frame(actions)
        btn_row1.pack(fill="x", pady=(0, 6))
        ttk.Button(btn_row1, text="Theme dev…", command=self._open_theme_dev).pack(side="left", padx=(0, 6))
        self._obs_record_btn = ttk.Button(
            btn_row1,
            text="Nagraj (OBS)",
            command=self._toggle_obs_recording,
        )
        self._obs_record_btn.pack(side="left", padx=(0, 6))
        self._bind_tooltip(
            self._obs_record_btn,
            "Przełącznik nagrywania OBS.\n"
            "Start: uruchamia OBS z auto-nagrywaniem (--startrecording + WebSocket).\n"
            "Stop: StopRecord → latest-desktop.webm w review-demos.",
        )
        ttk.Button(btn_row1, text="Nagraj podgląd", command=self._run_record).pack(side="left", padx=(0, 6))
        ttk.Button(btn_row1, text="Utwórz wideo na dysku", command=self._run_video_to_disk).pack(
            side="left", padx=(0, 6)
        )
        self.include_recordings_var = tk.BooleanVar(value=True)
        rec_cb = ttk.Checkbutton(
            btn_row1,
            text="Nagrania w paczce (Playwright)",
            variable=self.include_recordings_var,
        )
        rec_cb.pack(side="left", padx=(0, 6))
        self._bind_tooltip(
            rec_cb,
            "Zaznaczone: Pełny cykl nagrywa automatycznie (Playwright).\n"
            "Odznaczone: użyj «Nagraj (OBS)» / własne pliki wideo przed Pełnym cyklem.",
        )
        btn_review = ttk.Button(btn_row1, text="Review package only", command=self._run_review_package)
        btn_review.pack(side="left", padx=(0, 6))
        btn_sync = ttk.Button(btn_row1, text="Sync lustra (lokalnie)", command=self._run_sync_only)
        btn_sync.pack(side="left", padx=(0, 6))
        ttk.Button(btn_row1, text="Pełny cykl", command=self._run_full_cycle).pack(side="left")

        btn_row1_hint = ttk.Frame(actions)
        btn_row1_hint.pack(fill="x", pady=(0, 6))
        ttk.Label(
            btn_row1_hint,
            text=(
                "Sync lustra — kopiuje allowlistowane pliki motywu i generuje notatki/manifest. "
                "Review package only — lokalna paczka review, opcjonalnie z nagraniami/screenshotami, bez pushu."
            ),
            foreground="#666",
            wraplength=920,
            font=("Segoe UI", 9),
        ).pack(anchor="w")

        self._bind_tooltip(
            btn_sync,
            "Sync lustra — kopiuje allowlistowane pliki motywu i generuje notatki/manifest.",
        )
        self._bind_tooltip(
            btn_review,
            "Review package only — lokalna paczka review, opcjonalnie z nagraniami/screenshotami, "
            "bez pushu do GitHuba.",
        )

        btn_row2 = ttk.Frame(actions)
        btn_row2.pack(fill="x")
        ttk.Button(
            btn_row2,
            text="Kopiuj: prośba o ocenę planu",
            command=lambda: self._copy_text(build_plan_evaluation_message()),
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            btn_row2,
            text="Kopiuj: wiadomość review",
            command=self._copy_review_message,
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            btn_row2,
            text=f"Kopiuj: compact instructions ({GPT_KNOWLEDGE_PACK_VERSION})",
            command=self._copy_compact_instructions,
        ).pack(side="left", padx=(0, 6))
        ttk.Button(btn_row2, text="Otwórz review-demos", command=self._open_review_demos).pack(side="left")
        ttk.Button(btn_row2, text="Otwórz folder nagrań", command=self._open_videos_dir).pack(
            side="left", padx=(6, 0)
        )

        btn_row3 = ttk.Frame(actions)
        btn_row3.pack(fill="x", pady=(8, 0))
        ttk.Button(btn_row3, text="Okno rozmowy", command=self._open_conversation_window).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(btn_row3, text="Załaduj zip do rozmowy", command=self._load_knowledge_zip).pack(
            side="left", padx=(0, 6)
        )
        self._copy_start_prompt_btn = ttk.Button(
            btn_row3,
            text="Skopiuj prompt rozpoczęcia rozmowy",
            command=self._copy_conversation_start_prompt,
            state="disabled",
        )
        self._copy_start_prompt_btn.pack(side="left", padx=(0, 6))
        self.zip_status_var = tk.StringVar(value="ZIP wiedzy: nie załadowany")
        ttk.Label(btn_row3, textvariable=self.zip_status_var, foreground="#666").pack(side="left", padx=(8, 0))

        repos_frame = ttk.LabelFrame(page, text="Repozytoria GitHub GicleeArt", padding=10)
        repos_frame.pack(fill="x", padx=12, pady=(0, 8))
        ttk.Label(
            repos_frame,
            text=(
                "Wybierz cel świadomie: repo główne przechowuje pełny projekt, "
                "a repo robocze jest odseparowanym snapshotem motywu do pracy i review z GPT."
            ),
            foreground="#555",
            wraplength=920,
        ).pack(anchor="w", pady=(0, 8))

        main_repo_card = ttk.Frame(repos_frame, padding=(8, 6))
        main_repo_card.pack(fill="x")
        ttk.Label(
            main_repo_card,
            text="Repo główne",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            main_repo_card,
            text=(
                "eagleblastmusic-lgtm/gicleeart  •  branch master\n"
                "Pełny lokalny projekt: motyw Shopify, GicleeApp i narzędzia. "
                "Pliki runtime, logi i sekrety są pomijane albo blokują push."
            ),
            foreground="#555",
            wraplength=900,
            justify="left",
        ).pack(anchor="w", pady=(2, 6))
        main_repo_row = ttk.Frame(main_repo_card)
        main_repo_row.pack(fill="x")
        self._main_repo_btn = ttk.Button(
            main_repo_row,
            text="Sprawdź i push do repo głównego",
            command=self._start_main_repo_push,
        )
        self._main_repo_btn.pack(side="left")
        ttk.Label(
            main_repo_row,
            text="Dry-run → audyt → potwierdzenie → commit + push (master)",
            foreground="#666",
        ).pack(side="left", padx=(10, 0))

        ttk.Separator(repos_frame, orient="horizontal").pack(fill="x", pady=8)

        work_repo_card = ttk.Frame(repos_frame, padding=(8, 6))
        work_repo_card.pack(fill="x")
        ttk.Label(
            work_repo_card,
            text="Repo robocze GPT",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            work_repo_card,
            text=(
                "eagleblastmusic-lgtm/gicleeart-gpt  •  branch main\n"
                "Snapshot do pracy z GPT: allowlistowany motyw → .gpt_mirror. "
                "Nie zmienia repo głównego ani Shopify dev/live."
            ),
            foreground="#555",
            wraplength=900,
            justify="left",
        ).pack(anchor="w", pady=(2, 6))
        work_repo_row = ttk.Frame(work_repo_card)
        work_repo_row.pack(fill="x")
        self._gicleeart_btn = ttk.Button(
            work_repo_row,
            text="Sprawdź i push do repo roboczego GPT",
            command=self._start_gicleeart_gpt_push,
        )
        self._gicleeart_btn.pack(side="left")
        ttk.Label(
            work_repo_row,
            text="Dry-run → audyt → potwierdzenie → commit + push (main)",
            foreground="#666",
        ).pack(side="left", padx=(10, 0))

        self.status_var = tk.StringVar(value="Gotowy.")
        ttk.Label(page, textvariable=self.status_var, padding=(12, 0, 12, 4)).pack(fill="x")

        log_frame = ttk.LabelFrame(page, text="Log", padding=8)
        log_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.log = scrolledtext.ScrolledText(log_frame, height=18, wrap="word", font=("Consolas", 9))
        self.log.pack(fill="both", expand=True)

        self._append_log(
            "Utwórz puste repo na GitHub (np. gicleeart-gpt), wklej URL powyżej, Zapisz.\n"
            "Nagrywanie: Theme dev → «Nagraj (OBS)» → przewiń stronę → ten sam przycisk («Zatrzymaj») → Pełny cykl.\n"
            "Playwright (opcjonalnie): npm install && npx playwright install chromium w korzeniu motywu."
        )

    def _load_cfg_into_form(self) -> None:
        from Komponenty.stronaglowna.service import resolve_storefront_password

        c = self._cfg
        self.remote_var.set(c.remote_url)
        self.branch_var.set(c.branch)
        self.prefer_local_var.set(c.prefer_local_theme_dev)
        self.scroll_var.set(str(c.record_scroll_seconds))
        self.store_password_var.set(resolve_storefront_password())
        self.obs_password_var.set(c.obs_websocket_password)
        self.obs_port_var.set(str(c.obs_websocket_port) if c.obs_websocket_port else "")
        if c.last_push_sha:
            self.status_var.set(f"Ostatni push: {c.last_push_sha[:12]} ({c.last_push_at})")
        self._refresh_zip_status()

    def _refresh_zip_status(self) -> None:
        c = self._cfg
        if knowledge_zip_path():
            name = c.knowledge_zip_name or "gpt_knowledge.zip"
            when = f" ({c.knowledge_zip_loaded_at})" if c.knowledge_zip_loaded_at else ""
            self.zip_status_var.set(f"ZIP wiedzy: {name}{when}")
        else:
            self.zip_status_var.set("ZIP wiedzy: nie załadowany")
        self._update_start_prompt_button()

    def _update_start_prompt_button(self) -> None:
        if self._full_cycle_prompt_ready and knowledge_zip_path():
            self._copy_start_prompt_btn.configure(state="normal")
        else:
            self._copy_start_prompt_btn.configure(state="disabled")

    def _cfg_from_form(self):
        from .config import GptConfig

        try:
            scroll = float(self.scroll_var.get().replace(",", "."))
        except ValueError:
            scroll = 22.0
        try:
            obs_port = int(self.obs_port_var.get().strip() or "0")
        except ValueError:
            obs_port = 0
        return GptConfig(
            remote_url=self.remote_var.get().strip(),
            branch=self.branch_var.get().strip() or "main",
            commit_prefix="review",
            prefer_local_theme_dev=self.prefer_local_var.get(),
            record_scroll_seconds=scroll,
            record_wait_hero_seconds=self._cfg.record_wait_hero_seconds,
            last_push_sha=self._cfg.last_push_sha,
            last_push_at=self._cfg.last_push_at,
            knowledge_zip_name=self._cfg.knowledge_zip_name,
            knowledge_zip_loaded_at=self._cfg.knowledge_zip_loaded_at,
            obs_executable=self._cfg.obs_executable,
            obs_websocket_host=self._cfg.obs_websocket_host,
            obs_websocket_port=obs_port,
            obs_websocket_password=self.obs_password_var.get().strip(),
        )

    def _session_from_form(self) -> ReviewSession:
        return ReviewSession.from_form(
            self.review_goal_var.get(),
            self.known_issues_var.get(),
        )

    def _save_settings(self) -> None:
        from Komponenty.stronaglowna.service import save_storefront_password

        self._cfg = self._cfg_from_form()
        save_config(self._cfg)
        save_storefront_password(self.store_password_var.get())
        show_toast(self.root, "Zapisano ustawienia.")
        self.status_var.set("Ustawienia zapisane.")

    def _bind_tooltip(self, widget: tk.Widget, text: str) -> None:
        tip: dict[str, tk.Toplevel | None] = {"win": None}

        def show(_event: tk.Event) -> None:
            if tip["win"] is not None:
                return
            try:
                x = widget.winfo_rootx() + 16
                y = widget.winfo_rooty() + widget.winfo_height() + 4
            except tk.TclError:
                return
            tw = tk.Toplevel(widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            tk.Label(
                tw,
                text=text,
                bg="#ffffe0",
                fg="#222",
                relief="solid",
                borderwidth=1,
                padx=6,
                pady=2,
                font=("Segoe UI", 9),
                wraplength=420,
            ).pack()
            tip["win"] = tw

        def hide(_event: tk.Event) -> None:
            if tip["win"] is not None:
                tip["win"].destroy()
                tip["win"] = None

        widget.bind("<Enter>", show)
        widget.bind("<Leave>", hide)

    def _append_log(self, text: str) -> None:
        self.log.insert("end", text.rstrip() + "\n")
        self.log.see("end")

    def _clear_log(self) -> None:
        self.log.delete("1.0", "end")

    def _set_busy(self, busy: bool, status: str = "") -> None:
        self._busy = busy
        if status:
            self.status_var.set(status)

    def _copy_text(self, text: str) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        show_toast(self.root, "Skopiowano do schowka.")

    def _copy_compact_instructions(self) -> None:
        try:
            text = read_compact_instructions()
        except (OSError, ValueError) as exc:
            messagebox.showerror(APP_TITLE, str(exc), parent=self.root)
            return
        self._copy_text(text)
        show_toast(self.root, "Compact v35 — główne instrukcje z ZIP-a.")

    def _copy_conversation_start_prompt(self) -> None:
        self._cfg = self._cfg_from_form()
        session = self._session_from_form()
        msg = build_conversation_start_prompt(
            commit_sha=self._cfg.last_push_sha,
            review_goal=session.review_goal,
        )
        self._copy_text(msg)
        show_toast(self.root, "Prompt startowy — wklej w ChatGPT po dołączeniu ZIP.")

    def _open_conversation_window(self) -> None:
        dlg = tk.Toplevel(self.root)
        dlg.title("Okno rozmowy — ChatGPT + ZIP")
        position_toplevel_screen_center(dlg, 560, 300)
        dlg.transient(self.root)

        ttk.Label(
            dlg,
            text=(
                "Przygotuj rozmowę w ChatGPT (nowe okno + załącznik ZIP):\n"
                "1. «Skopiuj .zip» — archiwum wiedzy CLEAN_PACK v40 (47 plików) ze schowka plików\n"
                "2. Wklej ZIP w ChatGPT\n"
                "3. «Skopiuj Wiadomość początkową» — tekst startowy do wklejenia obok ZIP-a\n"
                "4. «Skopiuj wiadomość follow-up» — prośba o przeczytanie ZIP-a i połączenie z GitHubem\n"
                "5. «Skopiuj wiadomość potwierdzeń» — checklista Instructions, checkpoint, tryby, GitHub"
            ),
            padding=(12, 12, 12, 8),
            wraplength=480,
            justify="left",
        ).pack(anchor="w")

        try:
            md_files = list_starter_markdown_files()
            ttk.Label(
                dlg,
                text=f"Folder: {md_files[0].parent}\nPliki .md: {len(md_files)}",
                padding=(12, 0, 12, 8),
                foreground="#666",
                wraplength=480,
                justify="left",
            ).pack(anchor="w")
        except (FileNotFoundError, OSError) as exc:
            ttk.Label(
                dlg,
                text=str(exc),
                padding=(12, 0, 12, 8),
                foreground="#b00020",
                wraplength=480,
            ).pack(anchor="w")

        btn_row = ttk.Frame(dlg, padding=(12, 4, 12, 12))
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="Skopiuj .zip", command=lambda: self._conversation_copy_zip(dlg)).pack(
            side="left"
        )
        ttk.Button(
            btn_row,
            text="Zmień wiadomość początkową",
            command=lambda: self._open_edit_start_message_window(dlg),
        ).pack(side="left", padx=(8, 0))
        ttk.Button(btn_row, text="Zamknij", command=dlg.destroy).pack(side="right")

    def _open_edit_start_message_window(self, parent: tk.Misc) -> None:
        dlg = tk.Toplevel(parent)
        dlg.title("Zmień Wiadomość początkową")
        position_toplevel_screen_center(dlg, 720, 560)
        dlg.transient(parent)
        dlg.grab_set()

        try:
            starter_dir = gpt_starter_files_dir()
            initial_text = read_start_message_draft()
        except OSError as exc:
            messagebox.showerror(APP_TITLE, str(exc), parent=dlg)
            dlg.destroy()
            return

        ttk.Label(
            dlg,
            text=(
                f"Edytuj treść pliku «Wiadomość początkowa.txt».\n"
                f"Folder: {starter_dir}"
            ),
            padding=(12, 12, 12, 8),
            wraplength=660,
            justify="left",
        ).pack(anchor="w")

        editor = scrolledtext.ScrolledText(dlg, height=24, wrap="word", font=("Consolas", 10))
        editor.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        if initial_text:
            editor.insert("1.0", initial_text)
        editor.focus_set()

        btn_row = ttk.Frame(dlg, padding=(12, 4, 12, 12))
        btn_row.pack(fill="x")

        def save_message() -> None:
            try:
                write_start_message(editor.get("1.0", "end-1c"))
            except (OSError, ValueError) as exc:
                messagebox.showerror(APP_TITLE, str(exc), parent=dlg)
                return
            show_toast(dlg, "Zapisano Wiadomość początkową.txt")
            dlg.destroy()

        ttk.Button(btn_row, text="Zapisz", command=save_message).pack(side="left")
        ttk.Button(btn_row, text="Anuluj", command=dlg.destroy).pack(side="right")

    def _conversation_copy_zip(self, parent: tk.Misc) -> None:
        try:
            zip_path = build_starter_knowledge_zip()
            copy_zip_path_to_clipboard(zip_path)
        except (OSError, ValueError) as exc:
            messagebox.showerror(APP_TITLE, str(exc), parent=parent)
            return

        self._cfg = self._cfg_from_form()
        self._cfg.knowledge_zip_name = zip_path.name
        self._cfg.knowledge_zip_loaded_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        save_config(self._cfg)
        self._refresh_zip_status()
        show_toast(parent, f"ZIP w schowku ({zip_path.name}). Wklej w ChatGPT.")
        self._open_start_message_window(parent)

    def _open_start_message_window(self, parent: tk.Misc) -> None:
        dlg = tk.Toplevel(parent)
        dlg.title("Skopiuj Wiadomość początkową")
        position_toplevel_screen_center(dlg, 480, 160)
        dlg.transient(parent)
        dlg.grab_set()

        ttk.Label(
            dlg,
            text="ZIP jest w schowku. Teraz skopiuj wiadomość startową do ChatGPT.",
            padding=(12, 12, 12, 8),
            wraplength=440,
        ).pack(anchor="w")

        btn_row = ttk.Frame(dlg, padding=(12, 4, 12, 12))
        btn_row.pack(fill="x")

        def copy_message() -> None:
            try:
                text = read_start_message()
            except (OSError, ValueError) as exc:
                messagebox.showerror(APP_TITLE, str(exc), parent=dlg)
                return
            self._copy_text(text)
            show_toast(dlg, "Wiadomość początkowa — wklej w ChatGPT.")
            dlg.destroy()
            self._open_followup_message_window(parent)

        ttk.Button(btn_row, text="Skopiuj Wiadomość początkową", command=copy_message).pack(side="left")
        ttk.Button(btn_row, text="Później", command=dlg.destroy).pack(side="right")

    def _open_followup_message_window(self, parent: tk.Misc) -> None:
        dlg = tk.Toplevel(parent)
        dlg.title("Skopiuj wiadomość follow-up")
        position_toplevel_screen_center(dlg, 520, 180)
        dlg.transient(parent)
        dlg.grab_set()

        ttk.Label(
            dlg,
            text=(
                "Wiadomość początkowa jest w schowku. "
                "Teraz skopiuj kolejną wiadomość — prośbę o przeczytanie ZIP-a i GitHub."
            ),
            padding=(12, 12, 12, 8),
            wraplength=480,
        ).pack(anchor="w")

        btn_row = ttk.Frame(dlg, padding=(12, 4, 12, 12))
        btn_row.pack(fill="x")

        def copy_followup() -> None:
            self._copy_text(build_zip_read_github_followup_message())
            show_toast(dlg, "Wiadomość follow-up — wklej w ChatGPT.")
            dlg.destroy()
            self._open_confirmation_checklist_message_window(parent)

        ttk.Button(btn_row, text="Skopiuj wiadomość follow-up", command=copy_followup).pack(side="left")
        ttk.Button(btn_row, text="Później", command=dlg.destroy).pack(side="right")

    def _open_confirmation_checklist_message_window(self, parent: tk.Misc) -> None:
        dlg = tk.Toplevel(parent)
        dlg.title("Skopiuj wiadomość potwierdzeń")
        position_toplevel_screen_center(dlg, 520, 200)
        dlg.transient(parent)
        dlg.grab_set()

        ttk.Label(
            dlg,
            text=(
                "Ostatni krok: skopiuj checklistę potwierdzeń — "
                "Instructions, checkpoint, tryby analityczne i Shopify, GitHub, oczekiwanie na zadanie."
            ),
            padding=(12, 12, 12, 8),
            wraplength=480,
        ).pack(anchor="w")

        btn_row = ttk.Frame(dlg, padding=(12, 4, 12, 12))
        btn_row.pack(fill="x")

        def copy_checklist() -> None:
            self._copy_text(build_confirmation_checklist_message())
            show_toast(dlg, "Wiadomość potwierdzeń — wklej w ChatGPT.")
            dlg.destroy()

        ttk.Button(btn_row, text="Skopiuj wiadomość potwierdzeń", command=copy_checklist).pack(side="left")
        ttk.Button(btn_row, text="Później", command=dlg.destroy).pack(side="right")

    def _load_knowledge_zip(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Wybierz ZIP wiedzy (CLEAN_PACK v40)",
            filetypes=[("Archiwum ZIP", "*.zip"), ("Wszystkie pliki", "*.*")],
        )
        if not path:
            return
        try:
            name, loaded_at = import_knowledge_zip(Path(path))
        except (OSError, ValueError) as exc:
            messagebox.showerror(APP_TITLE, str(exc), parent=self.root)
            return
        self._cfg = self._cfg_from_form()
        self._cfg.knowledge_zip_name = name
        self._cfg.knowledge_zip_loaded_at = loaded_at
        save_config(self._cfg)
        self._refresh_zip_status()
        show_toast(self.root, f"ZIP zapisany lokalnie ({name}).")

    def _on_full_cycle_success(self) -> None:
        self._full_cycle_prompt_ready = True
        self._update_start_prompt_button()
        if not knowledge_zip_path():
            show_toast(self.root, "Pełny cykl OK — załaduj ZIP wiedzy przed rozmową z GPT.")
            return
        try:
            copy_knowledge_zip_to_clipboard()
        except OSError as exc:
            messagebox.showwarning(APP_TITLE, str(exc), parent=self.root)
            return
        show_toast(
            self.root,
            "ZIP w schowku — wklej w ChatGPT, potem «Skopiuj prompt rozpoczęcia rozmowy».",
        )

    def _copy_review_message(self) -> None:
        self._cfg = self._cfg_from_form()
        notes = ""
        dlg = tk.Toplevel(self.root)
        dlg.title("Uwagi do review (opcjonalnie)")
        position_toplevel_screen_center(dlg, 480, 160)
        dlg.transient(self.root)
        ttk.Label(dlg, text="Krótkie uwagi dla GPT (opcjonalnie):", padding=10).pack(anchor="w")
        var = tk.StringVar()
        ttk.Entry(dlg, textvariable=var, width=56).pack(padx=10, fill="x")

        def ok() -> None:
            nonlocal notes
            notes = var.get()
            dlg.destroy()
            msg = build_review_request(self._cfg, commit_sha=self._cfg.last_push_sha, notes=notes)
            self._copy_text(msg)

        ttk.Button(dlg, text="Kopiuj wiadomość", command=ok).pack(pady=10)

    def _open_theme_dev(self) -> None:
        open_theme_dev_preview(self.root, status_var=self.status_var, app_title=APP_TITLE)

    def _ask_manual_review_videos(self) -> tuple[Path, Path | None] | None:
        """Dialog wyboru ręcznych nagrań (desktop wymagany, mobile opcjonalny)."""
        dlg = tk.Toplevel(self.root)
        dlg.title("Załaduj nagrania do paczki review")
        position_toplevel_screen_center(dlg, 560, 220)
        dlg.transient(self.root)
        dlg.grab_set()

        ttk.Label(
            dlg,
            text="Wybierz własne nagrania ekranu (mp4, webm, mov…). Desktop wymagany.\n"
            "Kopia trafi do docs/review-demos/latest-desktop.webm (i opcjonalnie latest-mobile.webm)\n"
            "— tak szuka ich Custom GPT w repo.",
            padding=(12, 12, 12, 8),
            wraplength=520,
        ).pack(anchor="w")

        form = ttk.Frame(dlg, padding=(12, 0, 12, 8))
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)

        desktop_var = tk.StringVar()
        mobile_var = tk.StringVar()

        ttk.Label(form, text="Desktop:").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=desktop_var).grid(row=0, column=1, sticky="ew", padx=(8, 8))
        ttk.Button(
            form,
            text="Przeglądaj…",
            command=lambda: self._browse_video_file(desktop_var, dlg),
        ).grid(row=0, column=2)

        ttk.Label(form, text="Mobile:").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=mobile_var).grid(row=1, column=1, sticky="ew", padx=(8, 8))
        ttk.Button(
            form,
            text="Przeglądaj…",
            command=lambda: self._browse_video_file(mobile_var, dlg, required=False),
        ).grid(row=1, column=2)

        result: dict[str, object] = {"ok": False}

        btn_row = ttk.Frame(dlg, padding=(12, 4, 12, 12))
        btn_row.pack(fill="x")

        def on_ok() -> None:
            if not desktop_var.get().strip():
                messagebox.showerror(APP_TITLE, "Wybierz nagranie desktop.", parent=dlg)
                return
            result["desktop"] = Path(desktop_var.get().strip())
            mob = mobile_var.get().strip()
            result["mobile"] = Path(mob) if mob else None
            result["ok"] = True
            dlg.destroy()

        def on_cancel() -> None:
            dlg.destroy()

        ttk.Button(btn_row, text="OK — kontynuuj Pełny cykl", command=on_ok).pack(side="left")
        ttk.Button(btn_row, text="Anuluj", command=on_cancel).pack(side="right")

        dlg.protocol("WM_DELETE_WINDOW", on_cancel)
        dlg.wait_window()

        if not result.get("ok"):
            return None
        return result["desktop"], result["mobile"]  # type: ignore[return-value]

    def _browse_video_file(
        self,
        var: tk.StringVar,
        parent: tk.Misc,
        *,
        required: bool = True,
    ) -> None:
        path = filedialog.askopenfilename(
            parent=parent,
            title="Wybierz nagranie wideo" if required else "Nagranie mobile (opcjonalnie)",
            filetypes=[
                ("Wideo", "*.webm *.mp4 *.mov *.mkv"),
                ("WebM", "*.webm"),
                ("MP4", "*.mp4"),
                ("Wszystkie pliki", "*.*"),
            ],
        )
        if path:
            var.set(path)

    def _open_review_demos(self) -> None:
        from .config import REVIEW_DEMOS_DIR

        REVIEW_DEMOS_DIR.mkdir(parents=True, exist_ok=True)
        import os

        os.startfile(REVIEW_DEMOS_DIR)  # noqa: S606 — Windows

    def _open_videos_dir(self) -> None:
        from .config import VIDEOS_DIR

        VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
        import os

        os.startfile(VIDEOS_DIR)  # noqa: S606 — Windows

    def _run_async(self, label: str, worker, *, on_success=None) -> None:
        if self._busy:
            messagebox.showinfo(APP_TITLE, "Poczekaj na zakończenie bieżącej operacji.", parent=self.root)
            return
        self._save_settings()
        self._clear_log()
        self._set_busy(True, f"{label}…")

        def run() -> None:
            lines: list[str] = []

            err: str | None = None
            try:
                worker(lines)
            except Exception as exc:  # noqa: BLE001 — GUI pokazuje błąd użytkownikowi
                err = str(exc)
                lines.append(f"BŁĄD: {exc}")

            def finish() -> None:
                for line in lines:
                    self._append_log(line)
                self._set_busy(False, f"{label}: {'błąd' if err else 'gotowe'}")
                if err:
                    messagebox.showerror(APP_TITLE, err, parent=self.root)
                else:
                    show_toast(self.root, f"{label} — OK")
                    if on_success is not None:
                        on_success()

            self.root.after(0, finish)

        threading.Thread(target=run, daemon=True, name=f"integracjagpt-{label}").start()

    def _run_record(self) -> None:
        cfg = self._cfg_from_form()

        def worker(log: list[str]) -> None:
            from Komponenty.stronaglowna.service import save_storefront_password

            save_storefront_password(self.store_password_var.get())
            res = record_preview(
                prefer_local=cfg.prefer_local_theme_dev,
                scroll_seconds=cfg.record_scroll_seconds,
                wait_hero_seconds=cfg.record_wait_hero_seconds,
                log=log,
            )
            if not res.ok:
                raise RuntimeError(res.message)

        self._run_async("Nagranie podglądu", worker)

    def _set_obs_recording_ui(self, active: bool) -> None:
        self._obs_recording = active
        self._obs_record_btn.configure(text="Zatrzymaj (OBS)" if active else "Nagraj (OBS)")

    def _toggle_obs_recording(self) -> None:
        if self._obs_recording:
            self._run_obs_stop()
        else:
            self._run_obs_start()

    def _run_obs_start(self) -> None:
        cfg = self._cfg_from_form()

        def worker(log: list[str]) -> None:
            from Komponenty.stronaglowna.service import save_storefront_password
            from .obs_record import start_obs_recording

            save_storefront_password(self.store_password_var.get())
            res = start_obs_recording(
                cfg,
                prefer_local=cfg.prefer_local_theme_dev,
                log=log,
            )
            if not res.ok:
                raise RuntimeError(res.message)

        def on_ok() -> None:
            self._set_obs_recording_ui(True)
            self.status_var.set("OBS nagrywa — przewiń podgląd, potem kliknij «Zatrzymaj (OBS)».")

        self._run_async("Start OBS", worker, on_success=on_ok)

    def _run_obs_stop(self) -> None:
        cfg = self._cfg_from_form()

        def worker(log: list[str]) -> None:
            from .obs_record import stop_obs_recording

            res = stop_obs_recording(cfg, log=log)
            if not res.ok:
                raise RuntimeError(res.message)

        def on_ok() -> None:
            self._set_obs_recording_ui(False)
            self.status_var.set("Nagranie OBS → docs/review-demos/latest-desktop.webm")

        self._run_async("Stop OBS", worker, on_success=on_ok)

    def _run_video_to_disk(self) -> None:
        cfg = self._cfg_from_form()
        session = self._session_from_form()

        def worker(log: list[str]) -> None:
            from Komponenty.stronaglowna.service import save_storefront_password
            import os

            save_storefront_password(self.store_password_var.get())
            res = record_video_to_disk(
                prefer_local=cfg.prefer_local_theme_dev,
                scroll_seconds=cfg.record_scroll_seconds,
                wait_hero_seconds=cfg.record_wait_hero_seconds,
                session_label=session.review_goal,
                log=log,
            )
            if not res.ok:
                raise RuntimeError(res.message)
            if res.output_dir:
                log.append("")
                log.append(f"Gotowe — otwieram folder: {res.output_dir}")
                os.startfile(res.output_dir)  # noqa: S606 — Windows

        self._run_async("Utwórz wideo na dysku", worker)

    def _run_sync_only(self) -> None:
        session = self._session_from_form()

        def worker(log: list[str]) -> None:
            sync_theme_to_mirror(log=log, session=session)

        self._run_async("Sync lustra", worker)

    def _run_review_package(self) -> None:
        cfg = self._cfg_from_form()
        session = self._session_from_form()
        include_rec = self.include_recordings_var.get()

        def worker(log: list[str]) -> None:
            build_review_package(
                session,
                include_recordings=include_rec,
                prefer_local=cfg.prefer_local_theme_dev,
                scroll_seconds=cfg.record_scroll_seconds,
                wait_hero_seconds=cfg.record_wait_hero_seconds,
                log=log,
            )
            log.append("")
            log.append("Paczka gotowa w .gpt_mirror/ — bez pusha. Sprawdź REVIEW_MANIFEST.json i SYNC_NOTES.md.")

        self._run_async("Review package only", worker)

    def _start_main_repo_push(self) -> None:
        if self._busy:
            messagebox.showinfo(
                APP_TITLE,
                "Poczekaj na zakończenie bieżącej operacji.",
                parent=self.root,
            )
            return

        self._clear_log()
        self._main_repo_audit = None
        self._set_busy(True, "Sprawdzam repo główne gicleeart…")
        self._main_repo_btn.configure(state="disabled")

        def run() -> None:
            from Komponenty.pushe.service import dry_run_github_push

            lines: list[str] = []
            report = dry_run_github_push(on_line=lines.append)
            self.root.after(0, lambda: self._finish_main_repo_dry_run(lines, report))

        threading.Thread(
            target=run,
            daemon=True,
            name="integracjagpt-main-repo-dry-run",
        ).start()

    def _finish_main_repo_dry_run(self, lines: list[str], report) -> None:
        for line in lines:
            self._append_log(line)
        for line in report.format_report():
            self._append_log(line)

        self._main_repo_audit = report
        self._main_repo_btn.configure(state="normal")

        if report.blocked:
            self._set_busy(False, "Push repo głównego: zablokowany")
            messagebox.showerror(
                APP_TITLE,
                report.error or "Audyt wykrył blokady — commit i push anulowane.",
                parent=self.root,
            )
            return

        if report.no_changes:
            self._set_busy(False, "Brak zmian — repo główne jest aktualne")
            messagebox.showinfo(
                APP_TITLE,
                "Brak zmian — eagleblastmusic-lgtm/gicleeart jest aktualne.",
                parent=self.root,
            )
            return

        self._set_busy(False, "Repo główne gotowe — potwierdź push")
        preview_lines: list[str] = []
        if report.push_only:
            preview_lines.append(
                f"• working tree clean — wypchnięcie {report.unpushed_commits} lokalnych commitów"
            )
        else:
            for path in report.commit_candidates[:30]:
                preview_lines.append(f"• {path}")
            if len(report.commit_candidates) > 30:
                preview_lines.append(f"… i {len(report.commit_candidates) - 30} więcej")
        if report.deletable_files:
            preview_lines.append("")
            preview_lines.append("Usunięcia (opcjonalne):")
            for path in report.deletable_files[:20]:
                preview_lines.append(f"• {path}")

        include_deletions = False
        if report.deletable_files:
            include_deletions = messagebox.askyesno(
                APP_TITLE,
                f"Wykryto {len(report.deletable_files)} usuniętych plików.\n\n"
                "Uwzględnić je w commicie do repo głównego?",
                parent=self.root,
            )

        if not report.push_only and not report.commit_candidates and not include_deletions:
            self.status_var.set("Brak bezpiecznych plików do commita.")
            messagebox.showinfo(
                APP_TITLE,
                "Brak bezpiecznych plików do commita (bez usunięć).",
                parent=self.root,
            )
            return

        action = "Push" if report.push_only else "Commit + push"
        commit_line = (
            f"Commity do wypchnięcia: {report.unpushed_commits}\n"
            if report.push_only
            else f"Commit: {report.commit_message}\n"
        )
        if not messagebox.askyesno(
            APP_TITLE,
            f"{action} do repo głównego?\n\n"
            f"Repo: eagleblastmusic-lgtm/gicleeart ({report.branch})\n"
            + commit_line
            + (
                ""
                if report.push_only
                else (
                    f"Pliki: {len(report.commit_candidates)}"
                    + (f" + {len(report.deletable_files)} usunięć" if include_deletions else "")
                )
            )
            + "\n\n"
            + "\n".join(preview_lines),
            parent=self.root,
        ):
            self.status_var.set("Push repo głównego anulowany.")
            return

        self._run_main_repo_commit_push(include_deletions)

    def _run_main_repo_commit_push(self, include_deletions: bool) -> None:
        report = self._main_repo_audit
        if report is None:
            return

        self._set_busy(True, "Pushuję do repo głównego gicleeart…")
        self._main_repo_btn.configure(state="disabled")

        def run() -> None:
            from Komponenty.pushe.service import commit_and_push_github

            lines: list[str] = []
            result = commit_and_push_github(
                report,
                include_deletions=include_deletions,
                on_line=lines.append,
            )
            self.root.after(0, lambda: self._finish_main_repo_push(lines, result))

        threading.Thread(
            target=run,
            daemon=True,
            name="integracjagpt-main-repo-push",
        ).start()

    def _finish_main_repo_push(self, lines: list[str], result) -> None:
        for line in lines:
            self._append_log(line)
        self._main_repo_btn.configure(state="normal")

        if result.ok:
            self._set_busy(False, "Repo główne zaktualizowane")
            if result.commit_sha:
                self._append_log(f"Commit SHA: {result.commit_sha}")
            if result.committed_files:
                self._append_log("Pliki w commicie:")
                for path in result.committed_files:
                    self._append_log(f"  • {path}")
            show_toast(self.root, result.message or "Repo główne zaktualizowane")
            self.status_var.set(result.message or "Repo główne zaktualizowane")
        else:
            self._set_busy(False, "Push repo głównego: błąd")
            messagebox.showerror(
                APP_TITLE,
                result.message or "Push nie powiódł się.",
                parent=self.root,
            )

    def _start_gicleeart_gpt_push(self, *, skip_sync: bool = False, sync_result=None, include_recordings: bool = False) -> None:
        if self._busy:
            messagebox.showinfo(APP_TITLE, "Poczekaj na zakończenie bieżącej operacji.", parent=self.root)
            return
        if not skip_sync:
            self._clear_log()
        self._gicleeart_audit = None
        self._set_busy(True, "Sprawdzam snapshot motywu…")
        self._gicleeart_btn.configure(state="disabled")
        cfg = self._cfg_from_form()
        session = self._session_from_form()

        def run() -> None:
            from .gicleeart_gpt_push import dry_run_gicleeart_gpt_push

            lines: list[str] = []
            report = dry_run_gicleeart_gpt_push(
                cfg,
                session,
                skip_sync=skip_sync,
                sync_result=sync_result,
                include_recordings=include_recordings,
                log=lines,
            )
            self.root.after(
                0,
                lambda: self._finish_gicleeart_dry_run(
                    lines,
                    report,
                    cfg,
                    session,
                    on_push_success=getattr(self, "_gicleeart_full_cycle_on_success", None),
                ),
            )

        threading.Thread(
            target=run,
            daemon=True,
            name="integracjagpt-gicleeart-dry-run",
        ).start()

    def _finish_gicleeart_dry_run(
        self,
        lines: list[str],
        report,
        cfg,
        session,
        *,
        on_push_success=None,
    ) -> None:
        if on_push_success is not None:
            self._gicleeart_full_cycle_on_success = None
        for line in lines:
            self._append_log(line)
        for line in report.format_report():
            self._append_log(line)

        self._gicleeart_audit = report
        self._gicleeart_btn.configure(state="normal")

        if report.blocked:
            self._set_busy(False, "Push GicleeArt-GPT: zablokowany")
            messagebox.showerror(
                APP_TITLE,
                report.error or "Audyt wykrył blokady — commit i push anulowane.",
                parent=self.root,
            )
            return

        if report.no_changes:
            self._set_busy(False, "Brak zmian — gicleeart-gpt jest aktualne")
            messagebox.showinfo(
                APP_TITLE,
                "Brak zmian — gicleeart-gpt jest aktualne.",
                parent=self.root,
            )
            if on_push_success:
                on_push_success(None)
            return

        self._set_busy(False, "Gotowe do commita — potwierdź push")
        preview_lines = []
        for path in report.commit_candidates[:30]:
            preview_lines.append(f"• {path}")
        if len(report.commit_candidates) > 30:
            preview_lines.append(f"… i {len(report.commit_candidates) - 30} więcej")
        if report.deletable_files:
            preview_lines.append("")
            preview_lines.append("Usunięcia (opcjonalne):")
            for path in report.deletable_files[:20]:
                preview_lines.append(f"• {path}")

        include_deletions = False
        if report.deletable_files:
            include_deletions = messagebox.askyesno(
                APP_TITLE,
                "Wykryto usunięte pliki w lustrze motywu.\n\nUwzględnić je w commicie?",
                parent=self.root,
            )

        if not messagebox.askyesno(
            APP_TITLE,
            "Commit + push GicleeArt-GPT na GitHub?\n\n"
            f"Repo: eagleblastmusic-lgtm/gicleeart-gpt ({cfg.branch})\n"
            f"Commit: {report.commit_message}\n"
            f"Pliki: {len(report.commit_candidates)}"
            + (f" + {len(report.deletable_files)} usunięć" if include_deletions else "")
            + "\n\n"
            + "\n".join(preview_lines),
            parent=self.root,
        ):
            self.status_var.set("Push GicleeArt-GPT anulowany.")
            return

        self._run_gicleeart_commit_push(cfg, session, include_deletions, on_push_success=on_push_success)

    def _run_gicleeart_commit_push(
        self,
        cfg,
        session,
        include_deletions: bool,
        *,
        on_push_success=None,
    ) -> None:
        report = self._gicleeart_audit
        if report is None:
            return
        self._set_busy(True, "Pushuję GicleeArt-GPT do GitHub…")
        self._gicleeart_btn.configure(state="disabled")

        def run() -> None:
            from .gicleeart_gpt_push import commit_and_push_gicleeart_gpt

            lines: list[str] = []
            result = commit_and_push_gicleeart_gpt(
                report,
                cfg,
                session,
                include_deletions=include_deletions,
                log=lines,
            )
            self.root.after(
                0,
                lambda: self._finish_gicleeart_push(lines, result, cfg, on_push_success),
            )

        threading.Thread(
            target=run,
            daemon=True,
            name="integracjagpt-gicleeart-push",
        ).start()

    def _finish_gicleeart_push(self, lines: list[str], result, cfg, on_push_success=None) -> None:
        for line in lines:
            self._append_log(line)
        self._gicleeart_btn.configure(state="normal")
        if result.ok:
            self._set_busy(False, "GicleeArt-GPT zaktualizowane")
            if result.commit_sha:
                cfg.last_push_sha = result.commit_sha
                cfg.last_push_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
                save_config(cfg)
                self._cfg = cfg
                self._append_log(f"Commit SHA: {result.commit_sha}")
                self._append_log("Pliki w commicie:")
                for path in result.committed_files:
                    self._append_log(f"  • {path}")
            show_toast(self.root, result.message or "GicleeArt-GPT zaktualizowane")
            self.status_var.set(result.message or "GicleeArt-GPT zaktualizowane")
            if on_push_success:
                on_push_success(result)
        else:
            self._set_busy(False, "Push GicleeArt-GPT: błąd")
            messagebox.showerror(APP_TITLE, result.message or "Push nie powiódł się.", parent=self.root)

    def _start_gicleeapp_push(self) -> None:
        if self._busy:
            messagebox.showinfo(APP_TITLE, "Poczekaj na zakończenie bieżącej operacji.", parent=self.root)
            return
        self._clear_log()
        self._gicleeapp_audit = None
        self._set_busy(True, "Sprawdzam snapshot…")
        self._gicleeapp_btn.configure(state="disabled")

        def run() -> None:
            from .gicleeapp_push import dry_run_gicleeapp_push

            lines: list[str] = []
            report = dry_run_gicleeapp_push(log=lines)
            self.root.after(0, lambda: self._finish_gicleeapp_dry_run(lines, report))

        threading.Thread(target=run, daemon=True, name="integracjagpt-gicleeapp-dry-run").start()

    def _finish_gicleeapp_dry_run(self, lines: list[str], report) -> None:
        for line in lines:
            self._append_log(line)
        for line in report.format_report():
            self._append_log(line)

        self._gicleeapp_audit = report
        self._gicleeapp_btn.configure(state="normal")

        if report.blocked:
            self._set_busy(False, "Push GicleeApp: zablokowany")
            messagebox.showerror(
                APP_TITLE,
                report.error or "Audyt wykrył blokady — commit i push anulowane.",
                parent=self.root,
            )
            return

        if report.no_changes:
            self._set_busy(False, "Brak zmian — gicleeapp jest aktualne")
            messagebox.showinfo(
                APP_TITLE,
                "Brak zmian — gicleeapp jest aktualne.",
                parent=self.root,
            )
            return

        self._set_busy(False, "Gotowe do commita — potwierdź push")
        preview_lines = []
        for path in report.commit_candidates[:30]:
            preview_lines.append(f"• {path}")
        if len(report.commit_candidates) > 30:
            preview_lines.append(f"… i {len(report.commit_candidates) - 30} więcej")
        if report.deletable_files:
            preview_lines.append("")
            preview_lines.append("Usunięcia (opcjonalne):")
            for path in report.deletable_files[:20]:
                preview_lines.append(f"• {path}")
        if report.theme_related_changes:
            preview_lines.append("")
            preview_lines.append(
                "Uwaga: część zmian może wymagać osobnego snapshotu w gicleeart-gpt."
            )

        include_deletions = False
        if report.deletable_files:
            include_deletions = messagebox.askyesno(
                APP_TITLE,
                "Wykryto usunięte pliki aplikacji (nie review-only).\n\n"
                "Uwzględnić je w commicie?",
                parent=self.root,
            )

        if not messagebox.askyesno(
            APP_TITLE,
            "Commit + push GicleeApp na GitHub?\n\n"
            f"Repo: eagleblastmusic-lgtm/gicleeapp (main)\n"
            f"Pliki: {len(report.commit_candidates)}"
            + (f" + {len(report.deletable_files)} usunięć" if include_deletions else "")
            + "\n\n"
            + "\n".join(preview_lines),
            parent=self.root,
        ):
            self.status_var.set("Push GicleeApp anulowany.")
            return

        self._run_gicleeapp_commit_push(include_deletions)

    def _run_gicleeapp_commit_push(self, include_deletions: bool) -> None:
        report = self._gicleeapp_audit
        if report is None:
            return
        self._set_busy(True, "Pushuję do GitHub…")
        self._gicleeapp_btn.configure(state="disabled")

        def run() -> None:
            from .gicleeapp_push import commit_and_push_gicleeapp

            lines: list[str] = []
            result = commit_and_push_gicleeapp(
                report,
                include_deletions=include_deletions,
                log=lines,
            )
            self.root.after(0, lambda: self._finish_gicleeapp_push(lines, result))

        threading.Thread(target=run, daemon=True, name="integracjagpt-gicleeapp-push").start()

    def _finish_gicleeapp_push(self, lines: list[str], result) -> None:
        for line in lines:
            self._append_log(line)
        self._gicleeapp_btn.configure(state="normal")
        if result.ok:
            self._set_busy(False, "GicleeApp zaktualizowane")
            if result.commit_sha:
                self._append_log(f"Commit SHA: {result.commit_sha}")
                self._append_log("Pliki w commicie:")
                for path in result.committed_files:
                    self._append_log(f"  • {path}")
            if result.starter_sync_updated_files:
                self._append_log("Pliki startowe GPT (auto-sync):")
                for path in result.starter_sync_updated_files:
                    self._append_log(f"  • {path}")
            elif result.starter_sync_message:
                self._append_log(result.starter_sync_message)
            show_toast(self.root, result.message or "GicleeApp zaktualizowane")
            self.status_var.set(result.message or "GicleeApp zaktualizowane")
            self._offer_starter_files_push_after_gicleeapp()
        else:
            self._set_busy(False, "Push GicleeApp: błąd")
            messagebox.showerror(APP_TITLE, result.message or "Push nie powiódł się.", parent=self.root)

    def _offer_starter_files_push_after_gicleeapp(self) -> None:
        from .starter_files_push import dry_run_starter_files_push

        report = dry_run_starter_files_push(rebuild_zip=True, log=[])
        if report.blocked or report.no_changes:
            return
        if not messagebox.askyesno(
            APP_TITLE,
            "Pliki startowe GPT mają lokalne zmiany w monorepo.\n\n"
            f"Kandydaci: {len(report.commit_candidates)} plików\n\n"
            "Wypchnąć je teraz na origin/master?",
            parent=self.root,
        ):
            return
        self._starter_files_audit = report
        self._run_starter_files_commit_push(include_deletions=False)

    def _start_starter_files_push(self) -> None:
        if self._busy:
            messagebox.showinfo(APP_TITLE, "Poczekaj na zakończenie bieżącej operacji.", parent=self.root)
            return
        self._clear_log()
        self._starter_files_audit = None
        self._set_busy(True, "Sprawdzam pliki startowe GPT…")
        self._starter_files_btn.configure(state="disabled")

        def run() -> None:
            from .starter_files_push import dry_run_starter_files_push

            lines: list[str] = []
            report = dry_run_starter_files_push(rebuild_zip=True, log=lines)
            self.root.after(0, lambda: self._finish_starter_files_dry_run(lines, report))

        threading.Thread(target=run, daemon=True, name="integracjagpt-starter-files-dry-run").start()

    def _finish_starter_files_dry_run(self, lines: list[str], report) -> None:
        for line in lines:
            self._append_log(line)
        for line in report.format_report():
            self._append_log(line)

        self._starter_files_audit = report
        self._starter_files_btn.configure(state="normal")

        if report.blocked:
            self._set_busy(False, "Push plików startowych: zablokowany")
            messagebox.showerror(
                APP_TITLE,
                report.error or "Audyt wykrył blokady — commit i push anulowane.",
                parent=self.root,
            )
            return

        if report.no_changes:
            self._set_busy(False, "Brak zmian — pliki startowe GPT są aktualne")
            messagebox.showinfo(
                APP_TITLE,
                "Brak zmian — pliki startowe GPT są aktualne na monorepo.",
                parent=self.root,
            )
            return

        self._set_busy(False, "Gotowe do commita — potwierdź push")
        preview_lines = []
        for path in report.commit_candidates[:30]:
            preview_lines.append(f"• {path}")
        if len(report.commit_candidates) > 30:
            preview_lines.append(f"… i {len(report.commit_candidates) - 30} więcej")
        if report.outside_allowlist_hits:
            preview_lines.append("")
            preview_lines.append("Uwaga: inne pliki w folderze starterów (poza allowlistą) nie trafią do commita.")

        include_deletions = False
        if report.deletable_files:
            include_deletions = messagebox.askyesno(
                APP_TITLE,
                "Wykryto usunięte pliki startowe z allowlisty.\n\n"
                "Uwzględnić je w commicie?",
                parent=self.root,
            )

        if not messagebox.askyesno(
            APP_TITLE,
            "Commit + push plików startowych GPT na GitHub?\n\n"
            f"Repo: monorepo (origin/master)\n"
            f"Pliki: {len(report.commit_candidates)}"
            + (f" + {len(report.deletable_files)} usunięć" if include_deletions else "")
            + "\n\n"
            + "\n".join(preview_lines),
            parent=self.root,
        ):
            self.status_var.set("Push plików startowych GPT anulowany.")
            return

        self._run_starter_files_commit_push(include_deletions)

    def _run_starter_files_commit_push(self, include_deletions: bool) -> None:
        report = self._starter_files_audit
        if report is None:
            return
        self._set_busy(True, "Pushuję pliki startowe GPT…")
        self._starter_files_btn.configure(state="disabled")

        def run() -> None:
            from .starter_files_push import commit_and_push_starter_files

            lines: list[str] = []
            result = commit_and_push_starter_files(
                report,
                include_deletions=include_deletions,
                log=lines,
            )
            self.root.after(0, lambda: self._finish_starter_files_push(lines, result))

        threading.Thread(target=run, daemon=True, name="integracjagpt-starter-files-push").start()

    def _finish_starter_files_push(self, lines: list[str], result) -> None:
        for line in lines:
            self._append_log(line)
        self._starter_files_btn.configure(state="normal")
        if result.ok:
            self._set_busy(False, "Pliki startowe GPT zaktualizowane")
            if result.commit_sha:
                self._append_log(f"Commit SHA: {result.commit_sha}")
                self._append_log("Pliki w commicie:")
                for path in result.committed_files:
                    self._append_log(f"  • {path}")
            show_toast(self.root, result.message or "Pliki startowe GPT zaktualizowane")
            self.status_var.set(result.message or "Pliki startowe GPT zaktualizowane")
        else:
            self._set_busy(False, "Push plików startowych GPT: błąd")
            messagebox.showerror(APP_TITLE, result.message or "Push nie powiódł się.", parent=self.root)

    def _start_giclee_viewer_push(self) -> None:
        if self._busy:
            messagebox.showinfo(APP_TITLE, "Poczekaj na zakończenie bieżącej operacji.", parent=self.root)
            return
        self._clear_log()
        self._giclee_viewer_audit = None
        self._set_busy(True, "Sprawdzam Giclee Viewer…")
        self._giclee_viewer_btn.configure(state="disabled")

        def run() -> None:
            from .giclee_viewer_push import dry_run_giclee_viewer_push

            lines: list[str] = []
            report = dry_run_giclee_viewer_push(log=lines)
            self.root.after(0, lambda: self._finish_giclee_viewer_dry_run(lines, report))

        threading.Thread(target=run, daemon=True, name="integracjagpt-giclee-viewer-dry-run").start()

    def _finish_giclee_viewer_dry_run(self, lines: list[str], report) -> None:
        for line in lines:
            self._append_log(line)
        for line in report.format_report():
            self._append_log(line)

        self._giclee_viewer_audit = report
        self._giclee_viewer_btn.configure(state="normal")

        if report.blocked:
            self._set_busy(False, "Push Giclee Viewer: zablokowany")
            messagebox.showerror(
                APP_TITLE,
                report.error or "Audyt wykrył blokady — commit i push anulowane.",
                parent=self.root,
            )
            return

        if report.no_changes:
            self._set_busy(False, "Brak zmian — giclee-viewer jest aktualne")
            messagebox.showinfo(
                APP_TITLE,
                "Brak zmian — giclee-viewer jest aktualne na GitHub.",
                parent=self.root,
            )
            return

        self._set_busy(False, "Gotowe do pusha — potwierdź")
        preview_lines = []
        if report.push_only:
            preview_lines.append(
                f"• working tree clean — wypchnięcie {report.unpushed_commits} lokalnych commitów"
            )
        else:
            for path in report.commit_candidates[:30]:
                preview_lines.append(f"• {path}")
            if len(report.commit_candidates) > 30:
                preview_lines.append(f"… i {len(report.commit_candidates) - 30} więcej")

        include_deletions = False
        if report.deletable_files:
            include_deletions = messagebox.askyesno(
                APP_TITLE,
                "Wykryto usunięte pliki projektu.\n\nUwzględnić je w commicie?",
                parent=self.root,
            )

        action = "Push" if report.push_only else "Commit + push"
        if not messagebox.askyesno(
            APP_TITLE,
            f"{action} Giclee Viewer na GitHub?\n\n"
            f"Repo: eagleblastmusic-lgtm/giclee-viewer (master)\n"
            + (
                f"Commity do wypchnięcia: {report.unpushed_commits}\n\n"
                if report.push_only
                else (
                    f"Pliki: {len(report.commit_candidates)}"
                    + (f" + {len(report.deletable_files)} usunięć" if include_deletions else "")
                    + "\n\n"
                )
            )
            + "\n".join(preview_lines),
            parent=self.root,
        ):
            self.status_var.set("Push Giclee Viewer anulowany.")
            return

        self._run_giclee_viewer_commit_push(include_deletions)

    def _run_giclee_viewer_commit_push(self, include_deletions: bool) -> None:
        report = self._giclee_viewer_audit
        if report is None:
            return
        self._set_busy(True, "Pushuję Giclee Viewer…")
        self._giclee_viewer_btn.configure(state="disabled")

        def run() -> None:
            from .giclee_viewer_push import commit_and_push_giclee_viewer

            lines: list[str] = []
            result = commit_and_push_giclee_viewer(
                report,
                include_deletions=include_deletions,
                log=lines,
            )
            self.root.after(0, lambda: self._finish_giclee_viewer_push(lines, result))

        threading.Thread(target=run, daemon=True, name="integracjagpt-giclee-viewer-push").start()

    def _finish_giclee_viewer_push(self, lines: list[str], result) -> None:
        for line in lines:
            self._append_log(line)
        self._giclee_viewer_btn.configure(state="normal")
        if result.ok:
            self._set_busy(False, "Giclee Viewer zaktualizowane")
            if result.commit_sha:
                self._append_log(f"Commit SHA: {result.commit_sha}")
            if result.push_only:
                self._append_log(f"Wypchnięte commity: {result.pushed_commits}")
            elif result.committed_files:
                self._append_log("Pliki w commicie:")
                for path in result.committed_files:
                    self._append_log(f"  • {path}")
            show_toast(self.root, result.message or "Giclee Viewer zaktualizowane")
            self.status_var.set(result.message or "Giclee Viewer zaktualizowane")
        else:
            self._set_busy(False, "Push Giclee Viewer: błąd")
            messagebox.showerror(APP_TITLE, result.message or "Push nie powiódł się.", parent=self.root)

    def _run_full_cycle(self) -> None:
        cfg = self._cfg_from_form()
        session = self._session_from_form()
        include_rec = self.include_recordings_var.get()

        manual: tuple[Path, Path | None] | None = None
        if not include_rec:
            manual = self._ask_manual_review_videos()
            if manual is None:
                return

        self._clear_log()
        self._set_busy(True, "Pełny cykl — przygotowanie…")

        def worker(log: list[str]) -> None:
            from .mirror import SyncResult, sync_theme_to_mirror

            if manual is not None:
                from .record import import_manual_review_videos

                import_manual_review_videos(manual[0], manual[1], log=log)
            elif include_rec:
                from .record import record_preview
                from .review_session import route_from_url

                rec = record_preview(
                    prefer_local=cfg.prefer_local_theme_dev,
                    scroll_seconds=cfg.record_scroll_seconds,
                    wait_hero_seconds=cfg.record_wait_hero_seconds,
                    log=log,
                )
                if rec.ok:
                    session.routes_recorded = [route_from_url(rec.url_used)]
                else:
                    log.append(f"Nagranie pominięte: {rec.message}")

            log.append("=== Sync motywu → .gpt_mirror (Pełny cykl) ===")
            sync = sync_theme_to_mirror(log=log, session=session)
            if not sync.ok:
                raise RuntimeError("; ".join(sync.errors))

            self.root.after(
                0,
                lambda: self._finish_full_cycle_prepare(log, sync, cfg, session),
            )

        threading.Thread(target=worker, daemon=True, name="integracjagpt-full-cycle").start()

    def _finish_full_cycle_prepare(
        self,
        lines: list[str],
        sync,
        cfg,
        session,
    ) -> None:
        for line in lines:
            self._append_log(line)
        self._set_busy(False, "Pełny cykl — potwierdź push")

        def on_push_success(result) -> None:
            self._full_cycle_prompt_ready = True
            self._update_start_prompt_button()
            self._append_log("")
            self._append_log("--- Wiadomość do ChatGPT (skopiuj) ---")
            sha = (result.commit_sha if result else None) or cfg.last_push_sha
            self._append_log(build_review_request(cfg, commit_sha=sha))
            self.root.after(0, self._on_full_cycle_success)

        self._gicleeart_full_cycle_on_success = on_push_success
        self._start_gicleeart_gpt_push(skip_sync=True, sync_result=sync)


def main() -> None:
    root = tk.Tk()
    IntegracjaGptApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
