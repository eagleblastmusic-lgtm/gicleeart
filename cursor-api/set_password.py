"""Narzedzie do recznego ustawienia hasla do GicleeApp.

Uzycie:
    cd cursor-api
    python set_password.py

Alternatywnie mozna po prostu uruchomic GicleeApp - przy pierwszym starcie
pokaze dialog 'Ustaw haslo'. Ten skrypt przydaje sie gdy chcesz zmienic
haslo albo zresetowac.

Haslo jest zapisywane jako PBKDF2-SHA256 hash w pliku:
    Windows: %APPDATA%/Giclee/auth.json
    macOS:   ~/Library/Application Support/Giclee/auth.json
    Linux:   ~/.config/Giclee/auth.json

Plik NIE trafia do repo git - zawiera tylko hash (nie plaintext).
"""

from __future__ import annotations

import getpass
import sys
from pathlib import Path

# Zeby import zadzialal z folderu cursor-api/
sys.path.insert(0, str(Path(__file__).resolve().parent))

from Komponenty._shared import auth


def main() -> int:
    print("=" * 60)
    print("  GicleeApp - konfiguracja hasla dostepu")
    print("=" * 60)

    if auth.is_configured():
        print("\nHaslo jest juz ustawione.")
        print("Opcje:")
        print("  [1] Zmien haslo")
        print("  [2] Zresetuj (usun plik - aplikacja zapyta o nowe przy starcie)")
        print("  [3] Anuluj")
        choice = input("\nWybor: ").strip()
        if choice == "2":
            if auth.reset_password():
                print("Plik auth.json usuniety. Przy nastepnym starcie aplikacji ustaw nowe haslo.")
                return 0
            print("Nie udalo sie usunac pliku.")
            return 1
        if choice != "1":
            print("Anulowano.")
            return 0

    print("\nPodaj haslo (minimum 6 znakow). Haslo NIE jest wyswietlane w terminalu.")
    while True:
        p1 = getpass.getpass("Haslo: ")
        p2 = getpass.getpass("Powtorz: ")
        if p1 != p2:
            print("Hasla sie nie zgadzaja. Sprobuj ponownie.\n")
            continue
        try:
            auth.set_password(p1)
        except ValueError as e:
            print(f"BLAD: {e}\n")
            continue
        print("\nOK - haslo zapisane.")
        print(f"Plik: {auth._auth_file()}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
