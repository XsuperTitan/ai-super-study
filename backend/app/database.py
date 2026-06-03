from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.errors import AppError


class Base(DeclarativeBase):
    pass


_engine: Engine | None = None
_session_local: sessionmaker[Session] | None = None


def configure_database(database_url: str, pool_recycle: int = 3600) -> None:
    global _engine, _session_local

    if not database_url:
        _engine = None
        _session_local = None
        return

    _engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=pool_recycle,
    )
    _session_local = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)


def is_database_enabled() -> bool:
    return _session_local is not None


def get_db() -> Generator[Session, None, None]:
    if _session_local is None:
        raise AppError("HISTORY_DATABASE_DISABLED", "服务端历史记录未启用，当前可继续使用本地历史记录", 503)

    db = _session_local()
    try:
        yield db
    finally:
        db.close()
