# HawkEye Quick Start Guide

## Installation & Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Prepare Data
Ensure you have the Indian crime dataset:
```bash
data/raw/india_crime_data.csv  # Should exist from your setup
```

### 3. Start the API Server
```bash
uvicorn src.api:app --host 127.0.0.1 --port 8000 --reload
```

You should see:
```
INFO:     Application startup complete
Loaded India dataset: 250000 records
```

### 4. Open Frontend
Open in your browser:
```
file:///path/to/HawkEye/frontend/index.html
```

Or use a local HTTP server:
```bash
cd frontend
python -m http.server 8080
# Then visit http://localhost:8080
```

## Usage

### Click on Map
1. Click anywhere on the India map
2. Wait for analysis (10-second timeout)
3. See risk report, crime stats, and hotspot info

### Interpret Results

**Risk Score (0-100)**:
- 🟢 0-20: Very Safe
- 🟡 20-40: Safe  
- ⚡ 40-60: Moderate
- 🟠 60-80: High Risk
- 🔴 80-100: Very High Risk

**Crime Counts**:
- **1km**: Most relevant for immediate area
- **3km**: Local neighborhood context
- **5km**: Broader region analysis

**Reasons**: Machine-generated explanations of risk factors

### Debug Mode
Open the "📊 Debug Info" panel at bottom of intelligence panel to see:
- Server health status
- API request/response timing
- Error messages
- Detailed logs

## Troubleshooting

### "Server unavailable" message
**Problem**: API server not running
**Solution**: Start server with `uvicorn` command

### "Request timeout" after 10 seconds
**Problem**: API is slow (large dataset processing)
**Solution**: 
- Ensure sufficient RAM (4GB+)
- Check CPU usage
- Dataset may need indexing for speed

### "No major crime indicators" everywhere
**Problem**: Query location outside dataset coverage
**Solution**: Try clicking on major Indian cities (Delhi, Bangalore, Mumbai)

### Frontend page blank
**Problem**: CORS issue or file path wrong
**Solution**:
- Use `python -m http.server` to serve frontend
- Check browser console for errors (F12)
- Ensure API is running on port 8000

## API Endpoints

### Health Check
```bash
curl http://127.0.0.1:8000/health
```

**Response**:
```json
{
  "status": "ok",
  "dataset_size": 250000
}
```

### Risk Analysis
```bash
curl -X POST http://127.0.0.1:8000/risk \
  -H "Content-Type: application/json" \
  -d '{"features": {"latitude": 28.61, "longitude": 77.20}}'
```

**Response**:
```json
{
  "risk_score": 72.5,
  "risk_level": "High Risk",
  "crime_count": 142,
  "crimes_1km": 18,
  "crimes_3km": 45,
  "crimes_5km": 142,
  "dominant_crime": "THEFT",
  "top_crimes": {
    "THEFT": 35,
    "ASSAULT": 22,
    "BATTERY": 18
  },
  "nearest_hotspot_distance_km": 0.8,
  "nearest_hotspot_rank": 3,
  "reasons": [
    "⚠️ HIGH: 18 incidents within 1km indicates elevated risk...",
    "Located 0.8km from Rank #3 hotspot..."
  ]
}
```

### Heatmap Data
```bash
curl http://127.0.0.1:8000/heatmap-data
```

## Performance Tips

1. **First Load**: Initial dataset load takes 2-3 seconds
2. **Queries**: Analysis takes 1-2 seconds per location
3. **Memory**: Requires ~500MB RAM for 250K records
4. **Network**: Works locally without internet

## Code Structure

```
src/
├── api.py                    # FastAPI endpoints
├── models.py                 # Pydantic data models (NEW)
├── risk/
│   ├── intelligence_engine.py    # Main analysis
│   ├── risk_engine.py           # 4-factor risk scoring (IMPROVED)
│   ├── density_engine.py        # Crime radius analysis
│   └── hotspot_engine.py        # Hotspot distance calc
├── geospatial/
│   ├── hotspot_detector.py  # Grid-based hotspot detection
│   ├── heatmap.py          # Interactive maps
│   └── geo_utils.py        # Coordinate validation
└── utils/
    └── logging_config.py    # Logging setup

frontend/
├── index.html               # Professional layout (REDESIGNED)
├── app.js                   # Error recovery + logging (REWRITTEN)
└── style.css               # Modern design system (REWRITTEN)
```

## Next: Prediction Engine (Phase 5)

To implement time-based forecasting:

```python
# src/ml/forecast_engine.py
def forecast_crime_risk(lat, lon, hours_ahead=24):
    """Predict risk for next N hours"""
    # Uses saved ML models from Phase 4
    # Returns hourly risk curve
    pass

# Add to src/api.py
@app.get("/forecast/{hours}")
async def forecast(hours: int) -> ForecastResponse:
    # Get risk forecast
    pass
```

## Support

For issues or questions:
1. Check browser console (F12)
2. Check server logs in terminal
3. Check "📊 Debug Info" panel in frontend
4. Review `/logs/hawkeye.log` for errors

---

**Last Updated**: June 10, 2024  
**Architecture Version**: 2.0  
**Status**: Production-Ready for Tier 1 Fixes ✓
