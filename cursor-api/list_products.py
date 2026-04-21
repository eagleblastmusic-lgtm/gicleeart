"""
Lista produktów przez GraphQL Admin API (tylko stdlib — bez pip install).
Wymaga pliku .shopify_session.json z npm run oauth.
"""
import json
import ssl
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SESSION = ROOT / ".shopify_session.json"
API_VERSION = "2026-04"

QUERY = """
query {
  products(first: 50) {
    edges {
      node {
        id
        title
        handle
        status
      }
    }
    pageInfo {
      hasNextPage
    }
  }
}
"""


def main() -> None:
    if not SESSION.is_file():
        print(f"Brak {SESSION}. Uruchom: npm run oauth")
        return

    data = json.loads(SESSION.read_text(encoding="utf-8"))
    shop = data.get("shop", "").strip()
    token = data.get("accessToken", "").strip()
    if not shop or not token:
        print("Niepełna sesja w pliku.")
        return

    url = f"https://{shop}/admin/api/{API_VERSION}/graphql.json"
    body = json.dumps({"query": QUERY}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": token,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, context=ssl.create_default_context()) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}")
        print(e.read().decode("utf-8", errors="replace"))
        return

    result = json.loads(raw)
    if result.get("errors"):
        print(json.dumps(result["errors"], indent=2, ensure_ascii=False))
        if any(
            "ACCESS_DENIED" in str(e) or "access" in str(e).lower()
            for e in result["errors"]
        ):
            print(
                "\nJeśli brak uprawnień do odczytu, w aplikacji dopisz scope read_products,"
                " shopify app deploy, potem npm run oauth jeszcze raz."
            )
        return

    edges = result.get("data", {}).get("products", {}).get("edges", [])
    if not edges:
        print("(brak produktów na liście)")
        return

    for i, edge in enumerate(edges, 1):
        n = edge["node"]
        print(f"{i}. {n['title']}  —  /{n['handle']}  [{n.get('status', '')}]")

    info = result.get("data", {}).get("products", {}).get("pageInfo", {})
    if info.get("hasNextPage"):
        print("\n(są kolejne strony — można rozszerzyć skrypt o paginację)")


if __name__ == "__main__":
    main()
