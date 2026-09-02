"""SQLAlchemy engine / session factory.

SQLite is used for the prototype; because access goes exclusively through the
ORM, switching to PostgreSQL is a change of ``DATABASE_URL`` only.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

connect_args = (
    {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency - one session per request, always closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def session_scope():
    """Session factory for code that runs outside the request cycle.

    Background event-bus workers execute on their own threads and therefore
    cannot reuse the request-scoped session. Routing them through this
    function (rather than through ``SessionLocal`` directly) also gives the
    test suite a single place to redirect them at a throw-away database.
    """
    return SessionLocal()
