"""Dialog 'Ustawienia Meta API' - edycja tokenow 4 kanalow.

Zapisuje do data/cykl/meta_credentials.json (gitignore).

Dla FB: page_id + access_token.
Dla IG: ig_user_id + access_token (ten sam Page Access Token co dla FB powiazanego).

Przycisk 'Test polaczenia' dla kazdego kanalu - robi lekki GET do Graph API:
- FB: GET /{page_id}?fields=id,name&access_token=...
- IG: GET /{ig_user_id}?fields=id,username&access_token=...
"""

from __future__ import annotations

import tkinter as tk
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from collections.abc import Callable
from tkinter import messagebox, ttk

from Komponenty._shared.window_geometry import position_toplevel_screen_center

from . import meta_publisher, platforms_cykl as _cp, storage
from .meta_token_status import refresh_token_metadata_in_file


def open_meta_config_dialog(parent: tk.Misc, on_saved: Callable[[], None] | None = None) -> tk.Toplevel:
    dlg = tk.Toplevel(parent)
    dlg.title("Cykl - Ustawienia Meta API")
    position_toplevel_screen_center(dlg, 820, 720)
    dlg.minsize(740, 640)
    try:
        dlg.transient(parent.winfo_toplevel())
    except (tk.TclError, AttributeError):
        pass

    outer = ttk.Frame(dlg, padding=(14, 12))
    outer.pack(fill="both", expand=True)

    # Header
    hdr = ttk.Frame(outer)
    hdr.pack(fill="x")
    ttk.Label(
        hdr, text="Konfiguracja tokenow Meta Graph API",
        font=("Segoe UI", 14, "bold"),
    ).pack(side="left")
    hdr_btns = ttk.Frame(hdr)
    hdr_btns.pack(side="right")
    ttk.Button(
        hdr_btns, text="Instrukcja odnowy",
        command=lambda: _show_renewal_help(dlg),
    ).pack(side="right", padx=(6, 0))
    ttk.Button(
        hdr_btns, text="Pokaz instrukcje",
        command=lambda: _show_setup_help(dlg),
    ).pack(side="right")

    # Info
    info_text = (
        "Wprowadz tokeny i identyfikatory dla 4 kanalow (po 1 stronie FB + 1 konto IG\n"
        "Business Account na jezyk). Access Token = long-lived Page Access Token.\n"
        "Dla IG uzywamy tego samego tokenu co dla powiazanej strony FB.\n\n"
        "Pelna konfiguracja: przycisk 'Pokaz instrukcje'. Gdy token wygasnie: 'Instrukcja odnowy'.\n\n"
        "Wymagane scopes: pages_show_list, pages_manage_posts, pages_read_engagement,\n"
        "instagram_basic, instagram_content_publish."
    )
    ttk.Label(outer, text=info_text, foreground="#555", justify="left").pack(
        fill="x", pady=(6, 10)
    )

    # Ladujemy obecne credentiale
    creds = storage.load_meta_credentials()

    # Referencje do wpisow - zeby zebrac przy zapisie
    entries: dict[str, dict[str, tk.StringVar]] = {}
    show_tokens: dict[str, tk.BooleanVar] = {}
    token_entries: dict[str, ttk.Entry] = {}

    nb = ttk.Notebook(outer)
    nb.pack(fill="both", expand=True)

    for ch in _cp.all_channels():
        tab = ttk.Frame(nb, padding=(12, 10))
        nb.add(tab, text=f"{ch.label}")

        # Info z profilem
        top = ttk.Frame(tab)
        top.pack(fill="x", pady=(0, 8))
        ttk.Label(top, text=f"Strona: {ch.page_url}", foreground="#1976d2").pack(side="left")
        ttk.Button(
            top, text="Otworz",
            command=lambda u=ch.page_url: webbrowser.open(u),
        ).pack(side="left", padx=(8, 0))

        grid = ttk.Frame(tab)
        grid.pack(fill="x")
        grid.columnconfigure(1, weight=1)

        current = creds.get(ch.code, {})
        entries[ch.code] = {}

        row = 0

        if ch.platform == "fb":
            ttk.Label(grid, text="Page ID:").grid(row=row, column=0, sticky="w", pady=4, padx=(0, 8))
            var_pid = tk.StringVar(value=current.get("page_id", ""))
            ttk.Entry(grid, textvariable=var_pid, width=40).grid(row=row, column=1, sticky="ew", pady=4)
            entries[ch.code]["page_id"] = var_pid
            row += 1
        else:
            ttk.Label(grid, text="Instagram User ID:").grid(row=row, column=0, sticky="w", pady=4, padx=(0, 8))
            var_iid = tk.StringVar(value=current.get("ig_user_id", ""))
            ttk.Entry(grid, textvariable=var_iid, width=40).grid(row=row, column=1, sticky="ew", pady=4)
            entries[ch.code]["ig_user_id"] = var_iid
            row += 1

        ttk.Label(grid, text="Access Token:").grid(row=row, column=0, sticky="nw", pady=4, padx=(0, 8))
        token_row = ttk.Frame(grid)
        token_row.grid(row=row, column=1, sticky="ew", pady=4)
        token_row.columnconfigure(0, weight=1)
        var_tok = tk.StringVar(value=current.get("access_token", ""))
        tok_entry = ttk.Entry(token_row, textvariable=var_tok, show="*")
        tok_entry.grid(row=0, column=0, sticky="ew")
        show_var = tk.BooleanVar(value=False)

        def _toggle_show(code=ch.code, entry=tok_entry, var=show_var) -> None:
            entry.configure(show="" if var.get() else "*")

        ttk.Checkbutton(token_row, text="Pokaz", variable=show_var, command=_toggle_show).grid(
            row=0, column=1, padx=(6, 0)
        )
        entries[ch.code]["access_token"] = var_tok
        show_tokens[ch.code] = show_var
        token_entries[ch.code] = tok_entry
        row += 1

        # Test button
        test_btn = ttk.Button(
            grid, text="Test polaczenia",
            command=lambda c=ch.code, e=entries[ch.code]: _test_connection(dlg, c, e),
        )
        test_btn.grid(row=row, column=0, columnspan=2, sticky="w", pady=(8, 4))

        # Info status
        status_var = tk.StringVar(value="")
        ttk.Label(grid, textvariable=status_var, foreground="#666").grid(
            row=row + 1, column=0, columnspan=2, sticky="w"
        )
        entries[ch.code]["__status"] = status_var  # type: ignore[assignment]

    # Auto-publish checkbox
    cfg = storage.load_config()
    auto_var = tk.BooleanVar(value=bool(cfg.get("auto_publish")))
    auto_frame = ttk.Frame(outer)
    auto_frame.pack(fill="x", pady=(10, 4))
    ttk.Checkbutton(
        auto_frame,
        text="Auto-publikacja: publisher w tle co 60s bedzie wysylac posty ktorych czas nadszedl",
        variable=auto_var,
    ).pack(side="left")

    # Przyciski
    btns = ttk.Frame(outer)
    btns.pack(fill="x", pady=(10, 0))

    def _save() -> None:
        new_creds: dict[str, dict[str, str]] = {}
        for code, fields in entries.items():
            entry: dict[str, str] = {}
            for k, v in fields.items():
                if k.startswith("__"):
                    continue
                if isinstance(v, tk.StringVar):
                    entry[k] = v.get().strip()
            new_creds[code] = entry
        storage.save_meta_credentials(new_creds)
        refresh_token_metadata_in_file(mark_renewed=True)
        # Config auto_publish
        cfg2 = storage.load_config()
        cfg2["auto_publish"] = bool(auto_var.get())
        storage.save_config(cfg2)
        messagebox.showinfo(
            "Zapisano",
            "Tokeny zapisane w data/cykl/meta_credentials.json.\n\n"
            + ("Auto-publikacja WLACZONA - publisher bedzie wysylac zaplanowane posty."
               if auto_var.get()
               else "Auto-publikacja WYLACZONA - posty pozostana w kolejce do recznego 'Publikuj teraz'."),
            parent=dlg,
        )
        if on_saved:
            try:
                on_saved()
            except Exception:  # noqa: BLE001
                pass
        dlg.destroy()

    ttk.Button(btns, text="Zapisz", command=_save).pack(side="right", padx=(6, 0))
    ttk.Button(btns, text="Anuluj", command=dlg.destroy).pack(side="right")

    return dlg


def _test_connection(parent: tk.Misc, channel_code: str, fields: dict[str, tk.StringVar]) -> None:
    ch = _cp.get(channel_code)
    if ch is None:
        return
    token = fields.get("access_token", tk.StringVar()).get().strip()
    status_var = fields.get("__status")

    def _set_status(text: str, color: str = "#666") -> None:
        if isinstance(status_var, tk.StringVar):
            status_var.set(text)

    if not token:
        _set_status("Brak tokenu")
        return

    if ch.platform == "fb":
        page_id = fields.get("page_id", tk.StringVar()).get().strip()
        if not page_id:
            _set_status("Brak page_id")
            return
        url = f"{meta_publisher.GRAPH_BASE}/{page_id}"
        params = {"fields": "id,name,category", "access_token": token}
    else:
        ig_id = fields.get("ig_user_id", tk.StringVar()).get().strip()
        if not ig_id:
            _set_status("Brak ig_user_id")
            return
        url = f"{meta_publisher.GRAPH_BASE}/{ig_id}"
        params = {"fields": "id,username", "access_token": token}

    try:
        qs = urllib.parse.urlencode(params)
        req = urllib.request.Request(f"{url}?{qs}", method="GET")
        import json as _json
        import ssl as _ssl
        with urllib.request.urlopen(req, context=_ssl.create_default_context(), timeout=15) as resp:
            raw = resp.read().decode("utf-8")
        data = _json.loads(raw) if raw else {}
        name = data.get("name") or data.get("username") or data.get("id") or "?"
        _set_status(f"OK: {name}")
        messagebox.showinfo(
            f"Test {ch.label}",
            f"Polaczenie OK. Strona/konto: {name}",
            parent=parent,
        )
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        _set_status(f"HTTP {e.code}")
        messagebox.showerror(
            f"Test {ch.label}",
            f"HTTP {e.code}\n\n{detail[:500]}",
            parent=parent,
        )
    except Exception as e:  # noqa: BLE001
        _set_status(f"Blad: {e}")
        messagebox.showerror(f"Test {ch.label}", str(e), parent=parent)


_SETUP_HELP = """# Konfiguracja Meta API dla Cyklu (dzialajacy przeplyw)

Ten opis odpowiada konfiguracji, ktora **dziala** z aplikacja typu Business i **Facebook Login for Business** (bez URL callback na developers.facebook.com w polu redirect).

## 1. Aplikacja w Meta for Developers

1. Wejdz na [developers.facebook.com/apps](https://developers.facebook.com/apps/) i utworz aplikacje typu **Business** (np. GicleeArt Social Publisher).
2. Dodaj produkty: **Facebook Login for Business** oraz **Instagram** (Instagram Graph API).
3. W **Use cases** dostosuj m.in. **Manage messaging and content on Instagram** oraz **Manage everything on your Page** (Permissions and features: dodaj potrzebne scope, w tym `instagram_basic`, `instagram_content_publish`, `pages_*`).
4. W **Instagram API** otworz **API setup with Facebook login** i dodaj uprawnienia pod publikacje (Manage content on Instagram). Wiadomosci (DM) sa osobne, jesli ich nie potrzebujesz, nie musisz klikać paczki pod messaging.

## 2. OAuth (redirect na Twoja domene HTTPS)

W **Facebook Login for Business** → **Settings** wlacz **Client OAuth login** i **Web OAuth login**.

W **Valid OAuth Redirect URIs** wpisz adres **na swojej domenie** (Meta czesto **nie przyjmie** samego `https://developers.facebook.com/tools/explorer/callback` w tym produkcie), np.:

`https://twoja-domena.eu/meta/oauth/callback`

Ta sama wartosc musi byc podana pozniej jako `redirect_uri` w linku logowania. Strona pod tym URL musi istniec (HTTPS) albo przynajmniej nie zwracac bledu przy powrocie z Facebooka (parametr `code` w adresie).

W **App settings** → **Basic** ustaw **Privacy Policy URL** (dzialajacy publiczny HTTPS).

## 3. Pierwszy User Access Token (OAuth w przegladarce)

Zbuduj URL (podstaw **APP_ID** z Basic, **redirect_uri** dokladnie jak w panelu, zakodowany):

`https://www.facebook.com/v21.0/dialog/oauth?client_id=APP_ID&redirect_uri=...&scope=pages_show_list,pages_read_engagement,pages_manage_posts&response_type=code`

**Uwaga:** Jesli od razu dopiszesz `instagram_basic,instagram_content_publish` i dostaniesz **Invalid Scopes**, najpierw zaloguj sie **tylko** z `pages_*`, a uprawnienia Instagram dodaj w aplikacji (Permissions and features), potem wygeneruj token ponownie w **Graph API Explorer** (Add a Permission) albo drugim OAuth z pelnym `scope`.

Po zalogowaniu Facebook przekieruje na `redirect_uri?code=...`. Wymien `code` na **krotki user access token** (endpoint `oauth/access_token` z `client_id`, `client_secret`, `redirect_uri`, `code`).

## 4. Long-lived User Token

Wywolaj (np. w przegladarce lub PowerShellu, **bez** nawiasow `<>` wokol wartosci):

`GET https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=KROTKI_USER_TOKEN`

Odpowiedz JSON: pole `access_token` to **long-lived user token** (~60 dni). `client_secret` nie wklejaj na czat ani w screeny.

## 5. Page Access Token (gdy /me/accounts jest puste)

Czasem `GET /me/accounts` zwraca pusta liste mimo poprawnych uprawnien. **Dzialajace obejscie:** dla **kazdego znanego Page ID** (np. z Access Token Debugger, granular scopes):

`GET https://graph.facebook.com/v21.0/{PAGE_ID}?fields=access_token&access_token=LONG_LIVED_USER_TOKEN`

W odpowiedzi `access_token` to **Page Access Token** do wpisania w Cyklu (FB i ten sam dla powiazanego IG).

**PowerShell (token w apostrofach, jedna linia):**

`$t = 'LONG_LIVED_USER_TOKEN'`

`Invoke-RestMethod -Uri "https://graph.facebook.com/v21.0/PAGE_ID?fields=access_token&access_token=$t"`

## 6. Instagram User ID (ig_user_id)

Dla kazdej strony osobno (ten sam user token `$t`):

`GET /{PAGE_ID}?fields=instagram_business_account`

W JSON wez `instagram_business_account.id` i wpisz jako **Instagram User ID** w Cyklu. Token dla IG = **ten sam Page Access Token** co dla FB tej pary.

## 7. Ktora strona to PL, a ktora EN

`GET /{PAGE_ID}?fields=name,username` z user tokenem albo sprawdz nazwe w Meta Business Suite.

## 8. Wpisz w ten dialog i testuj

- **FB:** `page_id` + `access_token` (Page token).
- **IG:** `ig_user_id` + **ten sam** `access_token` co FB w parze jezykowej.

Zapisz i uzyj **Test polaczenia**.

## 9. App Review (produkcja / inni uzytkownicy)

Dla trybu Live i szerszego dostepu do danych czesto potrzebny jest **App Review** oraz Privacy Policy, Data Use itd. Na wlasnych kontach w roli developera czesc rzeczy dziala w trybie Development.

## 10. Bezpieczenstwo

Nie udostepniaj **App Secret**, pelnych tokenow ani `meta_credentials.json`. Po wycieku zresetuj **App Secret** w panelu i wygeneruj tokeny od nowa.
"""


_RENEWAL_HELP = """# Odnowa tokenow Meta (Cykl)

Uzyj tej listy, gdy Graph zwroci blad typu **token expired**, **OAuthException**, albo **Test polaczenia** w Cyklu przestanie dzialac.

## Co odswiezasz

- **Page Access Token** w `meta_credentials.json` (dla FB i IG w kazdej zakladce).
- Zwykle potrzebny jest nowy **long-lived user token** (krok posredni), potem ponowne pobranie **page tokenow** dla kazdej strony.

**ig_user_id** (Instagram Business Account ID) zwykle **nie zmienia sie**, dopoki nie rozlaczysz IG od strony w Business Suite.

## Kroki

1. **Graph API Explorer:** wybierz aplikacje, **User Token**, **Generate Access Token** i zaznacz scope: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `instagram_basic`, `instagram_content_publish`, `public_profile` (plus ewentualnie inne, ktore masz w aplikacji).

2. **Long-lived user:** tak samo jak przy pierwszej konfiguracji wywolaj wymiane `fb_exchange_token` z `client_id`, `client_secret` i krotkim user tokenem.

3. **Page tokeny:** dla kazdego **Page ID** (dwoch stron):

`GET https://graph.facebook.com/v21.0/{PAGE_ID}?fields=access_token&access_token=LONG_LIVED_USER_TOKEN`

(w PowerShell: token w zmiennej `$t` w **pojedynczych apostrofach**).

4. **Wpisz** nowe Page Tokeny w Cyklu (FB + IG dla PL i EN). Zapisz.

5. **Test polaczenia** na wszystkich czterech zakladkach.

## Gdy Explorer pokazuje "No configurations"

Sprawdz **Facebook Login for Business** → **Valid OAuth Redirect URIs** (Twoja domena HTTPS) oraz ze logowanie OAuth w przegladarce dziala z tym samym `redirect_uri`.

## Cykl 60 dni

User token uzyty do wymiany ma ograniczony wiek; po okresie odswiez krotki token (Explorer lub OAuth) i powtorz wymiane na long-lived oraz pobranie page tokenow.

## Po wycieku sekretu lub tokena

W **App settings** → **Basic** zresetuj **App Secret**, potem wygeneruj tokeny od nowa. Nie commituj `meta_credentials.json`.
"""


def _show_setup_help(parent: tk.Misc) -> None:
    try:
        from Komponenty._shared.help_dialog import show_help
        show_help(parent, title="Meta API - instrukcja konfiguracji", text=_SETUP_HELP)
    except ImportError:
        messagebox.showinfo("Meta API - instrukcja", _SETUP_HELP, parent=parent)


def _show_renewal_help(parent: tk.Misc) -> None:
    try:
        from Komponenty._shared.help_dialog import show_help
        show_help(parent, title="Meta API - instrukcja odnowy tokenow", text=_RENEWAL_HELP)
    except ImportError:
        messagebox.showinfo("Meta API - odnowa tokenow", _RENEWAL_HELP, parent=parent)
