"""Notification service - subscriber of the event bus plus a read API."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import database
from ..database import get_db
from ..deps import current_user
from ..events import bus
from ..models import Notification, User
from ..schemas import MessageOut, NotificationOut

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])
log = logging.getLogger("smartcare.notifications")


# --------------------------------------------------------------------------
# event subscribers
# --------------------------------------------------------------------------
def on_appointment_booked(payload: dict) -> None:
    """Persist a confirmation notice. Runs on a background worker thread and
    therefore opens its own database session."""
    with database.session_scope() as db:
        db.add(Notification(
            user_id=payload["user_id"],
            channel="in-app",
            subject="Appointment %s confirmed" % payload["reference"],
            body=("Dear %(patient_name)s, your appointment with %(doctor_name)s "
                  "on %(start_at)s is confirmed. Reference: %(reference)s. "
                  "Please arrive 15 minutes early." % payload),
        ))
        db.commit()
    log.info("confirmation queued", extra={"event": "notification.sent"})


def on_appointment_cancelled(payload: dict) -> None:
    with database.session_scope() as db:
        db.add(Notification(
            user_id=payload["user_id"],
            channel="in-app",
            subject="Appointment %s cancelled" % payload["reference"],
            body=("Your appointment with %(doctor_name)s on %(start_at)s has been "
                  "cancelled. The slot is now available for other patients."
                  % payload),
        ))
        db.commit()


bus.subscribe("appointment.booked", on_appointment_booked)
bus.subscribe("appointment.cancelled", on_appointment_cancelled)


# --------------------------------------------------------------------------
# read API
# --------------------------------------------------------------------------
@router.get("", response_model=list[NotificationOut])
def my_notifications(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Latest notifications for the authenticated user."""
    return (
        db.query(Notification)
        .filter(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )


@router.post("/{notification_id}/read", response_model=MessageOut)
def mark_read(notification_id: int, db: Session = Depends(get_db),
              user: User = Depends(current_user)):
    note = db.get(Notification, notification_id)
    if note is None or note.user_id != user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    note.is_read = True
    db.commit()
    return MessageOut(detail="Marked as read")
