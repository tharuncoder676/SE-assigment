"""Pydantic v2 request/response contracts.

These classes are the single source of truth for the OpenAPI document that
FastAPI publishes at /docs, which is what makes the design API-first.
"""
import datetime as dt
from typing import Optional

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(max_length=160)
    phone: str = Field(default="", max_length=20)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="patient", pattern="^(patient|doctor|admin)$")


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str
    full_name: str


class DoctorOut(BaseModel):
    id: int
    name: str
    speciality: str
    department: str
    qualification: str
    consultation_fee: int
    is_available: bool

    class Config:
        from_attributes = True


class SlotOut(BaseModel):
    id: int
    doctor_id: int
    start_at: dt.datetime
    end_at: dt.datetime
    is_booked: bool

    class Config:
        from_attributes = True


class BookingRequest(BaseModel):
    slot_id: int
    reason: str = Field(default="", max_length=500)


class AppointmentOut(BaseModel):
    id: int
    reference: str
    doctor_name: str
    speciality: str
    start_at: dt.datetime
    status: str
    reason: str


class NotificationOut(BaseModel):
    id: int
    subject: str
    body: str
    channel: str
    is_read: bool
    created_at: dt.datetime

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    detail: str
    reference: Optional[str] = None
