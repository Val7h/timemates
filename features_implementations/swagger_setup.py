# 📚 SWAGGER DOCUMENTATION SETUP
# Implementação para /docs e /redoc endpoints

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

def setup_swagger(app: FastAPI):
    """Configure Swagger documentation for FastAPI app"""

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title="TimeMates API",
            version="1.0.0",
            description="API para descobrir notícias, eventos e informações sobre cidades brasileiras com integração IBGE",
            routes=app.routes,
        )

        # Adicionar tags para organizar endpoints
        openapi_schema["tags"] = [
            {
                "name": "Cities",
                "description": "Endpoints relacionados a cidades brasileiras"
            },
            {
                "name": "News",
                "description": "Notícias locais por cidade"
            },
            {
                "name": "Events",
                "description": "Eventos locais por cidade"
            },
            {
                "name": "IBGE",
                "description": "Integração com dados IBGE em tempo real"
            },
            {
                "name": "Push Notifications",
                "description": "Gerenciar notificações push"
            },
            {
                "name": "Calendar",
                "description": "Integração com calendários (Google, Outlook)"
            },
            {
                "name": "Tourism",
                "description": "Dados turísticos e atrativos"
            },
            {
                "name": "Education",
                "description": "Eventos educacionais e workshops"
            }
        ]

        # Adicionar servidor info
        openapi_schema["servers"] = [
            {
                "url": "https://timemates.onrender.com",
                "description": "Production server"
            },
            {
                "url": "http://localhost:8000",
                "description": "Development server"
            }
        ]

        # Adicionar info de contato
        openapi_schema["info"]["contact"] = {
            "name": "TimeMates Support",
            "url": "https://github.com/Val7h/timemates",
            "email": "support@timemates.app"
        }

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi

    # URLs dos docs estarão em:
    # - Swagger UI: /docs
    # - ReDoc: /redoc

    return app


# EXEMPLO DE USO NO MAIN.PY:
"""
from fastapi import FastAPI
from features_implementations.swagger_setup import setup_swagger

app = FastAPI()

# Setup Swagger
setup_swagger(app)

# Agora acesse:
# http://localhost:8000/docs (Swagger UI)
# http://localhost:8000/redoc (ReDoc)
"""

# DOCUMENTAÇÃO DOS ENDPOINTS
"""
Endpoints que serão documentados:

CITIES:
  GET /api/cities - Listar todas 27 cidades
  GET /api/cities/top10/with-regions - Top 10 com regiões
  GET /api/city/{slug} - Info de uma cidade
  GET /api/city/{slug}/info-ibge - Info IBGE da cidade

NEWS:
  GET /api/news/{city} - Notícias de uma cidade
  GET /api/news/search - Buscar notícias

EVENTS:
  GET /api/events/{city} - Eventos de uma cidade
  POST /api/events/{id}/rsvp - Responder RSVP

IBGE:
  GET /api/city/{slug}/info-ibge - Dados IBGE em tempo real

PUSH:
  POST /api/subscribe - Subscribe para notificações
  POST /api/notifications/send - Enviar notificação

CALENDAR:
  POST /api/events/{id}/export-google - Exportar para Google
  POST /api/events/{id}/export-outlook - Exportar para Outlook

TOURISM:
  GET /api/tourism/{city}/attractions - Atrações
  GET /api/tourism/{city}/hotels - Hotéis
  GET /api/distance/{city1}/{city2} - Distância

EDUCATION:
  GET /api/education/workshops - Workshops
  POST /api/education/create - Criar workshop
"""
