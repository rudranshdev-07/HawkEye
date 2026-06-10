import pandas as pd

print("Loading Indian Dataset...")

df = pd.read_csv(
    "data/raw/india_crime_data.csv"
)

# --------------------------------
# MAP TO HAWKEYE SCHEMA
# --------------------------------

df["category"] = df["crime_type"]

df["description"] = (
    df["crime_type"]
    + " incident reported in "
    + df["district"]
)

df["location_description"] = df["district"]

df["ward"] = df["district"]

# --------------------------------
# SELECT COLUMNS
# --------------------------------

converted_df = df[
    [
        "crime_id",
        "date",
        "category",
        "description",
        "latitude",
        "longitude",
        "location_description",
        "arrest",
        "domestic",
        "district",
        "ward"
    ]
]

# --------------------------------
# SAVE
# --------------------------------

converted_df.to_csv(
    "data/processed/crime_processed_data.csv",
    index=False
)

print("SUCCESS")
print("Rows:", len(converted_df))
print("Saved -> data/processed/crime_processed_data.csv")