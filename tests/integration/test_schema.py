import pytest
from sqlalchemy import inspect, text


@pytest.mark.integration
def test_pgvector_schema(engine):
    inspector = inspect(engine)
    assert {"fish_species", "knowledge_sources", "knowledge_chunks", "predictions"} <= set(inspector.get_table_names())
    columns = {column["name"]: column for column in inspector.get_columns("knowledge_chunks")}
    assert str(columns["embedding"]["type"]) == "VECTOR(768)"
    with engine.connect() as connection:
        assert connection.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")).scalar_one() == "vector"