"""Database engine/session setup. Works with SQLite (local dev) and SQL Server (Azure SQL)."""
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings


NAMING = {  # readable, predictable constraint names on every database
    "pk": "pk_%(table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s",
    "ix": "ix_%(table_name)s_%(column_0_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)


def make_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        engine = create_engine(url, connect_args=connect_args)

        @event.listens_for(engine, "connect")
        def _enable_fk(dbapi_conn, _):  # SQLite ignores foreign keys unless asked
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

        return engine
    # SQL Server / Azure SQL (needs pyodbc + Microsoft ODBC Driver 18)
    return create_engine(url, pool_pre_ping=True)


engine = make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
