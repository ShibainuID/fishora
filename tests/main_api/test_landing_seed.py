from tests.main_api.fakes import FakeLandingPointRepository
from apps.main_api.services.landing_points import DEMO_LANDING_POINTS, seed_demo_landing_points


def test_demo_landing_points_match_the_operator_form_labels():
    names = {point.name for point in DEMO_LANDING_POINTS}
    ids = {point.id for point in DEMO_LANDING_POINTS}
    assert names == {"PPI Muara Angke", "TPI Cilacap", "PPI Karangsong"}
    assert ids == {"lp_muara_angke", "lp_cilacap", "lp_karangsong"}


def test_seed_landing_points_is_idempotent():
    repo = FakeLandingPointRepository()
    seed_demo_landing_points(repo)
    seed_demo_landing_points(repo)
    assert {point.id for point in repo.all()} == {
        "lp_muara_angke",
        "lp_cilacap",
        "lp_karangsong",
    }
