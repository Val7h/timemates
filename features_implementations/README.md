# Distance Calculation Feature

Geographic distance calculation for TimeMates using the Haversine formula.

## Quick Start

### 1. Backend Integration (main.py)

Add these 2 lines around line 49:

```python
from features_implementations.distance_routes import router as distance_router
app.include_router(distance_router)
```

### 2. Copy Frontend

```bash
cp distance_calculator.html ../static/
```

### 3. Test It

```bash
curl "http://localhost:8000/api/distance/calculate?lat1=-23.5505&lon1=-46.6333&lat2=-22.9068&lon2=-43.1729"
```

## Files

- **distance_calculation.py** - Core distance logic
- **distance_models.py** - Optional database models
- **distance_routes.py** - FastAPI endpoints
- **distance_calculator.html** - Interactive UI
- **DISTANCE_INTEGRATION_GUIDE.md** - Full documentation
- **INTEGRATION_CHECKLIST.md** - Step-by-step integration
- **DISTANCE_FEATURE_SUMMARY.md** - Feature overview

## API Endpoints

```
GET  /api/distance/calculate              # By coordinates
GET  /api/distance/between-cities         # Between 2 cities
GET  /api/distance/nearby-cities          # Find nearby
GET  /api/distance/cities-in-range        # Distance range
GET  /api/distance/stats/{city_id}        # Statistics
GET  /api/distance/user/preferences       # User prefs (auth)
POST /api/distance/user/preferences       # Update prefs (auth)
```

## Example Usage

### JavaScript
```javascript
const response = await fetch('/api/distance/calculate?lat1=-23&lon1=-46&lat2=-22&lon2=-43&unit=km');
const data = await response.json();
console.log(data.distance, data.unit);
```

### Python
```python
from features_implementations.distance_calculation import DistanceCalculator
d = DistanceCalculator.haversine(-23.5505, -46.6333, -22.9068, -43.1729, "km")
print(f"{d} km")
```

## Documentation

See DISTANCE_INTEGRATION_GUIDE.md for complete documentation.
See INTEGRATION_CHECKLIST.md for step-by-step integration.

## Key Features

✓ Haversine formula (accurate to 0.5%)
✓ Supports km and miles
✓ Coordinate validation
✓ City-based queries
✓ Range searches
✓ User preferences
✓ Analytics logging
✓ Responsive UI
✓ No external dependencies
✓ Production ready
