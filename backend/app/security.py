"""Authentication primitives implemented on the Python standard library.

Two concerns live here:

1. Password storage - PBKDF2-HMAC-SHA256 with a per-user 16-byte random salt
   and a configurable iteration count. Verification is done with
   ``hmac.compare_digest`` so the comparison is constant time.
2. Stateless sessions - compact JWTs signed with HS256. Keeping tokens
   stateless is what allows the API tier to be scaled horizontally without a
   shared session store.
"""
import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

from .config import settings

ALGORITHM = "HS256"


# --------------------------------------------------------------------------
# password hashing
# --------------------------------------------------------------------------
def hash_password(password: str, iterations: int | None = None) -> str:
    """Return ``pbkdf2_sha256$<iterations>$<salt_b64>$<hash_b64>``."""
    iterations = iterations or settings.PBKDF2_ITERATIONS
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt_b64, hash_b64 = stored.split("$")
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), _unb64(salt_b64), int(iterations)
    )
    return hmac.compare_digest(digest, _unb64(hash_b64))


# --------------------------------------------------------------------------
# JSON Web Tokens
# --------------------------------------------------------------------------
def create_access_token(subject: str, role: str, ttl: int | None = None) -> str:
    now = int(time.time())
    header = {"alg": ALGORITHM, "typ": "JWT"}
    claims = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + (ttl or settings.JWT_TTL_SECONDS),
        "iss": "smartcare",
    }
    signing_input = f"{_b64(_json(header))}.{_b64(_json(claims))}"
    signature = _sign(signing_input)
    return f"{signing_input}.{_b64(signature)}"


def decode_access_token(token: str) -> dict[str, Any]:
    """Validate signature and expiry. Raises ``ValueError`` when invalid."""
    try:
        header_b64, claims_b64, signature_b64 = token.split(".")
    except ValueError:
        raise ValueError("malformed token") from None

    expected = _sign(f"{header_b64}.{claims_b64}")
    if not hmac.compare_digest(expected, _unb64(signature_b64)):
        raise ValueError("signature mismatch")

    claims = json.loads(_unb64(claims_b64))
    if claims.get("exp", 0) < int(time.time()):
        raise ValueError("token expired")
    return claims


# --------------------------------------------------------------------------
# helpers - base64url without padding, as required by RFC 7515
# --------------------------------------------------------------------------
def _sign(signing_input: str) -> bytes:
    return hmac.new(
        settings.JWT_SECRET.encode(), signing_input.encode(), hashlib.sha256
    ).digest()


def _json(obj: dict[str, Any]) -> bytes:
    return json.dumps(obj, separators=(",", ":"), sort_keys=True).encode()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
