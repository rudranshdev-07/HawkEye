# HawkEye Phase 2-3 Technical Strategy

**Current Status**: Tier 1 Critical Fixes Complete (65% → 75% overall)  
**Next Target**: Phase 5 (Prediction Engine) + Phase 6 (Dashboard)  
**Timeline**: 2-3 weeks for full completion

---

## Phase 5: Prediction Engine (15% of work)

### Objective
Enable time-based crime forecasting: "What will risk be in 2 hours?"

### Architecture

```
Current Flow:
  User Location → Intelligence Engine → Risk Score (present tense)

New Flow:
  User Location + Time → Forecast Engine → Risk Scores (hourly/weekly)
  
System:
  ┌─────────────────────────────────────────────────┐
  │  Temporal Feature Generator                    │
  │  - Hour of day (0-23)                          │
  │  - Day of week (0-6)                           │
  │  - Month/season                                │
  │  - Holiday/event flags                         │
  └─────────────────────────────────────────────────┘
              ↓
  ┌─────────────────────────────────────────────────┐
  │  Saved ML Models (from Phase 4)                │
  │  - Logistic Regression                         │
  │  - Preprocessing Pipeline                      │
  │  - Risk Intelligence Layer                     │
  └─────────────────────────────────────────────────┘
              ↓
  ┌─────────────────────────────────────────────────┐
  │  Risk Forecast Array                           │
  │  [hour 0: 45.2, hour 1: 47.3, ...]            │
  └─────────────────────────────────────────────────┘
```

### Implementation Plan

#### Step 1: Create Forecast Engine
```python
# src/ml/forecast_engine.py
import joblib
from datetime import datetime, timedelta
import numpy as np

class CrimeForecastEngine:
    def __init__(self):
        self.model = joblib.load('models/best_model.pkl')
        self.preprocessor = joblib.load('models/preprocessing_pipeline.pkl')
    
    def forecast_risk(self, lat, lon, hours_ahead=24):
        """
        Generate hourly risk forecast
        
        Args:
            lat, lon: Query location
            hours_ahead: How many hours to forecast (default 24)
        
        Returns:
            List of risk scores for each hour
        """
        forecasts = []
        base_time = datetime.now()
        
        for hour_offset in range(hours_ahead):
            # Generate features for this time
            forecast_time = base_time + timedelta(hours=hour_offset)
            features = self._generate_temporal_features(lat, lon, forecast_time)
            
            # Predict using saved model
            prediction = self.model.predict([features])
            risk_score = self._convert_to_risk_score(prediction)
            
            forecasts.append({
                "hour": hour_offset,
                "time": forecast_time.isoformat(),
                "risk_score": risk_score,
                "confidence": 0.85  # Model confidence
            })
        
        return forecasts
    
    def _generate_temporal_features(self, lat, lon, forecast_time):
        """Generate features for future time"""
        features = []
        
        # Temporal features
        hour = forecast_time.hour
        day_of_week = forecast_time.weekday()
        month = forecast_time.month
        
        # Cyclical encoding (from Phase 4)
        hour_sin = np.sin(2 * np.pi * hour / 24)
        hour_cos = np.cos(2 * np.pi * hour / 24)
        day_sin = np.sin(2 * np.pi * day_of_week / 7)
        day_cos = np.cos(2 * np.pi * day_of_week / 7)
        month_sin = np.sin(2 * np.pi * month / 12)
        month_cos = np.cos(2 * np.pi * month / 12)
        
        # Spatial features
        features.append([
            lat, lon,
            hour, day_of_week, month,
            hour_sin, hour_cos, day_sin, day_cos, month_sin, month_cos,
            # ... other features from Phase 4
        ])
        
        return features
    
    def _convert_to_risk_score(self, prediction):
        """Convert model output to 0-100 risk score"""
        # prediction is arrest probability from model
        # convert to risk using severity weighting
        from src.risk.risk_engine import calculate_risk_score
        # ... implementation
```

#### Step 2: Add API Endpoints
```python
# In src/api.py

@app.get("/forecast")
async def forecast(
    latitude: float,
    longitude: float,
    hours: int = 24
) -> Dict[str, Any]:
    """
    Get crime risk forecast for location over next N hours
    
    Query Parameters:
        latitude: Location latitude
        longitude: Location longitude
        hours: Number of hours to forecast (1-168, default 24)
    
    Returns:
        Forecast data with hourly risk scores and confidence
    """
    try:
        forecast_engine = CrimeForecastEngine()
        forecasts = forecast_engine.forecast_risk(latitude, longitude, hours)
        
        return {
            "status": "success",
            "location": {"latitude": latitude, "longitude": longitude},
            "forecast_hours": hours,
            "forecasts": forecasts,
            "summary": {
                "peak_risk": max(f["risk_score"] for f in forecasts),
                "peak_hour": next(f["hour"] for f in forecasts 
                                  if f["risk_score"] == max(...)),
                "average_risk": np.mean([f["risk_score"] for f in forecasts])
            }
        }
    except Exception as e:
        logger.error(f"Forecast error: {e}")
        raise HTTPException(status_code=500, detail="Forecast failed")


@app.get("/weekly-forecast")
async def weekly_forecast(
    latitude: float,
    longitude: float
) -> Dict[str, Any]:
    """
    Get weekly (7 day) crime risk forecast
    Similar to hourly but for 168 hours
    """
    pass
```

#### Step 3: Frontend Visualization
```javascript
// frontend/app.js - Add chart visualization

function displayForecast(forecastData) {
    const canvas = document.createElement("canvas");
    
    // Chart.js library
    const ctx = canvas.getContext("2d");
    const chart = new Chart(ctx, {
        type: "line",
        data: {
            labels: forecastData.forecasts.map(f => f.time),
            datasets: [{
                label: "Risk Score Forecast",
                data: forecastData.forecasts.map(f => f.risk_score),
                borderColor: "#38bdf8",
                backgroundColor: "rgba(56, 189, 248, 0.1)",
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: { text: "24-Hour Crime Risk Forecast" }
            },
            scales: {
                y: { min: 0, max: 100 }
            }
        }
    });
    
    document.getElementById("forecastChart").appendChild(canvas);
}
```

#### Step 4: Testing
```python
# tests/test_forecast.py
import pytest
from src.ml.forecast_engine import CrimeForecastEngine

def test_forecast_returns_24_hours():
    engine = CrimeForecastEngine()
    forecast = engine.forecast_risk(28.61, 77.20, hours=24)
    assert len(forecast) == 24
    assert all(0 <= f["risk_score"] <= 100 for f in forecast)

def test_peak_risk_calculation():
    # Verify peak_hour matches peak_risk
    pass

def test_forecast_confidence():
    # Verify confidence scores
    pass
```

---

## Phase 6: Interactive Dashboard (15% of work)

### Objective
Build professional Streamlit dashboard for exploratory analysis

### Stack
- **Framework**: Streamlit (easy, interactive, no frontend complexity)
- **Maps**: Folium + Streamlit integration
- **Charts**: Plotly (responsive, beautiful)
- **Data**: Pandas (existing workflow)

### Architecture

```
Dashboard Structure:
┌─────────────────────────────────────────────────────┐
│  Sidebar Filters                                   │
│  ┌─────────────────────────────────────────────┐  │
│  │ City: [Delhi ▼]                             │  │
│  │ Crime Type: [Multi-select: Theft, Assault]  │  │
│  │ Date Range: [Calendar picker]               │  │
│  │ Risk Level: [Slider: 0 ─────● 100]          │  │
│  └─────────────────────────────────────────────┘  │
│                                                    │
├─────────────────────────────────────────────────────┤
│  Main Content Area                                │
│                                                    │
│  ┌──────────────────────┬──────────────────────┐  │
│  │  📊 Metrics          │  🗺️  Heatmap         │  │
│  │  ├─ Total Crimes     │  (Folium Map)       │  │
│  │  ├─ Avg Risk         │                      │  │
│  │  └─ Hotspots Found   │                      │  │
│  └──────────────────────┴──────────────────────┘  │
│                                                    │
│  ┌──────────────────────────────────────────────┐ │
│  │ 📈 Crime Trends (Line Chart)                 │ │
│  │ (Time series of incidents over days/weeks)  │ │
│  └──────────────────────────────────────────────┘ │
│                                                    │
│  ┌──────────────────────┬──────────────────────┐  │
│  │ 🚨 Top Hotspots      │ 🔍 Crime Categories  │  │
│  │ (Bar chart)          │ (Pie chart)          │  │
│  └──────────────────────┴──────────────────────┘  │
│                                                    │
│  ┌──────────────────────────────────────────────┐ │
│  │ 📍 Location Intelligence Inspector           │ │
│  │ [Latitude: ___] [Longitude: ___] [Analyze] │ │
│  │ (Shows detailed risk report)                 │ │
│  └──────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Implementation Plan

#### Step 1: Create Dashboard App
```python
# src/dashboard/app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium

from src.risk.intelligence_engine import get_location_intelligence
from src.preprocessing.ingestion import CrimeDataIngestor

# Page config
st.set_page_config(
    page_title="HawkEye Crime Intelligence Dashboard",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load data once (caching)
@st.cache_resource
def load_data():
    ingestor = CrimeDataIngestor()
    df, _ = ingestor.process_and_save(
        "data/raw/india_crime_data.csv",
        "data/processed/crime_data.csv"
    )
    return df

df = load_data()

# =====================================================
# SIDEBAR FILTERS
# =====================================================

st.sidebar.header("🔍 Filters")

selected_city = st.sidebar.selectbox(
    "City",
    df["city"].unique() if "city" in df.columns else ["All"]
)

selected_crimes = st.sidebar.multiselect(
    "Crime Types",
    df["category"].unique() if "category" in df.columns else [],
    default=None
)

date_range = st.sidebar.date_input(
    "Date Range",
    value=(df["date"].min(), df["date"].max()) if "date" in df.columns else None
)

risk_level_filter = st.sidebar.slider(
    "Minimum Risk Level",
    0, 100, 40
)

# Apply filters
df_filtered = df.copy()

if selected_city != "All":
    df_filtered = df_filtered[df_filtered["city"] == selected_city]

if selected_crimes:
    df_filtered = df_filtered[df_filtered["category"].isin(selected_crimes)]

# =====================================================
# MAIN DASHBOARD
# =====================================================

st.title("🛰️ HawkEye Crime Intelligence Dashboard")
st.markdown(f"Analyzing **{len(df_filtered):,}** crime incidents in {selected_city}")

# KPI Row
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Incidents", len(df_filtered))

with col2:
    avg_risk = 65  # Calculate from data
    st.metric("Avg Risk Score", f"{avg_risk:.1f}", delta="+2.3 from yesterday")

with col3:
    hotspot_count = 10  # Count hotspots
    st.metric("Hotspots Detected", hotspot_count)

with col4:
    violent_crime_pct = 35  # Calculate
    st.metric("Violent Crimes %", f"{violent_crime_pct}%", delta="-1.2%")

# Maps and Charts
st.markdown("---")
st.header("📊 Crime Visualization")

col1, col2 = st.columns(2)

# Heatmap
with col1:
    st.subheader("🗺️ Crime Heatmap")
    
    # Create Folium map
    m = folium.Map(
        location=[28.61, 77.20],
        zoom_start=11,
        tiles="CartoDB dark_matter"
    )
    
    # Add crime points
    for _, row in df_filtered.iterrows():
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=3,
            color="red",
            fill=True
        ).add_to(m)
    
    st_folium(m, width=700, height=500)

# Time Series
with col2:
    st.subheader("📈 Crime Trend")
    
    # Group by date
    trend_data = df_filtered.groupby(df_filtered["date"].dt.date).size()
    
    fig = px.line(
        x=trend_data.index,
        y=trend_data.values,
        labels={"x": "Date", "y": "Incidents"},
        markers=True
    )
    
    st.plotly_chart(fig, use_container_width=True)

# Bottom row: Hotspots and Categories
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.subheader("🚨 Top Crime Categories")
    
    top_crimes = df_filtered["category"].value_counts().head(8)
    
    fig = px.bar(
        x=top_crimes.values,
        y=top_crimes.index,
        orientation="h",
        labels={"x": "Incidents", "y": "Crime Type"}
    )
    
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("📍 Top Hotspots")
    
    # Group by district
    top_districts = df_filtered["district"].value_counts().head(8)
    
    fig = px.pie(
        values=top_districts.values,
        names=top_districts.index,
        title="Incidents by District"
    )
    
    st.plotly_chart(fig, use_container_width=True)

# Location Inspector
st.markdown("---")
st.header("🔎 Location Intelligence Inspector")

col1, col2, col3 = st.columns(3)

with col1:
    query_lat = st.number_input("Latitude", value=28.61, format="%.4f")

with col2:
    query_lon = st.number_input("Longitude", value=77.20, format="%.4f")

with col3:
    analyze_btn = st.button("🔍 Analyze Location")

if analyze_btn:
    with st.spinner("Analyzing location..."):
        intelligence = get_location_intelligence(query_lat, query_lon, df)
        
        # Display results in nice format
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Risk Score", intelligence["risk_score"])
            st.metric("Risk Level", intelligence["risk_level"])
            st.metric("Nearby Crimes (5km)", intelligence["crime_count"])
        
        with col2:
            st.metric("Crimes in 1km", intelligence["crimes_1km"])
            st.metric("Crimes in 3km", intelligence["crimes_3km"])
            st.metric("Dominant Crime", intelligence["dominant_crime"])
        
        # Reasons
        st.write("### Why is this location risky?")
        for reason in intelligence["reasons"]:
            st.write(f"- {reason}")
        
        # Hotspot info
        if intelligence["nearest_hotspot_distance_km"]:
            st.write("### Hotspot Proximity")
            st.write(f"**Distance**: {intelligence['nearest_hotspot_distance_km']} km")
            st.write(f"**Rank**: #{intelligence['nearest_hotspot_rank']}")
```

#### Step 2: Run Dashboard
```bash
streamlit run src/dashboard/app.py
# Opens at http://localhost:8501
```

#### Step 3: Deploy
```bash
# Deploy to Streamlit Cloud (free)
# 1. Push code to GitHub
# 2. Connect repo to https://share.streamlit.io
# 3. Dashboard auto-deploys
```

---

## Phase 7: Polish & Documentation (5% remaining)

### Deliverables

1. **Setup Guide** (`SETUP.md`)
   - System requirements
   - Installation steps
   - Configuration options
   - Troubleshooting

2. **API Documentation** (Auto-generated)
   ```bash
   # Available at http://localhost:8000/docs
   # Swagger UI auto-generated from Pydantic models
   ```

3. **User Guide** (`USER_GUIDE.md`)
   - How to use frontend
   - How to interpret results
   - Examples and screenshots

4. **Developer Guide** (`DEVELOPER_GUIDE.md`)
   - Architecture overview
   - How to extend modules
   - Contributing guidelines

5. **Deployment Guide** (`DEPLOY.md`)
   - Docker setup
   - Cloud deployment (AWS, GCP, Azure)
   - Performance optimization

6. **Open Source Ready**
   - LICENSE file
   - Contributing guidelines
   - Code of conduct
   - CI/CD pipeline (GitHub Actions)

---

## Implementation Timeline

```
Week 1: Phase 5 (Prediction Engine)
├─ Monday-Wednesday: Forecast engine development
├─ Thursday: API endpoints + testing
└─ Friday: Frontend visualization

Week 2: Phase 6 (Dashboard)
├─ Monday-Wednesday: Streamlit dashboard
├─ Thursday: Deployment setup
└─ Friday: Testing + refinement

Week 3: Phase 7 (Documentation + Polish)
├─ Monday-Tuesday: Documentation
├─ Wednesday: Demo + testing
├─ Thursday: Final touches
└─ Friday: Release preparation
```

---

## Success Metrics

### Functionality
- ✅ All endpoints working
- ✅ Forecast accuracy validated
- ✅ Dashboard loads in <2 seconds
- ✅ No bugs in critical paths

### Performance
- ✅ API response <2s for queries
- ✅ Dashboard <3s to load
- ✅ Forecast <5s for 168 hours
- ✅ Memory usage <1GB

### Quality
- ✅ Full test coverage (>80%)
- ✅ Zero critical bugs
- ✅ Complete documentation
- ✅ Code passes linting

### Impact
- ✅ Hackathon-ready feature set
- ✅ Impressive to recruiters
- ✅ Production-deployable
- ✅ Nationally scalable

---

## Resources

### Libraries to Use
- `pandas`: Data manipulation
- `scikit-learn`: ML (already saved models)
- `plotly`: Interactive charts
- `folium`: Maps
- `streamlit`: Dashboard
- `joblib`: Model loading

### Deployment Platforms
- **API**: Heroku, AWS EC2, Google Cloud
- **Dashboard**: Streamlit Cloud (free!)
- **Frontend**: GitHub Pages, Vercel, Netlify

### Learning Resources
- Streamlit docs: https://docs.streamlit.io/
- Plotly Express: https://plotly.com/python/plotly-express/
- FastAPI: https://fastapi.tiangolo.com/

---

## Final Checklist

- [ ] Phase 5 fully implemented and tested
- [ ] Phase 6 dashboard deployed
- [ ] All endpoints documented
- [ ] README updated
- [ ] SETUP.md written
- [ ] Test suite passing (>80% coverage)
- [ ] No TODOs in critical code
- [ ] Performance validated
- [ ] Ready for production deployment

---

**Status**: Ready to proceed with Phase 5  
**Estimated Completion**: 3 weeks  
**Hackathon Readiness**: 90%+ after Phase 6
