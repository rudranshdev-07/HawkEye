import os
import random
import argparse
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from src.utils.logging_config import logger

def generate_crime_dataset(num_records: int = 5000, seed: int = 42) -> pd.DataFrame:
    """
    Generates a realistic mock crime dataset with spatial hotspots, temporal patterns,
    and schema anomalies (missing fields, duplicates, invalid bounds).
    """
    np.random.seed(seed)
    random.seed(seed)
    
    logger.info(f"Generating synthetic dataset with {num_records} records...")
    
    # 1. Hotspot centers (lat, lon) in a Chicago-like coordinate frame
    hotspots = [
        {"name": "Downtown", "lat": 41.8781, "lon": -87.6298, "weight": 0.4, "spread": 0.015},
        {"name": "North Side", "lat": 41.9484, "lon": -87.6553, "weight": 0.25, "spread": 0.02},
        {"name": "South Side", "lat": 41.7789, "lon": -87.6290, "weight": 0.25, "spread": 0.025},
        {"name": "West Side", "lat": 41.8806, "lon": -87.7269, "weight": 0.1, "spread": 0.018}
    ]
    
    # 2. Base Categories and Descriptions
    crime_templates = {
        "THEFT": ["PETTY THEFT", "GRAND THEFT", "FROM BUILDING", "RETAIL THEFT"],
        "BATTERY": ["SIMPLE BATTERY", "AGGRAVATED BATTERY", "DOMESTIC BATTERY"],
        "ASSAULT": ["SIMPLE ASSAULT", "AGGRAVATED ASSAULT"],
        "CRIMINAL DAMAGE": ["TO VEHICLE", "TO PROPERTY", "GRAFFITI"],
        "BURGLARY": ["RESIDENTIAL", "COMMERCIAL", "FORCIBLE ENTRY"],
        "ROBBERY": ["ARMED ROBBERY", "STRONGARM ROBBERY"],
        "NARCOTICS": ["POSSESSION OF HEROIN", "POSSESSION OF COCAINE", "SALE/MANUFACTURE"],
        "MOTOR VEHICLE THEFT": ["AUTOMOBILE", "TRUCK", "MOTORCYCLE"]
    }
    
    # Location descriptions
    location_types = ["STREET", "ALLEY", "RESIDENCE", "APARTMENT", "SIDEWALK", "PARKING LOT", "COMMERCIAL BUILDING", "PARK"]
    
    # 3. Generate Records
    records = []
    
    # Dates spanning 3 years (2023-01-01 to 2025-12-31)
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2025, 12, 31)
    days_range = (end_date - start_date).days
    
    for i in range(num_records):
        # Unique ID
        crime_id = f"CR-{2023 + (i % 3)}-{i:06d}"
        
        # Temporal Simulation:
        # A: Seasonal: Crime is higher in summer months (June-August)
        # B: Weekly: Crime is higher on Friday/Saturday
        # C: Diurnal: Crime is higher at night (8 PM - 2 AM)
        while True:
            rand_day = random.randint(0, days_range)
            date_val = start_date + timedelta(days=rand_day)
            
            # Month weight (Summer high)
            month = date_val.month
            month_weight = 1.3 if month in [6, 7, 8] else (0.8 if month in [1, 2, 12] else 1.0)
            
            # Day of week weight (Weekend high)
            weekday = date_val.weekday()  # 0=Mon, 6=Sun
            weekday_weight = 1.2 if weekday in [4, 5] else 0.9
            
            # Hour (Night high)
            hour = random.randint(0, 23)
            hour_weight = 1.4 if hour >= 20 or hour <= 2 else 0.7
            
            # Random test
            combined_prob = month_weight * weekday_weight * hour_weight
            if random.random() < (combined_prob / 3.0):
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                date_str = date_val.replace(hour=hour, minute=minute, second=second).strftime("%Y-%m-%d %H:%M:%S")
                break
        
        # Category selection
        category = random.choice(list(crime_templates.keys()))
        description = random.choice(crime_templates[category])
        
        # Hotspot simulation: pick hotspot based on weights
        chosen_spot = random.choices(hotspots, weights=[h["weight"] for h in hotspots], k=1)[0]
        latitude = float(np.random.normal(chosen_spot["lat"], chosen_spot["spread"]))
        longitude = float(np.random.normal(chosen_spot["lon"], chosen_spot["spread"]))
        
        location_desc = random.choice(location_types)
        
        # Arrest / Domestic probabilities based on category
        if category in ["NARCOTICS", "BATTERY"]:
            arrest = random.random() < 0.75
        else:
            arrest = random.random() < 0.15
            
        domestic = random.random() < 0.35 if category in ["BATTERY", "ASSAULT"] else random.random() < 0.05
        
        district = f"D-{random.randint(1, 15):02d}"
        ward = f"W-{random.randint(1, 50):02d}"
        
        records.append({
            "crime_id": crime_id,
            "date": date_str,
            "category": category,
            "description": description,
            "latitude": latitude,
            "longitude": longitude,
            "location_description": location_desc,
            "arrest": arrest,
            "domestic": domestic,
            "district": district,
            "ward": ward
        })
        
    df = pd.DataFrame(records)
    
    # 4. Inject intentional anomalies for testing
    logger.info("Injecting anomalies for ingestion system validation...")
    
    # A. Introduce duplicates (about 1.5% of rows)
    num_duplicates = int(num_records * 0.015)
    dup_indices = np.random.choice(len(df), size=num_duplicates, replace=False)
    dup_rows = df.iloc[dup_indices].copy()
    # Make them exact matches
    df = pd.concat([df, dup_rows], ignore_index=True)
    
    # B. Introduce duplicate crime_ids with different values (about 0.5%)
    num_id_duplicates = int(num_records * 0.005)
    id_dup_indices = np.random.choice(len(df), size=num_id_duplicates, replace=False)
    for idx in id_dup_indices:
        new_row = df.iloc[idx].copy()
        new_row["category"] = "OTHER OFFENSE"
        new_row["description"] = "DUPLICATE ID TEST RECORD"
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        
    # C. Introduce missing coordinates (about 1%)
    missing_coords_indices = np.random.choice(len(df), size=int(num_records * 0.01), replace=False)
    df.loc[missing_coords_indices, "latitude"] = np.nan
    df.loc[missing_coords_indices, "longitude"] = np.nan
    
    # D. Introduce invalid coordinates (about 0.5%)
    invalid_coords_indices = np.random.choice(len(df), size=int(num_records * 0.005), replace=False)
    # Latitude out of bounds
    df.loc[invalid_coords_indices[:len(invalid_coords_indices)//2], "latitude"] = 95.0
    # Longitude out of bounds
    df.loc[invalid_coords_indices[len(invalid_coords_indices)//2:], "longitude"] = -190.0
    
    # E. Introduce malformed date string (about 0.5%)
    malformed_date_indices = np.random.choice(len(df), size=int(num_records * 0.005), replace=False)
    df.loc[malformed_date_indices, "date"] = "not-a-valid-date-string"
    
    # F. Introduce unrecognized categories (about 1%)
    unrecognized_cat_indices = np.random.choice(len(df), size=int(num_records * 0.01), replace=False)
    df.loc[unrecognized_cat_indices, "category"] = "PETTY THEFT"  # Not in the official list
    
    # G. Introduce missing description / domestic / district
    missing_desc_indices = np.random.choice(len(df), size=int(num_records * 0.03), replace=False)
    df.loc[missing_desc_indices, "description"] = np.nan
    
    missing_domestic_indices = np.random.choice(len(df), size=int(num_records * 0.02), replace=False)
    df["domestic"] = df["domestic"].astype(object)
    df.loc[missing_domestic_indices, "domestic"] = np.nan
    
    # Shuffle dataframe
    df = df.sample(frac=1).reset_index(drop=True)
    
    logger.info(f"Anomaly injection complete. Generated shape: {df.shape}")
    return df

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate mock crime data for HawkEye testing.")
    parser.add_argument("--output", type=str, default="data/raw/crime_raw_data.csv", help="Path to save generated CSV file.")
    parser.add_argument("--records", type=int, default=5000, help="Number of records to generate.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    
    args = parser.parse_args()
    
    # Ensure directory exists
    out_dir = os.path.dirname(args.output)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir)
        
    df = generate_crime_dataset(num_records=args.records, seed=args.seed)
    df.to_csv(args.output, index=False)
    logger.info(f"Mock crime dataset saved to: {args.output}")
