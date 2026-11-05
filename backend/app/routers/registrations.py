from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_participant
from ..models import CANCELLED, REGISTERED, Event, Registration, User
from ..schemas import RegistrationOut
from ..services.activity import log_activity
from ..services.events import count_registered, utcnow

router = APIRouter(prefix="/api", tags=["Registrations"])


def _out(r: Registration, e: Event) -> RegistrationOut:
    return RegistrationOut(
        id=r.id, event_id=e.id, status=r.status, registered_at=r.registered_at, cancelled_at=r.cancelled_at,
        event_title=e.title, event_start_time=e.start_time, event_location=e.location, event_status=e.status,
    )


@router.post("/events/{event_id}/register", response_model=RegistrationOut, status_code=status.HTTP_201_CREATED)
def register_for_event(event_id: int, db: Session = Depends(get_db), user: User = Depends(require_participant)):
    """One transaction: lock event row -> validate -> insert/reactivate registration -> audit log.
    The unique constraint and the capacity trigger are the final safety net against races."""
    event = db.execute(select(Event).where(Event.id == event_id).with_for_update()).scalar_one_or_none()
    if event is None:
        raise HTTPException(404, "Event not found.")
    if event.status != "published":
        raise HTTPException(409, "This event has been cancelled.")
    if event.start_time <= utcnow():
        raise HTTPException(409, "Registration is closed: the event has already started.")

    reg = db.scalar(select(Registration).where(Registration.user_id == user.id, Registration.event_id == event_id))
    if reg is not None and reg.status == REGISTERED:
        raise HTTPException(409, "You are already registered for this event.")
    if count_registered(db, event_id) >= event.capacity:
        raise HTTPException(409, "This event is full.")

    try:
        if reg is None:
            reg = Registration(user_id=user.id, event_id=event_id, status=REGISTERED, registered_at=utcnow())
            db.add(reg)
        else:  # re-registering after an earlier cancellation reuses the same row
            reg.status, reg.registered_at, reg.cancelled_at = REGISTERED, utcnow(), None
        db.flush()
        log_activity(db, user.id, "registration_created", "registration", reg.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "You are already registered for this event.")
    except DBAPIError as exc:
        db.rollback()
        if "capacity" in str(exc).lower():
            raise HTTPException(409, "This event is full.")
        raise
    return _out(reg, event)


@router.delete("/events/{event_id}/register", response_model=RegistrationOut)
def cancel_registration(event_id: int, db: Session = Depends(get_db), user: User = Depends(require_participant)):
    reg = db.scalar(select(Registration).where(Registration.user_id == user.id, Registration.event_id == event_id))
    if reg is None or reg.status != REGISTERED:
        raise HTTPException(404, "You have no active registration for this event.")
    event = db.get(Event, event_id)
    if event.start_time <= utcnow():
        raise HTTPException(409, "You cannot cancel after the event has started.")
    reg.status, reg.cancelled_at = CANCELLED, utcnow()
    log_activity(db, user.id, "registration_cancelled", "registration", reg.id)
    db.commit()
    return _out(reg, event)


@router.get("/registrations/mine", response_model=list[RegistrationOut])
def my_registrations(db: Session = Depends(get_db), user: User = Depends(require_participant)):
    rows = db.execute(
        select(Registration, Event).join(Event, Event.id == Registration.event_id)
        .where(Registration.user_id == user.id).order_by(Event.start_time)
    ).all()
    return [_out(r, e) for r, e in rows]
