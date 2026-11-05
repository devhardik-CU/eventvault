"""SQLAlchemy models (3NF). Registration counts are derived, never stored."""
from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, MetaData, Table, Unicode, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

REGISTERED = "registered"
CANCELLED = "cancelled"
ROLE_PARTICIPANT = "participant"
ROLE_ORGANIZER = "organizer"


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Unicode(30), unique=True, nullable=False)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    email: Mapped[str] = mapped_column(Unicode(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    role: Mapped[Role] = relationship()

    @property
    def role_name(self) -> str:
        return self.role.name


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Unicode(50), unique=True, nullable=False)


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_events_capacity_positive"),
        CheckConstraint("end_time > start_time", name="ck_events_end_after_start"),
        CheckConstraint("status IN ('published','cancelled')", name="ck_events_status"),
        Index("ix_events_start_time", "start_time"),
        Index("ix_events_category_id", "category_id"),
        Index("ix_events_organizer_id", "organizer_id"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(Unicode(150), nullable=False)
    description: Mapped[str] = mapped_column(Unicode(4000), nullable=False)
    location: Mapped[str] = mapped_column(Unicode(200), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # naive UTC
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # naive UTC
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Unicode(20), nullable=False, default="published")
    poster_key: Mapped[str | None] = mapped_column(Unicode(200), nullable=True)
    poster_content_type: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    organizer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    organizer: Mapped[User] = relationship()
    category: Mapped[Category] = relationship()


class Registration(Base):
    __tablename__ = "registrations"
    __table_args__ = (
        UniqueConstraint("user_id", "event_id", name="uq_registrations_user_event"),
        CheckConstraint("status IN ('registered','cancelled')", name="ck_registrations_status"),
        Index("ix_registrations_event_id", "event_id"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False)
    status: Mapped[str] = mapped_column(Unicode(20), nullable=False, default=REGISTERED)
    registered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[User] = relationship()
    event: Mapped[Event] = relationship()


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    __table_args__ = (Index("ix_activity_logs_created_at", "created_at"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(Unicode(50), nullable=False)
    entity: Mapped[str] = mapped_column(Unicode(50), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


# Read-only description of the vw_event_stats database view (created in db_objects.py).
# Kept in a separate MetaData so create_all() never tries to create it as a table.
event_stats_view = Table(
    "vw_event_stats", MetaData(),
    Column("event_id", Integer), Column("title", Unicode), Column("organizer_id", Integer),
    Column("category_id", Integer), Column("category_name", Unicode), Column("start_time", DateTime),
    Column("status", Unicode), Column("capacity", Integer),
    Column("registered_count", Integer), Column("cancelled_count", Integer),
)
