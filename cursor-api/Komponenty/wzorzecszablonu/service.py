"""Shopify: template_suffix (szablon motywu product.*) — lista i masowa zmiana."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Iterable

from Komponenty.dodajobraz import shopify_client as sc
from Komponenty.dodajobraz.create import PRODUCT_TYPE
from Komponenty.dodajobraz.description_update import (
    load_product_catalog_rows,
    product_catalog_sort_key,
)

Logger = Callable[[str], None]

DEFAULT_TEMPLATE_LABEL = "Domyślny produkt"

# Znane sufiksy — czytelniejsza etykieta w combobox (suffix pozostaje kluczem API).
_FRIENDLY_LABELS: dict[str, str] = {
    "": DEFAULT_TEMPLATE_LABEL,
    "fotografia-obraz": "fotografia-obraz",
    "nowy-szblon-produktu": "nowy-szblon-produktu",
    "szablon-produktu-v2": "szablon-produktu-v2",
    "szablon-produktu-v3": "szablon-produktu-v3",
    "szablon-wlasna-fotografia": "szablon-wlasna-fotografia",
}


def _log(logger: Logger | None, msg: str) -> None:
    if logger:
        logger(msg)


def theme_templates_dir() -> Path | None:
    """Katalog `templates/` motywu (repo nad `cursor-api/`)."""
    root = Path(__file__).resolve().parents[3]
    candidate = root / "templates"
    return candidate if candidate.is_dir() else None


def suffix_from_theme_filename(filename: str) -> str | None:
    """`templates/product.json` → ''; `templates/product.foo.json` → 'foo'."""
    name = (filename or "").replace("\\", "/").strip().lstrip("/")
    if not name.startswith("templates/product"):
        return None
    if not name.endswith(".json"):
        return None
    base = name[len("templates/") : -len(".json")]
    if base == "product":
        return ""
    prefix = "product."
    if base.startswith(prefix):
        return base[len(prefix) :]
    return None


def discover_product_templates_from_repo(*, logger: Logger | None = None) -> list[str]:
    """Sufiksy z plików `templates/product*.json` w repozytorium motywu."""
    tpl_dir = theme_templates_dir()
    if not tpl_dir:
        _log(logger, "[wzorzec] Brak katalogu templates/ w repo motywu.")
        return []
    suffixes: set[str] = set()
    for path in sorted(tpl_dir.glob("product*.json")):
        suffix = suffix_from_theme_filename(f"templates/{path.name}")
        if suffix is not None:
            suffixes.add(suffix)
    out = sorted(suffixes, key=lambda s: (0 if s == "" else 1, s))
    _log(logger, f"[wzorzec] Szablony z repo: {len(out)} ({tpl_dir}).")
    return out


def template_display_label(suffix: str) -> str:
    key = (suffix or "").strip()
    return _FRIENDLY_LABELS.get(key, key or DEFAULT_TEMPLATE_LABEL)


def build_template_options(suffixes: list[str]) -> list[dict[str, str]]:
    """Opcje do combobox: [{suffix, label}, ...] — zawsze z domyślnym produktem."""
    merged: set[str] = set(suffixes)
    merged.add("")
    ordered = sorted(merged, key=lambda s: (0 if s == "" else 1, s))
    return [{"suffix": s, "label": template_display_label(s)} for s in ordered]


def discover_product_templates(
    *,
    extra_suffixes: Iterable[str] | None = None,
    logger: Logger | None = None,
) -> list[dict[str, str]]:
    """Lista szablonów: repo motywu + sufiksy już używane na produktach."""
    repo_suffixes = discover_product_templates_from_repo(logger=logger)
    merged: set[str] = set(repo_suffixes)
    if extra_suffixes:
        for s in extra_suffixes:
            merged.add((s or "").strip())
    ordered = sorted(merged, key=lambda s: (0 if s == "" else 1, s))
    return build_template_options(ordered)


def load_catalog_with_template_suffix(
    *,
    logger: Logger | None = None,
    should_cancel: Callable[[], bool] | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Produkty typu Obraz + bieżący template_suffix oraz opcje szablonów."""
    shop, token = sc.load_session()
    rows = load_product_catalog_rows(
        logger=logger,
        should_cancel=should_cancel,
        on_progress=on_progress,
    )
    if should_cancel and should_cancel():
        return rows, build_template_options([""])

    if on_progress:
        on_progress("Pobieram wzorce szablonów produktów...")
    suffix_by_id = fetch_template_suffix_map(
        shop,
        token,
        logger=logger,
        should_cancel=should_cancel,
        on_progress=on_progress,
    )
    used_suffixes: set[str] = set()
    for row in rows:
        pid = int(row.get("product_id") or 0)
        suffix = suffix_by_id.get(pid, "")
        row["template_suffix"] = suffix
        row["template_label"] = template_display_label(suffix)
        used_suffixes.add(suffix)

    templates = discover_product_templates(extra_suffixes=used_suffixes, logger=logger)
    return rows, templates


def fetch_template_suffix_map(
    shop: str,
    token: str,
    *,
    logger: Logger | None = None,
    should_cancel: Callable[[], bool] | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> dict[int, str]:
    """Mapa product_id → template_suffix (REST)."""
    products = sc.fetch_all_products(
        shop,
        token,
        product_type=PRODUCT_TYPE,
        fields="id,template_suffix",
        should_cancel=should_cancel,
        on_page_progress=lambda n: on_progress(f"Wzorce: {n} produktów...") if on_progress else None,
    )
    out: dict[int, str] = {}
    for prod in products:
        try:
            pid = int(prod.get("id") or 0)
        except (TypeError, ValueError):
            continue
        if not pid:
            continue
        out[pid] = str(prod.get("template_suffix") or "").strip()
    _log(logger, f"[wzorzec] template_suffix: {len(out)} produkt(ów).")
    return out


def apply_template_suffix_batch(
    product_ids: list[int],
    suffix: str,
    *,
    logger: Logger | None = None,
    should_cancel: Callable[[], bool] | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Ustawia template_suffix na wskazanych produktach (pusta wartość = domyślny)."""
    shop, token = sc.load_session()
    clean_suffix = (suffix or "").strip()
    total = len(product_ids)
    updated = 0
    errors: list[str] = []

    for i, pid in enumerate(product_ids, start=1):
        if should_cancel and should_cancel():
            break
        if on_progress:
            on_progress(f"Zapis {i}/{total}...")
        try:
            sc.update_product(shop, token, int(pid), {"template_suffix": clean_suffix})
            updated += 1
            _log(
                logger,
                f"[wzorzec] OK produkt {pid} → «{template_display_label(clean_suffix)}»",
            )
        except sc.ShopifyError as exc:
            msg = f"Produkt {pid}: {exc}"
            errors.append(msg)
            _log(logger, f"[wzorzec] BŁĄD {msg}")

    return {
        "ok": not errors,
        "updated": updated,
        "total": total,
        "suffix": clean_suffix,
        "errors": errors,
    }


def sort_catalog_rows(rows: list[dict[str, Any]], *, col: str, reverse: bool) -> list[dict[str, Any]]:
    """Sortowanie wierszy katalogu (jak w innych komponentach listowych)."""
    items = list(rows)
    if col == "painting_title":
        items.sort(key=lambda r: (r.get("painting_title") or "").lower(), reverse=reverse)
    elif col == "handle":
        items.sort(key=lambda r: (r.get("handle") or "").lower(), reverse=reverse)
    elif col == "template_label":
        items.sort(
            key=lambda r: (
                (r.get("template_label") or "").lower(),
                product_catalog_sort_key(r),
            ),
            reverse=reverse,
        )
    else:
        items.sort(key=product_catalog_sort_key, reverse=reverse)
    return items
