# NirovaAI — নিরোভা
### Early Disease Detection for Bangladesh 🇧🇩

> AI-powered health assistant that tracks symptoms, detects diseases early,
> and provides second opinions grounded in Bangladesh medical guidelines.

---

## Project Structure

```
nirovaai/
├── backend/               ← FastAPI Python backend
│   ├── app/
│   │   ├── main.py        ← entry point
│   │   ├── api/           ← route handlers
│   │   ├── ai/            ← ML models + RAG + LLM
│   │   ├── core/          ← config, database, auth
│   │   └── models/        ← trained ML model files (.pkl, .json)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/              ← React 18 + Vite + Tailwind
│   ├── src/
│   │   ├── pages/         ← all page components
│   │   ├── components/    ← shared components
│   │   ├── context/       ← auth state
│   │   └── utils/         ← API service layer
│   └── package.json
├── scripts/
│   └── ingest_rag.py      ← loads medical knowledge into MongoDB
├── data/                  ← put WHO/IEDCR PDFs here for RAG
├── docker-compose.yml     ← run everything locally
└── .env                   ← single shared env file
```

---

## Quick Start (Local Development)

### Step 1 — Setup environment
```bash
# Fill in: MONGODB_URI, GROQ_API_KEY, GEMINI_API_KEY, SECRET_KEY, VITE_API_URL
```

### Step 2 — Add model files
Put these in `backend/app/models/` (already included):
- `disease_classifier.pkl` + `class_names.json` + `symptom_columns.json`
- `dengue_classifier.pkl` + `dengue_feature_columns.json`
- `skin_model.onnx` + `skin_classes.json` ← add when EfficientNet training done

### Step 3 — Start backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Or with Docker:
```bash
docker-compose up
```

### Step 4 — Start frontend
```bash
cd frontend
npm install
npm run dev
```

### Step 5 — Load RAG knowledge base (run once)
```bash
# Put medical PDFs in data/ folder first
python scripts/ingest_rag.py
```

### Step 6 — Open the app
- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs

---

## AI Models

| Model | Dataset | Accuracy | Purpose |
|-------|---------|----------|---------|
| XGBoost Disease Classifier | itachi9604 (4920 samples) | 87.07% | 41 diseases, 131 symptoms |
| XGBoost Dengue Detector | kawsarahmad BD hospital data | 89.1%, AUC 0.964 | Real Bangladesh dengue detection |
| EfficientNet-B0 Skin | ismailpromus ISIC dataset | Training... | 10 skin conditions |

---

## API Endpoints

```
POST /auth/register         → create account
POST /auth/login            → get JWT token
GET  /auth/me               → current user

POST /symptoms/log          → log symptoms + instant ML prediction
POST /symptoms/predict      → predict disease (+ dengue with lab values)
GET  /symptoms/history      → symptom history
GET  /symptoms/latest       → most recent log

POST /chat/ask              → RAG AI chat
WS   /chat/ws               → WebSocket streaming chat

GET  /health/timeline       → full health history (for charts)
GET  /health/alerts         → active disease alerts
GET  /health/summary        → AI monthly summary

POST /vision/analyze-skin   → skin condition from photo
POST /vision/analyze-lab    → lab report OCR + explanation
```

---

## Deployment

### Backend → Azure Container Apps
```bash
az login
az group create --name nirovaai-rg --location eastus
az containerapp env create --name nirovaai-env --resource-group nirovaai-rg --location eastus
az acr create --resource-group nirovaai-rg --name nirovanirova --sku Basic
az acr build --registry nirovanirova --image nirovaai-backend:latest ./backend
az containerapp create \
  --name nirovaai-api \
  --resource-group nirovaai-rg \
  --environment nirovaai-env \
  --image nirovanirova.azurecr.io/nirovaai-backend:latest \
  --target-port 8000 \
  --ingress external \
  --min-replicas 1
```

### Frontend → Vercel
```bash
cd frontend
npm install -g vercel
vercel --prod
# Set VITE_API_URL in root .env (single env file setup)
```

For full deployment and domain mapping steps, see `AZURE_DEPLOYMENT.md`.

---

## Capstone Documents

- Proposal: `CAPSTONE_PROPOSAL.md`
- Final Report: `FINAL_REPORT.md`

---

## Environment Variables

```env
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/nirovaai
MONGODB_DB_NAME=nirovaai
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=AIzaSy...
SECRET_KEY=your-secret-key
ALLOWED_ORIGINS=http://localhost:5173,https://nirovaai.app
FRONTEND_URL=http://localhost:5173

# Optional: email delivery for forgot-password
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=app-password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_USE_TLS=true
```

---

## Disclaimer
Disclaimer: এই সেবা কেবল তথ্যগত সহায়তা দেয়; এটি নিবন্ধিত চিকিৎসকের পরামর্শ, রোগ নির্ণয় বা চিকিৎসার বিকল্প নয়।
NirovaAI is for informational support only and does not replace professional medical consultation, diagnosis, or treatment.
