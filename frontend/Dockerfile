# ─────────────────────────────────────────────────────────────
# NirovaAI — Frontend Dockerfile
# Multi-stage: Build React → Serve with Nginx
# ─────────────────────────────────────────────────────────────

# ── Stage 1: Build ────────────────────────────────────────────
FROM node:20-alpine AS builder

LABEL maintainer="NirovaAI Team"

WORKDIR /app

# Layer cache: install deps before source copy
COPY package.json package-lock.json ./
RUN npm ci --production=false

# Copy source and build
COPY . .

# Accept API URL at build time
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=${VITE_API_URL}

RUN npm run build

# ── Stage 2: Serve ────────────────────────────────────────────
FROM nginx:1.27-alpine AS production

LABEL description="NirovaAI Frontend (Nginx)"

# Remove default Nginx config
RUN rm -rf /etc/nginx/conf.d/default.conf

# Copy custom Nginx config and built assets
COPY --from=builder /app/dist /usr/share/nginx/html
COPY ./nginx.conf /etc/nginx/conf.d/default.conf

# Security: run as non-root (nginx user exists in the base image)
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    touch /var/run/nginx.pid && \
    chown nginx:nginx /var/run/nginx.pid

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
