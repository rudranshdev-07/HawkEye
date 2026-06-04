import os
import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any
from src.utils.logging_config import logger
from src.preprocessing.schemas import CRIME_DATA_SCHEMA, VALID_CRIME_CATEGORIES

class CrimeDataIngestor:
    """
    Ingestor class responsible for loading, validating, cleaning, and reporting
    on raw crime datasets.
    """

    def __init__(self, schema: Dict[str, Dict[str, Any]] = CRIME_DATA_SCHEMA):
        self.schema = schema
        self.ingestion_report: Dict[str, Any] = {}

    def load_csv(self, file_path: str) -> pd.DataFrame:
        """
        Loads CSV file safely and logs the process.
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"Raw data file not found at {file_path}")
        
        logger.info(f"Attempting to load CSV file from: {file_path}")
        try:
            df = pd.read_csv(file_path)
            logger.info(f"Successfully loaded CSV with {len(df)} rows and {len(df.columns)} columns.")
            return df
        except Exception as e:
            logger.error(f"Error loading CSV file: {str(e)}")
            raise e

    def validate_schema(self, df: pd.DataFrame) -> Tuple[bool, list]:
        """
        Verifies that all required columns in the schema exist in the DataFrame.
        """
        missing_required = []
        for col, col_info in self.schema.items():
            if col_info["required"] and col not in df.columns:
                missing_required.append(col)
        
        if missing_required:
            logger.error(f"Schema validation failed. Missing required columns: {missing_required}")
            return False, missing_required
        
        logger.info("Schema validation succeeded. All required columns are present.")
        return True, []

    def clean_and_validate_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Performs data cleaning: type casting, coordinate validation,
        missing value detection, and duplicate removal.
        """
        initial_row_count = len(df)
        report = {
            "initial_rows": initial_row_count,
            "missing_values_before": {},
            "duplicates_removed": 0,
            "invalid_coordinates_removed": 0,
            "invalid_dates_removed": 0,
            "final_rows": 0
        }

        # Step 1: Detect missing values before clean
        for col in df.columns:
            missing_count = int(df[col].isna().sum())
            missing_pct = (missing_count / initial_row_count) * 100 if initial_row_count > 0 else 0
            report["missing_values_before"][col] = {
                "count": missing_count,
                "percentage": round(missing_pct, 2)
            }
            if missing_count > 0:
                logger.warning(f"Column '{col}' has {missing_count} missing values ({missing_pct:.2f}%).")

        # Step 2: Remove duplicates based on all columns or crime_id if it exists
        if "crime_id" in df.columns:
            # First log any duplicate IDs
            duplicate_ids = df.duplicated(subset=["crime_id"], keep=False).sum()
            if duplicate_ids > 0:
                logger.warning(f"Found {duplicate_ids} rows with duplicate crime_id.")
            
            # Keep the first occurrence
            cleaned_df = df.drop_duplicates(subset=["crime_id"], keep="first").copy()
            report["duplicates_removed"] = int(initial_row_count - len(cleaned_df))
        else:
            cleaned_df = df.drop_duplicates(keep="first").copy()
            report["duplicates_removed"] = int(initial_row_count - len(cleaned_df))
        
        if report["duplicates_removed"] > 0:
            logger.info(f"Removed {report['duplicates_removed']} duplicate rows.")

        # Step 3: Type casting and invalid value cleaning
        rows_before_validation = len(cleaned_df)

        # A: Validate and Parse Dates
        if "date" in cleaned_df.columns:
            cleaned_df["date"] = pd.to_datetime(cleaned_df["date"], errors="coerce")
            invalid_dates = cleaned_df["date"].isna()
            invalid_dates_count = int(invalid_dates.sum())
            if invalid_dates_count > 0:
                logger.warning(f"Found {invalid_dates_count} rows with invalid date formats. Dropping them.")
                cleaned_df = cleaned_df[~invalid_dates].copy()
                report["invalid_dates_removed"] = invalid_dates_count

        # B: Validate Coordinates (Latitude / Longitude)
        if "latitude" in cleaned_df.columns and "longitude" in cleaned_df.columns:
            # Cast to numeric
            cleaned_df["latitude"] = pd.to_numeric(cleaned_df["latitude"], errors="coerce")
            cleaned_df["longitude"] = pd.to_numeric(cleaned_df["longitude"], errors="coerce")

            # Check bounds based on schema
            lat_min = self.schema["latitude"].get("min", -90.0)
            lat_max = self.schema["latitude"].get("max", 90.0)
            lon_min = self.schema["longitude"].get("min", -180.0)
            lon_max = self.schema["longitude"].get("max", 180.0)

            valid_lat = (cleaned_df["latitude"] >= lat_min) & (cleaned_df["latitude"] <= lat_max)
            valid_lon = (cleaned_df["longitude"] >= lon_min) & (cleaned_df["longitude"] <= lon_max)
            valid_coords = valid_lat & valid_lon & cleaned_df["latitude"].notna() & cleaned_df["longitude"].notna()

            invalid_coords_count = int((~valid_coords).sum())
            if invalid_coords_count > 0:
                logger.warning(f"Found {invalid_coords_count} rows with invalid coordinates. Dropping them.")
                cleaned_df = cleaned_df[valid_coords].copy()
                report["invalid_coordinates_removed"] = invalid_coords_count

        # C: Convert Boolean flags
        for bool_col in ["arrest", "domestic"]:
            if bool_col in cleaned_df.columns:
                # Convert standard True/False, 1/0, "true"/"false" strings
                cleaned_df[bool_col] = cleaned_df[bool_col].map({
                    True: True, False: False,
                    1: True, 0: False,
                    "True": True, "False": False,
                    "true": True, "false": False,
                    "Y": True, "N": False,
                    "y": True, "n": False
                }).fillna(False).astype(bool)

        # D: Category cleaning (capitalize for consistency)
        if "category" in cleaned_df.columns:
            cleaned_df["category"] = cleaned_df["category"].str.strip().str.upper()
            # Issue warnings for unrecognized crime categories
            unrecognized = cleaned_df[~cleaned_df["category"].isin(VALID_CRIME_CATEGORIES)]["category"].unique()
            if len(unrecognized) > 0:
                logger.warning(f"Found unrecognized crime categories in data: {unrecognized}")

        report["final_rows"] = len(cleaned_df)
        logger.info(f"Cleaning complete. Retained {report['final_rows']} of {initial_row_count} raw rows.")
        
        self.ingestion_report = report
        return cleaned_df, report

    def process_and_save(self, raw_path: str, processed_path: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Complete pipeline: load raw CSV, validate schema, clean data, and save processed CSV.
        """
        # Load
        df = self.load_csv(raw_path)
        
        # Schema Validate
        is_valid, missing_cols = self.validate_schema(df)
        if not is_valid:
            raise ValueError(f"CSV schema is invalid. Missing required columns: {missing_cols}")
        
        # Clean
        cleaned_df, report = self.clean_and_validate_data(df)
        
        # Ensure target directory exists
        processed_dir = os.path.dirname(processed_path)
        if processed_dir and not os.path.exists(processed_dir):
            os.makedirs(processed_dir)
            
        # Save
        cleaned_df.to_csv(processed_path, index=False)
        logger.info(f"Processed dataset saved to: {processed_path}")
        
        return cleaned_df, report
