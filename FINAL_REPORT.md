# NirovaAI Final Capstone Report

## 1. Executive Summary
NirovaAI is a full-stack, AI-assisted health support platform designed for early disease awareness in Bangladesh. It combines symptom tracking, machine learning prediction, LLM-assisted guidance, and image-based analysis to provide users with structured and safer informational support.

## 2. Motivation and Context
Many users delay medical action because symptoms are unclear and healthcare access can be uneven. NirovaAI addresses this gap by giving users a consistent digital assistant to monitor health signals, review risk predictions, and follow actionable next steps.

## 3. System Architecture
- Frontend (React + Vite): user interface for authentication, symptom input, chat, vision upload, and timeline views.
- Backend (FastAPI): API orchestration for auth, symptoms, chat, health, and vision modules.
- Data Layer (MongoDB + Redis): persistent records and session/context caching.
- AI Layer:
  - Disease and dengue models for tabular symptom/lab features.
  - RAG retriever for medical context enrichment.
  - Vision module for skin/lab image interpretation.

## 4. Implemented Modules
- Auth module: register/login/profile/forgot-reset flows.
- Symptoms module: logging, prediction, history, latest records.
- Chat module: context-aware responses with page-level isolation.
- Vision module: skin and lab-report analysis APIs.
- Health module: timeline, alerts, summary.

## 5. Key Engineering Improvements
- Strong mode-based chat isolation to prevent cross-page context bleed.
- One-time cache schema migration to remove legacy mixed cache behavior.
- Production cleanup of frontend debug instrumentation.
- Better conversational formatting for short greetings and natural replies.
- Fallback reset verification flow when SMTP is unavailable.

## 6. AI Methodology
- Supervised ML handles deterministic disease/dengue risk scoring.
- LLM is used for explanation and conversational guidance.
- RAG retrieval injects medical context to reduce generic responses.
- Prompt policy separates conversational-only replies from health-structured guidance.

## 7. Testing and Validation
- Local backend run verified with FastAPI startup.
- API smoke scripts available under scripts.
- Frontend checks confirm no blocking compile errors after production cleanup.
- Model performance references are maintained in backend model evaluation JSON files.

## 8. Deployment Readiness
- Backend containerization available with Dockerfile and compose setup.
- Frontend build/deploy path available via Vercel.
- Azure deployment steps and custom domain planning documented separately.

## 9. Security and Safety Considerations
- JWT-based auth and protected API routes.
- Rate limit and cache controls in backend core utilities.
- Medical disclaimer enforced in product messaging.
- Sensitive environment variables externalized via .env.

## 10. Limitations and Future Work
- Add clinical partner validation and stronger medical governance loop.
- Expand multilingual support quality with strict translation QA.
- Add observability stack and formal SLOs for production operations.
- Introduce model drift monitoring and periodic retraining pipeline.

## 11. Conclusion
NirovaAI demonstrates an end-to-end AI health support platform suitable for a capstone deliverable and cloud deployment. The final build prioritizes practical utility, modular engineering, and safer AI interaction while keeping room for clinical and operational expansion.
