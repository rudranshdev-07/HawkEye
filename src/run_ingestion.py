import argparse
import json
import os
from src.preprocessing.ingestion import CrimeDataIngestor
from src.utils.logging_config import logger

def main():
    parser = argparse.ArgumentParser(description="HawkEye Data Ingestion Pipeline")
    parser.add_argument(
        "--raw-path", 
        type=str, 
        default="data/raw/crime_raw_data.csv", 
        help="Path to the raw CSV file"
    )
    parser.add_argument(
        "--processed-path", 
        type=str, 
        default="data/processed/crime_processed_data.csv", 
        help="Path to save the processed CSV file"
    )
    
    args = parser.parse_args()
    
    logger.info("Starting Data Ingestion System...")
    
    try:
        ingestor = CrimeDataIngestor()
        cleaned_df, report = ingestor.process_and_save(args.raw_path, args.processed_path)
        
        # Save a summary report to disk
        report_dir = "data/processed"
        report_path = os.path.join(report_dir, "ingestion_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=4)
            
        logger.info("Ingestion completed successfully.")
        
        # Format a user-friendly console block
        print("\n" + "=" * 50)
        print("          HAWKEYE INGESTION PIPELINE REPORT          ")
        print("=" * 50)
        print(f"Raw Input File:          {args.raw_path}")
        print(f"Processed Output File:   {args.processed_path}")
        print(f"Report Output File:      {report_path}")
        print("-" * 50)
        print(f"Initial Rows Loaded:     {report['initial_rows']}")
        print(f"Duplicates Removed:      {report['duplicates_removed']}")
        print(f"Invalid Dates Removed:   {report['invalid_dates_removed']}")
        print(f"Invalid Coords Removed:  {report['invalid_coordinates_removed']}")
        print(f"Final Cleaned Rows:      {report['final_rows']}")
        print("-" * 50)
        print("Column Missing Value Counts:")
        for col, info in report["missing_values_before"].items():
            if info["count"] > 0:
                print(f"  - {col:25} {info['count']:>6} ({info['percentage']:.2f}%)")
        print("=" * 50 + "\n")
        
    except Exception as e:
        logger.critical(f"Ingestion pipeline failed: {str(e)}", exc_info=True)
        print(f"\nERROR: Ingestion pipeline failed: {str(e)}\n")
        exit(1)

if __name__ == "__main__":
    main()
