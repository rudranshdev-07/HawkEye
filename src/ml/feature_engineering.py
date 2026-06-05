import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.cluster import DBSCAN
from typing import List, Dict, Any, Tuple
from src.utils.logging_config import logger
from src.geospatial.geo_utils import validate_coordinates, get_geographic_center
from src.geospatial.hotspot_detector import detect_crime_hotspots

def haversine_distance(lat1: np.ndarray, lon1: np.ndarray, lat2: float, lon2: float) -> np.ndarray:
    """
    Computes the Haversine distance in kilometers between array of points (lat1, lon1) 
    and a single reference point (lat2, lon2).
    """
    # Earth radius in km
    R = 6371.0
    
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    
    a = np.sin(dlat / 2.0)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2.0)**2
    c = 2.0 * np.arcsin(np.sqrt(a))
    
    return R * c

class CrimeFeatureEngineer(BaseEstimator, TransformerMixin):
    """
    Scikit-learn compatible transformer that performs feature engineering 
    on raw/processed crime incident data.
    """
    def __init__(
        self,
        dbscan_eps_meters: float = 300.0,
        dbscan_min_samples: int = 15,
        num_hotspots: int = 10
    ):
        self.dbscan_eps_meters = dbscan_eps_meters
        self.dbscan_min_samples = dbscan_min_samples
        self.num_hotspots = num_hotspots
        
        # Fit variables
        self.cluster_centroids_: List[Tuple[float, float]] = []
        self.hotspot_centroids_: List[Tuple[float, float]] = []
        self.default_lat_: float = 41.8781
        self.default_lon_: float = -87.6298

    def fit(self, X: pd.DataFrame, y=None):
        """
        Learns geospatial cluster centroids and hotspot centers from the training dataset.
        """
        logger.info("Fitting CrimeFeatureEngineer on training data...")
        df = X.copy()
        
        # Parse dates to datetime if not already
        if "date" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["date"]):
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            
        # Clean coordinates
        if "latitude" in df.columns and "longitude" in df.columns:
            # Drop NaN for coordinates to fit clustering
            df_coords = df.dropna(subset=["latitude", "longitude"]).copy()
            df_coords["latitude"] = pd.to_numeric(df_coords["latitude"], errors="coerce")
            df_coords["longitude"] = pd.to_numeric(df_coords["longitude"], errors="coerce")
            df_coords = df_coords[
                (df_coords["latitude"] >= -90) & (df_coords["latitude"] <= 90) &
                (df_coords["longitude"] >= -180) & (df_coords["longitude"] <= 180)
            ]
            
            # Compute default center
            self.default_lat_, self.default_lon_ = get_geographic_center(df_coords)
            
            # 1. Fit DBSCAN and get cluster centroids
            if len(df_coords) >= self.dbscan_min_samples:
                coords_rad = np.radians(df_coords[["latitude", "longitude"]].values)
                kms_per_radian = 6371.0
                eps_rad = (self.dbscan_eps_meters / 1000.0) / kms_per_radian
                
                db = DBSCAN(eps=eps_rad, min_samples=self.dbscan_min_samples, metric="haversine", algorithm="ball_tree")
                labels = db.fit_predict(coords_rad)
                
                df_coords["cluster_id"] = labels
                unique_labels = set(labels) - {-1}
                
                centroids = []
                for label in unique_labels:
                    cluster_points = df_coords[df_coords["cluster_id"] == label]
                    lat_c = float(cluster_points["latitude"].mean())
                    lon_c = float(cluster_points["longitude"].mean())
                    centroids.append((lat_c, lon_c))
                
                self.cluster_centroids_ = centroids
                logger.info(f"Feature Engineering: Identified {len(self.cluster_centroids_)} DBSCAN clusters during fit.")
            
            # 2. Fit Hotspots and get centroids
            try:
                hotspots, _ = detect_crime_hotspots(df_coords, grid_resolution=30, top_n=self.num_hotspots)
                self.hotspot_centroids_ = [(h["latitude"], h["longitude"]) for h in hotspots]
                logger.info(f"Feature Engineering: Identified {len(self.hotspot_centroids_)} hotspots during fit.")
            except Exception as e:
                logger.warning(f"Failed to extract hotspot centroids during fit: {str(e)}")
                self.hotspot_centroids_ = []
                
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Transforms raw data into feature-engineered representation.
        """
        logger.info(f"Transforming {len(X)} rows using CrimeFeatureEngineer...")
        df = X.copy()
        
        # 1. Handle missing/outlier coordinates
        if "latitude" not in df.columns or "longitude" not in df.columns:
            logger.error("Missing coordinate columns in dataset during transform.")
            raise ValueError("Dataset must contain 'latitude' and 'longitude' columns.")
            
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce").fillna(self.default_lat_)
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce").fillna(self.default_lon_)
        
        # Clip coordinates to valid ranges
        df["latitude"] = df["latitude"].clip(-90.0, 90.0)
        df["longitude"] = df["longitude"].clip(-180.0, 180.0)
        
        # 2. Extract Temporal Features
        if "date" not in df.columns:
            logger.error("Missing 'date' column in dataset during transform.")
            raise ValueError("Dataset must contain a 'date' column.")
            
        if not pd.api.types.is_datetime64_any_dtype(df["date"]):
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            
        # If date is NaT, fill with a dummy or use current time
        nat_mask = df["date"].isna()
        if nat_mask.any():
            logger.warning(f"Found {nat_mask.sum()} NaT values in date. Filling with default datetime.")
            df.loc[nat_mask, "date"] = pd.Timestamp("2023-01-01 00:00:00")
            
        df["hour"] = df["date"].dt.hour
        df["day_of_week"] = df["date"].dt.weekday
        df["month"] = df["date"].dt.month
        df["year"] = df["date"].dt.year
        
        # 3. Cyclical Temporal Encodings (sin/cos)
        df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24.0)
        df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24.0)
        df["day_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7.0)
        df["day_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7.0)
        df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12.0)
        df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12.0)
        
        # 4. Cluster-derived Features: Distance to each cluster centroid
        lat_arr = df["latitude"].values
        lon_arr = df["longitude"].values
        
        if self.cluster_centroids_:
            for idx, (lat_c, lon_c) in enumerate(self.cluster_centroids_):
                df[f"dist_to_cluster_{idx}"] = haversine_distance(lat_arr, lon_arr, lat_c, lon_c)
        else:
            # Fallback column if no clusters found
            df["dist_to_cluster_0"] = 0.0
            
        # 5. Hotspot-derived Features: Distance to each hotspot centroid
        if self.hotspot_centroids_:
            for idx, (lat_h, lon_h) in enumerate(self.hotspot_centroids_):
                df[f"dist_to_hotspot_{idx}"] = haversine_distance(lat_arr, lon_arr, lat_h, lon_h)
        else:
            # Fallback column if no hotspots found
            df["dist_to_hotspot_0"] = 0.0
            
        # 6. Fill missing categorical variables
        categorical_cols = ["category", "location_description", "district", "ward"]
        for col in categorical_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).fillna("UNKNOWN").str.strip().str.upper()
            else:
                df[col] = "UNKNOWN"
                
        # Fill missing domestic boolean
        if "domestic" in df.columns:
            df["domestic"] = df["domestic"].fillna(False).astype(bool)
        else:
            df["domestic"] = False
            
        # Keep only features we want to pass to the model, and drop temporary ones like 'date' if needed
        # But we'll leave it to the preprocessing column transformer to select the specific columns.
        return df
