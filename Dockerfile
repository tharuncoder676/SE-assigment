# ---------- stage 1: build the dependency layer ----------------------------
FROM python:3.12-slim AS builder
WORKDIR /install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install/deps -r requirements.txt

# ---------- stage 2: minimal runtime image ---------------------------------
FROM python:3.12-slim
LABEL org.opencontainers.image.title="SmartCare Appointment Platform" \
      org.opencontainers.image.version="1.0.0"

# Never run application code as root.
RUN useradd --create-home --uid 10001 smartcare
WORKDIR /app

COPY --from=builder /install/deps /usr/local
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production \
    DATABASE_URL=sqlite:////data/smartcare.db

RUN mkdir -p /data && chown -R smartcare:smartcare /app /data
USER smartcare
WORKDIR /app/backend
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
