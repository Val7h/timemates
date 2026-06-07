# 🏖️ TOURISM DATA & DISTANCE CALCULATION
# Atrações turísticas, hotéis, restaurantes, cálculo de distância

from sqlalchemy import Column, Integer, String, Float, DateTime
from fastapi import FastAPI, Depends
from math import radians, cos, sin, asin, sqrt

# DATABASE MODELS
class TouristAttraction:
    """Atrações turísticas, hotéis, restaurantes"""
    __tablename__ = "tourist_attractions"

    id = Column(Integer, primary_key=True)
    city_id = Column(Integer, ForeignKey("cities.id"))
    name = Column(String(200))
    type = Column(String(50))  # attraction, hotel, restaurant, museum, park
    description = Column(String(2000))
    rating = Column(Float)  # 1-5
    address = Column(String(500))
    phone = Column(String(20))
    website = Column(String(500))
    image_url = Column(String(500))
    latitude = Column(Float)
    longitude = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


# DISTANCE CALCULATION (Haversine Formula)
def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcular distância entre dois pontos em km
    usando fórmula de Haversine
    """
    # Converter para radianos
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Fórmula de Haversine
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Raio da Terra em km

    return c * r


def setup_tourism_section(app: FastAPI):
    """Setup tourism endpoints"""

    @app.get("/api/tourism/{city}/attractions")
    def get_attractions(city: str, db: Session = Depends(get_db)):
        """Listar atrações turísticas da cidade"""
        city_obj = db.query(City).filter(City.name == city).first()

        if not city_obj:
            raise HTTPException(status_code=404, detail="City not found")

        attractions = db.query(TouristAttraction).filter(
            TouristAttraction.city_id == city_obj.id,
            TouristAttraction.type == "attraction"
        ).order_by(TouristAttraction.rating.desc()).all()

        return {
            "success": True,
            "city": city,
            "data": attractions
        }

    @app.get("/api/tourism/{city}/hotels")
    def get_hotels(city: str, db: Session = Depends(get_db)):
        """Listar hotéis da cidade"""
        city_obj = db.query(City).filter(City.name == city).first()

        if not city_obj:
            raise HTTPException(status_code=404, detail="City not found")

        hotels = db.query(TouristAttraction).filter(
            TouristAttraction.city_id == city_obj.id,
            TouristAttraction.type == "hotel"
        ).order_by(TouristAttraction.rating.desc()).all()

        return {
            "success": True,
            "city": city,
            "data": hotels
        }

    @app.get("/api/tourism/{city}/restaurants")
    def get_restaurants(city: str, db: Session = Depends(get_db)):
        """Listar restaurantes da cidade"""
        city_obj = db.query(City).filter(City.name == city).first()

        if not city_obj:
            raise HTTPException(status_code=404, detail="City not found")

        restaurants = db.query(TouristAttraction).filter(
            TouristAttraction.city_id == city_obj.id,
            TouristAttraction.type == "restaurant"
        ).order_by(TouristAttraction.rating.desc()).all()

        return {
            "success": True,
            "city": city,
            "data": restaurants
        }

    @app.get("/api/distance/{city1}/{city2}")
    def get_distance(city1: str, city2: str, db: Session = Depends(get_db)):
        """Calcular distância entre duas cidades"""
        c1 = db.query(City).filter(City.name == city1).first()
        c2 = db.query(City).filter(City.name == city2).first()

        if not c1 or not c2:
            raise HTTPException(status_code=404, detail="City not found")

        coords1 = c1.coordinates or {"lat": 0, "lng": 0}
        coords2 = c2.coordinates or {"lat": 0, "lng": 0}

        distance_km = haversine_distance(
            coords1["lat"], coords1["lng"],
            coords2["lat"], coords2["lng"]
        )

        return {
            "success": True,
            "from": city1,
            "to": city2,
            "distance_km": round(distance_km, 2),
            "distance_miles": round(distance_km * 0.621371, 2),
            "driving_time_hours": round(distance_km / 100, 1)  # Aproximado
        }

    @app.get("/api/tourism/recommended-routes")
    def get_recommended_routes(db: Session = Depends(get_db)):
        """Retornar rotas turísticas recomendadas entre cidades"""
        routes = [
            {
                "name": "Rota Nordeste",
                "cities": ["Salvador", "Recife", "Natal", "Fortaleza"],
                "highlights": "Praias paradisíacas e cultura nordestina"
            },
            {
                "name": "Rota Sudeste",
                "cities": ["Rio de Janeiro", "São Paulo", "Belo Horizonte"],
                "highlights": "Cultura, natureza e vida urbana"
            },
            {
                "name": "Rota Sul",
                "cities": ["Curitiba", "Porto Alegre", "Florianópolis"],
                "highlights": "Natureza e clima temperado"
            },
            {
                "name": "Rota Centro-Oeste",
                "cities": ["Brasília", "Cuiabá", "Goiânia"],
                "highlights": "Cerrado e capital do Brasil"
            }
        ]

        # Calcular distâncias entre cidades de cada rota
        for route in routes:
            total_distance = 0
            for i in range(len(route["cities"]) - 1):
                c1 = db.query(City).filter(City.name == route["cities"][i]).first()
                c2 = db.query(City).filter(City.name == route["cities"][i+1]).first()

                if c1 and c2:
                    coords1 = c1.coordinates or {"lat": 0, "lng": 0}
                    coords2 = c2.coordinates or {"lat": 0, "lng": 0}
                    distance = haversine_distance(
                        coords1["lat"], coords1["lng"],
                        coords2["lat"], coords2["lng"]
                    )
                    total_distance += distance

            route["total_distance_km"] = round(total_distance, 2)
            route["estimated_days"] = round(total_distance / 500, 1)  # 500km/dia

        return {
            "success": True,
            "routes": routes
        }


# DADOS SEED
tourism_seed = [
    # São Paulo
    {"city": "São Paulo", "name": "Museu de Arte de SP (MASP)", "type": "museum", "rating": 4.8},
    {"city": "São Paulo", "name": "Pinacoteca do Estado", "type": "museum", "rating": 4.7},
    {"city": "São Paulo", "name": "Rua 25 de Março", "type": "attraction", "rating": 4.0},

    # Rio de Janeiro
    {"city": "Rio de Janeiro", "name": "Cristo Redentor", "type": "attraction", "rating": 4.9},
    {"city": "Rio de Janeiro", "name": "Pão de Açúcar", "type": "attraction", "rating": 4.8},
    {"city": "Rio de Janeiro", "name": "Praia de Copacabana", "type": "attraction", "rating": 4.5},

    # Outras cidades...
]
