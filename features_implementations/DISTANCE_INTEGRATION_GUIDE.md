# Distance Calculation Feature - Integration Guide

## Overview

The Distance Calculation feature enables TimeMates to calculate geographic distances between cities using the Haversine formula. This feature includes:

- **Backend API**: FastAPI endpoints for distance calculations
- **Database Models**: Optional caching and preference storage
- **Frontend UI**: Interactive distance calculator
- **User Preferences**: Store user location settings

## Files Included

1. **distance_calculation.py** - Core Haversine formula implementation
2. **distance_models.py** - SQLAlchemy database models for caching and preferences
3. **distance_routes.py** - FastAPI route definitions
4. **distance_calculator.html** - Interactive web interface
5. **DISTANCE_INTEGRATION_GUIDE.md** - This file

## Quick Start Integration

### Step 1: Backend Integration

#### 1.1 Add imports to `main.py`

```python
from features_implementations.distance_routes import router as distance_router

# ... existing code ...

# Add this with other router inclusions (around line 49)
app.include_router(distance_router)
```

#### 1.2 Update database models (Optional but recommended)

Add to `database.py` imports at the top:

```python
# Existing imports...

# Add these for distance feature
from features_implementations.distance_models import (
    DistanceCache,
    DistanceQuery,
    UserLocationPreference,
    DistanceBasedRecommendation
)
```

Then add to `Base.metadata.create_all()` section:

```python
# Create all tables
try:
    Base.metadata.create_all(bind=engine)
except Exception as _e:
    print(f"[DB] create_all erro: {_e}")
```

No additional code needed - SQLAlchemy will create the new tables automatically.

### Step 2: Frontend Integration

#### 2.1 Add link to navigation menu in `static/index.html`

Find the navigation section and add:

```html
<a href="/features_implementations/distance_calculator.html" class="nav-link">
    <span class="icon">📍</span>
    <span>Calculadora de Distância</span>
</a>
```

#### 2.2 Create separate page (recommended)

Copy `distance_calculator.html` to `static/distance_calculator.html`:

```bash
cp features_implementations/distance_calculator.html static/distance_calculator.html
```

Then reference it as `/static/distance_calculator.html` in your app.

### Step 3: Update City Model (Already Done)

The City model in `database.py` already has a `coordinates` field:

```python
coordinates = Column(JSON)  # {"latitude": float, "longitude": float}
```

Ensure your cities are populated with coordinates. Example format:

```python
{
    "latitude": -23.5505,
    "longitude": -46.6333
}
```

## API Endpoints Reference

### 1. Calculate Distance by Coordinates

**Endpoint**: `GET /api/distance/calculate`

**Query Parameters**:
- `lat1` (float): First point latitude (-90 to 90)
- `lon1` (float): First point longitude (-180 to 180)
- `lat2` (float): Second point latitude (-90 to 90)
- `lon2` (float): Second point longitude (-180 to 180)
- `unit` (string): "km" (default) or "miles"/"mi"

**Example**:
```bash
curl "http://localhost:8000/api/distance/calculate?lat1=-23.5505&lon1=-46.6333&lat2=-22.9068&lon2=-43.1729&unit=km"
```

**Response**:
```json
{
    "distance": 357.34,
    "unit": "km",
    "error": null
}
```

### 2. Distance Between Cities

**Endpoint**: `GET /api/distance/between-cities`

**Query Parameters**:
- `city1_id` (int): First city ID
- `city2_id` (int): Second city ID
- `unit` (string): "km" (default) or "miles"/"mi"

**Example**:
```bash
curl "http://localhost:8000/api/distance/between-cities?city1_id=1&city2_id=2&unit=km"
```

**Response**:
```json
{
    "city1": "São Paulo",
    "city1_id": 1,
    "city2": "Rio de Janeiro",
    "city2_id": 2,
    "distance": 357.34,
    "unit": "km",
    "error": null
}
```

### 3. Find Nearby Cities

**Endpoint**: `GET /api/distance/nearby-cities`

**Query Parameters**:
- `city_id` (int): Reference city ID
- `max_distance` (float): Maximum distance radius (default: 100)
- `unit` (string): "km" (default) or "miles"/"mi"
- `limit` (int): Maximum results (default: 50, max: 500)

**Example**:
```bash
curl "http://localhost:8000/api/distance/nearby-cities?city_id=1&max_distance=200&unit=km&limit=20"
```

**Response**:
```json
{
    "city_id": 1,
    "max_distance": 200,
    "unit": "km",
    "nearby_cities": [
        {
            "id": 2,
            "name": "Rio de Janeiro",
            "state": "RJ",
            "distance": 357.34,
            "unit": "km",
            "population": 6747815,
            "coordinates": {"latitude": -22.9068, "longitude": -43.1729}
        }
    ],
    "total_found": 5,
    "returned": 5
}
```

### 4. Find Cities in Distance Range

**Endpoint**: `GET /api/distance/cities-in-range`

**Query Parameters**:
- `latitude` (float): Reference point latitude
- `longitude` (float): Reference point longitude
- `min_distance` (float): Minimum distance (default: 0)
- `max_distance` (float): Maximum distance (default: 100)
- `unit` (string): "km" (default) or "miles"/"mi"
- `limit` (int): Maximum results (default: 50, max: 500)

**Example**:
```bash
curl "http://localhost:8000/api/distance/cities-in-range?latitude=-23&longitude=-46&min_distance=50&max_distance=200&unit=km"
```

### 5. Distance Statistics

**Endpoint**: `GET /api/distance/stats/{city_id}`

**Path Parameters**:
- `city_id` (int): City ID

**Query Parameters**:
- `unit` (string): "km" (default) or "miles"/"mi"

**Example**:
```bash
curl "http://localhost:8000/api/distance/stats/1?unit=km"
```

**Response**:
```json
{
    "city": "São Paulo",
    "city_id": 1,
    "min_distance": 50.25,
    "max_distance": 5000.0,
    "average_distance": 1234.56,
    "total_cities": 147,
    "unit": "km",
    "error": null
}
```

### 6. Get User Location Preferences (Authenticated)

**Endpoint**: `GET /api/distance/user/preferences`

**Headers**:
- `Authorization: Bearer {token}`

**Response**:
```json
{
    "user_id": 1,
    "home_city_id": 1,
    "preferred_distance_unit": "km",
    "max_search_distance": 100,
    "share_location": true,
    "show_distance_to_events": true
}
```

### 7. Update User Location Preferences (Authenticated)

**Endpoint**: `POST /api/distance/user/preferences`

**Headers**:
- `Authorization: Bearer {token}`

**Query Parameters** (all optional):
- `home_city_id` (int): User's home city ID
- `preferred_distance_unit` (string): "km" or "miles"/"mi"
- `max_search_distance` (float): Maximum search distance
- `share_location` (bool): Whether to share location
- `show_distance_to_events` (bool): Whether to show distances to events

**Example**:
```bash
curl -X POST "http://localhost:8000/api/distance/user/preferences?home_city_id=1&preferred_distance_unit=km&max_search_distance=200" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Database Schema

### DistanceCache Table

```sql
CREATE TABLE distance_cache (
    id INTEGER PRIMARY KEY,
    city1_id INTEGER NOT NULL,
    city2_id INTEGER NOT NULL,
    distance_km FLOAT NOT NULL,
    distance_miles FLOAT NOT NULL,
    calculated_at DATETIME,
    last_used_at DATETIME,
    use_count INTEGER,
    UNIQUE(city1_id, city2_id)
);
```

### DistanceQuery Table

```sql
CREATE TABLE distance_queries (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    origin_city_id INTEGER,
    destination_city_id INTEGER,
    origin_latitude FLOAT,
    origin_longitude FLOAT,
    destination_latitude FLOAT,
    destination_longitude FLOAT,
    distance_km FLOAT NOT NULL,
    query_type VARCHAR(50) NOT NULL,
    unit VARCHAR(10),
    created_at DATETIME,
    ip_address VARCHAR(50),
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(origin_city_id) REFERENCES cities(id),
    FOREIGN KEY(destination_city_id) REFERENCES cities(id)
);
```

### UserLocationPreference Table

```sql
CREATE TABLE user_location_preferences (
    id INTEGER PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL,
    home_city_id INTEGER,
    preferred_distance_unit VARCHAR(10),
    max_search_distance FLOAT,
    share_location BOOLEAN,
    show_distance_to_events BOOLEAN,
    updated_at DATETIME,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(home_city_id) REFERENCES cities(id)
);
```

## Python Usage Examples

### Direct Calculation

```python
from features_implementations.distance_calculation import DistanceCalculator

# Calculate distance between two coordinates
result = DistanceCalculator.calculate_distance(
    lat1=-23.5505,
    lon1=-46.6333,
    lat2=-22.9068,
    lon2=-43.1729,
    unit="km"
)

print(f"Distance: {result['distance']} {result['unit']}")
# Output: Distance: 357.34 km
```

### Using City Database

```python
from features_implementations.distance_calculation import CityDistanceCalculator
from database import SessionLocal

db = SessionLocal()

# Distance between two cities
result = CityDistanceCalculator.distance_between_cities(db, city1_id=1, city2_id=2)
print(f"{result['city1']} to {result['city2']}: {result['distance']} {result['unit']}")

# Find nearby cities
nearby = CityDistanceCalculator.find_nearby_cities(
    db,
    city_id=1,
    max_distance=200,
    unit="km"
)

for city in nearby:
    print(f"{city['name']}: {city['distance']} km away")

# Distance statistics
stats = CityDistanceCalculator.get_distance_stats(db, city_id=1)
print(f"Average distance from {stats['city']}: {stats['average_distance']} km")
```

## Configuration

### Environment Variables (Optional)

No specific environment variables required. The feature uses existing database connection.

### Requirements

The feature uses only Python standard library (`math`) and existing dependencies:
- FastAPI
- SQLAlchemy
- SQLite/PostgreSQL (already in use)

No additional packages need to be installed.

## Performance Considerations

### Distance Caching

For repeated calculations between the same cities, use the `DistanceCache` table:

```python
from features_implementations.distance_calculation import CityDistanceCalculator
from database import SessionLocal

db = SessionLocal()

# First call calculates and caches
result1 = CityDistanceCalculator.distance_between_cities(db, city1_id=1, city2_id=2)

# Subsequent calls could check cache first
# (you can implement caching middleware)
```

### Database Indexing

The models include optimized indexes:
- `distance_cache.city1_id, city2_id` - for fast lookups
- `distance_queries.user_id, created_at` - for analytics
- `user_location_preferences.user_id` - unique constraint

## Testing

### Manual Testing via curl

```bash
# Test coordinates calculation
curl "http://localhost:8000/api/distance/calculate?lat1=-23.5505&lon1=-46.6333&lat2=-22.9068&lon2=-43.1729&unit=km"

# Test cities calculation
curl "http://localhost:8000/api/distance/between-cities?city1_id=1&city2_id=2"

# Test nearby cities
curl "http://localhost:8000/api/distance/nearby-cities?city_id=1&max_distance=200"

# Test statistics
curl "http://localhost:8000/api/distance/stats/1"
```

### Python Unit Tests

Create `test_distance.py`:

```python
from features_implementations.distance_calculation import DistanceCalculator

def test_haversine():
    # São Paulo to Rio de Janeiro (approximately 357 km)
    distance = DistanceCalculator.haversine(
        lat1=-23.5505, lon1=-46.6333,
        lat2=-22.9068, lon2=-43.1729,
        unit="km"
    )
    assert 350 < distance < 365

def test_invalid_coordinates():
    result = DistanceCalculator.calculate_distance(
        lat1=91, lon1=0,  # Invalid latitude
        lat2=0, lon2=0,
        unit="km"
    )
    assert result["error"] is not None

if __name__ == "__main__":
    test_haversine()
    test_invalid_coordinates()
    print("All tests passed!")
```

## Features Roadmap

### Current Version (v1.0)
- Basic distance calculations
- Coordinate and city-based queries
- Nearby cities search
- Distance statistics

### Planned Enhancements
- Distance caching for performance
- User location preferences storage
- Location-based event recommendations
- Distance-based room suggestions
- Real-time distance tracking for events
- Route optimization between multiple cities
- Export distance data as CSV/JSON

## Troubleshooting

### Issue: Cities have no coordinates

**Solution**: Update city records with coordinates:

```python
from database import SessionLocal, City
import json

db = SessionLocal()
city = db.query(City).filter(City.name == "São Paulo").first()
city.coordinates = json.dumps({"latitude": -23.5505, "longitude": -46.6333})
db.commit()
```

### Issue: API returns 404 for city

**Solution**: Verify city exists in database:

```python
from database import SessionLocal, City

db = SessionLocal()
cities = db.query(City).all()
print(f"Total cities: {len(cities)}")
for city in cities[:5]:
    print(f"ID: {city.id}, Name: {city.name}")
```

### Issue: Inaccurate distances

The Haversine formula assumes:
- Earth is a perfect sphere (radius ≈ 6,371 km)
- No terrain elevation
- As-the-crow-flies distance, not road distance

For road distances, consider integrating with:
- Google Maps Distance Matrix API
- OSRM (Open Source Routing Machine)
- Mapbox Directions API

## Security Considerations

1. **Input Validation**: All coordinate inputs are validated for range
2. **Rate Limiting**: Consider adding rate limits to distance endpoints
3. **User Privacy**: Location preferences are optional and user-controlled
4. **Database**: Use connection pooling for production

## Support & Documentation

For questions or issues:
1. Check this integration guide
2. Review inline code comments in `distance_calculation.py`
3. Test endpoints manually with curl
4. Check FastAPI Swagger documentation at `/docs`
