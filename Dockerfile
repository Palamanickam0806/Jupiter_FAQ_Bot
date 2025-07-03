# ─ Base image ─────────────────────────────────────────────
FROM python:3.12-slim

# ─ Env & dirs ─────────────────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_BUILD_ISOLATION=1 \
    PORT=8000 \
    ANONYMIZED_TELEMETRY=false          # ← disables Chroma telemetry at boot

WORKDIR /app

# ─ Dependencies ───────────────────────────────────────────
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r requirements.txt

# ─ Source code ────────────────────────────────────────────
COPY . .

# ─ Entrypoint ─────────────────────────────────────────────
# Adjust module path if your Flask app factory lives elsewhere
CMD ["gunicorn", "-b", "0.0.0.0:8000", "main_bot:app"]
