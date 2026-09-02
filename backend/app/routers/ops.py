"""Operational endpoints consumed by Docker, Kubernetes and Prometheus."""
import time

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import require_role
from ..events import bus
from ..metrics import metrics
from ..models import Appointment, AuditLog, Doctor, User

router = APIRouter(tags=["Operations"])
STARTED_AT = time.time()


@router.get("/health")
def health():
    """Liveness probe - is the process running?"""
    return {
        "status": "UP",
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.ENV,
        "uptime_seconds": round(time.time() - STARTED_AT, 1),
    }


@router.get("/ready")
def ready(db: Session = Depends(get_db)):
    """Readiness probe - can the process actually serve traffic?"""
    checks = {}
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "UP"
    except Exception as exc:                                # pragma: no cover
        checks["database"] = "DOWN: %s" % exc
    checks["event_bus"] = "UP"
    status = "READY" if all(v == "UP" for v in checks.values()) else "NOT_READY"
    return {"status": status, "checks": checks}


@router.get("/metrics")
def prometheus_metrics():
    """Prometheus text exposition format."""
    return Response(content=metrics.render(), media_type="text/plain; version=0.0.4")


@router.get("/api/v1/admin/stats", tags=["Operations"])
def stats(db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    """Administrative dashboard counters. Admin role required."""
    return {
        "patients": db.query(User).filter(User.role == "patient").count(),
        "doctors": db.query(Doctor).count(),
        "appointments_confirmed": db.query(Appointment)
            .filter(Appointment.status == "CONFIRMED").count(),
        "appointments_cancelled": db.query(Appointment)
            .filter(Appointment.status == "CANCELLED").count(),
        "audit_entries": db.query(AuditLog).count(),
        "events_published": bus.published,
    }
