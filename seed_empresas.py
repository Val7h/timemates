"""
Seed - Empresas grandes do Brasil
"""
import urllib.request, urllib.parse, json, time, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = "http://localhost:8765"

with open("admin_token.txt") as f:
    TOKEN = f.read().strip()

HEADERS = {"Authorization": f"Bearer {TOKEN}"}

EMPRESAS = [
    # ── PETROLEO & ENERGIA ──
    ("Petrobras", "RJ", "Rio de Janeiro"),
    ("Shell Brasil", "RJ", "Rio de Janeiro"),
    ("TotalEnergies Brasil", "RJ", "Rio de Janeiro"),
    ("Raizen", "SP", "Sao Paulo"),
    ("Vibra Energia (BR Distribuidora)", "RJ", "Rio de Janeiro"),
    ("Eletrobras", "RJ", "Rio de Janeiro"),
    ("Cemig", "MG", "Belo Horizonte"),
    ("Copel", "PR", "Curitiba"),
    ("CPFL Energia", "SP", "Campinas"),
    ("Engie Brasil", "SC", "Florianopolis"),
    ("Equatorial Energia", "MA", "Sao Luis"),
    ("Neoenergia", "BA", "Salvador"),
    ("Enel Brasil", "SP", "Sao Paulo"),

    # ── MINERACAO & SIDERURGIA ──
    ("Vale", "RJ", "Rio de Janeiro"),
    ("Gerdau", "RS", "Porto Alegre"),
    ("CSN (Companhia Siderurgica Nacional)", "RJ", "Rio de Janeiro"),
    ("Usiminas", "MG", "Belo Horizonte"),
    ("ArcelorMittal Brasil", "MG", "Belo Horizonte"),
    ("Samarco Mineracao", "ES", "Vitoria"),
    ("Anglo American Brasil", "MG", "Belo Horizonte"),
    ("Kinross Brasil Mineracao", "MG", "Belo Horizonte"),

    # ── BANCOS & FINANCAS ──
    ("Banco do Brasil", "DF", "Brasilia"),
    ("Bradesco", "SP", "Osasco"),
    ("Itau Unibanco", "SP", "Sao Paulo"),
    ("Caixa Economica Federal", "DF", "Brasilia"),
    ("Santander Brasil", "SP", "Sao Paulo"),
    ("BTG Pactual", "SP", "Sao Paulo"),
    ("XP Investimentos", "SP", "Sao Paulo"),
    ("Nubank", "SP", "Sao Paulo"),
    ("Inter (Banco Inter)", "MG", "Belo Horizonte"),
    ("Sicredi", "RS", "Porto Alegre"),
    ("Sicoob", "DF", "Brasilia"),
    ("Banrisul", "RS", "Porto Alegre"),
    ("Banco do Nordeste (BNB)", "CE", "Fortaleza"),
    ("BNDES", "RJ", "Rio de Janeiro"),

    # ── TELECOMUNICACOES ──
    ("Claro Brasil", "SP", "Sao Paulo"),
    ("Vivo (Telefonica Brasil)", "SP", "Sao Paulo"),
    ("TIM Brasil", "RJ", "Rio de Janeiro"),
    ("Oi", "RJ", "Rio de Janeiro"),
    ("Embratel", "RJ", "Rio de Janeiro"),
    ("Algar Telecom", "MG", "Uberlandia"),

    # ── VAREJO & COMERCIO ──
    ("Mercado Livre Brasil", "SP", "Sao Paulo"),
    ("Americanas", "RJ", "Rio de Janeiro"),
    ("Magazineluiza (Magalu)", "SP", "Franca"),
    ("Grupo Pao de Acucar (GPA)", "SP", "Sao Paulo"),
    ("Carrefour Brasil", "SP", "Sao Paulo"),
    ("Atacadao", "SP", "Sao Paulo"),
    ("Casas Bahia (Via Varejo)", "SP", "Sao Paulo"),
    ("Riachuelo", "SP", "Sao Paulo"),
    ("Renner", "RS", "Porto Alegre"),
    ("C&A Brasil", "SP", "Sao Paulo"),
    ("Hering", "SC", "Blumenau"),
    ("Arezzo", "MG", "Belo Horizonte"),
    ("Grupo Soma", "RJ", "Rio de Janeiro"),
    ("Totvs", "SP", "Sao Paulo"),
    ("Localiza", "MG", "Belo Horizonte"),
    ("Movida", "SP", "Sao Paulo"),
    ("Unidas", "MG", "Belo Horizonte"),

    # ── ALIMENTOS & BEBIDAS ──
    ("JBS", "SP", "Sao Paulo"),
    ("BRF (Brasil Foods)", "SP", "Sao Paulo"),
    ("Marfrig", "SP", "Sao Paulo"),
    ("Minerva Foods", "SP", "Sao Paulo"),
    ("Ambev", "SP", "Sao Paulo"),
    ("Heineken Brasil", "SP", "Sao Paulo"),
    ("Coca-Cola Brasil", "SP", "Rio de Janeiro"),
    ("Nestle Brasil", "SP", "Sao Paulo"),
    ("Unilever Brasil", "SP", "Sao Paulo"),
    ("Sadia", "SC", "Concordia"),
    ("Perdigao", "SC", "Videira"),
    ("Vigor Alimentos", "SP", "Sao Paulo"),
    ("M. Dias Branco", "CE", "Eusebio"),

    # ── AGRONEGOCIO ──
    ("Embrapa", "DF", "Brasilia"),
    ("Copersucar", "SP", "Sao Paulo"),
    ("SLC Agricola", "RS", "Porto Alegre"),
    ("Amaggi (Andre Maggi)", "MT", "Cuiaba"),
    ("Louis Dreyfus Brasil", "SP", "Sao Paulo"),
    ("Cargill Brasil", "SP", "Sao Paulo"),
    ("ADM do Brasil", "SP", "Sao Paulo"),
    ("Bunge Brasil", "SP", "Sao Paulo"),

    # ── INDUSTRIA & MANUFATURA ──
    ("Embraer", "SP", "Sao Jose dos Campos"),
    ("Fiat Chrysler Brasil (Stellantis)", "MG", "Betim"),
    ("Volkswagen do Brasil", "SP", "Sao Paulo"),
    ("General Motors Brasil", "SP", "Sao Paulo"),
    ("Ford Brasil", "BA", "Camacari"),
    ("Toyota do Brasil", "SP", "Indaiatuba"),
    ("Honda Brasil", "SP", "Sumare"),
    ("Renault do Brasil", "PR", "Curitiba"),
    ("Volvo do Brasil", "PR", "Curitiba"),
    ("WEG Industrias", "SC", "Jaragua do Sul"),
    ("Weg Equipamentos Eletricos", "SC", "Jaragua do Sul"),
    ("Whirlpool (Brastemp/Consul)", "SP", "Sao Paulo"),
    ("Electrolux do Brasil", "SC", "Sao Carlos"),
    ("3M Brasil", "SP", "Sumare"),
    ("Bosch Brasil", "SP", "Campinas"),
    ("Mahle Brasil", "SP", "Mogi Guacu"),
    ("Embraco", "SC", "Joinville"),
    ("Intelbras", "SC", "Sao Jose"),
    ("Randon Implementos", "RS", "Caxias do Sul"),
    ("Marcopolo", "RS", "Caxias do Sul"),

    # ── CONSTRUCAO & REAL ESTATE ──
    ("MRV Engenharia", "MG", "Belo Horizonte"),
    ("Cyrela", "SP", "Sao Paulo"),
    ("PDG Realty", "SP", "Sao Paulo"),
    ("Gafisa", "SP", "Sao Paulo"),
    ("Tenda", "SP", "Sao Paulo"),
    ("Direcional Engenharia", "MG", "Belo Horizonte"),
    ("Even Construtora", "SP", "Sao Paulo"),
    ("EZTec", "SP", "Sao Paulo"),
    ("Odebrecht (Novonor)", "BA", "Salvador"),
    ("Andrade Gutierrez", "MG", "Belo Horizonte"),
    ("OAS", "BA", "Salvador"),
    ("WTorre", "SP", "Sao Paulo"),

    # ── SAUDE ──
    ("Rede D'Or Sao Luiz", "RJ", "Rio de Janeiro"),
    ("Hapvida", "CE", "Fortaleza"),
    ("NotreDame Intermedica", "SP", "Sao Paulo"),
    ("Unimed Brasil", "SP", "Sao Paulo"),
    ("Dasa (Diagnosticos da America)", "SP", "Barueri"),
    ("Fleury Medicina e Saude", "SP", "Sao Paulo"),
    ("Hermes Pardini", "MG", "Belo Horizonte"),
    ("Hypera Pharma", "SP", "Sao Paulo"),
    ("EMS (Eurofarma)", "SP", "Sao Paulo"),
    ("Blau Farmaceutica", "SP", "Cotia"),

    # ── LOGISTICA & TRANSPORTE ──
    ("Correios (ECT)", "DF", "Brasilia"),
    ("Latam Airlines Brasil", "SP", "Sao Paulo"),
    ("Gol Linhas Aereas", "SP", "Sao Paulo"),
    ("Azul Linhas Aereas", "SP", "Campinas"),
    ("JSL Logistica", "SP", "Sao Paulo"),
    ("TIM Participacoes", "RJ", "Rio de Janeiro"),
    ("Tegma Gestao Logistica", "SP", "Sao Bernardo do Campo"),

    # ── TECNOLOGIA ──
    ("CI&T", "SP", "Campinas"),
    ("Stefanini", "SP", "Sao Paulo"),
    ("Accenture Brasil", "SP", "Sao Paulo"),
    ("IBM Brasil", "SP", "Sao Paulo"),
    ("SAP Brasil", "SP", "Sao Paulo"),
    ("Oracle Brasil", "SP", "Sao Paulo"),
    ("Wipro Brasil", "SP", "Sao Paulo"),
    ("Capgemini Brasil", "SP", "Sao Paulo"),
    ("Atos Brasil", "SP", "Sao Paulo"),
    ("Senior Sistemas", "SC", "Blumenau"),
    ("LINX", "SP", "Sao Paulo"),
    ("VTEX", "RJ", "Rio de Janeiro"),
    ("Resultados Digitais (RD Station)", "SC", "Florianopolis"),
    ("Hotmart", "MG", "Belo Horizonte"),
    ("iFood", "SP", "Osasco"),
    ("99 (DiDi Brasil)", "SP", "Sao Paulo"),
    ("Rappi Brasil", "SP", "Sao Paulo"),
    ("Creditas", "SP", "Sao Paulo"),

    # ── PAPEL & CELULOSE ──
    ("Suzano Papel e Celulose", "SP", "Sao Paulo"),
    ("Klabin", "SP", "Sao Paulo"),
    ("Eldorado Brasil Celulose", "MS", "Tres Lagoas"),

    # ── SEGUROS ──
    ("Porto Seguro", "SP", "Sao Paulo"),
    ("SulAmerica Seguros", "SP", "Sao Paulo"),
    ("Zurich Brasil Seguros", "SP", "Sao Paulo"),
    ("Liberty Seguros", "SP", "Sao Paulo"),

    # ── EDUCACAO ──
    ("Grupo Kroton (Cogna)", "MG", "Belo Horizonte"),
    ("Grupo Anima Educacao", "SP", "Sao Paulo"),
    ("YDUQS (Estacio)", "RJ", "Rio de Janeiro"),
    ("Ser Educacional", "PE", "Recife"),
    ("Grupo SEB", "SP", "Sao Paulo"),
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
    print(f"=== Seed: {len(EMPRESAS)} Empresas Brasileiras ===\n")
    ok = 0
    erros = 0

    for i, (nome, estado, cidade) in enumerate(EMPRESAS, 1):
        try:
            r = post("/api/admin/institutions", {
                "name": nome,
                "type": "company",
                "state": estado,
                "city": cidade,
            }, HEADERS)
            print(f"[{i:03d}/{len(EMPRESAS)}] OK  {nome[:60]} | {cidade}/{estado}")
            ok += 1
        except Exception as e:
            print(f"[{i:03d}/{len(EMPRESAS)}] ERR {nome[:50]} => {e}")
            erros += 1
        time.sleep(0.03)

    print(f"\n{'='*60}")
    print(f"CONCLUIDO: {ok} empresas | {erros} erros")

    req = urllib.request.Request(BASE + "/api/institutions?type=company")
    total = len(json.loads(urllib.request.urlopen(req).read()))
    print(f"Total no banco: {total} empresas")


main()
