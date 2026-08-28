from collections.abc import Generator
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
if settings.database_url.startswith("sqlite"):
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_recycle=int(os.getenv("DATABASE_POOL_RECYCLE_SECONDS", "300")),
        pool_timeout=int(os.getenv("DATABASE_POOL_TIMEOUT_SECONDS", "5")),
        connect_args={"connect_timeout": int(os.getenv("DATABASE_CONNECT_TIMEOUT_SECONDS", "5"))},
    )
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

