"""Doctor directory and availability service."""
import datetime as dt
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Doctor, Slot
from ..schemas import DoctorOut, SlotOut

router = APIRouter(prefix="/api/v1/doctors", tags=["Doctors"])


@router.get("", response_model=List[DoctorOut])
def list_doctors(
    speciality: Optional[str] = Query(default=None, description="Filter by speciality"),
    q: Optional[str] = Query(default=None, description="Free-text search on name"),
    db: Session = Depends(get_db),
):
    """Directory of consulting doctors, optionally filtered."""
    query = db.query(Doctor).filter(Doctor.is_available.is_(True))
    if speciality:
        query = query.filter(Doctor.speciality == speciality)
    if q:
        query = query.filter(Doctor.name.ilike("%%%s%%" % q))
    return query.order_by(Doctor.name).all()


@router.get("/specialities", response_model=List[str])
def specialities(db: Session = Depends(get_db)):
    rows = db.query(Doctor.speciality).distinct().order_by(Doctor.speciality).all()
    return [r[0] for r in rows]


@router.get("/{doctor_id}/slots", response_model=List[SlotOut])
def available_slots(
    doctor_id: int,
    only_free: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    """Future consulting slots for one doctor."""
    if not db.get(Doctor, doctor_id):
        raise HTTPException(status_code=404, detail="Doctor not found")

    query = db.query(Slot).filter(
        Slot.doctor_id == doctor_id,
        Slot.start_at >= dt.datetime.utcnow(),
    )
    if only_free:
        query = query.filter(Slot.is_booked.is_(False))
    return query.order_by(Slot.start_at).limit(60).all()
