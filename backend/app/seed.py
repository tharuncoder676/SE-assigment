"""Idempotent demo-data loader.

Populates the doctor directory and generates a rolling seven-day slot
calendar so that a freshly started container is immediately demonstrable.
Re-running it is safe: it returns early once doctors exist.
"""
import datetime as dt
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from .config import settings
from .models import Doctor, Slot, User
from .security import hash_password

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
log = logging.getLogger("smartcare.seed")

DOCTORS = [
    ("Dr. Anitha Raman", "Cardiology", "Heart Centre", "MD, DM (Cardiology)", 800),
    ("Dr. Vikram Shetty", "Orthopaedics", "Bone & Joint", "MS (Ortho)", 700),
    ("Dr. Fatima Noor", "Paediatrics", "Child Care", "MD (Paediatrics)", 600),
    ("Dr. Rajesh Kumar", "General Medicine", "OPD Block A", "MBBS, MD", 400),
    ("Dr. Meera Krishnan", "Dermatology", "Skin Clinic", "MD (DVL)", 650),
    ("Dr. Samuel George", "Neurology", "Neuro Sciences", "DM (Neurology)", 950),
    ("Dr. Priya Balan", "Gynaecology", "Women's Health", "MS (OBG)", 750),
    ("Dr. Arun Prakash", "ENT", "OPD Block B", "MS (ENT)", 500),
]

WORKING_HOURS = [(9, 12), (15, 18)]   # morning and evening consulting blocks


def seed_database(db: Session, days: int = 7) -> None:
    if db.query(Doctor).count():
        return

    for name, speciality, department, qualification, fee in DOCTORS:
        db.add(Doctor(
            name=name, speciality=speciality, department=department,
            qualification=qualification, consultation_fee=fee,
        ))
    db.flush()

    today = dt.datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    step = dt.timedelta(minutes=settings.SLOT_MINUTES)
    created = 0
    for doctor in db.query(Doctor).all():
        for day in range(days):
            date = (today + dt.timedelta(days=day)).replace(hour=0)
            for start_hour, end_hour in WORKING_HOURS:
                cursor = date.replace(hour=start_hour)
                while cursor < date.replace(hour=end_hour):
                    db.add(Slot(doctor_id=doctor.id, start_at=cursor,
                                end_at=cursor + step))
                    cursor += step
                    created += 1

    db.add(User(
        full_name="System Administrator",
        email="admin@smartcare.local",
        password_hash=hash_password("Admin@12345"),
        role="admin",
    ))
    db.commit()
    log.info("seeded %d doctors and %d slots" % (len(DOCTORS), created))
