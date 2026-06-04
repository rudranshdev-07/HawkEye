import pytest
import pandas as pd
import numpy as np
from src.preprocessing.ingestion import CrimeDataIngestor
from src.preprocessing.schemas import CRIME_DATA_SCHEMA

@pytest.fixture
def sample_valid_data():
    return pd.DataFrame({
        "crime_id": ["CR-001", "CR-002", "CR-003"],
        "date": ["2023-06-01 12:00:00", "2023-06-02 13:00:00", "2023-06-03 14:00:00"],
        "category": ["THEFT", "BATTERY", "ASSAULT"],
        "description": ["PETTY THEFT", "SIMPLE BATTERY", "SIMPLE ASSAULT"],
        "latitude": [41.8781, 41.9484, 41.7789],
        "longitude": [-87.6298, -87.6553, -87.6290],
        "location_description": ["STREET", "ALLEY", "RESIDENCE"],
        "arrest": [True, False, True],
        "domestic": [False, True, False],
        "district": ["D-01", "D-02", "D-03"],
        "ward": ["W-01", "W-02", "W-03"]
    })

def test_validate_schema_success(sample_valid_data):
    ingestor = CrimeDataIngestor()
    is_valid, missing = ingestor.validate_schema(sample_valid_data)
    assert is_valid is True
    assert len(missing) == 0

def test_validate_schema_missing_required(sample_valid_data):
    # Drop required column 'crime_id'
    invalid_data = sample_valid_data.drop(columns=["crime_id"])
    ingestor = CrimeDataIngestor()
    is_valid, missing = ingestor.validate_schema(invalid_data)
    assert is_valid is False
    assert "crime_id" in missing

def test_validate_schema_missing_optional(sample_valid_data):
    # Drop optional column 'district'
    valid_data_missing_opt = sample_valid_data.drop(columns=["district"])
    ingestor = CrimeDataIngestor()
    is_valid, missing = ingestor.validate_schema(valid_data_missing_opt)
    # Optional field shouldn't fail schema validation
    assert is_valid is True
    assert len(missing) == 0

def test_duplicate_detection(sample_valid_data):
    # Add a duplicate record
    dup_row = sample_valid_data.iloc[[0]]
    duplicated_df = pd.concat([sample_valid_data, dup_row], ignore_index=True)
    
    ingestor = CrimeDataIngestor()
    cleaned_df, report = ingestor.clean_and_validate_data(duplicated_df)
    
    assert report["duplicates_removed"] == 1
    assert len(cleaned_df) == len(sample_valid_data)

def test_invalid_coordinates(sample_valid_data):
    # Add record with invalid latitude
    bad_row = sample_valid_data.iloc[[0]].copy()
    bad_row["crime_id"] = "CR-004"
    bad_row["latitude"] = 95.0  # Invalid
    
    # Add record with NaN coordinates
    nan_row = sample_valid_data.iloc[[0]].copy()
    nan_row["crime_id"] = "CR-005"
    nan_row["latitude"] = np.nan
    nan_row["longitude"] = np.nan
    
    test_df = pd.concat([sample_valid_data, bad_row, nan_row], ignore_index=True)
    
    ingestor = CrimeDataIngestor()
    cleaned_df, report = ingestor.clean_and_validate_data(test_df)
    
    assert report["invalid_coordinates_removed"] == 2
    assert len(cleaned_df) == len(sample_valid_data)

def test_invalid_date_parsing(sample_valid_data):
    bad_date_row = sample_valid_data.iloc[[0]].copy()
    bad_date_row["crime_id"] = "CR-006"
    bad_date_row["date"] = "not-a-valid-date"
    
    test_df = pd.concat([sample_valid_data, bad_date_row], ignore_index=True)
    
    ingestor = CrimeDataIngestor()
    cleaned_df, report = ingestor.clean_and_validate_data(test_df)
    
    assert report["invalid_dates_removed"] == 1
    assert len(cleaned_df) == len(sample_valid_data)
