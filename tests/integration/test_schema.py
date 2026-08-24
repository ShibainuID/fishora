import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError


def _constraint_names(connection, table: str) -> set[str]:
    return {
        row[0]
        for row in connection.execute(
            text("SELECT conname FROM pg_constraint WHERE conrelid = CAST(:table AS regclass)"),
            {"table": table},
        )
    }


@pytest.mark.integration
def test_pgvector_schema(engine):
    inspector = inspect(engine)
    assert {"fish_species", "knowledge_sources", "knowledge_chunks", "predictions"} <= set(inspector.get_table_names())
    columns = {column["name"]: column for column in inspector.get_columns("knowledge_chunks")}
    assert str(columns["embedding"]["type"]) == "VECTOR(768)"
    assert str(columns["embedding_model"]["type"]) == "VARCHAR(160)"
    assert columns["embedding"]["nullable"] is False
    assert columns["embedding_model"]["nullable"] is False
    with engine.connect() as connection:
        assert connection.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")).scalar_one() == "vector"
        for table, constraint in (
            ("knowledge_sources", "ck_knowledge_sources_verification_status"),
            ("knowledge_chunks", "ck_knowledge_chunks_verification_status"),
        ):
            names = _constraint_names(connection, table)
            assert constraint in names, f"{table} must constrain verification_status"


@pytest.mark.integration
def test_commerce_tables_exist_with_knowledge_snapshot(engine):
    inspector = inspect(engine)
    assert {"landing_points", "lots", "bids", "buyer_preferences"} <= set(inspector.get_table_names())
    lot_columns = {column["name"]: column for column in inspector.get_columns("lots")}
    assert "knowledge_snapshot" in lot_columns
    assert "prediction_id" in lot_columns
    bid_indexes = {index["name"] for index in inspector.get_indexes("bids")}
    assert "ix_bids_lot_id_created_at" in bid_indexes
    with engine.connect() as connection:
        names = _constraint_names(connection, "lots")
        for required in (
            "ck_lots_status",
            "ck_lots_quantity_positive",
            "ck_lots_price_positive",
            "ck_lots_auction_window",
        ):
            assert required in names
        assert "ck_bids_amount_positive" in _constraint_names(connection, "bids")


def _seed_commerce_parents(connection) -> None:
    connection.execute(text(
        "INSERT INTO fish_species (id, normalized_label, common_name_id, taxonomic_rank, taxonomy_status) "
        "VALUES ('species_schema_tenggiri', 'schema_tenggiri', 'Tenggiri', 'SPECIES', 'VERIFIED_TAXONOMY') "
        "ON CONFLICT (id) DO NOTHING"
    ))
    connection.execute(text(
        "INSERT INTO predictions (id, image_reference, predicted_species_id, confidence, top_candidates, "
        "model_version, verification_status, verified_species_id) "
        "VALUES ('pred_schema_1', 'images/x.jpg', 'species_schema_tenggiri', 0.9, '[]'::jsonb, "
        "'test', 'confirmed', 'species_schema_tenggiri') "
        "ON CONFLICT (id) DO NOTHING"
    ))
    connection.execute(text(
        "INSERT INTO landing_points (id, name, latitude, longitude) "
        "VALUES ('lp_schema_1', 'PPI Muara Angke', -6.104, 106.792) "
        "ON CONFLICT (id) DO NOTHING"
    ))


def _insert_lot(connection, **overrides):
    row = {
        "id": "lot_schema_ok",
        "prediction_id": "pred_schema_1",
        "operator_id": "op_1",
        "species_id": "species_schema_tenggiri",
        "landing_point_id": "lp_schema_1",
        "quantity_kg": 24,
        "size_category": "L",
        "starting_price_per_kg": 68000,
        "status": "active",
        "auction_starts_at": "2026-08-24 10:00:00+00",
        "auction_ends_at": "2026-08-24 14:00:00+00",
        "public_slug": "tenggiri-schema-ok",
        **overrides,
    }
    connection.execute(
        text(
            "INSERT INTO lots (id, prediction_id, operator_id, species_id, landing_point_id, "
            "quantity_kg, size_category, starting_price_per_kg, status, auction_starts_at, "
            "auction_ends_at, public_slug) "
            "VALUES (:id, :prediction_id, :operator_id, :species_id, :landing_point_id, "
            ":quantity_kg, :size_category, :starting_price_per_kg, :status, "
            ":auction_starts_at, :auction_ends_at, :public_slug)"
        ),
        row,
    )


@pytest.mark.integration
def test_lot_status_constraint_rejects_unknown_status(engine):
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            _seed_commerce_parents(connection)
            _insert_lot(connection, id="lot_bad_status", status="open", public_slug="bad-status")


@pytest.mark.integration
def test_lot_quantity_must_be_positive(engine):
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            _seed_commerce_parents(connection)
            _insert_lot(connection, id="lot_qty", quantity_kg=0, public_slug="qty-zero")


@pytest.mark.integration
def test_lot_price_must_be_positive(engine):
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            _seed_commerce_parents(connection)
            _insert_lot(connection, id="lot_price", starting_price_per_kg=0, public_slug="price-zero")


@pytest.mark.integration
def test_auction_end_must_follow_start(engine):
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            _seed_commerce_parents(connection)
            _insert_lot(
                connection,
                id="lot_window",
                public_slug="window-bad",
                auction_starts_at="2026-08-24 14:00:00+00",
                auction_ends_at="2026-08-24 10:00:00+00",
            )


@pytest.mark.integration
def test_bid_amount_must_be_positive(engine):
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            _seed_commerce_parents(connection)
            _insert_lot(connection, id="lot_bid_parent", public_slug="bid-parent")
            connection.execute(
                text(
                    "INSERT INTO bids (id, lot_id, buyer_id, amount_per_kg) "
                    "VALUES ('bid_zero', 'lot_bid_parent', 'buyer_1', 0)"
                )
            )
