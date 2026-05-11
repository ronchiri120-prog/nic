# ═══════════════════════════════════════════════════════════════════════
#  QuickLender — Multi-stage Dockerfile
#  Stage 1: builder  — installs deps + compiles wheels
#  Stage 2: runtime  — minimal production image
# ═══════════════════════════════════════════════════════════════════════

# ─── Stage 1: Builder ─────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# System build deps
RUN apt-get update -qq && apt-get install -y -qq \
    build-essential libpq-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps into a prefix
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --prefix=/install --no-deps -r requirements.txt

# ─── Stage 2: Runtime ─────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Runtime system deps only
RUN apt-get update -qq && apt-get install -y -qq \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 quicklender

# Copy installed packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app
COPY --chown=quicklender:quicklender . .

USER quicklender

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

EXPOSE 8000

CMD ["gunicorn", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "quicklender_project.wsgi:application"]
