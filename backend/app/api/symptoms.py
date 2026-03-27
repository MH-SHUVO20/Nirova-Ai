"""
NirovaAI — Symptoms API
========================
Endpoints:
- POST /symptoms/log      → log daily symptoms + instant ML prediction
- POST /symptoms/predict  → predict disease (with optional dengue lab values)
- GET  /symptoms/history  → get your symptom history
- GET  /symptoms/latest   → get your most recent log
"""

from fastapi import APIRouter, Depends, Request, Query
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional
from app.core.database import symptom_logs, alerts, users, symptom_analyses
from app.core.auth import get_current_user
from app.core.redis_client import cache_get, cache_set
from app.ai.ml.disease_model import predict_disease
from app.ai.ml.dengue_model import predict_dengue
from app.core.rate_limit import limiter
from datetime import datetime
import hashlib
import json
import logging
import os

router = APIRouter(prefix="/symptoms", tags=["Symptoms"])
log = logging.getLogger(__name__)

SYMPTOM_ALIASES = {
    "diarrhea": "diarrhoea",
    "shortness_of_breath": "breathlessness",
    "rash": "skin_rash",
}


def _normalize_symptoms(symptoms: List[str]) -> List[str]:
    normalized = []
    for symptom in symptoms:
        clean = symptom.strip().lower().replace(" ", "_")
        normalized.append(SYMPTOM_ALIASES.get(clean, clean))
    # Preserve order while removing duplicates.
    return list(dict.fromkeys(normalized))


async def _store_symptom_analysis(
    *,
    user_id,
    symptoms: List[str],
    analysis_mode: str,
    disease_prediction: Optional[dict],
    dengue_prediction: Optional[dict],
    extra: Optional[dict] = None,
) -> None:
    """Persist every symptom analysis result for longitudinal chat context."""
    try:
        payload = {
            "user_id": user_id,
            "analysis_mode": analysis_mode,
            "symptoms": symptoms or [],
            "disease_prediction": disease_prediction,
            "dengue_prediction": dengue_prediction,
            "created_at": datetime.utcnow(),
        }
        if extra:
            payload["meta"] = extra
        await symptom_analyses().insert_one(payload)
    except Exception as exc:
        log.warning(f"Could not save symptom analysis history: {exc}")


# Load valid symptoms
try:
    symptom_file = os.path.join(os.path.dirname(__file__), "..", "models", "symptom_columns.json")
    with open(symptom_file, "r") as f:
        VALID_SYMPTOMS = set(json.load(f))
except Exception as e:
    import logging
    logging.getLogger(__name__).warning(f"Failed to load symptom_columns.json: {e}")
    VALID_SYMPTOMS = set()

# ── Request Models ──

class SymptomLogRequest(BaseModel):
    symptoms: List[str]               # e.g. ["fever", "headache", "joint_pain"]
    severity: int = Field(5, ge=1, le=10) # 1-10 scale (1=mild, 10=severe)
    notes: str = ""                   # any additional notes from the patient
    district: Optional[str] = None   # patient's district for geographic tracking

    @field_validator('symptoms')
    def validate_symptoms(cls, v):
        v = _normalize_symptoms(v)
        if VALID_SYMPTOMS:
            invalid = [s for s in v if s not in VALID_SYMPTOMS]
            if invalid:
                raise ValueError(f"Invalid symptoms: {', '.join(invalid)}")
        return v

class PredictRequest(BaseModel):
    symptoms: List[str]
    # Optional dengue lab values — triggers Model 2 if provided
    ns1_result: Optional[int] = None  # NS1 antigen test: 0=negative, 1=positive
    igg_result: Optional[int] = None  # IgG antibody: 0=negative, 1=positive
    igm_result: Optional[int] = None  # IgM antibody: 0=negative, 1=positive
    age: Optional[int] = None
    district: Optional[str] = None

    @field_validator('symptoms')
    def validate_symptoms(cls, v):
        v = _normalize_symptoms(v)
        if VALID_SYMPTOMS:
            invalid = [s for s in v if s not in VALID_SYMPTOMS]
            if invalid:
                raise ValueError(f"Invalid symptoms: {', '.join(invalid)}")
        return v

    @field_validator("ns1_result", "igg_result", "igm_result")
    def validate_binary_values(cls, v):
        if v is None:
            return v
        if v not in (0, 1):
            raise ValueError("Lab values must be 0 or 1")
        return v


class DenguePredictRequest(BaseModel):
    symptoms: List[str] = []
    ns1_result: Optional[int] = None
    igg_result: Optional[int] = None
    igm_result: Optional[int] = None
    age: Optional[int] = None
    district: Optional[str] = None

    @field_validator('symptoms')
    def validate_symptoms(cls, v):
        v = _normalize_symptoms(v)
        if VALID_SYMPTOMS:
            invalid = [s for s in v if s not in VALID_SYMPTOMS]
            if invalid:
                raise ValueError(f"Invalid symptoms: {', '.join(invalid)}")
        return v

    @field_validator("ns1_result", "igg_result", "igm_result")
    def validate_binary_values(cls, v):
        if v is None:
            return v
        if v not in (0, 1):
            raise ValueError("Lab values must be 0 or 1")
        return v

    @model_validator(mode="after")
    def require_any_lab_value(self):
        if self.ns1_result is None and self.igg_result is None and self.igm_result is None:
            raise ValueError("Provide at least one lab value (NS1, IgG, or IgM)")
        return self


# ── Endpoints ──

@router.post("/log")
@limiter.limit("10/minute")
async def log_symptoms(
    request: Request,
    data: SymptomLogRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Log today's symptoms and get an instant disease prediction.
    This is the core feature — called every day by active users.
    """
    user_id = current_user["_id"]

    # Run ML prediction immediately
    prediction = predict_disease(data.symptoms)

    # Save to MongoDB
    log_entry = {
        "user_id": user_id,
        "symptoms": data.symptoms,
        "severity": data.severity,
        "notes": data.notes,
        "district": data.district or current_user.get("district", "Dhaka"),
        "risk_score": prediction.get("confidence", 0.0),
        "predicted_disease": prediction.get("predicted_disease"),
        "triage_color": prediction.get("triage_color", "green"),
        "ai_analysis": {
            "analysis_mode": "log",
            "disease_prediction": prediction,
            "saved_at": datetime.utcnow(),
        },
        "date": datetime.utcnow()
    }

    result = await symptom_logs().insert_one(log_entry)
    log_id = str(result.inserted_id)

    # Create a health alert if risk is high
    if prediction.get("confidence", 0) >= 0.7:
        await alerts().insert_one({
            "user_id": user_id,
            "disease": prediction.get("predicted_disease"),
            "probability": prediction.get("confidence"),
            "recommended_action": prediction.get("recommended_action"),
            "resolved": False,
            "created_at": datetime.utcnow()
        })
        log.info(f"High-risk alert created for user {user_id}: {prediction.get('predicted_disease')}")

    # Update user's total log count
    await users().update_one(
        {"_id": user_id},
        {"$inc": {"total_symptom_logs": 1}}
    )

    await _store_symptom_analysis(
        user_id=user_id,
        symptoms=data.symptoms,
        analysis_mode="log",
        disease_prediction=prediction,
        dengue_prediction=None,
        extra={"severity": data.severity, "district": log_entry["district"]},
    )

    return {
        "success": True,
        "log_id": log_id,
        "message": "Symptoms logged successfully",
        "prediction": prediction,
        "high_risk_alert": prediction.get("confidence", 0) >= 0.7
    }


@router.post("/predict")
@limiter.limit("10/minute")
async def predict(
    request: Request,
    data: PredictRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a disease prediction without saving to history.
    If NS1/IgG/IgM values are provided, also runs the dengue-specific model.
    """
    # Cache key must include all model-affecting inputs.
    normalized_symptoms = sorted(_normalize_symptoms(data.symptoms))
    cache_payload = {
        "user_id": str(current_user["_id"]),
        "symptoms": normalized_symptoms,
        "ns1_result": data.ns1_result,
        "igg_result": data.igg_result,
        "igm_result": data.igm_result,
        "age": data.age,
        "district": data.district,
    }
    cache_key = f"predict:{hashlib.sha256(json.dumps(cache_payload, sort_keys=True).encode()).hexdigest()[:24]}"
    cached = await cache_get(cache_key)
    if cached:
        return {"prediction": cached, "from_cache": True}

    # Always run general disease classifier
    disease_result = predict_disease(normalized_symptoms)

    # Run dengue-specific model if lab values were provided
    dengue_result = None
    has_lab_values = any([
        data.ns1_result is not None,
        data.igg_result is not None,
        data.igm_result is not None
    ])

    if has_lab_values:
        dengue_inputs = {
            "NS1": data.ns1_result or 0,
            "IgG": data.igg_result or 0,
            "IgM": data.igm_result or 0,
            "Age": data.age or 25,
            "Gender": 1,
            "Area": 0,
            "AreaType": 0,
            "HouseType": 0,
            "District": 0
        }
        dengue_result = predict_dengue(dengue_inputs)

    response = {
        "disease_prediction": disease_result,
        "dengue_prediction": dengue_result,
        "has_lab_values": has_lab_values,
        "symptoms_analyzed": normalized_symptoms
    }

    await _store_symptom_analysis(
        user_id=current_user["_id"],
        symptoms=normalized_symptoms,
        analysis_mode="predict",
        disease_prediction=disease_result,
        dengue_prediction=dengue_result,
        extra={"age": data.age, "district": data.district, "has_lab_values": has_lab_values},
    )

    # Cache for 1 hour
    await cache_set(cache_key, response, ttl_seconds=3600)

    return {"prediction": response, "from_cache": False}


@router.post("/predict-dengue")
@limiter.limit("10/minute")
async def predict_dengue_only(
    request: Request,
    data: DenguePredictRequest,
    current_user: dict = Depends(get_current_user)
):
    """Dedicated dengue prediction endpoint for dengue feature page."""
    cache_payload = {
        "user_id": str(current_user["_id"]),
        "symptoms": data.symptoms,
        "ns1_result": data.ns1_result,
        "igg_result": data.igg_result,
        "igm_result": data.igm_result,
        "age": data.age,
        "district": data.district,
    }
    cache_key = f"predict_dengue:{hashlib.sha256(json.dumps(cache_payload, sort_keys=True).encode()).hexdigest()[:24]}"
    cached = await cache_get(cache_key)
    if cached:
        return {"prediction": cached, "from_cache": True}

    dengue_inputs = {
        "NS1": data.ns1_result or 0,
        "IgG": data.igg_result or 0,
        "IgM": data.igm_result or 0,
        "Age": data.age or current_user.get("age") or 25,
        "Gender": 1,
        "Area": 0,
        "AreaType": 0,
        "HouseType": 0,
        "District": 0
    }
    dengue_result = predict_dengue(dengue_inputs)
    response = {
        "dengue_prediction": dengue_result,
        "symptoms_considered": data.symptoms,
        "lab_inputs_used": {
            "ns1_result": data.ns1_result,
            "igg_result": data.igg_result,
            "igm_result": data.igm_result,
        },
    }

    await _store_symptom_analysis(
        user_id=current_user["_id"],
        symptoms=data.symptoms,
        analysis_mode="dengue_only",
        disease_prediction=None,
        dengue_prediction=dengue_result,
        extra={"lab_inputs_used": response["lab_inputs_used"], "age": data.age, "district": data.district},
    )
    await cache_set(cache_key, response, ttl_seconds=3600)
    return {"prediction": response, "from_cache": False}


@router.get("/history")
async def get_history(
    limit: int = Query(default=30, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Get your symptom history (most recent first)"""
    cursor = symptom_logs().find(
        {"user_id": current_user["_id"]}
    ).sort("date", -1).limit(limit)

    history = []
    async for entry in cursor:
        history.append({
            "id": str(entry["_id"]),
            "symptoms": entry.get("symptoms", []),
            "severity": entry.get("severity", 0),
            "risk_score": entry.get("risk_score", 0.0),
            "predicted_disease": entry.get("predicted_disease"),
            "triage_color": entry.get("triage_color", "green"),
            "notes": entry.get("notes", ""),
            "date": entry["date"].isoformat() if entry.get("date") else None
        })

    return {
        "total_logs": len(history),
        "history": history
    }


@router.get("/latest")
async def get_latest(current_user: dict = Depends(get_current_user)):
    """Get your most recent symptom log"""
    latest = await symptom_logs().find_one(
        {"user_id": current_user["_id"]},
        sort=[("date", -1)]
    )

    if not latest:
        return {"message": "No symptoms logged yet. Start tracking your health!"}

    return {
        "id": str(latest["_id"]),
        "symptoms": latest.get("symptoms", []),
        "severity": latest.get("severity", 0),
        "risk_score": latest.get("risk_score", 0.0),
        "predicted_disease": latest.get("predicted_disease"),
        "triage_color": latest.get("triage_color", "green"),
        "date": latest["date"].isoformat() if latest.get("date") else None
    }
