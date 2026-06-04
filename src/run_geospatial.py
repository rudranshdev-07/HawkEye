import argparse
import json
import os
import pandas as pd
from src.geospatial.geo_utils import validate_coordinates, compute_regional_statistics, get_geographic_center
from src.geospatial.heatmap import generate_crime_heatmap
from src.geospatial.hotspot_detector import detect_crime_hotspots, generate_hotspot_map
from src.geospatial.clustering import run_dbscan_clustering, generate_cluster_map
from src.utils.logging_config import logger

def main():
    parser = argparse.ArgumentParser(description="HawkEye Geospatial Intelligence Engine")
    parser.add_argument(
        "--processed-path",
        type=str,
        default="data/processed/crime_processed_data.csv",
        help="Path to the cleaned/processed CSV dataset"
    )
    parser.add_argument(
        "--maps-dir",
        type=str,
        default="outputs/maps",
        help="Directory to save generated interactive HTML maps"
    )
    parser.add_argument(
        "--reports-dir",
        type=str,
        default="outputs/reports",
        help="Directory to save geographic risk reports"
    )
    
    args = parser.parse_args()
    
    logger.info("Starting Geospatial Intelligence Engine...")
    
    if not os.path.exists(args.processed_path):
        logger.error(f"Cleaned dataset not found: {args.processed_path}")
        print(f"\nERROR: Processed dataset not found at {args.processed_path}. Run Phase 1 first!\n")
        exit(1)
        
    try:
        # Load dataset
        df = pd.read_csv(args.processed_path)
        
        # 1. Validate Coordinates
        df_clean = validate_coordinates(df)
        center_lat, center_lon = get_geographic_center(df_clean)
        
        # Ensure outputs folders exist
        os.makedirs(args.maps_dir, exist_ok=True)
        os.makedirs(args.reports_dir, exist_ok=True)
        
        # 2. Regional Risk Statistics
        regional_stats = compute_regional_statistics(df_clean)
        
        # 3. Hotspot Detection & Mapping
        hotspots, df_grid = detect_crime_hotspots(df_clean, grid_resolution=30, top_n=10)
        heatmap_path = os.path.join(args.maps_dir, "crime_heatmap.html")
        generate_crime_heatmap(df_clean, heatmap_path)
        
        hotspot_map_path = os.path.join(args.maps_dir, "hotspot_map.html")
        generate_hotspot_map(df_clean, hotspots, hotspot_map_path)
        
        # 4. DBSCAN Clustering & Mapping
        df_clustered, cluster_summary = run_dbscan_clustering(df_clean, eps_meters=300, min_samples=15)
        cluster_map_path = os.path.join(args.maps_dir, "cluster_map.html")
        generate_cluster_map(df_clustered, cluster_summary, cluster_map_path)
        
        # 5. Risk Summary Report Compilation
        risk_report = {
            "summary": {
                "total_crimes_analyzed": len(df_clean),
                "map_center": {"latitude": center_lat, "longitude": center_lon},
                "hotspots_detected_count": len(hotspots),
                "dbscan_clusters_count": cluster_summary.get("number_of_clusters", 0),
                "dbscan_noise_count": cluster_summary.get("noise_incidents_count", 0),
                "dbscan_noise_percentage": cluster_summary.get("noise_percentage", 0.0)
            },
            "regional_risk": regional_stats,
            "hotspots": hotspots,
            "clusters": cluster_summary.get("clusters", {})
        }
        
        # Save JSON Report
        report_path = os.path.join(args.reports_dir, "geospatial_risk_report.json")
        with open(report_path, "w") as f:
            json.dump(risk_report, f, indent=4)
        logger.info(f"Geospatial Risk Summary saved to: {report_path}")
        
        # Print a formatted console output
        print("\n" + "=" * 50)
        print("         HAWKEYE GEOSPATIAL INTEL REPORT          ")
        print("=" * 50)
        print(f"Processed Incidents:     {len(df_clean)}")
        print(f"Centroid Coordinates:    {center_lat:.4f}, {center_lon:.4f}")
        print(f"Risk Report Saved to:    {report_path}")
        print("-" * 50)
        print(f"Interactive Maps Generated (HTML):")
        print(f"  1. Heatmap:            {heatmap_path}")
        print(f"  2. Hotspot Map:        {hotspot_map_path}")
        print(f"  3. Cluster Map:        {cluster_map_path}")
        print("-" * 50)
        print("Top 3 High-Density Hotspots:")
        for h in hotspots[:3]:
            print(f"  Rank #{h['rank']}: Coords({h['latitude']:.4f}, {h['longitude']:.4f}) | Count: {h['incident_count']} | Arrests: {h['arrest_rate']}%")
        print("-" * 50)
        print("DBSCAN Clustering Profile:")
        print(f"  - Total Clusters:      {cluster_summary.get('number_of_clusters', 0)}")
        print(f"  - Outliers (Noise):     {cluster_summary.get('noise_incidents_count', 0)} ({cluster_summary.get('noise_percentage', 0.0)}%)")
        print("=" * 50 + "\n")
        
    except Exception as e:
        logger.critical(f"Geospatial engine failed: {str(e)}", exc_info=True)
        print(f"\nERROR: Geospatial execution failed: {str(e)}\n")
        exit(1)

if __name__ == "__main__":
    main()
