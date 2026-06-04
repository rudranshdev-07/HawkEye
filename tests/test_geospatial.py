import os
import tempfile
import pytest
import pandas as pd
import numpy as np
from src.geospatial.geo_utils import validate_coordinates, get_geographic_center, compute_regional_statistics
from src.geospatial.heatmap import generate_crime_heatmap
from src.geospatial.hotspot_detector import detect_crime_hotspots, generate_hotspot_map
from src.geospatial.clustering import run_dbscan_clustering, generate_cluster_map

@pytest.fixture
def mock_geo_data():
    # 15 points grouped close together (Cluster 0), 15 points binned in Chicago loop (Cluster 1), and 1 outlier
    # Cluster 0: Centered around (41.8781, -87.6298)
    lats_0 = np.random.normal(41.8781, 0.0005, 15)
    lons_0 = np.random.normal(-87.6298, 0.0005, 15)
    
    # Cluster 1: Centered around (41.9484, -87.6553)
    lats_1 = np.random.normal(41.9484, 0.0005, 15)
    lons_1 = np.random.normal(-87.6553, 0.0005, 15)
    
    # Outlier/noise point:
    lats_noise = [41.7789]
    lons_noise = [-87.7269]
    
    all_lats = np.concatenate([lats_0, lats_1, lats_noise])
    all_lons = np.concatenate([lons_0, lons_1, lons_noise])
    
    return pd.DataFrame({
        "crime_id": [f"CR-{i}" for i in range(31)],
        "latitude": all_lats,
        "longitude": all_lons,
        "district": ["D-01"] * 15 + ["D-02"] * 15 + ["D-03"],
        "ward": ["W-01"] * 15 + ["W-02"] * 15 + ["W-03"],
        "category": ["THEFT"] * 10 + ["BATTERY"] * 10 + ["ASSAULT"] * 11,
        "arrest": [True] * 15 + [False] * 16,
        "domestic": [False] * 31
    })

def test_validate_coordinates():
    df = pd.DataFrame({
        "latitude": [41.8781, 95.0, np.nan, 41.7789],
        "longitude": [-87.6298, -87.6298, -87.6290, -200.0]
    })
    
    df_clean = validate_coordinates(df)
    # Only the first row is completely valid
    assert len(df_clean) == 1
    assert df_clean.iloc[0]["latitude"] == 41.8781

def test_get_geographic_center(mock_geo_data):
    center_lat, center_lon = get_geographic_center(mock_geo_data)
    assert 41.7 <= center_lat <= 42.0
    assert -87.8 <= center_lon <= -87.5

def test_compute_regional_statistics(mock_geo_data):
    stats = compute_regional_statistics(mock_geo_data)
    
    assert "D-01" in stats["district_risk"]
    assert "D-02" in stats["district_risk"]
    assert "D-03" in stats["district_risk"]
    
    # D-01 and D-02 should have 15 crimes (higher volume)
    assert stats["district_risk"]["D-01"]["crime_count"] == 15
    assert stats["district_risk"]["D-03"]["crime_count"] == 1

def test_hotspot_detector(mock_geo_data):
    hotspots, df_grid = detect_crime_hotspots(mock_geo_data, grid_resolution=10, top_n=3)
    
    assert len(hotspots) > 0
    # Check hotspot ranking
    assert hotspots[0]["rank"] == 1
    assert hotspots[0]["incident_count"] >= hotspots[1]["incident_count"]

def test_clustering_dbscan(mock_geo_data):
    # Cluster points close to each other (300 meters spacing)
    # DBSCAN eps_meters=400, min_samples=10
    df_clustered, cluster_summary = run_dbscan_clustering(mock_geo_data, eps_meters=400, min_samples=10)
    
    assert "cluster_id" in df_clustered.columns
    # Check that we found at least 2 clusters
    assert cluster_summary["number_of_clusters"] >= 2
    # Check that the noise point (41.7789, -87.7269) is classified as noise (-1)
    noise_row = df_clustered[df_clustered["latitude"] == 41.7789]
    if len(noise_row) > 0:
        assert noise_row.iloc[0]["cluster_id"] == -1

def test_maps_generation_flow(mock_geo_data):
    # Setup temporary files
    with tempfile.TemporaryDirectory() as tmpdir:
        heatmap_path = os.path.join(tmpdir, "heatmap.html")
        hotspot_path = os.path.join(tmpdir, "hotspots.html")
        cluster_path = os.path.join(tmpdir, "clusters.html")
        
        # 1. Heatmap
        generate_crime_heatmap(mock_geo_data, heatmap_path)
        assert os.path.exists(heatmap_path)
        assert os.path.getsize(heatmap_path) > 0
        
        # 2. Hotspots
        hotspots, _ = detect_crime_hotspots(mock_geo_data, grid_resolution=10, top_n=2)
        generate_hotspot_map(mock_geo_data, hotspots, hotspot_path)
        assert os.path.exists(hotspot_path)
        assert os.path.getsize(hotspot_path) > 0
        
        # 3. Clustering
        df_clustered, cluster_summary = run_dbscan_clustering(mock_geo_data, eps_meters=400, min_samples=10)
        generate_cluster_map(df_clustered, cluster_summary, cluster_path)
        assert os.path.exists(cluster_path)
        assert os.path.getsize(cluster_path) > 0
