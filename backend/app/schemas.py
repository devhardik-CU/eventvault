"""Pydantic request/response schemas with validation."""
import re
from datetime import datetime, timezone

from typing import Annotated

from pydantic import BaseModel, PlainSerializer, ConfigDict, EmailStr, Field, field_validator, model_validator


def _iso_utc(v: datetime) -> str:
    """Stored datetimes are naive UTC; send them with an explicit 'Z' so browsers don't treat them as local time."""
    return v.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


UtcDatetime = Annotated[datetime, PlainSerializer(_iso_utc, return_type=str)]


def _to_naive_utc(v: datetime) -> datetime:
    if v.tzinfo is not None:
        v = v.astimezone(timezone.utc).replace(tzinfo=None)
    return v


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: str = Field(default="participant", pattern="^(participant|organizer)$")

    @field_validator("full_name")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    @field_validator("password")
    @classmethod
    def _strong(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password is too long (max 72 bytes).")
        if not (re.search(r"[A-Za-z]", v) and re.search(r"\d", v)):
            raise ValueError("Password must contain at least one letter and one number.")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    email: EmailStr
    role_name: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class EventBase(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    description: str = Field(min_length=10, max_length=4000)
    location: str = Field(min_length=2, max_length=200)
    start_time: datetime
    end_time: datetime
    capacity: int = Field(gt=0, le=100000)
    category_id: int

    @field_validator("title", "description", "location")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Must not be blank.")
        return v

    @field_validator("start_time", "end_time")
    @classmethod
    def _utc(cls, v: datetime) -> datetime:
        return _to_naive_utc(v)

    @model_validator(mode="after")
    def _order(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time.")
        return self


class EventCreate(EventBase):
    @field_validator("start_time")
    @classmethod
    def _future(cls, v: datetime) -> datetime:
        if v <= datetime.now(timezone.utc).replace(tzinfo=None):
            raise ValueError("start_time must be in the future.")
        return v


class EventUpdate(EventBase):
    pass


class EventOut(BaseModel):
    id: int
    title: str
    description: str
    location: str
    start_time: UtcDatetime
    end_time: UtcDatetime
    capacity: int
    status: str
    category_id: int
    category_name: str
    organizer_id: int
    organizer_name: str
    registered_count: int
    spots_left: int
    has_poster: bool
    is_registered: bool = False  # whether the current user holds an active registration


class RegistrationOut(BaseModel):
    id: int
    event_id: int
    status: str
    registered_at: UtcDatetime
    cancelled_at: UtcDatetime | None
    event_title: str
    event_start_time: UtcDatetime
    event_location: str
    event_status: str


class AttendeeOut(BaseModel):
    registration_id: int
    user_id: int
    full_name: str
    email: EmailStr
    status: str
    registered_at: UtcDatetime


class EventStat(BaseModel):
    event_id: int
    title: str
    category_name: str
    start_time: UtcDatetime
    capacity: int
    registered_count: int
    cancelled_count: int
    fill_rate_percent: float


class CategoryStat(BaseModel):
    category_name: str
    events: int
    registrations: int


class DailyStat(BaseModel):
    date: str
    registrations: int


class AnalyticsOut(BaseModel):
    total_events: int
    upcoming_events: int
    cancelled_events: int
    total_registrations: int
    total_cancellations: int
    average_fill_rate_percent: float
    events: list[EventStat]
    by_category: list[CategoryStat]
    registrations_last_14_days: list[DailyStat]
