"""Seed lookup data and create the view + trigger.

SQLite (local) and SQL Server (Azure) each get their own SQL dialect.
The SQL Server versions here mirror database/sqlserver/*.sql and are NOT verifiable in the
development sandbox (no SQL Server available)."""
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine
from .models import Category, Role

DEFAULT_CATEGORIES = ["Workshop", "Seminar", "Competition", "Cultural", "Sports", "Networking"]

VIEW_SQLITE = """
CREATE VIEW IF NOT EXISTS vw_event_stats AS
SELECT e.id AS event_id, e.title, e.organizer_id, e.category_id, c.name AS category_name,
       e.start_time, e.status, e.capacity,
       COALESCE(SUM(CASE WHEN r.status = 'registered' THEN 1 ELSE 0 END), 0) AS registered_count,
       COALESCE(SUM(CASE WHEN r.status = 'cancelled' THEN 1 ELSE 0 END), 0) AS cancelled_count
FROM events e
JOIN categories c ON c.id = e.category_id
LEFT JOIN registrations r ON r.event_id = e.id
GROUP BY e.id, e.title, e.organizer_id, e.category_id, c.name, e.start_time, e.status, e.capacity
"""

VIEW_MSSQL = VIEW_SQLITE.replace("CREATE VIEW IF NOT EXISTS", "CREATE OR ALTER VIEW")

TRIGGERS_SQLITE = [
    """CREATE TRIGGER IF NOT EXISTS trg_registrations_capacity_ins
BEFORE INSERT ON registrations
WHEN NEW.status = 'registered'
 AND (SELECT COUNT(*) FROM registrations WHERE event_id = NEW.event_id AND status = 'registered')
     >= (SELECT capacity FROM events WHERE id = NEW.event_id)
BEGIN SELECT RAISE(ABORT, 'Event capacity exceeded.'); END""",
    """CREATE TRIGGER IF NOT EXISTS trg_registrations_capacity_upd
BEFORE UPDATE OF status ON registrations
WHEN NEW.status = 'registered' AND OLD.status <> 'registered'
 AND (SELECT COUNT(*) FROM registrations WHERE event_id = NEW.event_id AND status = 'registered')
     >= (SELECT capacity FROM events WHERE id = NEW.event_id)
BEGIN SELECT RAISE(ABORT, 'Event capacity exceeded.'); END""",
]

TRIGGER_MSSQL = """
CREATE OR ALTER TRIGGER dbo.trg_registrations_capacity ON dbo.registrations AFTER INSERT, UPDATE AS
BEGIN
  SET NOCOUNT ON;
  IF EXISTS (
    SELECT 1 FROM inserted i JOIN dbo.events AS e WITH (UPDLOCK, ROWLOCK) ON e.id = i.event_id
    WHERE i.status = 'registered'
      AND (SELECT COUNT(*) FROM dbo.registrations r WHERE r.event_id = e.id AND r.status = 'registered') > e.capacity)
  BEGIN
    ROLLBACK TRANSACTION;
    THROW 50001, 'Event capacity exceeded.', 1;
  END
END
"""


def create_db_objects(eng: Engine) -> None:
    with eng.begin() as conn:
        if eng.dialect.name == "sqlite":
            conn.execute(text(VIEW_SQLITE))
            for t in TRIGGERS_SQLITE:
                conn.execute(text(t))
        elif eng.dialect.name == "mssql":
            conn.execute(text(VIEW_MSSQL))
            conn.execute(text(TRIGGER_MSSQL))


def seed_lookups(db: Session) -> None:
    for name in ("participant", "organizer"):
        if not db.query(Role).filter_by(name=name).first():
            db.add(Role(name=name))
    for name in DEFAULT_CATEGORIES:
        if not db.query(Category).filter_by(name=name).first():
            db.add(Category(name=name))
    db.commit()


def init_db(eng: Engine = engine) -> None:
    Base.metadata.create_all(eng)
    create_db_objects(eng)
    db = SessionLocal(bind=eng)
    try:
        seed_lookups(db)
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    print("Database initialised.")
