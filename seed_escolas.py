"""
Seed - Escolas famosas do Brasil (militares, tradicionais, religiosas, estaduais)
"""
import urllib.request, urllib.parse, json, time, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = "http://localhost:8765"

with open("admin_token.txt") as f:
    TOKEN = f.read().strip()

HEADERS = {"Authorization": f"Bearer {TOKEN}"}

ESCOLAS = [
    # ── ACRE ──
    ("Colegio Estadual Helio Melo", "AC", "Rio Branco"),
    ("Centro de Ensino Medio Amalia Amorim", "AC", "Rio Branco"),

    # ── ALAGOAS ──
    ("Colegio Estadual Governador Lamenha Filho", "AL", "Maceio"),
    ("Centro Educacional Marista de Maceio", "AL", "Maceio"),
    ("Colegio Arquidiocesano Nossa Senhora Auxiliadora", "AL", "Maceio"),

    # ── AMAPA ──
    ("Centro de Ensino Medio Augusto Antunes", "AP", "Macapa"),
    ("Colegio Estadual Marco Zero do Equador", "AP", "Macapa"),

    # ── AMAZONAS ──
    ("Colegio Militar de Manaus", "AM", "Manaus"),
    ("Centro de Ensino Dom Bosco", "AM", "Manaus"),
    ("Colegio Nossa Senhora Auxiliadora", "AM", "Manaus"),
    ("Colegio Salesiano Dom Bosco Manaus", "AM", "Manaus"),

    # ── BAHIA ──
    ("Colegio Militar de Salvador", "BA", "Salvador"),
    ("Colegio Central (Instituto Central de Educacao Isaias Alves)", "BA", "Salvador"),
    ("Colegio Estadual Governador Lomanto Junior", "BA", "Salvador"),
    ("Colegio Nossa Senhora da Luz", "BA", "Salvador"),
    ("Colegio Marista Salvador", "BA", "Salvador"),
    ("Colegio Salesiano Nossa Senhora Auxiliadora Salvador", "BA", "Salvador"),
    ("Colegio Sao Jose de Salvador", "BA", "Salvador"),
    ("Colegio Nossa Senhora da Conceicao (Feira de Santana)", "BA", "Feira de Santana"),
    ("Colegio Estadual Agora Balthazar", "BA", "Vitoria da Conquista"),
    ("Colegio Nossa Senhora de Lourdes Palmares", "PE", "Palmares"),

    # ── CEARA ──
    ("Colegio Militar de Fortaleza", "CE", "Fortaleza"),
    ("Liceu do Ceara", "CE", "Fortaleza"),
    ("Colegio Farias Brito", "CE", "Fortaleza"),
    ("Colegio Sao Joao Fortaleza", "CE", "Fortaleza"),
    ("Colegio Santo Inacio Fortaleza", "CE", "Fortaleza"),
    ("Colegio Nossa Senhora das Gracas Fortaleza", "CE", "Fortaleza"),
    ("Colegio Ari de Sa Cavalcante", "CE", "Fortaleza"),
    ("Centro de Ensino Unificado de Fortaleza (CEFOR)", "CE", "Fortaleza"),
    ("Colegio Lourenco Filho", "CE", "Fortaleza"),
    ("Escola Estadual de Educacao Profissional EEFM Jose Albano", "CE", "Sobral"),

    # ── DISTRITO FEDERAL ──
    ("Colegio Militar de Brasilia", "DF", "Brasilia"),
    ("Centro Educacional La Salle Brasilia", "DF", "Brasilia"),
    ("Colegio Nossa Senhora de Fatima Brasilia", "DF", "Brasilia"),
    ("Colegio Marista Brasilia", "DF", "Brasilia"),
    ("Centro de Ensino Medio Elefante Branco", "DF", "Brasilia"),
    ("Centro de Ensino Medio Ave Branca", "DF", "Brasilia"),

    # ── ESPIRITO SANTO ──
    ("Colegio Estadual Goncalves Dias", "ES", "Vitoria"),
    ("Colegio Nossa Senhora Auxiliadora Vitoria", "ES", "Vitoria"),
    ("Colegio Marista Sao Joao Vitoria", "ES", "Vitoria"),
    ("Colegio Salesiano Cariacica", "ES", "Cariacica"),

    # ── GOIAS ──
    ("Colegio Estadual Lyceu de Goiania", "GO", "Goiania"),
    ("Colegio Marista Pio XII Goiania", "GO", "Goiania"),
    ("Colegio Nossa Senhora de Fatima Goiania", "GO", "Goiania"),
    ("Colegio Santa Clara Goiania", "GO", "Goiania"),
    ("Colegio Militar de Goias", "GO", "Goiania"),
    ("Colegio Salesiano Dom Bosco Goiania", "GO", "Goiania"),

    # ── MARANHAO ──
    ("Colegio Militar de Sao Luis", "MA", "Sao Luis"),
    ("Colegio Liceu Maranhanense", "MA", "Sao Luis"),
    ("Colegio Nossa Senhora das Gracas Sao Luis", "MA", "Sao Luis"),
    ("Colegio Sao Luis Sao Luis", "MA", "Sao Luis"),
    ("Colegio Salesiano Nossa Senhora Auxiliadora Sao Luis", "MA", "Sao Luis"),

    # ── MATO GROSSO ──
    ("Escola Estadual Liceu Cuiabano", "MT", "Cuiaba"),
    ("Colegio Salesiano Sao Domingos Savio Cuiaba", "MT", "Cuiaba"),
    ("Colegio Marista Cuiaba", "MT", "Cuiaba"),

    # ── MATO GROSSO DO SUL ──
    ("Colegio Estadual Maria Constanca Barros Machado", "MS", "Campo Grande"),
    ("Colegio Dom Bosco Campo Grande", "MS", "Campo Grande"),
    ("Colegio Marista Nossa Senhora da Abadia", "MS", "Campo Grande"),
    ("Escola Estadual Joaquim Murtinho", "MS", "Campo Grande"),

    # ── MINAS GERAIS ──
    ("Colegio Militar de Belo Horizonte", "MG", "Belo Horizonte"),
    ("Colegio Estadual Central de Minas Gerais", "MG", "Belo Horizonte"),
    ("Colegio Santo Agostinho Belo Horizonte", "MG", "Belo Horizonte"),
    ("Colegio Dom Bosco Belo Horizonte", "MG", "Belo Horizonte"),
    ("Colegio Marista Nossa Senhora das Gracas BH", "MG", "Belo Horizonte"),
    ("Colegio Loyola Belo Horizonte", "MG", "Belo Horizonte"),
    ("Colegio Sao Joao BH", "MG", "Belo Horizonte"),
    ("Colegio Anchieta Belo Horizonte", "MG", "Belo Horizonte"),
    ("Colegio Salesiano Dom Bosco Belo Horizonte", "MG", "Belo Horizonte"),
    ("Colegio Santa Maria Belo Horizonte", "MG", "Belo Horizonte"),
    ("Colegio Estadual Henrique Diniz", "MG", "Uberlandia"),
    ("Escola Estadual Bueno Brandao", "MG", "Juiz de Fora"),
    ("Colegio Santo Antonio Juiz de Fora", "MG", "Juiz de Fora"),

    # ── PARA ──
    ("Colegio Militar de Belem", "PA", "Belem"),
    ("Escola Estadual Paes de Carvalho", "PA", "Belem"),
    ("Colegio Nossa Senhora de Nazare Belem", "PA", "Belem"),
    ("Colegio Salesiano Nossa Senhora Auxiliadora Belem", "PA", "Belem"),
    ("Colegio Marista Assuncao Belem", "PA", "Belem"),

    # ── PARAIBA ──
    ("Colegio Estadual da Paraiba", "PB", "Joao Pessoa"),
    ("Colegio Pio X Joao Pessoa", "PB", "Joao Pessoa"),
    ("Escola Estadual Alcides Bezerra", "PB", "Joao Pessoa"),
    ("Colegio Nossa Senhora das Neves Joao Pessoa", "PB", "Joao Pessoa"),
    ("Escola Estadual de Comercio Epitacio Pessoa", "PB", "Joao Pessoa"),
    ("Colegio Estadual Epitacio Pessoa Campina Grande", "PB", "Campina Grande"),

    # ── PARANA ──
    ("Colegio Estadual do Parana", "PR", "Curitiba"),
    ("Colegio Militar de Curitiba", "PR", "Curitiba"),
    ("Colegio Notre Dame Curitiba", "PR", "Curitiba"),
    ("Colegio Santa Maria Curitiba", "PR", "Curitiba"),
    ("Colegio Marista Curitiba", "PR", "Curitiba"),
    ("Colegio Salesiano Santa Rosa Curitiba", "PR", "Curitiba"),
    ("Colegio Santo Inacio Curitiba", "PR", "Curitiba"),
    ("Colegio Positivo Curitiba", "PR", "Curitiba"),
    ("Colegio Bom Jesus Curitiba", "PR", "Curitiba"),
    ("Colegio Sao Jose Curitiba", "PR", "Curitiba"),
    ("Instituto de Educacao do Parana Professor Erasmo Pilotto", "PR", "Curitiba"),
    ("Colegio Estadual Professor Brasilio Itiberê", "PR", "Curitiba"),

    # ── PERNAMBUCO ──
    ("Colegio Militar do Recife", "PE", "Recife"),
    ("Colegio Nobre Sao Jose", "PE", "Recife"),
    ("Colegio Nossa Senhora do Carmo Recife", "PE", "Recife"),
    ("Colegio Santa Doroteia Recife", "PE", "Recife"),
    ("Colegio Salesiano Recife", "PE", "Recife"),
    ("Colegio Santa Maria Recife", "PE", "Recife"),
    ("Colegio Santa Cruz Recife", "PE", "Recife"),
    ("Colegio Marista Recife", "PE", "Recife"),
    ("Escola Estadual Professor Amorim", "PE", "Recife"),
    ("Colegio Anglo Recife", "PE", "Recife"),
    ("Colegio Estadual de Pernambuco", "PE", "Recife"),
    ("Colegio Nossa Senhora de Lourdes Recife", "PE", "Recife"),
    ("Colegio Boa Viagem Recife", "PE", "Recife"),
    ("Escola de Referencia em Ensino Medio Apolonio Sales", "PE", "Caruaru"),

    # ── PIAUI ──
    ("Colegio Estadual Zacarias de Goes", "PI", "Teresina"),
    ("Colegio Sagrado Coracao de Jesus Teresina", "PI", "Teresina"),
    ("Colegio Sao Francisco de Sales Teresina", "PI", "Teresina"),
    ("Escola Estadual Antonino Freire", "PI", "Teresina"),

    # ── RIO DE JANEIRO ──
    ("Colegio Pedro II (Sede)", "RJ", "Rio de Janeiro"),
    ("Colegio Militar do Rio de Janeiro", "RJ", "Rio de Janeiro"),
    ("Colegio Santo Inacio Rio de Janeiro", "RJ", "Rio de Janeiro"),
    ("Colegio Sao Bento Rio de Janeiro", "RJ", "Rio de Janeiro"),
    ("Colegio Nossa Senhora de Sion Rio de Janeiro", "RJ", "Rio de Janeiro"),
    ("Colegio Andrews Rio de Janeiro", "RJ", "Rio de Janeiro"),
    ("Colegio Estadual Amaro Cavalcanti", "RJ", "Rio de Janeiro"),
    ("Colegio Estadual Ferreira Viana", "RJ", "Rio de Janeiro"),
    ("Instituto de Educacao do Rio de Janeiro (IERJ)", "RJ", "Rio de Janeiro"),
    ("Colegio Nossa Senhora Auxiliadora Rio de Janeiro", "RJ", "Rio de Janeiro"),
    ("Colegio Salesiano Santa Rosa Rio de Janeiro", "RJ", "Rio de Janeiro"),
    ("Colegio La Salle Rio de Janeiro", "RJ", "Rio de Janeiro"),
    ("Colegio Santa Teresa Rio de Janeiro", "RJ", "Rio de Janeiro"),
    ("Colegio de Aplicacao UERJ", "RJ", "Rio de Janeiro"),
    ("Colegio Estadual Candido Mendes Niteroi", "RJ", "Niteroi"),
    ("Escola Estadual Joao Pessoa Volta Redonda", "RJ", "Volta Redonda"),

    # ── RIO GRANDE DO NORTE ──
    ("Colegio Estadual Augusto Severo", "RN", "Natal"),
    ("Ateneu Norte-Rio-Grandense", "RN", "Natal"),
    ("Colegio Nossa Senhora das Neves Natal", "RN", "Natal"),
    ("Colegio Salesiano Natal", "RN", "Natal"),
    ("Colegio Marista Natal", "RN", "Natal"),

    # ── RIO GRANDE DO SUL ──
    ("Colegio Militar de Porto Alegre", "RS", "Porto Alegre"),
    ("Colegio Estadual Julio de Castilhos", "RS", "Porto Alegre"),
    ("Instituto Estadual de Educacao Porto Alegre", "RS", "Porto Alegre"),
    ("Colegio Anchieta Porto Alegre", "RS", "Porto Alegre"),
    ("Colegio Farroupilha Porto Alegre", "RS", "Porto Alegre"),
    ("Colegio Sao Luis Porto Alegre", "RS", "Porto Alegre"),
    ("Colegio Notre Dame Porto Alegre", "RS", "Porto Alegre"),
    ("Colegio Israelita Brasileiro Porto Alegre", "RS", "Porto Alegre"),
    ("Colegio La Salle Porto Alegre", "RS", "Porto Alegre"),
    ("Colegio Salesiano Porto Alegre", "RS", "Porto Alegre"),
    ("Colegio Champagnat Porto Alegre", "RS", "Porto Alegre"),
    ("Colegio Santos Anjos Porto Alegre", "RS", "Porto Alegre"),
    ("Escola Estadual de Ensino Medio Pinheiro Machado", "RS", "Porto Alegre"),
    ("Colegio Estadual Sao Leopoldo", "RS", "Sao Leopoldo"),
    ("Colegio Sao Luís Ijui", "RS", "Ijui"),

    # ── RONDONIA ──
    ("Escola Estadual Carmela Dutra", "RO", "Porto Velho"),
    ("Colegio Nossa Senhora das Gracas Porto Velho", "RO", "Porto Velho"),

    # ── RORAIMA ──
    ("Escola Estadual Monteiro Lobato Boa Vista", "RR", "Boa Vista"),

    # ── SANTA CATARINA ──
    ("Colegio Estadual Aniceto Mossimann", "SC", "Florianopolis"),
    ("Colegio Catarinense Florianopolis", "SC", "Florianopolis"),
    ("Colegio Coracao de Jesus Florianopolis", "SC", "Florianopolis"),
    ("Colegio Salesiano Sao Jose Florianopolis", "SC", "Florianopolis"),
    ("Instituto Estadual de Educacao Florianopolis", "SC", "Florianopolis"),
    ("Colegio Medianeira Florianopolis", "SC", "Florianopolis"),
    ("Escola Estadual Basica Simao Jose Hess", "SC", "Florianopolis"),
    ("Escola Estadual Adolfo Konder", "SC", "Blumenau"),
    ("Colegio Sagrada Familia Blumenau", "SC", "Blumenau"),
    ("Colegio Sao Luis Joinville", "SC", "Joinville"),

    # ── SERGIPE ──
    ("Colegio Estadual Atheneu Sergipense", "SE", "Aracaju"),
    ("Colegio Nossa Senhora de Lourdes Aracaju", "SE", "Aracaju"),
    ("Colegio Salesiano Nossa Senhora Auxiliadora Aracaju", "SE", "Aracaju"),

    # ── SAO PAULO ──
    ("Colegio Militar de Sao Paulo", "SP", "Sao Paulo"),
    ("Escola Estadual Fernao Dias Paes", "SP", "Sao Paulo"),
    ("Escola Estadual Caetano de Campos", "SP", "Sao Paulo"),
    ("Colegio Sao Bento Sao Paulo", "SP", "Sao Paulo"),
    ("Colegio Nossa Senhora das Gracas Sao Paulo", "SP", "Sao Paulo"),
    ("Colegio Marista Arquidiocesano Sao Paulo", "SP", "Sao Paulo"),
    ("Colegio Salesiano Dom Bosco Sao Paulo", "SP", "Sao Paulo"),
    ("Colegio Santo Inacio Sao Paulo", "SP", "Sao Paulo"),
    ("Colegio Bandeirantes Sao Paulo", "SP", "Sao Paulo"),
    ("Colegio Anglo Sao Paulo", "SP", "Sao Paulo"),
    ("Colegio Etapa Sao Paulo", "SP", "Sao Paulo"),
    ("Colegio Objetivo Sao Paulo", "SP", "Sao Paulo"),
    ("Colegio Mackenzie Sao Paulo", "SP", "Sao Paulo"),
    ("Colegio Albert Einstein Sao Paulo", "SP", "Sao Paulo"),
    ("Escola Estadual Presidente Vargas Sao Paulo", "SP", "Sao Paulo"),
    ("Instituto Estadual Fernao Dias Paes", "SP", "Sao Paulo"),
    ("Colegio Sao Joao Sao Paulo", "SP", "Sao Paulo"),
    ("Colegio La Salle Sao Paulo", "SP", "Sao Paulo"),
    ("Colegio Notre Dame Sao Paulo", "SP", "Sao Paulo"),
    ("Escola Estadual Joao Kopke", "SP", "Sao Paulo"),
    ("Escola Estadual Rodrigues Alves", "SP", "Sao Paulo"),
    ("Colegio Estadual Escola Tecnica Estadual Jorge Street", "SP", "Sao Paulo"),
    ("Colegio Sao Luis Sao Paulo", "SP", "Sao Paulo"),
    ("Colegio Estadual Oswaldo Cruz Sao Paulo", "SP", "Sao Paulo"),
    ("Colegio Anglo Campinas", "SP", "Campinas"),
    ("Colegio Salesiano Dom Bosco Campinas", "SP", "Campinas"),
    ("Colegio Marista Campinas", "SP", "Campinas"),
    ("Escola Estadual Carlos Gomes Campinas", "SP", "Campinas"),
    ("Colegio Santa Marcelina Santos", "SP", "Santos"),
    ("Colegio Macedo Soares Santos", "SP", "Santos"),
    ("Colegio Sao Francisco de Assis Ribeirao Preto", "SP", "Ribeirao Preto"),
    ("Escola Estadual Otoniel Mota Ribeirao Preto", "SP", "Ribeirao Preto"),
    ("Colegio Dom Bosco Sao Jose dos Campos", "SP", "Sao Jose dos Campos"),

    # ── TOCANTINS ──
    ("Colegio Estadual Joaquim Teotonio Segurado", "TO", "Palmas"),
    ("Colegio Estadual Modelo Palmas", "TO", "Palmas"),
]


def post(url, data, headers={}):
    fd = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(BASE + url, data=fd, headers=headers)
    try:
        return json.loads(urllib.request.urlopen(req).read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise Exception(f"HTTP {e.code}: {body}")


def main():
    print(f"=== Seed: {len(ESCOLAS)} Escolas Brasileiras ===\n")
    ok = 0
    erros = 0

    for i, (nome, estado, cidade) in enumerate(ESCOLAS, 1):
        try:
            r = post("/api/admin/institutions", {
                "name": nome,
                "type": "school",
                "state": estado,
                "city": cidade,
            }, HEADERS)
            print(f"[{i:03d}/{len(ESCOLAS)}] OK  {nome[:65]} | {cidade}/{estado}")
            ok += 1
        except Exception as e:
            print(f"[{i:03d}/{len(ESCOLAS)}] ERR {nome[:50]} => {e}")
            erros += 1
        time.sleep(0.03)

    print(f"\n{'='*60}")
    print(f"CONCLUIDO: {ok} escolas | {erros} erros")

    req = urllib.request.Request(BASE + "/api/institutions?type=school")
    total = len(json.loads(urllib.request.urlopen(req).read()))
    print(f"Total no banco: {total} escolas")


main()
