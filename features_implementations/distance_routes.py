"""
FastAPI routes for distance calculation feature
Endpoints for calculating distances, finding nearby cities, and location-based queries
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db, User
from auth import get_current_user
from .distance_calculation import DistanceCalculator, CityDistanceCalculator

router = APIRouter(prefix="/api/distance", tags=["distance"])


# ============================================================================
# Direct Distance Calculations
# ============================================================================

@router.post("/calculate")
def calculate_distance(
    lat1: float = Query(..., description="First point latitude (-90 to 90)"),
    lon1: float = Query(..., description="First point longitude (-180 to 180)"),
    lat2: float = Query(..., description="Second point latitude (-90 to 90)"),
    lon2: float = Query(..., description="Second point longitude (-180 to 180)"),
    unit: str = Query("km", regex="^(km|miles|mi)$", description="Distance unit"),
    db: Session = Depends(get_db)
):
    """
    Calculate distance between two geographic coordinates using Haversine formula.

    Query Parameters:
    - lat1, lon1: First point coordinates
    - lat2, lon2: Second point coordinates
    - unit: "km" (default) or "miles"/"mi"

    Example:
    GET /api/distance/calculate?lat1=-23.5505&lon1=-46.6333&lat2=-22.9068&lon2=-43.1729&unit=km
    (São Paulo to Rio de Janeiro)
    """
    result = DistanceCalculator.calculate_distance(lat1, lon1, lat2, lon2, unit)

    if result["error"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/between-cities")
def distance_between_cities(
    city1_id: int = Query(..., description="First city ID"),
    city2_id: int = Query(..., description="Second city ID"),
    unit: str = Query("km", regex="^(km|miles|mi)$", description="Distance unit"),
    db: Session = Depends(get_db)
):
    """
    Calculate distance between two cities in database.

    Query Parameters:
    - city1_id: First city ID
    - city2_id: Second city ID
    - unit: "km" (default) or "miles"/"mi"

    Returns:
    - city1, city2: City names and IDs
    - distance: Distance value
    - unit: Distance unit used
    """
    if city1_id == city2_id:
        return {
            "city1": None,
            "city1_id": city1_id,
            "city2": None,
            "city2_id": city2_id,
            "distance": 0.0,
            "unit": unit,
            "error": "Cities are the same"
        }

    result = CityDistanceCalculator.distance_between_cities(db, city1_id, city2_id, unit)

    if result["error"]:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


# ============================================================================
# Nearby Cities and Range Queries
# ============================================================================

@router.get("/nearby-cities")
def find_nearby_cities(
    city_id: int = Query(..., description="Reference city ID"),
    max_distance: float = Query(100, description="Maximum distance (in unit)"),
    unit: str = Query("km", regex="^(km|miles|mi)$", description="Distance unit"),
    limit: int = Query(50, ge=1, le=500, description="Limit results"),
    db: Session = Depends(get_db)
):
    """
    Find all cities within specified distance from a reference city.

    Query Parameters:
    - city_id: Reference city ID
    - max_distance: Maximum distance (default 100)
    - unit: "km" (default) or "miles"/"mi"
    - limit: Maximum number of results (default 50, max 500)

    Returns:
    List of nearby cities sorted by distance:
    - id, name, state: City info
    - distance: Distance from reference city
    - population: City population
    - coordinates: Geographic coordinates
    """
    cities = CityDistanceCalculator.find_nearby_cities(db, city_id, max_distance, unit)

    if not cities:
        return {
            "city_id": city_id,
            "max_distance": max_distance,
            "unit": unit,
            "nearby_cities": [],
            "total_found": 0
        }

    # Apply limit and return
    limited_cities = cities[:limit]

    return {
        "city_id": city_id,
        "max_distance": max_distance,
        "unit": unit,
        "nearby_cities": limited_cities,
        "total_found": len(cities),
        "returned": len(limited_cities)
    }


@router.get("/cities-in-range")
def cities_in_distance_range(
    latitude: float = Query(..., description="Reference point latitude"),
    longitude: float = Query(..., description="Reference point longitude"),
    min_distance: float = Query(0, ge=0, description="Minimum distance"),
    max_distance: float = Query(100, description="Maximum distance"),
    unit: str = Query("km", regex="^(km|miles|mi)$", description="Distance unit"),
    limit: int = Query(50, ge=1, le=500, description="Limit results"),
    db: Session = Depends(get_db)
):
    """
    Find all cities within a distance range from arbitrary coordinates.

    Query Parameters:
    - latitude, longitude: Reference point
    - min_distance: Minimum distance (default 0)
    - max_distance: Maximum distance (default 100)
    - unit: "km" (default) or "miles"/"mi"
    - limit: Maximum number of results

    Returns:
    List of cities in range sorted by distance
    """
    if not DistanceCalculator.is_valid_coordinate(latitude, longitude):
        raise HTTPException(status_code=400, detail="Invalid coordinates")

    if min_distance > max_distance:
        raise HTTPException(
            status_code=400,
            detail="min_distance must be less than or equal to max_distance"
        )

    cities = CityDistanceCalculator.find_cities_by_distance_range(
        db, latitude, longitude, min_distance, max_distance, unit
    )

    limited_cities = cities[:limit]

    return {
        "reference_point": {
            "latitude": latitude,
            "longitude": longitude
        },
        "distance_range": {
            "min": min_distance,
            "max": max_distance,
            "unit": unit
        },
        "cities": limited_cities,
        "total_found": len(cities),
        "returned": len(limited_cities)
    }


# ============================================================================
# Distance Statistics
# ============================================================================

@router.get("/stats/{city_id}")
def distance_statistics(
    city_id: int,
    unit: str = Query("km", regex="^(km|miles|mi)$", description="Distance unit"),
    db: Session = Depends(get_db)
):
    """
    Get distance statistics for a city to all other cities.

    Path Parameters:
    - city_id: Reference city ID

    Query Parameters:
    - unit: "km" (default) or "miles"/"mi"

    Returns:
    - min_distance: Closest city distance
    - max_distance: Farthest city distance
    - average_distance: Average distance to all cities
    - total_cities: Number of cities in comparison
    """
    stats = CityDistanceCalculator.get_distance_stats(db, city_id, unit)

    if stats.get("error"):
        raise HTTPException(status_code=404, detail=stats["error"])

    return stats


# ============================================================================
# User Location Preferences (Authenticated)
# ============================================================================

@router.get("/user/preferences")
def get_user_location_preferences(
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Get current user's location preferences.
    Requires authentication.
    """
    from features_implementations.distance_models import UserLocationPreference

    prefs = db.query(UserLocationPreference).filter(
        UserLocationPreference.user_id == current_user.id
    ).first()

    if not prefs:
        # Return default preferences
        return {
            "user_id": current_user.id,
            "home_city_id": None,
            "preferred_distance_unit": "km",
            "max_search_distance": None,
            "share_location": True,
            "show_distance_to_events": True
        }

    return {
        "user_id": prefs.user_id,
        "home_city_id": prefs.home_city_id,
        "preferred_distance_unit": prefs.preferred_distance_unit,
        "max_search_distance": prefs.max_search_distance,
        "share_location": prefs.share_location,
        "show_distance_to_events": prefs.show_distance_to_events
    }


@router.post("/user/preferences")
def update_user_location_preferences(
    home_city_id: Optional[int] = Query(None),
    preferred_distance_unit: Optional[str] = Query(None, regex="^(km|miles|mi)$"),
    max_search_distance: Optional[float] = Query(None, ge=0),
    share_location: Optional[bool] = Query(None),
    show_distance_to_events: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Update current user's location preferences.
    Requires authentication.

    Query Parameters:
    - home_city_id: User's home city ID
    - preferred_distance_unit: "km" or "miles"/"mi"
    - max_search_distance: Maximum distance for searches
    - share_location: Whether to share location with other users
    - show_distance_to_events: Whether to show distances to events
    """
    from features_implementations.distance_models import UserLocationPreference

    prefs = db.query(UserLocationPreference).filter(
        UserLocationPreference.user_id == current_user.id
    ).first()

    if not prefs:
        prefs = UserLocationPreference(user_id=current_user.id)
        db.add(prefs)

    # Update only provided fields
    if home_city_id is not None:
        prefs.home_city_id = home_city_id
    if preferred_distance_unit:
        prefs.preferred_distance_unit = preferred_distance_unit
    if max_search_distance is not None:
        prefs.max_search_distance = max_search_distance
    if share_location is not None:
        prefs.share_location = share_location
    if show_distance_to_events is not None:
        prefs.show_distance_to_events = show_distance_to_events

    db.commit()
    db.refresh(prefs)

    return {
        "user_id": prefs.user_id,
        "home_city_id": prefs.home_city_id,
        "preferred_distance_unit": prefs.preferred_distance_unit,
        "max_search_distance": prefs.max_search_distance,
        "share_location": prefs.share_location,
        "show_distance_to_events": prefs.show_distance_to_events,
        "message": "Preferences updated successfully"
    }


# Import get_current_user_required if not already available
try:
    from auth import get_current_user_required
except ImportError:
    # Fallback if auth module structure is different
    def get_current_user_required(current_user: User = Depends(get_current_user)):
        if not current_user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return current_user
