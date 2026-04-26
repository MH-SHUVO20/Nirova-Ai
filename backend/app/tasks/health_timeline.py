"""
NirovaAI Health Timeline Aggregation
=====================================
Aggregate user health data into daily, weekly, and monthly timelines
for trend analysis and longitudinal health tracking.
"""

from datetime import datetime, timedelta
from bson import ObjectId
from app.core.database import (
    symptom_logs,
    timeline,
)
import logging

log = logging.getLogger(__name__)


async def aggregate_user_health(user_id: ObjectId, lookback_days: int = 90):
    """
    Aggregate user symptom data into health timeline for trend analysis.
    Called periodically (daily) to build historical records.
    """
    try:
        # Calculate date range
        now = datetime.utcnow()
        start_date = now - timedelta(days=lookback_days)
        
        # Get all symptom logs in period
        symptom_cursor = symptom_logs().find({
            "user_id": user_id,
            "created_at": {"$gte": start_date, "$lte": now}
        }).sort("created_at", 1)
        
        symptom_records = []
        async for log_entry in symptom_cursor:
            symptom_records.append(log_entry)
        
        if not symptom_records:
            log.debug(f"No symptom data for user {user_id} in last {lookback_days} days")
            return
        
        # Group by week
        weekly_summaries = _group_by_week(symptom_records)
        
        # Calculate trends
        trends = _calculate_trends(weekly_summaries)
        
        # Store weekly aggregation
        week_key = _get_week_key(now)
        await timeline().update_one(
            {
                "user_id": user_id,
                "week": week_key,
                "aggregation_type": "weekly"
            },
            {
                "$set": {
                    "user_id": user_id,
                    "week": week_key,
                    "aggregation_type": "weekly",
                    "summary": {
                        "total_logs": len(symptom_records),
                        "symptom_frequency": _get_symptom_frequency(symptom_records),
                        "average_severity": _calculate_average_severity(symptom_records),
                        "risk_scores": [r.get("risk_score", 0) for r in symptom_records],
                        "predominant_symptoms": _get_top_symptoms(symptom_records, top_n=5),
                    },
                    "trends": trends,
                    "last_updated": datetime.utcnow(),
                }
            },
            upsert=True
        )
        
        log.info(f"Aggregated health timeline for user {user_id}: {len(symptom_records)} symptom logs")
        return len(symptom_records)
        
    except Exception as e:
        log.error(f"Error aggregating health timeline for user {user_id}: {e}", exc_info=True)
        return None


def _get_week_key(dt: datetime) -> str:
    """ISO week string (YYYY-W##)"""
    iso_year, iso_week, _ = dt.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def _group_by_week(records: list) -> dict:
    """Group symptom records by week"""
    weekly = {}
    for record in records:
        week_key = _get_week_key(record.get("created_at", datetime.utcnow()))
        if week_key not in weekly:
            weekly[week_key] = []
        weekly[week_key].append(record)
    return weekly


def _calculate_average_severity(records: list) -> float:
    """Calculate mean severity score"""
    if not records:
        return 0.0
    severities = [r.get("severity", 5) for r in records]
    return sum(severities) / len(severities)


def _get_symptom_frequency(records: list) -> dict:
    """Count frequency of each symptom"""
    frequency = {}
    for record in records:
        for symptom in record.get("symptoms", []):
            frequency[symptom] = frequency.get(symptom, 0) + 1
    return frequency


def _get_top_symptoms(records: list, top_n: int = 5) -> list:
    """Get top N most frequent symptoms"""
    freq = _get_symptom_frequency(records)
    sorted_symptoms = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [{"symptom": s[0], "count": s[1]} for s in sorted_symptoms[:top_n]]


def _calculate_trends(weekly_summaries: dict) -> dict:
    """Calculate trend direction and statistics"""
    weeks = sorted(weekly_summaries.keys())
    if len(weeks) < 2:
        return {"trend": "insufficient_data", "weeks_analyzed": len(weeks)}
    
    # Calculate average severity per week
    severity_by_week = []
    for week_key in weeks:
        records = weekly_summaries[week_key]
        avg_sev = _calculate_average_severity(records)
        severity_by_week.append((week_key, avg_sev))
    
    # Determine trend
    if len(severity_by_week) >= 2:
        latest_avg = severity_by_week[-1][1]
        prev_avg = severity_by_week[-2][1]
        
        if latest_avg < prev_avg * 0.8:
            trend = "improving"
        elif latest_avg > prev_avg * 1.2:
            trend = "worsening"
        else:
            trend = "stable"
    else:
        trend = "unknown"
    
    return {
        "trend": trend,
        "weeks_analyzed": len(weeks),
        "latest_severity": severity_by_week[-1][1] if severity_by_week else None,
        "previous_severity": severity_by_week[-2][1] if len(severity_by_week) >= 2 else None,
        "severity_history": severity_by_week,
    }


async def get_user_health_timeline(
    user_id: ObjectId,
    period: str = "7d"  # 7d, 30d, 90d
) -> dict:
    """
    Retrieve aggregated health timeline for a user.
    
    Args:
        user_id: User MongoDB ID
        period: "7d" (last week), "30d" (last month), or "90d" (last quarter)
    
    Returns: Aggregated health trend data and summaries
    """
    try:
        lookback_map = {
            "7d": 7,
            "30d": 30,
            "90d": 90,
        }
        lookback_days = lookback_map.get(period, 30)
        
        # Get raw data
        start_date = datetime.utcnow() - timedelta(days=lookback_days)
        
        symptom_cursor = symptom_logs().find({
            "user_id": user_id,
            "created_at": {"$gte": start_date}
        }).sort("created_at", -1)
        
        records = []
        async for record in symptom_cursor:
            records.append({
                "date": record.get("created_at").isoformat(),
                "symptoms": record.get("symptoms", []),
                "severity": record.get("severity", 5),
                "risk_score": record.get("risk_score", 0),
            })
        
        # Aggregate
        weekly = _group_by_week(records)
        trends = _calculate_trends(weekly)
        
        return {
            "user_id": str(user_id),
            "period": period,
            "total_entries": len(records),
            "timespan_days": lookback_days,
            "data_points": records,
            "trends": trends,
            "top_symptoms": _get_top_symptoms(records, top_n=5),
            "average_severity": _calculate_average_severity(records),
            "statistics": {
                "min_severity": min([r["severity"] for r in records]) if records else None,
                "max_severity": max([r["severity"] for r in records]) if records else None,
                "avg_severity": _calculate_average_severity(records),
            }
        }
    except Exception as e:
        log.error(f"Error retrieving health timeline for user {user_id}: {e}")
        return {
            "error": True,
            "message": "Could not retrieve health timeline",
            "user_id": str(user_id),
        }
