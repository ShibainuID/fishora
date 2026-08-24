from dataclasses import dataclass
from decimal import Decimal

from apps.main_api.contracts import BuyerPreferenceRecord, LandingPointRecord, LotRecord
from apps.main_api.services.geo import haversine_km, within_serviceability

WEIGHTS = {
    "intended_use": 0.30,
    "characteristics": 0.25,
    "price": 0.20,
    "volume": 0.15,
    "distance": 0.10,
}

CRITERIA = ("intended_use", "characteristics", "price", "volume", "distance")


@dataclass(frozen=True)
class MatchReason:
    criterion: str
    met: bool
    detail: str
    value: str | None


@dataclass(frozen=True)
class MatchResult:
    score: float
    reasons: list[MatchReason]


def _fold(values: list[str]) -> set[str]:
    return {item.casefold().strip() for item in values if item and item.strip()}


def _lot_uses(lot: LotRecord) -> list[str]:
    snapshot = lot.knowledge_snapshot or {}
    return list(snapshot.get("commercial_uses") or [])


def _lot_characteristics(lot: LotRecord) -> list[str]:
    snapshot = lot.knowledge_snapshot or {}
    values = list(snapshot.get("characteristics") or [])
    for key in ("taste", "texture", "physical_characteristics"):
        raw = snapshot.get(key)
        if isinstance(raw, str) and raw.strip():
            values.append(raw)
    return values


def match_lot(
    lot: LotRecord,
    prefs: BuyerPreferenceRecord,
    landing: LandingPointRecord | None,
) -> MatchResult:
    uses_met = bool(_fold(prefs.intended_uses) & _fold(_lot_uses(lot)))
    chars_met = bool(_fold(prefs.characteristics) & _fold(_lot_characteristics(lot)))
    price_met = prefs.max_price_per_kg is None or lot.starting_price_per_kg <= prefs.max_price_per_kg
    volume_met = prefs.min_quantity_kg is None or lot.quantity_kg >= prefs.min_quantity_kg
    if landing is None:
        distance_km = None
        distance_met = False
    else:
        distance_km = haversine_km(prefs.latitude, prefs.longitude, landing.latitude, landing.longitude)
        distance_met = within_serviceability(
            prefs.latitude, prefs.longitude, landing.latitude, landing.longitude
        )

    flags = {
        "intended_use": uses_met,
        "characteristics": chars_met,
        "price": price_met,
        "volume": volume_met,
        "distance": distance_met,
    }
    details = {
        "intended_use": (
            "cocok untuk " + ", ".join(prefs.intended_uses) if uses_met else "penggunaan tidak cocok"
        ),
        "characteristics": (
            "ciri sesuai preferensi" if chars_met else "ciri tidak sesuai preferensi"
        ),
        "price": (
            f"Rp {lot.starting_price_per_kg:,.0f}/kg".replace(",", ".")
            if price_met
            else "harga di atas batas"
        ),
        "volume": (
            f"{lot.quantity_kg} kg" if volume_met else "volume di bawah kebutuhan"
        ),
        "distance": (
            f"{round(distance_km)} km" if distance_km is not None else "lokasi tidak diketahui"
        ),
    }
    values = {
        "intended_use": ", ".join(prefs.intended_uses) or None,
        "characteristics": ", ".join(prefs.characteristics) or None,
        "price": str(lot.starting_price_per_kg),
        "volume": f"{lot.quantity_kg} kg",
        "distance": None if distance_km is None else f"{round(distance_km)} km",
    }
    reasons = [
        MatchReason(criterion=name, met=flags[name], detail=details[name], value=values[name])
        for name in CRITERIA
    ]
    score = sum(WEIGHTS[name] for name in CRITERIA if flags[name])
    return MatchResult(score=score, reasons=reasons)


def recommend(
    lots: list[LotRecord],
    prefs: BuyerPreferenceRecord | None,
    landing_points: dict[str, LandingPointRecord],
) -> list[tuple[LotRecord, MatchResult]]:
    if prefs is None:
        return []
    ranked = []
    for lot in lots:
        landing = landing_points.get(lot.landing_point_id)
        if landing is None or not within_serviceability(
            prefs.latitude, prefs.longitude, landing.latitude, landing.longitude
        ):
            continue
        ranked.append((lot, match_lot(lot, prefs, landing)))
    ranked.sort(key=lambda item: item[1].score, reverse=True)
    return ranked
