"""
NirovaAI — Health Timeline API
================================
Endpoints:
- GET  /health/timeline  → full history with charts data
- GET  /health/alerts    → active disease alerts
- GET  /health/summary   → AI monthly summary
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.database import symptom_logs, alerts
from app.core.auth import get_current_user
from app.ai.llm_router import get_llm_response, MEDICAL_SYSTEM_PROMPT
from datetime import datetime, timedelta
from bson import ObjectId
from bson.errors import InvalidId
import logging

router = APIRouter(prefix="/health", tags=["Health Timeline"])
log = logging.getLogger(__name__)


def _to_iso(value) -> str:
    """Safely convert datetime-ish values to ISO strings for API responses."""
    if value is None:
        return datetime.utcnow().isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str):
        return value
    try:
        return value.isoformat()
    except Exception:
        return datetime.utcnow().isoformat()


@router.get("/timeline")
async def get_timeline(
    days: int = Query(default=30, ge=1, le=365),
    current_user: dict = Depends(get_current_user)
):
    """Get full health timeline — used for charts in frontend"""
    user_id = current_user["_id"]
    since = datetime.utcnow() - timedelta(days=days)

    try:
        # Get symptom logs
        timeline_entries = []
        async for entry in symptom_logs().find(
            {"user_id": user_id, "date": {"$gte": since}}
        ).sort("date", 1):
            timeline_entries.append({
                "date": _to_iso(entry.get("date") or entry.get("created_at")),
                "symptoms": entry.get("symptoms", []),
                "severity": entry.get("severity", 0),
                "risk_score": entry.get("risk_score", 0.0),
                "predicted_disease": entry.get("predicted_disease"),
                "triage_color": entry.get("triage_color", "green")
            })

        # Get active alerts
        active_alerts = []
        async for alert in alerts().find(
            {"user_id": user_id, "resolved": False}
        ).sort("created_at", -1).limit(10):
            active_alerts.append({
                "id": str(alert["_id"]),
                "disease": alert.get("disease"),
                "probability": alert.get("probability", 0.0),
                "recommended_action": alert.get("recommended_action"),
                "created_at": _to_iso(alert.get("created_at"))
            })
    except Exception as exc:
        log.error(f"Failed to build health timeline for user {user_id}: {exc}")
        timeline_entries = []
        active_alerts = []

    # Calculate summary stats
    avg_severity = (
        sum(e["severity"] for e in timeline_entries) / len(timeline_entries)
        if timeline_entries else 0
    )
    max_risk = max(
        (e["risk_score"] for e in timeline_entries), default=0
    )

    return {
        "period_days": days,
        "timeline": timeline_entries,
        "active_alerts": active_alerts,
        "summary": {
            "total_logs": len(timeline_entries),
            "average_severity": round(avg_severity, 1),
            "max_risk_score": round(max_risk, 2),
            "active_alert_count": len(active_alerts)
        }
    }


@router.get("/alerts")
async def get_alerts(current_user: dict = Depends(get_current_user)):
    """Get all health alerts for the current user"""
    alert_list = []
    async for alert in alerts().find(
        {"user_id": current_user["_id"]}
    ).sort("created_at", -1):
        alert_list.append({
            "id": str(alert["_id"]),
            "disease": alert.get("disease"),
            "probability": alert.get("probability", 0.0),
            "recommended_action": alert.get("recommended_action"),
            "resolved": alert.get("resolved", False),
            "created_at": alert["created_at"].isoformat()
        })

    return {"alerts": alert_list, "total": len(alert_list)}


@router.patch("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Mark an alert as resolved"""
    try:
        alert_obj_id = ObjectId(alert_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=400, detail="Invalid alert id")

    result = await alerts().update_one(
        {"_id": alert_obj_id, "user_id": current_user["_id"]},
        {"$set": {"resolved": True, "resolved_at": datetime.utcnow()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Alert not found")

    return {
        "message": "Alert marked as resolved",
        "updated": result.modified_count > 0
    }


@router.get("/summary")
async def get_monthly_summary(current_user: dict = Depends(get_current_user)):
    """Get an AI-generated monthly health summary"""
    user_id = current_user["_id"]
    since = datetime.utcnow() - timedelta(days=30)

    # Count symptom frequency
    symptom_counts = {}
    async for entry in symptom_logs().find(
        {"user_id": user_id, "date": {"$gte": since}}
    ):
        for symptom in entry.get("symptoms", []):
            symptom_counts[symptom] = symptom_counts.get(symptom, 0) + 1

    if not symptom_counts:
        return {
            "summary": "No health data logged in the last 30 days. "
                      "Start logging your symptoms daily for personalized insights!"
        }

    # Get top symptoms
    top_symptoms = sorted(symptom_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    symptom_text = ", ".join([f"{s} ({n} times)" for s, n in top_symptoms])

    # Ask LLM for summary
    messages = [
        {"role": "system", "content": MEDICAL_SYSTEM_PROMPT},
        {"role": "user", "content":
         f"This patient logged these symptoms in the last 30 days: {symptom_text}. "
         f"Provide a brief health summary and recommendations in 3-4 sentences."}
    ]

    summary_text = await get_llm_response(messages)

    return {
        "summary": summary_text,
        "top_symptoms": [{"symptom": s, "count": n} for s, n in top_symptoms],
        "period": "Last 30 days"
    }
