"""
Advanced Analytics & Health Insights Engine for NirovaAI BD Edition
Provides comprehensive health trend analysis, risk scoring, and actionable insights
Optimized for Bangladesh healthcare context and common tropical diseases
"""
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from enum import Enum
import statistics
import logging
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

# Bangladesh-specific health conditions and prevalence
BD_HEALTH_CONDITIONS = {
    "dengue": {"prevalence": "high", "season": "monsoon", "risk_factor": 25},
    "malaria": {"prevalence": "moderate", "season": "year-round", "risk_factor": 20},
    "typhoid": {"prevalence": "moderate", "season": "pre-monsoon", "risk_factor": 15},
    "diarrhea": {"prevalence": "very_high", "season": "monsoon", "risk_factor": 30},
    "pneumonia": {"prevalence": "high", "season": "winter", "risk_factor": 20},
    "respiratory_infection": {"prevalence": "very_high", "season": "winter", "risk_factor": 25},
    "skin_infection": {"prevalence": "high", "season": "summer", "risk_factor": 15},
    "asthma": {"prevalence": "moderate", "season": "year-round", "risk_factor": 18},
    "hypertension": {"prevalence": "moderate", "season": "year-round", "risk_factor": 20},
    "diabetes": {"prevalence": "moderate", "season": "year-round", "risk_factor": 22},
}


class HealthRiskLevel(str, Enum):
    """Health risk severity levels"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class TrendDirection(str, Enum):
    """Trend direction indicators"""
    IMPROVING = "improving"
    STABLE = "stable"
    WORSENING = "worsening"
    UNKNOWN = "unknown"


# Request/Response Models
class HealthMetricsRequest(BaseModel):
    """Request health metrics calculation"""
    user_id: str
    period_days: int = Field(default=30, ge=7, le=365, description="Analysis period in days")
    include_predictions: bool = Field(default=True, description="Include ML trend predictions")


class SymptomFrequency(BaseModel):
    """Symptom frequency statistics"""
    symptom: str
    occurrence_count: int
    percentage: float
    last_reported: datetime
    severity_average: float
    trend: TrendDirection


class RiskIndicator(BaseModel):
    """Individual health risk indicator"""
    indicator: str
    score: float  # 0-100
    severity: HealthRiskLevel
    recommendation: str
    last_updated: datetime


class HealthRiskProfile(BaseModel):
    """Overall health risk assessment"""
    user_id: str
    overall_risk: HealthRiskLevel
    risk_score: float  # 0-100
    contributing_factors: List[RiskIndicator]
    recommendations: List[str]
    urgent_actions: Optional[List[str]] = None
    professional_consultation_needed: bool


class HealthTrendAnalysis(BaseModel):
    """Health trend analytics"""
    period_start: datetime
    period_end: datetime
    symptoms_tracked: int
    top_symptoms: List[SymptomFrequency]
    trend_direction: TrendDirection
    improvement_metrics: Dict[str, float]
    seasonal_patterns: Optional[Dict[str, Any]] = None


class PersonalizedInsight(BaseModel):
    """ML-generated personalized health insight"""
    insight_type: str  # prediction, warning, opportunity, pattern
    title: str
    description: str
    severity: HealthRiskLevel
    action_items: List[str]
    confidence: float  # 0.0-1.0
    data_points_used: int
    generated_at: datetime


class HealthInsightDashboard(BaseModel):
    """Complete health insights dashboard"""
    user_id: str
    generated_at: datetime
    period: Dict[str, datetime]
    
    risk_profile: HealthRiskProfile
    trend_analysis: HealthTrendAnalysis
    personalized_insights: List[PersonalizedInsight]
    health_score: float  # 0-100
    comparison_to_peers: Dict[str, float]
    next_checkup_recommended: Optional[datetime] = None


class HealthAnalyticsEngine:
    """Advanced analytics for health insights and predictions"""
    
    def __init__(self):
        self.symptom_db = {}
        self.risk_thresholds = {
            HealthRiskLevel.LOW: (0, 30),
            HealthRiskLevel.MODERATE: (30, 60),
            HealthRiskLevel.HIGH: (60, 80),
            HealthRiskLevel.CRITICAL: (80, 100),
        }
    
    async def calculate_health_metrics(
        self,
        symptom_logs: List[Dict],
        diagnoses: List[Dict],
        medications: Optional[List[Dict]] = None,
    ) -> Dict:
        """
        Calculate comprehensive health metrics from user data
        
        Args:
            symptom_logs: User's symptom history
            diagnoses: Disease predictions/diagnoses
            medications: Current medications
        
        Returns:
            Comprehensive health metrics
        """
        if not symptom_logs:
            return {"status": "insufficient_data", "message": "Not enough health data"}
        
        metrics = {
            "total_symptoms_logged": len(symptom_logs),
            "total_diagnoses": len(diagnoses),
            "active_medications": len(medications) if medications else 0,
            "symptom_frequency_analysis": await self._analyze_symptom_frequency(symptom_logs),
            "temporal_patterns": await self._analyze_temporal_patterns(symptom_logs),
            "severity_trends": await self._analyze_severity_trends(symptom_logs),
            "comorbidity_patterns": await self._detect_comorbidities(diagnoses),
        }
        
        return metrics
    
    async def _analyze_symptom_frequency(self, symptom_logs: List[Dict]) -> Dict:
        """Analyze how frequently each symptom appears"""
        frequency_map = {}
        
        for log in symptom_logs:
            symptom = log.get("main_symptom", "unknown")
            if symptom not in frequency_map:
                frequency_map[symptom] = {
                    "count": 0,
                    "severities": [],
                    "dates": [],
                    "last_date": None
                }
            
            frequency_map[symptom]["count"] += 1
            severity = log.get("severity", 5)
            frequency_map[symptom]["severities"].append(severity)
            reported_date = log.get("created_at", datetime.utcnow())
            frequency_map[symptom]["dates"].append(reported_date)
            frequency_map[symptom]["last_date"] = reported_date
        
        # Calculate statistics
        analyzed = {}
        for symptom, data in frequency_map.items():
            avg_severity = statistics.mean(data["severities"]) if data["severities"] else 0
            analyzed[symptom] = {
                "frequency": data["count"],
                "average_severity": round(avg_severity, 1),
                "last_reported": data["last_date"],
                "trend": self._calculate_trend(data["severities"]),
                "percentage": round((data["count"] / len(symptom_logs)) * 100, 1)
            }
        
        # Sort by frequency
        return dict(sorted(analyzed.items(), key=lambda x: x[1]["frequency"], reverse=True))
    
    async def _analyze_temporal_patterns(self, symptom_logs: List[Dict]) -> Dict:
        """Detect temporal patterns (time of day, day of week, seasonal)"""
        if not symptom_logs:
            return {}
        
        patterns = {
            "day_of_week": {},
            "hour_of_day": {},
            "seasonal": {}
        }
        
        for log in symptom_logs:
            date = log.get("created_at", datetime.utcnow())
            
            # Day of week analysis
            day_name = date.strftime("%A")
            patterns["day_of_week"][day_name] = patterns["day_of_week"].get(day_name, 0) + 1
            
            # Hour of day analysis
            hour = date.hour
            patterns["hour_of_day"][hour] = patterns["hour_of_day"].get(hour, 0) + 1
            
            # Seasonal analysis
            month = date.month
            season = self._get_season(month)
            patterns["seasonal"][season] = patterns["seasonal"].get(season, 0) + 1
        
        return patterns
    
    def _get_season(self, month: int) -> str:
        """Get season from month"""
        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        else:
            return "autumn"
    
    async def _analyze_severity_trends(self, symptom_logs: List[Dict]) -> Dict:
        """Analyze severity trends over time"""
        if not symptom_logs:
            return {}
        
        # Sort by date
        sorted_logs = sorted(symptom_logs, key=lambda x: x.get("created_at", datetime.utcnow()))
        
        # Calculate moving average of severity (7-day window)
        severities = [log.get("severity", 5) for log in sorted_logs]
        moving_avg = []
        window = 7
        
        for i in range(len(severities)):
            window_start = max(0, i - window + 1)
            window_data = severities[window_start:i+1]
            moving_avg.append(statistics.mean(window_data))
        
        trend = self._calculate_trend(severities)
        
        return {
            "average_severity": round(statistics.mean(severities), 1),
            "min_severity": min(severities),
            "max_severity": max(severities),
            "severity_trend": trend,
            "moving_average": [round(x, 1) for x in moving_avg],
            "improvement_percentage": self._calculate_improvement(severities)
        }
    
    def _calculate_trend(self, values: List[float]) -> TrendDirection:
        """Calculate trend direction from values"""
        if len(values) < 2:
            return TrendDirection.UNKNOWN
        
        # Compare first half to second half
        mid = len(values) // 2
        first_half_avg = statistics.mean(values[:mid]) if mid > 0 else values[0]
        second_half_avg = statistics.mean(values[mid:])
        
        difference = first_half_avg - second_half_avg
        
        if difference > 2:  # Improvement threshold
            return TrendDirection.IMPROVING
        elif difference < -2:  # Worsening threshold
            return TrendDirection.WORSENING
        else:
            return TrendDirection.STABLE
    
    def _calculate_improvement(self, values: List[float]) -> float:
        """Calculate improvement percentage"""
        if len(values) < 2:
            return 0.0
        
        first_val = statistics.mean(values[:len(values)//2]) if len(values) > 1 else values[0]
        last_val = statistics.mean(values[len(values)//2:])
        
        if first_val == 0:
            return 0.0
        
        improvement = ((first_val - last_val) / first_val) * 100
        return round(max(-50, min(50, improvement)), 1)  # Cap at ±50%
    
    async def _detect_comorbidities(self, diagnoses: List[Dict]) -> Dict:
        """Detect co-occurring condition patterns"""
        if not diagnoses:
            return {}
        
        # Extract disease names
        diseases = [d.get("disease_name") for d in diagnoses if d.get("disease_name")]
        
        return {
            "unique_conditions": len(set(diseases)),
            "total_diagnoses": len(diseases),
            "most_common": max(set(diseases), key=diseases.count) if diseases else None,
            "comorbidity_risk": "high" if len(set(diseases)) > 3 else "moderate" if len(set(diseases)) > 1 else "low"
        }
    
    def calculate_health_risk_score(
        self,
        metrics: Dict,
        age: Optional[int] = None,
        medical_history: Optional[List[str]] = None
    ) -> RiskIndicator:
        """
        Calculate overall health risk score (0-100)
        
        Args:
            metrics: Health metrics from calculate_health_metrics
            age: User's age (used for risk adjustment)
            medical_history: List of past conditions
        
        Returns:
            Overall risk indicator
        """
        score = 0
        factors = []
        
        # Symptom frequency risk (0-30 points)
        symptom_freq = metrics.get("symptom_frequency_analysis", {})
        if symptom_freq:
            max_freq = max([d.get("frequency", 0) for d in symptom_freq.values()], default=0)
            freq_score = min(30, (max_freq / 20) * 30)  # Scale to 30 points max
            score += freq_score
            if freq_score > 15:
                factors.append("High symptom frequency detected")
        
        # Severity analysis (0-30 points)
        severity_data = metrics.get("severity_trends", {})
        avg_severity = severity_data.get("average_severity", 0)
        severity_score = (avg_severity / 10) * 30  # 10 is max severity
        score += severity_score
        if avg_severity > 6:
            factors.append("High symptom severity detected")
        
        # Trend analysis (0-20 points)
        trend = severity_data.get("severity_trend")
        if trend == TrendDirection.WORSENING:
            score += 20
            factors.append("Health condition appears to be worsening")
        elif trend == TrendDirection.IMPROVING:
            score = max(0, score - 10)  # Reduce risk for improvement
        
        # Comorbidity risk (0-20 points)
        comorbidity_risk = metrics.get("comorbidity_patterns", {}).get("comorbidity_risk", "low")
        if comorbidity_risk == "high":
            score += 20
            factors.append("Multiple conditions detected (comorbidity risk)")
        elif comorbidity_risk == "moderate":
            score += 10
        
        # Age adjustment (if provided)
        if age and age > 60:
            score = min(100, score * 1.2)
            factors.append(f"Age-adjusted risk (age {age})")
        
        # Medication count
        med_count = metrics.get("active_medications", 0)
        if med_count > 5:
            score = min(100, score * 1.1)
            factors.append(f"Multiple medications ({med_count} active)")
        
        # Determine severity level
        severity = HealthRiskLevel.LOW
        if score >= 80:
            severity = HealthRiskLevel.CRITICAL
        elif score >= 60:
            severity = HealthRiskLevel.HIGH
        elif score >= 30:
            severity = HealthRiskLevel.MODERATE
        
        return RiskIndicator(
            indicator="overall_health_risk",
            score=round(score, 1),
            severity=severity,
            recommendation=self._get_risk_recommendation(severity, factors),
            last_updated=datetime.utcnow()
        )
    
    def _get_risk_recommendation(self, severity: HealthRiskLevel, factors: List[str]) -> str:
        """Get recommendation based on risk level"""
        recommendations = {
            HealthRiskLevel.LOW: "Continue healthy lifestyle. Regular check-ups recommended.",
            HealthRiskLevel.MODERATE: "Consider scheduling a doctor's appointment for evaluation.",
            HealthRiskLevel.HIGH: "Recommend urgent medical consultation. Track symptoms closely.",
            HealthRiskLevel.CRITICAL: "Seek immediate medical attention. Document all symptoms.",
        }
        return recommendations.get(severity, "Consult healthcare provider.")
    
    async def generate_personalized_insights(
        self,
        user_id: str,
        metrics: Dict,
        risk_profile: RiskIndicator,
        language: str = "en"
    ) -> List[PersonalizedInsight]:
        """
        Generate ML-based personalized health insights
        
        Args:
            user_id: User ID
            metrics: Health metrics
            risk_profile: Risk assessment
            language: Language for insights
        
        Returns:
            List of personalized insights
        """
        insights = []
        
        # Insight 1: Symptom pattern warning
        symptom_freq = metrics.get("symptom_frequency_analysis", {})
        if symptom_freq:
            top_symptom = next(iter(symptom_freq.items()))[0]
            top_data = symptom_freq[top_symptom]
            
            if top_data["frequency"] > 5:
                insights.append(PersonalizedInsight(
                    insight_type="warning",
                    title=f"Recurring {top_symptom} Pattern",
                    description=f"You've reported {top_symptom} {top_data['frequency']} times in the analyzed period.",
                    severity=HealthRiskLevel.MODERATE if top_data["frequency"] < 10 else HealthRiskLevel.HIGH,
                    action_items=[
                        f"Schedule appointment to discuss persistent {top_symptom}",
                        f"Track {top_symptom} severity and duration",
                        f"Note any triggers or patterns"
                    ],
                    confidence=0.85,
                    data_points_used=top_data["frequency"],
                    generated_at=datetime.utcnow()
                ))
        
        # Insight 2: Trend insight
        severity_trend = metrics.get("severity_trends", {}).get("severity_trend")
        if severity_trend == TrendDirection.IMPROVED:
            insights.append(PersonalizedInsight(
                insight_type="positive_opportunity",
                title="Health Improvement Detected",
                description="Your symptoms show an improving trend. Continue current health practices.",
                severity=HealthRiskLevel.LOW,
                action_items=[
                    "Maintain current health behaviors",
                    "Continue any treatments prescribed",
                    "Regular monitoring recommended"
                ],
                confidence=0.9,
                data_points_used=len(metrics.get("severity_trends", {}).get("moving_average", [])),
                generated_at=datetime.utcnow()
            ))
        
        # Insight 3: Temporal pattern insight
        temporal = metrics.get("temporal_patterns", {})
        day_patterns = temporal.get("day_of_week", {})
        if day_patterns:
            worst_day = max(day_patterns, key=day_patterns.get)
            insights.append(PersonalizedInsight(
                insight_type="pattern",
                title=f"Symptom Pattern on {worst_day}s",
                description=f"You tend to report symptoms more frequently on {worst_day}s.",
                severity=HealthRiskLevel.MODERATE,
                action_items=[
                    f"Review activities/stressors on {worst_day}s",
                    f"Plan preventive measures for {worst_day}s",
                    f"Note environment/behavior changes on {worst_day}s"
                ],
                confidence=0.75,
                data_points_used=day_patterns[worst_day],
                generated_at=datetime.utcnow()
            ))
        
        return insights
    
    def calculate_health_score(self, metrics: Dict, risk_profile: RiskIndicator) -> float:
        """
        Calculate overall health score (0-100)
        Higher score = better health
        
        Args:
            metrics: Health metrics
            risk_profile: Risk assessment
        
        Returns:
            Health score 0-100
        """
        # Inverse of risk score
        health_score = 100 - risk_profile.score
        
        # Bonus for improvement trend
        severity_trend = metrics.get("severity_trends", {}).get("severity_trend")
        if severity_trend == TrendDirection.IMPROVING:
            health_score = min(100, health_score + 10)
        elif severity_trend == TrendDirection.WORSENING:
            health_score = max(0, health_score - 10)
        
        return round(health_score, 1)


# Singleton instance
health_analytics = HealthAnalyticsEngine()


async def get_health_analytics() -> HealthAnalyticsEngine:
    """FastAPI dependency for health analytics"""
    return health_analytics
