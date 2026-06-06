#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Seed script para popular banco de dados com as 27 capitais brasileiras
Execute: python seed_cities.py
"""

from datetime import datetime, timedelta
from database import SessionLocal, City, CityChallenge, CityBadge, Base, engine
import json

CAPITAIS_BRASILEIRAS = [
    # NORTE
    {"slug": "macapa", "name": "Macapá", "state": "AP", "population": 512902, "landmark": "Forte de São José de Macapá", "ibge_code": 1600055},
    {"slug": "porto-velho", "name": "Porto Velho", "state": "RO", "population": 539205, "landmark": "Estação Férrea Madeira-Mamoré", "ibge_code": 1100205},
    {"slug": "boa-vista", "name": "Boa Vista", "state": "RR", "population": 330120, "landmark": "Catedral de Boa Vista", "ibge_code": 1400100},
    {"slug": "manaus", "name": "Manaus", "state": "AM", "population": 1802014, "landmark": "Teatro Amazonas", "ibge_code": 1302603},
    {"slug": "belem", "name": "Belém", "state": "PA", "population": 1506476, "landmark": "Basílica de Nazaré", "ibge_code": 1501402},
    {"slug": "palmas", "name": "Palmas", "state": "TO", "population": 305296, "landmark": "Praia da Graciosa", "ibge_code": 2804901},

    # NORDESTE
    {"slug": "sao-luis", "name": "São Luís", "state": "MA", "population": 1108975, "landmark": "Centro Histórico", "ibge_code": 2111300},
    {"slug": "teresina", "name": "Teresina", "state": "PI", "population": 866383, "landmark": "Ponte Getúlio Vargas", "ibge_code": 2211001},
    {"slug": "fortaleza", "name": "Fortaleza", "state": "CE", "population": 2669342, "landmark": "Praia de Iracema", "ibge_code": 2304400},
    {"slug": "natal", "name": "Natal", "state": "RN", "population": 885180, "landmark": "Ponte Newton Navarro", "ibge_code": 2408102},
    {"slug": "joao-pessoa", "name": "João Pessoa", "state": "PB", "population": 809051, "landmark": "Farol do Cabo Branco", "ibge_code": 2507507},
    {"slug": "recife", "name": "Recife", "state": "PE", "population": 1645727, "landmark": "Ponte Maurício de Nassau", "ibge_code": 2611606},
    {"slug": "maceio", "name": "Maceió", "state": "AL", "population": 1025360, "landmark": "Praia de Ponta Verde", "ibge_code": 2704302},
    {"slug": "salvador", "name": "Salvador", "state": "BA", "population": 2595140, "landmark": "Pelourinho", "ibge_code": 2704302},

    # CENTRO-OESTE
    {"slug": "brasilia", "name": "Brasília", "state": "DF", "population": 3124186, "landmark": "Catedral Metropolitana", "ibge_code": 5300108},
    {"slug": "goiania", "name": "Goiânia", "state": "GO", "population": 1536097, "landmark": "Praça Cívica", "ibge_code": 5208707},
    {"slug": "cuiaba", "name": "Cuiabá", "state": "MT", "population": 612547, "landmark": "Basílica do Senhor Bom Jesus", "ibge_code": 5103403},
    {"slug": "campo-grande", "name": "Campo Grande", "state": "MS", "population": 889975, "landmark": "Avenida Afonso Pena", "ibge_code": 5002704},

    # SUDESTE
    {"slug": "sao-paulo", "name": "São Paulo", "state": "SP", "population": 11975881, "landmark": "MASP", "ibge_code": 3550308},
    {"slug": "rio-de-janeiro", "name": "Rio de Janeiro", "state": "RJ", "population": 6775561, "landmark": "Cristo Redentor", "ibge_code": 3304557},
    {"slug": "vitoria", "name": "Vitória", "state": "ES", "population": 365855, "landmark": "Convento da Penha", "ibge_code": 3505708},
    {"slug": "belo-horizonte", "name": "Belo Horizonte", "state": "MG", "population": 2530701, "landmark": "Praça da Liberdade", "ibge_code": 3106200},

    # SUL
    {"slug": "curitiba", "name": "Curitiba", "state": "PR", "population": 1963726, "landmark": "Ópera de Arame", "ibge_code": 4106902},
    {"slug": "florianopolis", "name": "Florianópolis", "state": "SC", "population": 507178, "landmark": "Lagoa da Conceição", "ibge_code": 4204402},
    {"slug": "porto-alegre", "name": "Porto Alegre", "state": "RS", "population": 1440939, "landmark": "Guaíba", "ibge_code": 4314902},

    # Interior de PB (adicionado como referência)
    {"slug": "campina-grande", "name": "Campina Grande", "state": "PB", "population": 410332, "landmark": "Açude Epitácio Pessoa", "ibge_code": 2504009},

    # Cidades regionais importantes (adicionadas)
    {"slug": "abadiania", "name": "Abadiânia", "state": "GO", "population": 8442, "landmark": "Vale da Lua", "ibge_code": 5200050},
]

DESAFIOS_GLOBAIS = [
    {"title": "📸 Tire foto do landmark local", "description": "Fotografe o ponto turístico mais famoso da sua cidade", "reward": 100, "difficulty": "facil"},
    {"title": "🤝 Conheça alguém de outra capital", "description": "Envie mensagem para alguém de uma cidade diferente", "reward": 300, "difficulty": "medio"},
    {"title": "🎪 Organize um encontro", "description": "Crie um evento e consiga 5+ confirmações", "reward": 250, "difficulty": "dificil"},
    {"title": "🔥 Visite 3 salas novas", "description": "Explore e entre em 3 salas diferentes em 24h", "reward": 50, "difficulty": "facil"},
    {"title": "💬 Compartilhe uma dica local", "description": "Adicione uma dica útil sobre um lugar na sua cidade", "reward": 75, "difficulty": "facil"},
]

BADGES_GLOBAIS = [
    {"badge_type": "explorador", "description": "Visite 3+ salas em uma cidade"},
    {"badge_type": "conquistador", "description": "RSVP para 20+ eventos"},
    {"badge_type": "trending_king", "description": "Receba 50+ reações em posts"},
    {"badge_type": "ambassador", "description": "Visite todas as 27 capitais"},
    {"badge_type": "photographer", "description": "Complete 5 desafios de foto"},
    {"badge_type": "social_butterfly", "description": "Poste 50+ mensagens"},
    {"badge_type": "network_master", "description": "Converse com pessoas de 10+ cidades"},
]

def seed_database():
    # Criar tabelas se não existirem
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # Verificar se cidades já existem
        existing = db.query(City).count()
        if existing > 0:
            print(f"[OK] Banco ja tem {existing} cidades. Pulando seed de cidades.")
        else:
            print(f"[INFO] Adicionando {len(CAPITAIS_BRASILEIRAS)} capitais...")
            for cap in CAPITAIS_BRASILEIRAS:
                city = City(
                    slug=cap["slug"],
                    name=cap["name"],
                    state=cap["state"],
                    population=cap["population"],
                    landmark_image=f"https://via.placeholder.com/300x200?text={cap['landmark']}",
                    coordinates={"latitude": -10.0 + hash(cap["slug"]) % 30, "longitude": -50.0 + hash(cap["slug"]) % 30}
                )
                db.add(city)
            db.commit()
            print(f"[OK] {len(CAPITAIS_BRASILEIRAS)} capitais adicionadas!")

        # Adicionar desafios globais para cada cidade
        print("[INFO] Adicionando desafios...")
        cities = db.query(City).all()
        for city in cities:
            existing_challenges = db.query(CityChallenge).filter(CityChallenge.city_id == city.id).count()
            if existing_challenges == 0:
                for desafio in DESAFIOS_GLOBAIS:
                    challenge = CityChallenge(
                        city_id=city.id,
                        title=desafio["title"],
                        description=desafio["description"],
                        reward_points=desafio["reward"],
                        difficulty=desafio["difficulty"],
                        active=True
                    )
                    db.add(challenge)
        db.commit()
        print(f"[OK] Desafios adicionados para todas as cidades!")

        print("\n[SUCCESS] Seed completo!")
        print(f"Total de cidades: {db.query(City).count()}")
        print(f"Total de desafios: {db.query(CityChallenge).count()}")

    except Exception as e:
        print(f"[ERROR] Erro: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
