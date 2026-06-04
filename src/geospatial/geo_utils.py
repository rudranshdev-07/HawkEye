import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple
from src.utils.logging_config import logger

def validate_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validates latitude and longitude fields. Returns a cleaned DataFrame copy
    retaining only rows with valid, non-null, within-bounds float coordinates.
    """
    if "latitude" not in df.columns or "longitude" not in df.columns:
        logger.error("Missing coordinate columns in dataset.")
        raise ValueError("Dataset must contain 'latitude' and 'longitude' columns.")
        
    initial_len = len(df)
    
    # Cast to numeric, coerce errors to NaN
    df_clean = df.copy()
    df_clean["latitude"] = pd.to_numeric(df_clean["latitude"], errors="coerce")
    df_clean["longitude"] = pd.to_numeric(df_clean["longitude"], errors="coerce")
    
    # Check bounds
    valid_coords = (
        df_clean["latitude"].notna() &
        df_clean["longitude"].notna() &
        (df_clean["latitude"] >= -90.0) &
        (df_clean["latitude"] <= 90.0) &
        (df_clean["longitude"] >= -180.0) &
        (df_clean["longitude"] <= 180.0)
    )
    
    df_clean = df_clean[valid_coords].copy()
    dropped_count = initial_len - len(df_clean)
    if dropped_count > 0:
        logger.warning(f"Geospatial Validation: Dropped {dropped_count} rows with invalid coordinates.")
        
    return df_clean

def get_geographic_center(df: pd.DataFrame) -> Tuple[float, float]:
    """
    Computes the mean latitude and longitude of the dataset to center maps.
    Defaults to (41.8781, -87.6298) [Chicago] if the dataset is empty.
    """
    if len(df) == 0:
        return 41.8781, -87.6298
    mean_lat = float(df["latitude"].mean())
    mean_lon = float(df["longitude"].mean())
    return mean_lat, mean_lon

def compute_regional_statistics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes binned crime metrics and risk scores by district and ward.
    Classifies risk based on crime volume percentiles:
    - High Risk: Top 25% (>= 75th percentile)
    - Medium Risk: 25th to 75th percentile
    - Low Risk: Bottom 25% (< 25th percentile)
    """
    df_valid = validate_coordinates(df)
    total_crimes = len(df_valid)
    
    if total_crimes == 0:
        return {"districts": {}, "wards": {}}
        
    # District Stats
    district_counts = df_valid["district"].value_counts()
    district_stats = {}
    if not district_counts.empty:
        p25 = np.percentile(district_counts.values, 25)
        p75 = np.percentile(district_counts.values, 75)
        
        for dist, count in district_counts.items():
            cnt = int(count)
            pct = (cnt / total_crimes) * 100
            
            # Risk ranking
            if cnt >= p75:
                risk = "HIGH"
            elif cnt <= p25:
                risk = "LOW"
            else:
                risk = "MEDIUM"
                
            district_stats[str(dist)] = {
                "crime_count": cnt,
                "percentage": round(float(pct), 2),
                "risk_level": risk
            }
            
    # Ward Stats
    ward_counts = df_valid["ward"].value_counts()
    ward_stats = {}
    if not ward_counts.empty:
        p25 = np.percentile(ward_counts.values, 25)
        p75 = np.percentile(ward_counts.values, 75)
        
        for ward, count in ward_counts.items():
            cnt = int(count)
            pct = (cnt / total_crimes) * 100
            
            if cnt >= p75:
                risk = "HIGH"
            elif cnt <= p25:
                risk = "LOW"
            else:
                risk = "MEDIUM"
                
            ward_stats[str(ward)] = {
                "crime_count": cnt,
                "percentage": round(float(pct), 2),
                "risk_level": risk
            }
            
    logger.info(f"Geographic statistics computed for {len(district_stats)} districts and {len(ward_stats)} wards.")
    return {
        "district_risk": district_stats,
        "ward_risk": ward_stats
    }
