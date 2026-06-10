"""
Advanced Location Intelligence Engine for HawkEye.

Orchestrates geospatial analysis, crime profiling, hotspot detection, 
and risk scoring to produce comprehensive intelligence reports.
"""

import pandas as pd
from math import radians, sin, cos, sqrt, atan2
from typing import Dict, Any

from src.risk.density_engine import crimes_within_radius
from src.risk.risk_engine import (
    calculate_risk_score,
    risk_level,
    generate_safety_tips
)

from src.geospatial.hotspot_detector import (
    detect_crime_hotspots
)

from src.risk.hotspot_engine import (
    nearest_hotspot
)

from src.utils.logging_config import logger

EARTH_RADIUS = 6371


# =============================================================================
# DISTANCE CALCULATOR
# =============================================================================

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two points on Earth.
    
    Args:
        lat1, lon1: First point coordinates
        lat2, lon2: Second point coordinates
    
    Returns:
        Distance in kilometers
    """
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1))
        * cos(radians(lat2))
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return EARTH_RADIUS * c


# =============================================================================
# MAIN INTELLIGENCE ENGINE
# =============================================================================

def get_location_intelligence(
    lat: float,
    lon: float,
    df: pd.DataFrame
) -> Dict[str, Any]:
    """
    Generate comprehensive intelligence report for a queried location.
    
    Analyzes surrounding crime patterns, hotspot proximity, severity,
    and population factors to produce a complete risk assessment with
    explainability.
    
    Args:
        lat: Latitude of query location
        lon: Longitude of query location
        df: Crime incidents DataFrame
    
    Returns:
        Dictionary with risk assessment, crime statistics, and reasons
    """
    
    try:
        lat = float(lat)
        lon = float(lon)
        
        logger.info(f"Intelligence query: ({lat:.4f}, {lon:.4f})")
        
        # =====================================================
        # DATA VALIDATION & CLEANING
        # =====================================================
        
        if df is None or len(df) == 0:
            logger.warning("Empty dataset provided to intelligence engine")
            return _empty_intelligence_response(lat, lon)
        
        df = df.dropna(
            subset=["latitude", "longitude"]
        ).copy()
        
        if len(df) == 0:
            logger.warning("No valid coordinates after cleaning")
            return _empty_intelligence_response(lat, lon)
        
        # =====================================================
        # CRIME RADIUS ANALYSIS
        # =====================================================
        
        crimes_1km = crimes_within_radius(df, lat, lon, 1)
        crimes_3km = crimes_within_radius(df, lat, lon, 3)
        crimes_5km = crimes_within_radius(df, lat, lon, 5)
        
        logger.debug(f"Crime counts: 1km={crimes_1km}, 3km={crimes_3km}, 5km={crimes_5km}")
        
        # =====================================================
        # NEARBY INCIDENTS (5KM ANALYSIS) - VECTORIZED
        # =====================================================
        
        # Calculate distances for all records at once (vectorized)
        from src.risk.density_engine import haversine_vectorized
        import numpy as np
        
        distances = haversine_vectorized(
            lat, lon,
            df["latitude"].values,
            df["longitude"].values
        )
        
        # Filter to records within 5km
        nearby_mask = distances <= 5
        nearby_df = df[nearby_mask].copy()
        nearby_df["distance_km"] = distances[nearby_mask]
        
        crime_count = len(nearby_df)
        
        logger.debug(f"Nearby crime incidents (5km): {crime_count}")
        
        # =====================================================
        # CRIME PROFILE & CATEGORIES
        # =====================================================
        
        top_crimes = {}
        dominant_crime = "Other"
        
        if crime_count > 0 and "category" in nearby_df.columns:
            # Get top 5 crime categories
            crime_counts = nearby_df["category"].value_counts().head(5)
            top_crimes = crime_counts.to_dict()
            dominant_crime = crime_counts.idxmax()
            
            logger.debug(f"Dominant crime: {dominant_crime}")
        
        # =====================================================
        # HISTORICAL RISK & SEVERITY
        # =====================================================
        
        avg_historical_risk = 0.0
        avg_severity = 5.0  # Default to moderate
        
        # Use existing risk_score field if available
        if crime_count > 0 and "risk_score" in nearby_df.columns:
            valid_risks = nearby_df["risk_score"].dropna()
            if len(valid_risks) > 0:
                avg_historical_risk = float(valid_risks.mean())
                avg_severity = max(1, min(avg_historical_risk * 10, 10))
        
        # Or use severity field directly
        if crime_count > 0 and "severity" in nearby_df.columns:
            valid_severities = nearby_df["severity"].dropna()
            if len(valid_severities) > 0:
                avg_severity = float(valid_severities.mean())
        
        logger.debug(f"Avg severity: {avg_severity:.2f}")
        
        # =====================================================
        # POPULATION DENSITY
        # =====================================================
        
        population_density = 10000  # Default urban density
        
        if crime_count > 0 and "population_density" in nearby_df.columns:
            valid_pops = nearby_df["population_density"].dropna()
            if len(valid_pops) > 0:
                population_density = int(valid_pops.mean())
        
        # =====================================================
        # HOTSPOT DETECTION & PROXIMITY
        # =====================================================
        
        hotspots = []
        hotspot_info = None
        hotspot_distance = 999.0
        
        try:
            hotspots, _ = detect_crime_hotspots(df)
            
            if hotspots:
                hotspot_info = nearest_hotspot(lat, lon, hotspots)
                
                if hotspot_info:
                    hotspot_distance = float(hotspot_info["distance_km"])
                    logger.debug(f"Nearest hotspot: rank={hotspot_info['rank']}, distance={hotspot_distance:.2f}km")
        
        except Exception as e:
            logger.warning(f"Hotspot detection error: {str(e)}")
        
        # =====================================================
        # ADVANCED RISK SCORING
        # =====================================================
        
        final_risk_score, risk_components = calculate_risk_score(
            crimes_1km=crimes_1km,
            crimes_3km=crimes_3km,
            crimes_5km=crimes_5km,
            hotspot_distance=hotspot_distance,
            avg_severity=avg_severity,
            population_density=population_density,
            hotspot_rank=hotspot_info["rank"] if hotspot_info else None,
            hotspot_incident_count=hotspot_info["incident_count"] if hotspot_info else None,
            dominant_crime=dominant_crime
        )
        
        final_risk_level = risk_level(final_risk_score)
        
        logger.info(f"Risk assessment: score={final_risk_score}, level={final_risk_level}")
        
        # =====================================================
        # REASONING & EXPLAINABILITY
        # =====================================================
        
        reasons = _generate_reasoning(
            crimes_1km, crimes_3km, crimes_5km,
            hotspot_info, avg_historical_risk,
            dominant_crime, crime_count,
            final_risk_score
        )
        
        # =====================================================
        # SAFETY TIPS & RECOMMENDATIONS
        # =====================================================
        
        safety_tips = generate_safety_tips(
            final_risk_score,
            dominant_crime,
            crimes_1km
        )
        
        # =====================================================
        # CONSTRUCT RESPONSE
        # =====================================================
        
        return {
            "risk_score": final_risk_score,
            "risk_level": final_risk_level,
            "risk_components": risk_components.dict() if hasattr(risk_components, 'dict') else {
                "density_score": risk_components.density_score,
                "hotspot_score": risk_components.hotspot_score,
                "severity_score": risk_components.severity_score,
                "population_score": risk_components.population_score
            },
            "crime_count": crime_count,
            "crimes_1km": crimes_1km,
            "crimes_3km": crimes_3km,
            "crimes_5km": crimes_5km,
            "avg_historical_risk": round(avg_historical_risk, 4),
            "population_density": population_density,
            "dominant_crime": dominant_crime,
            "top_crimes": top_crimes,
            "reasons": reasons,
            "safety_tips": [tip.dict() for tip in safety_tips],
            "nearest_hotspot_distance_km": (
                round(hotspot_info["distance_km"], 2)
                if hotspot_info else None
            ),
            "nearest_hotspot_rank": (
                hotspot_info["rank"]
                if hotspot_info else None
            ),
            "hotspot_incidents": (
                hotspot_info["incident_count"]
                if hotspot_info else None
            ),
            "hotspot_categories": (
                hotspot_info["top_categories"]
                if hotspot_info else None
            )
        }
    
    except Exception as e:
        logger.error(f"Error in intelligence engine: {str(e)}", exc_info=True)
        return _empty_intelligence_response(lat, lon)


# =============================================================================
# REASONING ENGINE
# =============================================================================

def _generate_reasoning(
    crimes_1km: int,
    crimes_3km: int,
    crimes_5km: int,
    hotspot_info: Dict[str, Any],
    avg_historical_risk: float,
    dominant_crime: str,
    crime_count: int,
    risk_score: float
) -> list:
    """
    Generate human-readable explanations for risk assessment.
    
    Args:
        Various crime metrics and context
    
    Returns:
        List of explanation strings
    """
    reasons = []
    
    # Crime density reasoning
    if crimes_1km > 50:
        reasons.append(
            f"🔴 CRITICAL: {crimes_1km} crime incidents detected within 1km radius. "
            "Extremely high concentration of criminal activity."
        )
    elif crimes_1km > 25:
        reasons.append(
            f"⚠️ HIGH: {crimes_1km} crime incidents within 1km. "
            "Elevated concentration suggests elevated risk."
        )
    elif crimes_1km > 10:
        reasons.append(
            f"⚡ MODERATE: {crimes_1km} incidents within 1km indicates "
            "notable criminal activity in immediate vicinity."
        )
    
    # Regional crime volume
    if crimes_5km > 200:
        reasons.append(
            f"Large volume of {crimes_5km} crime incidents in broader 5km region. "
            "High overall area crime volume."
        )
    
    # Hotspot proximity
    if hotspot_info:
        distance = hotspot_info["distance_km"]
        rank = hotspot_info["rank"]
        
        if distance < 0.5:
            reasons.append(
                f"⛔ {distance:.2f}km from Rank #{rank} hotspot. "
                "Location is INSIDE or adjacent to major crime hotspot."
            )
        elif distance < 2.0:
            reasons.append(
                f"Located {distance:.2f}km from Rank #{rank} hotspot. "
                "Close proximity to established crime center."
            )
        elif distance < 5.0:
            reasons.append(
                f"Within 5km of Rank #{rank} hotspot ({distance:.2f}km). "
                "Moderate proximity to crime concentration area."
            )
    
    # Crime severity
    if avg_historical_risk > 0.75:
        reasons.append(
            "Historical crime data shows SIGNIFICANTLY elevated severity. "
            "Past incidents in area were serious."
        )
    elif avg_historical_risk > 0.50:
        reasons.append(
            "Historical crime severity is above average. "
            "Area has recorded moderately serious incidents."
        )
    
    # Crime type
    violent_crimes = {"ASSAULT", "BATTERY", "ROBBERY", "WEAPONS VIOLATION"}
    if dominant_crime.upper() in violent_crimes:
        reasons.append(
            f"Most common crime type is {dominant_crime} — a violent offense. "
            "Physical safety concern is primary risk."
        )
    else:
        reasons.append(
            f"Most frequently reported crime: {dominant_crime}. "
            "Property/other crimes are dominant."
        )
    
    # Overall risk assessment
    if risk_score >= 80:
        reasons.append(
            "🚨 CRITICAL RISK: Multiple factors converge to create very high threat level. "
            "Extreme caution recommended."
        )
    elif risk_score >= 60:
        reasons.append(
            "⚠️ HIGH RISK: Significant risk factors present. "
            "Exercise heightened awareness."
        )
    elif risk_score < 20:
        reasons.append(
            "✅ VERY SAFE: Crime indicators are minimal. Area appears safe."
        )
    
    # Fallback if no reasons generated
    if len(reasons) == 0:
        reasons.append("No major crime indicators detected at this location.")
    
    return reasons


def _empty_intelligence_response(lat: float, lon: float) -> Dict[str, Any]:
    """Return safe-defaults response when data is unavailable."""
    return {
        "risk_score": 0.0,
        "risk_level": "Very Safe",
        "risk_components": {
            "density_score": 0.0,
            "hotspot_score": 0.0,
            "severity_score": 0.0,
            "population_score": 0.0
        },
        "crime_count": 0,
        "crimes_1km": 0,
        "crimes_3km": 0,
        "crimes_5km": 0,
        "avg_historical_risk": 0.0,
        "population_density": 0,
        "dominant_crime": "Unknown",
        "top_crimes": {},
        "reasons": ["Unable to analyze location: insufficient data available."],
        "safety_tips": [
            {
                "tip": "⚠️ Insufficient data for analysis. Please try another location.",
                "icon": "⚠️",
                "priority": "medium"
            }
        ],
        "nearest_hotspot_distance_km": None,
        "nearest_hotspot_rank": None,
        "hotspot_incidents": None,
        "hotspot_categories": None
    }