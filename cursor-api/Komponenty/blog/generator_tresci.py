"""Okno 'Generator tresci' - toplevel dialog.

Flow:
1. Uzytkownik wpisuje/edytuje temat (mozna tez podac URL zdjecia).
2. Klikniecie "Prompt dla Opus" lub "Prompt dla GPT":
   - prompt jest zbudowany (uwzglednia obecne tytuly z cache - zeby nie duplikowac),
   - AUTOMATYCZNIE kopiowany do schowka systemowego (autokopiowanie),
   - pokazany w textarea na gorze dialogu.
3. Uzytkownik wkleja prompt do Cursor/Claude/ChatGPT i dostaje odpowiedz (JSON).
4. Klikniecie "Wklej odpowiedz ze schowka" - wkleja (autowklejanie) do dolnej textarea.
5. "Podglad" - parsuje JSON i pokazuje checkliste jezykow (7 checkboxow) + preview PL.
6. "Wyslij na bloga" - tworzy artykul w Shopify (PL) + rejestruje tlumaczenia (EN/DE/FR/ES/NL/IT).
"""

from __future__ import annotations

import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from Komponenty._shared.toast import show_toast

from . import preview, prompts, shopify_blog, storage

_LANG_LABELS = {
    "pl": "Polski",
    "en": "Angielski",
    "de": "Niemiecki",
    "fr": "Francuski",
    "es": "Hiszpanski",
    "nl": "Holenderski",
    "it": "Wloski",
}


def open_content_generator(
    parent: tk.Misc,
    *,
    initial_topic: str = "",
    topic_id: str = "",
) -> tk.Toplevel:
    """Otwiera okno generatora tresci."""
    dlg = tk.Toplevel(parent)
    dlg.title("Blog - Generator tresci")
    dlg.geometry("1100x780")
    dlg.minsize(900, 650)
    try:
        dlg.transient(parent.winfo_toplevel())
    except (tk.TclError, AttributeError):
        pass

    state: dict[str, Any] = {
        "parsed": None,          # dict z parsowanej odpowiedzi LLM
        "topic_id": topic_id,    # jesli przyszlismy z propozycji - id do oznaczenia "used"
        "sending": False,
    }

    # ---------- layout ----------
    root = ttk.Frame(dlg, padding=(10, 8))
    root.pack(fill="both", expand=True)

    # ----- Input row: temat + URL zdjecia -----
    input_frame = ttk.LabelFrame(root, text="1. Temat posta + opcjonalnie obrazek", padding=8)
    input_frame.pack(fill="x", pady=(0, 6))
    input_frame.columnconfigure(1, weight=1)

    ttk.Label(input_frame, text="Temat:").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=2)
    topic_var = tk.StringVar(value=initial_topic)
    topic_entry = ttk.Entry(input_frame, textvariable=topic_var, font=("Segoe UI", 10))
    topic_entry.grid(row=0, column=1, columnspan=4, sticky="ew", pady=2)

    ttk.Label(input_frame, text="Obrazek (URL https:// lub lokalny plik):").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=2)
    image_var = tk.StringVar(value="")
    image_entry = ttk.Entry(input_frame, textvariable=image_var)
    image_entry.grid(row=1, column=1, sticky="ew", pady=2)
    image_status = ttk.Label(input_frame, text="", foreground="#666", font=("Segoe UI", 9))
    image_status.grid(row=1, column=2, sticky="w", padx=(6, 0))

    def _pick_image() -> None:
        path = filedialog.askopenfilename(
            title="Wybierz obrazek",
            filetypes=[
                ("Obrazki", "*.jpg *.jpeg *.png *.webp *.gif"),
                ("Wszystkie", "*.*"),
            ],
            parent=dlg,
        )
        if path:
            image_var.set(path)

    ttk.Button(input_frame, text="...", width=3, command=_pick_image).grid(row=1, column=3, padx=(4, 0))
    ttk.Button(
        input_frame, text="X", width=3,
        command=lambda: (image_var.set(""), image_status.configure(text="")),
    ).grid(row=1, column=4, padx=(4, 0))

    ttk.Label(input_frame, text="Autor:").grid(row=2, column=0, sticky="w", padx=(0, 6), pady=2)
    author_var = tk.StringVar(value="GicleeArt")
    ttk.Entry(input_frame, textvariable=author_var, width=22).grid(row=2, column=1, sticky="w", pady=2)

    def _update_image_status(*_args: Any) -> None:
        val = image_var.get().strip()
        if not val:
            image_status.configure(text="(bez zdjecia)", foreground="#999")
            return
        if val.startswith("http://") or val.startswith("https://"):
            image_status.configure(text="URL ✓", foreground="#1b5e20")
            return
        p = Path(val).expanduser()
        if p.is_file():
            size_kb = p.stat().st_size // 1024
            image_status.configure(text=f"plik ✓ ({size_kb} KB)", foreground="#1b5e20")
        else:
            image_status.configure(text="plik NIE istnieje", foreground="#c62828")

    image_var.trace_add("write", _update_image_status)
    _update_image_status()

    # ----- Prompt area -----
    prompt_frame = ttk.LabelFrame(
        root, text="2. Prompt - klik kopiuje do schowka, wklej do Opus/GPT", padding=8,
    )
    prompt_frame.pack(fill="both", expand=True, pady=6)

    btn_row = ttk.Frame(prompt_frame)
    btn_row.pack(fill="x", pady=(0, 6))
    ttk.Button(
        btn_row, text="📋 Prompt dla Claude Opus",
        command=lambda: _build_and_copy_prompt(dlg, topic_var, image_var, prompt_text, variant="opus"),
    ).pack(side="left")
    ttk.Button(
        btn_row, text="📋 Prompt dla GPT",
        command=lambda: _build_and_copy_prompt(dlg, topic_var, image_var, prompt_text, variant="gpt"),
    ).pack(side="left", padx=(6, 0))
    ttk.Button(
        btn_row, text="Kopiuj ponownie",
        command=lambda: _copy_to_clipboard(dlg, prompt_text.get("1.0", "end-1c")),
    ).pack(side="left", padx=(16, 0))
    ttk.Label(
        btn_row, text="(klikniecie generuje prompt i OD RAZU kopiuje go do schowka)",
        foreground="#666",
    ).pack(side="left", padx=(10, 0))

    prompt_container = ttk.Frame(prompt_frame)
    prompt_container.pack(fill="both", expand=True)
    prompt_text = tk.Text(prompt_container, wrap="word", height=10, font=("Consolas", 9))
    prompt_sb = ttk.Scrollbar(prompt_container, orient="vertical", command=prompt_text.yview)
    prompt_text.configure(yscrollcommand=prompt_sb.set)
    prompt_text.pack(side="left", fill="both", expand=True)
    prompt_sb.pack(side="right", fill="y")

    # ----- Response area -----
    resp_frame = ttk.LabelFrame(
        root, text="3. Odpowiedz z LLM (JSON z 7 wersjami jezykowymi)", padding=8,
    )
    resp_frame.pack(fill="both", expand=True, pady=6)

    resp_btn_row = ttk.Frame(resp_frame)
    resp_btn_row.pack(fill="x", pady=(0, 6))
    ttk.Button(
        resp_btn_row, text="📥 Wklej odpowiedz ze schowka",
        command=lambda: _paste_from_clipboard(dlg, response_text),
    ).pack(side="left")
    ttk.Button(
        resp_btn_row, text="Wyczysc",
        command=lambda: response_text.delete("1.0", "end"),
    ).pack(side="left", padx=(6, 0))
    ttk.Button(
        resp_btn_row, text="🔍 Sprawdz odpowiedz",
        command=lambda: _validate_response(dlg, response_text, state, lang_vars, preview_label),
    ).pack(side="left", padx=(16, 0))
    ttk.Button(
        resp_btn_row, text="🌐 Podglad w przegladarce",
        command=lambda: _open_preview(dlg, state, response_text, lang_vars, preview_label),
    ).pack(side="left", padx=(6, 0))

    resp_container = ttk.Frame(resp_frame)
    resp_container.pack(fill="both", expand=True)
    response_text = tk.Text(resp_container, wrap="word", height=10, font=("Consolas", 9))
    resp_sb = ttk.Scrollbar(resp_container, orient="vertical", command=response_text.yview)
    response_text.configure(yscrollcommand=resp_sb.set)
    response_text.pack(side="left", fill="both", expand=True)
    resp_sb.pack(side="right", fill="y")

    # ----- Languages + send -----
    send_frame = ttk.LabelFrame(root, text="4. Wybierz jezyki i wyslij na bloga Shopify", padding=8)
    send_frame.pack(fill="x", pady=(6, 0))

    lang_vars: dict[str, tk.BooleanVar] = {}
    langs_row = ttk.Frame(send_frame)
    langs_row.pack(fill="x")
    ttk.Label(langs_row, text="Jezyki:").pack(side="left")
    for code, label in _LANG_LABELS.items():
        v = tk.BooleanVar(value=True)
        lang_vars[code] = v
        ttk.Checkbutton(langs_row, text=label, variable=v).pack(side="left", padx=(10, 0))

    action_row = ttk.Frame(send_frame)
    action_row.pack(fill="x", pady=(8, 0))
    preview_label = ttk.Label(action_row, text="(najpierw 'Sprawdz odpowiedz' lub 'Podglad')", foreground="#888")
    preview_label.pack(side="left")

    send_btn = ttk.Button(
        action_row, text="🚀 Wyslij na bloga",
        command=lambda: _send_article(
            dlg, state, topic_var, image_var, author_var, lang_vars, preview_label, send_btn,
        ),
    )
    send_btn.pack(side="right")
    ttk.Button(action_row, text="Zamknij", command=dlg.destroy).pack(side="right", padx=(0, 6))

    # ESC zamyka
    dlg.bind("<Escape>", lambda _e: dlg.destroy())

    # Auto-focus na temacie
    topic_entry.focus_set()

    return dlg


# ---------------------------------------------------------------------------
# Akcje
# ---------------------------------------------------------------------------

def _build_and_copy_prompt(
    dlg: tk.Toplevel,
    topic_var: tk.StringVar,
    image_var: tk.StringVar,
    prompt_text: tk.Text,
    *,
    variant: str,
) -> None:
    topic = topic_var.get().strip()
    if not topic:
        messagebox.showwarning("Brak tematu", "Wpisz temat posta.", parent=dlg)
        return
    image_url = image_var.get().strip()

    # Obecne tytuly z cache - zeby LLM nie duplikowal tematyki.
    cache = storage.load_articles_cache()
    existing_titles = [str(a.get("title") or "") for a in (cache.get("articles") or []) if a.get("title")]

    if variant == "opus":
        prompt = prompts.build_content_prompt_opus(topic, image_url=image_url, existing_titles=existing_titles)
    else:
        prompt = prompts.build_content_prompt_gpt(topic, image_url=image_url, existing_titles=existing_titles)

    prompt_text.delete("1.0", "end")
    prompt_text.insert("1.0", prompt)
    _copy_to_clipboard(dlg, prompt)


def _copy_to_clipboard(dlg: tk.Toplevel, content: str) -> None:
    if not content.strip():
        return
    try:
        dlg.clipboard_clear()
        dlg.clipboard_append(content)
        dlg.update()  # wymuszenie by inne apki zobaczyly schowek
    except tk.TclError:
        return
    show_toast(dlg, "Skopiowano do schowka", duration_ms=1200)


def _paste_from_clipboard(dlg: tk.Toplevel, target: tk.Text) -> None:
    try:
        content = dlg.clipboard_get()
    except tk.TclError:
        messagebox.showwarning("Pusty schowek", "Schowek jest pusty lub niedostepny.", parent=dlg)
        return
    target.delete("1.0", "end")
    target.insert("1.0", content)
    show_toast(dlg, "Wklejono ze schowka", duration_ms=1000)


def _open_preview(
    dlg: tk.Toplevel,
    state: dict[str, Any],
    response_text: tk.Text,
    lang_vars: dict[str, tk.BooleanVar],
    preview_label: ttk.Label,
) -> None:
    """Podglad HTML w przegladarce. Jesli JSON nie byl jeszcze zwalidowany - walidujemy teraz."""
    if not state.get("parsed"):
        _validate_response(dlg, response_text, state, lang_vars, preview_label)
    data = state.get("parsed")
    if not data:
        return
    try:
        path = preview.open_preview_in_browser(data)
    except Exception as e:  # noqa: BLE001
        messagebox.showerror("Blad podgladu", f"Nie udalo sie wygenerowac podgladu:\n{e}", parent=dlg)
        return
    show_toast(dlg, f"Otwarto: {path.name}", duration_ms=1200)


def _validate_response(
    dlg: tk.Toplevel,
    response_text: tk.Text,
    state: dict[str, Any],
    lang_vars: dict[str, tk.BooleanVar],
    preview_label: ttk.Label,
) -> None:
    raw = response_text.get("1.0", "end-1c").strip()
    if not raw:
        messagebox.showwarning("Brak odpowiedzi", "Wklej najpierw odpowiedz z LLM.", parent=dlg)
        return
    try:
        data = prompts.parse_content_response(raw)
    except ValueError as e:
        state["parsed"] = None
        preview_label.configure(text=f"❌ {e}", foreground="#c62828")
        messagebox.showerror("Blad parsowania", str(e), parent=dlg)
        return

    state["parsed"] = data
    langs = data.get("languages") or {}
    found = [code for code in lang_vars if code in langs]
    missing = [code for code in lang_vars if code not in langs]
    pl_title = (langs.get("pl") or {}).get("title") or "(brak)"
    preview_label.configure(
        text=f"✅ OK. PL: \"{pl_title[:60]}\" | jezyki: {', '.join(found)}",
        foreground="#1b5e20",
    )
    for code, v in lang_vars.items():
        v.set(code in langs)

    if missing:
        messagebox.showinfo(
            "Czesciowe tlumaczenia",
            f"Odpowiedz zawiera {len(found)} jezykow. Brakuje: {', '.join(missing)}.\n"
            "Mozesz wyslac to co jest.",
            parent=dlg,
        )


def _send_article(
    dlg: tk.Toplevel,
    state: dict[str, Any],
    topic_var: tk.StringVar,
    image_var: tk.StringVar,
    author_var: tk.StringVar,
    lang_vars: dict[str, tk.BooleanVar],
    preview_label: ttk.Label,
    send_btn: ttk.Button,
) -> None:
    if state.get("sending"):
        return
    data = state.get("parsed")
    if not data:
        messagebox.showwarning(
            "Brak zwalidowanej odpowiedzi",
            "Najpierw kliknij 'Sprawdz odpowiedz'.",
            parent=dlg,
        )
        return

    langs = data.get("languages") or {}
    pl = langs.get("pl") or {}
    if not (pl.get("title") and pl.get("body_html")):
        messagebox.showerror(
            "Brak wersji PL",
            "Wersja PL (bazowa) jest wymagana - brak title/body_html.",
            parent=dlg,
        )
        return

    selected_locales = [
        code for code, v in lang_vars.items()
        if code != "pl" and v.get() and code in langs
    ]

    image_url = image_var.get().strip()
    author = author_var.get().strip() or "GicleeArt"

    if not messagebox.askyesno(
        "Wyslac post?",
        f"Zostanie opublikowany post:\n\n"
        f"PL: {pl.get('title')}\n"
        f"Tlumaczenia: {', '.join(selected_locales) if selected_locales else '(tylko PL)'}\n\n"
        f"Kontynuowac?",
        parent=dlg,
    ):
        return

    state["sending"] = True
    send_btn.configure(state="disabled", text="Wysylam...")
    preview_label.configure(text="⏳ Wysylam na Shopify...", foreground="#555")

    def _worker() -> None:
        try:
            shop, token = shopify_blog.load_session()
            blogs = shopify_blog.list_blogs(shop, token)
            if not blogs:
                raise shopify_blog.ShopifyError(
                    "Brak blogow w sklepie Shopify. Utworz bloga w Shopify Admin -> Sklep internetowy -> Blog."
                )
            blog_id = int(blogs[0].get("id") or 0)

            # 1) Utworz artykul w PL
            tags = pl.get("tags") or []
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]
            article = shopify_blog.create_article(
                shop, token, blog_id,
                title=str(pl.get("title") or ""),
                body_html=str(pl.get("body_html") or ""),
                summary_html=str(pl.get("summary_html") or ""),
                tags=list(tags),
                author=author,
                image_src=image_url,
                image_alt=str(pl.get("title") or ""),
                seo_title=str(pl.get("seo_title") or ""),
                seo_description=str(pl.get("seo_description") or ""),
                published=True,
            )
            article_id = int(article.get("id") or 0)
            if not article_id:
                raise shopify_blog.ShopifyError(f"Shopify nie zwrocil id artykulu: {article}")

            # 2) Tlumaczenia
            translation_errors: list[str] = []
            for locale in selected_locales:
                loc = langs.get(locale) or {}
                try:
                    shopify_blog.register_article_translations(
                        shop, token,
                        article_id=article_id,
                        locale=locale,
                        title=str(loc.get("title") or ""),
                        body_html=str(loc.get("body_html") or ""),
                        summary_html=str(loc.get("summary_html") or ""),
                        seo_title=str(loc.get("seo_title") or ""),
                        seo_description=str(loc.get("seo_description") or ""),
                    )
                except shopify_blog.ShopifyError as e:
                    translation_errors.append(f"{locale}: {e}")

            # 3) Oznaczamy temat jako uzyty (jesli przyszlismy z propozycji)
            topic_id = state.get("topic_id") or ""
            if topic_id:
                storage.mark_topic_used(topic_id, True)

            # 4) Odswiez cache artykulow (bez blokowania - best effort)
            try:
                all_articles = shopify_blog.list_all_articles(shop, token)
                storage.save_articles_cache(all_articles)
            except shopify_blog.ShopifyError:
                pass

            admin_url = shopify_blog.article_admin_url(shop, blog_id, article_id)
            summary = (
                f"✅ Post opublikowany!\n\n"
                f"ID: {article_id}\nTytul: {article.get('title')}\n"
                f"Tlumaczenia: {len(selected_locales) - len(translation_errors)}/{len(selected_locales)}\n\n"
                f"Admin: {admin_url}"
            )
            if translation_errors:
                summary += "\n\nBledy tlumaczen:\n" + "\n".join(translation_errors)

            def _on_success() -> None:
                preview_label.configure(text=f"✅ ID {article_id} - opublikowano", foreground="#1b5e20")
                messagebox.showinfo("Sukces", summary, parent=dlg)

            dlg.after(0, _on_success)
        except Exception as e:  # noqa: BLE001
            err_msg = str(e)

            def _on_error() -> None:
                preview_label.configure(text=f"❌ {err_msg[:80]}", foreground="#c62828")
                messagebox.showerror("Blad wysylki", err_msg, parent=dlg)

            dlg.after(0, _on_error)
        finally:
            def _reset() -> None:
                state["sending"] = False
                send_btn.configure(state="normal", text="🚀 Wyslij na bloga")
            dlg.after(0, _reset)

    threading.Thread(target=_worker, daemon=True).start()
