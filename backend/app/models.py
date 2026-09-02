"""Domain model.

Users -> Doctors -> Slots -> Appointments -> Notifications / AuditLog.
The unique constraint on Slot(doctor_id, start_at) plus the unique index on
Appointment(slot_id) is what makes double booking impossible at the storage
layer rather than only in application code.
"""
import datetime as dt

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(20), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="patient")  # patient|doctor|admin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

    appointments: Mapped[list["Appointment"]] = relationship(back_populates="patient")


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    speciality: Mapped[str] = mapped_column(String(80), index=True)
    department: Mapped[str] = mapped_column(String(80))
    qualification: Mapped[str] = mapped_column(String(120), default="")
    consultation_fee: Mapped[int] = mapped_column(Integer, default=500)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)

    slots: Mapped[list["Slot"]] = relationship(
        back_populates="doctor", cascade="all, delete-orphan"
    )


class Slot(Base):
    """A bookable unit of a doctor's calendar."""
    __tablename__ = "slots"
    __table_args__ = (UniqueConstraint("doctor_id", "start_at", name="uq_doctor_slot"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), index=True)
    start_at: Mapped[dt.datetime] = mapped_column(DateTime, index=True)
    end_at: Mapped[dt.datetime] = mapped_column(DateTime)
    is_booked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    doctor: Mapped[Doctor] = relationship(back_populates="slots")


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), index=True)
    slot_id: Mapped[int] = mapped_column(ForeignKey("slots.id"), unique=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="CONFIRMED", index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

    patient: Mapped[User] = relationship(back_populates="appointments")
    doctor: Mapped[Doctor] = relationship()
    slot: Mapped[Slot] = relationship()


class Notification(Base):
    """Written asynchronously by the event bus subscriber."""
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    channel: Mapped[str] = mapped_column(String(20), default="in-app")
    subject: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class AuditLog(Base):
    """Append-only trail required for patient-data accountability."""
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(160), index=True)
    action: Mapped[str] = mapped_column(String(60), index=True)
    entity: Mapped[str] = mapped_column(String(60))
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
