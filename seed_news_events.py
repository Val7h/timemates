#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Seed script para popular notícias e eventos das 27 capitais
Execute: python seed_news_events.py
"""

from datetime import datetime, timedelta
from database import SessionLocal, LocalNews, LocalEvent, Base, engine
import random

# Notícias por cidade
NOTICIAS_POR_CIDADE = {
    "Macapá": [
        {"title": "Prefeitura inaugura nova ponte sobre o Rio Amazonas", "category": "breaking_news", "description": "Obra de 3 anos finalmente é entregue à população de Macapá."},
        {"title": "Festival de Cultura Indígena acontece no mês que vem", "category": "events", "description": "Celebração anual das tradições culturais da região norte."},
        {"title": "Economia de Macapá cresce 5% no trimestre", "category": "economy", "description": "Setor de turismo lidera recuperação econômica."},
        {"title": "Universidade Federal abre 500 novas vagas", "category": "education", "description": "Maior oferta de cursos de graduação na história da instituição."},
        {"title": "Mercado de Peixe em Macapá é eleito patrimônio cultural", "category": "culture", "description": "IPHAN reconhece importância histórica do local."},
    ],
    "Belém": [
        {"title": "Basilíca de Nazaré recebe milhões de fiéis", "category": "religion", "description": "Romaria anual atrai peregrinos de todo o Brasil."},
        {"title": "Museu Goeldi inaugura exposição sobre flora amazônica", "category": "culture", "description": "Mostra com 500 espécies de plantas nunca antes exibidas."},
        {"title": "Porto de Belém bate recorde de movimentação", "category": "business", "description": "Exportações de açaí crescem 40% em um ano."},
        {"title": "Novos corredores de ônibus conectam zona periférica", "category": "news", "description": "Investimento em mobilidade urbana melhora acessibilidade."},
        {"title": "Chefs belenenses competem em festival gastronômico", "category": "culture", "description": "Culinária paraense é destaque em competição nacional."},
    ],
    "Rio de Janeiro": [
        {"title": "Cristo Redentor recebe 2 milhões de visitantes em 2024", "category": "tourism", "description": "Monumento continua sendo maior atração turística do Brasil."},
        {"title": "Praia de Copacabana ganha novo projeto de revitalização", "category": "urban_planning", "description": "Investimento de R$ 50 milhões moderniza infraestrutura."},
        {"title": "Carnaval 2025 terá maior orçamento da história", "category": "events", "description": "Escolas de samba recebem R$ 30 milhões para produção."},
        {"title": "Economia do Rio cresce com setor de startups", "category": "technology", "description": "150 novas empresas de tech estabelecem sedes na cidade."},
        {"title": "Museu do Amanhã expõe tecnologia de ponta", "category": "culture", "description": "Exposição interativa atrai visitantes de todas as idades."},
    ],
    "São Paulo": [
        {"title": "Metrô de SP expande com 20 novas estações", "category": "urban_planning", "description": "Maior expansão de transporte público em 10 anos."},
        {"title": "MASP inicia temporada de exposições de arte moderna", "category": "culture", "description": "Mostra inclui obras de Portinari e Athos Bulcão."},
        {"title": "São Paulo sedia Summit Global de Inovação", "category": "technology", "description": "10 mil participantes de 50 países se reúnem na capital."},
        {"title": "Viaduto do Chá é reaberto após restauração", "category": "news", "description": "Obra de arte histórica restaurada e pronta para uso."},
        {"title": "Restaurantes paulistas ganham 8 estrelas Michelin", "category": "gastronomy", "description": "São Paulo reafirma posição como capital gastronômica."},
    ],
    "Brasília": [
        {"title": "Congresso Nacional aprova nova lei sobre sustentabilidade", "category": "politics", "description": "Medida ambiental é considerada histórica por especialistas."},
        {"title": "Esplanada dos Ministérios ganha novo projeto paisagístico", "category": "urban_planning", "description": "Obra busca melhorar qualidade ambiental da capital."},
        {"title": "Universidade de Brasília é ranqueada entre top 100 mundial", "category": "education", "description": "UnB sobe 15 posições em ranking internacional."},
        {"title": "Catedral Metropolitana comemora 50 anos", "category": "culture", "description": "Celebrações especiais ao longo de todo o ano."},
        {"title": "Brasília atrai investimentos em tecnologia limpa", "category": "business", "description": "5 novas empresas de energia renovável se instalam."},
    ],
    "Campina Grande": [
        {"title": "Festa de São João é eleita melhor do Nordeste", "category": "events", "description": "Rainha da Borborema mantém tradição de grandes celebrações."},
        {"title": "Universidade Federal inicia pesquisa sobre secas", "category": "science", "description": "Projeto busca soluções para crises hídricas."},
        {"title": "Parque da Açude Epitácio Pessoa recebe novo projeto", "category": "urban_planning", "description": "Espaço histórico ganha modernização mantendo identidade."},
        {"title": "Quadrilhas juninas de Campina conquistam prêmios", "category": "culture", "description": "Tradição cultural alcança reconhecimento nacional."},
        {"title": "Comercio local cresce com turismo cultural", "category": "business", "description": "Lojistas relatam aumento de 30% nas vendas."},
    ],
    "Abadiânia": [
        {"title": "Vale da Lua atrai turistas de todo o mundo", "category": "tourism", "description": "Destino esotérico continua em alta."},
        {"title": "Comunidade holística de Abadiânia cresce", "category": "news", "description": "Pessoas buscam bem-estar e espiritualidade no Vale Místico."},
        {"title": "Pousadas de Abadiânia ganham prêmio de hospitalidade", "category": "business", "description": "Turismo interno reconhece qualidade de atendimento."},
        {"title": "Abadiânia investe em preservação ambiental", "category": "environment", "description": "Projeto protege nascentes de água da região."},
        {"title": "Encontro anual de terapeutas atrai 5 mil pessoas", "category": "events", "description": "Evento consolida Abadiânia como centro de práticas integrativas."},
    ],
}

# Eventos por cidade
EVENTOS_POR_CIDADE = {
    "Macapá": [
        {"title": "Festival de Música Amazônica", "date": "2026-07-15", "time": "20:00", "location": "Praça da Matriz", "description": "Shows de artistas regionais e nacionais."},
        {"title": "Encontro de Povos Indígenas", "date": "2026-08-10", "time": "09:00", "location": "Centro Cultural", "description": "Celebração das tradições indígenas da Amazônia."},
        {"title": "Maratona de Macapá", "date": "2026-09-01", "time": "06:00", "location": "Avenida Edmundo Barbosa", "description": "Corrida com 5km e 10km."},
        {"title": "Feira do Açaí", "date": "2026-09-20", "time": "08:00", "location": "Mercado Flutuante", "description": "Degustação de produtos derivados do açaí."},
        {"title": "Workshop de Artesanato Local", "date": "2026-10-05", "time": "14:00", "location": "Casa da Cultura", "description": "Aprenda técnicas tradicionais com mestres locais."},
    ],
    "Belém": [
        {"title": "Romaria da Basílica de Nazaré", "date": "2026-10-08", "time": "06:00", "location": "Basílica de Nazaré", "description": "Celebração religiosa com procissão e missa."},
        {"title": "Mostra de Cinema Amazônico", "date": "2026-07-20", "time": "18:00", "location": "Cine Líbero", "description": "Documentários e filmes sobre a região."},
        {"title": "Festa do Açaí", "date": "2026-08-15", "time": "17:00", "location": "Mercado Ver-o-Peso", "description": "Degustação e competição de receitas."},
        {"title": "Passeio Gastronômico em Belém", "date": "2026-09-10", "time": "19:00", "location": "Centro Histórico", "description": "Tour por restaurantes tradicionais paraenses."},
        {"title": "Encontro de Lendas Amazônicas", "date": "2026-10-30", "time": "20:00", "location": "Teatro da Paz", "description": "Contação de histórias sobre mitologia amazônica."},
    ],
    "Rio de Janeiro": [
        {"title": "Carnaval Rio 2025", "date": "2025-03-04", "time": "20:00", "location": "Sambodrome", "description": "Maior carnaval do mundo."},
        {"title": "Festival de Surf do Rio", "date": "2026-07-01", "time": "08:00", "location": "Praia de Arpoador", "description": "Competição internacional de surfe."},
        {"title": "Cinema no Forte", "date": "2026-08-15", "time": "19:30", "location": "Forte de Copacabana", "description": "Sessão de cinema ao ar livre."},
        {"title": "Festa da Cidade do Rio", "date": "2026-11-20", "time": "10:00", "location": "Parque Lage", "description": "Celebração do aniversário da cidade."},
        {"title": "Festival de Jazz do Rio", "date": "2026-09-05", "time": "18:00", "location": "Centro Cultural", "description": "Apresentações de artistas internacionais."},
    ],
    "São Paulo": [
        {"title": "Festa da Primavera SP", "date": "2026-09-21", "time": "09:00", "location": "Ibirapuera", "description": "Celebração da estação com atividades culturais."},
        {"title": "São Paulo Fashion Week", "date": "2026-11-01", "time": "14:00", "location": "Pavilhão da Bienal", "description": "Maior semana de moda da América Latina."},
        {"title": "Virada Cultural SP", "date": "2026-05-16", "time": "18:00", "location": "Diversos locais", "description": "24 horas de arte, música e cultura."},
        {"title": "Marathon de São Paulo", "date": "2026-08-02", "time": "07:00", "location": "Av. Paulista", "description": "Corrida com 42km."},
        {"title": "Festival de Cinema de SP", "date": "2026-10-15", "time": "19:00", "location": "Espaço Itaú", "description": "Mostra de filmes nacionais e internacionais."},
    ],
    "Brasília": [
        {"title": "Aniversário de Brasília", "date": "2026-04-21", "time": "10:00", "location": "Esplanada", "description": "Celebração da capital com shows e eventos."},
        {"title": "Semana do Meio Ambiente", "date": "2026-06-05", "time": "08:00", "location": "Catedral", "description": "Atividades sobre sustentabilidade."},
        {"title": "Festival de Música Clássica", "date": "2026-07-10", "time": "20:00", "location": "Auditório Nacional", "description": "Orquestras apresentam clássicos."},
        {"title": "Passeio Cicloturístico", "date": "2026-08-22", "time": "07:00", "location": "Esplanada", "description": "Pedalada em grupo pela cidade."},
        {"title": "Congresso Nacional em Aberto", "date": "2026-09-15", "time": "09:00", "location": "Congresso", "description": "Visitação especial ao prédio histórico."},
    ],
    "Campina Grande": [
        {"title": "São João de Campina Grande", "date": "2026-06-23", "time": "19:00", "location": "Parque da Açude", "description": "Maior festa junina da Paraíba."},
        {"title": "Festa da Rainha da Borborema", "date": "2026-07-15", "time": "18:00", "location": "Praça da Bandeira", "description": "Celebração da identidade local."},
        {"title": "Competição de Quadrilhas", "date": "2026-06-28", "time": "20:00", "location": "Estádio Presidente Varela", "description": "Disputa das melhores quadrilhas."},
        {"title": "Tour pela Campina Histórica", "date": "2026-08-10", "time": "09:00", "location": "Centro", "description": "Passeio guiado pela história da cidade."},
        {"title": "Show de Forró", "date": "2026-09-05", "time": "21:00", "location": "Parque da Açude", "description": "Apresentação de bandas tradicionais."},
    ],
    "Abadiânia": [
        {"title": "Encontro de Terapeutas Holísticos", "date": "2026-07-01", "time": "09:00", "location": "Vale da Lua", "description": "3 dias de workshops e meditação."},
        {"title": "Passeio ao Vale da Lua", "date": "2026-08-15", "time": "08:00", "location": "Vale Místico", "description": "Trilha e banho nas piscinas naturais."},
        {"title": "Sessão de Cristais e Energia", "date": "2026-09-10", "time": "19:00", "location": "Centro Espiritual", "description": "Experiência de cura com cristais."},
        {"title": "Retiro de Yoga e Meditação", "date": "2026-10-05", "time": "06:00", "location": "Pousada Serrana", "description": "7 dias de práticas integrativas."},
        {"title": "Festa de Integração Comunitária", "date": "2026-11-20", "time": "17:00", "location": "Praça Central", "description": "Encontro entre turistas e moradores."},
    ],
}

def seed_news_events():
    # Criar tabelas se não existirem
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        print("[INFO] Verificando se já há notícias e eventos...")
        existing_news = db.query(LocalNews).count()
        existing_events = db.query(LocalEvent).count()

        if existing_news > 0 or existing_events > 0:
            print(f"[OK] Banco já tem {existing_news} notícias e {existing_events} eventos. Pulando seed.")
            db.close()
            return

        print("[INFO] Adicionando notícias e eventos...")

        # Adicionar notícias
        for city_name, noticias in NOTICIAS_POR_CIDADE.items():
            for noticia in noticias:
                # Variar data entre os últimos 30 dias
                days_ago = random.randint(0, 30)
                news_obj = LocalNews(
                    city=city_name,
                    title=noticia["title"],
                    content=noticia["description"],
                    category=noticia["category"],
                    source="Local News",
                    published_at=datetime.utcnow() - timedelta(days=days_ago),
                    created_at=datetime.utcnow() - timedelta(days=days_ago),
                )
                db.add(news_obj)

        db.commit()
        print(f"[OK] Notícias adicionadas!")

        # Adicionar eventos
        # Usar um admin user para created_by_id (vamos usar 1 como padrão)
        for city_name, eventos in EVENTOS_POR_CIDADE.items():
            for evento in eventos:
                event_obj = LocalEvent(
                    city=city_name,
                    title=evento["title"],
                    description=evento["description"],
                    date=evento["date"],  # String no formato YYYY-MM-DD
                    time=evento["time"],
                    location=evento["location"],
                    created_by_id=1,  # Admin user
                    status="active",
                    created_at=datetime.utcnow(),
                )
                db.add(event_obj)

        db.commit()
        print(f"[OK] Eventos adicionados!")

        print("\n[SUCCESS] Seed completo!")
        total_news = db.query(LocalNews).count()
        total_events = db.query(LocalEvent).count()
        print(f"Total de notícias: {total_news}")
        print(f"Total de eventos: {total_events}")

    except Exception as e:
        print(f"[ERROR] Erro: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_news_events()
