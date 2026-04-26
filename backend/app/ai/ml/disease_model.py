# Disease prediction model using XGBoost

import asyncio
import json
import logging
import os
from typing import List

import numpy as np

from app.ai.llm_router import get_llm_response

log = logging.getLogger(__name__)

_model = None
_class_names = None
_symptom_columns = None
_is_loaded = False


def load_disease_model():
    """Load disease classifier from disk"""
    global _model, _class_names, _symptom_columns, _is_loaded

    here = os.path.dirname(__file__)
    candidate_dirs = [
        os.path.abspath(os.path.join(here, "../../models")),   # backend/app/models (current layout)
        os.path.abspath(os.path.join(here, "../../../models")),  # backend/models (legacy layout)
    ]

    models_dir = None
    for path in candidate_dirs:
        classes_path = os.path.join(path, "class_names.json")
        columns_path = os.path.join(path, "symptom_columns.json")
        if os.path.exists(classes_path) and os.path.exists(columns_path):
            models_dir = path
            break

    if not models_dir:
        raise FileNotFoundError(
            "Missing class_names.json or symptom_columns.json in expected model directories: "
            + ", ".join(candidate_dirs)
        )

    pkl_path     = os.path.join(models_dir, "disease_classifier.pkl")
    classes_path = os.path.join(models_dir, "class_names.json")
    columns_path = os.path.join(models_dir, "symptom_columns.json")

    with open(classes_path) as f:
        _class_names = json.load(f)

    with open(columns_path) as f:
        _symptom_columns = json.load(f)

    if not os.path.exists(pkl_path):
        raise FileNotFoundError(f"disease_classifier.pkl not found in {models_dir}")

    import joblib
    _model = joblib.load(pkl_path)
    _is_loaded = True
    log.info(f"Disease model loaded: {len(_class_names)} diseases")



def predict_disease(symptoms: List[str]) -> dict:
    """Predict disease from list of symptoms"""
    if _is_loaded and _model:
        try:
            return _run_model(symptoms)
        except Exception as e:
            log.warning(f"Model prediction failed: {e}, using fallback")

    # Use LLM for fallback/emergency suggestions
    prompt = [
        {"role": "system", "content": "You are a medical triage and emergency drug suggestion AI for Bangladesh. Given a list of symptoms, provide the most likely disease, triage color (red/yellow/green), confidence (0-1), emergency drug suggestions (if any), and a recommended action. If symptoms are severe, prioritize emergency care and safe OTC drugs only. Respond in JSON with keys: predicted_disease, confidence, triage_color, emergency_drug_suggestions (list), recommended_action, disclaimer."},
        {"role": "user", "content": f"Symptoms: {', '.join(symptoms)}"}
    ]
    try:
        llm_result = asyncio.run(get_llm_response(prompt))
        import json
        return json.loads(llm_result)
    except Exception as e:
        log.error(f"LLM fallback failed: {e}")
        return {
            "predicted_disease": "Unable to predict",
            "confidence": 0.0,
            "triage_color": "red",
            "emergency_drug_suggestions": [],
            "recommended_action": "Seek emergency care immediately.",
            "disclaimer": "AI fallback failed. Please consult a doctor."
        }


def _run_model(symptoms: List[str]) -> dict:
    """Run the ML model to predict disease"""
    features = np.zeros(len(_symptom_columns), dtype=np.float32)
    matched_symptoms = []

    for symptom in symptoms:
        clean = symptom.lower().strip().replace(" ", "_")

        if clean in _symptom_columns:
            features[_symptom_columns.index(clean)] = 1.0
            matched_symptoms.append(clean)
        else:
            # Try partial matching for typos or variations
            for col in _symptom_columns:
                if clean in col or col in clean:
                    features[_symptom_columns.index(col)] = 1.0
                    matched_symptoms.append(col)
                    break

    probabilities = _model.predict_proba([features])[0]
    predicted_idx = int(np.argmax(probabilities))
    confidence = float(probabilities[predicted_idx])
    top3_indices = np.argsort(probabilities)[::-1][:3]
    top3 = [
        {"disease": _class_names[i], "probability": round(float(probabilities[i]), 3)}
        for i in top3_indices
    ]

    disease_name = _class_names[predicted_idx] if predicted_idx < len(_class_names) else "Unknown"
    return _format_result(disease_name, confidence, top3, matched_symptoms)

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


