# Azure Deployment Guide (nirovaai.app)

## 1. Target Topology
- Backend API: Azure Container Apps.
- Database: MongoDB Atlas (existing) or Azure Cosmos DB for Mongo API (optional migration).
- Cache: Azure Cache for Redis.
- Frontend: Vercel (existing) or Azure Static Web Apps.
- Domain: nirovaai.app mapped to frontend and api.nirovaai.app mapped to backend.

## 2. Prerequisites
- Azure subscription with billing enabled.
- Azure CLI installed and logged in.
- Container registry access.
- DNS access for nirovaai.app records.

## 3. Backend Deploy (Container Apps)
Build and push image:

```bash
az login
az group create --name nirovaai-rg --location eastus
az acr create --resource-group nirovaai-rg --name nirovaaiacr --sku Basic
az acr build --registry nirovaaiacr --image nirovaai-backend:latest ./backend
```

Create Container Apps environment and app:

```bash
az containerapp env create --name nirovaai-env --resource-group nirovaai-rg --location eastus
az containerapp create \
  --name nirovaai-api \
  --resource-group nirovaai-rg \
  --environment nirovaai-env \
  --image nirovaaiacr.azurecr.io/nirovaai-backend:latest \
  --target-port 8000 \
  --ingress external \
  --registry-server nirovaaiacr.azurecr.io \
  --min-replicas 1 --max-replicas 3
```

Set environment variables:

```bash
az containerapp update \
  --name nirovaai-api \
  --resource-group nirovaai-rg \
  --set-env-vars \
  MONGODB_URI="..." \
  MONGODB_DB_NAME="nirovaai" \
  SECRET_KEY="..." \
  GROQ_API_KEY="..." \
  GEMINI_API_KEY="..." \
  ALLOWED_ORIGINS="https://nirovaai.app,https://www.nirovaai.app" \
  FRONTEND_URL="https://nirovaai.app"
```

## 4. Frontend Deploy
Option A (current simple path): keep Vercel and set `VITE_API_URL` to backend HTTPS URL.

Option B (Azure-native): deploy frontend on Azure Static Web Apps and set environment config accordingly.

## 5. Custom Domain Setup
- Frontend:
  - Map `nirovaai.app` and `www.nirovaai.app` to frontend host.
- Backend:
  - Map `api.nirovaai.app` to Container Apps ingress endpoint.
- DNS records:
  - Add `A` or `CNAME` records as required by host provider.
- TLS:
  - Enable managed certificates on both frontend and backend hosts.

## 6. Production Checklist
- Disable debug logging in frontend and backend.
- Verify CORS includes production domain only.
- Enforce strong secrets and rotate API keys.
- Add uptime monitoring and error telemetry.
- Run smoke tests against production endpoints.

## 7. Suggested Go-Live Validation
- Auth register/login flow works.
- Symptoms prediction works and history persists.
- Chat responds with mode-isolated context.
- Vision endpoints respond within expected limits.
- Domain + TLS valid on root and API subdomain.
