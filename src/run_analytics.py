import argparse
import json
import os
import pandas as pd
from src.analytics.analytics_engine import CrimeAnalyticsEngine
from src.visualization.charts import generate_and_save_charts
from src.utils.logging_config import logger

def main():
    parser = argparse.ArgumentParser(description="HawkEye Crime Analytics Engine")
    parser.add_argument(
        "--processed-path",
        type=str,
        default="data/processed/crime_processed_data.csv",
        help="Path to the cleaned/processed CSV file"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="reports/charts",
        help="Directory to save visual charts"
    )
    parser.add_argument(
        "--report-path",
        type=str,
        default="data/processed/analytics_summary.json",
        help="Path to save the JSON summary report"
    )
    
    args = parser.parse_args()
    
    logger.info("Starting Crime Analytics Engine...")
    
    if not os.path.exists(args.processed_path):
        logger.error(f"Processed dataset not found: {args.processed_path}")
        print(f"\nERROR: Cleaned dataset not found at {args.processed_path}. Please run Phase 1 first!\n")
        exit(1)
        
    try:
        # Load processed data
        df = pd.read_csv(args.processed_path)
        
        # Instantiate and run analysis
        engine = CrimeAnalyticsEngine(df)
        report = engine.generate_all_reports()
        
        # Ensure target directories exist
        report_dir = os.path.dirname(args.report_path)
        if report_dir and not os.path.exists(report_dir):
            os.makedirs(report_dir)
            
        # Save JSON report
        with open(args.report_path, "w") as f:
            json.dump(report, f, indent=4)
        logger.info(f"JSON analysis summary saved to: {args.report_path}")
        
        # Generate Visual Charts
        generate_and_save_charts(report, args.output_dir)
        
        # Print a formatted console output
        freq = report["frequency"]
        cats = report["categories"]
        stats = report["statistics"]
        locations = report["locations"]
        
        print("\n" + "=" * 50)
        print("          HAWKEYE CRIME ANALYTICS REPORT          ")
        print("=" * 50)
        print(f"Processed Dataset:       {args.processed_path}")
        print(f"JSON Report Path:        {args.report_path}")
        print(f"Charts Saved to:         {args.output_dir}/")
        print("-" * 50)
        print(f"Total Crimes Analyzed:   {freq['total_records']}")
        print(f"Days Covered:            {freq['days_covered']}")
        print(f"Daily Crime Average:     {freq['daily_average']:.2f}")
        print(f"Overall Arrest Rate:     {stats['overall_arrest_rate']}%")
        print(f"Overall Domestic Rate:   {stats['overall_domestic_rate']}%")
        print("-" * 50)
        print("Top 5 Crime Categories:")
        sorted_cats = sorted(cats.items(), key=lambda x: x[1]["count"], reverse=True)[:5]
        for cat, details in sorted_cats:
            print(f"  - {cat:22} {details['count']:>5} ({details['percentage']:.2f}%)")
        print("-" * 50)
        print("Top 5 Crime Locations:")
        sorted_locs = sorted(locations["top_locations"].items(), key=lambda x: x[1], reverse=True)[:5]
        for loc, count in sorted_locs:
            print(f"  - {loc:22} {count:>5}")
        print("=" * 50 + "\n")
        
    except Exception as e:
        logger.critical(f"Analytics engine failed: {str(e)}", exc_info=True)
        print(f"\nERROR: Analytics execution failed: {str(e)}\n")
        exit(1)

if __name__ == "__main__":
    main()
