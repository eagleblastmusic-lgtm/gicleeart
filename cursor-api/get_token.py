"""
Odczyt tokenu offline z pliku utworzonego przez: npm run oauth
(nie commituj .shopify_session.json ani .env).
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SESSION = ROOT / ".shopify_session.json"


def main() -> None:
    if not SESSION.is_file():
        print(f"Brak {SESSION}. Uruchom: npm run oauth i zaloguj sklep.")
        return
    data = json.loads(SESSION.read_text(encoding="utf-8"))
    shop = data.get("shop", "")
    token = data.get("accessToken", "")
    print("shop:", shop)
    print("accessToken (ostatnie 6):", (token[-6:] if token else "(brak)"))


if __name__ == "__main__":
    main()
