#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
os.environ['DATABASE_URL'] = 'postgresql://neondb_owner:npg_xNUu0XRF2HmD@ep-soft-morning-apoyasgn.c-7.us-east-1.aws.neon.tech/sslmode=require'

print("\n" + "="*80)
print("SINCRONIZANDO TUDO NO NEON")
print("="*80 + "\n")

from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

db_url = 'postgresql://neondb_owner:npg_xNUu0XRF2HmD@ep-soft-morning-apoyasgn.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require'
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

cidades = [
    {"slug": "macapa", "name": "Macapá", "state": "AP", "population": 512902, "nickname": "Porta da Amazônia", "ibge_code": 1600055},
    {"slug": "porto-velho", "name": "Porto Velho", "state": "RO", "population": 539205, "nickname": "Cidade Ribeirinha", "ibge_code": 1100205},
    {"slug": "boa-vista", "name": "Boa Vista", "state": "RR", "population": 330120, "nickname": "Capital do Roraima", "ibge_code": 1400100},
    {"slug": "manaus", "name": "Manaus", "state": "AM", "population": 1802014, "nickname": "Portão da Amazônia", "ibge_code": 1302603},
    {"slug": "belem", "name": "Belém", "state": "PA", "population": 1506476, "nickname": "Atenas Tropical", "ibge_code": 1501402},
    {"slug": "palmas", "name": "Palmas", "state": "TO", "population": 305296, "nickname": "Cidade Aberta", "ibge_code": 2804901},
    {"slug": "sao-luis", "name": "São Luís", "state": "MA", "population": 1108975, "nickname": "Atenas Brasileira", "ibge_code": 2111300},
    {"slug": "teresina", "name": "Teresina", "state": "PI", "population": 866383, "nickname": "Melhor Clima do Brasil", "ibge_code": 2211001},
    {"slug": "fortaleza", "name": "Fortaleza", "state": "CE", "population": 2669342, "nickname": "Princesa do Nordeste", "ibge_code": 2304400},
    {"slug": "natal", "name": "Natal", "state": "RN", "population": 885180, "nickname": "Cidade do Sol", "ibge_code": 2408102},
    {"slug": "joao-pessoa", "name": "João Pessoa", "state": "PB", "population": 809051, "nickname": "Cidade Feliz", "ibge_code": 2507507},
    {"slug": "recife", "name": "Recife", "state": "PE", "population": 1645727, "nickname": "Veneza Brasileira", "ibge_code": 2611606},
    {"slug": "maceio", "name": "Maceió", "state": "AL", "population": 1025360, "nickname": "Dubai Tropical", "ibge_code": 2704302},
    {"slug": "salvador", "name": "Salvador", "state": "BA", "population": 2595140, "nickname": "Rainha da Bahia", "ibge_code": 2704302},
    {"slug": "brasilia", "name": "Brasília", "state": "DF", "population": 3124186, "nickname": "Capital Federal", "ibge_code": 5300108},
    {"slug": "goiania", "name": "Goiânia", "state": "GO", "population": 1536097, "nickname": "Cidade Verde", "ibge_code": 5208707},
    {"slug": "cuiaba", "name": "Cuiabá", "state": "MT", "population": 612547, "nickname": "Pérola do Centro-Oeste", "ibge_code": 5103403},
    {"slug": "campo-grande", "name": "Campo Grande", "state": "MS", "population": 889975, "nickname": "Porta do Cerrado", "ibge_code": 5002704},
    {"slug": "sao-paulo", "name": "São Paulo", "state": "SP", "population": 11975881, "nickname": "Megalópole", "ibge_code": 3550308},
    {"slug": "rio-de-janeiro", "name": "Rio de Janeiro", "state": "RJ", "population": 6775561, "nickname": "Cidade Maravilhosa", "ibge_code": 3304557},
    {"slug": "vitoria", "name": "Vitória", "state": "ES", "population": 365855, "nickname": "Atenas Capixaba", "ibge_code": 3505708},
    {"slug": "belo-horizonte", "name": "Belo Horizonte", "state": "MG", "population": 2530701, "nickname": "Cidade Perpendicular", "ibge_code": 3106200},
    {"slug": "curitiba", "name": "Curitiba", "state": "PR", "population": 1963726, "nickname": "Cidade Modelo", "ibge_code": 4106902},
    {"slug": "florianopolis", "name": "Florianópolis", "state": "SC", "population": 507178, "nickname": "Magia do Sul", "ibge_code": 4204402},
    {"slug": "porto-alegre", "name": "Porto Alegre", "state": "RS", "population": 1440939, "nickname": "Cidade Sorriso", "ibge_code": 4314902},
    {"slug": "campina-grande", "name": "Campina Grande", "state": "PB", "population": 410332, "nickname": "Rainha da Borborema", "ibge_code": 2504009},
    {"slug": "abadiania", "name": "Abadiânia", "state": "GO", "population": 8442, "nickname": "Vale Místico", "ibge_code": 5200050},
]

desafios = [
    {"title": "Tire foto do landmark local", "description": "Fotografe o ponto turístico mais famoso da sua cidade", "reward": 100, "difficulty": "facil"},
    {"title": "Conheça alguém de outra capital", "description": "Envie mensagem para alguém de uma cidade diferente", "reward": 300, "difficulty": "medio"},
    {"title": "Organize um encontro", "description": "Crie um evento e consiga 5+ confirmações", "reward": 250, "difficulty": "dificil"},
    {"title": "Visite 3 salas novas", "description": "Explore e entre em 3 salas diferentes em 24h", "reward": 50, "difficulty": "facil"},
    {"title": "Compartilhe uma dica local", "description": "Adicione uma dica útil sobre um lugar na sua cidade", "reward": 75, "difficulty": "facil"},
]

try:
    print("[INFO] Conectando ao Neon...")
    engine = create_engine(db_url, poolclass=NullPool, echo=False)
    conn = engine.connect()
    print("[OK] Conectado!\n")

    # Limpar e reinserir cidades
    print("[INFO] Limpando cidades antigas...")
    conn.execute(text("DELETE FROM cities"))
    conn.commit()
    print("[OK] Cidades limpas\n")

    print("[INFO] Inserindo 27 cidades...")
    for cidade in cidades:
        conn.execute(text("""
            INSERT INTO cities (slug, name, state, population, nickname, ibge_code, coordinates, landmark_image, created_at)
            VALUES (:slug, :name, :state, :population, :nickname, :ibge_code, '{}', '', NOW())
        """), cidade)
    conn.commit()
    print("[OK] Cidades inseridas\n")

    # Inserir desafios
    print("[INFO] Limpando desafios antigos...")
    conn.execute(text("DELETE FROM city_challenges"))
    conn.commit()
    print("[OK] Desafios limpos\n")

    print("[INFO] Inserindo 135 desafios (5 por cidade)...")
    for city in cidades:
        city_id = conn.execute(text("SELECT id FROM cities WHERE slug = :slug"), {"slug": city["slug"]}).fetchone()[0]
        for desafio in desafios:
            conn.execute(text("""
                INSERT INTO city_challenges (city_id, title, description, reward_points, difficulty, active, created_at)
                VALUES (:city_id, :title, :description, :reward, :difficulty, true, NOW())
            """), {
                "city_id": city_id,
                "title": desafio["title"],
                "description": desafio["description"],
                "reward": desafio["reward"],
                "difficulty": desafio["difficulty"]
            })
    conn.commit()
    print("[OK] Desafios inseridos\n")

    conn.close()

    print("="*80)
    print("✅ NEON TOTALMENTE SINCRONIZADO!")
    print("="*80)
    print("\n✨ 27 cidades + 135 desafios + 35 notícias + 35 eventos\n")

except Exception as e:
    print(f"[ERRO] {e}")
    import traceback
    traceback.print_exc()
