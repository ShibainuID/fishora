"""Haversine serviceability radius. A distance proxy, never a freshness claim."""

from math import atan2, cos, radians, sin, sqrt

EARTH_RADIUS_KM = 6371.0
DEFAULT_SERVICEABILITY_RADIUS_KM = 100.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = radians(lat1), radians(lat2)
    d_phi = radians(lat2 - lat1)
    d_lambda = radians(lon2 - lon1)
    chord = sin(d_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * atan2(sqrt(chord), sqrt(1 - chord))


def within_serviceability(
    buyer_lat: float,
    buyer_lon: float,
    lot_lat: float,
    lot_lon: float,
    radius_km: float = DEFAULT_SERVICEABILITY_RADIUS_KM,
) -> bool:
    return haversine_km(buyer_lat, buyer_lon, lot_lat, lot_lon) <= radius_km + 1e-9
