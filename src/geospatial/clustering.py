import os
import folium
from folium.plugins import MarkerCluster
import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
from typing import Dict, Any, List, Tuple
from src.geospatial.geo_utils import validate_coordinates, get_geographic_center
from src.utils.logging_config import logger

def run_dbscan_clustering(
    df: pd.DataFrame,
    eps_meters: float = 300.0,
    min_samples: int = 15
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Applies DBSCAN clustering on geographic points.
    Converts meters to radians for correct Haversine distance computations.
    Returns:
      1. DataFrame with a 'cluster_id' column.
      2. Summary dict of clusters (centroids, counts, bounds).
    """
    df_clean = validate_coordinates(df)
    if len(df_clean) == 0:
        logger.warning("Empty dataset passed to clustering engine.")
        df_clean["cluster_id"] = -1
        return df_clean, {}
        
    # Convert coordinates to radians
    coords_rad = np.radians(df_clean[["latitude", "longitude"]].values)
    
    # Earth's radius in meters is ~6,371,000
    kms_per_radian = 6371000.0
    eps_rad = eps_meters / kms_per_radian
    
    logger.info(f"Running DBSCAN: eps={eps_meters}m ({eps_rad:.6f} rad), min_samples={min_samples}")
    
    db = DBSCAN(eps=eps_rad, min_samples=min_samples, metric="haversine", algorithm="ball_tree")
    labels = db.fit_predict(coords_rad)
    
    df_clean["cluster_id"] = labels
    
    # Analyze clusters
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)
    
    cluster_summary = {
        "total_incidents": len(df_clean),
        "number_of_clusters": n_clusters,
        "noise_incidents_count": n_noise,
        "noise_percentage": round(float((n_noise / len(df_clean)) * 100), 2) if len(df_clean) > 0 else 0.0,
        "clusters": {}
    }
    
    if n_clusters > 0:
        grouped = df_clean[df_clean["cluster_id"] != -1].groupby("cluster_id")
        for clus_id, group in grouped:
            centroid_lat = float(group["latitude"].mean())
            centroid_lon = float(group["longitude"].mean())
            
            top_cats = group["category"].value_counts().head(2).to_dict()
            cats_str = ", ".join([f"{k} ({v})" for k, v in top_cats.items()])
            
            cluster_summary["clusters"][int(clus_id)] = {
                "cluster_id": int(clus_id),
                "size": len(group),
                "percentage": round(float((len(group) / len(df_clean)) * 100), 2),
                "centroid_lat": round(centroid_lat, 5),
                "centroid_lon": round(centroid_lon, 5),
                "top_categories": cats_str
            }
            
    logger.info(f"DBSCAN complete. Found {n_clusters} clusters. Noise points: {n_noise}.")
    return df_clean, cluster_summary

def generate_cluster_map(
    df_clustered: pd.DataFrame,
    cluster_summary: Dict[str, Any],
    output_path: str = "outputs/maps/cluster_map.html"
) -> str:
    """
    Generates an interactive Folium map representing DBSCAN clusters.
    Uses MarkerCluster for raw points and large colored circles for core centroids.
    """
    if len(df_clustered) == 0:
        center_lat, center_lon = 41.8781, -87.6298
    else:
        center_lat, center_lon = get_geographic_center(df_clustered)
        
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=12,
        tiles="Cartodb dark_matter",
        name="Dark Mode"
    )
    
    folium.TileLayer("Cartodb positron", name="Light Mode").add_to(m)
    folium.TileLayer("OpenStreetMap", name="Detailed Street Map").add_to(m)
    
    # 1. Plot individual clustered points using Folium MarkerCluster for smooth rendering
    marker_cluster = MarkerCluster(name="Clustered Crime Incidents", show=False).add_to(m)
    
    # Unique colors for top clusters, cycle if more than 10
    colors_cycle = ["#390099", "#9e0059", "#ff0054", "#ff5400", "#ffbd00", "#00ffb7", "#00bbf9", "#00f5d4", "#70e000", "#ccff33"]
    
    # Sample points to draw on map to prevent massive files (cap at 3000 points)
    df_sample = df_clustered.sample(n=min(len(df_clustered), 3000), random_state=42)
    
    for _, row in df_sample.iterrows():
        c_id = int(row["cluster_id"])
        
        # Noise points get dark grey, clustered points get colored markers
        if c_id == -1:
            color = "#5c5c5c"
            popup_text = f"Outlier Incident<br/>Category: {row['category']}"
            radius = 3
            opacity = 0.4
        else:
            color = colors_cycle[c_id % len(colors_cycle)]
            popup_text = f"Cluster #{c_id}<br/>Category: {row['category']}"
            radius = 5
            opacity = 0.8
            
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=opacity,
            popup=popup_text
        ).add_to(marker_cluster)
        
    # 2. Draw centroids of core clusters on main map as prominent rings
    centroids_layer = folium.FeatureGroup(name="Cluster Centroids")
    
    for clus_id, info in cluster_summary.get("clusters", {}).items():
        color = colors_cycle[int(clus_id) % len(colors_cycle)]
        
        centroid_html = f"""
        <div style="font-family: sans-serif; font-size: 13px; color: #1a1a1e; width: 220px;">
            <h4 style="margin: 0 0 6px 0; color: {color};">Cluster #{clus_id} Centroid</h4>
            <hr style="margin: 4px 0; border: 0; border-top: 1px solid #ddd;"/>
            <b>Incident Count:</b> {info['size']} ({info['percentage']:.1f}%)<br/>
            <b>Location:</b> {info['centroid_lat']:.4f}, {info['centroid_lon']:.4f}<br/>
            <b>Primary Crimes:</b><br/>
            <span style="font-size: 11px; color: #555;">{info['top_categories']}</span>
        </div>
        """
        
        # Plot large core circle
        folium.Circle(
            location=[info["centroid_lat"], info["centroid_lon"]],
            radius=200,  # Constant size ring to represent centroid
            color=color,
            weight=3,
            fill=True,
            fill_color=color,
            fill_opacity=0.15,
            popup=folium.Popup(centroid_html, max_width=240),
            tooltip=f"Cluster #{clus_id}: {info['size']} crimes"
        ).add_to(centroids_layer)
        
        # Numbered marker label
        folium.map.Marker(
            location=[info["centroid_lat"], info["centroid_lon"]],
            icon=folium.DivIcon(
                html=f"""<div style="font-family: sans-serif; color: white; background-color: {color}; 
                      border-radius: 50%; width: 22px; height: 22px; line-height: 22px; text-align: center; 
                      font-weight: bold; border: 1.5px solid white; font-size: 10px; transform: translate(-11px, -11px);">
                      C{clus_id}
                      </div>"""
            )
        ).add_to(centroids_layer)
        
    centroids_layer.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    
    # Save map
    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir)
        
    m.save(output_path)
    logger.info(f"Geospatial cluster map saved to: {output_path}")
    return output_path
