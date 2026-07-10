"""Grafiki ze schowka i ich podglad w Notatniku."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from . import gui as _gui
from .clipboard_images import (
    iter_render_segments,
    make_asset_destination,
    markdown_image_reference,
    resolve_local_image,
    rewrite_local_image_links_for_move,
)
from .interactive_gui import InteractiveNotatnikApp


class ClipboardImageNotatnikApp(InteractiveNotatnikApp):
    """Notatnik z reczna kolejnoscia, dwuklikiem i grafikami ze schowka."""

    def _build_ui(self) -> None:
        super()._build_ui()
        self._preview_image_refs: list[object] = []

        ttk.Separator(self.md_toolbar, orient="vertical").pack(
            side="left",
            fill="y",
            padx=6,
        )
        ttk.Button(
            self.md_toolbar,
            text="Wklej grafike",
            command=lambda: self._paste_image_from_clipboard(show_no_image=True),
        ).pack(side="left", padx=1)

        # <<Paste>> obejmuje Ctrl+V oraz standardowe polecenie Wklej systemu Tk.
        # Zwracamy "break" tylko wtedy, gdy schowek rzeczywiscie zawiera grafike.
        self.edit_text.bind("<<Paste>>", self._on_edit_paste, add="+")

    def _on_edit_paste(self, _event: tk.Event | None = None) -> str | None:
        if not self._edit_mode or self._current_path is None:
            return None
        pasted = self._paste_image_from_clipboard(show_no_image=False)
        return "break" if pasted else None

    def _read_clipboard_image(self):
        try:
            from PIL import Image, ImageGrab
        except ImportError as exc:  # pragma: no cover - zalezy od srodowiska
            raise RuntimeError(
                "Brakuje biblioteki Pillow. Zainstaluj ja poleceniem: "
                "python -m pip install Pillow"
            ) from exc

        try:
            clipboard = ImageGrab.grabclipboard()
        except (OSError, RuntimeError) as exc:
            raise RuntimeError(f"Nie udalo sie odczytac schowka: {exc}") from exc

        if isinstance(clipboard, Image.Image):
            return clipboard.copy()

        if isinstance(clipboard, list):
            for raw_path in clipboard:
                path = Path(str(raw_path))
                if not path.is_file():
                    continue
                try:
                    with Image.open(path) as source:
                        return source.copy()
                except (OSError, ValueError):
                    continue
        return None

    def _paste_image_from_clipboard(self, *, show_no_image: bool) -> bool:
        if self._current_path is None:
            if show_no_image:
                messagebox.showinfo(
                    "Brak notatki",
                    "Najpierw wybierz notatke i wejdz w tryb edycji.",
                    parent=self.root,
                )
            return False
        if not self._edit_mode:
            self._enter_edit_mode()

        try:
            image = self._read_clipboard_image()
        except RuntimeError as exc:
            messagebox.showerror("Wklej grafike", str(exc), parent=self.root)
            return False

        if image is None:
            if show_no_image:
                messagebox.showinfo(
                    "Wklej grafike",
                    "Schowek nie zawiera grafiki ani obslugiwnego pliku obrazu.",
                    parent=self.root,
                )
            return False

        destination = make_asset_destination(self.notes_dir)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")

        try:
            from PIL import Image, ImageOps

            prepared = ImageOps.exif_transpose(image)
            if prepared.mode not in {"RGB", "RGBA"}:
                prepared = prepared.convert("RGBA" if "A" in prepared.getbands() else "RGB")

            # Chroni notatki przed przypadkowym zapisaniem ogromnego zrzutu.
            max_size = (2560, 2560)
            if prepared.width > max_size[0] or prepared.height > max_size[1]:
                prepared = prepared.copy()
                prepared.thumbnail(max_size, Image.Resampling.LANCZOS)

            prepared.save(temporary, format="PNG", optimize=True)
            temporary.replace(destination)
        except (OSError, ValueError) as exc:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            messagebox.showerror(
                "Wklej grafike",
                f"Nie udalo sie zapisac grafiki:\n{exc}",
                parent=self.root,
            )
            return False

        reference = markdown_image_reference(self._current_path, destination)
        line_before = self.edit_text.get("insert linestart", "insert")
        prefix = "" if not line_before.strip() else "\n"
        self.edit_text.insert("insert", f"{prefix}{reference}\n")
        self.edit_text.focus_set()
        self.edit_text.see("insert")
        self._highlight_edit_links()
        _gui.show_toast(self.root, "Wklejono grafike do notatki")
        return True

    def _render_preview(self, content: str) -> None:
        if not hasattr(self, "_preview_image_refs"):
            self._preview_image_refs = []
        self._preview_image_refs.clear()

        if self._current_path is None:
            super()._render_preview(content)
            return

        try:
            from PIL import Image, ImageOps, ImageTk
            from Komponenty._shared.help_dialog import _render_markdown, _setup_tags
        except ImportError:
            super()._render_preview(content)
            return

        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        _setup_tags(self.preview_text)
        self.preview_text.update_idletasks()
        available_width = self.preview_text.winfo_width() - 32
        max_width = max(320, min(1100, available_width if available_width > 100 else 760))

        for kind, first, second in iter_render_segments(content):
            if kind == "markdown":
                _render_markdown(self.preview_text, first)
                continue

            alt, raw_target = first, second
            image_path = resolve_local_image(
                self._current_path,
                raw_target,
                self.notes_dir,
            )
            if image_path is None:
                self.preview_text.insert(
                    "end",
                    f"[Nie znaleziono grafiki: {alt or raw_target}]\n",
                    "quote",
                )
                continue

            try:
                with Image.open(image_path) as source:
                    prepared = ImageOps.exif_transpose(source).copy()
                prepared.thumbnail((max_width, 900), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(prepared)
            except (OSError, ValueError, tk.TclError):
                self.preview_text.insert(
                    "end",
                    f"[Nie mozna wyswietlic grafiki: {alt or image_path.name}]\n",
                    "quote",
                )
                continue

            self.preview_text.image_create("end", image=photo)
            self._preview_image_refs.append(photo)
            self.preview_text.insert("end", "\n")

        self.preview_text.configure(state="disabled")

    def _fixup_favorites_after_move(self, old: Path, new: Path) -> None:
        super()._fixup_favorites_after_move(old, new)
        if (
            old.suffix.casefold() != ".md"
            or new.suffix.casefold() != ".md"
            or old.parent.resolve() == new.parent.resolve()
            or not new.is_file()
        ):
            return

        try:
            content = new.read_text(encoding="utf-8")
            rewritten = rewrite_local_image_links_for_move(
                content,
                old,
                new,
                self.notes_dir,
            )
            if rewritten != content:
                new.write_text(rewritten, encoding="utf-8")
        except OSError as exc:
            messagebox.showwarning(
                "Przeniesiono notatke",
                "Notatka zostala przeniesiona, ale nie udalo sie zaktualizowac "
                f"sciezek grafik:\n{exc}",
                parent=self.root,
            )


def main() -> None:
    """Uruchamia pelny wariant Notatnika."""
    original_class = _gui.NotatnikApp
    _gui.NotatnikApp = ClipboardImageNotatnikApp
    try:
        _gui.main()
    finally:
        _gui.NotatnikApp = original_class
