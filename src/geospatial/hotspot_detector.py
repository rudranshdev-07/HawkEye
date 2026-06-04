import os
import folium
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple
from src.geospatial.geo_utils import validate_coordinates, get_geographic_center
from src.utils.logging_config import logger

def detect_crime_hotspots(
    df: pd.DataFrame,
    grid_resolution: int = 30,
    top_n: int = 10
) -> Tuple[List[Dict[str, Any]], pd.DataFrame]:
    """
    Divides the coordinate bounds of the dataset into a grid of size resolution x resolution.
    Bins all crime points into these grid cells and ranks the cells by volume.
    Returns:
      1. A list of dicts describing the top N hotspots.
      2. The updated DataFrame containing grid assignment columns.
    """
    df_clean = validate_coordinates(df)
    if len(df_clean) == 0:
        logger.warning("Empty dataset passed to hotspot detector.")
        return [], df_clean
        
    lat_min, lat_max = df_clean["latitude"].min(), df_clean["latitude"].max()
    lon_min, lon_max = df_clean["longitude"].min(), df_clean["longitude"].max()
    
    # Avoid zero division if bounds are identical
    lat_range = lat_max - lat_min if lat_max != lat_min else 0.001
    lon_range = lon_max - lon_min if lon_max != lon_min else 0.001
    
    # Calculate cell assignments
    df_clean["grid_lat"] = ((df_clean["latitude"] - lat_min) / lat_range * (grid_resolution - 1)).round().astype(int)
    df_clean["grid_lon"] = ((df_clean["longitude"] - lon_min) / lon_range * (grid_resolution - 1)).round().astype(int)
    
    # Group by grid coordinate
    grid_groups = df_clean.groupby(["grid_lat", "grid_lon"])
    grid_counts = grid_groups.size().sort_values(ascending=False)
    
    total_crimes = len(df_clean)
    hotspots = []
    
    for rank, ((g_lat, g_lon), count) in enumerate(grid_counts.head(top_n).items(), 1):
        group_df = grid_groups.get_group((g_lat, g_lon))
        
        # Calculate cluster centroid
        centroid_lat = float(group_df["latitude"].mean())
        centroid_lon = float(group_df["longitude"].mean())
        
        # Category composition in this hotspot
        top_cats = group_df["category"].value_counts().head(3).to_dict()
        top_cats_str = ", ".join([f"{k} ({v})" for k, v in top_cats.items()])
        
        # Domestic and Arrest percentages
        arrests = int(group_df["arrest"].sum()) if "arrest" in group_df.columns else 0
        domestics = int(group_df["domestic"].sum()) if "domestic" in group_df.columns else 0
        group_len = len(group_df)
        
        hotspots.append({
            "rank": rank,
            "latitude": round(centroid_lat, 5),
            "longitude": round(centroid_lon, 5),
            "incident_count": int(count),
            "percentage": round(float((count / total_crimes) * 100), 2),
            "top_categories": top_cats_str,
            "arrest_rate": round(float((arrests / group_len) * 100), 2) if group_len > 0 else 0.0,
            "domestic_rate": round(float((domestics / group_len) * 100), 2) if group_len > 0 else 0.0
        })
        
    logger.info(f"Hotspot Detection: Identified and ranked the top {len(hotspots)} geospatial hotspots.")
    return hotspots, df_clean

def generate_hotspot_map(
    df: pd.DataFrame,
    hotspots: List[Dict[str, Any]],
    output_path: str = "outputs/maps/hotspot_map.html"
) -> str:
    """
    Renders an interactive Folium map representing hotspots as circle overlays
    with details, tooltips, and ranked markers.
    """
    df_clean = validate_coordinates(df)
    if len(df_clean) == 0:
        center_lat, center_lon = 41.8781, -87.6298
    else:
        center_lat, center_lon = get_geographic_center(df_clean)
        
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=12,
        tiles="Cartodb dark_matter",
        name="Dark Mode"
    )
    
    folium.TileLayer("Cartodb positron", name="Light Mode").add_to(m)
    folium.TileLayer("OpenStreetMap", name="Detailed Street Map").add_to(m)
    
    # Plot hotspots
    hotspot_layer = folium.FeatureGroup(name="Ranked Hotspots")
    
    # Define color scale for hotspots (Red is top, down to yellow/orange)
    colors = ["#ff0000", "#ff4500", "#ff8c00", "#ffa500", "#ffbe00", "#ffd700", "#e6e600", "#c8e600", "#aae600", "#8ce600"]
    
    for h in hotspots:
        color = colors[min(h["rank"] - 1, len(colors) - 1)]
        
        # Circle size proportional to density
        radius_meters = float(h["incident_count"]) * 1.5
        # Cap radius bounds for neat visualization
        radius_meters = max(min(radius_meters, 800.0), 100.0)
        
        # HTML formatted popup
        popup_html = f"""
        <div style="font-family: sans-serif; font-size: 13px; color: #1a1a1e; width: 240px;">
            <h4 style="margin: 0 0 8px 0; color: {color}; text-transform: uppercase;">Hotspot Rank #{h["rank"]}</h4>
            <table style="width: 100%; border-collapse: collapse;">
                <tr><td style="padding: 2px 0;"><b>Incidents:</b></td><td style="text-align: right;">{h["incident_count"]} ({h["percentage"]}%)</td></tr>
                <tr><td style="padding: 2px 0;"><b>Centroid:</b></td><td style="text-align: right; font-size: 11px;">{h["latitude"]:.4f}, {h["longitude"]:.4f}</td></tr>
                <tr><td style="padding: 2px 0;"><b>Arrest Rate:</b></td><td style="text-align: right;">{h["arrest_rate"]}%</td></tr>
                <tr><td style="padding: 2px 0;"><b>Domestic Rate:</b></td><td style="text-align: right;">{h["domestic_rate"]}%</td></tr>
            </table>
            <div style="margin-top: 8px; border-top: 1px solid #ddd; padding-top: 6px;">
                <b>Top Offenses:</b><br/>
                <span style="font-size: 11px; color: #555;">{h["top_categories"]}</span>
            </div>
        </div>
        """
        
        # Add Circle
        folium.Circle(
            location=[h["latitude"], h["longitude"]],
            radius=radius_meters,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.3,
            popup=folium.Popup(popup_html, max_width=260),
            tooltip=f"Rank #{h['rank']}: {h['incident_count']} Incidents"
        ).add_to(hotspot_layer)
        
        # Add numbered marker icon
        folium.map.Marker(
            location=[h["latitude"], h["longitude"]],
            icon=folium.DivIcon(
                html=f"""<div style="font-family: sans-serif; color: white; background-color: {color}; 
                      border-radius: 50%; width: 24px; height: 24px; line-height: 24px; text-align: center; 
                      font-weight: bold; border: 2px solid white; font-size: 11px; transform: translate(-12px, -12px);">
                      {h["rank"]}
                      </div>"""
            )
        ).add_to(hotspot_layer)
        
    hotspot_layer.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    
    # Save map
    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir)
        
    m.save(output_path)
    logger.info(f"Geospatial hotspot map saved to: {output_path}")
    return output_path
