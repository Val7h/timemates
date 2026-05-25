"""
Seed - Universidades Estaduais do Brasil
"""
import urllib.request, urllib.parse, json, time, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = "http://localhost:8765"

with open("admin_token.txt") as f:
    TOKEN = f.read().strip()

HEADERS = {"Authorization": f"Bearer {TOKEN}"}

ESTADUAIS = [
    # ── SAO PAULO ──
    ("Universidade de Sao Paulo (USP)", "SP", "Sao Paulo"),
    ("Universidade Estadual de Campinas (UNICAMP)", "SP", "Campinas"),
    ("Universidade Estadual Paulista (UNESP)", "SP", "Sao Paulo"),
    ("Universidade Virtual do Estado de Sao Paulo (UNIVESP)", "SP", "Sao Paulo"),

    # ── RIO DE JANEIRO ──
    ("Universidade do Estado do Rio de Janeiro (UERJ)", "RJ", "Rio de Janeiro"),
    ("Universidade Estadual do Norte Fluminense (UENF)", "RJ", "Campos dos Goytacazes"),
    ("Universidade do Grande Rio (UNIGRANRIO)", "RJ", "Duque de Caxias"),

    # ── MINAS GERAIS ──
    ("Universidade do Estado de Minas Gerais (UEMG)", "MG", "Belo Horizonte"),
    ("Universidade Estadual de Montes Claros (UNIMONTES)", "MG", "Montes Claros"),
    ("Universidade Estadual de Minas Gerais (FEEMG)", "MG", "Belo Horizonte"),

    # ── BAHIA ──
    ("Universidade Estadual de Feira de Santana (UEFS)", "BA", "Feira de Santana"),
    ("Universidade Estadual de Santa Cruz (UESC)", "BA", "Ilheus"),
    ("Universidade Estadual do Sudoeste da Bahia (UESB)", "BA", "Vitoria da Conquista"),
    ("Universidade Estadual da Bahia (UNEB)", "BA", "Salvador"),
    ("Universidade do Estado da Bahia (UNEB)", "BA", "Salvador"),

    # ── CEARA ──
    ("Universidade Estadual do Ceara (UECE)", "CE", "Fortaleza"),
    ("Universidade Regional do Cariri (URCA)", "CE", "Crato"),
    ("Universidade Estadual Vale do Acara (UVA)", "CE", "Sobral"),

    # ── PERNAMBUCO ──
    ("Universidade de Pernambuco (UPE)", "PE", "Recife"),

    # ── PARANA ──
    ("Universidade Estadual de Londrina (UEL)", "PR", "Londrina"),
    ("Universidade Estadual de Maringa (UEM)", "PR", "Maringa"),
    ("Universidade Estadual de Ponta Grossa (UEPG)", "PR", "Ponta Grossa"),
    ("Universidade Estadual do Centro-Oeste (UNICENTRO)", "PR", "Guarapuava"),
    ("Universidade Estadual do Norte do Parana (UENP)", "PR", "Jacarezinho"),
    ("Universidade Estadual do Oeste do Parana (UNIOESTE)", "PR", "Cascavel"),
    ("Universidade Estadual do Parana (UNESPAR)", "PR", "Curitiba"),

    # ── RIO GRANDE DO SUL ──
    ("Universidade Estadual do Rio Grande do Sul (UERGS)", "RS", "Porto Alegre"),

    # ── SANTA CATARINA ──
    ("Universidade do Estado de Santa Catarina (UDESC)", "SC", "Florianopolis"),

    # ── GOIAS ──
    ("Universidade Estadual de Goias (UEG)", "GO", "Anapolis"),

    # ── MATO GROSSO ──
    ("Universidade do Estado de Mato Grosso (UNEMAT)", "MT", "Caceres"),

    # ── MATO GROSSO DO SUL ──
    ("Universidade Estadual de Mato Grosso do Sul (UEMS)", "MS", "Dourados"),

    # ── MARANHAO ──
    ("Universidade Estadual do Maranhao (UEMA)", "MA", "Sao Luis"),

    # ── PARA ──
    ("Universidade do Estado do Para (UEPA)", "PA", "Belem"),

    # ── AMAZONAS ──
    ("Universidade do Estado do Amazonas (UEA)", "AM", "Manaus"),

    # ── PIAUI ──
    ("Universidade Estadual do Piaui (UESPI)", "PI", "Teresina"),

    # ── RIO GRANDE DO NORTE ──
    ("Universidade do Estado do Rio Grande do Norte (UERN)", "RN", "Mossoro"),

    # ── PARAIBA ──
    ("Universidade Estadual da Paraiba (UEPB)", "PB", "Campina Grande"),

    # ── ALAGOAS ──
    ("Universidade Estadual de Alagoas (UNEAL)", "AL", "Arapiraca"),

    # ── SERGIPE ──
    ("Universidade Estadual de Sergipe (UFS Estadual)", "SE", "Lagarto"),

    # ── ESPIRITO SANTO ──
    ("Universidade Estadual do Norte do Espirito Santo (UNES)", "ES", "Sao Mateus"),

    # ── TOCANTINS ──
    ("Universidade Estadual do Tocantins (UNITINS)", "TO", "Palmas"),

    # ── RONDONIA ──
    ("Universidade Estadual de Rondonia (UNERO)", "RO", "Ji-Parana"),

    # ── PARTICULARES DE GRANDE PORTE ──
    ("Pontificia Universidade Catolica de Sao Paulo (PUC-SP)", "SP", "Sao Paulo"),
    ("Pontificia Universidade Catolica do Rio de Janeiro (PUC-Rio)", "RJ", "Rio de Janeiro"),
    ("Pontificia Universidade Catolica de Minas Gerais (PUC Minas)", "MG", "Belo Horizonte"),
    ("Pontificia Universidade Catolica do Rio Grande do Sul (PUCRS)", "RS", "Porto Alegre"),
    ("Pontificia Universidade Catolica do Parana (PUCPR)", "PR", "Curitiba"),
    ("Pontificia Universidade Catolica de Campinas (PUC-Campinas)", "SP", "Campinas"),
    ("Universidade Metodista de Sao Paulo (UMESP)", "SP", "Sao Bernardo do Campo"),
    ("Universidade Presbiteriana Mackenzie", "SP", "Sao Paulo"),
    ("Universidade Sao Francisco (USF)", "SP", "Braganca Paulista"),
    ("Universidade Cruzeiro do Sul", "SP", "Sao Paulo"),
    ("Centro Universitario FEI", "SP", "Sao Bernardo do Campo"),
    ("Universidade Estadual de Santa Cruz (UESC)", "BA", "Ilheus"),
    ("Universidade do Vale do Rio dos Sinos (UNISINOS)", "RS", "Sao Leopoldo"),
    ("Universidade de Caxias do Sul (UCS)", "RS", "Caxias do Sul"),
    ("Universidade Regional de Blumenau (FURB)", "SC", "Blumenau"),
    ("Universidade do Vale do Itajai (UNIVALI)", "SC", "Itajai"),
    ("Universidade Comunitaria da Regiao de Chapeco (UNOCHAPECO)", "SC", "Chapeco"),
    ("Universidade do Oeste de Santa Catarina (UNOESC)", "SC", "Joacaba"),
    ("Universidade do Sul de Santa Catarina (UNISUL)", "SC", "Tubarao"),
    ("Universidade Norte do Parana (UNOPAR)", "PR", "Londrina"),
    ("Centro Universitario Ingenieur (UNINTER)", "PR", "Curitiba"),
    ("Universidade Positivo (UP)", "PR", "Curitiba"),
    ("Universidade do Vale do Paraiba (UNIVAP)", "SP", "Sao Jose dos Campos"),
    ("Universidade de Ribeirao Preto (UNAERP)", "SP", "Ribeirao Preto"),
    ("Universidade de Franca (UNIFRAN)", "SP", "Franca"),
    ("Universidade Bandeirante (UNIBAN)", "SP", "Sao Paulo"),
    ("Universidade Sao Judas Tadeu (USJT)", "SP", "Sao Paulo"),
    ("Universidade Federal de Integra Lusofonia Afro-Brasileira (UNILAB)", "CE", "Redencao"),
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
    print(f"=== Seed: {len(ESTADUAIS)} Universidades Estaduais/Particulares ===\n")
    ok = 0
    erros = 0

    for i, (nome, estado, cidade) in enumerate(ESTADUAIS, 1):
        try:
            r = post("/api/admin/institutions", {
                "name": nome,
                "type": "university",
                "state": estado,
                "city": cidade,
            }, HEADERS)
            print(f"[{i:03d}/{len(ESTADUAIS)}] OK  {nome[:65]} | {cidade}/{estado}")
            ok += 1
        except Exception as e:
            print(f"[{i:03d}/{len(ESTADUAIS)}] ERR {nome[:50]} => {e}")
            erros += 1
        time.sleep(0.03)

    print(f"\n{'='*60}")
    print(f"CONCLUIDO: {ok} universidades | {erros} erros")

    req = urllib.request.Request(BASE + "/api/institutions?type=university")
    total = len(json.loads(urllib.request.urlopen(req).read()))
    print(f"Total no banco: {total} universidades")


main()
