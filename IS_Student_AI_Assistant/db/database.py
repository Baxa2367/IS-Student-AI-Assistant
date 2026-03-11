from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base


def init_db(sqlite_path: str) -> sessionmaker:
    """
    Initialize the SQLAlchemy engine/session and create tables.
    Migrations are not used; create_all() runs on startup.
    """
    engine = create_engine(f"sqlite:///{sqlite_path}", echo=False, future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)