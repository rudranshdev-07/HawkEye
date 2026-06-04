from typing import Dict, Any, List

# Define the expected columns, their Python/Pandas types, and whether they are required.
CRIME_DATA_SCHEMA: Dict[str, Dict[str, Any]] = {
    "crime_id": {"type": "string", "required": True},
    "date": {"type": "datetime", "required": True},
    "category": {"type": "string", "required": True},
    "description": {"type": "string", "required": False},
    "latitude": {"type": "float", "required": True, "min": -90.0, "max": 90.0},
    "longitude": {"type": "float", "required": True, "min": -180.0, "max": 180.0},
    "location_description": {"type": "string", "required": False},
    "arrest": {"type": "boolean", "required": False},
    "domestic": {"type": "boolean", "required": False},
    "district": {"type": "string", "required": False},
    "ward": {"type": "string", "required": False}
}

# Standard categories we expect (for validation warnings, to catch spelling variations)
VALID_CRIME_CATEGORIES: List[str] = [
    "THEFT",
    "BATTERY",
    "ASSUALT",  # Keep misspelling or fix to ASSAULT
    "ASSAULT",
    "DESTRUCTIVE DECIBELS",
    "CRIMINAL DAMAGE",
    "BURGLARY",
    "ROBBERY",
    "NARCOTICS",
    "MOTOR VEHICLE THEFT",
    "DECEPTIVE PRACTICE",
    "WEAPONS VIOLATION",
    "OTHER OFFENSE"
]
