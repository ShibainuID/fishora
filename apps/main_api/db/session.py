from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from apps.main_api.config import MainSettings


def create_engine_from_settings(settings: MainSettings) -> Engine:
    return create_engine(settings.database_url, pool_pre_ping=True)


def session_factory(settings: MainSettings) -> sessionmaker[Session]:
    return sessionmaker(bind=create_engine_from_settings(settings), expire_on_commit=False)