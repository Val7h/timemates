"""
Seed runner - usa token salvo, adiciona universidades sem duplicata
"""
import urllib.request, urllib.parse, json, time, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = "http://localhost:8765"

with open("admin_token.txt") as f:
    TOKEN = f.read().strip()

HEADERS = {"Authorization": f"Bearer {TOKEN}"}

UNIVERSIDADES = [
    # ACRE
    ("Universidade Federal do Acre (UFAC)", "AC", "Rio Branco"),
    # ALAGOAS
    ("Universidade Federal de Alagoas (UFAL)", "AL", "Maceio"),
    # AMAPA
    ("Universidade Federal do Amapa (UNIFAP)", "AP", "Macapa"),
    # AMAZONAS
    ("Universidade Federal do Amazonas (UFAM)", "AM", "Manaus"),
    # BAHIA
    ("Universidade Federal da Bahia (UFBA)", "BA", "Salvador"),
    ("Universidade Federal do Reconcavo da Bahia (UFRB)", "BA", "Cruz das Almas"),
    ("Universidade Federal do Oeste da Bahia (UFOB)", "BA", "Barreiras"),
    ("Universidade Federal do Sul da Bahia (UFSB)", "BA", "Itabuna"),
    # CEARA
    ("Universidade Federal do Ceara (UFC)", "CE", "Fortaleza"),
    ("Universidade Federal do Cariri (UFCA)", "CE", "Juazeiro do Norte"),
    ("Universidade da Integracao Internacional da Lusofonia Afro-Brasileira (UNILAB)", "CE", "Redencao"),
    # DISTRITO FEDERAL
    ("Universidade de Brasilia (UnB)", "DF", "Brasilia"),
    # ESPIRITO SANTO
    ("Universidade Federal do Espirito Santo (UFES)", "ES", "Vitoria"),
    # GOIAS
    ("Universidade Federal de Goias (UFG)", "GO", "Goiania"),
    ("Universidade Federal de Catalao (UFCAT)", "GO", "Catalao"),
    ("Universidade Federal de Jatai (UFJ)", "GO", "Jatai"),
    # MARANHAO
    ("Universidade Federal do Maranhao (UFMA)", "MA", "Sao Luis"),
    # MATO GROSSO
    ("Universidade Federal de Mato Grosso (UFMT)", "MT", "Cuiaba"),
    # MATO GROSSO DO SUL
    ("Universidade Federal de Mato Grosso do Sul (UFMS)", "MS", "Campo Grande"),
    ("Universidade Federal da Grande Dourados (UFGD)", "MS", "Dourados"),
    # MINAS GERAIS
    ("Universidade Federal de Minas Gerais (UFMG)", "MG", "Belo Horizonte"),
    ("Universidade Federal de Vicosa (UFV)", "MG", "Vicosa"),
    ("Universidade Federal de Juiz de Fora (UFJF)", "MG", "Juiz de Fora"),
    ("Universidade Federal de Ouro Preto (UFOP)", "MG", "Ouro Preto"),
    ("Universidade Federal de Lavras (UFLA)", "MG", "Lavras"),
    ("Universidade Federal de Alfenas (UNIFAL-MG)", "MG", "Alfenas"),
    ("Universidade Federal de Itajuba (UNIFEI)", "MG", "Itajuba"),
    ("Universidade Federal de Sao Joao del-Rei (UFSJ)", "MG", "Sao Joao del-Rei"),
    ("Universidade Federal do Triangulo Mineiro (UFTM)", "MG", "Uberaba"),
    ("Universidade Federal dos Vales do Jequitinhonha e Mucuri (UFVJM)", "MG", "Diamantina"),
    ("Universidade Federal de Uberlandia (UFU)", "MG", "Uberlandia"),
    # PARA
    ("Universidade Federal do Para (UFPA)", "PA", "Belem"),
    ("Universidade Federal Rural da Amazonia (UFRA)", "PA", "Belem"),
    ("Universidade Federal do Oeste do Para (UFOPA)", "PA", "Santarem"),
    ("Universidade Federal do Sul e Sudeste do Para (UNIFESSPA)", "PA", "Maraba"),
    # PARAIBA
    ("Universidade Federal da Paraiba (UFPB)", "PB", "Joao Pessoa"),
    ("Universidade Federal de Campina Grande (UFCG)", "PB", "Campina Grande"),
    # PARANA
    ("Universidade Federal do Parana (UFPR)", "PR", "Curitiba"),
    ("Universidade Tecnologica Federal do Parana (UTFPR)", "PR", "Curitiba"),
    ("Universidade Federal da Integracao Latino-Americana (UNILA)", "PR", "Foz do Iguacu"),
    # PERNAMBUCO
    ("Universidade Federal de Pernambuco (UFPE)", "PE", "Recife"),
    ("Universidade Federal Rural de Pernambuco (UFRPE)", "PE", "Recife"),
    ("Universidade Federal do Vale do Sao Francisco (UNIVASF)", "PE", "Petrolina"),
    ("Universidade Federal do Agreste de Pernambuco (UFAPE)", "PE", "Garanhuns"),
    # PIAUI
    ("Universidade Federal do Piaui (UFPI)", "PI", "Teresina"),
    ("Universidade Federal do Delta do Parnaiba (UFDPar)", "PI", "Parnaiba"),
    # RIO DE JANEIRO
    ("Universidade Federal do Rio de Janeiro (UFRJ)", "RJ", "Rio de Janeiro"),
    ("Universidade Federal Fluminense (UFF)", "RJ", "Niteroi"),
    ("Universidade Federal do Estado do Rio de Janeiro (UNIRIO)", "RJ", "Rio de Janeiro"),
    ("Universidade Federal Rural do Rio de Janeiro (UFRRJ)", "RJ", "Seropedica"),
    # RIO GRANDE DO NORTE
    ("Universidade Federal do Rio Grande do Norte (UFRN)", "RN", "Natal"),
    ("Universidade Federal Rural do Semi-Arido (UFERSA)", "RN", "Mossoro"),
    # RIO GRANDE DO SUL
    ("Universidade Federal do Rio Grande do Sul (UFRGS)", "RS", "Porto Alegre"),
    ("Universidade Federal de Santa Maria (UFSM)", "RS", "Santa Maria"),
    ("Universidade Federal do Rio Grande (FURG)", "RS", "Rio Grande"),
    ("Universidade Federal de Pelotas (UFPEL)", "RS", "Pelotas"),
    ("Universidade Federal de Ciencias da Saude de Porto Alegre (UFCSPA)", "RS", "Porto Alegre"),
    ("Universidade Federal do Pampa (UNIPAMPA)", "RS", "Bage"),
    # RONDONIA
    ("Fundacao Universidade Federal de Rondonia (UNIR)", "RO", "Porto Velho"),
    # RORAIMA
    ("Universidade Federal de Roraima (UFRR)", "RR", "Boa Vista"),
    # SANTA CATARINA
    ("Universidade Federal de Santa Catarina (UFSC)", "SC", "Florianopolis"),
    ("Universidade Federal da Fronteira Sul (UFFS)", "SC", "Chapeco"),
    # SERGIPE
    ("Universidade Federal de Sergipe (UFS)", "SE", "Sao Cristovao"),
    # SAO PAULO
    ("Universidade Federal de Sao Carlos (UFSCar)", "SP", "Sao Carlos"),
    ("Universidade Federal de Sao Paulo (UNIFESP)", "SP", "Sao Paulo"),
    ("Universidade Federal do ABC (UFABC)", "SP", "Santo Andre"),
    # TOCANTINS
    ("Universidade Federal do Tocantins (UFT)", "TO", "Palmas"),
    ("Universidade Federal do Norte do Tocantins (UFNT)", "TO", "Araguaina"),
]


def post(url, data, headers={}):
    fd = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(BASE + url, data=fd, headers=headers)
    return json.loads(urllib.request.urlopen(req).read())


def main():
    print(f"=== Seed: {len(UNIVERSIDADES)} Universidades Federais ===\n")
    ok = 0
    erros = 0

    for i, (nome, estado, cidade) in enumerate(UNIVERSIDADES, 1):
        try:
            r = post("/api/admin/institutions", {
                "name": nome,
                "type": "university",
                "state": estado,
                "city": cidade,
            }, HEADERS)
            print(f"[{i:02d}/{len(UNIVERSIDADES)}] OK  {nome[:65]} | {cidade}/{estado}")
            ok += 1
        except Exception as e:
            print(f"[{i:02d}/{len(UNIVERSIDADES)}] ERR {nome[:50]} => {e}")
            erros += 1
        time.sleep(0.03)

    print(f"\n{'='*60}")
    print(f"CONCLUIDO: {ok} universidades | {erros} erros")

    # Verificar total
    req = urllib.request.Request(BASE + "/api/institutions?type=university")
    total = len(json.loads(urllib.request.urlopen(req).read()))
    print(f"Total no banco: {total} universidades federais")


main()
