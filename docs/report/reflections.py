"""Section 16 — one independently written reflection page per team member.

Each covers the same five prompts (decisions, challenges, learning, SDG,
course outcomes) but from the part of the system that person actually owned,
so no two pages tell the same story.
"""
from docbuild import h1, h2, para
from docx.shared import Pt

# (name, register number, role, [five paragraphs])
REFLECTIONS = [

# ---------------------------------------------------------------- 1
("Tharunkumar S", "192511416", "Team lead · architecture and the booking core", [

 ("**Design and development decisions I contributed to.** The decision I argued for hardest, and "
  "the one I got wrong first, was how to stop two patients booking the same slot. My first "
  "implementation read the slot, checked `is_booked`, then wrote the appointment. It looked "
  "obviously correct to me and it passed the test I had written for it. What I had actually "
  "written was a check-then-act race: nothing prevents a second request reading the same row "
  "between my check and my write. The fix was to stop treating it as an application problem and "
  "put a `UNIQUE` constraint on `appointments.slot_id`, so the database refuses the second write "
  "no matter what any code does. The other decision I owned was rejecting microservices. With "
  "four modules and eight of us, we would have paid for network hops, distributed transactions "
  "and four pipelines and bought nothing, so we built a modular monolith with real boundaries "
  "that can be split later."),

 ("**Challenges I faced.** Leading eight people on one codebase was harder than the code. Early "
  "on we had two members editing the same router and losing each other's work, so we moved to "
  "short-lived feature branches with a review before merge, and the pipeline as the gate. The "
  "technical low point was realising that our concurrency test had been passing for the wrong "
  "reason — the fixture shared one database session across all ten threads, so they were never "
  "truly concurrent. My first instinct when the corrected fixture failed was to make the error go "
  "away. Talking it through with Farhan, we realised the failure was the point: the test had "
  "finally become capable of detecting the bug it existed to catch."),

 ("**What I learned.** Put invariants where they cannot be bypassed. A rule enforced by the "
  "storage engine survives every future refactor; a rule enforced by a comment does not. I now "
  "think of the application-level check as an optimisation and the constraint as the guarantee, "
  "which is a distinction I did not have language for before this assignment. I also learned that "
  "an architecture decision is only defensible if you can name what you rejected and why, which "
  "is why Section 11 is written the way it is."),

 ("**SDG connection.** The work relates most directly to **SDG 3, Good Health and Well-being**. "
  "Removing the telephone queue between a patient and an appointment lowers a real barrier to "
  "timely care, and eliminating double bookings prevents a consultation slot being wasted on a "
  "scheduling error while another patient waits. There is a secondary connection to **SDG 9**, "
  "because an API-first, containerised service is the kind of digital infrastructure a public "
  "health system can actually maintain and extend."),

 ("**Course outcome attainment.** **CO1 and CO2** were met by moving from a plain-language problem "
  "statement to numbered requirements and then to an architecture chosen against explicit "
  "alternatives. **CO3** was met by implementing and containerising the system so the design "
  "became something that runs. **CO4** was met through the test suite and the load testing that "
  "turned \"it feels fast\" into figures I can defend. **CO5** was met by comparing architectural "
  "alternatives honestly and documenting the limitations of what we built."),
]),

# ---------------------------------------------------------------- 2
("A. Lokesh Kumar", "192524157", "Domain model and database design", [

 ("**Design and development decisions I contributed to.** I owned the six-table schema. The "
  "decision I am most pleased with is that three of our constraints do real work rather than just "
  "describing data: `users.email` is unique so an identity cannot be duplicated, "
  "`slots(doctor_id, start_at)` is unique so a calendar cannot contain the same moment twice, and "
  "`appointments.slot_id` is unique so a slot cannot be sold twice. I also argued for the "
  "append-only `audit_log` table being written inside the same transaction as the action it "
  "records, because a trail written afterwards can silently diverge from what actually happened."),

 ("**Challenges I faced.** My first schema had `is_booked` on the slot as the only record that a "
  "slot was taken, with the appointment merely referencing it. It seemed tidy and it was wrong: "
  "it stores the same fact in two places, so the two can disagree, and it gives the database "
  "nothing to enforce. Reworking it so the appointment row itself is the unique claim on the slot "
  "took an afternoon and made the booking handler simpler rather than more complex, which "
  "surprised me. The second challenge was the seed loader — my first version created duplicate "
  "doctors every restart until I made it idempotent by returning early when doctors already "
  "exist."),

 ("**What I learned.** A schema is not passive storage, it is where the business rules live. I "
  "used to think of constraints as a tidiness exercise and validation as the real work; I now "
  "think the opposite, because application validation is advisory and a constraint is not. I also "
  "learned to be careful about storing a fact twice: `slot.is_booked` is still there as an index "
  "for fast filtering, but it is derived, and the appointment row is the truth."),

 ("**SDG connection.** **SDG 3, Good Health and Well-being** is the direct link, since the "
  "integrity rules I wrote are what stop a patient turning up to a consultation that was given "
  "away. I would also claim **SDG 12, Responsible Consumption**: an indexed query that returns in "
  "milliseconds consumes far less energy per booking than a full scan, and index design is a "
  "sustainability decision as much as a performance one."),

 ("**Course outcome attainment.** **CO1 and CO2** were met by translating the functional "
  "requirements in Section 3.1 into an entity model that satisfies them. **CO3** was met by "
  "implementing that model in SQLAlchemy and producing the ER diagram in Figure 3. **CO4** was met "
  "by verifying the constraints under a concurrent test rather than assuming them. **CO5** was met "
  "through the data-store comparison in Section 11.3, including why a document store was the "
  "wrong choice for an invariant that spans related rows."),
]),

# ---------------------------------------------------------------- 3
("Prathapaneni Karthik", "192472038", "Authentication and security", [

 ("**Design and development decisions I contributed to.** I implemented password storage and "
  "sessions on the Python standard library rather than pulling in a framework, so that I "
  "understood every line rather than trusting a default. Passwords are PBKDF2-HMAC-SHA256 with a "
  "16-byte per-user salt at 600 000 iterations, verified with `hmac.compare_digest` so the "
  "comparison is constant time. Sessions are stateless HS256 JWTs, which is what lets the API "
  "tier scale horizontally with no shared session store. The subtler decision was in the login "
  "handler: when the e-mail does not exist we still verify a dummy hash, so response time does not "
  "reveal which addresses are registered."),

 ("**Challenges I faced.** My benchmark said a single password hash costs about 252 milliseconds, "
  "and my first reaction was that I had chosen the wrong iteration count. I had not — that cost "
  "is the whole point, because it is what makes an offline attack on a stolen database "
  "impractical. The real lesson was where that cost is allowed to appear. Paying 252 ms once at "
  "login is fine; paying it per request would cap the system at about four requests per second. "
  "That is the argument for token-based sessions, and Figure 9 is the chart I made to prove it to "
  "the rest of the team. A smaller challenge was error handling: I originally returned different "
  "messages for a malformed token and an expired one, which is a small information leak. They are "
  "now chained with `from None` and answer identically."),

 ("**What I learned.** Security is a set of measured trade-offs, not a checklist. Before this I "
  "would have said \"use strong hashing\" and stopped; now I can say what 600 000 rounds costs in "
  "milliseconds, why that number is chosen, and where in the request path it is affordable. I "
  "also learned that a timing difference is a channel — the dummy-hash path in the login handler "
  "exists only because of that."),

 ("**SDG connection.** **SDG 3, Good Health and Well-being** depends on patients trusting the "
  "system enough to use it, and appointment data is medical data by implication: knowing that "
  "someone booked an oncologist reveals something even with no diagnosis stored. The access "
  "control and audit trail I worked on support **SDG 16** as well, in the narrow sense of "
  "accountable institutions — every privileged action is attributable to a principal."),

 ("**Course outcome attainment.** **CO1 and CO2** were met by turning the security "
  "non-functional requirements into a concrete design. **CO3** was met by implementing it. **CO4** "
  "was met through the nine authentication test cases, including proving that a tampered "
  "signature and an expired token are both rejected. **CO5** was met by evaluating alternatives "
  "such as server-side sessions and RS256, and by writing up the privacy and ethics implications "
  "in Section 12."),
]),

# ---------------------------------------------------------------- 4
("D. Sam Angel Raj", "192511157", "Event-driven notification service", [

 ("**Design and development decisions I contributed to.** I built the event bus and the "
  "notification subscriber. The decision that shaped my part of the system is that booking does "
  "not call the notification service; it publishes an `appointment.booked` event and returns "
  "immediately. Delivery happens on a background worker pool. I deliberately gave the bus the "
  "same shape of interface a real broker has — `subscribe`, `publish`, topics — so that replacing "
  "it with RabbitMQ later changes my file and nothing that calls it."),

 ("**Challenges I faced.** My subscriber ran on a worker thread and reused the request-scoped "
  "database session, which failed intermittently and confusingly. The session belongs to the "
  "request that opened it, and by the time my handler ran that request had often finished. The "
  "fix was to route background work through a `session_scope()` factory so each worker opens its "
  "own session, which also gave the test suite a single place to redirect those workers at a "
  "throw-away database. The second challenge was proving that the design does what I claim: an "
  "assertion cannot easily show that something happened *after* the response. In the end the "
  "evidence is the timestamped log sequence in Console 6, where the booking is logged, the event "
  "is published, and only then is the notification queued."),

 ("**What I learned.** Moving work off the request path is a design decision, not an "
  "optimisation, and the difference matters. If I had made the notification call fast instead of "
  "asynchronous, the system would still fail whenever the notification channel was down. "
  "Asynchrony changes the failure mode, not just the latency. I also learned that thread "
  "ownership of resources is something to design explicitly rather than discover through "
  "intermittent bugs."),

 ("**SDG connection.** **SDG 3, Good Health and Well-being**: a confirmation that reliably "
  "reaches a patient reduces missed appointments, and a missed appointment is a wasted clinical "
  "slot as well as delayed care for that person. The design also touches **SDG 9**, since "
  "decoupling services through events is what makes the platform extensible without rewriting "
  "the parts that already work."),

 ("**Course outcome attainment.** **CO1 and CO2** were met by identifying responsiveness as a "
  "non-functional requirement and choosing an architectural style that satisfies it. **CO3** was "
  "met by implementing the bus and subscriber. **CO4** was met by TC-19, which proves the event "
  "is published and the notification arrives afterwards. **CO5** was met by comparing an "
  "in-process bus against RabbitMQ and Kafka in Section 11.3 and being honest in Section 13.2 "
  "that our version loses undelivered events if the process dies."),
]),

# ---------------------------------------------------------------- 5
("S. Dharshansrinath", "192521216", "API design and the patient portal", [

 ("**Design and development decisions I contributed to.** I designed the REST contract and built "
  "the patient portal. The decision I would defend most strongly is API-first: every capability "
  "is an HTTP endpoint described by an OpenAPI document that FastAPI generates from the same "
  "Pydantic models it validates with, so the documentation cannot drift from the implementation. "
  "The alternative — a server-rendered application — would have been quicker and would have "
  "recreated exactly the integration problem the organisation complained about. I also spent "
  "longer than expected choosing status codes: 409 for a taken slot rather than a generic 400, "
  "because 409 tells the client something actionable."),

 ("**Challenges I faced.** My first version of the portal hid booked slots in JavaScript after "
  "fetching everything. It looked identical to the user and was wrong in two ways: it sends data "
  "the caller should not have, and it means the server is not the authority on availability. "
  "Moving the filter into the query was a small change that made me think differently about where "
  "decisions belong. The other challenge was error handling in the client — I originally swallowed "
  "failed requests silently, so a 409 looked like nothing happening. The conflict path in "
  "Screenshot 6 exists because we decided every failure must be visible to the patient."),

 ("**What I learned.** A published contract is a design artefact, not documentation you write "
  "afterwards. Because the OpenAPI document is generated, adding a mobile client later needs no "
  "backend work at all, and that property came free from a decision made in week one. I also "
  "learned that the client should never be the place a rule is enforced, only the place it is "
  "displayed."),

 ("**SDG connection.** **SDG 10, Reduced Inequalities** is the one I thought about most. Slots "
  "are allocated strictly first-come-first-served with no hidden prioritisation, and the "
  "interface is plain semantic HTML that works on a low-cost phone, because a booking system that "
  "only works well on an expensive device quietly rations care by income. **SDG 3** follows from "
  "making the booking path short enough that people complete it."),

 ("**Course outcome attainment.** **CO1 and CO2** were met by deriving the endpoint set from the "
  "functional requirements in Section 3.1. **CO3** was met by implementing both the contract and "
  "the client that consumes it. **CO4** was met by TC-25, which asserts every route appears in "
  "the published document, and by the screenshot automation that drives the real journey. **CO5** "
  "was met through the interface-style comparison in Section 4.4 and the accessibility discussion "
  "in Section 12.2, including admitting we have not tested with a screen reader."),
]),

# ---------------------------------------------------------------- 6
("M. Mohammed Farhan", "192521141", "Testing and quality assurance", [

 ("**Design and development decisions I contributed to.** I owned the test suite. The decision "
  "that shaped it was to weight it towards integration tests that drive a real HTTP request "
  "against a real database, rather than unit tests with mocks. Unit-testing our booking logic in "
  "isolation would have missed the only bug in it that mattered, because that bug lived in the "
  "interaction between two sessions and a transaction. I also insisted that every failure path "
  "gets a test, not just the happy one, which is why there is a case for each of 401, 403, 404, "
  "409 and 422."),

 ("**Challenges I faced.** TC-16, the ten-thread booking race, is the test I am proudest of and "
  "the one that embarrassed me. My first version spun up ten threads, asserted one success and "
  "nine conflicts, and passed immediately. That should have been suspicious and it was: the "
  "fixture handed every thread the *same* SQLAlchemy session, so they were never concurrent at "
  "the database level. When I made the fixture open a session per request, exactly as uvicorn "
  "does in production, it failed loudly with a session-state error. That failure was the useful "
  "result. Moving to a file-backed SQLite database so ten real threads open ten real connections "
  "made the test pass for the right reason. I also had to correct our coverage figure: my first "
  "number, 96%, was counting the test files themselves, and restricting measurement to the "
  "application package gives the honest 95%."),

 ("**What I learned.** A green test proves nothing until you have watched it go red for the "
  "reason it exists to catch. I now deliberately break the mechanism a test guards and confirm "
  "the test notices — removing the `UNIQUE` constraint makes TC-16 report multiple successes, "
  "which is exactly what it should do. I also learned to distrust a metric I have not checked the "
  "scope of."),

 ("**SDG connection.** **SDG 3, Good Health and Well-being**: in a healthcare system a defect is "
  "not an inconvenience, it is a patient who arrives for an appointment that no longer exists. "
  "The tests are what let us change the system without gambling with that. There is a link to "
  "**SDG 9** as well, since automated verification is what makes infrastructure resilient rather "
  "than merely working on the day it was built."),

 ("**Course outcome attainment.** **CO1 and CO2** were met by tracing every functional "
  "requirement to a test case in Section 3.1. **CO3** was met by testing the implementation as a "
  "running system rather than as isolated functions. **CO4** is the outcome I engaged with most: "
  "25 cases covering functional correctness, security, reliability and concurrency, with expected "
  "and actual results recorded in Section 8. **CO5** was met by evaluating what the suite does "
  "not cover and saying so in Section 13.2."),
]),

# ---------------------------------------------------------------- 7
("R. Hemanth", "192521327", "Containerisation and CI/CD", [

 ("**Design and development decisions I contributed to.** I built the container image and the "
  "delivery pipeline. The image is a two-stage build so the toolchain used to install "
  "dependencies never ships, and the runtime stage creates an unprivileged user (uid 10001) and "
  "switches to it before the application executes. The pipeline is four stages — static analysis, "
  "tests, image build with a smoke test, then a gated staging deploy — and each stage gates the "
  "next. I pushed for the pipeline to exist in week one rather than at the end, which the team "
  "was not initially convinced by."),

 ("**Challenges I faced.** Both of the failures in Section 9.6 were mine. The first push failed "
  "static analysis because ruff flagged FastAPI's `Depends()` dependency-injection idiom under "
  "rule B008. My instinct was to add a blanket ignore; instead we wrote a project lint "
  "configuration that documents precisely which two rules are disabled and why, because a "
  "suppressed warning with no explanation is a trap for whoever reads it next. The second failure "
  "was more embarrassing: my staging command was a YAML plain scalar containing an inline `#`, "
  "which truncated the shell line and left an unterminated quote. Neither defect would have been "
  "caught by reading the code, and both were caught in under two minutes by automation. We left "
  "both failures in the run history rather than rewriting it, because a pipeline that has never "
  "failed has never been shown to work."),

 ("**What I learned.** A pipeline is a gate, not a report. Its value is entirely in what it "
  "refuses to let through, which means it has to run on every push and it has to block. I also "
  "learned the practical worth of laptop-and-runner parity: when Docker Desktop refused to start "
  "on one of our machines, the container evidence still existed because the image is built from a "
  "clean checkout on a machine none of us configured."),

 ("**SDG connection.** **SDG 9, Industry, Innovation and Infrastructure** is the direct link — "
  "reproducible deployment is what makes software maintainable by an organisation rather than by "
  "the individuals who wrote it. **SDG 12** applies too: a multi-stage build that discards the "
  "compiler toolchain produces a much smaller image to store and transfer, and that is a real "
  "reduction in storage and bandwidth every time it is pulled."),

 ("**Course outcome attainment.** **CO1 and CO2** were met by treating deployability as a "
  "requirement from the start rather than an afterthought. **CO3** was met by containerising the "
  "system and automating its build. **CO4** is evidenced by the pipeline run in Console 9 and the "
  "container smoke test in Console 10. **CO5** was met through the deployment comparison in "
  "Section 11.3 and by identifying Kubernetes with a metrics-driven autoscaler as the next step "
  "in Section 13.3."),
]),

# ---------------------------------------------------------------- 8
("Hari Krishna R S", "192521130", "Observability and performance engineering", [

 ("**Design and development decisions I contributed to.** I implemented the observability layer: "
  "a Prometheus-compatible metric registry, structured JSON logging, and the liveness and "
  "readiness probes. The distinction between `/health` and `/ready` is the decision I would "
  "defend: a process that is alive but cannot reach its database looks identical to a healthy one "
  "unless you actually query the dependency, so `/ready` executes `SELECT 1`. I also keyed "
  "metrics on the route template rather than the raw URL, so `/doctors/6/slots` and "
  "`/doctors/7/slots` share one series instead of creating one each, which would have made the "
  "metric store grow without bound."),

 ("**Challenges I faced.** My first load test reported 2 050 milliseconds for every scenario, at "
  "every level of concurrency. I nearly published it. A flat number that does not move when you "
  "change the load is not a performance result, it is a constant, and that is what made me look "
  "again. On Windows, `localhost` resolves to the IPv6 address `::1` first, and uvicorn was bound "
  "to IPv4 only, so every connection spent about two seconds failing over before succeeding. "
  "Addressing the server as `127.0.0.1` and pooling connections, as a real browser does, gave the "
  "true figures — around 1.5 ms. The whole of Section 10 would have been wrong, and confidently "
  "wrong, if I had trusted the first run."),

 ("**What I learned.** Be suspicious of measurements that are too tidy. A latency figure that "
  "does not respond to load is telling you about your instrument, not your system. I also learned "
  "to report percentiles rather than averages: our p50 at fifty concurrent users is 102 ms while "
  "the p99 is 263 ms, and it is the p99 that a patient actually experiences on a bad request. "
  "Finally, the throughput curve taught me something I had assumed away — throughput peaks at "
  "five workers and then *falls*, which means scaling has to be horizontal rather than pushing "
  "more traffic at one instance."),

 ("**SDG connection.** **SDG 3, Good Health and Well-being** depends on the service being "
  "available when someone needs it, and probes and metrics are what let operators know it is "
  "failing before patients tell them. **SDG 12, Responsible Consumption** is the connection I "
  "measured most directly: an application answering a read in three milliseconds burns far less "
  "energy per booking than one taking three hundred, though I should be honest that I measured "
  "time, not power."),

 ("**Course outcome attainment.** **CO1 and CO2** were met by turning vague goals such as \"the "
  "system should be fast\" into numbered non-functional requirements with targets. **CO3** was met "
  "by implementing the instrumentation. **CO4** is the outcome I engaged with most: the load "
  "harness, the percentile analysis and the validation table in Section 10.4 that checks each "
  "target against a measurement. **CO5** was met by identifying the saturation point and stating "
  "in Section 13.2 that single-machine testing does not establish behaviour at hospital scale."),
]),
]


def section16(doc):
    h1(doc, "16.  Individual Reflections", page_break=True)
    para(doc, "Each member of the team wrote their own reflection independently, covering the "
              "design and development decisions they contributed to, the challenges they met, what "
              "they learned, the SDG connection they see in their part of the work, and how the "
              "assignment contributed to the mapped course outcomes. They appear below, one page "
              "per member, in the order given in Section 14.", space_after=6)

    for index, (name, reg, role, paragraphs) in enumerate(REFLECTIONS):
        if index:
            doc.add_page_break()
        h2(doc, "16.%d  %s — %s" % (index + 1, name, reg))
        para(doc, "Role on the team: %s" % role, italic=True, space_after=5)
        for text in paragraphs:
            para(doc, text)
        doc.add_paragraph()
        para(doc, "Signature: ______________________          Date: ______________",
             justify=False, space_after=2)
