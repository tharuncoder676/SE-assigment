"""Authentication service: registration, login and profile."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import current_user
from ..models import AuditLog, User
from ..ratelimit import limiter
from ..schemas import LoginRequest, RegisterRequest, TokenResponse
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
log = logging.getLogger("smartcare.auth")


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Create a patient account and return an access token."""
    if db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(status_code=409, detail="Email is already registered")

    user = User(
        full_name=payload.full_name,
        email=payload.email.lower(),
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.add(AuditLog(actor=user.email, action="REGISTER", entity="user"))
    db.commit()
    db.refresh(user)
    log.info("user registered", extra={"user": user.email})

    return TokenResponse(
        access_token=create_access_token(user.email, user.role),
        expires_in=settings.JWT_TTL_SECONDS,
        role=user.role,
        full_name=user.full_name,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Exchange e-mail and password for a signed JWT."""
    client = request.client.host if request.client else "unknown"
    if not limiter.allow("login:%s" % client):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts, please retry shortly",
        )

    user = db.query(User).filter(User.email == payload.email.lower()).first()
    # The password is verified even when the account does not exist so that the
    # response time does not disclose which e-mail addresses are registered.
    reference_hash = user.password_hash if user else hash_password("dummy", 1000)
    if not verify_password(payload.password, reference_hash) or user is None:
        db.add(AuditLog(actor=payload.email.lower(), action="LOGIN_FAILED", entity="user"))
        db.commit()
        log.warning("failed login", extra={"user": payload.email.lower()})
        raise HTTPException(status_code=401, detail="Invalid e-mail or password")

    db.add(AuditLog(actor=user.email, action="LOGIN", entity="user"))
    db.commit()
    return TokenResponse(
        access_token=create_access_token(user.email, user.role),
        expires_in=settings.JWT_TTL_SECONDS,
        role=user.role,
        full_name=user.full_name,
    )


@router.get("/me", tags=["Authentication"])
def me(user: User = Depends(current_user)):
    """Return the profile of the caller identified by the bearer token."""
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
    }
