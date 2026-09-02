"""Central configuration. All values are overridable through environment
variables so the same image can run in dev, test and production (12-factor)."""
import os


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "SmartCare Appointment Platform")
    VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    ENV: str = os.getenv("APP_ENV", "development")

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./smartcare.db")

    # HS256 signing key for access tokens. MUST be supplied in production.
    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-only-insecure-secret-change-me")
    JWT_TTL_SECONDS: int = int(os.getenv("JWT_TTL_SECONDS", "3600"))

    # Password hashing work factor (OWASP recommends >= 600000 for PBKDF2-SHA256)
    PBKDF2_ITERATIONS: int = int(os.getenv("PBKDF2_ITERATIONS", "600000"))

    # Sliding-window rate limit applied to authentication endpoints
    RATE_LIMIT_MAX: int = int(os.getenv("RATE_LIMIT_MAX", "20"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

    SLOT_MINUTES: int = int(os.getenv("SLOT_MINUTES", "30"))


settings = Settings()
