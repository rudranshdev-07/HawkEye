import os
import tempfile
import pytest
import numpy as np
import pandas as pd
from src.ml.feature_engineering import CrimeFeatureEngineer
from src.ml.preprocessing import CrimePreprocessor, prepare_data_splits
from src.ml.models import train_and_compare_models, save_serialized_pipeline, load_serialized_pipeline
from src.ml.risk_intelligence import RiskIntelligenceLayer, get_severity_weight

@pytest.fixture
def sample_ml_data():
    """
    Creates a sample DataFrame of 50 records representing various categories
    and coordinates, with some missing coordinates and various arrest outcomes.
    """
    # 25 thefts, 25 batteries
    np.random.seed(42)
    lats = np.random.normal(41.8781, 0.01, 50)
    lons = np.random.normal(-87.6298, 0.01, 50)
    
    # Inject some missing values
    lats[5] = np.nan
    lons[10] = np.nan
    
    dates = pd.date_range("2023-01-01 00:00:00", periods=50, freq="h").strftime("%Y-%m-%d %H:%M:%S")
    categories = ["THEFT"] * 25 + ["BATTERY"] * 25
    arrests = [False] * 20 + [True] * 5 + [True] * 20 + [False] * 5 # Different arrest rates for theft and battery
    
    return pd.DataFrame({
        "crime_id": [f"CR-{i:03d}" for i in range(50)],
        "date": dates,
        "category": categories,
        "description": ["PETTY"] * 25 + ["SIMPLE"] * 25,
        "latitude": lats,
        "longitude": lons,
        "arrest": arrests,
        "domestic": [False] * 40 + [True] * 10,
        "district": ["D-01"] * 25 + ["D-02"] * 25,
        "ward": ["W-01"] * 25 + ["W-02"] * 25
    })

def test_feature_engineering_extraction(sample_ml_data):
    engineer = CrimeFeatureEngineer(dbscan_eps_meters=300.0, dbscan_min_samples=5, num_hotspots=3)
    engineer.fit(sample_ml_data)
    
    df_feat = engineer.transform(sample_ml_data)
    
    # Test temporal feature extraction
    assert "hour" in df_feat.columns
    assert "day_of_week" in df_feat.columns
    assert "month" in df_feat.columns
    assert "year" in df_feat.columns
    
    # Test cyclical encodings
    assert "hour_sin" in df_feat.columns
    assert "hour_cos" in df_feat.columns
    assert "day_sin" in df_feat.columns
    
    # Test coordinates imputing
    assert df_feat["latitude"].isna().sum() == 0
    assert df_feat["longitude"].isna().sum() == 0
    
    # Test cluster-derived features (should create dist_to_cluster_* columns)
    cluster_cols = [c for c in df_feat.columns if c.startswith("dist_to_cluster_")]
    assert len(cluster_cols) > 0
    
    # Test hotspot-derived features (should create dist_to_hotspot_* columns)
    hotspot_cols = [c for c in df_feat.columns if c.startswith("dist_to_hotspot_")]
    assert len(hotspot_cols) > 0

def test_preprocessing_pipeline(sample_ml_data):
    preprocessor = CrimePreprocessor(dbscan_eps_meters=300.0, dbscan_min_samples=5, num_hotspots=2)
    preprocessor.fit(sample_ml_data)
    
    X_processed = preprocessor.transform(sample_ml_data)
    
    # Check that processed features is a 2D numpy array
    assert isinstance(X_processed, np.ndarray)
    assert len(X_processed.shape) == 2
    assert X_processed.shape[0] == len(sample_ml_data)
    
    # Verify feature names out
    feature_names = preprocessor.get_feature_names_out()
    assert len(feature_names) == X_processed.shape[1]
    
    # Test split function
    X_train, X_test, y_train, y_test = prepare_data_splits(sample_ml_data, target_col="arrest", test_size=0.2)
    assert len(X_train) == 40
    assert len(X_test) == 10
    assert len(y_train) == 40
    assert len(y_test) == 10
    assert y_train.name == "arrest"

def test_models_train_and_serialize(sample_ml_data):
    # Prepare split
    X_train, X_test, y_train, y_test = prepare_data_splits(sample_ml_data, target_col="arrest", test_size=0.2)
    
    # Fit preprocessor
    preprocessor = CrimePreprocessor(dbscan_eps_meters=300.0, dbscan_min_samples=5, num_hotspots=2)
    preprocessor.fit(X_train)
    
    X_train_p = preprocessor.transform(X_train)
    X_test_p = preprocessor.transform(X_test)
    
    # Train models
    eval_results, best_name, best_model = train_and_compare_models(
        X_train_p, y_train.values, X_test_p, y_test.values
    )
    
    # Verify models evaluated
    assert "Random Forest" in eval_results
    assert "Gradient Boosting" in eval_results
    assert "Decision Tree" in eval_results
    assert "Logistic Regression" in eval_results
    
    assert best_name in eval_results
    assert best_model is not None
    
    # Test persistence in temp dir
    with tempfile.TemporaryDirectory() as tmpdir:
        prep_path, model_path = save_serialized_pipeline(preprocessor, best_model, tmpdir)
        
        assert os.path.exists(prep_path)
        assert os.path.exists(model_path)
        
        # Load back
        loaded_prep, loaded_model = load_serialized_pipeline(tmpdir)
        assert loaded_prep is not None
        assert loaded_model is not None
        
        # Check we can transform unseen data
        X_unseen_p = loaded_prep.transform(X_test)
        assert X_unseen_p.shape == X_test_p.shape
        
        # Check predictions
        preds = loaded_model.predict(X_unseen_p)
        assert len(preds) == len(X_test)

def test_risk_intelligence_layer(sample_ml_data):
    # Preprocessor and mock model
    preprocessor = CrimePreprocessor(dbscan_eps_meters=300.0, dbscan_min_samples=5, num_hotspots=2)
    preprocessor.fit(sample_ml_data)
    
    X_p = preprocessor.transform(sample_ml_data)
    
    # We will fit a simple model
    from sklearn.tree import DecisionTreeClassifier
    model = DecisionTreeClassifier(max_depth=2, random_state=42)
    model.fit(X_p, sample_ml_data["arrest"].astype(int).values)
    
    # Instantiate risk layer
    risk_layer = RiskIntelligenceLayer(preprocessor, model)
    
    # Assess risk
    df_assessed = risk_layer.assess_risk(sample_ml_data)
    
    # Columns check
    assert "arrest_probability" in df_assessed.columns
    assert "risk_score" in df_assessed.columns
    assert "risk_level" in df_assessed.columns
    
    # Values check
    assert df_assessed["arrest_probability"].min() >= 0.0
    assert df_assessed["arrest_probability"].max() <= 1.0
    assert df_assessed["risk_score"].min() >= 0.0
    assert df_assessed["risk_score"].max() <= 1.0
    
    # Verify levels assigned correctly
    levels = df_assessed["risk_level"].unique()
    for lvl in levels:
        assert lvl in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        
    # Check severity weights helper
    assert get_severity_weight("ASSAULT") == 1.5
    assert get_severity_weight("THEFT") == 0.7
    assert get_severity_weight("UNKNOWN_CRIME") == 0.7
    
    # Test report generation
    report = risk_layer.generate_risk_report(df_assessed)
    assert report["total_assessed"] == 50
    assert "overall_averages" in report
    assert "risk_level_counts" in report
    assert "category_breakdown" in report
