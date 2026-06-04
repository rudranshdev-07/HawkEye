import pytest
import pandas as pd
import numpy as np
from src.analytics.analytics_engine import CrimeAnalyticsEngine

@pytest.fixture
def clean_crime_data():
    return pd.DataFrame({
        "crime_id": ["CR-1", "CR-2", "CR-3", "CR-4", "CR-5"],
        "date": pd.to_datetime([
            "2023-01-01 02:00:00",  # Sunday, Hour 2
            "2023-01-02 14:00:00",  # Monday, Hour 14
            "2023-01-03 20:00:00",  # Tuesday, Hour 20
            "2023-01-03 22:30:00",  # Tuesday, Hour 22
            "2023-06-15 08:00:00"   # Thursday, Hour 8
        ]),
        "category": ["THEFT", "BATTERY", "THEFT", "NARCOTICS", "THEFT"],
        "description": ["PETTY", "SIMPLE", "GRAND", "POSSESSION", "PETTY"],
        "latitude": [41.8781, 41.9484, 41.7789, 41.8806, 41.8781],
        "longitude": [-87.6298, -87.6553, -87.6290, -87.7269, -87.6298],
        "location_description": ["STREET", "ALLEY", "STREET", "SIDEWALK", "RESIDENCE"],
        "arrest": [False, True, False, True, False],
        "domestic": [False, True, False, False, False],
        "district": ["D-01", "D-02", "D-01", "D-03", "D-01"],
        "ward": ["W-01", "W-02", "W-01", "W-03", "W-01"]
    })

def test_initialization_and_temporal_extraction(clean_crime_data):
    engine = CrimeAnalyticsEngine(clean_crime_data)
    df = engine.df
    
    # Check that new fields are created
    assert "year" in df.columns
    assert "month" in df.columns
    assert "day_name" in df.columns
    assert "hour" in df.columns
    
    # Sunday = 6, Monday = 0, Tuesday = 1, Thursday = 3
    assert list(df["day_of_week"]) == [6, 0, 1, 1, 3]
    assert list(df["hour"]) == [2, 14, 20, 22, 8]

def test_frequency_analysis(clean_crime_data):
    engine = CrimeAnalyticsEngine(clean_crime_data)
    freq = engine.run_frequency_analysis()
    
    assert freq["total_records"] == 5
    assert freq["days_covered"] == 4  # 1/1, 1/2, 1/3, 6/15
    assert freq["daily_average"] == 1.25  # 5 / 4

def test_category_analysis(clean_crime_data):
    engine = CrimeAnalyticsEngine(clean_crime_data)
    cats = engine.run_category_analysis()
    
    assert cats["THEFT"]["count"] == 3
    assert cats["THEFT"]["percentage"] == 60.0
    assert cats["BATTERY"]["count"] == 1
    assert cats["BATTERY"]["percentage"] == 20.0
    assert cats["NARCOTICS"]["count"] == 1
    assert cats["NARCOTICS"]["percentage"] == 20.0

def test_temporal_trends(clean_crime_data):
    engine = CrimeAnalyticsEngine(clean_crime_data)
    trends = engine.run_temporal_analysis()
    
    # Yearly
    assert trends["yearly_trends"]["2023"] == 5
    
    # Monthly Seasonality
    assert trends["monthly_seasonality"]["January"] == 4
    assert trends["monthly_seasonality"]["June"] == 1
    assert trends["monthly_seasonality"]["December"] == 0
    
    # Weekly distribution
    assert trends["weekly_distribution"]["Sunday"] == 1
    assert trends["weekly_distribution"]["Monday"] == 1
    assert trends["weekly_distribution"]["Tuesday"] == 2
    assert trends["weekly_distribution"]["Thursday"] == 1
    assert trends["weekly_distribution"]["Friday"] == 0
    
    # Hourly distribution
    assert trends["hourly_distribution"][2] == 1
    assert trends["hourly_distribution"][14] == 1
    assert trends["hourly_distribution"][20] == 1
    assert trends["hourly_distribution"][22] == 1
    assert trends["hourly_distribution"][8] == 1
    assert trends["hourly_distribution"][0] == 0

def test_location_analysis(clean_crime_data):
    engine = CrimeAnalyticsEngine(clean_crime_data)
    locs = engine.run_location_analysis()
    
    assert locs["top_locations"]["STREET"] == 2
    assert locs["top_locations"]["RESIDENCE"] == 1
    assert locs["top_districts"]["D-01"] == 3

def test_statistical_summaries(clean_crime_data):
    engine = CrimeAnalyticsEngine(clean_crime_data)
    stats = engine.run_statistical_summaries()
    
    # 2 arrests out of 5 crimes = 40.0%
    assert stats["overall_arrest_rate"] == 40.0
    # 1 domestic out of 5 crimes = 20.0%
    assert stats["overall_domestic_rate"] == 20.0
    
    # Arrest rates by category
    # THEFT: 0 arrests out of 3 = 0%
    assert stats["arrest_rates_by_category"]["THEFT"]["arrest_rate"] == 0.0
    # BATTERY: 1 arrest out of 1 = 100%
    assert stats["arrest_rates_by_category"]["BATTERY"]["arrest_rate"] == 100.0
    # NARCOTICS: 1 arrest out of 1 = 100%
    assert stats["arrest_rates_by_category"]["NARCOTICS"]["arrest_rate"] == 100.0
    
    # Day-Hour matrix size: 7 days x 24 hours
    matrix = stats["day_hour_density_matrix"]
    assert len(matrix) == 7
    assert len(matrix[0]) == 24
    
    # 2023-01-01 02:00:00 is Sunday (DOW 6), Hour 2
    assert matrix[6][2] == 1
    # 2023-01-02 14:00:00 is Monday (DOW 0), Hour 14
    assert matrix[0][14] == 1
    # 2023-01-03 20:00:00 is Tuesday (DOW 1), Hour 20
    assert matrix[1][20] == 1
    # 2023-01-03 22:30:00 is Tuesday (DOW 1), Hour 22
    assert matrix[1][22] == 1
    # 2023-06-15 08:00:00 is Thursday (DOW 3), Hour 8
    assert matrix[3][8] == 1
    
    # Monday Hour 0 should be 0
    assert matrix[0][0] == 0
