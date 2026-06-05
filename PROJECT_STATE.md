# HawkEye Project State

This document tracks the current state, progress, and architectural status of the HawkEye AI-powered crime intelligence platform.

---

## Overall Project Completion: 65%

| Phase | Component | Status | Weight | Key Features |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 1** | Data Ingestion | **Completed** | 15% | Schema checking, date/coordinate parsing, duplicate removal, anomaly logging. |
| **Phase 2** | Crime Analytics | **Completed** | 15% | Spatial-temporal aggregation, category profiling, statistical summaries. |
| **Phase 3** | Geospatial Intelligence | **Completed** | 15% | DBSCAN clustering, grid hotspots, interactive Folium overlays (heatmap, cluster, hotspots). |
| **Phase 4** | Machine Learning | **Completed** | 20% | Scikit-learn preprocessing pipelines, multi-model evaluation (RF, GB, DT, LR), joblib persistence, Risk Intelligence Layer. |
| **Phase 5** | Prediction Engine | *Not Started* | 15% | Hourly/weekly forecasting, spatial-temporal risk maps. |
| **Phase 6** | Interactive Dashboard | *Not Started* | 15% | Streamlit interface, live filters, predictive overlays, Folium integrations. |
| **Phase 7** | Final Polish & Quality | *Not Started* | 5% | setup instructions, final verification tests, docs. |

---

## Phase 4 Self-Audit

### 1. Implemented Components
* **Feature Engineering** (`src/ml/feature_engineering.py`):
  * Extracts temporal (`hour`, `day_of_week`, `month`, `year`) and cyclical features (`hour_sin`, `hour_cos`, `day_sin`, `day_cos`, `month_sin`, `month_cos`) to capture periodic behavior.
  * Captures spatial context by computing the Haversine distance to each DBSCAN cluster centroid and top hotspot centroid.
  * Imputes missing coordinates using median coordinates and fills other columns with standard categories.
* **Preprocessing Pipeline** (`src/ml/preprocessing.py`):
  * Leverages a reusable custom estimator wrapping `ColumnTransformer`, `StandardScaler`, and `OneHotEncoder`.
  * Preserves class distributions using stratified training/test split.
* **Model Training & Comparison** (`src/ml/models.py`):
  * Compares **Random Forest**, **Gradient Boosting**, **Decision Tree**, and **Logistic Regression**.
  * Outputs F1-Score, Accuracy, Precision, Recall, and Confusion Matrices.
  * Automatically identifies and serializes the best model.
* **Model Persistence**:
  * Saves preprocessor pipeline to `models/preprocessing_pipeline.pkl`.
  * Saves best trained model to `models/best_model.pkl`.
* **Risk Intelligence Layer** (`src/ml/risk_intelligence.py`):
  * Computes unnormalized risk scores using category severity weights:
    * Violent/Personal (ASSAULT, BATTERY, ROBBERY, WEAPONS VIOLATION) = 1.5
    * Property/Narcotics (BURGLARY, MOTOR VEHICLE THEFT, NARCOTICS) = 1.0
    * Minor/Other (THEFT, CRIMINAL DAMAGE, DECEPTIVE PRACTICE, OTHER OFFENSE) = 0.7
  * Combines severity weight with predicted arrest probability:
    $$\text{Risk Score} = \text{Severity Weight} \times (1.0 - P(\text{arrest}))$$
  * Normalizes and classifies into **LOW (<0.25)**, **MEDIUM (0.25–0.50)**, **HIGH (0.50–0.75)**, and **CRITICAL (>=0.75)**.

### 2. Verification & Test Run Outcomes
* **Unit Tests**: Created `tests/test_ml.py` which covers all ML components. Executed `python -m pytest` resulting in **22/22 tests passing** (including existing ingestion, analytics, and geospatial suites).
* **Pipeline Output**: Run successfully on a synthetic 6,000-record dataset:
  * **Best Model**: `Logistic Regression` with an F1 Score of **0.6834** (Accuracy: **82.84%**).
  * **Risk Profile Summary**: Out of 5,881 incidents, the Risk Intelligence Layer successfully categorized:
    * **MEDIUM**: 1,860 incidents (31.63%)
    * **CRITICAL**: 1,469 incidents (24.98%)
    * **HIGH**: 1,467 incidents (24.94%)
    * **LOW**: 1,085 incidents (18.45%)

---

## Recommended Next Phase

### Phase 5: Prediction Engine
The logical next step is **Phase 5 (Prediction Engine)**. 
We will leverage the saved models and preprocessors to perform:
1. **Crime Forecasting**: Predicting the expected volume of crime in the upcoming hours/days using temporal models.
2. **Spatial Risk Assessment**: Creating a spatial forecasting mesh that outputs risk profiles for different coordinates based on the time of day.
3. **Integration Ready**: Generating forecasts that will feed directly into the Streamlit UI (Phase 6).
