from collections import Counter
from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_organizer
from ..models import REGISTERED, Event, Registration, User, event_stats_view as v
from ..schemas import AnalyticsOut, CategoryStat, DailyStat, EventStat
from ..services.events import utcnow

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/organizer", response_model=AnalyticsOut)
def organizer_analytics(db: Session = Depends(get_db), user: User = Depends(require_organizer)):
    now = utcnow()
    # Per-event numbers come from the vw_event_stats database view (joins events, categories, registrations).
    rows = db.execute(select(v).where(v.c.organizer_id == user.id).order_by(v.c.start_time.desc())).mappings().all()

    def fill(r):
        return round(100.0 * r["registered_count"] / r["capacity"], 1) if r["capacity"] else 0.0

    events = [
        EventStat(event_id=r["event_id"], title=r["title"], category_name=r["category_name"], start_time=r["start_time"],
                  capacity=r["capacity"], registered_count=r["registered_count"], cancelled_count=r["cancelled_count"],
                  fill_rate_percent=fill(r))
        for r in rows
    ]
    active = [r for r in rows if r["status"] == "published"]
    avg_fill = round(sum(fill(r) for r in active) / len(active), 1) if active else 0.0

    cat_counter: dict[str, list[int]] = {}
    for r in active:
        c = cat_counter.setdefault(r["category_name"], [0, 0])
        c[0] += 1
        c[1] += r["registered_count"]

    since = now - timedelta(days=13)
    reg_times = db.scalars(
        select(Registration.registered_at).join(Event, Event.id == Registration.event_id)
        .where(Event.organizer_id == user.id, Registration.status == REGISTERED, Registration.registered_at >= since.replace(hour=0, minute=0, second=0, microsecond=0))
    ).all()
    per_day = Counter(t.date().isoformat() for t in reg_times)
    daily = [DailyStat(date=(since + timedelta(days=i)).date().isoformat(), registrations=per_day.get((since + timedelta(days=i)).date().isoformat(), 0)) for i in range(14)]

    return AnalyticsOut(
        total_events=len(rows),
        upcoming_events=sum(1 for r in active if r["start_time"] > now),
        cancelled_events=sum(1 for r in rows if r["status"] == "cancelled"),
        total_registrations=sum(r["registered_count"] for r in rows),
        total_cancellations=sum(r["cancelled_count"] for r in rows),
        average_fill_rate_percent=avg_fill,
        events=events,
        by_category=[CategoryStat(category_name=k, events=v[0], registrations=v[1]) for k, v in sorted(cat_counter.items())],
        registrations_last_14_days=daily,
    )
