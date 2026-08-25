import re
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


def fold_terms(values: list[str]) -> set[str]:
    return {item.casefold().strip() for item in values if item and item.strip()}


_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def fold_words(values: list[str]) -> set[str]:
    """Every word across the values, casefolded.

    A knowledge card states taste and texture as sentences and lists processing
    methods as short phrases, while a buyer states one word. Comparing the two
    as whole strings can never intersect, so the comparison is by word.
    """
    words: set[str] = set()
    for value in values:
        if value:
            words.update(match.group().casefold() for match in _WORD.finditer(value))
    return words


def lot_uses(lot: LotRecord) -> list[str]:
    """What the fish can be used for.

    Both fields, because a buyer's answer to "what do you cook or sell" can be
    either. PRD 8.3.5 reads "Suitable for grilling", a processing method, while
    `commercial_uses` holds segments like Restoran, so reading only the latter
    scored a cooking method against a list of customer types.
    """
    snapshot = lot.knowledge_snapshot or {}
    return [
        *(snapshot.get("processing_methods") or []),
        *(snapshot.get("commercial_uses") or []),
    ]


def lot_characteristics(lot: LotRecord) -> list[str]:
    snapshot = lot.knowledge_snapshot or {}
    # `characteristics` is not a KnowledgeCard field; kept only for snapshots
    # written before the card contract settled.
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
    uses_met = bool(fold_words(prefs.intended_uses) & fold_words(lot_uses(lot)))
    chars_met = bool(fold_words(prefs.characteristics) & fold_words(lot_characteristics(lot)))
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
