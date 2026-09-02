# SmartCare — Smart Healthcare Appointment and Patient Service Platform

A containerised, API-first appointment platform for a multi-specialty
healthcare organisation. Built for the CSA10 Software Engineering assignment
as a demonstration of the full software engineering life cycle: requirements,
architecture, implementation, automated testing, containerisation, CI/CD,
monitoring and logging.

## Architecture at a glance

| Layer | Technology | Responsibility |
|---|---|---|
| Client | HTML5 / CSS3 / vanilla ES6 | Single-page patient portal |
| API gateway | FastAPI (ASGI) | Routing, validation, authentication, observability middleware |
| Services | Auth · Doctors · Appointments · Notifications | Independently routed modules, ready to split into microservices |
| Messaging | In-process event bus (`appointment.booked`, `appointment.cancelled`) | Asynchronous, non-blocking notification delivery |
| Data | SQLAlchemy 2.0 ORM over SQLite (PostgreSQL-ready) | Persistence, uniqueness constraints, audit trail |
| Runtime | Docker multi-stage image, non-root user | Reproducible deployment |
| CI/CD | GitHub Actions — lint → test → build → deploy | Automated quality gate |
| Observability | JSON structured logs, `/health`, `/ready`, `/metrics` | Operability |

## Running locally

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open <http://localhost:8000> for the portal and <http://localhost:8000/docs>
for the interactive OpenAPI documentation.

VS Code users can press F5 instead: `.vscode/launch.json` defines run
configurations for the API with reload, the test suite, a single test file and
the load-test harness.

## Running the tests

```bash
cd backend
python -m pytest
```

## Running in Docker

```bash
docker compose up --build -d
docker compose ps
curl http://localhost:8000/health
```

## Seeded demo data

* 8 doctors across 8 specialities
* A rolling 7-day calendar of 30-minute slots (morning 09:00–12:00, evening 15:00–18:00)
* Administrator account `admin@smartcare.local` / `Admin@12345`

## API summary

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/api/v1/auth/register` | — | Create a patient account |
| POST | `/api/v1/auth/login` | — | Obtain a JWT (rate limited) |
| GET | `/api/v1/auth/me` | Bearer | Current profile |
| GET | `/api/v1/doctors` | — | Directory, filter by speciality or name |
| GET | `/api/v1/doctors/{id}/slots` | — | Free future slots |
| POST | `/api/v1/appointments` | Bearer | Book a slot (409 on conflict) |
| GET | `/api/v1/appointments` | Bearer | Appointment history |
| DELETE | `/api/v1/appointments/{ref}` | Bearer | Cancel and release the slot |
| GET | `/api/v1/notifications` | Bearer | Event-generated notices |
| GET | `/api/v1/admin/stats` | Bearer (admin) | Operational counters |
| GET | `/health` `/ready` `/metrics` | — | Probes and Prometheus metrics |

## Security notes

* Passwords: PBKDF2-HMAC-SHA256, 600 000 iterations, 16-byte per-user salt,
  constant-time verification.
* Sessions: stateless HS256 JWTs with `exp` and `iss` claims.
* Login endpoint protected by a sliding-window rate limiter.
* Baseline security headers on every response; append-only audit log for all
  authentication and appointment actions.

## Licence

MIT — prepared for academic submission.
