"""
NirovaAI — Dengue Classifier (Model 2)
========================================
Trained on real Bangladesh hospital data (kawsarahmad dataset):
- 1000 real Dhaka patients
- Binary: Dengue Positive or Negative
doctors use to diagnose dengue in clinical practice.

Features needed:
- NS1: NS1 antigen test result (0 or 1)
- IgG: IgG antibody test result (0 or 1)
- IgM: IgM antibody test result (0 or 1)
- Age: patient age (number)
- Gender: 0=female, 1=male
- Area, AreaType, HouseType, District: location info (0-indexed)

Files needed in backend/app/models/:
- dengue_classifier.pkl
- dengue_feature_columns.json
"""

import numpy as np
import json
import os
import logging
from pathlib import Path

log = logging.getLogger(__name__)

_model = None
_feature_columns = None
_is_loaded = False


def _resolve_models_dir(required_files: list[str]) -> str:
    here = Path(__file__).resolve()

    candidates = [
        here.parents[2] / "models",
        here.parents[3] / "models",
        Path("/app/models"),
        Path.cwd() / "models",
    ]

    for cand in candidates:
        try:
            if cand.exists() and all((cand / f).exists() for f in required_files):
                return str(cand)
        except Exception:
            continue

    return str(candidates[0])


def load_dengue_model():
    """Load the dengue classifier from disk"""
    global _model, _feature_columns, _is_loaded

    models_dir = _resolve_models_dir([
        "dengue_classifier.pkl",
        "dengue_feature_columns.json",
    ])

    pkl_path  = os.path.join(models_dir, "dengue_classifier.pkl")
    cols_path = os.path.join(models_dir, "dengue_feature_columns.json")

    if not os.path.exists(pkl_path):
        raise FileNotFoundError(f"dengue_classifier.pkl not found in {models_dir}")

    import joblib
    _model = joblib.load(pkl_path)

    with open(cols_path) as f:
        _feature_columns = json.load(f)

    _is_loaded = True
    log.info(f"Dengue model loaded: features={_feature_columns}")


def predict_dengue(feature_values: dict) -> dict:
    """
    Predict dengue from lab test results.

    Args:
        feature_values: dict with keys matching dengue_feature_columns.json
                       e.g. {"NS1": 1, "IgG": 0, "IgM": 0, "Age": 25, ...}

    Returns:
        Prediction result with probability and recommended action
    """
    if _is_loaded and _model:
        try:
            return _run_model(feature_values)
        except Exception as e:
            log.warning(f"Dengue model failed: {e}, using rule-based fallback")

    return _rule_based(feature_values)


def _run_model(feature_values: dict) -> dict:
    """Run the XGBoost dengue classifier"""
    # Build feature vector in correct order
    features = np.zeros(len(_feature_columns), dtype=np.float32)
    for i, col in enumerate(_feature_columns):
        if col in feature_values:
            features[i] = float(feature_values[col])

    probabilities = _model.predict_proba([features])[0]
    prediction = int(_model.predict([features])[0])
    dengue_probability = float(probabilities[1])  # probability of being positive

    return _format_result(prediction, dengue_probability)



def _rule_based(feature_values: dict) -> dict:
    """Fallback without external APIs."""
    ns1 = int(bool(feature_values.get("NS1", 0)))
    igm = int(bool(feature_values.get("IgM", 0)))
    igg = int(bool(feature_values.get("IgG", 0)))

    is_positive = bool(ns1 or igm)
    probability = 0.85 if ns1 else (0.7 if igm else (0.25 if igg else 0.15))

    if is_positive and probability >= 0.8:
        urgency = "urgent"
        action = "High suspicion of dengue. See a doctor today and get CBC/platelets follow-up."
    elif is_positive:
        urgency = "high"
        action = "Possible dengue. Please visit a doctor and consider NS1/IgM testing."
    else:
        urgency = "low"
        action = "Low dengue likelihood from provided values; monitor symptoms and seek care if worsening."

    return {
        "result": "Dengue Positive" if is_positive else "Dengue Negative",
        "is_dengue_positive": is_positive,
        "probability": round(float(probability), 3),
        "probability_percent": f"{round(float(probability) * 100, 1)}%",
        "urgency": urgency,
        "recommended_action": action,
        "clinical_note": "Rule-based fallback (model unavailable).",
        "model": "Rule-based fallback",
        "disclaimer": "This does not replace professional medical consultation, diagnosis, or treatment",
    }


def _format_result(prediction: int, probability: float) -> dict:
    """Format dengue prediction into consistent response"""
    is_positive = prediction == 1

    if is_positive and probability >= 0.8:
        action = "High probability of dengue. See a doctor TODAY and request blood test"
        urgency = "urgent"
    elif is_positive:
        action = "Possible dengue. Please visit a doctor and get NS1 antigen test"
        urgency = "high"
    else:
        action = "Low dengue probability. Continue monitoring symptoms"
        urgency = "low"

    return {
        "result": "Dengue Positive" if is_positive else "Dengue Negative",
        "is_dengue_positive": is_positive,
        "probability": round(probability, 3),
        "probability_percent": f"{round(probability * 100, 1)}%",
        "urgency": urgency,
        "recommended_action": action,
        "clinical_note": "IgG and NS1 tests are most reliable for dengue diagnosis in Bangladesh",
        "model": "XGBoost model" if _is_loaded else "Rule-based fallback",
        "disclaimer": "এই সেবা কেবল তথ্যগত সহায়তা দেয়; এটি নিবন্ধিত চিকিৎসকের পরামর্শ, রোগ নির্ণয় বা চিকিৎসার বিকল্প নয়। "
                  "This does not replace professional medical consultation, diagnosis, or treatment"
    }
