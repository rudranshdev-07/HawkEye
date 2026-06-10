"""
Unified Pydantic data models for HawkEye geospatial intelligence platform.

This module defines the canonical data structures used across the entire pipeline,
ensuring type safety, validation, and consistency from API endpoints through to
ML models and intelligence engines.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum


# =============================================================================
# ENUMS
# =============================================================================

class RiskLevel(str, Enum):
    """Risk classification levels for locations."""
    VERY_SAFE = "Very Safe"
    SAFE = "Safe"
    MODERATE = "Moderate"
    HIGH_RISK = "High Risk"
    VERY_HIGH_RISK = "Very High Risk"


class CrimeCategory(str, Enum):
    """Standard crime categories for Indian crime data."""
    THEFT = "THEFT"
    BATTERY = "BATTERY"
    ASSAULT = "ASSAULT"
    BURGLARY = "BURGLARY"
    ROBBERY = "ROBBERY"
    NARCOTICS = "NARCOTICS"
    MOTOR_VEHICLE_THEFT = "MOTOR VEHICLE THEFT"
    CRIMINAL_DAMAGE = "CRIMINAL DAMAGE"
    DECEPTIVE_PRACTICE = "DECEPTIVE PRACTICE"
    WEAPONS_VIOLATION = "WEAPONS VIOLATION"
    OTHER_OFFENSE = "OTHER OFFENSE"


# =============================================================================
# CRIME DATA MODELS
# =============================================================================

class CrimeIncident(BaseModel):
    """
    Canonical crime incident record from the Indian crime dataset.
    All coordinates are validated to be within [-90, 90] for lat and [-180, 180] for lon.
    """
    crime_id: str
    date: datetime
    category: str
    description: Optional[str] = None
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    location_description: Optional[str] = None
    arrest: bool = False
    domestic: bool = False
    district: Optional[str] = None
    ward: Optional[str] = None
    city: Optional[str] = None
    severity: Optional[int] = Field(None, ge=1, le=10)
    hour: Optional[int] = Field(None, ge=0, le=23)
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    month: Optional[int] = Field(None, ge=1, le=12)
    year: Optional[int] = Field(None, ge=2000)
    population_density: Optional[float] = Field(None, ge=0)
    weather: Optional[str] = None

    @validator('latitude', 'longitude', pre=True)
    def convert_to_float(cls, v):
        """Ensure coordinates are floats."""
        if v is None:
            return None
        return float(v)

    class Config:
        use_enum_values = False


# =============================================================================
# HOTSPOT MODELS
# =============================================================================

class Hotspot(BaseModel):
    """
    Detected crime hotspot representing a grid cell or cluster of crime incidents.
    Includes composition analysis and risk metrics.
    """
    rank: int = Field(..., ge=1)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    incident_count: int = Field(..., ge=1)
    percentage: float = Field(..., ge=0.0, le=100.0)
    top_categories: str
    arrest_rate: float = Field(..., ge=0.0, le=100.0)
    domestic_rate: float = Field(..., ge=0.0, le=100.0)


class NearestHotspotInfo(BaseModel):
    """Information about the nearest hotspot to a queried location."""
    distance_km: float = Field(..., ge=0.0)
    rank: int = Field(..., ge=1)
    incident_count: int = Field(..., ge=0)
    top_categories: str


# =============================================================================
# RISK INTELLIGENCE MODELS
# =============================================================================

class RiskScoreComponents(BaseModel):
    """
    Detailed breakdown of risk score components for explainability.
    Each component contributes to the final risk score (0-100).
    """
    density_score: float = Field(..., ge=0.0, le=100.0, description="Crime density contribution")
    hotspot_score: float = Field(..., ge=0.0, le=100.0, description="Proximity to hotspot contribution")
    severity_score: float = Field(..., ge=0.0, le=100.0, description="Historical severity contribution")
    population_score: float = Field(..., ge=0.0, le=100.0, description="Population density contribution")


class LocationIntelligence(BaseModel):
    """
    Complete intelligence report for a queried location.
    Returned by the /risk endpoint and used throughout the platform.
    """
    # Risk Assessment
    risk_score: float = Field(..., ge=0.0, le=100.0)
    risk_level: RiskLevel
    risk_components: Optional[RiskScoreComponents] = None

    # Crime Counts
    crime_count: int = Field(..., ge=0)
    crimes_1km: int = Field(..., ge=0)
    crimes_3km: int = Field(..., ge=0)
    crimes_5km: int = Field(..., ge=0)

    # Crime Profile
    dominant_crime: str
    top_crimes: Dict[str, int]
    avg_historical_risk: float = Field(..., ge=0.0, le=1.0)

    # Demographics
    population_density: int = Field(..., ge=0)

    # Hotspot Information
    nearest_hotspot_distance_km: Optional[float] = Field(None, ge=0.0)
    nearest_hotspot_rank: Optional[int] = Field(None, ge=1)
    hotspot_incidents: Optional[int] = Field(None, ge=0)
    hotspot_categories: Optional[str] = None

    # Explainability
    reasons: List[str]
    
    # Safety Tips & Recommendations
    safety_tips: Optional[List[SafetyTip]] = None


# =============================================================================
# API REQUEST/RESPONSE MODELS
# =============================================================================

class RiskRequest(BaseModel):
    """Request model for /risk endpoint."""
    features: Dict[str, Any]
    crime_types: Optional[List[str]] = None  # Filter by specific crime types
    include_forecast: Optional[bool] = False  # Include hourly forecast
    include_trends: Optional[bool] = False    # Include historical trends

    @validator('features')
    def validate_features(cls, v):
        """Ensure latitude and longitude are provided."""
        if 'latitude' not in v or 'longitude' not in v:
            raise ValueError("features must contain 'latitude' and 'longitude'")
        return v


class RiskResponse(LocationIntelligence):
    """Standard response from /risk endpoint."""
    pass


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    dataset_size: Optional[int] = None


class HeatmapResponse(BaseModel):
    """Response from /heatmap generation endpoint."""
    status: str
    heatmap_path: str


class HeatmapDataResponse(BaseModel):
    """Raw heatmap point data."""
    heatpoints: List[List[float]]


# =============================================================================
# STATISTICAL MODELS
# =============================================================================

class DistrictStats(BaseModel):
    """Crime statistics for a single district."""
    crime_count: int = Field(..., ge=0)
    percentage: float = Field(..., ge=0.0, le=100.0)
    risk_level: str


class RegionalStatistics(BaseModel):
    """Aggregated statistics for districts and wards."""
    district_risk: Dict[str, DistrictStats]
    ward_risk: Dict[str, DistrictStats]


class HotspotSummary(BaseModel):
    """Summary of all detected hotspots."""
    hotspots: List[Hotspot]
    total_hotspots: int
    coverage_percentage: float = Field(..., ge=0.0, le=100.0)


# =============================================================================
# ADVANCED FEATURES MODELS
# =============================================================================

class SafetyTip(BaseModel):
    """Safety recommendation for a location."""
    tip: str
    icon: str
    priority: str = Field(..., regex="^(high|medium|low)$")


class HeatmapPoint(BaseModel):
    """Single crime data point for heatmap visualization."""
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    intensity: Optional[float] = Field(None, ge=0.0, le=1.0)


class HeatmapDataResponse(BaseModel):
    """Raw heatmap point data for client rendering."""
    heatpoints: List[List[float]]
    intensity: Optional[List[float]] = None


class CrimeTrendPoint(BaseModel):
    """Crime trend data point for timeline visualization."""
    period: str  # e.g., "2024-01", "2024-Q1", "2024-W01"
    crime_count: int = Field(..., ge=0)
    crime_categories: Dict[str, int]
    avg_severity: float = Field(..., ge=0.0, le=10.0)


class CrimeTrendsResponse(BaseModel):
    """Historical crime trends for a location."""
    location_name: str
    latitude: float
    longitude: float
    trends: List[CrimeTrendPoint]
    total_crimes: int
    trend_direction: str = Field(..., regex="^(increasing|stable|decreasing)$")


class RiskForecast(BaseModel):
    """Risk forecast for a specific hour."""
    hour: int = Field(..., ge=0, le=23)
    timestamp: str
    predicted_risk_score: float = Field(..., ge=0.0, le=100.0)
    predicted_risk_level: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class ForecastResponse(BaseModel):
    """Time-based risk forecasting response."""
    location_coordinates: Dict[str, float]
    forecast_date: str
    forecasts: List[RiskForecast]
    safest_hours: List[int]
    dangerous_hours: List[int]


class LocationComparison(BaseModel):
    """Risk comparison between two locations."""
    location_a: Dict[str, Any]
    location_b: Dict[str, Any]
    risk_difference: float
    safer_location: str
    comparison_metrics: Dict[str, Any]


class RouteSafetySegment(BaseModel):
    """Risk analysis for a route segment."""
    segment_index: int
    latitude: float
    longitude: float
    segment_risk_score: float = Field(..., ge=0.0, le=100.0)
    segment_risk_level: str
    top_crime: str


class RouteSafetyResponse(BaseModel):
    """Route safety analysis response."""
    route_name: Optional[str] = None
    total_waypoints: int
    overall_route_risk: float = Field(..., ge=0.0, le=100.0)
    overall_risk_level: str
    safest_segments: List[int]
    dangerous_segments: List[int]
    segments: List[RouteSafetySegment]
    recommendations: List[str]
