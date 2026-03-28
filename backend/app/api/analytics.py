"""
Analytics API endpoints for health insights dashboard
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import datetime, timedelta
import logging

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.analytics import (
    HealthAnalyticsEngine,
    health_analytics,
    HealthMetricsRequest,
    HealthRiskProfile,
    HealthTrendAnalysis,
    PersonalizedInsight,
    HealthInsightDashboard,
    HealthRiskLevel
)

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["analytics"])


async def fetch_user_health_data(db, user_id: str, days: int):
    """Fetch user's health data from database"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Fetch symptom logs
    symptom_logs = await db["symptom_logs"].find(
        {
            "user_id": user_id,
            "created_at": {"$gte": cutoff_date}
        },
        {"_id": 0}
    ).to_list(length=None)
    
    # Fetch diagnoses/predictions
    diagnoses = await db["health_timeline"].find(
        {
            "user_id": user_id,
            "created_at": {"$gte": cutoff_date}
        },
        {"_id": 0}
    ).to_list(length=None)
    
    # Fetch medications (if stored)
    medications = await db["medications"].find(
        {"user_id": user_id},
        {"_id": 0}
    ).to_list(length=None)
    
    return symptom_logs, diagnoses, medications


# Endpoints

@router.get("/health-metrics")
async def get_health_metrics(
    days: int = Query(30, ge=7, le=365, description="Analysis period in days"),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Calculate comprehensive health metrics for user
    
    Analyzes:
    - Symptom frequency and patterns
    - Severity trends
    - Temporal patterns (time of day, day of week, seasonal)
    - Comorbidity detection
    """
    user_id = current_user["_id"]
    
    symptom_logs, diagnoses, medications = await fetch_user_health_data(db, user_id, days)
    
    if not symptom_logs:
        log.info(f"No health data found for user {user_id} in last {days} days")
        return {
            "status": "insufficient_data",
            "message": f"No health records in last {days} days",
            "user_id": user_id,
            "period_days": days
        }
    
    metrics = await health_analytics.calculate_health_metrics(
        symptom_logs=symptom_logs,
        diagnoses=diagnoses,
        medications=medications
    )
    
    log.info(f"Calculated health metrics for user {user_id}")
    
    return {
        "user_id": user_id,
        "period_days": days,
        "period_start": datetime.utcnow() - timedelta(days=days),
        "period_end": datetime.utcnow(),
        "metrics": metrics,
        "generated_at": datetime.utcnow()
    }


@router.get("/health-score")
async def get_health_score(
    days: int = Query(30, ge=7, le=365),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Get overall health score (0-100)
    
    Higher = better health. Based on:
    - Symptom severity and frequency
    - Trend direction
    - Comorbidity risk
    - Age and medication count
    """
    user_id = current_user["_id"]
    
    symptom_logs, diagnoses, medications = await fetch_user_health_data(db, user_id, days)
    
    if not symptom_logs:
        return {
            "user_id": user_id,
            "health_score": 85,  # Good baseline for no symptoms
            "risk_level": "low",
            "message": "No recent health concerns recorded"
        }
    
    metrics = await health_analytics.calculate_health_metrics(
        symptom_logs=symptom_logs,
        diagnoses=diagnoses,
        medications=medications
    )
    
    # Get user's age for risk adjustment
    user_doc = await db["users"].find_one({"_id": user_id}, {"age": 1})
    age = user_doc.get("age") if user_doc else None
    medical_history = user_doc.get("medical_history") if user_doc else None
    
    risk_profile = health_analytics.calculate_health_risk_score(metrics, age, medical_history)
    health_score = health_analytics.calculate_health_score(metrics, risk_profile)
    
    log.info(f"Calculated health score for user {user_id}: {health_score}")
    
    return {
        "user_id": user_id,
        "health_score": health_score,
        "risk_level": risk_profile.severity,
        "risk_score": risk_profile.score,
        "recommendation": risk_profile.recommendation,
        "generated_at": datetime.utcnow()
    }


@router.get("/risk-assessment")
async def get_risk_assessment(
    days: int = Query(30, ge=7, le=365),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Get detailed health risk assessment
    
    Returns:
    - Overall risk level (low, moderate, high, critical)
    - Risk score (0-100)
    - Contributing factors
    - Specific recommendations
    - Urgent action items if needed
    """
    user_id = current_user["_id"]
    
    symptom_logs, diagnoses, medications = await fetch_user_health_data(db, user_id, days)
    
    if not symptom_logs:
        return {
            "user_id": user_id,
            "risk_level": "low",
            "risk_score": 15,
            "contributing_factors": [],
            "recommendations": ["Continue regular health monitoring"],
            "professional_consultation_needed": False
        }
    
    metrics = await health_analytics.calculate_health_metrics(
        symptom_logs=symptom_logs,
        diagnoses=diagnoses,
        medications=medications
    )
    
    user_doc = await db["users"].find_one({"_id": user_id}, {"age": 1, "medical_history": 1})
    age = user_doc.get("age") if user_doc else None
    medical_history = user_doc.get("medical_history") if user_doc else None
    
    risk_profile = health_analytics.calculate_health_risk_score(metrics, age, medical_history)
    
    # Generate recommendations based on risk level
    recommendations = []
    urgent_actions = []
    
    if risk_profile.severity == HealthRiskLevel.CRITICAL:
        urgent_actions = [
            "Seek immediate medical attention",
            "Document current symptoms in detail",
            "Prepare list of medications and allergies",
            "Contact emergency services if symptoms worsen"
        ]
    elif risk_profile.severity == HealthRiskLevel.HIGH:
        recommendations = [
            "Schedule doctor's appointment urgently",
            "Monitor symptoms closely",
            "Track medication adherence",
            "Maintain health diary"
        ]
    elif risk_profile.severity == HealthRiskLevel.MODERATE:
        recommendations = [
            "Schedule routine health check-up",
            "Continue current treatments",
            "Regular symptom monitoring",
            "Healthy lifestyle practices"
        ]
    else:
        recommendations = [
            "Continue healthy lifestyle",
            "Regular exercise recommended",
            "Balanced diet and adequate sleep",
            "Regular check-ups"
        ]
    
    log.info(f"Generated risk assessment for user {user_id}: {risk_profile.severity}")
    
    return {
        "user_id": user_id,
        "risk_level": risk_profile.severity,
        "risk_score": risk_profile.score,
        "recommendation": risk_profile.recommendation,
        "general_recommendations": recommendations,
        "urgent_actions": urgent_actions if urgent_actions else None,
        "professional_consultation_needed": risk_profile.severity in [HealthRiskLevel.HIGH, HealthRiskLevel.CRITICAL],
        "generated_at": datetime.utcnow()
    }


@router.get("/trend-analysis")
async def get_trend_analysis(
    days: int = Query(30, ge=7, le=365),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Get health trend analysis
    
    Shows:
    - Top recurring symptoms
    - Trend direction (improving, stable, worsening)
    - Symptom frequency ranking
    - Temporal patterns
    - Improvement metrics
    """
    user_id = current_user["_id"]
    
    symptom_logs, _, _ = await fetch_user_health_data(db, user_id, days)
    
    if not symptom_logs:
        return {
            "user_id": user_id,
            "status": "insufficient_data",
            "message": f"No symptom data in last {days} days"
        }
    
    metrics = await health_analytics.calculate_health_metrics(
        symptom_logs=symptom_logs,
        diagnoses=[],
        medications=[]
    )
    
    symptom_freq = metrics.get("symptom_frequency_analysis", {})
    temporal = metrics.get("temporal_patterns", {})
    severity = metrics.get("severity_trends", {})
    
    # Format top symptoms
    top_symptoms = []
    for symptom, data in list(symptom_freq.items())[:5]:
        top_symptoms.append({
            "symptom": symptom,
            "occurrences": data["frequency"],
            "average_severity": data["average_severity"],
            "trend": data["trend"],
            "percentage": data["percentage"],
            "last_reported": data["last_reported"]
        })
    
    log.info(f"Generated trend analysis for user {user_id}")
    
    return {
        "user_id": user_id,
        "period_days": days,
        "period_start": datetime.utcnow() - timedelta(days=days),
        "period_end": datetime.utcnow(),
        "total_symptoms_logged": metrics["total_symptoms_logged"],
        "top_symptoms": top_symptoms,
        "overall_trend": severity.get("severity_trend", "unknown"),
        "improvement_percentage": severity.get("improvement_percentage", 0),
        "average_severity": severity.get("average_severity", 0),
        "temporal_patterns": {
            "worst_day": max(temporal.get("day_of_week", {}), default=None, key=lambda k: temporal["day_of_week"][k]),
            "days_per_week": dict(temporal.get("day_of_week", {})),
            "hours_by_frequency": temporal.get("hour_of_day", {}),
            "seasonal_distribution": temporal.get("seasonal", {})
        },
        "generated_at": datetime.utcnow()
    }


@router.get("/personalized-insights")
async def get_personalized_insights(
    days: int = Query(30, ge=7, le=365),
    language: str = Query("en", description="Language for insights (en, bn)"),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Get ML-generated personalized health insights
    
    Includes:
    - Pattern warnings
    - Positive trends
    - Temporal insights
    - Risk-based recommendations
    - Actionable next steps
    """
    user_id = current_user["_id"]
    
    symptom_logs, diagnoses, medications = await fetch_user_health_data(db, user_id, days)
    
    if not symptom_logs:
        return {
            "user_id": user_id,
            "insights": [],
            "message": "Not enough data to generate insights"
        }
    
    metrics = await health_analytics.calculate_health_metrics(
        symptom_logs=symptom_logs,
        diagnoses=diagnoses,
        medications=medications
    )
    
    user_doc = await db["users"].find_one({"_id": user_id}, {"age": 1, "medical_history": 1})
    age = user_doc.get("age") if user_doc else None
    medical_history = user_doc.get("medical_history") if user_doc else None
    
    risk_profile = health_analytics.calculate_health_risk_score(metrics, age, medical_history)
    
    insights = await health_analytics.generate_personalized_insights(
        user_id=user_id,
        metrics=metrics,
        risk_profile=risk_profile,
        language=language
    )
    
    log.info(f"Generated {len(insights)} personalized insights for user {user_id}")
    
    return {
        "user_id": user_id,
        "num_insights": len(insights),
        "insights": [
            {
                "type": insight.insight_type,
                "title": insight.title,
                "description": insight.description,
                "severity": insight.severity,
                "actions": insight.action_items,
                "confidence": insight.confidence,
                "generated_at": insight.generated_at
            }
            for insight in insights
        ],
        "language": language,
        "generated_at": datetime.utcnow()
    }


@router.get("/dashboard")
async def get_health_insights_dashboard(
    days: int = Query(30, ge=7, le=365),
    language: str = Query("en"),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Get complete health insights dashboard
    
    Combines all analytics into one comprehensive view:
    - Health score and risk assessment
    - Trend analysis
    - Personalized insights
    - Recommendations and next steps
    """
    user_id = current_user["_id"]
    
    symptom_logs, diagnoses, medications = await fetch_user_health_data(db, user_id, days)
    
    if not symptom_logs:
        return {
            "user_id": user_id,
            "status": "insufficient_data",
            "health_score": None,
            "message": f"No health data in last {days} days. Start tracking symptoms to get insights."
        }
    
    # Calculate all components
    metrics = await health_analytics.calculate_health_metrics(
        symptom_logs=symptom_logs,
        diagnoses=diagnoses,
        medications=medications
    )
    
    user_doc = await db["users"].find_one({"_id": user_id}, {"age": 1, "medical_history": 1})
    age = user_doc.get("age") if user_doc else None
    medical_history = user_doc.get("medical_history") if user_doc else None
    
    risk_profile = health_analytics.calculate_health_risk_score(metrics, age, medical_history)
    health_score = health_analytics.calculate_health_score(metrics, risk_profile)
    insights = await health_analytics.generate_personalized_insights(
        user_id, metrics, risk_profile, language
    )
    
    # Format response
    log.info(f"Generated complete health dashboard for user {user_id}")
    
    return {
        "user_id": user_id,
        "generated_at": datetime.utcnow(),
        "period": {
            "start": (datetime.utcnow() - timedelta(days=days)).isoformat(),
            "end": datetime.utcnow().isoformat(),
            "days": days
        },
        "health_score": health_score,
        "risk_assessment": {
            "level": risk_profile.severity,
            "score": risk_profile.score,
            "recommendation": risk_profile.recommendation
        },
        "trend_summary": {
            "direction": metrics.get("severity_trends", {}).get("severity_trend", "unknown"),
            "improvement": metrics.get("severity_trends", {}).get("improvement_percentage", 0),
            "top_symptoms": list(
                dict(sorted(
                    metrics.get("symptom_frequency_analysis", {}).items(),
                    key=lambda x: x[1]["frequency"],
                    reverse=True
                )).keys()
            )[:3]
        },
        "insights": [
            {
                "type": i.insight_type,
                "title": i.title,
                "description": i.description,
                "severity": i.severity,
                "actions": i.action_items
            }
            for i in insights
        ],
        "next_steps": [
            "Review personalized insights above",
            "Track daily symptoms consistently",
            "Follow medication schedule if applicable",
            "Schedule check-up if recommended"
        ],
        "language": language
    }


@router.get("/health-check")
async def analytics_health_check() -> dict:
    """Health check for analytics service"""
    return {
        "status": "healthy",
        "service": "health_analytics",
        "features": [
            "symptom_frequency_analysis",
            "severity_trends",
            "temporal_patterns",
            "comorbidity_detection",
            "risk_scoring",
            "personalized_insights",
            "health_score_calculation"
        ],
        "timestamp": datetime.utcnow(),
        "message": "Analytics engine ready for health insights"
    }
