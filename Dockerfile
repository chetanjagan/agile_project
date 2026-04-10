# ─────────────────────────────────────────────
#  Stage 1 — Builder (install dependencies)
# ─────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install into a prefix so we can copy them cleanly
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --prefix=/install --no-cache-dir -r requirements.txt


# ─────────────────────────────────────────────
#  Stage 2 — Runtime (lean final image)
# ─────────────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL maintainer="taskflow@example.com"
LABEL version="1.0.0"
LABEL description="TaskFlow — Agile Task Management App"

# Create non-root user for security
RUN groupadd -r taskflow && useradd -r -g taskflow taskflow

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY --chown=taskflow:taskflow . .

# Create data directory for SQLite (will be mounted as volume in k8s)
RUN mkdir -p /app/instance && chown taskflow:taskflow /app/instance

# Switch to non-root user
USER taskflow

# Expose port
EXPOSE 5000

# Health check — Docker/K8s will use this to know if the container is alive
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# Start with Gunicorn (production WSGI server, NOT Flask dev server)
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "2", \
     "--threads", "4", \
     "--worker-class", "gthread", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info", \
     "app:app"]
