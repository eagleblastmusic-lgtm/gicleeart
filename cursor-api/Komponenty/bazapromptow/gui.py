"""Baza Promptow — przyciski z gotowym tekstem do schowka."""

from __future__ import annotations

import os
import shutil
import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from Komponenty._shared.clipboard_image import (
    clipboard_file_paths_for_import,
    clipboard_images_for_import,
    clipboard_video_paths_for_import,
    copy_pil_image_to_clipboard,
)
from Komponenty._shared.toast import show_toast
from Komponenty._shared.tk_scroll import bind_mousewheel_to_canvas
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .catalog import load_catalog_rows
from .select_dialog import open_product_select_dialog
from .media_preview import (
    MIN_PLAYBACK_FPS,
    boomerang_frame_indices,
    extract_video_poster,
    load_segment_playback,
    probe_video_duration,
)
from .storage import (
    FOLDER_ALL,
    FOLDER_UNCATEGORIZED,
    DEFAULT_FOLDER_ID,
    DEFAULT_VIDEO_PREVIEW_END_SEC,
    HOVER_PREVIEW_IMAGE,
    HOVER_PREVIEW_VIDEO,
    FolderEntry,
    PromptEntry,
    PromptStore,
    context_image_path,
    context_file_path,
    context_video_path,
    context_video_poster_path,
    delete_prompt_context_attachments,
    import_context_image,
    import_context_image_pil,
    import_context_file,
    import_context_video,
    load_prompts,
    delete_context_image_file,
    delete_context_file,
    delete_context_video_file,
    new_folder_id,
    new_prompt_id,
    next_folder_sort_key,
    next_sort_key,
    normalize_video_preview_range,
    save_prompts,
    sync_context_images,
    sync_context_files,
    sync_context_videos,
)

APP_TITLE = "Baza Promptow"
_CONTEXT_THUMB_SIZE = (96, 72)
_HOVER_PREVIEW_SIZE = (240, 180)


def _format_file_size(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes // 1024} KB"
    return f"{num_bytes / (1024 * 1024):.1f} MB"


class BazaPromptowApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        position_toplevel_screen_center(self.root, 920, 720)
        self.root.minsize(640, 420)

        self._store = load_prompts()
        self._selected_id: str | None = None
        self._active_folder_view = FOLDER_ALL
        self._button_by_id: dict[str, tk.Button] = {}
        self._folder_tree: ttk.Treeview | None = None
        self._catalog_rows: list[dict] = []
        self._catalog_loading = False
        self._context_thumb_refs: list[tk.PhotoImage] = []
        self._hover_preview_win: tk.Toplevel | None = None
        self._hover_preview_photo: tk.PhotoImage | None = None
        self._hover_preview_frames: list[tk.PhotoImage] = []
        self._hover_preview_after_id: str | None = None
        self._hover_preview_temp_dir: Path | None = None
        self._hover_preview_image_label: tk.Label | None = None
        self._hover_preview_boomerang_indices: list[int] = []
        self._hover_preview_session: object | None = None

        self._build_ui()
        self._render_folders()
        self._render_buttons()
        self._load_catalog_async()

    def _build_ui(self) -> None:
        toolbar = ttk.Frame(self.root, padding=(12, 10, 12, 6))
        toolbar.pack(fill="x")
        ttk.Label(toolbar, text=APP_TITLE, font=("Segoe UI", 16, "bold")).pack(side="left")
        ttk.Button(toolbar, text="+ Dodaj prompt", command=self._add_prompt).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Przenies do folderu", command=self._move_selected_to_folder).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Edytuj", command=self._edit_selected).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Kontekst", command=self._edit_context_selected).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Usun", command=self._delete_selected).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Odswiez prompty", command=self._reload).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Odswiez katalog", command=self._load_catalog_async).pack(side="right", padx=(6, 0))

        hint = ttk.Label(
            self.root,
            text=(
                "Kliknij prompt: w «Strona Główna» od razu kopiuje do schowka; "
                "w pozostalych folderach — wybor artysty i obrazu z katalogu. PPM — edycja."
            ),
            padding=(12, 0, 12, 6),
            foreground="#555",
            wraplength=880,
        )
        hint.pack(fill="x")

        self.status_var = tk.StringVar(value="Ladowanie katalogu produktow...")
        ttk.Label(self.root, textvariable=self.status_var, padding=(12, 0, 12, 4)).pack(fill="x")

        body = ttk.Panedwindow(self.root, orient="horizontal")
        body.pack(fill="both", expand=True, padx=12, pady=(0, 0))

        folders_frame = ttk.LabelFrame(body, text="Foldery", padding=(6, 6, 6, 6))
        body.add(folders_frame, weight=0)

        folders_toolbar = ttk.Frame(folders_frame)
        folders_toolbar.pack(fill="x", pady=(0, 6))
        ttk.Button(folders_toolbar, text="+ Folder", command=self._add_folder).pack(side="left")
        ttk.Button(folders_toolbar, text="+ Podfolder", command=self._add_subfolder).pack(side="left", padx=(6, 0))
        ttk.Button(folders_toolbar, text="Usun folder", command=self._delete_active_folder).pack(side="left", padx=(6, 0))

        folder_tree_wrap = ttk.Frame(folders_frame)
        folder_tree_wrap.pack(fill="both", expand=True)
        self._folder_tree = ttk.Treeview(
            folder_tree_wrap,
            show="tree",
            selectmode="browse",
            height=18,
        )
        self._folder_tree.tag_configure("virtual", foreground="#555")
        folder_scroll = ttk.Scrollbar(folder_tree_wrap, orient="vertical", command=self._folder_tree.yview)
        self._folder_tree.configure(yscrollcommand=folder_scroll.set)
        self._folder_tree.pack(side="left", fill="both", expand=True)
        folder_scroll.pack(side="right", fill="y")
        self._folder_tree.bind("<<TreeviewSelect>>", lambda _e: self._on_folder_selected())

        prompts_frame = ttk.Frame(body)
        body.add(prompts_frame, weight=1)

        outer = ttk.Frame(prompts_frame)
        outer.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(outer, highlightthickness=0, borderwidth=0)
        scroll_y = ttk.Scrollbar(outer, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._buttons_frame = ttk.Frame(self._canvas)
        self._canvas_window = self._canvas.create_window((0, 0), window=self._buttons_frame, anchor="nw")

        self._buttons_frame.bind("<Configure>", self._on_frame_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel, add="+")

        preview_frame = ttk.LabelFrame(self.root, text="Podglad szablonu (placeholdery)", padding=8)
        preview_frame.pack(fill="x", padx=12, pady=(0, 6))
        self.preview_text = tk.Text(
            preview_frame,
            height=4,
            wrap="word",
            font=("Segoe UI", 10),
            state="disabled",
            relief="flat",
            background="#f8f8f8",
        )
        self.preview_text.pack(fill="x")

        context_frame = ttk.LabelFrame(
            self.root,
            text="Kontekst (notatki, grafiki, filmiki i pliki — nie ida do schowka przy «Kopiuj prompt»)",
            padding=8,
        )
        context_frame.pack(fill="x", padx=12, pady=(0, 12))
        self.context_preview = tk.Text(
            context_frame,
            height=3,
            wrap="word",
            font=("Segoe UI", 10),
            state="disabled",
            relief="flat",
            background="#f4f6f8",
            foreground="#333",
        )
        self.context_preview.pack(fill="x")
        self.context_images_preview = ttk.Frame(context_frame)
        self.context_images_preview.pack(fill="x", pady=(6, 0))
        self.context_files_preview = ttk.Frame(context_frame)
        self.context_files_preview.pack(fill="x", pady=(4, 0))
        self.context_videos_preview = ttk.Frame(context_frame)
        self.context_videos_preview.pack(fill="x", pady=(4, 0))

    def _on_frame_configure(self, _event: tk.Event | None = None) -> None:
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self._canvas.itemconfigure(self._canvas_window, width=event.width)

    def _on_mousewheel(self, event: tk.Event) -> None:
        try:
            widget = self.root.winfo_containing(event.x_root, event.y_root)
            if widget is None:
                return
            # Kursor nad osobnym oknem (np. Kontekst) — nie przewijaj listy promptow.
            if widget.winfo_toplevel() is not self.root:
                return
        except tk.TclError:
            return
        delta = int(-1 * (event.delta / 120))
        self._canvas.yview_scroll(delta, "units")
        self._hide_context_hover_preview()

    def _scrollable_frame(self, parent: tk.Misc) -> tuple[ttk.Frame, tk.Canvas]:
        """Ramka z pionowym scrollbarem — wypelnij zwracana ramke, potem _finish_scrollable_frame."""
        wrap = ttk.Frame(parent)
        wrap.pack(fill="both", expand=True)
        canvas = tk.Canvas(wrap, highlightthickness=0, bd=0)
        vsb = ttk.Scrollbar(wrap, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        inner = ttk.Frame(canvas)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _scrollregion(_evt: object = None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        inner.bind("<Configure>", _scrollregion)

        def _fill_width(evt: tk.Event) -> None:
            canvas.itemconfigure(win_id, width=evt.width)

        canvas.bind("<Configure>", _fill_width)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        return inner, canvas

    def _finish_scrollable_frame(self, canvas: tk.Canvas, inner: ttk.Frame) -> None:
        bind_mousewheel_to_canvas(canvas, inner, include_text=True)

    def _hide_context_hover_preview(self) -> None:
        self._hover_preview_session = None
        if self._hover_preview_after_id is not None:
            try:
                self.root.after_cancel(self._hover_preview_after_id)
            except tk.TclError:
                pass
            self._hover_preview_after_id = None
        if self._hover_preview_temp_dir is not None:
            shutil.rmtree(self._hover_preview_temp_dir, ignore_errors=True)
            self._hover_preview_temp_dir = None
        if self._hover_preview_win is not None:
            try:
                self._hover_preview_win.destroy()
            except tk.TclError:
                pass
            self._hover_preview_win = None
        self._hover_preview_photo = None
        self._hover_preview_frames.clear()
        self._hover_preview_image_label = None
        self._hover_preview_boomerang_indices.clear()

    def _resolved_video_preview_range(self, entry: PromptEntry, video_path: Path) -> tuple[float, float]:
        duration = probe_video_duration(video_path)
        return normalize_video_preview_range(
            entry.context_video_preview_start_sec,
            entry.context_video_preview_end_sec,
            duration=duration,
        )

    def _parse_video_preview_range_fields(
        self,
        start_text: str,
        end_text: str,
        *,
        video_path: Path | None = None,
        parent: tk.Misc | None = None,
    ) -> tuple[float, float] | None:
        try:
            start = float(str(start_text).strip().replace(",", "."))
            end = float(str(end_text).strip().replace(",", "."))
        except ValueError:
            messagebox.showwarning(
                APP_TITLE,
                "Podaj poprawny zakres podglądu wideo (sekundy, np. 0 i 3 lub 3.5 i 7.2).",
                parent=parent or self.root,
            )
            return None
        duration = probe_video_duration(video_path) if video_path and video_path.is_file() else None
        start, end = normalize_video_preview_range(start, end, duration=duration)
        if end <= start:
            messagebox.showwarning(
                APP_TITLE,
                "Sekunda końca musi być większa niż początek podglądu.",
                parent=parent or self.root,
            )
            return None
        return start, end

    def _position_hover_preview_window(self, win: tk.Toplevel, anchor: tk.Widget) -> None:
        win.update_idletasks()
        ax = anchor.winfo_rootx()
        ay = anchor.winfo_rooty()
        aw = anchor.winfo_width()
        ah = anchor.winfo_height()
        pw = win.winfo_width()
        ph = win.winfo_height()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = ax + aw + 10
        if x + pw > screen_w - 8:
            x = max(8, ax - pw - 10)
        y = ay + max(0, (ah - ph) // 2)
        y = max(8, min(y, screen_h - ph - 8))
        win.geometry(f"+{x}+{y}")

    def _hover_preview_mode(self, entry: PromptEntry) -> str:
        mode = (entry.context_hover_preview or HOVER_PREVIEW_IMAGE).strip().lower()
        if mode == HOVER_PREVIEW_VIDEO and entry.context_videos:
            return HOVER_PREVIEW_VIDEO
        if entry.context_images:
            return HOVER_PREVIEW_IMAGE
        if entry.context_videos:
            return HOVER_PREVIEW_VIDEO
        return mode

    def _show_context_hover_preview(self, entry: PromptEntry, anchor: tk.Widget) -> None:
        mode = self._hover_preview_mode(entry)
        if mode == HOVER_PREVIEW_VIDEO:
            self._show_video_hover_preview(entry, anchor)
        else:
            self._show_image_hover_preview(entry, anchor)

    def _show_image_hover_preview(self, entry: PromptEntry, anchor: tk.Widget) -> None:
        if not entry.context_images:
            return
        rel = entry.context_images[0]
        path = context_image_path(rel)
        if not path.is_file():
            return

        self._hide_context_hover_preview()

        try:
            from PIL import Image, ImageTk

            img = Image.open(path)
            img.thumbnail(_HOVER_PREVIEW_SIZE, Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
        except Exception:
            return

        win = tk.Toplevel(self.root)
        win.wm_overrideredirect(True)
        win.attributes("-topmost", True)
        self._hover_preview_win = win
        self._hover_preview_photo = photo

        shell = tk.Frame(win, bg="#4a4a4a", bd=1, relief="solid")
        shell.pack()
        tk.Label(shell, image=photo, bg="#1a1a1a", bd=0).pack(padx=2, pady=(2, 0))
        caption = path.name
        if len(entry.context_images) > 1:
            caption = f"{path.name}  (+{len(entry.context_images) - 1})"
        tk.Label(
            shell,
            text=caption,
            font=("Segoe UI", 8),
            bg="#2a2a2a",
            fg="#ddd",
            anchor="w",
            padx=6,
            pady=3,
        ).pack(fill="x")
        self._position_hover_preview_window(win, anchor)

    def _start_video_hover_playback(
        self,
        *,
        session: object,
        photos: list[tk.PhotoImage],
        fps: float,
        image_label: tk.Label,
    ) -> None:
        if session is not self._hover_preview_session or not photos:
            return
        self._hover_preview_frames = photos
        self._hover_preview_image_label = image_label
        indices = boomerang_frame_indices(len(photos))
        self._hover_preview_boomerang_indices = indices
        if len(indices) <= 1:
            image_label.configure(image=photos[0])
            return
        interval = max(33, int(1000 / max(MIN_PLAYBACK_FPS, fps)))
        state = {"pos": 0}

        def _tick() -> None:
            if session is not self._hover_preview_session or self._hover_preview_image_label is None:
                return
            state["pos"] = (state["pos"] + 1) % len(indices)
            photo_idx = indices[state["pos"]]
            self._hover_preview_image_label.configure(image=photos[photo_idx])
            self._hover_preview_after_id = self.root.after(interval, _tick)

        image_label.configure(image=photos[indices[0]])
        self._hover_preview_after_id = self.root.after(interval, _tick)

    def _show_video_hover_preview(self, entry: PromptEntry, anchor: tk.Widget) -> None:
        if not entry.context_videos:
            return
        rel = entry.context_videos[0]
        path = context_video_path(rel)
        if not path.is_file():
            return

        self._hide_context_hover_preview()
        session = object()
        self._hover_preview_session = session

        start_sec, end_sec = self._resolved_video_preview_range(entry, path)

        win = tk.Toplevel(self.root)
        win.wm_overrideredirect(True)
        win.attributes("-topmost", True)
        self._hover_preview_win = win

        shell = tk.Frame(win, bg="#4a4a4a", bd=1, relief="solid")
        shell.pack()
        media = tk.Frame(shell, bg="#1a1a1a")
        media.pack(padx=2, pady=(2, 0))
        image_label = tk.Label(media, bg="#1a1a1a", bd=0)
        image_label.pack()
        self._hover_preview_image_label = image_label

        poster = context_video_poster_path(rel)
        if not poster.is_file():
            extract_video_poster(path, poster, start_sec=start_sec)
        if poster.is_file():
            try:
                from PIL import Image, ImageTk

                img = Image.open(poster)
                img.thumbnail(_HOVER_PREVIEW_SIZE, Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                image_label.configure(image=photo)
                self._hover_preview_photo = photo
            except Exception:
                pass

        status_label = tk.Label(
            media,
            text="Ładowanie…",
            font=("Segoe UI", 8),
            bg="#1a1a1a",
            fg="#888",
        )
        status_label.pack(pady=(2, 0))

        caption = f"{path.name}  ({start_sec:g}–{end_sec:g}s)"
        if len(entry.context_videos) > 1:
            caption = f"{path.name}  ({start_sec:g}–{end_sec:g}s, +{len(entry.context_videos) - 1})"
        tk.Label(
            shell,
            text=caption,
            font=("Segoe UI", 8),
            bg="#2a2a2a",
            fg="#ddd",
            anchor="w",
            padx=6,
            pady=3,
        ).pack(fill="x")
        self._position_hover_preview_window(win, anchor)

        def _on_playback_ready(playback: object | None) -> None:
            if session is not self._hover_preview_session:
                if playback is not None and getattr(playback, "temp_dir", None):
                    shutil.rmtree(playback.temp_dir, ignore_errors=True)
                return
            if playback is None or not getattr(playback, "images", None):
                status_label.configure(text="Brak ffmpeg do odtwarzania")
                return
            temp_dir = getattr(playback, "temp_dir", None)
            if temp_dir:
                if self._hover_preview_temp_dir is not None:
                    shutil.rmtree(self._hover_preview_temp_dir, ignore_errors=True)
                self._hover_preview_temp_dir = temp_dir
            try:
                from PIL import ImageTk

                photos = [ImageTk.PhotoImage(img) for img in playback.images]
            except Exception:
                status_label.configure(text="Nie udalo sie odtworzyc")
                return
            status_label.destroy()
            self._start_video_hover_playback(
                session=session,
                photos=photos,
                fps=float(getattr(playback, "fps", 24.0)),
                image_label=image_label,
            )

        def _worker() -> None:
            playback = load_segment_playback(
                path,
                start_sec=start_sec,
                end_sec=end_sec,
                width=_HOVER_PREVIEW_SIZE[0],
            )
            self.root.after(0, lambda p=playback: _on_playback_ready(p))

        threading.Thread(target=_worker, daemon=True, name="bazapromptow-hover-video").start()

    def _bind_context_hover_preview(self, btn: tk.Button, entry: PromptEntry) -> None:
        if not entry.context_images and not entry.context_videos:
            return

        def _on_enter(_event: tk.Event) -> None:
            self._show_context_hover_preview(entry, btn)

        def _on_leave(_event: tk.Event) -> None:
            self._hide_context_hover_preview()

        btn.bind("<Enter>", _on_enter, add="+")
        btn.bind("<Leave>", _on_leave, add="+")

    def _render_image_strip(
        self,
        parent: tk.Misc,
        images: list[str],
        *,
        thumb_refs: list[tk.PhotoImage] | None = None,
        on_remove: Callable[[int], None] | None = None,
        on_copy: Callable[[str], None] | None = None,
    ) -> None:
        for child in parent.winfo_children():
            child.destroy()
        if not images:
            return
        refs = thumb_refs if thumb_refs is not None else self._context_thumb_refs
        for idx, rel in enumerate(images):
            cell = ttk.Frame(parent, padding=(0, 0, 8, 0))
            cell.pack(side="left")
            path = context_image_path(rel)
            photo = None
            try:
                from PIL import Image, ImageTk

                if path.is_file():
                    img = Image.open(path)
                    img.thumbnail(_CONTEXT_THUMB_SIZE)
                    photo = ImageTk.PhotoImage(img)
                    refs.append(photo)
            except Exception:
                photo = None
            if photo is not None:
                ttk.Label(cell, image=photo).pack()
            else:
                ttk.Label(cell, text=path.name, width=14, anchor="center").pack()
            ttk.Label(cell, text=path.name, font=("Segoe UI", 8), foreground="#666").pack()
            btn_row = ttk.Frame(cell)
            btn_row.pack(pady=(2, 0))
            if on_copy is not None:
                ttk.Button(btn_row, text="Schowek", width=8, command=lambda r=rel: on_copy(r)).pack(
                    side="left", padx=(0, 4)
                )
            if on_remove is not None:
                ttk.Button(btn_row, text="Usun", width=6, command=lambda i=idx: on_remove(i)).pack(side="left")

    def _copy_context_image(self, rel_path: str, *, parent: tk.Misc | None = None) -> None:
        path = context_image_path(rel_path)
        if not path.is_file():
            messagebox.showwarning(APP_TITLE, "Plik grafiki nie istnieje.", parent=parent or self.root)
            return
        try:
            from PIL import Image

            copy_pil_image_to_clipboard(Image.open(path))
            host = parent or self.root
            host.clipboard_append("")
            host.update()
            show_toast(host, "Grafika w schowku.", duration_ms=1200)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Nie udalo sie skopiowac grafiki:\n{exc}", parent=parent or self.root)

    def _render_file_strip(
        self,
        parent: tk.Misc,
        files: list[str],
        *,
        on_remove: Callable[[int], None] | None = None,
        on_open: Callable[[str], None] | None = None,
        on_copy_path: Callable[[str], None] | None = None,
    ) -> None:
        for child in parent.winfo_children():
            child.destroy()
        if not files:
            return
        for idx, rel in enumerate(files):
            path = context_file_path(rel)
            row = ttk.Frame(parent, padding=(0, 0, 0, 2))
            row.pack(fill="x")
            size_label = ""
            if path.is_file():
                size_label = f" ({_format_file_size(path.stat().st_size)})"
            ttk.Label(
                row,
                text=f"{path.name}{size_label}",
                font=("Segoe UI", 9),
                anchor="w",
            ).pack(side="left", fill="x", expand=True)
            btn_row = ttk.Frame(row)
            btn_row.pack(side="right")
            if on_open is not None:
                ttk.Button(btn_row, text="Otworz", width=8, command=lambda r=rel: on_open(r)).pack(
                    side="left", padx=(0, 4),
                )
            if on_copy_path is not None:
                ttk.Button(btn_row, text="Sciezka", width=8, command=lambda r=rel: on_copy_path(r)).pack(
                    side="left", padx=(0, 4),
                )
            if on_remove is not None:
                ttk.Button(btn_row, text="Usun", width=6, command=lambda i=idx: on_remove(i)).pack(side="left")

    def _open_context_file(self, rel_path: str, *, parent: tk.Misc | None = None) -> None:
        path = context_file_path(rel_path)
        if not path.is_file():
            messagebox.showwarning(APP_TITLE, "Plik nie istnieje.", parent=parent or self.root)
            return
        try:
            os.startfile(path)  # type: ignore[attr-defined]
        except OSError as exc:
            messagebox.showerror(APP_TITLE, f"Nie udalo sie otworzyc pliku:\n{exc}", parent=parent or self.root)

    def _copy_context_file_path(self, rel_path: str, *, parent: tk.Misc | None = None) -> None:
        path = context_file_path(rel_path)
        if not path.is_file():
            messagebox.showwarning(APP_TITLE, "Plik nie istnieje.", parent=parent or self.root)
            return
        host = parent or self.root
        try:
            host.clipboard_clear()
            host.clipboard_append(str(path.resolve()))
            host.update()
            show_toast(host, "Sciezka w schowku.", duration_ms=1200)
        except tk.TclError as exc:
            messagebox.showerror(APP_TITLE, str(exc), parent=host)

    def _video_poster_photo(
        self,
        rel: str,
        *,
        thumb_refs: list[tk.PhotoImage],
    ) -> tk.PhotoImage | None:
        poster = context_video_poster_path(rel)
        path = poster if poster.is_file() else context_video_path(rel)
        try:
            from PIL import Image, ImageTk

            if not path.is_file():
                return None
            img = Image.open(path)
            img.thumbnail(_CONTEXT_THUMB_SIZE, Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            thumb_refs.append(photo)
            return photo
        except Exception:
            return None

    def _render_video_strip(
        self,
        parent: tk.Misc,
        videos: list[str],
        *,
        thumb_refs: list[tk.PhotoImage] | None = None,
        on_remove: Callable[[int], None] | None = None,
        on_open: Callable[[str], None] | None = None,
        on_copy_path: Callable[[str], None] | None = None,
    ) -> None:
        for child in parent.winfo_children():
            child.destroy()
        if not videos:
            return
        refs = thumb_refs if thumb_refs is not None else self._context_thumb_refs
        for idx, rel in enumerate(videos):
            cell = ttk.Frame(parent, padding=(0, 0, 8, 0))
            cell.pack(side="left")
            path = context_video_path(rel)
            photo = self._video_poster_photo(rel, thumb_refs=refs)
            if photo is not None:
                ttk.Label(cell, image=photo).pack()
            else:
                ttk.Label(cell, text="▶", width=8, anchor="center", font=("Segoe UI", 16)).pack()
            ttk.Label(cell, text=path.name, font=("Segoe UI", 8), foreground="#666").pack()
            btn_row = ttk.Frame(cell)
            btn_row.pack(pady=(2, 0))
            if on_open is not None:
                ttk.Button(btn_row, text="Odtworz", width=8, command=lambda r=rel: on_open(r)).pack(
                    side="left", padx=(0, 4),
                )
            if on_copy_path is not None:
                ttk.Button(btn_row, text="Sciezka", width=8, command=lambda r=rel: on_copy_path(r)).pack(
                    side="left", padx=(0, 4),
                )
            if on_remove is not None:
                ttk.Button(btn_row, text="Usun", width=6, command=lambda i=idx: on_remove(i)).pack(side="left")

    def _open_context_video(self, rel_path: str, *, parent: tk.Misc | None = None) -> None:
        path = context_video_path(rel_path)
        if not path.is_file():
            messagebox.showwarning(APP_TITLE, "Plik wideo nie istnieje.", parent=parent or self.root)
            return
        try:
            os.startfile(path)  # type: ignore[attr-defined]
        except OSError as exc:
            messagebox.showerror(APP_TITLE, f"Nie udalo sie odtworzyc filmu:\n{exc}", parent=parent or self.root)

    def _copy_context_video_path(self, rel_path: str, *, parent: tk.Misc | None = None) -> None:
        path = context_video_path(rel_path)
        if not path.is_file():
            messagebox.showwarning(APP_TITLE, "Plik wideo nie istnieje.", parent=parent or self.root)
            return
        host = parent or self.root
        try:
            host.clipboard_clear()
            host.clipboard_append(str(path.resolve()))
            host.update()
            show_toast(host, "Sciezka w schowku.", duration_ms=1200)
        except tk.TclError as exc:
            messagebox.showerror(APP_TITLE, str(exc), parent=host)

    def _load_catalog_async(self) -> None:
        if self._catalog_loading:
            return
        self._catalog_loading = True
        self.status_var.set("Pobieram katalog produktow z Shopify...")

        def work() -> None:
            try:
                rows = load_catalog_rows(
                    on_progress=lambda s: self.root.after(
                        0, lambda m=s: self.status_var.set(m),
                    ),
                )
            except Exception as exc:
                self.root.after(
                    0,
                    lambda e=exc: (
                        self.status_var.set(f"Blad katalogu: {e}"),
                        messagebox.showerror(APP_TITLE, str(e), parent=self.root),
                    ),
                )
                self.root.after(0, lambda: setattr(self, "_catalog_loading", False))
                return

            def done() -> None:
                self._catalog_rows = rows
                self._catalog_loading = False
                n = len(self._store.prompts)
                self.status_var.set(
                    f"Katalog: {len(rows)} obraz(ow), {n} prompt(ow). Kliknij przycisk, aby wybrac produkt.",
                )

            self.root.after(0, done)

        threading.Thread(target=work, daemon=True, name="bazapromptow-catalog").start()

    def _reload(self) -> None:
        self._store = load_prompts()
        self._selected_id = None
        self._render_folders()
        self._render_buttons()
        self.status_var.set(f"Odswiezono prompty ({len(self._store.prompts)}).")

    def _folder_label(self, view_id: str) -> str:
        if view_id == FOLDER_ALL:
            return f"Wszystkie ({self._store.count_in_view(FOLDER_ALL)})"
        if view_id == FOLDER_UNCATEGORIZED:
            return f"Bez folderu ({self._store.count_in_view(FOLDER_UNCATEGORIZED)})"
        folder = self._store.find_folder(view_id)
        label = folder.label if folder else view_id
        return f"{label} ({self._store.count_in_view(view_id)})"

    def _active_real_folder_id(self) -> str | None:
        if self._active_folder_view in (FOLDER_ALL, FOLDER_UNCATEGORIZED):
            return None
        return self._active_folder_view

    def _render_folders(self) -> None:
        if self._folder_tree is None:
            return
        for item in self._folder_tree.get_children(""):
            self._folder_tree.delete(item)

        self._folder_tree.insert(
            "",
            "end",
            iid=FOLDER_ALL,
            text=self._folder_label(FOLDER_ALL),
            tags=("virtual",),
            open=True,
        )
        self._folder_tree.insert(
            "",
            "end",
            iid=FOLDER_UNCATEGORIZED,
            text=self._folder_label(FOLDER_UNCATEGORIZED),
            tags=("virtual",),
            open=True,
        )

        def insert_children(parent_id: str, tree_parent: str) -> None:
            for folder in self._store.folder_children(parent_id):
                self._folder_tree.insert(
                    tree_parent,
                    "end",
                    iid=folder.id,
                    text=self._folder_label(folder.id),
                    open=True,
                )
                insert_children(folder.id, folder.id)

        insert_children("", "")

        if self._active_folder_view in self._folder_tree.get_children("") or self._folder_tree.exists(self._active_folder_view):
            self._folder_tree.selection_set(self._active_folder_view)
            self._folder_tree.see(self._active_folder_view)
        else:
            self._active_folder_view = FOLDER_ALL
            self._folder_tree.selection_set(FOLDER_ALL)
            self._folder_tree.see(FOLDER_ALL)

    def _on_folder_selected(self) -> None:
        if self._folder_tree is None:
            return
        sel = self._folder_tree.selection()
        if not sel:
            return
        view_id = str(sel[0])
        self._active_folder_view = view_id
        self._render_buttons()

    def _render_buttons(self) -> None:
        self._hide_context_hover_preview()
        for child in self._buttons_frame.winfo_children():
            child.destroy()
        self._button_by_id.clear()

        prompts = self._store.prompts_in_view(self._active_folder_view)
        if not prompts:
            if self._active_folder_view == FOLDER_ALL:
                empty_text = "Brak promptow. Kliknij «Dodaj prompt», aby utworzyc pierwszy."
            else:
                empty_text = "Brak promptow w tym folderze. Kliknij prompt i uzyj «Przenies do folderu»."
            ttk.Label(
                self._buttons_frame,
                text=empty_text,
                foreground="#777",
                padding=20,
            ).pack(anchor="w")
            self._update_preview(None)
            return

        cols = 2
        for idx, entry in enumerate(prompts):
            row, col = divmod(idx, cols)
            btn = tk.Button(
                self._buttons_frame,
                text=entry.label or "(bez nazwy)",
                font=("Segoe UI", 10),
                relief="raised",
                bd=1,
                padx=10,
                pady=8,
                cursor="hand2",
                anchor="center",
                command=lambda e=entry: self._use_prompt(e),
            )
            btn.grid(row=row, column=col, sticky="ew", padx=6, pady=6)
            btn.bind("<Button-3>", lambda ev, e=entry: self._show_context_menu(ev, e))
            btn.bind("<Control-Button-1>", lambda _ev, e=entry: self._copy_raw(e), add="+")
            self._bind_context_hover_preview(btn, entry)
            self._button_by_id[entry.id] = btn

        for c in range(cols):
            self._buttons_frame.grid_columnconfigure(c, weight=1)

        if self._selected_id:
            self._highlight_selection()

    def _select(self, prompt_id: str) -> None:
        self._selected_id = prompt_id
        self._highlight_selection()
        entry = self._find(prompt_id)
        self._update_preview(entry)

    def _highlight_selection(self) -> None:
        for pid, btn in self._button_by_id.items():
            if pid == self._selected_id:
                btn.configure(bg="#b2dfdb", activebackground="#80cbc4")
            else:
                btn.configure(bg="SystemButtonFace", activebackground="SystemButtonFace")

    def _find(self, prompt_id: str) -> PromptEntry | None:
        for p in self._store.prompts:
            if p.id == prompt_id:
                return p
        return None

    def _update_preview(self, entry: PromptEntry | None) -> None:
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        self.context_preview.configure(state="normal")
        self.context_preview.delete("1.0", "end")
        if entry and entry.text.strip():
            preview = entry.text.strip()
            if len(preview) > 600:
                preview = preview[:600] + "..."
            self.preview_text.insert("1.0", preview)
        if entry and entry.context.strip():
            ctx = entry.context.strip()
            if len(ctx) > 400:
                ctx = ctx[:400] + "..."
            self.context_preview.insert("1.0", ctx)
        elif entry and (entry.context_images or entry.context_files or entry.context_videos):
            parts: list[str] = []
            if entry.context_images:
                parts.append(f"{len(entry.context_images)} graf.")
            if entry.context_videos:
                parts.append(f"{len(entry.context_videos)} film.")
            if entry.context_files:
                parts.append(f"{len(entry.context_files)} plik.")
            self.context_preview.insert("1.0", f"({', '.join(parts)} w kontekście)")
        else:
            self.context_preview.insert(
                "1.0",
                "(brak — użyj «Kontekst», aby dodać notatki, grafiki, filmiki lub pliki)",
            )
        self.preview_text.configure(state="disabled")
        self.context_preview.configure(state="disabled")
        self._context_thumb_refs.clear()
        if entry and entry.context_images:
            self._render_image_strip(
                self.context_images_preview,
                entry.context_images,
                on_copy=lambda rel: self._copy_context_image(rel),
            )
        else:
            for child in self.context_images_preview.winfo_children():
                child.destroy()
        if entry and entry.context_files:
            self._render_file_strip(
                self.context_files_preview,
                entry.context_files,
                on_open=lambda rel: self._open_context_file(rel),
                on_copy_path=lambda rel: self._copy_context_file_path(rel),
            )
        else:
            for child in self.context_files_preview.winfo_children():
                child.destroy()
        if entry and entry.context_videos:
            self._render_video_strip(
                self.context_videos_preview,
                entry.context_videos,
                on_open=lambda rel: self._open_context_video(rel),
                on_copy_path=lambda rel: self._copy_context_video_path(rel),
            )
        else:
            for child in self.context_videos_preview.winfo_children():
                child.destroy()

    def _is_homepage_prompt(self, entry: PromptEntry) -> bool:
        if not entry.folder_id:
            return False
        if entry.folder_id == DEFAULT_FOLDER_ID:
            return True
        return self._store.is_descendant_of(entry.folder_id, DEFAULT_FOLDER_ID)

    def _use_prompt(self, entry: PromptEntry) -> None:
        self._select(entry.id)
        if self._is_homepage_prompt(entry):
            self._copy_raw(entry, toast=f"Skopiowano: {entry.label}")
            return
        self._open_catalog_dialog(entry)

    def _open_catalog_dialog(self, entry: PromptEntry) -> None:
        if self._catalog_loading:
            messagebox.showinfo(
                APP_TITLE,
                "Katalog produktow jest jeszcze ladowany. Poczekaj chwile.",
                parent=self.root,
            )
            return
        if not self._catalog_rows:
            if messagebox.askyesno(
                APP_TITLE,
                "Katalog jest pusty lub nie zaladowany.\nPobrac produkty z Shopify teraz?",
                parent=self.root,
            ):
                self._load_catalog_async()
            return
        open_product_select_dialog(
            self.root,
            entry=entry,
            catalog_rows=self._catalog_rows,
            on_status=self.status_var.set,
        )

    def _copy_raw(self, entry: PromptEntry, *, toast: str | None = None) -> None:
        """Surowy szablon bez wyboru produktu."""
        text = (entry.text or "").strip()
        if not text:
            return
        self._select(entry.id)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()
        show_toast(self.root, toast or f"Szablon «{entry.label}» (bez podmiany)", duration_ms=1400)

    def _show_context_menu(self, event: tk.Event, entry: PromptEntry) -> None:
        self._select(entry.id)
        menu = tk.Menu(self.root, tearoff=0)
        if self._is_homepage_prompt(entry):
            menu.add_command(label="Kopiuj prompt", command=lambda: self._copy_raw(entry, toast=f"Skopiowano: {entry.label}"))
            menu.add_command(label="Wybierz obraz i kopiuj...", command=lambda: self._open_catalog_dialog(entry))
        else:
            menu.add_command(label="Wybierz obraz i kopiuj...", command=lambda: self._open_catalog_dialog(entry))
            menu.add_command(label="Kopiuj szablon (surowy)", command=lambda: self._copy_raw(entry))
        menu.add_command(label="Edytuj...", command=lambda: self._edit_prompt(entry))
        menu.add_command(label="Kontekst...", command=lambda: self._edit_context(entry))
        menu.add_separator()
        move_menu = tk.Menu(menu, tearoff=0)
        for folder, depth in self._store.folder_tree_with_depth():
            prefix = ("  " * depth) + ("└ " if depth else "")
            move_menu.add_command(
                label=f"{prefix}{folder.label}",
                command=lambda f=folder: self._move_prompts_to_folder([entry.id], f.id),
            )
        move_menu.add_command(
            label="Bez folderu",
            command=lambda: self._move_prompts_to_folder([entry.id], ""),
        )
        menu.add_cascade(label="Przenies do folderu", menu=move_menu)
        menu.add_separator()
        menu.add_command(label="Przesun w gore", command=lambda: self._move(entry.id, -1))
        menu.add_command(label="Przesun w dol", command=lambda: self._move(entry.id, 1))
        menu.add_separator()
        menu.add_command(label="Usun", command=lambda: self._delete_prompt(entry))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _embed_context_images_editor(
        self,
        parent: tk.Misc,
        *,
        prompt_id: str,
        initial_images: list[str],
        dialog_parent: tk.Misc,
    ) -> tuple[list[str], list[str], Callable[[], None]]:
        """Panel grafik kontekstu z podglądem. Zwraca (working, added_in_session, discard_additions)."""
        images_frame = ttk.LabelFrame(parent, text="Grafiki kontekstu", padding=(8, 8))
        images_frame.pack(fill="x", pady=(0, 10))

        images_toolbar = ttk.Frame(images_frame)
        images_toolbar.pack(fill="x", pady=(0, 6))
        images_row = ttk.Frame(images_frame)
        images_row.pack(fill="x")

        working_images: list[str] = list(initial_images)
        added_in_session: list[str] = []
        editor_thumb_refs: list[tk.PhotoImage] = []

        def _render_editor_images() -> None:
            self._render_image_strip(
                images_row,
                working_images,
                thumb_refs=editor_thumb_refs,
                on_remove=_remove_image,
                on_copy=lambda rel: self._copy_context_image(rel, parent=dialog_parent),
            )

        def _remove_image(idx: int) -> None:
            if idx < 0 or idx >= len(working_images):
                return
            working_images.pop(idx)
            _render_editor_images()

        def _import_sources(sources: list[object]) -> None:
            errors: list[str] = []
            imported = 0
            for source in sources:
                try:
                    if isinstance(source, Path):
                        rel = import_context_image(prompt_id, source)
                    else:
                        rel = import_context_image_pil(prompt_id, source)
                    working_images.append(rel)
                    added_in_session.append(rel)
                    imported += 1
                except Exception as exc:
                    label = source.name if isinstance(source, Path) else "schowek"
                    errors.append(f"{label}: {exc}")
            if imported:
                _render_editor_images()
                show_toast(dialog_parent, f"Wklejono {imported} graf.", duration_ms=1200)
            if errors:
                messagebox.showwarning(
                    APP_TITLE,
                    "Nie dodano części grafik:\n" + "\n".join(errors[:8]),
                    parent=dialog_parent,
                )

        def _add_images() -> None:
            paths = filedialog.askopenfilenames(
                parent=dialog_parent,
                title="Dodaj grafiki do kontekstu",
                filetypes=[
                    ("Obrazy", "*.jpg *.jpeg *.png *.webp *.gif *.bmp"),
                    ("Wszystkie pliki", "*.*"),
                ],
            )
            if not paths:
                return
            _import_sources([Path(raw) for raw in paths])

        def _paste_from_clipboard() -> None:
            try:
                sources = clipboard_images_for_import()
            except Exception as exc:
                messagebox.showerror(
                    APP_TITLE,
                    f"Nie udało się odczytać schowka:\n{exc}",
                    parent=dialog_parent,
                )
                return
            if not sources:
                messagebox.showinfo(
                    APP_TITLE,
                    "Schowek nie zawiera grafiki (bitmapy ani pliku obrazu).",
                    parent=dialog_parent,
                )
                return
            _import_sources(sources)

        def _discard_session_additions() -> None:
            for rel in added_in_session:
                if rel not in initial_images:
                    delete_context_image_file(rel)

        ttk.Button(images_toolbar, text="Dodaj grafikę…", command=_add_images).pack(side="left")
        ttk.Button(images_toolbar, text="Wklej ze schowka", command=_paste_from_clipboard).pack(
            side="left", padx=(8, 0),
        )

        def _on_paste_shortcut(_event: tk.Event) -> str:
            _paste_from_clipboard()
            return "break"

        for widget in (images_frame, images_toolbar, images_row):
            widget.bind("<Control-v>", _on_paste_shortcut)
            widget.bind("<Control-V>", _on_paste_shortcut)
        _render_editor_images()
        return working_images, added_in_session, _discard_session_additions

    def _embed_context_files_editor(
        self,
        parent: tk.Misc,
        *,
        prompt_id: str,
        initial_files: list[str],
        dialog_parent: tk.Misc,
    ) -> tuple[list[str], list[str], Callable[[], None]]:
        """Panel plikow kontekstu (inne niz grafiki)."""
        files_frame = ttk.LabelFrame(parent, text="Pliki kontekstu", padding=(8, 8))
        files_frame.pack(fill="x", pady=(0, 10))

        files_toolbar = ttk.Frame(files_frame)
        files_toolbar.pack(fill="x", pady=(0, 6))
        files_list = ttk.Frame(files_frame)
        files_list.pack(fill="x")

        working_files: list[str] = list(initial_files)
        added_in_session: list[str] = []

        def _render_editor_files() -> None:
            self._render_file_strip(
                files_list,
                working_files,
                on_remove=_remove_file,
                on_open=lambda rel: self._open_context_file(rel, parent=dialog_parent),
                on_copy_path=lambda rel: self._copy_context_file_path(rel, parent=dialog_parent),
            )

        def _remove_file(idx: int) -> None:
            if idx < 0 or idx >= len(working_files):
                return
            working_files.pop(idx)
            _render_editor_files()

        def _import_paths(paths: list[Path]) -> None:
            errors: list[str] = []
            imported = 0
            for raw in paths:
                try:
                    rel = import_context_file(prompt_id, raw)
                    working_files.append(rel)
                    added_in_session.append(rel)
                    imported += 1
                except Exception as exc:
                    errors.append(f"{raw.name}: {exc}")
            if imported:
                _render_editor_files()
                show_toast(dialog_parent, f"Dodano {imported} pl.", duration_ms=1200)
            if errors:
                messagebox.showwarning(
                    APP_TITLE,
                    "Nie dodano części plików:\n" + "\n".join(errors[:8]),
                    parent=dialog_parent,
                )

        def _add_files() -> None:
            paths = filedialog.askopenfilenames(
                parent=dialog_parent,
                title="Dodaj pliki do kontekstu",
            )
            if not paths:
                return
            _import_paths([Path(raw) for raw in paths])

        def _paste_from_clipboard() -> None:
            try:
                paths = clipboard_file_paths_for_import(exclude_images=True)
            except Exception as exc:
                messagebox.showerror(
                    APP_TITLE,
                    f"Nie udało się odczytać schowka:\n{exc}",
                    parent=dialog_parent,
                )
                return
            if not paths:
                messagebox.showinfo(
                    APP_TITLE,
                    "Schowek nie zawiera pliku do załączenia (skopiuj plik w Eksploratorze).",
                    parent=dialog_parent,
                )
                return
            _import_paths(paths)

        def _discard_session_additions() -> None:
            for rel in added_in_session:
                if rel not in initial_files:
                    delete_context_file(rel)

        ttk.Button(files_toolbar, text="Dodaj plik…", command=_add_files).pack(side="left")
        ttk.Button(files_toolbar, text="Wklej ze schowka", command=_paste_from_clipboard).pack(
            side="left", padx=(8, 0),
        )

        def _on_paste_shortcut(_event: tk.Event) -> str:
            _paste_from_clipboard()
            return "break"

        for widget in (files_frame, files_toolbar, files_list):
            widget.bind("<Control-v>", _on_paste_shortcut)
            widget.bind("<Control-V>", _on_paste_shortcut)
        _render_editor_files()
        return working_files, added_in_session, _discard_session_additions

    def _embed_hover_preview_selector(
        self,
        parent: tk.Misc,
        *,
        initial: str,
        start_sec: float = 0.0,
        end_sec: float = 0.0,
    ) -> tuple[tk.StringVar, tk.StringVar, tk.StringVar]:
        frame = ttk.LabelFrame(parent, text="Podgląd po najechaniu na prompt", padding=(8, 8))
        frame.pack(fill="x", pady=(0, 10))
        value = initial if initial in (HOVER_PREVIEW_IMAGE, HOVER_PREVIEW_VIDEO) else HOVER_PREVIEW_IMAGE
        preview_var = tk.StringVar(value=value)
        row = ttk.Frame(frame)
        row.pack(fill="x")
        ttk.Radiobutton(row, text="Grafika", variable=preview_var, value=HOVER_PREVIEW_IMAGE).pack(side="left")
        ttk.Radiobutton(row, text="Filmik", variable=preview_var, value=HOVER_PREVIEW_VIDEO).pack(
            side="left", padx=(12, 0),
        )
        ttk.Label(
            row,
            text="(pierwsza grafika lub pierwszy film z listy)",
            foreground="#666",
            font=("Segoe UI", 8),
        ).pack(side="left", padx=(12, 0))

        end_display = end_sec if end_sec > 0 else DEFAULT_VIDEO_PREVIEW_END_SEC
        start_var = tk.StringVar(value=f"{max(0.0, start_sec):g}")
        end_var = tk.StringVar(value=f"{end_display:g}")
        range_row = ttk.Frame(frame)
        range_row.pack(fill="x", pady=(8, 0))
        ttk.Label(range_row, text="Zakres podglądu filmiku (s, np. 3.5):").pack(side="left")
        ttk.Label(range_row, text="od").pack(side="left", padx=(10, 4))
        ttk.Entry(range_row, textvariable=start_var, width=7, font=("Segoe UI", 10)).pack(side="left")
        ttk.Label(range_row, text="do").pack(side="left", padx=(10, 4))
        ttk.Entry(range_row, textvariable=end_var, width=7, font=("Segoe UI", 10)).pack(side="left")
        ttk.Label(
            range_row,
            text="(boomerang: zapętlone do przodu i wstecz)",
            foreground="#666",
            font=("Segoe UI", 8),
        ).pack(side="left", padx=(12, 0))
        return preview_var, start_var, end_var

    def _embed_context_videos_editor(
        self,
        parent: tk.Misc,
        *,
        prompt_id: str,
        initial_videos: list[str],
        dialog_parent: tk.Misc,
    ) -> tuple[list[str], list[str], Callable[[], None]]:
        videos_frame = ttk.LabelFrame(parent, text="Filmiki kontekstu", padding=(8, 8))
        videos_frame.pack(fill="x", pady=(0, 10))

        videos_toolbar = ttk.Frame(videos_frame)
        videos_toolbar.pack(fill="x", pady=(0, 6))
        videos_row = ttk.Frame(videos_frame)
        videos_row.pack(fill="x")

        working_videos: list[str] = list(initial_videos)
        added_in_session: list[str] = []
        editor_thumb_refs: list[tk.PhotoImage] = []

        def _render_editor_videos() -> None:
            self._render_video_strip(
                videos_row,
                working_videos,
                thumb_refs=editor_thumb_refs,
                on_remove=_remove_video,
                on_open=lambda rel: self._open_context_video(rel, parent=dialog_parent),
                on_copy_path=lambda rel: self._copy_context_video_path(rel, parent=dialog_parent),
            )

        def _remove_video(idx: int) -> None:
            if idx < 0 or idx >= len(working_videos):
                return
            working_videos.pop(idx)
            _render_editor_videos()

        def _import_paths(paths: list[Path]) -> None:
            errors: list[str] = []
            imported = 0
            for raw in paths:
                try:
                    rel = import_context_video(prompt_id, raw)
                    working_videos.append(rel)
                    added_in_session.append(rel)
                    imported += 1
                except Exception as exc:
                    errors.append(f"{raw.name}: {exc}")
            if imported:
                _render_editor_videos()
                show_toast(dialog_parent, f"Dodano {imported} film.", duration_ms=1200)
            if errors:
                messagebox.showwarning(
                    APP_TITLE,
                    "Nie dodano części filmów:\n" + "\n".join(errors[:8]),
                    parent=dialog_parent,
                )

        def _add_videos() -> None:
            paths = filedialog.askopenfilenames(
                parent=dialog_parent,
                title="Dodaj filmiki do kontekstu",
                filetypes=[
                    ("Wideo", "*.mp4 *.webm *.mov *.avi *.mkv *.m4v *.wmv"),
                    ("Wszystkie pliki", "*.*"),
                ],
            )
            if not paths:
                return
            _import_paths([Path(raw) for raw in paths])

        def _paste_from_clipboard() -> None:
            try:
                paths = clipboard_video_paths_for_import()
            except Exception as exc:
                messagebox.showerror(
                    APP_TITLE,
                    f"Nie udało się odczytać schowka:\n{exc}",
                    parent=dialog_parent,
                )
                return
            if not paths:
                messagebox.showinfo(
                    APP_TITLE,
                    "Schowek nie zawiera pliku wideo (skopiuj film w Eksploratorze).",
                    parent=dialog_parent,
                )
                return
            _import_paths(paths)

        def _discard_session_additions() -> None:
            for rel in added_in_session:
                if rel not in initial_videos:
                    delete_context_video_file(rel)

        ttk.Button(videos_toolbar, text="Dodaj filmik…", command=_add_videos).pack(side="left")
        ttk.Button(videos_toolbar, text="Wklej ze schowka", command=_paste_from_clipboard).pack(
            side="left", padx=(8, 0),
        )

        def _on_paste_shortcut(_event: tk.Event) -> str:
            _paste_from_clipboard()
            return "break"

        for widget in (videos_frame, videos_toolbar, videos_row):
            widget.bind("<Control-v>", _on_paste_shortcut)
            widget.bind("<Control-V>", _on_paste_shortcut)
        _render_editor_videos()
        return working_videos, added_in_session, _discard_session_additions

    def _prompt_dialog(
        self,
        *,
        title: str,
        label: str = "",
        text: str = "",
        context: str = "",
        context_images: list[str] | None = None,
        context_files: list[str] | None = None,
        context_videos: list[str] | None = None,
        context_hover_preview: str = HOVER_PREVIEW_IMAGE,
        context_video_preview_start_sec: float = 0.0,
        context_video_preview_end_sec: float = 0.0,
        prompt_id: str | None = None,
        with_context: bool = False,
    ) -> tuple[str, str, str, list[str], list[str], list[str], str, float, float] | tuple[str, str] | None:
        win = tk.Toplevel(self.root)
        win.title(title)
        win.transient(self.root)
        win.grab_set()
        if with_context:
            position_toplevel_screen_center(win, 800, 820)
            win.minsize(580, 600)
        else:
            position_toplevel_screen_center(win, 640, 480)
            win.minsize(480, 320)

        body = ttk.Frame(win, padding=12)
        body.pack(fill="both", expand=True)

        scroll_canvas: tk.Canvas | None = None
        if with_context:
            form, scroll_canvas = self._scrollable_frame(body)
        else:
            form = body

        ttk.Label(form, text="Nazwa przycisku:").pack(anchor="w")
        label_var = tk.StringVar(value=label)
        label_entry = ttk.Entry(form, textvariable=label_var, font=("Segoe UI", 11))
        label_entry.pack(fill="x", pady=(4, 10))
        label_entry.focus_set()

        ttk.Label(form, text="Tresc promptu (uzyj [autor] i [tytuł]):").pack(anchor="w")
        prompt_height = 8 if with_context else 14
        text_box = tk.Text(form, wrap="word", font=("Consolas", 10), height=prompt_height)
        text_box.pack(fill="both", expand=not with_context, pady=(4, 10))
        if text:
            text_box.insert("1.0", text)

        context_box: tk.Text | None = None
        working_images: list[str] = []
        working_files: list[str] = []
        working_videos: list[str] = []
        saved_images: list[str] = []
        saved_files: list[str] = []
        saved_videos: list[str] = []
        discard_images: Callable[[], None] | None = None
        discard_files: Callable[[], None] | None = None
        discard_videos: Callable[[], None] | None = None
        hover_preview_var: tk.StringVar | None = None
        video_start_var: tk.StringVar | None = None
        video_end_var: tk.StringVar | None = None

        if with_context:
            if not prompt_id:
                raise ValueError("prompt_id is required when with_context=True")
            ttk.Label(
                form,
                text=(
                    "Kontekst (notatki, grafiki, filmiki i pliki — podgląd w aplikacji, "
                    "nie idą do schowka przy «Kopiuj prompt»)."
                ),
                wraplength=700,
                foreground="#555",
            ).pack(anchor="w", pady=(0, 4))
            ttk.Label(form, text="Notatki kontekstu:").pack(anchor="w")
            context_box = tk.Text(form, wrap="word", font=("Segoe UI", 10), height=5)
            context_box.pack(fill="x", pady=(4, 8))
            if context:
                context_box.insert("1.0", context)
            saved_images = list(context_images or [])
            working_images, _added, discard_images = self._embed_context_images_editor(
                form,
                prompt_id=prompt_id,
                initial_images=saved_images,
                dialog_parent=win,
            )
            saved_files = list(context_files or [])
            working_files, _added_files, discard_files = self._embed_context_files_editor(
                form,
                prompt_id=prompt_id,
                initial_files=saved_files,
                dialog_parent=win,
            )
            saved_videos = list(context_videos or [])
            working_videos, _added_videos, discard_videos = self._embed_context_videos_editor(
                form,
                prompt_id=prompt_id,
                initial_videos=saved_videos,
                dialog_parent=win,
            )
            hover_preview_var, video_start_var, video_end_var = self._embed_hover_preview_selector(
                form,
                initial=context_hover_preview,
                start_sec=context_video_preview_start_sec,
                end_sec=context_video_preview_end_sec,
            )

        result: dict[str, object | None] = {"value": None}

        def _ok() -> None:
            lbl = label_var.get().strip()
            txt = text_box.get("1.0", "end-1c")
            if not lbl:
                messagebox.showwarning(APP_TITLE, "Podaj nazwe przycisku.", parent=win)
                return
            if not txt.strip():
                messagebox.showwarning(APP_TITLE, "Prompt nie moze byc pusty.", parent=win)
                return
            if with_context and context_box is not None and hover_preview_var is not None:
                ctx = context_box.get("1.0", "end-1c")
                sync_context_images(saved_images, working_images)
                sync_context_files(saved_files, working_files)
                sync_context_videos(saved_videos, working_videos)
                preview_kind = hover_preview_var.get().strip().lower()
                if preview_kind not in (HOVER_PREVIEW_IMAGE, HOVER_PREVIEW_VIDEO):
                    preview_kind = HOVER_PREVIEW_IMAGE
                video_path = None
                if working_videos:
                    video_path = context_video_path(working_videos[0])
                range_vals = self._parse_video_preview_range_fields(
                    video_start_var.get() if video_start_var else "0",
                    video_end_var.get() if video_end_var else str(DEFAULT_VIDEO_PREVIEW_END_SEC),
                    video_path=video_path,
                    parent=win,
                )
                if range_vals is None:
                    return
                video_start, video_end = range_vals
                result["value"] = (
                    lbl,
                    txt,
                    ctx,
                    list(working_images),
                    list(working_files),
                    list(working_videos),
                    preview_kind,
                    video_start,
                    video_end,
                )
            else:
                result["value"] = (lbl, txt)
            win.destroy()

        def _cancel() -> None:
            if discard_images is not None:
                discard_images()
            if discard_files is not None:
                discard_files()
            if discard_videos is not None:
                discard_videos()
            win.destroy()

        btns = ttk.Frame(body)
        btns.pack(fill="x", pady=(8, 0))
        ttk.Button(btns, text="Anuluj", command=_cancel).pack(side="right")
        ttk.Button(btns, text="Zapisz", command=_ok).pack(side="right", padx=(0, 8))
        if with_context and context_box is not None:
            ttk.Button(
                btns,
                text="Wyczyść notatki",
                command=lambda: context_box.delete("1.0", "end"),
            ).pack(side="left")
        win.bind("<Escape>", lambda _e: _cancel())
        win.bind("<Control-Return>", lambda _e: _ok())
        win.protocol("WM_DELETE_WINDOW", _cancel)

        if scroll_canvas is not None:
            self._finish_scrollable_frame(scroll_canvas, form)

        self.root.wait_window(win)
        val = result["value"]
        if val is None:
            return None
        if with_context:
            row = val
            return (
                str(row[0]),
                str(row[1]),
                str(row[2]),
                list(row[3]),  # type: ignore[arg-type]
                list(row[4]),  # type: ignore[arg-type]
                list(row[5]),  # type: ignore[arg-type]
                str(row[6]),
                float(row[7]),  # type: ignore[arg-type]
                float(row[8]),  # type: ignore[arg-type]
            )
        return str(val[0]), str(val[1])  # type: ignore[index]

    def _add_prompt(self) -> None:
        prompt_id = new_prompt_id()
        data = self._prompt_dialog(
            title="Nowy prompt",
            with_context=True,
            prompt_id=prompt_id,
        )
        if not data:
            delete_prompt_context_attachments(prompt_id)
            return
        label, text, context, context_images, context_files, context_videos, hover_preview, video_start, video_end = data  # type: ignore[misc]
        entry = PromptEntry(
            id=prompt_id,
            label=label,
            text=text,
            sort_key=next_sort_key(self._store),
            folder_id="" if self._active_folder_view in (FOLDER_ALL, FOLDER_UNCATEGORIZED) else self._active_folder_view,
            context=context,
            context_images=list(context_images),
            context_files=list(context_files),
            context_videos=list(context_videos),
            context_hover_preview=hover_preview,
            context_video_preview_start_sec=video_start,
            context_video_preview_end_sec=video_end,
        )
        self._store.prompts.append(entry)
        save_prompts(self._store)
        self._selected_id = entry.id
        self._render_folders()
        self._render_buttons()
        self._update_preview(entry)
        self.status_var.set(f"Dodano: {label}")

    def _edit_selected(self) -> None:
        if not self._selected_id:
            messagebox.showinfo(APP_TITLE, "Zaznacz prompt (kliknij przycisk).", parent=self.root)
            return
        entry = self._find(self._selected_id)
        if entry:
            self._edit_prompt(entry)

    def _edit_prompt(self, entry: PromptEntry) -> None:
        data = self._prompt_dialog(
            title="Edytuj prompt",
            label=entry.label,
            text=entry.text,
        )
        if not data:
            return
        label, text = data
        entry.label = label
        entry.text = text
        save_prompts(self._store)
        self._render_folders()
        self._render_buttons()
        self._update_preview(entry)
        self.status_var.set(f"Zapisano: {label}")

    def _edit_context_selected(self) -> None:
        if not self._selected_id:
            messagebox.showinfo(APP_TITLE, "Zaznacz prompt (kliknij przycisk).", parent=self.root)
            return
        entry = self._find(self._selected_id)
        if entry:
            self._edit_context(entry)

    def _edit_context(self, entry: PromptEntry) -> None:
        self._select(entry.id)
        win = tk.Toplevel(self.root)
        win.title(f"Kontekst — {entry.label}")
        win.transient(self.root)
        win.grab_set()
        position_toplevel_screen_center(win, 800, 780)
        win.minsize(580, 560)

        body = ttk.Frame(win, padding=12)
        body.pack(fill="both", expand=True)

        form, scroll_canvas = self._scrollable_frame(body)

        ttk.Label(
            form,
            text=(
                "Notatki, grafiki, filmiki i pliki powiązane z tym promptem (podgląd w aplikacji).\n"
                "Przy «Kopiuj prompt» do schowka trafia wyłącznie szablon promptu.\n"
                "Wybierz, czy po najechaniu na prompt pokazać grafikę czy filmik."
            ),
            wraplength=700,
            foreground="#555",
        ).pack(anchor="w", pady=(0, 8))

        ttk.Label(form, text="Notatki:").pack(anchor="w")
        text_box = tk.Text(form, wrap="word", font=("Segoe UI", 10), height=7)
        text_box.pack(fill="x", pady=(4, 10))
        if entry.context:
            text_box.insert("1.0", entry.context)

        working_images, _added_in_session, discard_image_additions = self._embed_context_images_editor(
            form,
            prompt_id=entry.id,
            initial_images=list(entry.context_images),
            dialog_parent=win,
        )
        saved_images = list(entry.context_images)
        working_files, _added_files, discard_file_additions = self._embed_context_files_editor(
            form,
            prompt_id=entry.id,
            initial_files=list(entry.context_files),
            dialog_parent=win,
        )
        saved_files = list(entry.context_files)
        working_videos, _added_videos, discard_video_additions = self._embed_context_videos_editor(
            form,
            prompt_id=entry.id,
            initial_videos=list(entry.context_videos),
            dialog_parent=win,
        )
        saved_videos = list(entry.context_videos)
        hover_preview_var, video_start_var, video_end_var = self._embed_hover_preview_selector(
            form,
            initial=entry.context_hover_preview,
            start_sec=entry.context_video_preview_start_sec,
            end_sec=entry.context_video_preview_end_sec,
        )
        result: dict[str, bool] = {"saved": False}

        def _save() -> None:
            entry.context = text_box.get("1.0", "end-1c")
            sync_context_images(saved_images, working_images)
            sync_context_files(saved_files, working_files)
            sync_context_videos(saved_videos, working_videos)
            entry.context_images = list(working_images)
            entry.context_files = list(working_files)
            entry.context_videos = list(working_videos)
            preview_kind = hover_preview_var.get().strip().lower()
            entry.context_hover_preview = (
                preview_kind if preview_kind in (HOVER_PREVIEW_IMAGE, HOVER_PREVIEW_VIDEO) else HOVER_PREVIEW_IMAGE
            )
            video_path = context_video_path(working_videos[0]) if working_videos else None
            range_vals = self._parse_video_preview_range_fields(
                video_start_var.get(),
                video_end_var.get(),
                video_path=video_path,
                parent=win,
            )
            if range_vals is None:
                return
            entry.context_video_preview_start_sec, entry.context_video_preview_end_sec = range_vals
            save_prompts(self._store)
            self._update_preview(entry)
            n_text = len(entry.context.strip())
            n_img = len(entry.context_images)
            n_files = len(entry.context_files)
            n_videos = len(entry.context_videos)
            parts: list[str] = []
            if n_text:
                parts.append(f"{n_text} znaków")
            if n_img:
                parts.append(f"{n_img} graf.")
            if n_videos:
                parts.append(f"{n_videos} film.")
            if n_files:
                parts.append(f"{n_files} pl.")
            detail = f" ({', '.join(parts)})" if parts else " (pusty)"
            self.status_var.set(f"Kontekst zapisany: {entry.label}{detail}")
            result["saved"] = True
            win.destroy()

        def _cancel() -> None:
            if not result["saved"]:
                discard_image_additions()
                discard_file_additions()
                discard_video_additions()
            win.destroy()

        btns = ttk.Frame(body)
        btns.pack(fill="x", pady=(8, 0))
        ttk.Button(btns, text="Anuluj", command=_cancel).pack(side="right")
        ttk.Button(btns, text="Zapisz", command=_save).pack(side="right", padx=(0, 8))
        ttk.Button(btns, text="Wyczyść notatki", command=lambda: text_box.delete("1.0", "end")).pack(side="left")
        win.bind("<Escape>", lambda _e: _cancel())
        win.bind("<Control-Return>", lambda _e: _save())
        win.protocol("WM_DELETE_WINDOW", _cancel)
        text_box.focus_set()

        self._finish_scrollable_frame(scroll_canvas, form)

        self.root.wait_window(win)
        if result["saved"]:
            show_toast(self.root, f"Kontekst: {entry.label}", duration_ms=1200)

    def _delete_selected(self) -> None:
        if not self._selected_id:
            messagebox.showinfo(APP_TITLE, "Zaznacz prompt do usuniecia.", parent=self.root)
            return
        entry = self._find(self._selected_id)
        if entry:
            self._delete_prompt(entry)

    def _delete_prompt(self, entry: PromptEntry) -> None:
        if not messagebox.askyesno(
            APP_TITLE,
            f"Usunac prompt «{entry.label}»?",
            parent=self.root,
        ):
            return
        delete_prompt_context_attachments(
            entry.id,
            images=entry.context_images,
            files=entry.context_files,
            videos=entry.context_videos,
        )
        self._store.prompts = [p for p in self._store.prompts if p.id != entry.id]
        save_prompts(self._store)
        self._selected_id = None
        self._render_folders()
        self._render_buttons()
        self.status_var.set("Usunieto prompt.")

    def _move_selected_to_folder(self) -> None:
        if not self._selected_id:
            messagebox.showinfo(
                APP_TITLE,
                "Kliknij prompt, potem uzyj «Przenies do folderu».",
                parent=self.root,
            )
            return
        self._choose_folder_and_move([self._selected_id])

    def _choose_folder_and_move(self, prompt_ids: list[str]) -> None:
        folders = self._store.folder_tree_with_depth()
        if not folders:
            messagebox.showinfo(APP_TITLE, "Brak folderow.", parent=self.root)
            return

        win = tk.Toplevel(self.root)
        win.title("Przenies do folderu")
        win.transient(self.root)
        win.grab_set()
        position_toplevel_screen_center(win, 460, 360)
        win.minsize(380, 280)

        body = ttk.Frame(win, padding=12)
        body.pack(fill="both", expand=True)

        n = len(prompt_ids)
        ttk.Label(
            body,
            text=f"Przenies {n} prompt(ow) do:",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(0, 8))

        list_wrap = ttk.Frame(body)
        list_wrap.pack(fill="both", expand=True)
        folder_list = tk.Listbox(list_wrap, exportselection=False, font=("Segoe UI", 10), height=10)
        folder_scroll = ttk.Scrollbar(list_wrap, orient="vertical", command=folder_list.yview)
        folder_list.configure(yscrollcommand=folder_scroll.set)
        folder_list.pack(side="left", fill="both", expand=True)
        folder_scroll.pack(side="right", fill="y")

        folder_ids: list[str] = [""]
        folder_list.insert("end", "Bez folderu")
        for folder, depth in folders:
            prefix = ("  " * depth) + ("└ " if depth else "")
            folder_list.insert("end", f"{prefix}{folder.label}")
            folder_ids.append(folder.id)

        folder_list.selection_set(0)

        result: dict[str, str | None] = {"folder_id": None}

        def _ok() -> None:
            sel = folder_list.curselection()
            if not sel:
                return
            result["folder_id"] = folder_ids[int(sel[0])]
            win.destroy()

        def _cancel() -> None:
            win.destroy()

        btns = ttk.Frame(body)
        btns.pack(fill="x", pady=(12, 0))
        ttk.Button(btns, text="Anuluj", command=_cancel).pack(side="right")
        ttk.Button(btns, text="Przenies", command=_ok).pack(side="right", padx=(0, 8))
        folder_list.bind("<Double-Button-1>", lambda _e: _ok())
        win.bind("<Escape>", lambda _e: _cancel())
        win.protocol("WM_DELETE_WINDOW", _cancel)

        self.root.wait_window(win)
        if result["folder_id"] is None:
            return
        self._move_prompts_to_folder(prompt_ids, str(result["folder_id"]))

    def _move_prompts_to_folder(self, prompt_ids: list[str], folder_id: str) -> None:
        if not prompt_ids:
            return
        moved = 0
        for prompt_id in prompt_ids:
            entry = self._find(prompt_id)
            if not entry:
                continue
            entry.folder_id = folder_id
            moved += 1
        if not moved:
            return
        save_prompts(self._store)
        self._render_folders()
        self._render_buttons()
        if folder_id:
            folder = self._store.find_folder(folder_id)
            target = folder.label if folder else folder_id
        else:
            target = "Bez folderu"
        self.status_var.set(f"Przeniesiono {moved} prompt(ow) do: {target}.")

    def _create_folder(self, *, parent_id: str, title: str) -> None:
        label = simpledialog.askstring(
            APP_TITLE,
            title,
            parent=self.root,
        )
        if not label:
            return
        label = label.strip()
        if not label:
            messagebox.showwarning(APP_TITLE, "Podaj nazwe folderu.", parent=self.root)
            return
        siblings = {f.label.lower() for f in self._store.folder_children(parent_id)}
        if label.lower() in siblings:
            messagebox.showwarning(APP_TITLE, "Folder o takiej nazwie juz istnieje na tym poziomie.", parent=self.root)
            return
        folder = FolderEntry(
            id=new_folder_id(),
            label=label,
            sort_key=next_folder_sort_key(self._store, parent_id),
            parent_id=parent_id,
        )
        self._store.folders.append(folder)
        save_prompts(self._store)
        self._active_folder_view = folder.id
        self._render_folders()
        self._render_buttons()
        self.status_var.set(f"Dodano folder: {self._store.folder_path_label(folder.id)}")

    def _add_folder(self) -> None:
        self._create_folder(parent_id="", title="Nazwa nowego folderu:")

    def _add_subfolder(self) -> None:
        parent_id = self._active_real_folder_id()
        if not parent_id:
            messagebox.showinfo(
                APP_TITLE,
                "Wybierz folder nadrzedny (nie «Wszystkie» ani «Bez folderu»), potem kliknij «+ Podfolder».",
                parent=self.root,
            )
            return
        parent = self._store.find_folder(parent_id)
        parent_label = parent.label if parent else parent_id
        self._create_folder(
            parent_id=parent_id,
            title=f"Nazwa podfolderu w «{parent_label}»:",
        )

    def _delete_active_folder(self) -> None:
        view_id = self._active_folder_view
        if view_id in (FOLDER_ALL, FOLDER_UNCATEGORIZED):
            messagebox.showinfo(
                APP_TITLE,
                "Wybierz konkretny folder do usuniecia (nie «Wszystkie» ani «Bez folderu»).",
                parent=self.root,
            )
            return
        if view_id == DEFAULT_FOLDER_ID:
            messagebox.showinfo(APP_TITLE, "Folder «Strona Główna» jest domyslny i nie moze byc usuniety.", parent=self.root)
            return
        folder = self._store.find_folder(view_id)
        if not folder:
            return
        remove_ids = self._store.descendant_folder_ids(view_id)
        count = sum(1 for p in self._store.prompts if p.folder_id in remove_ids)
        subfolders = len(remove_ids) - 1
        msg = f"Folder «{folder.label}» zawiera {count} prompt(ow)."
        if subfolders:
            msg += f"\nUsuniete zostana tez {subfolders} podfolder(y)."
        msg += "\nPrompty trafia do «Bez folderu». Kontynuowac?"
        if count and not messagebox.askyesno(APP_TITLE, msg, parent=self.root):
            return
        if not count and subfolders and not messagebox.askyesno(APP_TITLE, msg, parent=self.root):
            return
        for prompt in self._store.prompts:
            if prompt.folder_id in remove_ids:
                prompt.folder_id = ""
        self._store.folders = [f for f in self._store.folders if f.id not in remove_ids]
        save_prompts(self._store)
        self._active_folder_view = FOLDER_ALL
        self._render_folders()
        self._render_buttons()
        self.status_var.set(f"Usunieto folder: {folder.label}")

    def _move(self, prompt_id: str, direction: int) -> None:
        ordered = self._store.sorted()
        ids = [p.id for p in ordered]
        if prompt_id not in ids:
            return
        idx = ids.index(prompt_id)
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(ids):
            return
        ids[idx], ids[new_idx] = ids[new_idx], ids[idx]
        for sort_key, pid in enumerate(ids):
            entry = self._find(pid)
            if entry:
                entry.sort_key = sort_key
        save_prompts(self._store)
        self._render_buttons()
        self._select(prompt_id)


def main() -> None:
    root = tk.Tk()
    BazaPromptowApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
