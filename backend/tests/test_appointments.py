"""TC-10 .. TC-18 - booking, double-booking, cancellation and notifications."""
import threading
import time

from app.events import bus


def test_tc10_doctor_directory_and_filter(client):
    all_doctors = client.get("/api/v1/doctors").json()
    assert len(all_doctors) == 8

    cardiology = client.get("/api/v1/doctors?speciality=Cardiology").json()
    assert len(cardiology) == 1
    assert cardiology[0]["name"] == "Dr. Anitha Raman"

    search = client.get("/api/v1/doctors?q=vikram").json()
    assert search[0]["speciality"] == "Orthopaedics"


def test_tc11_slots_are_generated_and_free(client, free_slot):
    assert free_slot["is_booked"] is False
    assert free_slot["start_at"] < free_slot["end_at"]


def test_tc12_unknown_doctor_returns_404(client):
    assert client.get("/api/v1/doctors/9999/slots").status_code == 404


def test_tc13_booking_requires_authentication(client, free_slot):
    response = client.post("/api/v1/appointments", json={"slot_id": free_slot["id"]})
    assert response.status_code == 401


def test_tc14_successful_booking(client, patient, free_slot):
    response = client.post("/api/v1/appointments", headers=patient, json={
        "slot_id": free_slot["id"], "reason": "Routine cardiac review",
    })
    assert response.status_code == 201
    reference = response.json()["reference"]
    assert reference.startswith("SC-")

    mine = client.get("/api/v1/appointments", headers=patient).json()
    assert mine[0]["reference"] == reference
    assert mine[0]["status"] == "CONFIRMED"
    assert mine[0]["reason"] == "Routine cardiac review"


def test_tc15_double_booking_is_rejected(client, patient, free_slot):
    first = client.post("/api/v1/appointments", headers=patient,
                        json={"slot_id": free_slot["id"]})
    second = client.post("/api/v1/appointments", headers=patient,
                         json={"slot_id": free_slot["id"]})
    assert first.status_code == 201
    assert second.status_code == 409
    assert "already been booked" in second.json()["detail"]


def test_tc16_concurrent_booking_yields_exactly_one_winner(client, patient, free_slot):
    """Ten threads race for the same slot; the unique constraint must allow
    exactly one to win."""
    results = []
    lock = threading.Lock()

    def attempt():
        response = client.post("/api/v1/appointments", headers=patient,
                               json={"slot_id": free_slot["id"]})
        with lock:
            results.append(response.status_code)

    threads = [threading.Thread(target=attempt) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results.count(201) == 1
    assert results.count(409) == 9


def test_tc17_cancellation_releases_the_slot(client, patient, free_slot):
    reference = client.post("/api/v1/appointments", headers=patient,
                            json={"slot_id": free_slot["id"]}).json()["reference"]

    doctor_id = free_slot["doctor_id"]
    booked_ids = [s["id"] for s in
                  client.get("/api/v1/doctors/%d/slots" % doctor_id).json()]
    assert free_slot["id"] not in booked_ids       # no longer offered

    cancelled = client.delete("/api/v1/appointments/" + reference, headers=patient)
    assert cancelled.status_code == 200

    freed_ids = [s["id"] for s in
                 client.get("/api/v1/doctors/%d/slots" % doctor_id).json()]
    assert free_slot["id"] in freed_ids            # returned to the pool

    assert client.delete("/api/v1/appointments/" + reference,
                         headers=patient).status_code == 409


def test_tc18_cancelling_an_unknown_reference_returns_404(client, patient):
    assert client.delete("/api/v1/appointments/SC-NOTREAL",
                         headers=patient).status_code == 404


def test_tc19_booking_publishes_an_event_and_delivers_a_notification(
        client, patient, free_slot):
    """The booking response must not wait for the notification, but the
    notification must nevertheless arrive shortly afterwards."""
    before = bus.published
    response = client.post("/api/v1/appointments", headers=patient,
                           json={"slot_id": free_slot["id"], "reason": "Fever"})
    assert response.status_code == 201
    assert bus.published > before                  # event was published

    reference = response.json()["reference"]
    deadline = time.time() + 5
    subjects = []
    while time.time() < deadline:
        subjects = [n["subject"] for n in
                    client.get("/api/v1/notifications", headers=patient).json()]
        if any(reference in s for s in subjects):
            break
        time.sleep(0.05)

    assert any(reference in s and "confirmed" in s for s in subjects), subjects
