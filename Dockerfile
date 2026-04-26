# ─────────────────────────────────────────────────────────────
# NirovaAI — Monolith Dockerfile (Frontend + Backend)
# For single-container deployments (Azure App Service, Railway, etc.)
# ─────────────────────────────────────────────────────────────

# ── Stage 1: Build React Frontend ─────────────────────────────
FROM node:20-alpine AS frontend-build
WORKDIR /build

# Layer cache: install deps before copying source
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --production=false

COPY frontend/ ./
ARG VITE_API_URL=""
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build
# Output: /build/dist

# ── Stage 2: Python Backend + Serve Frontend ──────────────────
FROM python:3.11-slim AS production

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# Layer cache: install Python deps before copying source
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./

# Copy frontend build output
COPY --from=frontend-build /build/dist ./static

# Set ownership and create model directory
RUN mkdir -p /app/models && chown -R appuser:appuser /app

# Run as non-root
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
