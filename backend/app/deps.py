"""Shared FastAPI dependencies: current user + role checks."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, joinedload

from .database import get_db
from .models import ROLE_ORGANIZER, ROLE_PARTICIPANT, User
from .security import decode_access_token

bearer = HTTPBearer(auto_error=False)


def _user_from_creds(creds: HTTPAuthorizationCredentials | None, db: Session) -> User | None:
    if creds is None:
        return None
    payload = decode_access_token(creds.credentials)
    if not payload:
        return None
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError):
        return None
    # Always re-read the user (and role) from the DB; never trust the role stored in the token.
    return db.query(User).options(joinedload(User.role)).filter(User.id == user_id).first()


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    user = _user_from_creds(creds, db)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated.", headers={"WWW-Authenticate": "Bearer"})
    return user


def get_optional_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User | None:
    return _user_from_creds(creds, db)


def require_organizer(user: User = Depends(get_current_user)) -> User:
    if user.role_name != ROLE_ORGANIZER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Organizer role required.")
    return user


def require_participant(user: User = Depends(get_current_user)) -> User:
    if user.role_name != ROLE_PARTICIPANT:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Participant role required.")
    return user
