"""The team, in one place, so the title page, Section 14, the reflections and
the signature block cannot disagree with each other."""

MEMBERS = [
    ("Tharunkumar S",        "192511416", "Team lead · architecture and the booking core"),
    ("A. Lokesh Kumar",      "192524157", "Domain model and database design"),
    ("Prathapaneni Karthik", "192472038", "Authentication and security"),
    ("D. Sam Angel Raj",     "192511157", "Event-driven notification service"),
    ("S. Dharshansrinath",   "192521216", "API design and the patient portal"),
    ("M. Mohammed Farhan",   "192521141", "Testing and quality assurance"),
    ("R. Hemanth",           "192521327", "Containerisation and CI/CD"),
    ("Hari Krishna R S",     "192521130", "Observability and performance engineering"),
]

CONTRIBUTIONS = [
    ("Tharunkumar S", "192511416",
     "Architecture and booking core",
     "Chaired the architecture decisions in Section 4.4; implemented the transactional booking "
     "handler and its concurrency control; owned the modular-monolith decision and the "
     "repository; reviewed every merge",
     "1, 4, 5, 11"),
    ("A. Lokesh Kumar", "192524157",
     "Domain model and database design",
     "Designed the six-table schema and its constraints, including UNIQUE(slot_id) and "
     "uq(doctor_id, start_at); wrote the ORM models, the audit trail and the idempotent seed "
     "loader; produced the ER diagram",
     "5.3, 6.1"),
    ("Prathapaneni Karthik", "192472038",
     "Authentication and security",
     "Implemented PBKDF2-SHA256 password storage and HS256 JWT issue and verification on the "
     "standard library; the role guard, the sliding-window rate limiter and the constant-time "
     "comparisons; ran the cryptographic benchmark",
     "5.6, 6.2, 6.3, 10.3"),
    ("D. Sam Angel Raj", "192511157",
     "Event-driven notification service",
     "Built the publish/subscribe event bus and its worker pool; wrote the notification "
     "subscriber and the injectable session factory that lets background workers hold their own "
     "database session",
     "4.4, 5.5, 7.3"),
    ("S. Dharshansrinath", "192521216",
     "API design and patient portal",
     "Designed the versioned REST contract and the Pydantic schemas that generate it; chose the "
     "status-code semantics; built the single-page patient portal and the screenshot automation",
     "5.4, 7.2, 9.1"),
    ("M. Mohammed Farhan", "192521141",
     "Testing and quality assurance",
     "Wrote the 25-case test suite including the ten-thread booking race; diagnosed and fixed the "
     "fixture defect described in Section 8.2; configured coverage measurement and the test "
     "traceability matrix",
     "8, 10.4"),
    ("R. Hemanth", "192521327",
     "Containerisation and CI/CD",
     "Wrote the multi-stage non-root Dockerfile and compose file; built the four-stage GitHub "
     "Actions pipeline; resolved the two pipeline failures recorded in Section 9.6 and set the "
     "project lint policy",
     "4.5, 7.4, 9.5, 9.6"),
    ("Hari Krishna R S", "192521130",
     "Observability and performance",
     "Implemented the Prometheus registry, structured JSON logging and the health and readiness "
     "probes; wrote the load-test harness, found the IPv6 measurement artefact and produced the "
     "performance charts",
     "7.3, 9.4, 10.1, 10.2"),
]
