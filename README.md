
# NirovaAI — নিরোভা 🇧🇩

<div align="center">
<strong>Empowering Bangladesh with Accessible, AI-Driven Early Disease Detection</strong>
</div>

<div align="center">
     [![Live App](https://img.shields.io/badge/🌐%20Live%20App-nirovaai.app-blue?style=for-the-badge)](https://nirovaai.app)
     [![Stack](https://img.shields.io/badge/stack-React%20%7C%20FastAPI%20%7C%20MongoDB%20%7C%20Azure-06b6d4?style=flat-square&logo=github)](https://github.com/MH-SHUVO20/Nirova-Ai)
     [![Deployed on Azure](https://img.shields.io/badge/deployed-Azure%20Container%20Apps-0078d4?style=flat-square&logo=microsoftazure)](https://azure.microsoft.com)
     <br>
     <strong>AI-powered early disease detection platform for Bangladesh 🇧🇩</strong>
</div>

---

## 📑 Documentation

- [Final Report](https://docs.google.com/document/d/18EAp14PDXJyHnaqIcLgNo2S9NDRckopE_1rZGbjKJU0/edit?usp=sharing)
- [Project Proposal](https://docs.google.com/document/d/1lHR8M3vpf8BGUelYZNe87DpABMs_j7W8iWiebr5IxOw/edit?usp=sharing)

---

## 🚀 Quick Start

1. **Clone the repository:**
     ```bash
     git clone https://github.com/MH-SHUVO20/Nirova-Ai.git
     cd Nirova-Ai
     ```
2. **Configure environment:**
     - Copy `.env.example` to `.env` and fill in your secrets.
3. **Start the stack:**
     ```bash
     docker-compose up --build
     ```
4. **Access the app:**
     - Frontend: http://localhost:5173
     - Backend API: http://localhost:8000
     - API Docs: http://localhost:8000/docs

---

---


## 🩺 Problem Definition and Context

Bangladesh faces a critical shortage of healthcare professionals, with a **doctor:patient ratio of 1:2,000**. Millions lack timely access to care, especially in rural areas where travel and costs are prohibitive. Diseases like dengue, diabetes, and other treatable conditions often go undiagnosed until advanced stages.

**NirovaAI** bridges this gap by providing accessible, AI-powered early disease risk detection and medical guidance for all, with a focus on rural, underserved, and Bengali-speaking communities.

**Key Objectives:**
- Enable **early detection** of 41+ diseases and real-time risk alerts
- Deliver clear explanations and next steps in Bangla and English
- Support skin condition analysis, dengue risk, and lab report explanation using **Bangladesh-specific models**
- Ground all AI advice in **official Bangladesh and WHO medical knowledge** (via RAG)
- **Note:** This platform is **not** a substitute for registered physician diagnosis or emergency care

---


## ✨ Features

| Feature | User Experience |
|---|---|
| 🔐 **JWT Auth & Password Reset** | Sign up/login, secure sessions, password reset via email (if configured) |
| 👨‍⚕️ **Symptom Checker** | Enter symptoms and instantly receive AI-powered disease prediction, triaged by urgency |
| 🦟 **Dengue Detector** | Bangladesh-specific model—enter clinical info, get real dengue risk, actionable triage advice |
| 🤖 **AI Health Chat** | Chat live with an LLM (Bangla/English) grounded in Bangladesh+WHO medical docs (RAG) |
| 🔬 **Skin Analysis** | Instantly analyze skin condition photos—Gemini Vision API, no app install required |
| 🧾 **Lab Report OCR & Explain** | Upload scanned labs; Gemini Vision extracts and explains meaning in user's language |
| 📊 **Health Timeline** | Visualize all previous symptoms, predictions, and AI suggestions over time |
| 🚨 **Disease Alerts** | See active risk alerts and monthly AI-generated health summaries |
| 🌐 **Bilingual Support** | Get answers in either Bengali or English—auto or by user choice |
| 📈 **Admin Analytics** | (Backend) Health usage data for admins; supports future dashboards |
| ⚡ **Streaming Responses** | Real-time chat (WebSocket) for instant, token-by-token LLM delivery |
| 📨 **Password Reset** | Request email reset with optional SMTP configuration |

---


## 🖥️ Frontend Implementation

| Technology | Version | Use |
|---|---|---|
| React | 18 | Component-based UI; local state/context |
| Vite | ^4 | Fast dev/build tooling |
| Tailwind CSS | ^3 | Scalable, utility-first styling |
| Nginx | stable | Serves frontend from inside container |
| PostCSS | ^8 | Style transforms (with Tailwind) |
| React Context API | - | Global auth state management |
| WebSocket | - | Enables streaming chat for LLM |

**UI/UX Decisions:**
- Mobile-first, responsive design (Bangla font-optimized)
- Bengali/English switch and clear feedback on predictions
- Lab & skin image uploads use Gemini Vision for instant rich results
- Real-time charting/health timelines
- Clean error states, loading spinners, accessibility for rural users

---


## 🛠️ Backend Implementation

| Technology | Version | Use |
|---|---|---|
| FastAPI | ^0.110 | Modern async Python REST API server |
| Uvicorn | ^0.29 | ASGI app runner, Python server |
| MongoDB Atlas | (cloud) | Persistent user, analysis, RAG data |
| PyMongo | ^4.7 | Python MongoDB client |
| Redis | ^5 | Caching, rate limiting |
| Pydantic | ^2 | Data validation, schema serialization |
| JWT (jose) | ^3 | Auth tokens |
| Python | 3.11 | Language base |

**APIs and Database:**
- Auth: Registration, JWT, password reset
- Symptoms: Log, analyze, view history (all tied to MongoDB per user)
- Chat: FastAPI async WS endpoint with context-aware LLM
- RAG knowledge: APIs can search/retrieve Bangladesh medical facts (vector search)
- Admin endpoints: Only accessible if user is admin

---


## 🧠 AI Integration & Methodology

### Models Table

| Model File | Type | Dataset | Input Features | Output | Metrics |
|---|---|---|---|---|---|
| `disease_classifier.pkl` | XGBoost multi-class | itachi9604/disease-symptom-description-dataset — 4,920 real + 24,600 augmented | 131 binary symptom features | 41 disease classes | **100% CV on augmented training data** — reflects dataset structure, not guaranteed on unseen real-world symptoms. See `disease_model_eval.json`. |
| `dengue_classifier.pkl` | XGBoost binary | kawsarahmad/dengue-dataset-bangladesh — 1,000 real BD hospital + 5,000 augmented | Gender, Age, NS1, IgG, IgM, Area, AreaType, HouseType, District | Dengue positive/negative, risk score | Accuracy: **89.1%**, AUC: **0.964** |

> Confusion matrix for `dengue_classifier`: `[[406, 61], [48, 485]]` — see `backend/app/models/dengue_model_eval.json`.

### Model Details

**disease_classifier.pkl**
- Trained on: [itachi9604/disease-symptom-description-dataset](https://www.kaggle.com/itachi9604/disease-symptom-description-dataset)
- 41 disease classes, 131 symptoms, 4,920 real + 24,600 augmented samples
- Input: Multi-hot vector (0/1) for each symptom
- Output: Top N probable diseases, ranked by probability
- Eval: 100% mean cross-validation accuracy (augmented training); real-world accuracy will be lower — full classification metrics in `backend/app/models/disease_model_eval.json`

**dengue_classifier.pkl**
- Trained on: [kawsarahmad/dengue-dataset-bangladesh](https://www.kaggle.com/kawsarahmad/dengue-dataset-bangladesh) + augmentation
- Input: Clinical/lab features (Gender, Age, NS1, IgG, IgM, Area, AreaType, HouseType, District)
- Output: Dengue positive/negative, risk probability
- Accuracy: **89.1%, AUC 0.964** on validation
- Full classification report & confusion matrix in `backend/app/models/dengue_model_eval.json`

**Google Gemini API (Vision)**
- *Skin Photo Analysis:* User uploads a skin lesion photo → forwarded to Gemini Vision API with clinical history prompt → returns condition classification, confidence, and triage advice in Bengali or English
- *Lab OCR:* User uploads scanned blood/lab report → Gemini extracts test results, units, and provides plain-language explanation of abnormal findings
- Output: Structured JSON parsed by backend, relayed to user

**RAG Pipeline**
- Source PDFs: Bangladesh Ministry of Health, IEDCR, and WHO guides

---


## ⚙️ Full Tech Stack

### AI/ML

| Tool | Version/Source | Use |
|---|---|---|
| xgboost | ^2.x | Disease/dengue classifiers |
| scikit-learn | ^1.x | Preprocessing, label encoding |
| Groq API (LLaMA 3) | [groq.com](https://console.groq.com) | LLM streaming health chat |
| Google Gemini API | [aistudio.google.com](https://aistudio.google.com) | Vision: lab OCR & skin analysis |
| sentence-transformers | ^2.x | Text embedding for RAG |
| numpy, pandas | latest | Feature engineering |
| RAG pipeline | custom | Grounded Bangladesh-specific retrieval |

### Infrastructure

| Tech | Purpose |
|---|---|
| Docker (multi-stage) | Root build: React + Python + static assets, single container |
| Docker Compose | Local stack orchestration |
| Azure Container Apps | Production hosting, pulls from Docker Hub |
| Docker Hub | Container image registry |
| Azure Bicep | Infrastructure-as-code |
| GitHub Actions | End-to-end CI/CD, deployment automation |

---



## 🗂️ Project Structure

```
Nirova-Ai/
│
├── backend/
│   ├── Dockerfile              ← Python 3.11 backend image
│   ├── requirements.txt        ← Python dependencies (AI, API)
│   └── app/
│       ├── main.py             ← FastAPI entry point
│       ├── __init__.py
│       ├── api/
│       │   ├── __init__.py
│       │   ├── auth.py         ← Register, login, password reset
│       │   ├── symptoms.py     ← Symptom log, analyze, predict
│       │   ├── chat.py         ← LLM chat + RAG + WebSocket
│       │   ├── health.py       ← Timeline, alerts, summaries
│       │   ├── vision.py       ← Skin & lab analysis via Gemini
│       │   ├── language.py     ← Translation API
│       │   └── analytics.py    ← Admin usage endpoints
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py
│       │   ├── auth.py
│       │   ├── analytics.py
│       │   ├── errors.py
│       │   ├── database.py
│       │   ├── language_detector.py
│       │   ├── monitoring.py
│       │   ├── rate_limit.py
│       │   ├── redis_client.py
│       │   └── translations.py
│       ├── ai/
│       │   ├── __init__.py
│       │   ├── llm_router.py
│       │   ├── agents/
│       │   │   ├── __init__.py
│       │   │   └── langgraph_orchestrator.py
│       │   ├── ml/
│       │   │   ├── __init__.py
│       │   │   ├── dengue_model.py
│       │   │   └── disease_model.py
│       │   ├── rag/
│       │   │   ├── __init__.py
│       │   │   ├── embedder.py
│       │   │   └── retriever.py
│       │   └── vision/
│       │       ├── __init__.py
│       │       └── skin_model.py
│       ├── models/
│       │   ├── class_names.json
│       │   ├── dengue_feature_columns.json
│       │   ├── dengue_model_eval.json
│       │   ├── disease_model_eval.json
│       │   ├── symptom_columns.json
│       │   ├── disease_classifier.pkl
│       │   ├── dengue_classifier.pkl
│       │   └── disease_label_encoder.pkl
│       └── tasks/
│           ├── __init__.py
│           └── health_timeline.py
├── frontend/
│   ├── Dockerfile              ← Nginx + Vite build
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   ├── nginx.conf
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   ├── vercel.json
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       ├── index.css
│       ├── components/
│       │   ├── EmergencyHospitals.jsx
│       │   ├── ErrorBoundary.jsx
│       │   ├── GlobalChatWidget.jsx
│       │   ├── LanguageSelector.jsx
│       │   └── Layout.jsx
│       ├── context/
│       │   ├── AuthContext.jsx
│       │   ├── LanguageContext.jsx
│       │   └── ThemeContext.jsx
│       ├── pages/
│       │   ├── ChatPage.jsx
│       │   ├── DashboardPage.jsx
│       │   ├── DenguePage.jsx
│       │   ├── ForgotPasswordPage.jsx
│       │   ├── LabReportPage.jsx
│       │   ├── LandingPage.jsx
│       │   ├── LoginPage.jsx
│       │   ├── PrescriptionPage.jsx
│       │   ├── RegisterPage.jsx
│       │   ├── ResetPasswordPage.jsx
│       │   ├── SkinPage.jsx
│       │   ├── SymptomsPage.jsx
│       │   └── TimelinePage.jsx
│       └── utils/
│           ├── api.js
│           └── location.js
├── infrastructure/
│   ├── azure.yaml
│   ├── main.bicep              ← Azure Container Apps IaC
│   ├── parameters.prod.json
│   ├── README.md
│   ├── modules/
│   │   ├── acr.bicep
│   │   ├── appinsights.bicep
│   │   ├── cosmosdb.bicep
│   │   ├── keyvault.bicep
│   │   ├── privateendpoints.bicep
│   │   ├── redis.bicep
│   │   ├── storage.bicep
│   │   ├── webapp_backend.bicep
│   │   └── webapp_frontend.bicep
│   └── parameters/
│       ├── dev.parameters.json
│       └── prod.parameters.json
├── scripts/
│   ├── ingest_rag.py           ← Load medical PDFs into MongoDB Vector Search
│   └── smoke_apis.ps1          ← Post-deploy API smoke tests
├── Dockerfile                  ← Root multi-stage build (React → FastAPI)
├── docker-compose.yml          ← Local dev: frontend, backend, mongo, redis
└── .env.example                ← All required environment variables
```

---


## 🖥️ Local Development Setup

### Prerequisites
- Docker + Docker Compose
- MongoDB Atlas account (free tier)
- [Groq API key](https://console.groq.com) (free)
- [Gemini API key](https://aistudio.google.com) (free)

### Step 1 — Clone

```bash
git clone https://github.com/MH-SHUVO20/Nirova-Ai.git
cd Nirova-Ai
```

### Step 2 — Environment Variables

Copy `.env.example` to `.env` and fill in all secrets:

```env
# Core
APP_NAME=NirovaAI
DEBUG=false
ALLOWED_ORIGINS=http://localhost:5173,https://nirovaai.app
FRONTEND_URL=http://localhost:5173

# MongoDB
MONGODB_URI=your_mongo_atlas_connection_string
MONGODB_DB_NAME=nirovaai

# Auth
SECRET_KEY=your-random-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=10080
AUTH_COOKIE_NAME=access_token

# AI/ML
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=AIzaSy...
RAG_TOP_K=4
RAG_CANDIDATE_LIMIT=30
RAG_KB_MAX_CHARS=2800

# Redis
REDIS_URL=redis://localhost:6379/0

# Optional: email (password reset)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_USE_TLS=true
```

### Step 3 — Start Everything

```bash
docker-compose up --build
```

| Service | URL |
|---|---|
| 🌐 Frontend (Vite dev) | http://localhost:5173 |
| ⚡ Backend API | http://localhost:8000 |
| 📖 Swagger UI | http://localhost:8000/docs |
| 🍃 MongoDB | localhost:27017 |
| 🔴 Redis | localhost:6379 |

### Step 4 — Load RAG Knowledge Base (run once)

```bash
# Place WHO / IEDCR medical PDFs in /data folder first
python scripts/ingest_rag.py
```

---


## 🗃️ API Reference

### Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | No | Register: email + password |
| POST | `/auth/login` | No | Login → JWT token |
| GET | `/auth/me` | Yes | Get current user profile |
| POST | `/auth/forgot` | No | Request password reset email |
| POST | `/auth/reset` | No | Confirm code + new password |

### Symptoms

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/symptoms/analyze` | Yes | Submit symptoms → ML disease prediction |
| POST | `/symptoms/log` | Yes | Log symptoms + save prediction |
| GET | `/symptoms/history` | Yes | Full symptom log history |
| GET | `/symptoms/latest` | Yes | Most recent entry |

### Chat (LLM + RAG)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/chat/ask` | Yes | RAG-grounded AI chat response |
| WS | `/chat/ws` | Yes | WebSocket real-time streaming chat |

### Health

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | No | Liveness check |
| GET | `/health/timeline` | Yes | Full health history for charts |
| GET | `/health/alerts` | Yes | Active disease alerts |
| GET | `/health/summary` | Yes | AI-generated monthly summary |

### Vision (Gemini)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/vision/detect` | Yes | Skin condition from photo |
| POST | `/vision/analyze-lab` | Yes | Lab report OCR + explanation |

### Language & Analytics

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/language/translate` | No | Translate content to target language |
| GET | `/analytics/usage` | Yes (admin) | API usage stats |

> Full request/response schemas at [nirovaai.app/docs](https://nirovaai.app/docs)

---


## 🚀 Deployment — Single Container on Azure

NirovaAI ships as **one Docker container** serving everything on port 8000:

- **Stage 1** (`node:18-alpine`): builds React app → outputs `/app/frontend/dist`
- **Stage 2** (`python:3.11-slim`): installs Python + ML deps, copies backend, copies `dist/` into FastAPI `/static`
- One container, one port — frontend SPA and API both served by FastAPI


### CI/CD Pipeline (Docker Hub → Azure)

```
Push to main
     │
     ▼
Docker build (root Dockerfile, multi-stage)
     │
     ├── docker push → Docker Hub (mh-shuvo20/nirovaai:latest)
     │
     ├── Azure Container Apps pulls new image from Docker Hub
     │        └── rolling update, zero downtime
     │
     └── smoke tests (scripts/smoke_apis.ps1)
```

### Architecture

```
                     nirovaai.app
                          │
         ┌────────────────▼────────────────┐
         │       Azure Container Apps       │
         │                                 │
         │  ┌─────────────────────────────┐│
         │  │    Single Docker Container  ││
         │  │                             ││
         │  │  FastAPI  :8000             ││
         │  │  ├── /api/*   → REST API   ││
         │  │  ├── /chat/ws → WebSocket  ││
         │  │  └── /*       → React SPA  ││
         │  │       (from /static/dist)  ││
         │  └─────────────────────────────┘│
         └────────────────┬────────────────┘
                          │
         ┌────────────────▼────────────────┐
         │           Docker Hub            │
         │    mh-shuvo20/nirovaai:latest   │
         └────────────────┬────────────────┘
                          │
         ┌────────────────▼────────────────┐
         │         MongoDB Atlas           │
         └─────────────────────────────────┘
```

**Live URL:** [https://nirovaai.app](https://nirovaai.app)

---



## 📝 Repo Usage

- Monorepo structure: `frontend/`, `backend/`, `infrastructure/`, `scripts/`
- All API and ML code in repo — no opaque binaries
- Descriptive commit messages (feature/fix convention), squash merges for clarity
- CI/CD handled via Docker Hub builds and Azure Container Apps

---


## 💡 Innovation & Impact

- **Bengali Language First** — Medical chat, symptom explanations, and AI vision natively support Bengali, serving the actual population of Bangladesh
- **Bangladesh-Localized Models** — Dengue detector trained on real Bangladesh hospital records; RAG uses only Bangladesh and WHO medical sources
- **RAG Reduces Hallucinations** — Unlike generic LLMs, NirovaAI grounds every medical answer in verified Bangladesh-specific PDFs (IEDCR, DGHS, WHO)
- **True Multimodal** — Gemini API enables skin and lab imaging via simple web upload, with no local ML infrastructure required
- **Rural Access** — Brings expert triage and early awareness to villages with just a smartphone and internet connection
- **Open & Transparent AI** — All model code, methodology, datasets, and metrics are visible in the repo

---


## 📝 Disclaimer

> **NirovaAI is for informational support only.**  
> This is NOT a substitute for professional medical diagnosis, treatment, or emergency services.  
> Always consult a licensed physician for any serious or unexpected symptoms.

> **এই সেবা শুধুমাত্র তথ্যগত সহায়তা দেয়।**  
> নিবন্ধিত চিকিৎসকের পরামর্শ বা চিকিৎসার বিকল্প নয়। জরুরি অবস্থায় নিকটস্থ হাসপাতালে যান।

---


## 👤 Author

**MH Shuvo** — BSc Computer Science Capstone Project  
[GitHub: @MH-SHUVO20](https://github.com/MH-SHUVO20)

---


---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 📬 Contact & Support

For questions, feedback, or support, please open an issue on GitHub or contact [MH Shuvo](https://github.com/MH-SHUVO20).

<div align="center">
<strong>Built for Bangladesh 🇧🇩</strong><br/>
<em>Because early detection saves lives.</em>
</div>