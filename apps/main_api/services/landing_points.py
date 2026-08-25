"""Demo landing points used by the operator form and geo filter."""

from apps.main_api.contracts import LandingPointRecord

DEMO_LANDING_POINTS = (
    LandingPointRecord(id="lp_muara_angke", name="PPI Muara Angke", latitude=-6.104, longitude=106.792),
    LandingPointRecord(id="lp_cilacap", name="TPI Cilacap", latitude=-7.732, longitude=109.015),
    LandingPointRecord(id="lp_karangsong", name="PPI Karangsong", latitude=-6.305, longitude=108.320),
)


def seed_demo_landing_points(repo) -> None:
    for point in DEMO_LANDING_POINTS:
        repo.upsert(point)
