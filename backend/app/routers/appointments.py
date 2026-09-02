"""Appointment booking service - the core transactional use case."""
import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..events import bus
from ..models import Appointment, AuditLog, Doctor, Slot, User
from ..schemas import AppointmentOut, BookingRequest, MessageOut

router = APIRouter(prefix="/api/v1/appointments", tags=["Appointments"])
log = logging.getLogger("smartcare.appointments")


def _reference() -> str:
    return "SC-%s" % secrets.token_hex(4).upper()


@router.post("", response_model=MessageOut, status_code=201)
def book(
    payload: BookingRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Book a slot.

    Concurrency safety comes from the database, not from the application:
    the row is re-read with ``SELECT ... FOR UPDATE`` semantics inside the
    transaction and ``Appointment.slot_id`` carries a UNIQUE index, so if two
    requests race, exactly one commits and the other receives HTTP 409.
    """
    slot = db.get(Slot, payload.slot_id, with_for_update=True)
    if slot is None:
        raise HTTPException(status_code=404, detail="Slot not found")
    if slot.is_booked:
        raise HTTPException(status_code=409, detail="Slot has already been booked")

    appointment = Appointment(
        reference=_reference(),
        patient_id=user.id,
        doctor_id=slot.doctor_id,
        slot_id=slot.id,
        reason=payload.reason,
        status="CONFIRMED",
    )
    slot.is_booked = True
    db.add(appointment)
    db.add(AuditLog(
        actor=user.email, action="BOOK", entity="appointment",
        detail="slot=%s" % slot.id,
    ))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Slot has already been booked"
        ) from None

    db.refresh(appointment)
    doctor = db.get(Doctor, slot.doctor_id)
    log.info("appointment booked", extra={"user": user.email, "event": "appointment.booked"})

    # Fire-and-forget: notification delivery is not on the critical path.
    bus.publish("appointment.booked", {
        "user_id": user.id,
        "patient_name": user.full_name,
        "doctor_name": doctor.name,
        "reference": appointment.reference,
        "start_at": slot.start_at.strftime("%d-%m-%Y %H:%M"),
    })
    return MessageOut(detail="Appointment confirmed", reference=appointment.reference)


@router.get("", response_model=list[AppointmentOut])
def my_appointments(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Appointment history of the authenticated patient."""
    rows = (
        db.query(Appointment)
        .filter(Appointment.patient_id == user.id)
        .order_by(Appointment.created_at.desc())
        .all()
    )
    return [
        AppointmentOut(
            id=a.id, reference=a.reference, doctor_name=a.doctor.name,
            speciality=a.doctor.speciality, start_at=a.slot.start_at,
            status=a.status, reason=a.reason,
        )
        for a in rows
    ]


@router.delete("/{reference}", response_model=MessageOut)
def cancel(reference: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Cancel an appointment and release the slot back to the pool."""
    appointment = (
        db.query(Appointment).filter(Appointment.reference == reference).first()
    )
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appointment.patient_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your appointment")
    if appointment.status == "CANCELLED":
        raise HTTPException(status_code=409, detail="Appointment is already cancelled")

    appointment.status = "CANCELLED"
    appointment.slot.is_booked = False
    db.add(AuditLog(actor=user.email, action="CANCEL", entity="appointment",
                    detail=reference))
    db.commit()

    bus.publish("appointment.cancelled", {
        "user_id": user.id, "reference": reference,
        "doctor_name": appointment.doctor.name,
        "start_at": appointment.slot.start_at.strftime("%d-%m-%Y %H:%M"),
    })
    return MessageOut(detail="Appointment cancelled", reference=reference)
