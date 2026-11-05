import logging

from sqlalchemy.orm import Session

from ..models import ActivityLog

logger = logging.getLogger("eventvault.activity")


def log_activity(db: Session, user_id: int | None, action: str, entity: str, entity_id: int | None = None) -> None:
    """Add an audit row to the current transaction (caller commits) and write a log line."""
    db.add(ActivityLog(user_id=user_id, action=action, entity=entity, entity_id=entity_id))
    logger.info("user=%s action=%s entity=%s id=%s", user_id, action, entity, entity_id)
