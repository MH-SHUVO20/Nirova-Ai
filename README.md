

# NirovaAI — নিরোভা 🇧🇩


<div align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:0D1117,50:1F6FEB,100:58A6FF&height=130&section=header&text=NirovaAI&fontSize=38&fontColor=ffffff&fontAlignY=65&animation=fadeIn" width="100%"/>
     <h3>AI-Powered Early Disease Detection for Bangladesh</h3>
     <p><b>Delivering accessible, reliable, and AI-driven medical guidance and early disease risk detection for rural, underserved, and Bengali-speaking communities.</b></p>
</div>

---


---

## 🌐 Project Links

- **Live Application:** [https://nirovaai.app](https://nirovaai.app)
- **GitHub Repository:** [github.com/MH-SHUVO20/Nirova-Ai](https://github.com/MH-SHUVO20/Nirova-Ai)


## 📄 Documentation

- **Project Proposal:** [Google Doc](https://docs.google.com/document/d/1lHR8M3vpf8BGUelYZNe87DpABMs_j7W8iWiebr5IxOw/edit?usp=sharing)
- **Final Report:** [Google Doc](https://docs.google.com/document/d/18EAp14PDXJyHnaqIcLgNo2S9NDRckopE_1rZGbjKJU0/edit?usp=sharing)

[![Live App](https://img.shields.io/badge/🌐%20Live%20App-nirovaai.app-blue?style=for-the-badge)](https://nirovaai.app)
[![Stack](https://img.shields.io/badge/stack-React%20%7C%20FastAPI%20%7C%20MongoDB%20%7C%20Azure-06b6d4?style=flat-square&logo=github)](https://github.com/MH-SHUVO20/Nirova-Ai)
[![Deployed on Azure](https://img.shields.io/badge/deployed-Azure%20Container%20Apps-0078d4?style=flat-square&logo=microsoftazure)](https://azure.microsoft.com)
[![CI/CD](https://github.com/MH-SHUVO20/Nirova-Ai/actions/workflows/deploy.yml/badge.svg)](https://github.com/MH-SHUVO20/Nirova-Ai/actions)

---

## 🩺 Problem Statement & Context


Bangladesh faces a critical shortage of healthcare professionals — with a doctor-to-patient ratio of 1:2,000 — leaving millions without timely access to care. Rural populations are especially impacted due to travel barriers and costs. As a result, conditions like dengue, diabetes, and other treatable diseases often go undiagnosed until advanced stages.

**NirovaAI** bridges this gap by providing accessible, AI-powered early disease risk detection and medical guidance tailored for Bangladesh, with a focus on rural, underserved, and Bengali-speaking users.

---

## 🚀 Key Objectives


- Enable **early detection** of 41+ diseases and provide real-time risk alerts
- Deliver clear, actionable explanations and next steps in both Bangla and English
- Support skin condition analysis, dengue risk assessment, and lab report interpretation using **Bangladesh-specific models**
- Ground all AI guidance in **official Bangladesh and WHO medical knowledge** (via RAG)
- **Note:** This platform is **not** a substitute for professional medical diagnosis or emergency care

---

## ✨ Key Features


| Feature | Description |
|---|---|
| 🔐 **JWT Authentication & Password Reset** | Secure registration, login, and password reset via email |
| 👨‍⚕️ **Symptom Checker** | AI-powered disease prediction and triage based on user symptoms |
| 🦟 **Dengue Detector** | Bangladesh-specific model for accurate dengue risk assessment and triage advice |
| 🤖 **AI Health Chat** | Real-time chat with an LLM (Bangla/English), grounded in Bangladesh and WHO medical sources (RAG) |
| 🔬 **Skin Analysis** | Instant skin condition analysis using Gemini Vision API (no app install required) |
| 🧾 **Lab Report OCR & Explanation** | Upload lab reports for OCR and AI-powered explanation in user's language |
| 📊 **Health Timeline** | Visualize historical symptoms, predictions, and AI suggestions |
| 🚨 **Disease Alerts** | Receive active risk alerts and monthly AI-generated health summaries |
| 🌐 **Bilingual Support** | Answers available in Bengali or English (auto or user-selected) |
| 📈 **Admin Analytics** | Health usage analytics for administrators; supports future dashboards |
| ⚡ **Streaming Responses** | Real-time, token-by-token LLM chat via WebSocket |
| 📨 **Password Reset** | Request password reset with optional SMTP configuration |

---

## 🛠️ Technology Stack


**Frontend:** React, Vite, Tailwind CSS, Nginx
**Backend:** FastAPI, Uvicorn, MongoDB Atlas, PyMongo, Redis, Pydantic, JWT (jose), Python 3.11
**AI/ML:** XGBoost, scikit-learn, Groq API (LLaMA 3), Google Gemini API, sentence-transformers, numpy, pandas, custom RAG pipeline

**Deployment & Infrastructure:**

| Tool | Purpose |
|---|---|
| Docker (multi-stage) | Single container build |
| Docker Compose | Local stack orchestration |
| Docker Hub | Container image registry |
| Azure Container Apps | Cloud hosting |
| Azure Bicep | Infrastructure-as-code |
| GitHub Actions | End-to-end CI/CD, deployment automation |

---

## 🗂️ Project Structure Overview

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
│       │   └── database.py
│       ├── ai/
│       ├── models/
│       └── tasks/
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── components/
│       ├── pages/
│       ├── context/
│       └── utils/
├── infrastructure/
│   ├── main.bicep
│   └── modules/
├── scripts/
│   ├── ingest_rag.py
│   └── smoke_apis.ps1
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## ⚙️ Setup & Installation

### 1. Clone the Repository

```bash
git clone https://github.com/MH-SHUVO20/Nirova-Ai.git
cd Nirova-Ai
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your secrets (MongoDB, API keys, etc.)

### 3. Start All Services

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

### 4. Load RAG Knowledge Base (one-time)

```bash
# Place WHO / IEDCR medical PDFs in /data folder first
python scripts/ingest_rag.py
```

---

## 🗃️ API Reference (Selected Endpoints)

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


> For full request/response schemas, see [nirovaai.app/docs](https://nirovaai.app/docs)

---

## 🚀 Deployment: Single Container on Azure

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

### System Architecture

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

## 📦 Repository Usage & Conventions

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

## ⚠️ Disclaimer

> **NirovaAI is for informational support only.**
> This is NOT a substitute for professional medical diagnosis, treatment, or emergency services.
> Always consult a licensed physician for any serious or unexpected symptoms.

> **এই সেবা শুধুমাত্র তথ্যগত সহায়তা দেয়।**
> নিবন্ধিত চিকিৎসকের পরামর্শ বা চিকিৎসার বিকল্প নয়। জরুরি অবস্থায় নিকটস্থ হাসপাতালে যান।

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## 📬 Contact & Support

For questions, feedback, or support, please open an issue on GitHub or contact [MH Shuvo](https://github.com/MH-SHUVO20).

---

## 👤 Author

**Md. Mehedi Hasan Shuvo** — Project Owner & Lead Developer  
[GitHub: @MH-SHUVO20](https://github.com/MH-SHUVO20)

---

<div align="center">
<strong>Built for Bangladesh 🇧🇩</strong><br/>
<em>Because early detection saves lives.</em>
</div>
