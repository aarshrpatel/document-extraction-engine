from functools import lru_cache
from typing import Generator

from sqlalchemy.orm import Session

from extraction_engine.config import Settings, get_settings
from extraction_engine.db.session import get_session_factory
from extraction_engine.pipeline.pipeline import ExtractionPipeline


@lru_cache
def _get_session_factory():
    return get_session_factory(get_settings())


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions."""
    session_factory = _get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@lru_cache
def get_pipeline() -> ExtractionPipeline:
    """Get shared pipeline instance."""
    return ExtractionPipeline(get_settings())
