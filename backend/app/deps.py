"""Shared FastAPI dependencies: bearer-token extraction and role guards."""
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .security import decode_access_token

UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def current_user(
    authorization: str = Header(default=""), db: Session = Depends(get_db)
) -> User:
    if not authorization.lower().startswith("bearer "):
        raise UNAUTHORIZED
    try:
        claims = decode_access_token(authorization.split(" ", 1)[1].strip())
    except ValueError:
        raise UNAUTHORIZED

    user = db.query(User).filter(User.email == claims["sub"]).first()
    if user is None or not user.is_active:
        raise UNAUTHORIZED
    return user


def require_role(*roles: str):
    """Role-based access control guard used on administrative endpoints."""
    def guard(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted for role '%s'" % user.role,
            )
        return user
    return guard
