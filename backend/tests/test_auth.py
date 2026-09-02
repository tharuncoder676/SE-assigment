"""TC-01 .. TC-08 - authentication, password storage and access control."""
import time

import pytest

from app.security import (
    create_access_token, decode_access_token, hash_password, verify_password,
)


def test_tc01_register_returns_token(client):
    response = client.post("/api/v1/auth/register", json={
        "full_name": "Arun Kumar",
        "email": "arun@example.com",
        "phone": "9000000001",
        "password": "Str0ng@Pass1",
    })
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["role"] == "patient"
    assert len(body["access_token"].split(".")) == 3


def test_tc02_duplicate_email_rejected(client, patient):
    response = client.post("/api/v1/auth/register", json={
        "full_name": "Impostor",
        "email": "priya.patient@smartcare.local",
        "password": "Another@1234",
    })
    assert response.status_code == 409


def test_tc03_short_password_rejected(client):
    response = client.post("/api/v1/auth/register", json={
        "full_name": "Weak User", "email": "weak@example.com", "password": "abc",
    })
    assert response.status_code == 422        # pydantic validation


def test_tc04_login_success_and_failure(client, patient):
    ok = client.post("/api/v1/auth/login", json={
        "email": "priya.patient@smartcare.local", "password": "Patient@12345",
    })
    assert ok.status_code == 200

    bad = client.post("/api/v1/auth/login", json={
        "email": "priya.patient@smartcare.local", "password": "WrongPass99",
    })
    assert bad.status_code == 401
    assert "Invalid" in bad.json()["detail"]


def test_tc05_password_is_never_stored_in_clear(client, db_session, patient):
    from app.models import User
    user = db_session.query(User).filter(
        User.email == "priya.patient@smartcare.local").first()
    assert "Patient@12345" not in user.password_hash
    assert user.password_hash.startswith("pbkdf2_sha256$")
    assert verify_password("Patient@12345", user.password_hash)
    assert not verify_password("Patient@12346", user.password_hash)


def test_tc06_salt_makes_identical_passwords_differ():
    first = hash_password("SamePassword1", 1000)
    second = hash_password("SamePassword1", 1000)
    assert first != second                     # unique per-user salt
    assert verify_password("SamePassword1", first)
    assert verify_password("SamePassword1", second)


def test_tc07_protected_route_requires_valid_token(client, patient):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me",
                      headers={"Authorization": "Bearer forged.token.value"}
                      ).status_code == 401
    assert client.get("/api/v1/auth/me", headers=patient).json()["email"] == \
        "priya.patient@smartcare.local"


def test_tc08_tampered_or_expired_token_is_rejected():
    token = create_access_token("user@example.com", "patient")
    assert decode_access_token(token)["role"] == "patient"

    header, claims, signature = token.split(".")
    tampered = "%s.%s.%s" % (header, claims, signature[:-2] + "AA")
    with pytest.raises(ValueError):
        decode_access_token(tampered)

    expired = create_access_token("user@example.com", "patient", ttl=-1)
    time.sleep(0.01)
    with pytest.raises(ValueError):
        decode_access_token(expired)


def test_tc09_role_guard_blocks_patient_from_admin_endpoint(client, patient):
    assert client.get("/api/v1/admin/stats", headers=patient).status_code == 403
