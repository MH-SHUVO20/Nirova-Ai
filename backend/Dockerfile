# ─────────────────────────────────────────────────────────────
# NirovaAI — Backend Dockerfile
# Used by docker-compose for the backend service
# ─────────────────────────────────────────────────────────────
FROM python:3.11-slim

LABEL maintainer="NirovaAI Team"
LABEL description="NirovaAI FastAPI Backend"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# Layer cache: install deps first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create model directory and set ownership
RUN mkdir -p /app/models && chown -R appuser:appuser /app

# Run as non-root user
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
