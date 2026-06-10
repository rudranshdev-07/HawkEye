"""
Advanced risk scoring engine for HawkEye geospatial intelligence platform.

Uses multi-factor weighted scoring with normalization to produce stable,
explainable risk assessments (0-100 scale).
"""

import math
from typing import Dict, Tuple
from src.models import RiskLevel, RiskScoreComponents


# =============================================================================
# CONSTANTS & CALIBRATION
# =============================================================================

# Crime density thresholds (incidents per km radius)
CRIME_DENSITY_THRESHOLDS = {
    "critical": 50,      # >=50 crimes in 1km
    "high": 25,          # >=25 crimes in 1km
    "moderate": 10,      # >=10 crimes in 1km
    "low": 1             # >=1 crime in 1km
}

# Hotspot distance danger zones (kilometers)
HOTSPOT_DANGER_ZONES = {
    "immediate": 0.5,    # <0.5km: highest risk
    "close": 2.0,        # <2km: high risk
    "nearby": 5.0,       # <5km: moderate risk
    "far": float('inf')  # >=5km: minimal risk
}

# Severity weighting (normalized 0-1 scale)
SEVERITY_WEIGHTS = {
    "critical": 1.0,
    "high": 0.7,
    "moderate": 0.5,
    "low": 0.2
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def normalize_score(value: float, max_value: float, scale: float = 100.0) -> float:
    """
    Normalize a value to 0-scale range using exponential mapping for sensitivity.
    
    Args:
        value: Raw score value
        max_value: Maximum expected value for calibration
        scale: Output scale (default 100)
    
    Returns:
        Normalized score in [0, scale]
    """
    if max_value <= 0 or value <= 0:
        return 0.0
    
    # Use logarithmic scaling for better distribution
    normalized = (math.log1p(value) / math.log1p(max_value)) * scale
    return min(normalized, scale)


def calculate_density_score(
    crimes_1km: int,
    crimes_3km: int,
    crimes_5km: int
) -> Tuple[float, str]:
    """
    Calculate density component score based on crime concentration.
    
    Higher weight on crimes within 1km as they are most relevant.
    
    Args:
        crimes_1km: Number of crimes within 1km
        crimes_3km: Number of crimes within 3km
        crimes_5km: Number of crimes within 5km
    
    Returns:
        (density_score: 0-100, density_level: critical|high|moderate|low)
    """
    # Weighted density metric
    # 1km crimes are 4x more important than 5km crimes
    weighted_density = (
        crimes_1km * 1.0 +
        crimes_3km * 0.5 +
        crimes_5km * 0.15
    )
    
    # Determine density level
    if crimes_1km >= CRIME_DENSITY_THRESHOLDS["critical"]:
        density_level = "critical"
    elif crimes_1km >= CRIME_DENSITY_THRESHOLDS["high"]:
        density_level = "high"
    elif crimes_1km >= CRIME_DENSITY_THRESHOLDS["moderate"]:
        density_level = "moderate"
    else:
        density_level = "low"
    
    # Normalize to 0-100 scale using calibration point
    # At 50 crimes in 1km + context, we reach ~80 points
    density_score = normalize_score(
        weighted_density,
        max_value=60.0,
        scale=100.0
    )
    
    return min(density_score, 100.0), density_level


def calculate_hotspot_score(
    hotspot_distance_km: float,
    hotspot_rank: int = None,
    hotspot_incident_count: int = None
) -> Tuple[float, str]:
    """
    Calculate hotspot proximity component score.
    
    Proximity to detected crime hotspots significantly impacts risk.
    Rank multiplier amplifies the effect of being near top hotspots.
    
    Args:
        hotspot_distance_km: Distance to nearest hotspot
        hotspot_rank: Rank of nearest hotspot (1 is most severe)
        hotspot_incident_count: Number of incidents in hotspot
    
    Returns:
        (hotspot_score: 0-100, proximity_level: immediate|close|nearby|far)
    """
    if hotspot_distance_km >= HOTSPOT_DANGER_ZONES["nearby"]:
        base_score = 5.0
        proximity_level = "far"
    elif hotspot_distance_km >= HOTSPOT_DANGER_ZONES["close"]:
        base_score = 25.0
        proximity_level = "nearby"
    elif hotspot_distance_km >= HOTSPOT_DANGER_ZONES["immediate"]:
        base_score = 50.0
        proximity_level = "close"
    else:
        base_score = 80.0
        proximity_level = "immediate"
    
    # Rank multiplier: Top hotspots (rank 1-3) increase score more
    rank_multiplier = 1.0
    if hotspot_rank is not None:
        if hotspot_rank <= 3:
            rank_multiplier = 1.2
        elif hotspot_rank <= 5:
            rank_multiplier = 1.1
    
    hotspot_score = base_score * rank_multiplier
    
    return min(hotspot_score, 100.0), proximity_level


def calculate_severity_score(
    avg_severity: float,
    dominant_crime: str
) -> float:
    """
    Calculate severity component based on historical risk and crime type.
    
    Args:
        avg_severity: Historical severity average (0-10 scale)
        dominant_crime: Most common crime type in area
    
    Returns:
        severity_score: 0-100
    """
    # Base severity from historical data
    severity_normalized = min((avg_severity / 10.0) * 100.0, 100.0)
    
    # Crime type weighting
    violent_crimes = {"ASSAULT", "BATTERY", "ROBBERY", "WEAPONS VIOLATION"}
    property_crimes = {"BURGLARY", "MOTOR VEHICLE THEFT", "THEFT"}
    narcotics_crimes = {"NARCOTICS", "CRIMINAL DAMAGE"}
    
    crime_weight = 0.5  # Default
    if dominant_crime.upper() in violent_crimes:
        crime_weight = 1.0
    elif dominant_crime.upper() in property_crimes:
        crime_weight = 0.7
    elif dominant_crime.upper() in narcotics_crimes:
        crime_weight = 0.8
    
    # Combine historical and crime-type factors
    severity_score = severity_normalized * crime_weight * 0.7 + severity_normalized * 0.3
    
    return min(severity_score, 100.0)


def calculate_population_score(population_density: int) -> float:
    """
    Calculate population density component.
    
    Higher population density typically correlates with higher crime exposure.
    
    Args:
        population_density: People per square km
    
    Returns:
        population_score: 0-100
    """
    # Calibration: 5000 people/km² = moderate score
    # 50000+ people/km² = high score
    pop_normalized = min((population_density / 50000.0) * 100.0, 100.0)
    
    return pop_normalized


# =============================================================================
# PRIMARY SCORING FUNCTION
# =============================================================================

def calculate_risk_score(
    crimes_1km: int,
    crimes_3km: int,
    crimes_5km: int,
    hotspot_distance: float,
    avg_severity: float = 5.0,
    population_density: int = 10000,
    hotspot_rank: int = None,
    hotspot_incident_count: int = None,
    dominant_crime: str = "OTHER OFFENSE"
) -> Tuple[float, RiskScoreComponents]:
    """
    Calculate comprehensive risk score with component breakdown.
    
    Combines four major risk factors with intelligent weighting:
    1. Crime Density (45% weight) - most important
    2. Hotspot Proximity (30% weight) - structural risk
    3. Severity Profile (15% weight) - crime type/history
    4. Population Density (10% weight) - exposure
    
    Args:
        crimes_1km: Incidents within 1km
        crimes_3km: Incidents within 3km
        crimes_5km: Incidents within 5km
        hotspot_distance: Distance to nearest hotspot (km)
        avg_severity: Historical severity (0-10 scale)
        population_density: People per km²
        hotspot_rank: Rank of nearest hotspot
        hotspot_incident_count: Incidents in hotspot
        dominant_crime: Most common crime type
    
    Returns:
        (risk_score: 0-100, components: RiskScoreComponents breakdown)
    """
    
    # Calculate individual components
    density_score, _ = calculate_density_score(crimes_1km, crimes_3km, crimes_5km)
    hotspot_score, _ = calculate_hotspot_score(
        hotspot_distance,
        hotspot_rank,
        hotspot_incident_count
    )
    severity_score = calculate_severity_score(avg_severity, dominant_crime)
    population_score = calculate_population_score(population_density)
    
    # Weighted combination
    WEIGHTS = {
        "density": 0.45,
        "hotspot": 0.30,
        "severity": 0.15,
        "population": 0.10
    }
    
    final_score = (
        density_score * WEIGHTS["density"] +
        hotspot_score * WEIGHTS["hotspot"] +
        severity_score * WEIGHTS["severity"] +
        population_score * WEIGHTS["population"]
    )
    
    # Build component breakdown
    components = RiskScoreComponents(
        density_score=round(density_score, 2),
        hotspot_score=round(hotspot_score, 2),
        severity_score=round(severity_score, 2),
        population_score=round(population_score, 2)
    )
    
    return round(min(final_score, 100.0), 2), components


# =============================================================================
# RISK LEVEL CLASSIFICATION
# =============================================================================

def risk_level(score: float) -> str:
    """
    Classify numerical risk score into categorical level.
    
    Thresholds:
    - 0-20: Very Safe (minimal crime indicators)
    - 20-40: Safe (low risk)
    - 40-60: Moderate (balanced risk/safety)
    - 60-80: High Risk (elevated threat)
    - 80-100: Very High Risk (critical concern)
    
    Args:
        score: Risk score 0-100
    
    Returns:
        Risk level classification
    """
    if score < 20:
        return RiskLevel.VERY_SAFE.value
    elif score < 40:
        return RiskLevel.SAFE.value
    elif score < 60:
        return RiskLevel.MODERATE.value
    elif score < 80:
        return RiskLevel.HIGH_RISK.value
    else:
        return RiskLevel.VERY_HIGH_RISK.value


# =============================================================================
# SAFETY TIPS GENERATION
# =============================================================================

def generate_safety_tips(
    risk_score: float,
    dominant_crime: str,
    crimes_1km: int
) -> list:
    """
    Generate context-aware safety recommendations based on location risk profile.
    
    Args:
        risk_score: Numerical risk (0-100)
        dominant_crime: Most common crime type
        crimes_1km: Number of crimes within 1km
    
    Returns:
        List of SafetyTip dictionaries with icon, message, and priority
    """
    from src.models import SafetyTip
    
    tips = []
    
    # High-risk area warnings
    if risk_score >= 80:
        tips.append(SafetyTip(
            tip="🚨 CRITICAL RISK: Avoid this area, especially at night. Consider alternative routes.",
            icon="🚨",
            priority="high"
        ))
        tips.append(SafetyTip(
            tip="👥 Travel in groups if you must visit. Stay aware of surroundings.",
            icon="👥",
            priority="high"
        ))
    elif risk_score >= 60:
        tips.append(SafetyTip(
            tip="⚠️ HIGH RISK: Exercise heightened caution. Avoid isolated areas.",
            icon="⚠️",
            priority="high"
        ))
    elif risk_score >= 40:
        tips.append(SafetyTip(
            tip="🟡 MODERATE RISK: Take normal precautions. Be aware of surroundings.",
            icon="🟡",
            priority="medium"
        ))
    else:
        tips.append(SafetyTip(
            tip="✅ SAFE AREA: Crime indicators are minimal. Use normal precautions.",
            icon="✅",
            priority="low"
        ))
    
    # Crime-specific tips
    violent_crimes = {"ASSAULT", "BATTERY", "ROBBERY", "WEAPONS VIOLATION"}
    if dominant_crime.upper() in violent_crimes:
        tips.append(SafetyTip(
            tip=f"🤕 {dominant_crime} is common here. Avoid confrontations and stay in well-lit areas.",
            icon="🤕",
            priority="high"
        ))
    elif dominant_crime.upper() in {"THEFT", "BURGLARY", "MOTOR VEHICLE THEFT"}:
        tips.append(SafetyTip(
            tip="💰 Property crimes are common. Secure valuables and don't leave items in vehicles.",
            icon="💰",
            priority="medium"
        ))
    
    # High crime concentration
    if crimes_1km > 50:
        tips.append(SafetyTip(
            tip="📍 High crime concentration in this specific area. Consider visiting different locations.",
            icon="📍",
            priority="high"
        ))
    
    # General safety reminder
    if risk_score < 40:
        tips.append(SafetyTip(
            tip="🎯 Maintain awareness even in safe areas. Trust your instincts.",
            icon="🎯",
            priority="low"
        ))
    
    return tips