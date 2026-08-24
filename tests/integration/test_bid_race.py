import threading
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from apps.main_api.db.lot_repository import SqlLotRepository
from apps.main_api.errors import BidOutbid


def _seed(connection) -> None:
    connection.execute(text(
        "INSERT INTO fish_species (id, normalized_label, common_name_id, taxonomic_rank, taxonomy_status) "
        "VALUES ('species_race_tenggiri', 'race_tenggiri', 'Tenggiri', 'SPECIES', 'VERIFIED_TAXONOMY') "
        "ON CONFLICT (id) DO NOTHING"
    ))
    connection.execute(text(
        "INSERT INTO predictions (id, image_reference, predicted_species_id, confidence, top_candidates, "
        "model_version, verification_status, verified_species_id) "
        "VALUES ('pred_race_1', 'images/race.jpg', 'species_race_tenggiri', 0.9, '[]'::jsonb, "
        "'test', 'confirmed', 'species_race_tenggiri') "
        "ON CONFLICT (id) DO NOTHING"
    ))
    connection.execute(text(
        "INSERT INTO landing_points (id, name, latitude, longitude) "
        "VALUES ('lp_race_1', 'PPI Muara Angke', -6.104, 106.792) "
        "ON CONFLICT (id) DO NOTHING"
    ))
    now = datetime(2026, 8, 24, 10, 0, tzinfo=timezone.utc)
    connection.execute(text(
        "INSERT INTO lots (id, prediction_id, operator_id, species_id, landing_point_id, quantity_kg, "
        "size_category, starting_price_per_kg, status, auction_starts_at, auction_ends_at, public_slug) "
        "VALUES ('lot_race_1', 'pred_race_1', 'op_1', 'species_race_tenggiri', 'lp_race_1', 24, "
        "'L', 68000, 'active', :starts, :ends, 'tenggiri-race1') "
        "ON CONFLICT (id) DO UPDATE SET status = 'active', allocated_buyer_id = NULL"
    ), {"starts": now, "ends": now + timedelta(hours=4)})
    connection.execute(text("DELETE FROM bids WHERE lot_id = 'lot_race_1'"))


@pytest.mark.integration
def test_concurrent_equal_bids_cannot_both_win(engine):
    with engine.begin() as connection:
        _seed(connection)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    repo = SqlLotRepository(factory)
    barrier = threading.Barrier(2)
    outcomes: list[object] = [None, None]

    def worker(index: int, buyer_id: str) -> None:
        barrier.wait()
        try:
            outcomes[index] = repo.place_bid("lot_race_1", buyer_id, Decimal("70000"))
        except BidOutbid as exc:
            outcomes[index] = exc

    threads = [
        threading.Thread(target=worker, args=(0, "buyer_a")),
        threading.Thread(target=worker, args=(1, "buyer_b")),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    wins = [item for item in outcomes if not isinstance(item, BidOutbid)]
    losses = [item for item in outcomes if isinstance(item, BidOutbid)]
    assert len(wins) == 1
    assert len(losses) == 1
    assert Decimal(losses[0].current_highest_per_kg) == Decimal("70000")
    assert len(repo.list_bids("lot_race_1")) == 1
