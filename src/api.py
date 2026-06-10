from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import logging
from pathlib import Path

from src.risk.intelligence_engine import get_location_intelligence
from src.geospatial.heatmap import generate_crime_heatmap
from src.models import (
    RiskRequest,
    RiskResponse,
    HealthResponse,
    HeatmapResponse,
    HeatmapDataResponse,
    CrimeTrendsResponse,
    ForecastResponse,
    LocationComparison,
    RouteSafetyResponse
)
from src.utils.logging_config import logger

# =============================================================================
# APP INITIALIZATION
# =============================================================================

app = FastAPI(
    title="HawkEye Geo Intelligence API",
    description="AI-powered geospatial crime intelligence for Indian cities",
    version="1.0.0"
)

# =============================================================================
# CORS CONFIGURATION
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# GLOBAL STATE
# =============================================================================

crime_df = None
DATASET_LOADED = False

# =============================================================================
# STARTUP EVENT - DATA LOADING
# =============================================================================

@app.on_event("startup")
async def load_dataset():
    """Load the Indian crime dataset on application startup."""
    global crime_df, DATASET_LOADED
    
    try:
        data_path = Path("data/raw/india_crime_data.csv")
        
        if not data_path.exists():
            logger.error(f"Dataset not found at {data_path}")
            crime_df = pd.DataFrame()
            DATASET_LOADED = False
            return
        
        crime_df = pd.read_csv(data_path)
        logger.info(f"✓ Successfully loaded Indian crime dataset: {len(crime_df)} records")
        
        # Validate schema
        required_cols = {"latitude", "longitude", "category"}
        missing_cols = required_cols - set(crime_df.columns)
        if missing_cols:
            logger.warning(f"Missing expected columns: {missing_cols}")
        
        DATASET_LOADED = len(crime_df) > 0
        
    except Exception as e:
        logger.error(f"✗ Failed to load dataset: {str(e)}")
        crime_df = pd.DataFrame()
        DATASET_LOADED = False


# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """
    Health check endpoint.
    Returns status and dataset information.
    """
    return HealthResponse(
        status="ok" if DATASET_LOADED else "degraded",
        dataset_size=len(crime_df) if crime_df is not None else 0
    )


# =============================================================================
# MAIN RISK INTELLIGENCE ENDPOINT
# =============================================================================

@app.post("/risk", response_model=RiskResponse)
async def risk(request: RiskRequest) -> RiskResponse:
    """
    Main intelligence endpoint.
    
    Accepts coordinates and returns comprehensive risk analysis including:
    - Risk score and classification
    - Crime counts within radius
    - Dominant crime categories
    - Nearest hotspot information
    - Explainability reasons
    
    Query Parameters:
        - latitude: float (-90 to 90)
        - longitude: float (-180 to 180)
    
    Returns:
        LocationIntelligence: Complete risk report
    
    Raises:
        HTTPException: 400 if invalid coordinates, 503 if dataset unavailable
    """
    try:
        # Validate dataset
        if not DATASET_LOADED or crime_df is None or len(crime_df) == 0:
            logger.error("Risk endpoint called but dataset not loaded")
            raise HTTPException(
                status_code=503,
                detail="Dataset not available. Please check server logs."
            )
        
        # Extract coordinates
        features = request.features
        latitude = float(features.get("latitude"))
        longitude = float(features.get("longitude"))
        
        # Validate coordinate ranges
        if not (-90 <= latitude <= 90):
            raise HTTPException(status_code=400, detail="Latitude must be between -90 and 90")
        if not (-180 <= longitude <= 180):
            raise HTTPException(status_code=400, detail="Longitude must be between -180 and 180")
        
        logger.info(f"Processing risk query for location: ({latitude}, {longitude})")
        
        # Get intelligence
        intelligence = get_location_intelligence(latitude, longitude, crime_df)
        
        logger.info(f"Risk analysis complete: score={intelligence['risk_score']}, level={intelligence['risk_level']}")
        
        return RiskResponse(**intelligence)
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error in /risk: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in /risk endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error during intelligence analysis"
        )


# =============================================================================
# HEATMAP GENERATION
# =============================================================================

@app.get("/heatmap", response_model=HeatmapResponse)
async def heatmap() -> HeatmapResponse:
    """
    Generate interactive Folium crime density heatmap.
    
    Returns:
        HeatmapResponse: Path to generated HTML map file
    
    Raises:
        HTTPException: 503 if dataset unavailable
    """
    try:
        if not DATASET_LOADED or crime_df is None or len(crime_df) == 0:
            raise HTTPException(status_code=503, detail="Dataset not available")
        
        logger.info("Generating crime heatmap...")
        path = generate_crime_heatmap(crime_df)
        logger.info(f"Heatmap generated: {path}")
        
        return HeatmapResponse(
            status="generated",
            heatmap_path=path
        )
        
    except Exception as e:
        logger.error(f"Error generating heatmap: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate heatmap")


# =============================================================================
# HEATMAP DATA (FOR FRONTEND RENDERING)
# =============================================================================

@app.get("/heatmap-data", response_model=HeatmapDataResponse)
async def heatmap_data() -> HeatmapDataResponse:
    """
    Get raw heatmap data points for client-side rendering.
    Returns list of [latitude, longitude] pairs.
    
    Returns:
        HeatmapDataResponse: Array of coordinate pairs
    
    Raises:
        HTTPException: 503 if dataset unavailable
    """
    try:
        if not DATASET_LOADED or crime_df is None or len(crime_df) == 0:
            raise HTTPException(status_code=503, detail="Dataset not available")
        
        # Extract valid coordinates
        valid_coords = crime_df[["latitude", "longitude"]].dropna()
        
        return HeatmapDataResponse(
            heatpoints=valid_coords.values.tolist()
        )
        
    except Exception as e:
        logger.error(f"Error retrieving heatmap data: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve heatmap data")


# =============================================================================
# ADVANCED FEATURES ENDPOINTS
# =============================================================================

@app.get("/trends", response_model=CrimeTrendsResponse)
async def crime_trends(
    latitude: float = 28.61,
    longitude: float = 77.20,
    radius_km: int = 1
) -> CrimeTrendsResponse:
    """
    Get historical crime trends for a location (monthly).
    
    Args:
        latitude: Location latitude
        longitude: Location longitude  
        radius_km: Radius for crime analysis
    
    Returns:
        CrimeTrendsResponse: Historical crime trends
    """
    try:
        if not DATASET_LOADED or crime_df is None or len(crime_df) == 0:
            raise HTTPException(status_code=503, detail="Dataset not available")
        
        # Filter crimes within radius
        from src.risk.intelligence_engine import haversine
        
        distances = []
        for _, row in crime_df.iterrows():
            d = haversine(latitude, longitude, row["latitude"], row["longitude"])
            distances.append(d)
        
        nearby_df = crime_df[[(d <= radius_km) for d in distances]].copy()
        
        # Aggregate by month if date field exists
        trends = []
        if "date" in nearby_df.columns:
            try:
                nearby_df["month"] = pd.to_datetime(nearby_df["date"]).dt.to_period("M")
                monthly = nearby_df.groupby("month").agg({
                    "latitude": "count",
                    "category": lambda x: x.value_counts().to_dict() if len(x) > 0 else {}
                }).rename(columns={"latitude": "count"})
                
                for period, row in monthly.iterrows():
                    trends.append({
                        "period": str(period),
                        "crime_count": int(row["count"]),
                        "crime_categories": row["category"],
                        "avg_severity": 5.0
                    })
            except:
                pass
        
        # Determine trend direction
        trend_direction = "stable"
        if len(trends) > 1:
            recent_avg = sum([t["crime_count"] for t in trends[-3:]]) / 3 if len(trends) >= 3 else trends[-1]["crime_count"]
            older_avg = sum([t["crime_count"] for t in trends[:3]]) / 3 if len(trends) >= 3 else trends[0]["crime_count"]
            if recent_avg > older_avg * 1.1:
                trend_direction = "increasing"
            elif recent_avg < older_avg * 0.9:
                trend_direction = "decreasing"
        
        return CrimeTrendsResponse(
            location_name="Query Location",
            latitude=latitude,
            longitude=longitude,
            trends=trends if trends else [{"period": "No data", "crime_count": 0, "crime_categories": {}, "avg_severity": 0.0}],
            total_crimes=len(nearby_df),
            trend_direction=trend_direction
        )
    
    except Exception as e:
        logger.error(f"Error in trends endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve trends")


@app.post("/forecast")
async def forecast_risk(
    latitude: float,
    longitude: float,
    date: Optional[str] = None
) -> ForecastResponse:
    """
    Forecast hourly risk for a location (simulated ML-based forecast).
    
    Args:
        latitude: Location latitude
        longitude: Location longitude
        date: Date for forecast (defaults to today)
    
    Returns:
        ForecastResponse: Hourly risk forecasts
    """
    try:
        if not DATASET_LOADED or crime_df is None or len(crime_df) == 0:
            raise HTTPException(status_code=503, detail="Dataset not available")
        
        from datetime import datetime, timedelta
        import random
        
        # Get base risk for this location
        from src.risk.intelligence_engine import get_location_intelligence
        base_intel = get_location_intelligence(latitude, longitude, crime_df)
        base_risk = base_intel.get("risk_score", 50)
        
        # Generate 24-hour forecast with realistic patterns
        forecasts = []
        safest_hours = []
        dangerous_hours = []
        
        # Typical crime patterns: peaks at night (22:00-02:00) and morning (06:00-09:00)
        hour_multipliers = {
            0: 1.3, 1: 1.4, 2: 1.35,  # Late night peak
            3: 1.0, 4: 0.8, 5: 0.7,   # Early morning low
            6: 0.9, 7: 1.1, 8: 1.2, 9: 1.1,  # Morning rush
            10: 0.9, 11: 0.8, 12: 0.7,  # Midday low
            13: 0.8, 14: 0.85, 15: 0.9,  # Afternoon
            16: 1.0, 17: 1.2, 18: 1.3,  # Evening
            19: 1.2, 20: 1.3, 21: 1.4, 22: 1.45, 23: 1.4  # Night peak
        }
        
        forecast_date = date or datetime.now().strftime("%Y-%m-%d")
        
        for hour in range(24):
            multiplier = hour_multipliers.get(hour, 1.0)
            noise = random.uniform(-5, 5)
            predicted_risk = min(100, max(0, base_risk * multiplier + noise))
            
            risk_level = "Very Safe" if predicted_risk < 20 else "Safe" if predicted_risk < 40 else "Moderate" if predicted_risk < 60 else "High Risk" if predicted_risk < 80 else "Very High Risk"
            confidence = 0.75 + random.uniform(-0.1, 0.15)  # 0.65-0.90 confidence
            
            forecast = {
                "hour": hour,
                "timestamp": f"{forecast_date}T{hour:02d}:00:00Z",
                "predicted_risk_score": round(predicted_risk, 2),
                "predicted_risk_level": risk_level,
                "confidence": round(confidence, 2)
            }
            forecasts.append(forecast)
            
            if predicted_risk < 35:
                safest_hours.append(hour)
            elif predicted_risk > 70:
                dangerous_hours.append(hour)
        
        return ForecastResponse(
            location_coordinates={"latitude": latitude, "longitude": longitude},
            forecast_date=forecast_date,
            forecasts=forecasts,
            safest_hours=safest_hours,
            dangerous_hours=dangerous_hours
        )
    
    except Exception as e:
        logger.error(f"Error in forecast endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate forecast")


@app.post("/compare")
async def compare_locations(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float
) -> LocationComparison:
    """
    Compare risk between two locations.
    
    Args:
        latitude_a, longitude_a: First location
        latitude_b, longitude_b: Second location
    
    Returns:
        LocationComparison: Risk comparison
    """
    try:
        if not DATASET_LOADED or crime_df is None or len(crime_df) == 0:
            raise HTTPException(status_code=503, detail="Dataset not available")
        
        from src.risk.intelligence_engine import get_location_intelligence
        
        intel_a = get_location_intelligence(latitude_a, longitude_a, crime_df)
        intel_b = get_location_intelligence(latitude_b, longitude_b, crime_df)
        
        risk_a = intel_a["risk_score"]
        risk_b = intel_b["risk_score"]
        difference = abs(risk_a - risk_b)
        safer = "Location A" if risk_a < risk_b else "Location B"
        
        return LocationComparison(
            location_a={"latitude": latitude_a, "longitude": longitude_a, "risk_score": risk_a},
            location_b={"latitude": latitude_b, "longitude": longitude_b, "risk_score": risk_b},
            risk_difference=round(difference, 2),
            safer_location=safer,
            comparison_metrics={
                "location_a_crimes_1km": intel_a["crimes_1km"],
                "location_b_crimes_1km": intel_b["crimes_1km"],
                "location_a_dominant_crime": intel_a["dominant_crime"],
                "location_b_dominant_crime": intel_b["dominant_crime"]
            }
        )
    
    except Exception as e:
        logger.error(f"Error in compare endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to compare locations")


@app.post("/route-safety")
async def route_safety(
    waypoints: list
) -> RouteSafetyResponse:
    """
    Analyze safety along a route defined by waypoints.
    
    Args:
        waypoints: List of [lat, lon] coordinates
    
    Returns:
        RouteSafetyResponse: Route safety analysis
    """
    try:
        if not DATASET_LOADED or crime_df is None or len(crime_df) == 0:
            raise HTTPException(status_code=503, detail="Dataset not available")
        
        from src.risk.intelligence_engine import get_location_intelligence, haversine
        
        if not waypoints or len(waypoints) < 2:
            raise ValueError("At least 2 waypoints required")
        
        segments = []
        total_risk = 0
        safest = []
        dangerous = []
        
        for i, (lat, lon) in enumerate(waypoints):
            intel = get_location_intelligence(lat, lon, crime_df)
            risk = intel["risk_score"]
            total_risk += risk
            
            segment = {
                "segment_index": i,
                "latitude": lat,
                "longitude": lon,
                "segment_risk_score": risk,
                "segment_risk_level": intel["risk_level"],
                "top_crime": intel["dominant_crime"]
            }
            segments.append(segment)
            
            if risk < 35:
                safest.append(i)
            elif risk > 70:
                dangerous.append(i)
        
        avg_route_risk = total_risk / len(waypoints)
        route_level = "Very Safe" if avg_route_risk < 20 else "Safe" if avg_route_risk < 40 else "Moderate" if avg_route_risk < 60 else "High Risk" if avg_route_risk < 80 else "Very High Risk"
        
        recommendations = []
        if avg_route_risk > 70:
            recommendations.append("⚠️ Consider alternative routes with lower crime rates")
        if len(dangerous) > 0:
            recommendations.append(f"🚨 Segments {dangerous} have high risk - avoid if possible")
        if len(safest) > 0:
            recommendations.append(f"✅ Segments {safest} are relatively safe")
        
        return RouteSafetyResponse(
            total_waypoints=len(waypoints),
            overall_route_risk=round(avg_route_risk, 2),
            overall_risk_level=route_level,
            safest_segments=safest,
            dangerous_segments=dangerous,
            segments=segments,
            recommendations=recommendations
        )
    
    except Exception as e:
        logger.error(f"Error in route-safety endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to analyze route safety")