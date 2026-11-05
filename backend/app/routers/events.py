from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..deps import get_optional_user, require_organizer
from ..models import CANCELLED, REGISTERED, Category, Event, Registration, User
from ..schemas import AttendeeOut, CategoryOut, EventCreate, EventOut, EventUpdate
from ..services.activity import log_activity
from ..services.events import count_registered, events_with_counts, registered_event_ids, to_event_out, utcnow
from ..services.storage import StorageError, detect_image_type, get_storage

router = APIRouter(prefix="/api", tags=["Events"])


def _build(db: Session, rows, user: User | None) -> list[EventOut]:
    ids = registered_event_ids(db, user.id if user else None, [e.id for e, _ in rows])
    return [to_event_out(e, n, ids) for e, n in rows]


def _owned_event(db: Session, event_id: int, user: User) -> Event:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(404, "Event not found.")
    if event.organizer_id != user.id:
        raise HTTPException(403, "You can only manage your own events.")
    return event


def _check_category(db: Session, category_id: int) -> None:
    if db.get(Category, category_id) is None:
        raise HTTPException(422, "Unknown category_id.")


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.scalars(select(Category).order_by(Category.name)).all()


@router.get("/events", response_model=list[EventOut])
def list_events(
    q: str | None = Query(None, max_length=100),
    category_id: int | None = None,
    include_past: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    stmt = events_with_counts().where(Event.status == "published")
    if not include_past:
        stmt = stmt.where(Event.end_time >= utcnow())
    if category_id:
        stmt = stmt.where(Event.category_id == category_id)
    if q and q.strip():
        term = q.strip()
        stmt = stmt.where(
            Event.title.icontains(term, autoescape=True)
            | Event.description.icontains(term, autoescape=True)
            | Event.location.icontains(term, autoescape=True)
        )
    rows = db.execute(stmt.order_by(Event.start_time).offset(skip).limit(limit)).unique().all()
    return _build(db, rows, user)


@router.get("/events/mine", response_model=list[EventOut])
def my_events(db: Session = Depends(get_db), user: User = Depends(require_organizer)):
    rows = db.execute(events_with_counts().where(Event.organizer_id == user.id).order_by(Event.start_time.desc())).unique().all()
    return _build(db, rows, user)


@router.get("/events/{event_id}", response_model=EventOut)
def get_event(event_id: int, db: Session = Depends(get_db), user: User | None = Depends(get_optional_user)):
    row = db.execute(events_with_counts().where(Event.id == event_id)).unique().first()
    if row is None:
        raise HTTPException(404, "Event not found.")
    return _build(db, [row], user)[0]


@router.post("/events", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def create_event(data: EventCreate, db: Session = Depends(get_db), user: User = Depends(require_organizer)):
    _check_category(db, data.category_id)
    event = Event(**data.model_dump(), organizer_id=user.id, status="published")
    db.add(event)
    db.flush()
    log_activity(db, user.id, "event_created", "event", event.id)
    db.commit()
    return get_event(event.id, db, user)


@router.put("/events/{event_id}", response_model=EventOut)
def update_event(event_id: int, data: EventUpdate, db: Session = Depends(get_db), user: User = Depends(require_organizer)):
    event = _owned_event(db, event_id, user)
    if event.status == CANCELLED:
        raise HTTPException(409, "A cancelled event cannot be edited.")
    _check_category(db, data.category_id)
    if data.capacity < count_registered(db, event.id):
        raise HTTPException(409, "Capacity cannot be lower than the current number of registrations.")
    for field, value in data.model_dump().items():
        setattr(event, field, value)
    log_activity(db, user.id, "event_updated", "event", event.id)
    db.commit()
    return get_event(event.id, db, user)


@router.post("/events/{event_id}/cancel", response_model=EventOut)
def cancel_event(event_id: int, db: Session = Depends(get_db), user: User = Depends(require_organizer)):
    event = _owned_event(db, event_id, user)
    if event.status == CANCELLED:
        raise HTTPException(409, "Event is already cancelled.")
    event.status = CANCELLED
    log_activity(db, user.id, "event_cancelled", "event", event.id)
    db.commit()
    return get_event(event.id, db, user)


@router.get("/events/{event_id}/attendees", response_model=list[AttendeeOut])
def attendees(event_id: int, db: Session = Depends(get_db), user: User = Depends(require_organizer)):
    _owned_event(db, event_id, user)
    rows = db.execute(
        select(Registration, User).join(User, User.id == Registration.user_id)
        .where(Registration.event_id == event_id, Registration.status == REGISTERED)
        .order_by(Registration.registered_at)
    ).all()
    return [
        AttendeeOut(registration_id=r.id, user_id=u.id, full_name=u.full_name, email=u.email, status=r.status, registered_at=r.registered_at)
        for r, u in rows
    ]


@router.post("/events/{event_id}/poster", response_model=EventOut)
async def upload_poster(event_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(require_organizer)):
    event = _owned_event(db, event_id, user)
    max_bytes = get_settings().max_upload_bytes
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(413, f"File too large (max {max_bytes // 1024 // 1024} MB).")
    content_type = detect_image_type(data)
    if content_type is None:
        raise HTTPException(415, "Only JPEG, PNG or WebP images are allowed.")
    storage = get_storage()
    try:
        new_key = storage.save(data, content_type)
    except StorageError:
        raise HTTPException(502, "File storage is unavailable. The poster was NOT saved.")
    old_key = event.poster_key
    event.poster_key, event.poster_content_type = new_key, content_type
    log_activity(db, user.id, "poster_uploaded", "event", event.id)
    db.commit()
    if old_key:
        storage.delete(old_key)
    return get_event(event.id, db, user)


@router.get("/events/{event_id}/poster")
def get_poster(event_id: int, db: Session = Depends(get_db)):
    event = db.get(Event, event_id)
    if event is None or not event.poster_key:
        raise HTTPException(404, "Poster not found.")
    try:
        data = get_storage().read(event.poster_key)
    except StorageError:
        raise HTTPException(502, "File storage is unavailable.")
    return Response(content=data, media_type=event.poster_content_type or "application/octet-stream",
                    headers={"Cache-Control": "public, max-age=300"})
