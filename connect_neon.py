#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os

# SECURITY: DATABASE_URL must come from environment variable (.env file or shell)
# DO NOT hardcode credentials here. Previous versions of this file leaked the
# Neon DATABASE_URL into git history (commits 2905930, 5950dd2) - that credential
# has since been rotated. See SECRETS_ROTATION_PLAN.md for details.
if not os.environ.get('DATABASE_URL'):
    # Auto-load from .env if available
    _env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(_env_path):
        with open(_env_path, encoding="utf-8") as _ef:
            for _line in _ef:
                _line = _line.strip()
                if _line.startswith("DATABASE_URL="):
                    os.environ['DATABASE_URL'] = _line.split("=", 1)[1].strip()
                    break

if not os.environ.get('DATABASE_URL'):
    raise RuntimeError(
        "DATABASE_URL not set. Add it to .env or export it before running this script."
    )

print("\n" + "="*80)
print("POPULANDO NEON REMOTAMENTE")
print("="*80 + "\n")

from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

db_url = os.environ['DATABASE_URL']
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

noticias_sql = [
    ("Macapá", "Prefeitura inaugura nova ponte sobre o Rio Amazonas", "Obra de 3 anos finalmente é entregue à população de Macapá.", "breaking_news"),
    ("Macapá", "Festival de Cultura Indígena acontece no mês que vem", "Celebração anual das tradições culturais da região norte.", "events"),
    ("Macapá", "Economia de Macapá cresce 5% no trimestre", "Setor de turismo lidera recuperação econômica.", "economy"),
    ("Macapá", "Universidade Federal abre 500 novas vagas", "Maior oferta de cursos de graduação na história da instituição.", "education"),
    ("Macapá", "Mercado de Peixe em Macapá é eleito patrimônio cultural", "IPHAN reconhece importância histórica do local.", "culture"),
    ("Belém", "Basílica de Nazaré recebe milhões de fiéis", "Romaria anual atrai peregrinos de todo o Brasil.", "religion"),
    ("Belém", "Museu Goeldi inaugura exposição sobre flora amazônica", "Mostra com 500 espécies de plantas nunca antes exibidas.", "culture"),
    ("Belém", "Porto de Belém bate recorde de movimentação", "Exportações de açaí crescem 40% em um ano.", "business"),
    ("Belém", "Novos corredores de ônibus conectam zona periférica", "Investimento em mobilidade urbana melhora acessibilidade.", "news"),
    ("Belém", "Chefs belenenses competem em festival gastronômico", "Culinária paraense é destaque em competição nacional.", "culture"),
    ("Rio de Janeiro", "Cristo Redentor recebe 2 milhões de visitantes em 2024", "Monumento continua sendo maior atração turística do Brasil.", "tourism"),
    ("Rio de Janeiro", "Praia de Copacabana ganha novo projeto de revitalização", "Investimento de R$ 50 milhões moderniza infraestrutura.", "urban_planning"),
    ("Rio de Janeiro", "Carnaval 2025 terá maior orçamento da história", "Escolas de samba recebem R$ 30 milhões para produção.", "events"),
    ("Rio de Janeiro", "Economia do Rio cresce com setor de startups", "150 novas empresas de tech estabelecem sedes na cidade.", "technology"),
    ("Rio de Janeiro", "Museu do Amanhã expõe tecnologia de ponta", "Exposição interativa atrai visitantes de todas as idades.", "culture"),
    ("São Paulo", "Metrô de SP expande com 20 novas estações", "Maior expansão de transporte público em 10 anos.", "urban_planning"),
    ("São Paulo", "MASP inicia temporada de exposições de arte moderna", "Mostra inclui obras de Portinari e Athos Bulcão.", "culture"),
    ("São Paulo", "São Paulo sedia Summit Global de Inovação", "10 mil participantes de 50 países se reúnem na capital.", "technology"),
    ("São Paulo", "Viaduto do Chá é reaberto após restauração", "Obra de arte histórica restaurada e pronta para uso.", "news"),
    ("São Paulo", "Restaurantes paulistas ganham 8 estrelas Michelin", "São Paulo reafirma posição como capital gastronômica.", "gastronomy"),
    ("Brasília", "Congresso Nacional aprova nova lei sobre sustentabilidade", "Medida ambiental é considerada histórica por especialistas.", "politics"),
    ("Brasília", "Esplanada dos Ministérios ganha novo projeto paisagístico", "Obra busca melhorar qualidade ambiental da capital.", "urban_planning"),
    ("Brasília", "Universidade de Brasília é ranqueada entre top 100 mundial", "UnB sobe 15 posições em ranking internacional.", "education"),
    ("Brasília", "Catedral Metropolitana comemora 50 anos", "Celebrações especiais ao longo de todo o ano.", "culture"),
    ("Brasília", "Brasília atrai investimentos em tecnologia limpa", "5 novas empresas de energia renovável se instalam.", "business"),
    ("Campina Grande", "Festa de São João é eleita melhor do Nordeste", "Rainha da Borborema mantém tradição de grandes celebrações.", "events"),
    ("Campina Grande", "Universidade Federal inicia pesquisa sobre secas", "Projeto busca soluções para crises hídricas.", "science"),
    ("Campina Grande", "Parque da Açude Epitácio Pessoa recebe novo projeto", "Espaço histórico ganha modernização mantendo identidade.", "urban_planning"),
    ("Campina Grande", "Quadrilhas juninas de Campina conquistam prêmios", "Tradição cultural alcança reconhecimento nacional.", "culture"),
    ("Campina Grande", "Comercio local cresce com turismo cultural", "Lojistas relatam aumento de 30% nas vendas.", "business"),
    ("Abadiânia", "Vale da Lua atrai turistas de todo o mundo", "Destino esotérico continua em alta.", "tourism"),
    ("Abadiânia", "Comunidade holística de Abadiânia cresce", "Pessoas buscam bem-estar e espiritualidade no Vale Místico.", "news"),
    ("Abadiânia", "Pousadas de Abadiânia ganham prêmio de hospitalidade", "Turismo interno reconhece qualidade de atendimento.", "business"),
    ("Abadiânia", "Abadiânia investe em preservação ambiental", "Projeto protege nascentes de água da região.", "environment"),
    ("Abadiânia", "Encontro anual de terapeutas atrai 5 mil pessoas", "Evento consolida Abadiânia como centro de práticas integrativas.", "events"),
]

eventos_sql = [
    ("Macapá", "Festival de Música Amazônica", "Shows de artistas regionais e nacionais.", "2026-07-15", "20:00", "Praça da Matriz"),
    ("Macapá", "Encontro de Povos Indígenas", "Celebração das tradições indígenas da Amazônia.", "2026-08-10", "09:00", "Centro Cultural"),
    ("Macapá", "Maratona de Macapá", "Corrida com 5km e 10km.", "2026-09-01", "06:00", "Avenida Edmundo Barbosa"),
    ("Macapá", "Feira do Açaí", "Degustação de produtos derivados do açaí.", "2026-09-20", "08:00", "Mercado Flutuante"),
    ("Macapá", "Workshop de Artesanato Local", "Aprenda técnicas tradicionais com mestres locais.", "2026-10-05", "14:00", "Casa da Cultura"),
    ("Belém", "Romaria da Basílica de Nazaré", "Celebração religiosa com procissão e missa.", "2026-10-08", "06:00", "Basílica de Nazaré"),
    ("Belém", "Mostra de Cinema Amazônico", "Documentários e filmes sobre a região.", "2026-07-20", "18:00", "Cine Líbero"),
    ("Belém", "Festa do Açaí", "Degustação e competição de receitas.", "2026-08-15", "17:00", "Mercado Ver-o-Peso"),
    ("Belém", "Passeio Gastronômico em Belém", "Tour por restaurantes tradicionais paraenses.", "2026-09-10", "19:00", "Centro Histórico"),
    ("Belém", "Encontro de Lendas Amazônicas", "Contação de histórias sobre mitologia amazônica.", "2026-10-30", "20:00", "Teatro da Paz"),
    ("Rio de Janeiro", "Carnaval Rio 2025", "Maior carnaval do mundo.", "2025-03-04", "20:00", "Sambodrome"),
    ("Rio de Janeiro", "Festival de Surf do Rio", "Competição internacional de surfe.", "2026-07-01", "08:00", "Praia de Arpoador"),
    ("Rio de Janeiro", "Cinema no Forte", "Sessão de cinema ao ar livre.", "2026-08-15", "19:30", "Forte de Copacabana"),
    ("Rio de Janeiro", "Festa da Cidade do Rio", "Celebração do aniversário da cidade.", "2026-11-20", "10:00", "Parque Lage"),
    ("Rio de Janeiro", "Festival de Jazz do Rio", "Apresentações de artistas internacionais.", "2026-09-05", "18:00", "Centro Cultural"),
    ("São Paulo", "Festa da Primavera SP", "Celebração da estação com atividades culturais.", "2026-09-21", "09:00", "Ibirapuera"),
    ("São Paulo", "São Paulo Fashion Week", "Maior semana de moda da América Latina.", "2026-11-01", "14:00", "Pavilhão da Bienal"),
    ("São Paulo", "Virada Cultural SP", "24 horas de arte, música e cultura.", "2026-05-16", "18:00", "Diversos locais"),
    ("São Paulo", "Marathon de São Paulo", "Corrida com 42km.", "2026-08-02", "07:00", "Av. Paulista"),
    ("São Paulo", "Festival de Cinema de SP", "Mostra de filmes nacionais e internacionais.", "2026-10-15", "19:00", "Espaço Itaú"),
    ("Brasília", "Aniversário de Brasília", "Celebração da capital com shows e eventos.", "2026-04-21", "10:00", "Esplanada"),
    ("Brasília", "Semana do Meio Ambiente", "Atividades sobre sustentabilidade.", "2026-06-05", "08:00", "Catedral"),
    ("Brasília", "Festival de Música Clássica", "Orquestras apresentam clássicos.", "2026-07-10", "20:00", "Auditório Nacional"),
    ("Brasília", "Passeio Cicloturístico", "Pedalada em grupo pela cidade.", "2026-08-22", "07:00", "Esplanada"),
    ("Brasília", "Congresso Nacional em Aberto", "Visitação especial ao prédio histórico.", "2026-09-15", "09:00", "Congresso"),
    ("Campina Grande", "São João de Campina Grande", "Maior festa junina da Paraíba.", "2026-06-23", "19:00", "Parque da Açude"),
    ("Campina Grande", "Festa da Rainha da Borborema", "Celebração da identidade local.", "2026-07-15", "18:00", "Praça da Bandeira"),
    ("Campina Grande", "Competição de Quadrilhas", "Disputa das melhores quadrilhas.", "2026-06-28", "20:00", "Estádio Presidente Varela"),
    ("Campina Grande", "Tour pela Campina Histórica", "Passeio guiado pela história da cidade.", "2026-08-10", "09:00", "Centro"),
    ("Campina Grande", "Show de Forró", "Apresentação de bandas tradicionais.", "2026-09-05", "21:00", "Parque da Açude"),
    ("Abadiânia", "Encontro de Terapeutas Holísticos", "3 dias de workshops e meditação.", "2026-07-01", "09:00", "Vale da Lua"),
    ("Abadiânia", "Passeio ao Vale da Lua", "Trilha e banho nas piscinas naturais.", "2026-08-15", "08:00", "Vale Místico"),
    ("Abadiânia", "Sessão de Cristais e Energia", "Experiência de cura com cristais.", "2026-09-10", "19:00", "Centro Espiritual"),
    ("Abadiânia", "Retiro de Yoga e Meditação", "7 dias de práticas integrativas.", "2026-10-05", "06:00", "Pousada Serrana"),
    ("Abadiânia", "Festa de Integração Comunitária", "Encontro entre turistas e moradores.", "2026-11-20", "17:00", "Praça Central"),
]

try:
    print("[INFO] Conectando ao Neon PostgreSQL...")
    engine = create_engine(db_url, poolclass=NullPool, echo=False)
    conn = engine.connect()
    print("[OK] Conectado!\n")

    print("[INFO] Limpando dados antigos...")
    conn.execute(text("DELETE FROM local_news"))
    conn.execute(text("DELETE FROM local_events"))
    conn.commit()
    print("[OK] Dados antigos removidos\n")

    print("[INFO] Inserindo 35 notícias...")
    for city, title, content, category in noticias_sql:
        conn.execute(text(
            "INSERT INTO local_news (city, title, content, category, source, published_at, created_at) VALUES (:city, :title, :content, :category, 'Local News', NOW(), NOW())"
        ), {"city": city, "title": title, "content": content, "category": category})
    conn.commit()
    print("[OK] Notícias inseridas\n")

    print("[INFO] Inserindo 35 eventos...")
    for city, title, description, date, time, location in eventos_sql:
        conn.execute(text(
            "INSERT INTO local_events (city, title, description, date, time, location, created_by_id, status, created_at) VALUES (:city, :title, :description, :date, :time, :location, 1, 'active', NOW())"
        ), {"city": city, "title": title, "description": description, "date": date, "time": time, "location": location})
    conn.commit()
    print("[OK] Eventos inseridos\n")

    conn.close()

    print("="*80)
    print("✅ NEON POPULADO COM SUCESSO!")
    print("="*80)
    print("\n📰 35 Notícias inseridas")
    print("🎪 35 Eventos inseridos")
    print("\n✨ TOTAL: 70 registros no banco NEON remoto!\n")

except Exception as e:
    print(f"[ERRO] {e}")
    import traceback
    traceback.print_exc()
