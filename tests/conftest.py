import pytest

from apps.main_api.config import MainSettings
from apps.main_api.db import models  # noqa: F401  (registers pgvector types for reflection)
from apps.main_api.db.session import create_engine_from_settings


@pytest.fixture(scope="session")
def engine():
    return create_engine_from_settings(MainSettings())