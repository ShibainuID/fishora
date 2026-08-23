import pytest
from sqlalchemy import inspect, text


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
            names = {
                row[0] for row in connection.execute(
                    text("SELECT conname FROM pg_constraint WHERE conrelid = CAST(:table AS regclass)"),
                    {"table": table},
                )
            }
            assert constraint in names, f"{table} must constrain verification_status"