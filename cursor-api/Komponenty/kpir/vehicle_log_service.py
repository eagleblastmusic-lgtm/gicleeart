"""Ewidencja przebiegu pojazdu — wymagana przy ST firmowym i 100% kosztów auta."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import CompanyVehicle, MileageLogEntry
from .storage import (
    list_mileage_log,
    list_vehicles,
    new_mileage_log_id,
    new_vehicle_id,
    save_mileage_entry,
    save_vehicle,
)
from .validation import ValidationError


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def create_vehicle(**kwargs: Any) -> CompanyVehicle:
    now = _now()
    pct = float(kwargs.get("business_use_pct") or 100)
    if not 0 < pct <= 100:
        raise ValidationError("Udział firmowy musi być między 0 a 100%.")
    vehicle = CompanyVehicle(
        id=new_vehicle_id(),
        name=str(kwargs.get("name") or ""),
        registration_number=str(kwargs.get("registration_number") or ""),
        fixed_asset_id=str(kwargs.get("fixed_asset_id") or ""),
        business_use_pct=pct,
        notes=str(kwargs.get("notes") or ""),
        created_at=now,
        updated_at=now,
    )
    save_vehicle(vehicle)
    return vehicle


def add_mileage_entry(
    vehicle_id: str,
    log_date: str,
    *,
    trip_km: float,
    odometer_km: float = 0.0,
    route_description: str = "",
    purpose: str = "business",
) -> MileageLogEntry:
    if trip_km <= 0:
        raise ValidationError("Przebieg musi być dodatni.")
    if purpose not in ("business", "private"):
        raise ValidationError("Cel jazdy: business lub private.")
    vehicles = {v.id for v in list_vehicles()}
    if vehicle_id not in vehicles:
        raise ValidationError("Nie znaleziono pojazdu.")
    entry = MileageLogEntry(
        id=new_mileage_log_id(),
        vehicle_id=vehicle_id,
        log_date=log_date[:10],
        odometer_km=odometer_km,
        trip_km=trip_km,
        route_description=route_description,
        purpose=purpose,
        created_at=_now(),
    )
    save_mileage_entry(entry)
    return entry


def mileage_for_year(vehicle_id: str, year: int) -> list[MileageLogEntry]:
    return [
        e for e in list_mileage_log()
        if e.vehicle_id == vehicle_id and e.log_date.startswith(f"{year:04d}")
    ]


def mileage_summary(vehicle_id: str, year: int) -> dict[str, Any]:
    rows = mileage_for_year(vehicle_id, year)
    business = round(sum(e.trip_km for e in rows if e.purpose == "business"), 1)
    private = round(sum(e.trip_km for e in rows if e.purpose == "private"), 1)
    total = round(business + private, 1)
    return {
        "year": year,
        "vehicle_id": vehicle_id,
        "business_km": business,
        "private_km": private,
        "total_km": total,
        "business_pct": round(100.0 * business / total, 1) if total else 0.0,
        "entry_count": len(rows),
    }
