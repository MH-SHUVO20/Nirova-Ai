# Capstone Project Proposal

## Project Title
NirovaAI: AI-Powered Early Disease Detection and Health Support for Bangladesh

## Problem Statement
Bangladesh faces a high burden of preventable health complications due to delayed symptom interpretation, limited access to specialists in rural areas, and low continuity in day-to-day health tracking. People often ignore early warning symptoms or cannot quickly connect those symptoms to possible conditions. This delay increases treatment cost and risk.

## Proposed Solution
NirovaAI is a bilingual (Bangla + English) AI health assistant that helps users:
- Log and monitor symptoms over time.
- Get ML-based risk predictions for common diseases and dengue.
- Receive context-aware chat guidance grounded in medical references.
- Analyze skin images and lab report images for supportive interpretation.
- Track timeline summaries and alerts for early action.

## Key Objectives
- Build a production-ready full-stack health support platform.
- Integrate traditional ML + LLM + retrieval (RAG) in one workflow.
- Ensure safer AI output through structured formatting and disclaimer boundaries.
- Support Bangladesh-focused usage with local language and context.

## Core Features
- Authentication and secure user profile management.
- Symptom logging and prediction endpoint.
- Dengue-focused specialized model with local feature set.
- AI chat with page-specific context isolation.
- Skin image and lab report analysis pipeline.
- Health timeline and summary APIs.

## Technology Stack
- Frontend: React, Vite, Tailwind.
- Backend: FastAPI, Python.
- Data: MongoDB, Redis.
- AI: XGBoost models, ONNX vision pipeline, RAG retriever, LLM routing.
- DevOps: Docker and Azure-ready deployment flow.

## Expected Outcomes
- Faster early warning and better symptom awareness.
- Improved health decision support for non-expert users.
- A practical capstone demonstrating real-world AI system integration.

## Scope and Limitations
- NirovaAI is informational and not a replacement for licensed doctors.
- Predictions are decision-support signals, not clinical diagnosis.
- Requires internet and backend model availability for full functionality.

## Evaluation Plan
- Functional testing of all user flows.
- Model validation based on existing evaluation artifacts.
- End-to-end API smoke tests.
- Deployment validation on cloud infrastructure.
