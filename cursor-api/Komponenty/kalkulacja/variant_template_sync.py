"""Synchronizacja cen z kalkulatora do szablonu wariantów produktu (dodajobraz)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from Komponenty.dodajobraz import templates as variant_templates

from .calculator import calc_sell_price_for_shop_labels
from .store import load_settings


@dataclass
class VariantTemplateSyncResult:
    template_names: list[str] = field(default_factory=list)
    variants_total: int = 0
    variants_updated: int = 0
    variants_unchanged: int = 0
    variants_skipped: int = 0
    price_samples: list[dict[str, Any]] = field(default_factory=list)

    def summary(self) -> str:
        names = ", ".join(self.template_names) or "—"
        return (
            f"Szablony: {names}. "
            f"Zaktualizowano {self.variants_updated} wariantów "
            f"(bez zmian: {self.variants_unchanged}, pominięto: {self.variants_skipped})."
        )


def sync_variant_template_prices(
    *,
    all_templates: bool = True,
    template_ids: list[str] | None = None,
) -> VariantTemplateSyncResult:
    """Ustawia `price` w `variant_templates.json` wg zapisanego cennika kalkulatora.

    Mapowanie etykiet sklepu: option2 = M/L/XL, option3 = Sosna/Dąb (jak w dodajobraz).
    Kolor ramy i passe-partout nie wpływają na cenę — aktualizowane są wszystkie warianty
    z tym samym rozmiarem i drewnem.
    """
    settings = load_settings()
    templates = variant_templates.load_templates()
    if not templates:
        raise FileNotFoundError(
            "Brak pliku szablonów wariantów (Komponenty/dodajobraz/data/variant_templates.json)."
        )

    if all_templates:
        targets = templates
    else:
        default = variant_templates.get_default()
        targets = [default] if default else templates[:1]

    if template_ids:
        allowed = {tid.strip() for tid in template_ids if tid and str(tid).strip()}
        targets = [t for t in targets if t.id in allowed]
        if not targets:
            raise ValueError("Nie znaleziono szablonu o podanym id.")

    result = VariantTemplateSyncResult()
    seen_keys: set[tuple[str, str, str]] = set()

    for tpl in targets:
        result.template_names.append(tpl.name)
        for variant in tpl.variants:
            result.variants_total += 1
            size_label = str(variant.get("option2") or "").strip()
            wood_label = str(variant.get("option3") or "").strip()
            price = calc_sell_price_for_shop_labels(
                wood_label,
                size_label,
                settings=settings,
            )
            if price is None or price <= 0:
                result.variants_skipped += 1
                continue

            new_price = f"{price:.2f}"
            old_price = str(variant.get("price") or "").strip()
            if old_price == new_price:
                result.variants_unchanged += 1
                continue

            variant["price"] = new_price
            result.variants_updated += 1

            sample_key = (tpl.name, size_label, wood_label)
            if sample_key not in seen_keys and len(result.price_samples) < 12:
                seen_keys.add(sample_key)
                result.price_samples.append(
                    {
                        "template": tpl.name,
                        "size": size_label,
                        "wood": wood_label,
                        "old_price": old_price or None,
                        "new_price": new_price,
                    }
                )

        tpl.updated_at = datetime.now().isoformat(timespec="seconds")

    variant_templates.save_templates(templates)
    return result
