"""
Distance Calculation Feature for TimeMates
Calculates distance between cities using Haversine formula
Supports km, miles, and custom range queries
"""

from math import radians, sin, cos, sqrt, atan2
from typing import Dict, Tuple, Optional, List
from sqlalchemy.orm import Session


class DistanceCalculator:
    """Haversine formula-based distance calculator for geographic coordinates."""

    EARTH_RADIUS_KM = 6371  # Earth's radius in kilometers
    EARTH_RADIUS_MILES = 3959  # Earth's radius in miles

    @staticmethod
    def haversine(
        lat1: float, lon1: float,
        lat2: float, lon2: float,
        unit: str = "km"
    ) -> float:
        """
        Calculate distance between two points using Haversine formula.

        Args:
            lat1, lon1: Latitude and longitude of first point (degrees)
            lat2, lon2: Latitude and longitude of second point (degrees)
            unit: "km" (kilometers) or "miles" (miles or "mi")

        Returns:
            Distance between points in specified unit
        """
        radius = DistanceCalculator.EARTH_RADIUS_KM if unit in ("km", "kilometer") else DistanceCalculator.EARTH_RADIUS_MILES

        # Convert to radians
        lat1_rad = radians(lat1)
        lon1_rad = radians(lon1)
        lat2_rad = radians(lat2)
        lon2_rad = radians(lon2)

        # Differences
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        # Haversine formula
        a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        distance = radius * c

        return round(distance, 2)

    @staticmethod
    def extract_coordinates(coord_data: Dict) -> Optional[Tuple[float, float]]:
        """
        Extract latitude and longitude from coordinate data.

        Args:
            coord_data: Dictionary with 'latitude' and 'longitude' keys

        Returns:
            Tuple of (latitude, longitude) or None if invalid
        """
        if not coord_data or not isinstance(coord_data, dict):
            return None

        try:
            lat = float(coord_data.get("latitude", 0))
            lon = float(coord_data.get("longitude", 0))
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return (lat, lon)
        except (ValueError, TypeError):
            pass

        return None

    @staticmethod
    def is_valid_coordinate(lat: float, lon: float) -> bool:
        """Check if latitude and longitude are valid."""
        try:
            return -90 <= float(lat) <= 90 and -180 <= float(lon) <= 180
        except (ValueError, TypeError):
            return False

    @staticmethod
    def calculate_distance(
        lat1: float, lon1: float,
        lat2: float, lon2: float,
        unit: str = "km"
    ) -> Dict:
        """
        Calculate distance between two coordinates with validation.

        Args:
            lat1, lon1: First point coordinates
            lat2, lon2: Second point coordinates
            unit: Distance unit ("km" or "miles"/"mi")

        Returns:
            Dictionary with distance and unit
        """
        if not (DistanceCalculator.is_valid_coordinate(lat1, lon1) and
                DistanceCalculator.is_valid_coordinate(lat2, lon2)):
            return {"error": "Invalid coordinates", "distance": None}

        distance = DistanceCalculator.haversine(lat1, lon1, lat2, lon2, unit)

        return {
            "distance": distance,
            "unit": unit,
            "error": None
        }


class CityDistanceCalculator:
    """Calculate distances between cities in the database."""

    @staticmethod
    def get_city_coordinates(db: Session, city_id: int) -> Optional[Tuple[float, float]]:
        """Get coordinates for a city by ID."""
        from database import City

        city = db.query(City).filter(City.id == city_id).first()
        if not city or not city.coordinates:
            return None

        return DistanceCalculator.extract_coordinates(city.coordinates)

    @staticmethod
    def distance_between_cities(
        db: Session,
        city1_id: int,
        city2_id: int,
        unit: str = "km"
    ) -> Dict:
        """Calculate distance between two cities."""
        from database import City

        city1 = db.query(City).filter(City.id == city1_id).first()
        city2 = db.query(City).filter(City.id == city2_id).first()

        if not city1 or not city2:
            return {"error": "One or both cities not found", "distance": None}

        coords1 = DistanceCalculator.extract_coordinates(city1.coordinates)
        coords2 = DistanceCalculator.extract_coordinates(city2.coordinates)

        if not coords1 or not coords2:
            return {"error": "Missing coordinates for one or both cities", "distance": None}

        distance = DistanceCalculator.haversine(
            coords1[0], coords1[1],
            coords2[0], coords2[1],
            unit
        )

        return {
            "city1": city1.name,
            "city1_id": city1.id,
            "city2": city2.name,
            "city2_id": city2.id,
            "distance": distance,
            "unit": unit,
            "error": None
        }

    @staticmethod
    def find_nearby_cities(
        db: Session,
        city_id: int,
        max_distance: float,
        unit: str = "km"
    ) -> List[Dict]:
        """
        Find all cities within a specified distance.

        Args:
            db: Database session
            city_id: Reference city ID
            max_distance: Maximum distance radius
            unit: Distance unit ("km" or "miles"/"mi")

        Returns:
            List of cities with their distances, sorted by distance
        """
        from database import City

        center_city = db.query(City).filter(City.id == city_id).first()
        if not center_city:
            return []

        center_coords = DistanceCalculator.extract_coordinates(center_city.coordinates)
        if not center_coords:
            return []

        # Get all cities
        all_cities = db.query(City).filter(City.id != city_id).all()

        nearby = []
        for city in all_cities:
            coords = DistanceCalculator.extract_coordinates(city.coordinates)
            if not coords:
                continue

            distance = DistanceCalculator.haversine(
                center_coords[0], center_coords[1],
                coords[0], coords[1],
                unit
            )

            if distance <= max_distance:
                nearby.append({
                    "id": city.id,
                    "name": city.name,
                    "state": city.state,
                    "distance": distance,
                    "unit": unit,
                    "population": city.population,
                    "coordinates": city.coordinates
                })

        # Sort by distance
        nearby.sort(key=lambda x: x["distance"])

        return nearby

    @staticmethod
    def find_cities_by_distance_range(
        db: Session,
        lat: float,
        lon: float,
        min_distance: float,
        max_distance: float,
        unit: str = "km"
    ) -> List[Dict]:
        """
        Find all cities within a distance range from a given point.

        Args:
            db: Database session
            lat, lon: Reference point coordinates
            min_distance: Minimum distance radius
            max_distance: Maximum distance radius
            unit: Distance unit ("km" or "miles"/"mi")

        Returns:
            List of cities within range, sorted by distance
        """
        from database import City

        if not DistanceCalculator.is_valid_coordinate(lat, lon):
            return []

        all_cities = db.query(City).all()

        results = []
        for city in all_cities:
            coords = DistanceCalculator.extract_coordinates(city.coordinates)
            if not coords:
                continue

            distance = DistanceCalculator.haversine(
                lat, lon,
                coords[0], coords[1],
                unit
            )

            if min_distance <= distance <= max_distance:
                results.append({
                    "id": city.id,
                    "name": city.name,
                    "state": city.state,
                    "distance": distance,
                    "unit": unit,
                    "population": city.population,
                    "coordinates": city.coordinates
                })

        results.sort(key=lambda x: x["distance"])
        return results

    @staticmethod
    def get_distance_stats(
        db: Session,
        city_id: int,
        unit: str = "km"
    ) -> Dict:
        """
        Get distance statistics for a city to all other cities.

        Args:
            db: Database session
            city_id: Reference city ID
            unit: Distance unit ("km" or "miles"/"mi")

        Returns:
            Dictionary with min, max, average distances
        """
        from database import City

        center_city = db.query(City).filter(City.id == city_id).first()
        if not center_city:
            return {"error": "City not found"}

        center_coords = DistanceCalculator.extract_coordinates(center_city.coordinates)
        if not center_coords:
            return {"error": "Invalid coordinates"}

        all_cities = db.query(City).filter(City.id != city_id).all()

        distances = []
        for city in all_cities:
            coords = DistanceCalculator.extract_coordinates(city.coordinates)
            if coords:
                distance = DistanceCalculator.haversine(
                    center_coords[0], center_coords[1],
                    coords[0], coords[1],
                    unit
                )
                distances.append(distance)

        if not distances:
            return {"error": "No valid cities to compare"}

        return {
            "city": center_city.name,
            "city_id": city_id,
            "min_distance": min(distances),
            "max_distance": max(distances),
            "average_distance": round(sum(distances) / len(distances), 2),
            "total_cities": len(distances),
            "unit": unit,
            "error": None
        }
