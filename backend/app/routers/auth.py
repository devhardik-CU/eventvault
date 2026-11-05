from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import get_current_user
from ..models import Role, User
from ..schemas import LoginIn, RegisterIn, TokenOut, UserOut
from ..security import create_access_token, hash_password, verify_password
from ..services.activity import log_activity

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")
    role = db.query(Role).filter(Role.name == data.role).one()
    user = User(full_name=data.full_name, email=email, password_hash=hash_password(data.password), role_id=role.id)
    db.add(user)
    try:
        db.flush()
        log_activity(db, user.id, "user_registered", "user", user.id)
        db.commit()
    except IntegrityError:  # two simultaneous sign-ups with the same email
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")
    user = db.query(User).options(joinedload(User.role)).filter(User.id == user.id).one()
    return TokenOut(access_token=create_access_token(user.id, user.role_name), user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).options(joinedload(User.role)).filter(User.email == data.email.lower()).first()
    if not verify_password(data.password, user.password_hash if user else None):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")
    log_activity(db, user.id, "user_login", "user", user.id)
    db.commit()
    return TokenOut(access_token=create_access_token(user.id, user.role_name), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
