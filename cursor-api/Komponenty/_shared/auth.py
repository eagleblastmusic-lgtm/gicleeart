"""Uwierzytelnianie dla aplikacji Giclee.

Cel: zabezpieczenie launchera GicleeApp + webowego serwera produkcji prostym
haslem. Haslo NIE jest trzymane plaintext - liczymy pbkdf2_hmac z saltem,
porownujemy przez `hmac.compare_digest` (stala-czasowa, odporne na timing).

Lokalizacja pliku auth:
- Windows: `%APPDATA%/Giclee/auth.json`
- macOS:   `~/Library/Application Support/Giclee/auth.json`
- Linux:   `~/.config/Giclee/auth.json`

Plik NIE jest w repo - trzymany per-user, per-machine. Jesli sie zgubi,
aplikacja zapyta o ustawienie hasla od nowa.

Struktura auth.json:
{
  "version": 1,
  "algo": "pbkdf2_sha256",
  "iterations": 480000,
  "salt_hex": "...",
  "hash_hex": "...",
  "created_at": "2026-04-20T12:00:00"
}
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from Komponenty._shared.window_geometry import position_toplevel_screen_center

_ALGO = "pbkdf2_sha256"
_ITERATIONS = 480_000  # OWASP 2023+ rekomendacja dla PBKDF2-SHA256
_SALT_BYTES = 32

_MIN_PASSWORD_LENGTH = 6


def _app_data_dir() -> Path:
    """Zwraca folder konfiguracji aplikacji per-user (niezalezny od Explorer/cwd)."""
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / "Giclee"
        return Path.home() / "AppData" / "Roaming" / "Giclee"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Giclee"
    return Path.home() / ".config" / "Giclee"


def _auth_file() -> Path:
    return _app_data_dir() / "auth.json"


def is_configured() -> bool:
    """True jesli haslo juz jest ustawione (plik auth.json istnieje i ma prawidlowy format)."""
    p = _auth_file()
    if not p.is_file():
        return False
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return all(k in data for k in ("algo", "iterations", "salt_hex", "hash_hex"))
    except (OSError, json.JSONDecodeError):
        return False


def _hash(password: str, *, salt: bytes, iterations: int = _ITERATIONS) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)


def set_password(password: str) -> None:
    """Ustawia nowe haslo (nadpisuje poprzednie jesli bylo)."""
    if not password or len(password) < _MIN_PASSWORD_LENGTH:
        raise ValueError(f"Haslo musi miec przynajmniej {_MIN_PASSWORD_LENGTH} znakow.")
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = _hash(password, salt=salt)
    p = _auth_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "algo": _ALGO,
        "iterations": _ITERATIONS,
        "salt_hex": salt.hex(),
        "hash_hex": digest.hex(),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    p.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    # Windows - nie mozemy ustawic chmod 600 tak jak na Unix, ale APPDATA
    # jest per-user i domyslnie niedostepne dla innych userow systemowych.
    if not sys.platform.startswith("win"):
        try:
            os.chmod(p, 0o600)
        except OSError:
            pass


def verify_password(password: str) -> bool:
    """Porownuje wpisane haslo z hashem w auth.json. Stala-czasowo."""
    if not is_configured():
        return False
    try:
        data = json.loads(_auth_file().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    salt = bytes.fromhex(str(data.get("salt_hex") or ""))
    expected_hash = bytes.fromhex(str(data.get("hash_hex") or ""))
    iterations = int(data.get("iterations") or _ITERATIONS)
    try:
        actual_hash = _hash(password or "", salt=salt, iterations=iterations)
    except ValueError:
        return False
    return hmac.compare_digest(expected_hash, actual_hash)


def reset_password() -> bool:
    """Usuwa plik auth.json (zresetuje haslo; przy nastepnym starcie apka zapyta o nowe).

    UZYWAJ ostroznie - nie ma potwierdzenia tozsamosci. Sensowne tylko z konsoli
    gdy user sam sie zalogowal do swojego konta systemowego.
    """
    p = _auth_file()
    if p.is_file():
        try:
            p.unlink()
            return True
        except OSError:
            return False
    return False


# ---------------------------------------------------------------------------
# Tkinter UI helpers
# ---------------------------------------------------------------------------

def prompt_setup_or_login(parent: Any | None = None) -> bool:
    """Pokazuje dialog logowania (lub ustawiania hasla przy pierwszym uruchomieniu).

    Zwraca True przy sukcesie. Przy anulowaniu lub wielokrotnym bledzie - False.
    """
    import tkinter as tk

    # Jesli nie ma roota - tworzymy tymczasowy. Nie withdraw - widoczny jako
    # male okno-placeholder, bo inaczej dialog Toplevel moze sie ukryc za
    # innymi oknami i wygladac jakby apka nie startowala.
    created_root = False
    if parent is None:
        root = tk.Tk()
        root.title("GicleeApp")
        root.geometry("1x1+0+0")  # malutkie, zaraz zostanie zniszczone
        # Nie ukrywamy - trzymamy widoczne 1px zeby taskbar pokazywal apke i
        # dialog mial rodzica do topmost/focus.
        root.attributes("-alpha", 0.0)  # calkowicie przezroczyste
        try:
            root.attributes("-topmost", True)
        except tk.TclError:
            pass
        root.update_idletasks()
        created_root = True
        parent = root

    try:
        if not is_configured():
            return _show_setup_dialog(parent)
        return _show_login_dialog(parent)
    finally:
        if created_root:
            try:
                parent.destroy()
            except tk.TclError:
                pass


def _show_setup_dialog(parent: Any) -> bool:
    import tkinter as tk
    from tkinter import messagebox, ttk

    dlg = tk.Toplevel(parent)
    dlg.title("GicleeApp - ustaw haslo")
    dlg.resizable(False, False)
    try:
        dlg.transient(parent.winfo_toplevel())
    except (tk.TclError, AttributeError):
        pass
    # Wyciagnij dialog na wierzch + centrowanie
    try:
        dlg.attributes("-topmost", True)
    except tk.TclError:
        pass
    position_toplevel_screen_center(dlg, 480, 280)
    dlg.lift()
    dlg.focus_force()
    dlg.grab_set()

    frame = ttk.Frame(dlg, padding=16)
    frame.pack(fill="both", expand=True)

    ttk.Label(
        frame,
        text="Pierwsze uruchomienie GicleeApp",
        font=("Segoe UI", 13, "bold"),
    ).pack(anchor="w")
    ttk.Label(
        frame,
        text=(
            "Ustaw haslo, ktorym bedziesz logowac sie do aplikacji\n"
            "(chroni dane klientow - adresy, zamowienia).\n\n"
            f"Minimum {_MIN_PASSWORD_LENGTH} znakow. Haslo zostanie\n"
            "zapisane lokalnie (zaszyfrowane) i NIE wychodzi z komputera."
        ),
        justify="left",
        foreground="#555",
    ).pack(anchor="w", pady=(2, 10))

    pwd_row = ttk.Frame(frame)
    pwd_row.pack(fill="x", pady=2)
    ttk.Label(pwd_row, text="Haslo:", width=12).pack(side="left")
    pwd_var = tk.StringVar()
    ttk.Entry(pwd_row, textvariable=pwd_var, show="●", width=28).pack(
        side="left", fill="x", expand=True
    )

    pwd2_row = ttk.Frame(frame)
    pwd2_row.pack(fill="x", pady=2)
    ttk.Label(pwd2_row, text="Powtorz:", width=12).pack(side="left")
    pwd2_var = tk.StringVar()
    ttk.Entry(pwd2_row, textvariable=pwd2_var, show="●", width=28).pack(
        side="left", fill="x", expand=True
    )

    result = {"ok": False}

    def _save() -> None:
        p1 = pwd_var.get()
        p2 = pwd2_var.get()
        if p1 != p2:
            messagebox.showerror("Haslo", "Hasla nie sa takie same.", parent=dlg)
            return
        if len(p1) < _MIN_PASSWORD_LENGTH:
            messagebox.showerror(
                "Haslo",
                f"Haslo musi miec przynajmniej {_MIN_PASSWORD_LENGTH} znakow.",
                parent=dlg,
            )
            return
        try:
            set_password(p1)
        except (ValueError, OSError) as e:
            messagebox.showerror("Haslo", f"Nie udalo sie zapisac hasla:\n{e}", parent=dlg)
            return
        messagebox.showinfo(
            "Haslo", "Haslo ustawione.\nOd teraz kazdy start aplikacji bedzie wymagal go wpisania.",
            parent=dlg,
        )
        result["ok"] = True
        dlg.destroy()

    btns = ttk.Frame(frame)
    btns.pack(fill="x", pady=(14, 0))
    ttk.Button(btns, text="Anuluj (zamknij apke)", command=dlg.destroy).pack(side="right")
    ttk.Button(btns, text="Ustaw haslo", command=_save).pack(side="right", padx=(0, 6))
    dlg.bind("<Return>", lambda _e: _save())
    dlg.bind("<Escape>", lambda _e: dlg.destroy())
    dlg.protocol("WM_DELETE_WINDOW", dlg.destroy)

    dlg.wait_window()
    return result["ok"]


def _show_login_dialog(parent: Any) -> bool:
    import tkinter as tk
    from tkinter import messagebox, ttk

    dlg = tk.Toplevel(parent)
    dlg.title("GicleeApp - logowanie")
    dlg.resizable(False, False)
    try:
        dlg.transient(parent.winfo_toplevel())
    except (tk.TclError, AttributeError):
        pass
    try:
        dlg.attributes("-topmost", True)
    except tk.TclError:
        pass
    position_toplevel_screen_center(dlg, 380, 200)
    dlg.lift()
    dlg.focus_force()
    dlg.grab_set()

    frame = ttk.Frame(dlg, padding=16)
    frame.pack(fill="both", expand=True)
    ttk.Label(
        frame, text="GicleeApp - logowanie",
        font=("Segoe UI", 13, "bold"),
    ).pack(anchor="w")
    ttk.Label(
        frame, text="Wpisz haslo dostepu:",
        foreground="#555",
    ).pack(anchor="w", pady=(2, 10))

    pwd_var = tk.StringVar()
    pwd_entry = ttk.Entry(frame, textvariable=pwd_var, show="●", width=30)
    pwd_entry.pack(fill="x")
    pwd_entry.focus_set()

    attempt = {"count": 0}
    result = {"ok": False}

    def _try() -> None:
        attempt["count"] += 1
        if verify_password(pwd_var.get()):
            result["ok"] = True
            dlg.destroy()
            return
        pwd_var.set("")
        if attempt["count"] >= 3:
            messagebox.showerror(
                "Logowanie",
                "Trzykrotnie bledne haslo. Aplikacja zostanie zamknieta.",
                parent=dlg,
            )
            dlg.destroy()
            return
        messagebox.showwarning(
            "Logowanie",
            f"Bledne haslo. Pozostale proby: {3 - attempt['count']}",
            parent=dlg,
        )

    btns = ttk.Frame(frame)
    btns.pack(fill="x", pady=(14, 0))
    ttk.Button(btns, text="Zamknij", command=dlg.destroy).pack(side="right")
    ttk.Button(btns, text="Zaloguj", command=_try).pack(side="right", padx=(0, 6))

    dlg.bind("<Return>", lambda _e: _try())
    dlg.bind("<Escape>", lambda _e: dlg.destroy())
    dlg.protocol("WM_DELETE_WINDOW", dlg.destroy)

    dlg.wait_window()
    return result["ok"]
