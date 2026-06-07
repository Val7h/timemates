"""
Database models for distance calculation feature
Includes optional caching and distance history tracking
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class DistanceCache(Base):
    """
    Cache for calculated distances between cities.
    Improves performance by avoiding repeated calculations.
    """
    __tablename__ = "distance_cache"

    id = Column(Integer, primary_key=True, index=True)

    # City IDs (ordered to ensure consistency: min_id, max_id)
    city1_id = Column(Integer, ForeignKey("cities.id"), nullable=False, index=True)
    city2_id = Column(Integer, ForeignKey("cities.id"), nullable=False, index=True)

    # Cached distances
    distance_km = Column(Float, nullable=False)  # Always stored in km
    distance_miles = Column(Float, nullable=False)

    # Metadata
    calculated_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    use_count = Column(Integer, default=1)  # Track popularity for maintenance

    # For composite uniqueness (city1_id, city2_id) must be unique
    # Index both to speed up lookups
    __table_args__ = (
        {"indexes": [
            {"name": "idx_distance_cache_cities", "columns": ["city1_id", "city2_id"]},
        ]},
    )

    def __repr__(self):
        return f"<DistanceCache({self.city1_id}, {self.city2_id}, {self.distance_km}km)>"


class DistanceQuery(Base):
    """
    Log of distance queries for analytics and user preferences.
    Track what distance queries users are making.
    """
    __tablename__ = "distance_queries"

    id = Column(Integer, primary_key=True, index=True)

    # User who made the query
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # Query parameters
    origin_city_id = Column(Integer, ForeignKey("cities.id"), nullable=True, index=True)
    destination_city_id = Column(Integer, ForeignKey("cities.id"), nullable=True)

    # For arbitrary coordinate queries
    origin_latitude = Column(Float, nullable=True)
    origin_longitude = Column(Float, nullable=True)
    destination_latitude = Column(Float, nullable=True)
    destination_longitude = Column(Float, nullable=True)

    # Query result
    distance_km = Column(Float, nullable=False)
    query_type = Column(String(50), nullable=False)  # "city_to_city", "point_to_city", "point_to_point", "nearby"
    unit = Column(String(10), default="km")

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    ip_address = Column(String(50), nullable=True)  # For analytics

    def __repr__(self):
        return f"<DistanceQuery({self.query_type}, {self.distance_km}{self.unit})>"


class UserLocationPreference(Base):
    """
    User preferences for location-based features.
    Stores user's home city and distance preferences.
    """
    __tablename__ = "user_location_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)

    # User's home/preferred city
    home_city_id = Column(Integer, ForeignKey("cities.id"), nullable=True)

    # Distance preferences
    preferred_distance_unit = Column(String(10), default="km")  # "km" or "miles"
    max_search_distance = Column(Float, nullable=True)  # e.g., 100 (km or miles)

    # Location privacy
    share_location = Column(Boolean, default=True)
    show_distance_to_events = Column(Boolean, default=True)

    # Metadata
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<UserLocationPreference(user={self.user_id}, city={self.home_city_id})>"


class DistanceBasedRecommendation(Base):
    """
    Recommendations based on distance (events, rooms, people).
    Store recommendations to avoid recalculation.
    """
    __tablename__ = "distance_based_recommendations"

    id = Column(Integer, primary_key=True, index=True)

    # User receiving recommendation
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Recommendation target (polymorphic - could be event, room, person)
    target_type = Column(String(50), nullable=False)  # "room", "event", "user"
    target_id = Column(Integer, nullable=False)

    # Distance from user's location
    distance_km = Column(Float, nullable=False)

    # Recommendation score (distance-based + other factors)
    recommendation_score = Column(Float, default=0.0)  # 0-100

    # Metadata
    calculated_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # When to recalculate

    def __repr__(self):
        return f"<DistanceBasedRecommendation(user={self.user_id}, {self.target_type}, {self.distance_km}km)>"
