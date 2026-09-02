"""SmartCare application entry point.

Composition root: creates the FastAPI application, installs the cross-cutting
middleware (correlation id, structured access log, metrics, security headers),
mounts the four service routers and serves the single-page frontend.
"""
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import Base, SessionLocal, engine
from .logging_conf import configure_logging
from .metrics import metrics
from .routers import appointments, auth, doctors, notifications, ops
from .seed import FRONTEND_DIR, seed_database

configure_logging()
log = logging.getLogger("smartcare.http")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Schema creation and demo-data seeding on start-up."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_database(db)
    log.info("application started", extra={"event": "startup"})
    yield
    log.info("application stopped", extra={"event": "shutdown"})


DESCRIPTION = """
API-first backend for the **Smart Healthcare Appointment and Patient Service
Platform**.

Four logical services are exposed behind one gateway process:

* **Authentication** - registration, login, JWT issue and profile
* **Doctors** - directory, specialities and slot availability
* **Appointments** - transactional booking, history and cancellation
* **Notifications** - event-driven confirmations delivered asynchronously

Operational endpoints `/health`, `/ready` and `/metrics` support container
orchestration and Prometheus scraping.
"""

app = FastAPI(
    title=settings.APP_NAME,
    description=DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan,
    contact={"name": "SmartCare Engineering Team"},
    license_info={"name": "MIT"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    """Attach a correlation id, time the request, record metrics, log one
    structured line and set baseline security headers."""
    request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:12])
    started = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - started

    route = request.scope.get("route")
    path = getattr(route, "path", request.url.path)
    metrics.observe(request.method, path, response.status_code, elapsed)

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"

    log.info(
        "request handled",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": round(elapsed * 1000, 2),
        },
    )
    return response


app.include_router(ops.router)
app.include_router(auth.router)
app.include_router(doctors.router)
app.include_router(appointments.router)
app.include_router(notifications.router)

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))
