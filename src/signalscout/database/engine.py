from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from signalscout.config import Settings
from signalscout.database.models import Base


def build_engine(settings: Settings):
    settings.database_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(settings.database_url, future=True)
    Base.metadata.create_all(engine)
    return engine


def build_session_factory(settings: Settings) -> sessionmaker[Session]:
    engine = build_engine(settings)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)
