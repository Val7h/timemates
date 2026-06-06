"""
Script de deployment - Popular database com dados de teste
Execute: python seed_deployment_data.py

Este script popula:
- 27 cidades brasileiras (capitais)
- Notícias por cidade (5 por cidade selecionada)
- Eventos por cidade (3 por cidade selecionada)
- Dicas locais (3 por cidade selecionada)
- Desafios (3 por cidade selecionada)
- POIs (4 por cidade selecionada)
- Badges (3 por cidade selecionada)
"""

from datetime import datetime, timedelta
from database import (
    SessionLocal, Base, engine,
    City, CityNews, CityEvent, LocalTip, CityChallenge, LocalPOI, CityBadge
)
from sqlalchemy import text
import random
import json

# Capitais brasileiras (27)
CAPITAIS_BRASILEIRAS = [
    {"slug": "macapa", "name": "Macapá", "state": "AP", "population": 512902, "landmark": "Forte de São José de Macapá"},
    {"slug": "porto-velho", "name": "Porto Velho", "state": "RO", "population": 539205, "landmark": "Estação Férrea Madeira-Mamoré"},
    {"slug": "boa-vista", "name": "Boa Vista", "state": "RR", "population": 330120, "landmark": "Catedral de Boa Vista"},
    {"slug": "manaus", "name": "Manaus", "state": "AM", "population": 1802014, "landmark": "Teatro Amazonas"},
    {"slug": "belem", "name": "Belém", "state": "PA", "population": 1506476, "landmark": "Basílica de Nazaré"},
    {"slug": "palmas", "name": "Palmas", "state": "TO", "population": 305296, "landmark": "Praia da Graciosa"},
    {"slug": "sao-luis", "name": "São Luís", "state": "MA", "population": 1108975, "landmark": "Centro Histórico"},
    {"slug": "teresina", "name": "Teresina", "state": "PI", "population": 866383, "landmark": "Ponte Getúlio Vargas"},
    {"slug": "fortaleza", "name": "Fortaleza", "state": "CE", "population": 2669342, "landmark": "Praia de Iracema"},
    {"slug": "natal", "name": "Natal", "state": "RN", "population": 885180, "landmark": "Ponte Newton Navarro"},
    {"slug": "joao-pessoa", "name": "João Pessoa", "state": "PB", "population": 809051, "landmark": "Farol do Cabo Branco"},
    {"slug": "recife", "name": "Recife", "state": "PE", "population": 1645727, "landmark": "Ponte Maurício de Nassau"},
    {"slug": "maceio", "name": "Maceió", "state": "AL", "population": 1025360, "landmark": "Praia de Ponta Verde"},
    {"slug": "salvador", "name": "Salvador", "state": "BA", "population": 2595140, "landmark": "Pelourinho"},
    {"slug": "brasilia", "name": "Brasília", "state": "DF", "population": 3124186, "landmark": "Catedral Metropolitana"},
    {"slug": "goiania", "name": "Goiânia", "state": "GO", "population": 1536097, "landmark": "Praça Cívica"},
    {"slug": "cuiaba", "name": "Cuiabá", "state": "MT", "population": 612547, "landmark": "Basílica do Senhor Bom Jesus"},
    {"slug": "campo-grande", "name": "Campo Grande", "state": "MS", "population": 889975, "landmark": "Avenida Afonso Pena"},
    {"slug": "sao-paulo", "name": "São Paulo", "state": "SP", "population": 11975881, "landmark": "MASP"},
    {"slug": "rio-de-janeiro", "name": "Rio de Janeiro", "state": "RJ", "population": 6775561, "landmark": "Cristo Redentor"},
    {"slug": "vitoria", "name": "Vitória", "state": "ES", "population": 365855, "landmark": "Convento da Penha"},
    {"slug": "belo-horizonte", "name": "Belo Horizonte", "state": "MG", "population": 2530701, "landmark": "Praça da Liberdade"},
    {"slug": "curitiba", "name": "Curitiba", "state": "PR", "population": 1963726, "landmark": "Ópera de Arame"},
    {"slug": "florianopolis", "name": "Florianópolis", "state": "SC", "population": 507178, "landmark": "Lagoa da Conceição"},
    {"slug": "porto-alegre", "name": "Porto Alegre", "state": "RS", "population": 1440939, "landmark": "Guaíba"},
    {"slug": "campina-grande", "name": "Campina Grande", "state": "PB", "population": 410332, "landmark": "Açude Epitácio Pessoa"},
]

# Seed data organizado por cidade
SEED_DATA = {
    "rio-de-janeiro": {
        "news": [
            {"title": "Cristo Redentor recebe 2 milhões de visitantes", "content": "O monumento icônico do Rio recebe número recorde de visitantes em 2026...", "source": "O Globo"},
            {"title": "Rock in Rio 2026 anuncia lineup imperdível", "content": "Festival de música mais esperado do ano já tem datas confirmadas...", "source": "Globo.com"},
            {"title": "Praia de Copacabana com melhor qualidade de água", "content": "Programa de despoluição mostra resultados positivos...", "source": "Extra"},
            {"title": "Maracanã recebe novo projeto de revitalização", "content": "Estádio emblemático passa por modernização completa...", "source": "G1"},
            {"title": "Parque Lage reabre com novas exposições", "content": "Espaço cultural oferece programação renovada...", "source": "UOL"},
        ],
        "events": [
            {"title": "Show de Samba no Morro da Mangueira", "description": "Apresentação das alas da escola para temporada carnavalesca", "location": "Morro da Mangueira", "category": "cultural", "date_offset": 10},
            {"title": "Maratona do Rio 2026", "description": "Corrida de 42km pelas principais atrações da cidade", "location": "Avenida Atlântica", "category": "esporte", "date_offset": 15},
            {"title": "Festival de Gastronomia no Porto Maravilha", "description": "Chefs renomados apresentam pratos da culinária carioca", "location": "Porto Maravilha", "category": "gastronomia", "date_offset": 20},
        ],
        "tips": [
            {"title": "Melhor pão de queijo da Zona Sul", "description": "Padaria com 30 anos, faz pão de queijo todos os dias", "location": "Padaria da Vovó", "category": "cafe", "rating": 4.8},
            {"title": "Trilha escondida para Pedra da Gávea", "description": "Trilha alternativa menos conhecida com vista incrível", "location": "Pedra da Gávea", "category": "parque", "rating": 4.9},
            {"title": "Restaurante de comida caseira carioca", "description": "Tem bobó de camarão que é de morrer, feito pela dona", "location": "Casa da Tia Maria", "category": "restaurante", "rating": 4.7},
        ],
        "challenges": [
            {"title": "Tire Foto no Cristo Redentor", "description": "Visite o monumento mais icônico do Rio", "instructions": "Suba até o Cristo Redentor e tire uma selfie criativa", "difficulty": "facil", "points": 50},
            {"title": "Mergulhe em Copacabana ao Amanhecer", "description": "Nada na praia mais famosa do Rio no nascer do sol", "instructions": "Entre na água antes das 6h30 e tire uma foto", "difficulty": "medio", "points": 100},
            {"title": "Trilha Pedra da Gávea Completa", "description": "Complete a trilha mais desafiadora do Rio", "instructions": "Suba até o topo e envie foto com vista", "difficulty": "dificil", "points": 200},
        ],
        "pois": [
            {"name": "Cristo Redentor", "category": "landmark", "lat": -22.9519, "lng": -43.2105, "address": "Estrada da Corcovada, Rio de Janeiro - RJ", "description": "Monumento icônico do Rio e patrimônio da humanidade", "rating": 4.9, "photos": 5000},
            {"name": "Praia de Copacabana", "category": "beach", "lat": -22.9829, "lng": -43.1925, "address": "Av. Atlântica, Rio de Janeiro - RJ", "description": "Praia mais famosa do Rio com 4km de extensão", "rating": 4.7, "photos": 8000},
            {"name": "Museu de Arte Moderna", "category": "museum", "lat": -22.9063, "lng": -43.1650, "address": "Avenida Infante Dom Henrique 85", "description": "Importante museu de arte moderna brasileira", "rating": 4.6, "photos": 1200},
            {"name": "Pão de Açúcar", "category": "landmark", "lat": -22.9432, "lng": -43.1614, "address": "Avenida Pasteur, 520 - Praia Vermelha", "description": "Um dos cartões postais do Rio com teleférico", "rating": 4.8, "photos": 6000},
        ],
        "badges": [
            {"badge_name": "Explorador do Rio", "description": "Visitou 5 pontos de interesse diferentes no Rio", "criteria": {"pois_visited": 5}},
            {"badge_name": "Foodie Carioca", "description": "Submeteu 5 dicas de restaurantes", "criteria": {"tips_submitted": 5}},
            {"badge_name": "Aventureiro do Cristo", "description": "Concluiu o desafio do Cristo Redentor", "criteria": {"challenges_completed": 1}},
        ]
    },
    "sao-paulo": {
        "news": [
            {"title": "Museu do Ipiranga reabre com nova instalação", "content": "Reforma de 3 anos transforma museu histórico em espaço moderno...", "source": "Folha de S.Paulo"},
            {"title": "Avenida Paulista registra recorde de eventos culturais", "content": "Programação mensal com shows, teatro e exposições...", "source": "G1 SP"},
            {"title": "MASP celebra 70 anos de história", "content": "Museu de Arte de São Paulo inaugura nova ala...", "source": "UOL"},
            {"title": "Vila Mariana em transformação cultural", "content": "Novos espaços de arte e cultura abrem na região...", "source": "Folha"},
            {"title": "Ibirapuera recebe novo centro de inovação", "content": "Parque se consolida como polo cultural...", "source": "G1"},
        ],
        "events": [
            {"title": "SPFW - São Paulo Fashion Week", "description": "Maior evento de moda do Brasil", "location": "Ibirapuera", "category": "cultural", "date_offset": 25},
            {"title": "Virada Cultural SP", "description": "24h de cultura, arte e música gratuita", "location": "Diversos pontos da cidade", "category": "cultural", "date_offset": 45},
            {"title": "Festival de Tecnologia e Inovação", "description": "Encontro de startups e tecnologia", "location": "SESC Pompéia", "category": "cultural", "date_offset": 32},
        ],
        "tips": [
            {"title": "Biblioteca Viva do Bom Retiro", "description": "Espaço público com 20 mil livros, ambiente acolhedor", "location": "Bom Retiro", "category": "museu", "rating": 4.6},
            {"title": "Boteco tradicional da Vila Madalena", "description": "Chopp gelado e porções generosas, frequentado por artistas", "location": "Vila Madalena", "category": "bar", "rating": 4.5},
            {"title": "Padaria francesa escondida na Consolação", "description": "Pão francês fresquinho todo dia", "location": "Consolação", "category": "cafe", "rating": 4.8},
        ],
        "challenges": [
            {"title": "Visite o MASP em 1 Hora", "description": "Conheça o Museu de Arte de São Paulo", "instructions": "Entre no MASP e tire foto com o prédio icônico", "difficulty": "facil", "points": 50},
            {"title": "Grafite na Vila Madalena", "description": "Encontre e fotografe 5 murais diferentes", "instructions": "Tire fotos de murais e compartilhe locations", "difficulty": "medio", "points": 100},
            {"title": "Explore Ibirapuera Completamente", "description": "Visite todos os museus do parque", "instructions": "Tire fotos em cada museu", "difficulty": "dificil", "points": 200},
        ],
        "pois": [
            {"name": "Museu do Ipiranga", "category": "museum", "lat": -23.5955, "lng": -46.6181, "address": "Avenida Nazaré, 1000", "description": "Museu da independência com historia do Brasil", "rating": 4.7, "photos": 3000},
            {"name": "Parque Ibirapuera", "category": "park", "lat": -23.5897, "lng": -46.6580, "address": "Av. Pedro Álvares Cabral, S/N", "description": "Maior parque urbano de SP com museus e lagos", "rating": 4.8, "photos": 10000},
            {"name": "MASP - Museu de Arte de São Paulo", "category": "museum", "lat": -23.5619, "lng": -46.6560, "address": "Avenida Paulista, 1578", "description": "Importante acervo de arte europeia e brasileira", "rating": 4.6, "photos": 5000},
            {"name": "Vila Madalena", "category": "neighborhood", "lat": -23.5585, "lng": -46.6808, "address": "Vila Madalena, São Paulo", "description": "Bairro boêmio com arte de rua e vida noturna", "rating": 4.7, "photos": 4000},
        ],
        "badges": [
            {"badge_name": "Amante da Arte SP", "description": "Visitou todos os 3 museus principais de SP", "criteria": {"museums_visited": 3}},
            {"badge_name": "Paulista Expert", "description": "Submeteu 10 dicas sobre São Paulo", "criteria": {"tips_submitted": 10}},
            {"badge_name": "Explorador de Parques", "description": "Visitou 5 parques diferentes em SP", "criteria": {"parks_visited": 5}},
        ]
    },
    "belo-horizonte": {
        "news": [
            {"title": "Lagoa da Pampulha desperta interesse turístico", "content": "Projeto de revitalização traz novos bares e restaurantes à região...", "source": "Estado de Minas"},
            {"title": "Circuito da Liberdade recebe nova sinalização", "content": "Melhoria de acessibilidade em principais pontos turísticos...", "source": "G1 Minas"},
            {"title": "Belo Horizonte entre top 10 cidades mais limpas do Brasil", "content": "Programa de sustentabilidade mostra resultados...", "source": "UOL"},
            {"title": "Novo complexo cultural na região central", "content": "Centro da cidade ganha atração para turistas...", "source": "Estado de Minas"},
            {"title": "Praça da Liberdade comemora restauração", "content": "Histórico cartão postal recebe novo aporte...", "source": "G1"},
        ],
        "events": [
            {"title": "Festival de Jazz da Lagoa", "description": "Apresentações de artistas locais e internacionais", "location": "Lagoa da Pampulha", "category": "cultural", "date_offset": 30},
            {"title": "Festa de Comida Mineira", "description": "Celebração da gastronomia típica de Minas", "location": "Parque Municipal", "category": "gastronomia", "date_offset": 35},
            {"title": "Trilha da Serra do Curral", "description": "Caminhada ecológica com vista panorâmica", "location": "Serra do Curral", "category": "esporte", "date_offset": 28},
        ],
        "tips": [
            {"title": "Mercado Central - Compre produtos frescos", "description": "Tradição de BH desde 1929, frutas, queijos, pão", "location": "Mercado Central", "category": "shop", "rating": 4.8},
            {"title": "Pão de Queijo Mineiro Autêntico", "description": "Lugar com receita centenária de pão de queijo", "location": "Centro", "category": "cafe", "rating": 4.9},
            {"title": "Restaurante de Comida Mineira Tradicional", "description": "Feijão tropeiro, broa e muito mais", "location": "Praça da Liberdade", "category": "restaurante", "rating": 4.7},
        ],
        "challenges": [
            {"title": "Foto na Lagoa da Pampulha", "description": "Tire uma foto bonita na vista mais linda de BH", "instructions": "Vá ao parque e capture o pôr do sol", "difficulty": "facil", "points": 50},
            {"title": "Conheça os 5 Museus da Pampulha", "description": "Visite o complexo cultural completo", "instructions": "Tire fotos em cada museu", "difficulty": "medio", "points": 100},
            {"title": "Suba a Serra do Curral", "description": "Complete a trilha com vista panorâmica", "instructions": "Chegue ao topo e tire foto", "difficulty": "dificil", "points": 150},
        ],
        "pois": [
            {"name": "Lagoa da Pampulha", "category": "park", "lat": -19.9217, "lng": -43.9711, "address": "Av. Otacílio Neves", "description": "Lago artificial com complexo cultural", "rating": 4.7, "photos": 4000},
            {"name": "Museu de Arte Moderna de Belo Horizonte", "category": "museum", "lat": -19.9166, "lng": -43.9729, "address": "Av. Afonso Pena, 1687", "description": "Acervo de arte moderna brasileira", "rating": 4.5, "photos": 1500},
            {"name": "Praça da Liberdade", "category": "landmark", "lat": -19.9289, "lng": -43.9400, "address": "Praça da Liberdade, Belo Horizonte", "description": "Coração histórico de Belo Horizonte", "rating": 4.6, "photos": 3000},
            {"name": "Serra do Curral", "category": "park", "lat": -19.9350, "lng": -43.8900, "address": "Serra do Curral, Belo Horizonte", "description": "Trilha com vista panorâmica da cidade", "rating": 4.8, "photos": 2500},
        ],
        "badges": [
            {"badge_name": "Amigo de BH", "description": "Visitou a Lagoa da Pampulha", "criteria": {"pampulha_visited": True}},
            {"badge_name": "Gourmet Mineiro", "description": "Descobriu 5 restaurantes tradicionais", "criteria": {"restaurants_discovered": 5}},
            {"badge_name": "Explorador de Trilhas", "description": "Completou 3 trilhas diferentes", "criteria": {"trails_completed": 3}},
        ]
    },
    "salvador": {
        "news": [
            {"title": "Carnaval de Salvador 2027 já movimenta economia", "content": "Pousadas lotadas com meses de antecedência...", "source": "Correio da Bahia"},
            {"title": "Pelourinho recebe novo projeto de restauro", "content": "Patrimônio histórico passa por renovação completa...", "source": "G1 Bahia"},
            {"title": "Festa de Iemanjá atrai turistas de todo Brasil", "content": "Celebração tradicional continua a atrair multidões...", "source": "UOL"},
            {"title": "Museu de Arte Sagrada abre novas alas", "content": "Instituição cultural marca presença renovada...", "source": "Bahia Notícias"},
            {"title": "Praia de Farol da Barra com melhor infraestrutura", "content": "Investimentos em turismo costeiro continuam...", "source": "G1"},
        ],
        "events": [
            {"title": "Festa de Iemanjá", "description": "Celebração tradicional da Rainha do Mar", "location": "Praia do Rio Vermelho", "category": "cultural", "date_offset": 60},
            {"title": "Carnaval de Salvador", "description": "Maior festa de rua do Brasil", "location": "Centro Histórico", "category": "cultural", "date_offset": 90},
            {"title": "Festival de Culinária Baiana", "description": "Sabores tradicionais e inovadores", "location": "Mercado Modelo", "category": "gastronomia", "date_offset": 40},
        ],
        "tips": [
            {"title": "Acarajé Autêntico do Pelourinho", "description": "Receita centenária feita na hora", "location": "Pelourinho", "category": "comida", "rating": 4.9},
            {"title": "Mirante do Farol da Barra", "description": "Melhor vista do pôr do sol em Salvador", "location": "Farol da Barra", "category": "parque", "rating": 4.8},
            {"title": "Moqueca de Peixe Tradicional", "description": "Restaurante com receita passada por gerações", "location": "Centro Histórico", "category": "restaurante", "rating": 4.7},
        ],
        "challenges": [
            {"title": "Explore o Pelourinho", "description": "Tire foto em cada rua histórica", "instructions": "Visite 5 ruas diferentes", "difficulty": "facil", "points": 75},
            {"title": "Celebre Iemanjá", "description": "Participe da festa traditionnal", "instructions": "Leve uma oferta à praia", "difficulty": "medio", "points": 125},
            {"title": "Mestre Carnavalesco", "description": "Estude história do Carnaval baiano", "instructions": "Visite 3 museus carnavalescos", "difficulty": "dificil", "points": 200},
        ],
        "pois": [
            {"name": "Pelourinho", "category": "landmark", "lat": -12.9719, "lng": -38.5140, "address": "Centro Histórico, Salvador", "description": "Centro histórico com arquitetura colonial", "rating": 4.9, "photos": 7000},
            {"name": "Farol da Barra", "category": "beach", "lat": -13.0017, "lng": -38.3306, "address": "Praia do Farol da Barra", "description": "Praia com museu do farol", "rating": 4.8, "photos": 5000},
            {"name": "Mercado Modelo", "category": "market", "lat": -12.9747, "lng": -38.5114, "address": "Av. Contorno, Salvador", "description": "Mercado tradicional com artesanato", "rating": 4.6, "photos": 3000},
            {"name": "Museu de Arte Sagrada", "category": "museum", "lat": -12.9719, "lng": -38.5140, "address": "Rua Inácio Accioli", "description": "Acervo de arte religiosa", "rating": 4.5, "photos": 1200},
        ],
        "badges": [
            {"badge_name": "Baiano Raiz", "description": "Visitou o Pelourinho", "criteria": {"pelourinho_visited": True}},
            {"badge_name": "Devoto de Iemanjá", "description": "Participou da festa de Iemanjá", "criteria": {"iemanja_participated": True}},
            {"badge_name": "Carnavalesco", "description": "Explorou história do Carnaval", "criteria": {"carnival_history": True}},
        ]
    },
    "fortaleza": {
        "news": [
            {"title": "Praia do Futuro recebe novo complexo gastronômico", "content": "Investimento de R$ 50 milhões em infraestrutura turística...", "source": "Diário do Nordeste"},
            {"title": "Centro de Fortaleza passa por revitalização", "content": "Projeto de requalificação urbana está em fase avançada...", "source": "G1 Ceará"},
            {"title": "Fortaleza entre os destinos preferidos do Brasil", "content": "Turismo cresce 25% em comparação ao ano anterior...", "source": "UOL"},
            {"title": "Ateliês de artesanato ganham novo espaço", "content": "Artistas locais recebem apoio para expansão...", "source": "Tribuna do Ceará"},
            {"title": "Praia de Iracema recebe nova vida gastronômica", "content": "Restaurantes de alta gastronomia chegam à região...", "source": "G1"),
        ],
        "events": [
            {"title": "Regata da Praia do Futuro", "description": "Competição de vela tradicional", "location": "Praia do Futuro", "category": "esporte", "date_offset": 35},
            {"title": "Festival de Gastronomia Nordestina", "description": "Sabores típicos do sertão e da costa", "location": "Praia de Iracema", "category": "gastronomia", "date_offset": 42},
            {"title": "Show de Forró Tradicional", "description": "Música típica do Nordeste", "location": "Centro Histórico", "category": "cultural", "date_offset": 38},
        ],
        "tips": [
            {"title": "Camarão Fresco na Praia do Futuro", "description": "Barracas com camarão trazido na hora", "location": "Praia do Futuro", "category": "restaurante", "rating": 4.9},
            {"title": "Artesanato Cearense Autêntico", "description": "Loja com peças exclusivas de artesãos locais", "location": "Centro", "category": "shop", "rating": 4.7},
            {"title": "Água de Coco Verde Gelada", "description": "Lugar onde vendem a melhor água de coco", "location": "Praia de Iracema", "category": "cafe", "rating": 4.8},
        ],
        "challenges": [
            {"title": "Banhe-se em Iracema", "description": "Nade na praia mais famosa de Fortaleza", "instructions": "Entre na água e tire selfie", "difficulty": "facil", "points": 50},
            {"title": "Prove Comida Nordestina Autêntica", "description": "Coma em 3 restaurantes diferentes", "instructions": "Tire foto da comida", "difficulty": "medio", "points": 100},
            {"title": "Explore a Costa do Futuro", "description": "Visite 5 praias diferentes", "instructions": "Cole fotos em cada uma", "difficulty": "dificil", "points": 175},
        ],
        "pois": [
            {"name": "Praia de Iracema", "category": "beach", "lat": -3.7319, "lng": -38.5240, "address": "Av. Beira Mar, Fortaleza", "description": "Praia urbana famosa de Fortaleza", "rating": 4.8, "photos": 6000},
            {"name": "Praia do Futuro", "category": "beach", "lat": -3.7700, "lng": -38.4300, "address": "Av. Zezé Diogo, Fortaleza", "description": "Praia com infraestrutura turística", "rating": 4.7, "photos": 5500},
            {"name": "Centro Cultural Dragão do Mar", "category": "museum", "lat": -3.7325, "lng": -38.5245, "address": "Rua Dragão do Mar", "description": "Espaço cultural em Fortaleza", "rating": 4.6, "photos": 2000},
            {"name": "Mercado dos Mariscos", "category": "market", "lat": -3.7270, "lng": -38.5180, "address": "Av. Beira Mar", "description": "Mercado com frutos do mar frescos", "rating": 4.7, "photos": 1800},
        ],
        "badges": [
            {"badge_name": "Praiano", "description": "Visitou 3 praias em Fortaleza", "criteria": {"beaches_visited": 3}},
            {"badge_name": "Mestre do Forró", "description": "Dançou forró tradicional", "criteria": {"forro_danced": True}},
            {"badge_name": "Faminto de Nordeste", "description": "Experimentou 5 pratos típicos", "criteria": {"typical_dishes": 5}},
        ]
    },
}


def seed_cities(db):
    """Popula as 27 cidades brasileiras."""
    print("\n[1/7] Populando 27 cidades brasileiras...")

    for cap in CAPITAIS_BRASILEIRAS:
        existing = db.query(City).filter(City.slug == cap["slug"]).first()
        if not existing:
            # Gera coordenadas pseudo-aleatórias baseadas no slug
            lat = -10.0 + (hash(cap["slug"]) % 3000) / 100
            lng = -50.0 + (hash(cap["slug"]) % 2000) / 100

            city = City(
                slug=cap["slug"],
                name=cap["name"],
                state=cap["state"],
                population=cap["population"],
                landmark_image=f"https://via.placeholder.com/300x200?text={cap['landmark']}",
                coordinates={"latitude": lat, "longitude": lng}
            )
            db.add(city)

    db.commit()
    print(f"✓ {len(CAPITAIS_BRASILEIRAS)} cidades adicionadas")


def seed_news(db):
    """Popula notícias para cidades selecionadas."""
    print("[2/7] Populando notícias...")

    count = 0
    for slug, data in SEED_DATA.items():
        city = db.query(City).filter(City.slug == slug).first()
        if city and "news" in data:
            for news_item in data["news"]:
                new_news = CityNews(
                    city_id=city.id,
                    title=news_item["title"],
                    content=news_item["content"],
                    source=news_item["source"],
                    published_at=datetime.utcnow() - timedelta(days=random.randint(0, 7)),
                    views=random.randint(100, 5000),
                    engagement_count=random.randint(10, 500)
                )
                db.add(new_news)
                count += 1

    db.commit()
    print(f"✓ {count} notícias adicionadas")


def seed_events(db):
    """Popula eventos para cidades selecionadas."""
    print("[3/7] Populando eventos...")

    count = 0
    for slug, data in SEED_DATA.items():
        city = db.query(City).filter(City.slug == slug).first()
        if city and "events" in data:
            for event_item in data["events"]:
                new_event = CityEvent(
                    city_id=city.id,
                    title=event_item["title"],
                    description=event_item["description"],
                    location=event_item["location"],
                    category=event_item["category"],
                    date=datetime.utcnow() + timedelta(days=event_item["date_offset"]),
                    end_date=datetime.utcnow() + timedelta(days=event_item["date_offset"] + 1),
                    attendees=random.randint(100, 10000)
                )
                db.add(new_event)
                count += 1

    db.commit()
    print(f"✓ {count} eventos adicionados")


def seed_tips(db):
    """Popula dicas locais para cidades selecionadas."""
    print("[4/7] Populando dicas locais...")

    # Criar usuário de teste se não existir
    from database import User
    test_user = db.query(User).filter(User.email == "seed@example.com").first()
    if not test_user:
        from auth import hash_password
        test_user = User(
            full_name="Seed User",
            email="seed@example.com",
            password_hash=hash_password("password123"),
            cpf_hash="00000000000",
            is_active=True
        )
        db.add(test_user)
        db.commit()

    count = 0
    for slug, data in SEED_DATA.items():
        city = db.query(City).filter(City.slug == slug).first()
        if city and "tips" in data:
            for tip_item in data["tips"]:
                new_tip = LocalTip(
                    city_id=city.id,
                    user_id=test_user.id,
                    title=tip_item["title"],
                    description=tip_item["description"],
                    location=tip_item["location"],
                    rating=tip_item.get("rating", 4.5)
                )
                db.add(new_tip)
                count += 1

    db.commit()
    print(f"✓ {count} dicas locais adicionadas")


def seed_challenges(db):
    """Popula desafios para cidades selecionadas."""
    print("[5/7] Populando desafios...")

    count = 0
    for slug, data in SEED_DATA.items():
        city = db.query(City).filter(City.slug == slug).first()
        if city and "challenges" in data:
            for challenge_item in data["challenges"]:
                new_challenge = CityChallenge(
                    city_id=city.id,
                    title=challenge_item["title"],
                    description=challenge_item["description"],
                    reward_points=challenge_item["points"],
                    difficulty=challenge_item["difficulty"],
                    active=True
                )
                db.add(new_challenge)
                count += 1

    db.commit()
    print(f"✓ {count} desafios adicionados")


def seed_pois(db):
    """Popula POIs (Pontos de Interesse) para cidades selecionadas."""
    print("[6/7] Populando POIs (Pontos de Interesse)...")

    count = 0
    for slug, data in SEED_DATA.items():
        city = db.query(City).filter(City.slug == slug).first()
        if city and "pois" in data:
            for poi_item in data["pois"]:
                new_poi = LocalPOI(
                    city_id=city.id,
                    name=poi_item["name"],
                    type=poi_item["category"],
                    latitude=poi_item["lat"],
                    longitude=poi_item["lng"]
                )
                db.add(new_poi)
                count += 1

    db.commit()
    print(f"✓ {count} POIs adicionados")


def seed_badges(db):
    """Popula badges para cidades selecionadas."""
    print("[7/7] Populando badges...")

    # Usar o mesmo usuário de teste
    test_user = db.query(User).filter(User.email == "seed@example.com").first()
    if not test_user:
        return

    count = 0
    for slug, data in SEED_DATA.items():
        city = db.query(City).filter(City.slug == slug).first()
        if city and "badges" in data:
            for badge_item in data["badges"]:
                new_badge = CityBadge(
                    user_id=test_user.id,
                    city_id=city.id,
                    badge_type=badge_item["badge_name"].lower().replace(" ", "_"),
                )
                db.add(new_badge)
                count += 1

    db.commit()
    print(f"✓ {count} badges adicionados")


def main():
    print("\n" + "="*70)
    print("  DEPLOYMENT - POPULANDO DATABASE COM DADOS DE TESTE")
    print("="*70)

    # Criar tabelas se não existirem
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # Executar todos os seeds
        seed_cities(db)
        seed_news(db)
        seed_events(db)
        seed_tips(db)
        seed_challenges(db)
        seed_pois(db)
        seed_badges(db)

        print("\n" + "="*70)
        print("  ✓ DATABASE POPULADO COM SUCESSO!")
        print("="*70)
        print("\nDados adicionados:")
        print(f"  - 27 cidades brasileiras")
        print(f"  - Notícias por cidade")
        print(f"  - Eventos por cidade")
        print(f"  - Dicas locais por cidade")
        print(f"  - Desafios por cidade")
        print(f"  - POIs por cidade")
        print(f"  - Badges de usuário")
        print("\n")

    except Exception as e:
        print(f"\n✗ Erro ao popular database: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
