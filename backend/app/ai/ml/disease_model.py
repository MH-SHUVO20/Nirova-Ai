# Disease prediction model using XGBoost

import numpy as np
import json
import os
import logging
from pathlib import Path
from typing import List

log = logging.getLogger(__name__)

_model = None
_class_names = None
_symptom_columns = None
_symptom_to_index = {}
_is_loaded = False


def _resolve_models_dir(required_files: list[str]) -> str:
    here = Path(__file__).resolve()

    candidates = [
        # Typical local layout: backend/app/models
        here.parents[2] / "models",
        # Alternate layout: backend/models
        here.parents[3] / "models",
        # Docker compose volume: /app/models
        Path("/app/models"),
        # Fallback: cwd/models
        Path.cwd() / "models",
    ]

    for cand in candidates:
        try:
            if cand.exists() and all((cand / f).exists() for f in required_files):
                return str(cand)
        except Exception:
            continue

    # Default to the most likely location for error messages
    return str(candidates[0])


def load_disease_model():
    """Load disease classifier from disk"""
    global _model, _class_names, _symptom_columns, _symptom_to_index, _is_loaded

    models_dir = _resolve_models_dir([
        "disease_classifier.pkl",
        "class_names.json",
        "symptom_columns.json",
    ])

    pkl_path     = os.path.join(models_dir, "disease_classifier.pkl")
    classes_path = os.path.join(models_dir, "class_names.json")
    columns_path = os.path.join(models_dir, "symptom_columns.json")

    if not os.path.exists(classes_path) or not os.path.exists(columns_path):
        raise FileNotFoundError(
            f"Missing class_names.json or symptom_columns.json in {models_dir}"
        )

    with open(classes_path) as f:
        _class_names = json.load(f)

    with open(columns_path) as f:
        _symptom_columns = json.load(f)
    _symptom_to_index = {name: idx for idx, name in enumerate(_symptom_columns)}

    if not os.path.exists(pkl_path):
        raise FileNotFoundError(f"disease_classifier.pkl not found in {models_dir}")

    import joblib
    _model = joblib.load(pkl_path)
    _is_loaded = True
    log.info(f"Disease model loaded: {len(_class_names)} diseases")



def _basic_fallback(symptoms: List[str]) -> dict:
    normalized = {s.lower().strip().replace(" ", "_") for s in symptoms}
    severe_flags = {
        "difficulty_breathing",
        "shortness_of_breath",
        "chest_pain",
        "severe_abdominal_pain",
        "bleeding",
        "unconscious",
        "confusion",
        "seizure",
    }

    triage = "red" if (normalized & severe_flags) else "yellow"
    action = "Seek urgent medical care immediately." if triage == "red" else "Monitor closely and see a doctor if symptoms worsen."

    return {
        "predicted_disease": "Unknown (model unavailable)",
        "confidence": 0.0,
        "triage_color": triage,
        "recommended_action": action,
        "top3_predictions": [],
        "symptoms_recognized": [],
        "model": "Fallback",
        "disclaimer": "This does not replace professional medical consultation, diagnosis, or treatment.",
    }


def predict_disease(symptoms: List[str]) -> dict:
    """Predict disease from list of symptoms"""
    if _is_loaded and _model:
        try:
            return _run_model(symptoms)
        except Exception as e:
            log.warning(f"Model prediction failed: {e}, using fallback")

    return _basic_fallback(symptoms)


def _run_model(symptoms: List[str]) -> dict:
    """Run the ML model to predict disease"""
    features = np.zeros(len(_symptom_columns), dtype=np.float32)
    matched_symptoms = []

    for symptom in symptoms:
        clean = symptom.lower().strip().replace(" ", "_")
        matched = _match_symptom_column(clean)
        if not matched:
            continue
        features[_symptom_to_index[matched]] = 1.0
        matched_symptoms.append(matched)

    if not matched_symptoms:
        fallback = _basic_fallback(symptoms)
        fallback["recommended_action"] = (
            "Symptoms were not recognized by the clinical model. "
            "Try selecting standard symptom names or add more details."
        )
        fallback["model"] = "Fallback (no matched symptoms)"
        return fallback

    probabilities = _model.predict_proba([features])[0]
    predicted_idx = int(np.argmax(probabilities))
    confidence = float(probabilities[predicted_idx])
    sorted_indices = np.argsort(probabilities)[::-1]
    second_confidence = float(probabilities[sorted_indices[1]]) if len(sorted_indices) > 1 else 0.0
    confidence_margin = confidence - second_confidence
    top3_indices = np.argsort(probabilities)[::-1][:3]
    top3 = [
        {"disease": _resolve_disease_label(i), "probability": round(float(probabilities[i]), 3)}
        for i in top3_indices
    ]

    disease_name = _resolve_disease_label(predicted_idx)
    # Guardrail: avoid alarming disease labels when model signal is weak/flat.
    if confidence < 0.40 or (confidence < 0.50 and confidence_margin < 0.08) or len(matched_symptoms) < 2:
        return {
            "predicted_disease": "Inconclusive (need more symptom detail)",
            "confidence": round(confidence, 3),
            "triage_color": "yellow",
            "recommended_action": (
                "Current symptom pattern is insufficient for a reliable condition label. "
                "Track additional symptoms and seek clinician review if worsening."
            ),
            "top3_predictions": top3,
            "symptoms_recognized": matched_symptoms,
            "model": "XGBoost model (low-confidence guardrail)",
            "disclaimer": "This does not replace professional medical consultation, diagnosis, or treatment.",
        }

    return _format_result(disease_name, confidence, top3, matched_symptoms)


def _resolve_disease_label(index: int) -> str:
    """Resolve disease label using model classes when available."""
    try:
        if hasattr(_model, "classes_"):
            cls = _model.classes_[index]
            if isinstance(cls, (int, np.integer)):
                i = int(cls)
                if 0 <= i < len(_class_names):
                    return str(_class_names[i])
            return str(cls)
    except Exception:
        pass
    if _class_names and 0 <= index < len(_class_names):
        return str(_class_names[index])
    return "Unknown"


def _match_symptom_column(clean_symptom: str) -> str | None:
    """Resolve an input symptom to a known model column."""
    if clean_symptom in _symptom_columns:
        return clean_symptom
    # Try partial matching for typos or variations.
    for col in _symptom_columns:
        if clean_symptom in col or col in clean_symptom:
            return col
    return None


## _rule_based_predict removed: now handled by LLM fallback


def _format_result(disease: str, confidence: float, top3: list, matched: list) -> dict:
    """Format prediction into standard response"""
    if confidence >= 0.7:
        triage = "red"
        action = "Please see a doctor today"
    elif confidence >= 0.5:
        triage = "yellow"
        action = "Monitor your symptoms and see a doctor if they worsen"
    else:
        triage = "green"
        action = "Rest, stay hydrated, and monitor your symptoms"

    return {
        "predicted_disease": disease,
        "confidence": round(confidence, 3),
        "triage_color": triage,
        "recommended_action": action,
        "top3_predictions": top3,
        "symptoms_recognized": matched,
        "model": "XGBoost model" if _is_loaded else "Rule-based fallback",
        "disclaimer": "এই সেবা কেবল তথ্যগত সহায়তা দেয়; এটি নিবন্ধিত চিকিৎসকের পরামর্শ, রোগ নির্ণয় বা চিকিৎসার বিকল্প নয়। "
                  "This does not replace professional medical consultation, diagnosis, or treatment"
    }


