import os
import folium
from folium.plugins import HeatMap
import pandas as pd
from src.geospatial.geo_utils import validate_coordinates, get_geographic_center
from src.utils.logging_config import logger

def generate_crime_heatmap(
    df: pd.DataFrame, 
    output_path: str = "outputs/maps/crime_heatmap.html",
    radius: int = 15,
    blur: int = 10,
    zoom_start: int = 11
) -> str:
    """
    Creates an interactive Folium map with a crime density heatmap layer.
    Saves the output map as an HTML file.
    """
    # Clean and validate
    df_clean = validate_coordinates(df)
    if len(df_clean) == 0:
        logger.warning("Empty dataset passed to heatmap generator. Creating empty map.")
        # Center in Chicago
        center_lat, center_lon = 41.8781, -87.6298
    else:
        center_lat, center_lon = get_geographic_center(df_clean)
        
    logger.info(f"Generating heatmap around map center: ({center_lat:.4f}, {center_lon:.4f})")
    
    # Initialize Folium Map with premium CartoDB Dark Matter tile as default
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_start,
        tiles="Cartodb dark_matter",
        name="Dark Mode"
    )
    
    # Add other basemaps for premium customization
    folium.TileLayer("Cartodb positron", name="Light Mode").add_to(m)
    folium.TileLayer("OpenStreetMap", name="Detailed Street Map").add_to(m)
    
    # Extract coordinate points: list of [lat, lon]
    heat_data = df_clean[["latitude", "longitude"]].values.tolist()
    
    # Create and add HeatMap layer
    HeatMap(
        data=heat_data,
        radius=radius,
        blur=blur,
        min_opacity=0.3,
        max_zoom=18,
        name="Crime Density Heatmap"
    ).add_to(m)
    
    # Layer control panel
    folium.LayerControl(collapsed=False).add_to(m)
    
    # Ensure parent directories exist
    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir)
        
    m.save(output_path)
    logger.info(f"Geospatial crime heatmap successfully saved to: {output_path}")
    return output_path
