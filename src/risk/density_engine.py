import pandas as pd
import numpy as np
from math import radians, pi

EARTH_RADIUS = 6371


def haversine_vectorized(lat1, lon1, lat2_array, lon2_array):
    """
    Vectorized haversine distance calculation.
    Calculates distance from (lat1, lon1) to all points in arrays.
    
    Returns distances in kilometers.
    """
    dlat = np.radians(lat2_array - lat1)
    dlon = np.radians(lon2_array - lon1)

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(np.radians(lat1))
        * np.cos(np.radians(lat2_array))
        * np.sin(dlon / 2) ** 2
    )

    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return EARTH_RADIUS * c


def crimes_within_radius(df, lat, lon, radius_km):
    """
    Count crimes within a given radius using vectorized operations.
    
    Args:
        df: DataFrame with latitude/longitude columns
        lat: Query latitude
        lon: Query longitude
        radius_km: Search radius in kilometers
    
    Returns:
        Count of crimes within radius
    """
    try:
        # Vectorized distance calculation
        distances = haversine_vectorized(
            lat, lon,
            df["latitude"].values,
            df["longitude"].values
        )
        
        # Count incidents within radius
        return int(np.sum(distances <= radius_km))
    
    except Exception as e:
        # Fallback to safe default
        return 0
