from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from extraction_engine.config import Settings


class Base(DeclarativeBase):
    pass


def get_engine(settings: Settings):
    return create_engine(settings.database_url, pool_pre_ping=True)


def get_session_factory(settings: Settings):
    engine = get_engine(settings)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)
