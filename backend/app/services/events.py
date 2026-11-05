"""Event queries shared by routers. Registered counts are computed from the registrations table."""
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from ..models import REGISTERED, Event, Registration
from ..schemas import EventOut


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _counts_subquery():
    return (
        select(Registration.event_id.label("event_id"), func.count(Registration.id).label("n"))
        .where(Registration.status == REGISTERED)
        .group_by(Registration.event_id)
        .subquery()
    )


def events_with_counts():
    counts = _counts_subquery()
    return (
        select(Event, func.coalesce(counts.c.n, 0))
        .outerjoin(counts, counts.c.event_id == Event.id)
        .options(joinedload(Event.category), joinedload(Event.organizer))
    )


def to_event_out(event: Event, registered_count: int, registered_ids: set[int]) -> EventOut:
    return EventOut(
        id=event.id, title=event.title, description=event.description, location=event.location,
        start_time=event.start_time, end_time=event.end_time, capacity=event.capacity, status=event.status,
        category_id=event.category_id, category_name=event.category.name,
        organizer_id=event.organizer_id, organizer_name=event.organizer.full_name,
        registered_count=registered_count, spots_left=max(event.capacity - registered_count, 0),
        has_poster=bool(event.poster_key), is_registered=event.id in registered_ids,
    )


def registered_event_ids(db: Session, user_id: int | None, event_ids: list[int]) -> set[int]:
    if user_id is None or not event_ids:
        return set()
    rows = db.execute(
        select(Registration.event_id).where(
            Registration.user_id == user_id, Registration.status == REGISTERED, Registration.event_id.in_(event_ids)
        )
    ).scalars()
    return set(rows)


def count_registered(db: Session, event_id: int) -> int:
    return db.scalar(
        select(func.count(Registration.id)).where(Registration.event_id == event_id, Registration.status == REGISTERED)
    ) or 0
