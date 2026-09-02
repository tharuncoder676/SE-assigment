"""Sections 5-8: design, algorithms, implementation, test cases."""
from docbuild import (bullets, cap, code, figure, h1, h2, link_para, note, para,
                      table, FIG, SHOT)

REPO = "https://github.com/tharuncoder676/SE-assigment"
BLOB = REPO + "/blob/main/"


# =========================================================== section 5
def section5(doc):
    h1(doc, "5.  Design, Proposed Solution and Methodology", page_break=True)

    h2(doc, "5.1  Architecture")
    para(doc, "Figure 1 on the title page shows the whole system. Four bounded contexts sit "
              "behind one FastAPI process. Requests pass through a middleware chain that assigns "
              "a correlation ID, times the request, records metrics, sets security headers, "
              "validates the body against a schema and verifies the bearer token, in that order. "
              "The booking service publishes to an event bus rather than calling the notification "
              "service, and the persistence tier is reached only through the ORM, which is what "
              "makes the SQLite-to-PostgreSQL move a configuration change.")
    para(doc, "The single most consequential line in the design is not in any diagram: it is the "
              "`UNIQUE` constraint on `appointments.slot_id`. Everything else about booking "
              "correctness follows from putting that rule where the database can enforce it "
              "instead of where application code has to remember to check it.")

    h2(doc, "5.2  Use case model")
    figure(doc, FIG / "fig2.png", 14.4,
           "Figure 2 — Use case model. The patient is the primary actor. The dashed «triggers» "
           "relationship records that booking raises an event which the notification service, a "
           "secondary actor, consumes asynchronously.")

    h2(doc, "5.3  Database design")
    para(doc, "Six tables. Three of them carry a constraint that is doing real work rather than "
              "just describing data: `users.email` is unique so an identity cannot be duplicated, "
              "`slots(doctor_id, start_at)` is unique so a calendar cannot contain the same "
              "moment twice, and `appointments.slot_id` is unique so a slot cannot be sold twice.")
    figure(doc, FIG / "fig3.png", 16.0,
           "Figure 3 — Entity relationship diagram. The UNIQUE constraint on appointments.slot_id "
           "(shown in red) is the mechanism that makes double booking impossible.")

    h2(doc, "5.4  API design")
    para(doc, "The API is versioned under `/api/v1` and described by an OpenAPI document that "
              "FastAPI generates from the Pydantic schemas, so the documentation cannot drift "
              "away from the implementation. Status codes are chosen to be meaningful to a "
              "client: 409 means \"someone else got there first, choose another slot\", which is "
              "actionable, whereas a generic 400 would not be.")
    table(doc,
          ["Method & path", "Auth", "Purpose", "Success", "Failure modes"],
          [["POST `/api/v1/auth/register`", "—", "Create a patient account and issue a token", "201", "409 duplicate, 422 invalid"],
           ["POST `/api/v1/auth/login`", "—", "Exchange credentials for a JWT", "200", "401 bad credentials, 429 throttled"],
           ["GET `/api/v1/auth/me`", "Bearer", "Profile of the calling principal", "200", "401 missing or invalid token"],
           ["GET `/api/v1/doctors`", "—", "Directory, filtered by speciality or name", "200", "—"],
           ["GET `/api/v1/doctors/{id}/slots`", "—", "Future unbooked slots for one doctor", "200", "404 unknown doctor"],
           ["POST `/api/v1/appointments`", "Bearer", "Book a slot", "201", "401, 404 unknown slot, 409 taken"],
           ["GET `/api/v1/appointments`", "Bearer", "The caller's own appointment history", "200", "401"],
           ["DELETE `/api/v1/appointments/{ref}`", "Bearer", "Cancel and release the slot", "200", "403 not yours, 404, 409 already cancelled"],
           ["GET `/api/v1/notifications`", "Bearer", "Event-generated notices for the caller", "200", "401"],
           ["GET `/api/v1/admin/stats`", "Admin", "Operational counters", "200", "401, 403 wrong role"],
           ["GET `/health`  `/ready`  `/metrics`", "—", "Liveness, readiness, Prometheus scrape", "200", "—"]],
          widths=[27, 8, 30, 8, 27], size=8.2, align_center=(1, 3))

    h2(doc, "5.5  Booking sequence")
    figure(doc, FIG / "fig4.png", 16.2,
           "Figure 4 — Sequence of a successful booking. Dashed arrows are returns. The green "
           "arrows leave the request path: the patient's 201 response is sent before the "
           "notification row is written.")

    h2(doc, "5.6  Security design")
    para(doc, "Passwords are stored as PBKDF2-HMAC-SHA256 with a 16-byte per-user salt and "
              "600 000 iterations, the figure OWASP currently recommends, and verified with a "
              "constant-time comparison. Sessions are stateless HS256 JSON Web Tokens carrying "
              "`sub`, `role`, `iat`, `exp` and `iss`, which is what allows the API tier to be "
              "scaled horizontally without a shared session store. Login is protected by a "
              "sliding-window rate limiter, and the login handler verifies a dummy hash when the "
              "account does not exist so that response time does not reveal which e-mail "
              "addresses are registered. Authorisation is a dependency-injected role guard, and "
              "authentication failures are chained with `from None` so the client is never told "
              "whether a token was malformed, forged or merely expired.")


# =========================================================== section 6
def section6(doc):
    h1(doc, "6.  Algorithm, Pseudocode and Flowchart", page_break=True)

    h2(doc, "6.1  The booking algorithm")
    para(doc, "This is the only genuinely difficult algorithm in the system, and the difficulty "
              "is not arithmetic. It is that two requests can arrive for the same slot at the "
              "same instant. The pseudocode below is the design; the flowchart in Figure 5 is the "
              "same thing with every failure path made explicit.")
    code(doc, """
ALGORITHM BookAppointment(slot_id, reason, bearer_token)

 1  claims <- VerifyJWT(bearer_token)                  // signature, exp, issuer
 2  IF claims is invalid THEN RETURN 401 Unauthorized
 3  patient <- LookupUser(claims.sub)
 4
 5  BEGIN TRANSACTION
 6      slot <- SELECT * FROM slots
 7               WHERE id = slot_id FOR UPDATE          // pessimistic row lock
 8      IF slot IS NULL THEN
 9          ROLLBACK ; RETURN 404 Not Found
10      IF slot.is_booked THEN
11          ROLLBACK ; RETURN 409 Conflict              // fast path for the common case
12
13      reference <- "SC-" + UPPER(RandomHex(4))
14      INSERT INTO appointments (reference, patient_id, doctor_id, slot_id,
15                                reason, status) VALUES (..., 'CONFIRMED')
16      UPDATE slots SET is_booked = TRUE WHERE id = slot_id
17      INSERT INTO audit_log (actor, action, entity, detail)
18  TRY
19      COMMIT                                          // UNIQUE(slot_id) is the real guard
20  CATCH IntegrityError
21      ROLLBACK ; RETURN 409 Conflict                  // lost the race at commit time
22
23  Publish("appointment.booked", {...})                // queued, NOT awaited
24  RETURN 201 Created with reference
""", caption="Listing 1 — Booking algorithm. Lines 10-11 and 19-21 are two different defences "
             "against the same hazard; the second is the one that is actually sufficient.")

    para(doc, "Lines 10 and 11 look like they solve the concurrency problem, and they do not. "
              "They are an optimisation: they let the overwhelmingly common case (the slot is "
              "visibly taken) fail cheaply without doing any write work. The guarantee comes from "
              "line 19. If two transactions both pass the check at line 10, exactly one of them "
              "will succeed at `COMMIT`, because the database will not allow two rows with the "
              "same `slot_id`. The other receives an `IntegrityError` and is converted into the "
              "same 409 the caller would have got anyway.")

    figure(doc, FIG / "fig5.png", 11.4,
           "Figure 5 — Booking flowchart. Every terminal state is an explicit HTTP status code, "
           "and every one of them is asserted by a test in Section 8.")

    h2(doc, "6.2  Password storage and token verification")
    code(doc, """
ALGORITHM HashPassword(password)
 1  salt   <- CSPRNG(16 bytes)                          // unique per user
 2  digest <- PBKDF2-HMAC-SHA256(password, salt, iterations = 600 000)
 3  RETURN "pbkdf2_sha256$" + iterations + "$" + b64(salt) + "$" + b64(digest)

ALGORITHM VerifyPassword(password, stored)
 1  algorithm, iterations, salt, expected <- Split(stored, "$")
 2  digest <- PBKDF2-HMAC-SHA256(password, salt, iterations)
 3  RETURN ConstantTimeEquals(digest, expected)         // never a plain == comparison

ALGORITHM VerifyToken(token)
 1  header, claims, signature <- Split(token, ".")      // reject if not exactly 3 parts
 2  expected <- HMAC-SHA256(secret, header + "." + claims)
 3  IF NOT ConstantTimeEquals(expected, signature) THEN RAISE   // forged
 4  IF claims.exp < Now() THEN RAISE                            // expired
 5  RETURN claims
""", caption="Listing 2 — Security primitives. The salt at line 1 is why two users with the same "
             "password have different stored values; the constant-time comparison is why an "
             "attacker cannot learn the digest one byte at a time.")

    h2(doc, "6.3  Sliding-window rate limiting")
    code(doc, """
ALGORITHM Allow(key)                                    // one key per client address
 1  now <- MonotonicClock()
 2  ACQUIRE lock
 3      WHILE hits[key] not empty AND now - hits[key].front > window
 4          hits[key].pop_front()                       // evict events that aged out
 5      IF Length(hits[key]) >= max_events THEN
 6          RETURN False                                // caller responds 429
 7      hits[key].push_back(now)
 8      RETURN True
""", caption="Listing 3 — Sliding-window limiter. A monotonic clock is used deliberately, so that "
             "a system clock adjustment cannot widen or collapse the window.")


# =========================================================== section 7
def section7(doc):
    h1(doc, "7.  Implementation, Source Code and Tools Used")

    h2(doc, "7.1  Tools")
    table(doc,
          ["Area", "Tool and version", "Why this one"],
          [["Language", "Python 3.12", "Modern typing, and the standard library covers the cryptography we needed"],
           ["API framework", "FastAPI 0.110 on uvicorn", "Generates the OpenAPI document from the same models it validates with"],
           ["Validation", "Pydantic 2.13", "One definition serves as validation, serialisation and documentation"],
           ["ORM", "SQLAlchemy 2.0", "Lets the storage engine change without the query code changing"],
           ["Database", "SQLite (dev/test), PostgreSQL-ready", "Zero setup for reviewers; the ORM keeps the migration path open"],
           ["Frontend", "HTML5, CSS3, vanilla ES6", "No build step, so the UI cannot rot independently of the API"],
           ["Testing", "pytest 8.4, coverage.py", "Fixtures made per-test isolation straightforward"],
           ["Static analysis", "ruff, bandit", "Style and bug patterns; medium-and-above security findings"],
           ["Containers", "Docker, multi-stage build", "Same artefact on a laptop and on the runner"],
           ["CI/CD", "GitHub Actions", "Free, and lives next to the code it gates"],
           ["Observability", "Custom Prometheus registry, JSON logging", "Standard exposition format with no extra dependency"],
           ["Load testing", "Custom httpx harness", "We needed per-request latencies to report percentiles, not just averages"],
           ["Version control", "Git and GitHub", "Protected main branch; the pipeline is the gate"]],
          widths=[15, 25, 60], size=8.3)

    h2(doc, "7.2  Repository layout")
    code(doc, """
SE-assigment/
├── backend/
│   ├── app/
│   │   ├── main.py            FastAPI app, middleware chain, router mounting
│   │   ├── config.py          Environment-driven settings (12-factor)
│   │   ├── database.py        Engine, session factory, request-scoped dependency
│   │   ├── models.py          Six SQLAlchemy models and their constraints
│   │   ├── schemas.py         Pydantic request/response contracts
│   │   ├── security.py        PBKDF2 hashing and HS256 JWTs (standard library only)
│   │   ├── deps.py            Bearer-token extraction and the role guard
│   │   ├── events.py          In-process publish/subscribe bus
│   │   ├── ratelimit.py       Sliding-window limiter
│   │   ├── metrics.py         Prometheus registry (counters + latency histogram)
│   │   ├── logging_conf.py    Structured JSON log formatter
│   │   ├── seed.py            Idempotent demo data loader
│   │   └── routers/           auth · doctors · appointments · notifications · ops
│   └── tests/                 25 tests across four modules
├── frontend/                  index.html · styles.css · app.js
├── docs/                      figures, screenshots, console transcripts, load test
├── .github/workflows/ci.yml   Four-stage pipeline
├── Dockerfile                 Multi-stage, non-root, HEALTHCHECK
└── docker-compose.yml         Local orchestration with a named volume
""", size=7.4, caption="Listing 4 — Repository layout. 58 tracked files.")

    h2(doc, "7.3  Key implementation extracts")
    para(doc, "**The booking handler.** The comment in the docstring is the important part: this "
              "code is safe because of what the database guarantees, not because of what the "
              "function checks.")
    code(doc, """
@router.post("", response_model=MessageOut, status_code=201)
def book(payload: BookingRequest,
         db: Session = Depends(get_db),
         user: User = Depends(current_user)):
    \"\"\"Concurrency safety comes from the database, not from the application:
    the row is re-read with SELECT ... FOR UPDATE semantics inside the
    transaction and Appointment.slot_id carries a UNIQUE index, so if two
    requests race, exactly one commits and the other receives HTTP 409.\"\"\"
    slot = db.get(Slot, payload.slot_id, with_for_update=True)
    if slot is None:
        raise HTTPException(status_code=404, detail="Slot not found")
    if slot.is_booked:
        raise HTTPException(status_code=409, detail="Slot has already been booked")

    appointment = Appointment(reference=_reference(), patient_id=user.id,
                              doctor_id=slot.doctor_id, slot_id=slot.id,
                              reason=payload.reason, status="CONFIRMED")
    slot.is_booked = True
    db.add(appointment)
    db.add(AuditLog(actor=user.email, action="BOOK", entity="appointment",
                    detail="slot=%s" % slot.id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Slot has already been booked"
        ) from None
    ...
    bus.publish("appointment.booked", {...})     # fire and forget
    return MessageOut(detail="Appointment confirmed", reference=appointment.reference)
""", size=7.3, caption="Listing 5 — backend/app/routers/appointments.py")

    para(doc, "**The event bus.** Twenty-odd lines, but they are the reason booking is fast. The "
              "interface is deliberately the same shape as a real broker's, so replacing it with "
              "RabbitMQ or Kafka changes this file and nothing else.")
    code(doc, """
class EventBus:
    def __init__(self, workers: int = 4) -> None:
        self._subscribers = defaultdict(list)
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="event")

    def subscribe(self, topic, handler):
        self._subscribers[topic].append(handler)

    def publish(self, topic, payload, sync=False):
        self.published += 1
        log.info("event published", extra={"event": topic})
        for handler in self._subscribers[topic]:
            if sync:
                self._run(handler, topic, payload)
            else:
                self._pool.submit(self._run, handler, topic, payload)   # returns at once
""", size=7.3, caption="Listing 6 — backend/app/events.py")

    para(doc, "**The observability middleware.** One decorator gives every request a correlation "
              "ID, a latency measurement, a metrics observation, three security headers and "
              "exactly one structured log line.")
    code(doc, """
@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:12])
    started = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - started

    route = request.scope.get("route")
    metrics.observe(request.method, getattr(route, "path", request.url.path),
                    response.status_code, elapsed)

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"

    log.info("request handled", extra={"request_id": request_id, "method": request.method,
             "path": request.url.path, "status": response.status_code,
             "duration_ms": round(elapsed * 1000, 2)})
    return response
""", size=7.3, caption="Listing 7 — backend/app/main.py. Metrics are keyed on the route template, "
                       "not the raw URL, so /doctors/6/slots and /doctors/7/slots share a series "
                       "instead of creating one each.")

    para(doc, "**The container image.** Two stages, so the compiler toolchain used to install "
              "dependencies never ships. The runtime stage creates an unprivileged user and "
              "switches to it before the application is ever executed.")
    code(doc, """
FROM python:3.12-slim AS builder
WORKDIR /install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install/deps -r requirements.txt

FROM python:3.12-slim
RUN useradd --create-home --uid 10001 smartcare      # never run application code as root
WORKDIR /app
COPY --from=builder /install/deps /usr/local
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/
ENV PYTHONUNBUFFERED=1 APP_ENV=production DATABASE_URL=sqlite:////data/smartcare.db
RUN mkdir -p /data && chown -R smartcare:smartcare /app /data
USER smartcare
WORKDIR /app/backend
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
  CMD python -c "import urllib.request,sys; sys.exit(0 if ...status==200 else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
""", size=7.3, caption="Listing 8 — Dockerfile")

    h2(doc, "7.4  Continuous integration and delivery")
    figure(doc, FIG / "fig6.png", 16.4,
           "Figure 6 — The delivery pipeline. It is a gate rather than a report: stage N+1 never "
           "starts unless stage N passed. Section 9 shows a real run, and two real failures.")


# =========================================================== section 8
def section8(doc):
    h1(doc, "8.  Test Cases and Expected / Actual Results", page_break=True)

    h2(doc, "8.1  The suite")
    para(doc, "Twenty-five automated tests run in about two seconds. Every one of them is in the "
              "repository, and every one runs on every push. The \"actual\" column below is not "
              "transcribed by hand; it is the output shown in the pytest screenshot in Section 9.")
    table(doc,
          ["ID", "What it checks", "Expected", "Actual", "P/F"],
          [["TC-01", "Registration returns a three-part JWT and role `patient`", "201, valid token", "201, token verified", "Pass"],
           ["TC-02", "A second registration on the same e-mail is refused", "409 Conflict", "409 Conflict", "Pass"],
           ["TC-03", "A password shorter than 8 characters is rejected by schema validation", "422", "422", "Pass"],
           ["TC-04", "Correct credentials succeed; a wrong password does not", "200 then 401", "200 then 401", "Pass"],
           ["TC-05", "The stored value contains no plaintext and starts `pbkdf2_sha256$`", "No plaintext", "Prefix and salt confirmed", "Pass"],
           ["TC-06", "Two identical passwords produce different stored hashes", "Different digests", "Different, both verify", "Pass"],
           ["TC-07", "A protected route rejects a missing and a forged token", "401 both times", "401 both times", "Pass"],
           ["TC-08", "A tampered signature and an expired token are both rejected", "ValueError raised", "Raised in both cases", "Pass"],
           ["TC-09", "A patient calling an admin endpoint is refused", "403 Forbidden", "403 Forbidden", "Pass"],
           ["TC-10", "Directory listing, speciality filter and name search", "8 doctors; filters correct", "8; Cardiology 1; search hit", "Pass"],
           ["TC-11", "Generated slots are free and well ordered", "`is_booked` false, start < end", "Confirmed", "Pass"],
           ["TC-12", "Slots for a non-existent doctor", "404", "404", "Pass"],
           ["TC-13", "Booking without a token", "401", "401", "Pass"],
           ["TC-14", "A valid booking returns an `SC-` reference and appears in history", "201 + reference", "201, `SC-…`, history correct", "Pass"],
           ["TC-15", "Booking the same slot twice in sequence", "201 then 409", "201 then 409", "Pass"],
           ["TC-16", "**Ten threads race for one slot**", "**Exactly 1 × 201, 9 × 409**", "**1 × 201, 9 × 409**", "Pass"],
           ["TC-17", "Cancelling removes it from the calendar then returns it to the pool", "Slot freed; second cancel 409", "Both confirmed", "Pass"],
           ["TC-18", "Cancelling an unknown reference", "404", "404", "Pass"],
           ["TC-19", "Booking publishes an event and the notification arrives afterwards", "Event count rises; notice appears", "Both observed", "Pass"],
           ["TC-20", "Liveness probe reports version and uptime", "200, status UP", "200, UP, v1.0.0", "Pass"],
           ["TC-21", "Readiness probe actually queries the database", "200, database UP", "200, database UP", "Pass"],
           ["TC-22", "Metrics are valid Prometheus exposition", "Counter and histogram present", "Both present", "Pass"],
           ["TC-23", "Security headers and a correlation ID on every response", "nosniff, DENY, X-Request-ID", "All three present", "Pass"],
           ["TC-24", "The limiter blocks past its threshold and is per-key", "3 allowed, then denied", "Exactly as specified", "Pass"],
           ["TC-25", "The OpenAPI document lists every route", "All paths present", "All present", "Pass"]],
          widths=[6, 42, 21, 24, 7], size=7.9, align_center=(0, 4))

    h2(doc, "8.2  The test that was passing for the wrong reason")
    para(doc, "TC-16 is the test we are proudest of, and it is also the one that embarrassed us. "
              "Our first version spun up ten threads and asserted one success and nine conflicts, "
              "and it passed immediately. That should have been suspicious, and it was: the "
              "fixture handed every thread the *same* SQLAlchemy session, so the threads were "
              "never really concurrent at the database level. When we made the fixture open a "
              "separate session per request, exactly as uvicorn does in production, the test "
              "started failing with `InvalidRequestError: This session is in 'prepared' state`.")
    para(doc, "That failure was the useful result. We changed the fixture to give each request its "
              "own session against a file-backed SQLite database, so that ten real OS threads open "
              "ten real connections. The test then passed for the right reason, and it now "
              "exercises the `UNIQUE` constraint rather than accidentally serialising through one "
              "connection.")
    note(doc, "**The lesson we took from this.** A green test is not evidence until you have seen "
              "it fail for the reason it is supposed to catch. We now deliberately break the "
              "mechanism a test is guarding and check that the test notices. Removing the `UNIQUE` "
              "constraint makes TC-16 report multiple 201s, which is exactly what it should do.")

    h2(doc, "8.3  Coverage")
    para(doc, "Coverage is measured over the application package only. Our first figure was 96%, "
              "which flattered us because it was counting the test files themselves; a "
              "`.coveragerc` restricting measurement to `app` gives the honest number: **605 "
              "statements, 30 missed, 95% covered.** The uncovered lines are defensive branches "
              "such as the readiness handler's database-down path, which we could only exercise "
              "by breaking the database on purpose.")
