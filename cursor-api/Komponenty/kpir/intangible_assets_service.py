"""Ewidencja WNiP — amortyzacja do kol. 15 PKPiR."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .entry_service import create_entry, post_entry
from .models import IntangibleAsset
from .storage import list_intangible_assets, new_intangible_asset_id, save_intangible_asset
from .validation import ValidationError


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def create_intangible_asset(**kwargs: Any) -> IntangibleAsset:
    now = _now()
    value = float(kwargs.get("initial_value") or 0)
    if value <= 0:
        raise ValidationError("Wartość początkowa WNiP musi być dodatnia.")
    asset = IntangibleAsset(
        id=new_intangible_asset_id(),
        name=str(kwargs.get("name") or ""),
        acquisition_date=str(kwargs.get("acquisition_date") or now[:10]),
        document_number=str(kwargs.get("document_number") or ""),
        initial_value=value,
        depreciation_rate=float(kwargs.get("depreciation_rate") or 0.20),
        notes=str(kwargs.get("notes") or ""),
        created_at=now,
        updated_at=now,
    )
    save_intangible_asset(asset)
    return asset


def monthly_depreciation(asset: IntangibleAsset) -> float:
    if not asset.is_active:
        return 0.0
    annual = asset.initial_value * asset.depreciation_rate
    monthly = round(annual / 12, 2)
    remaining = asset.initial_value - asset.accumulated_depreciation
    return round(min(monthly, max(0.0, remaining)), 2)


def post_monthly_depreciation(year: int, month: int) -> list[Any]:
    posted = []
    event_date = f"{year:04d}-{month:02d}-28"
    for asset in list_intangible_assets():
        if not asset.is_active:
            continue
        amount = monthly_depreciation(asset)
        if amount <= 0:
            continue
        entry = create_entry(
            event_date=event_date,
            document_number=f"AM-WN/{asset.id}/{year:04d}{month:02d}",
            description=f"Amortyzacja WNiP: {asset.name}",
            other_expenses=amount,
            source="intangible_asset",
            entry_type="cost",
            amount_pln=amount,
        )
        entry = post_entry(entry)
        asset.accumulated_depreciation = round(asset.accumulated_depreciation + amount, 2)
        asset.updated_at = _now()
        save_intangible_asset(asset)
        posted.append(entry)
    return posted


def intangible_assets_summary() -> dict[str, Any]:
    assets = list_intangible_assets()
    active = [a for a in assets if a.is_active]
    return {
        "count": len(assets),
        "active_count": len(active),
        "total_initial": round(sum(a.initial_value for a in active), 2),
        "total_net": round(sum(a.net_value for a in active), 2),
    }
