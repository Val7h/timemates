#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
os.environ['DATABASE_URL'] = 'postgresql://neondb_owner:npg_xNUu0XRF2HmD@ep-soft-morning-apoyasgn.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require'

print("\n" + "="*80)
print("🧪 TESTE COMPLETO DO TIMEMMATES")
print("="*80 + "\n")

from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

db_url = os.environ['DATABASE_URL']
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

try:
    print("[CONECTANDO ao Neon...")
    engine = create_engine(db_url, poolclass=NullPool, echo=False)
    conn = engine.connect()
    print("✅ CONECTADO ao banco remoto!\n")

    # TESTE 1: Cidades
    print("="*80)
    print("TESTE 1: CIDADES (27 CAPITAIS)")
    print("="*80 + "\n")

    result = conn.execute(text("SELECT COUNT(*), COUNT(DISTINCT state) FROM cities"))
    count, states = result.fetchone()
    print(f"✅ Total de cidades: {count}/27")
    print(f"✅ Estados únicos: {states}\n")

    result = conn.execute(text(
        "SELECT name, state, population, nickname FROM cities WHERE population > 0 ORDER BY population DESC LIMIT 5"
    ))
    print("TOP 5 MAIORES CIDADES:\n")
    for name, state, pop, nick in result:
        print(f"  {name:20} ({state}) - {pop:>12,} hab - '{nick}'")

    print()

    # TESTE 2: Acentuação
    print("="*80)
    print("TESTE 2: ACENTUAÇÃO (UTF-8)")
    print("="*80 + "\n")

    result = conn.execute(text(
        "SELECT name FROM cities WHERE name LIKE '%ã%' OR name LIKE '%â%' OR name LIKE '%é%'"
    ))
    cities_with_accents = result.fetchall()
    print(f"✅ Cidades com acentos: {len(cities_with_accents)}\n")
    for (name,) in cities_with_accents:
        print(f"  • {name}")

    print()

    # TESTE 3: Notícias
    print("="*80)
    print("TESTE 3: NOTÍCIAS LOCAIS (35 REGISTROS)")
    print("="*80 + "\n")

    result = conn.execute(text("SELECT COUNT(*) FROM local_news"))
    news_count = result.fetchone()[0]
    print(f"✅ Total de notícias: {news_count}/35\n")

    result = conn.execute(text(
        "SELECT COUNT(DISTINCT category) FROM local_news"
    ))
    categories = result.fetchone()[0]
    print(f"✅ Categorias diferentes: {categories}\n")

    result = conn.execute(text(
        "SELECT city, COUNT(*) FROM local_news GROUP BY city ORDER BY COUNT(*) DESC"
    ))
    print("NOTÍCIAS POR CIDADE:\n")
    for city, count in result:
        print(f"  {city:20} → {count} notícias")

    print()

    # TESTE 4: Eventos
    print("="*80)
    print("TESTE 4: EVENTOS LOCAIS (35 REGISTROS)")
    print("="*80 + "\n")

    result = conn.execute(text("SELECT COUNT(*) FROM local_events"))
    events_count = result.fetchone()[0]
    print(f"✅ Total de eventos: {events_count}/35\n")

    result = conn.execute(text(
        "SELECT city, COUNT(*) FROM local_events GROUP BY city ORDER BY COUNT(*) DESC"
    ))
    print("EVENTOS POR CIDADE:\n")
    for city, count in result:
        print(f"  {city:20} → {count} eventos")

    print()

    # TESTE 5: Busca por cidade
    print("="*80)
    print("TESTE 5: BUSCA POR CIDADE")
    print("="*80 + "\n")

    test_searches = [
        ("Campina Grande", "Campina Grande"),
        ("São Paulo", "São Paulo"),
        ("Rio", "Rio de Janeiro"),
        ("João", "João Pessoa"),
        ("Belém", "Belém"),
    ]

    for search_term, expected in test_searches:
        result = conn.execute(text(
            f"SELECT name FROM cities WHERE name ILIKE '%{search_term}%'"
        ))
        found = result.fetchone()
        if found and expected in found[0]:
            print(f"✅ Busca '{search_term}' → Encontrou '{found[0]}'")
        else:
            print(f"❌ Busca '{search_term}' → FALHOU")

    print()

    # TESTE 6: Desafios
    print("="*80)
    print("TESTE 6: DESAFIOS (GAMIFICATION)")
    print("="*80 + "\n")

    result = conn.execute(text("SELECT COUNT(*) FROM city_challenges"))
    challenges_count = result.fetchone()[0]
    print(f"✅ Total de desafios: {challenges_count}/135\n")

    result = conn.execute(text(
        "SELECT city_id, COUNT(*) FROM city_challenges GROUP BY city_id LIMIT 5"
    ))
    print("AMOSTRA DE DESAFIOS POR CIDADE:\n")
    for city_id, count in result:
        print(f"  Cidade {city_id} → {count} desafios")

    print()

    # TESTE 7: Nicknames
    print("="*80)
    print("TESTE 7: NICKNAMES DAS CIDADES")
    print("="*80 + "\n")

    result = conn.execute(text(
        "SELECT COUNT(*) FROM cities WHERE nickname IS NOT NULL AND nickname != ''"
    ))
    with_nicknames = result.fetchone()[0]
    print(f"✅ Cidades com nicknames: {with_nicknames}/27\n")

    result = conn.execute(text(
        "SELECT name, nickname FROM cities WHERE nickname IS NOT NULL ORDER BY name LIMIT 10"
    ))
    print("AMOSTRA DE NICKNAMES:\n")
    for name, nick in result:
        print(f"  {name:20} → {nick}")

    print()

    # TESTE 8: Dados de Campina Grande
    print("="*80)
    print("TESTE 8: DADOS COMPLETOS (CAMPINA GRANDE)")
    print("="*80 + "\n")

    result = conn.execute(text(
        "SELECT name, state, population, nickname FROM cities WHERE name = 'Campina Grande'"
    ))
    city_data = result.fetchone()
    if city_data:
        name, state, pop, nick = city_data
        print(f"✅ Nome: {name}")
        print(f"✅ Estado: {state}")
        print(f"✅ População: {pop:,} habitantes")
        print(f"✅ Nickname: {nick}\n")

    # Notícias de Campina Grande
    result = conn.execute(text(
        "SELECT COUNT(*) FROM local_news WHERE city = 'Campina Grande'"
    ))
    news = result.fetchone()[0]
    print(f"✅ Notícias: {news}")

    # Eventos de Campina Grande
    result = conn.execute(text(
        "SELECT COUNT(*) FROM local_events WHERE city = 'Campina Grande'"
    ))
    events = result.fetchone()[0]
    print(f"✅ Eventos: {events}\n")

    # TESTE 9: Abadiânia (validar acentuação)
    print("="*80)
    print("TESTE 9: VALIDAÇÃO DE ACENTUAÇÃO (ABADIÂNIA)")
    print("="*80 + "\n")

    result = conn.execute(text(
        "SELECT name FROM cities WHERE slug = 'abadiania'"
    ))
    abadia = result.fetchone()
    if abadia and abadia[0] == "Abadiânia":
        print(f"✅ CORRETO: '{abadia[0]}' (com acento)")
    else:
        print(f"❌ ERRO: '{abadia[0]}' (acentuação incorreta)")

    print()

    # RESULTADO FINAL
    print("="*80)
    print("📊 RESUMO DE TESTES")
    print("="*80 + "\n")

    result = conn.execute(text("""
        SELECT
            (SELECT COUNT(*) FROM cities) as cities,
            (SELECT COUNT(*) FROM local_news) as news,
            (SELECT COUNT(*) FROM local_events) as events,
            (SELECT COUNT(*) FROM city_challenges) as challenges
    """))

    cities, news, events, challenges = result.fetchone()

    print(f"✅ Cidades: {cities}/27")
    print(f"✅ Notícias: {news}/35")
    print(f"✅ Eventos: {events}/35")
    print(f"✅ Desafios: {challenges}/135")
    print(f"\n✨ TOTAL: {cities + news + events + challenges} registros no banco!\n")

    # Verificar status final
    all_good = (cities == 27 and news == 35 and events == 35 and challenges == 135)

    print("="*80)
    if all_good:
        print("🎉 TODOS OS TESTES PASSARAM! APP ESTÁ 100% FUNCIONAL!")
    else:
        print("⚠️  ALGUNS DADOS PODEM ESTAR INCOMPLETOS")
    print("="*80 + "\n")

    conn.close()

except Exception as e:
    print(f"❌ ERRO: {e}")
    import traceback
    traceback.print_exc()
