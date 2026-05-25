"""
Seed - Cidades do Brasil (capitais + grandes cidades)
"""
import urllib.request, urllib.parse, json, time, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = "http://localhost:8765"

with open("admin_token.txt") as f:
    TOKEN = f.read().strip()

HEADERS = {"Authorization": f"Bearer {TOKEN}"}

CIDADES = [
    # ── 27 CAPITAIS ──
    ("Rio Branco", "AC", "Rio Branco"),
    ("Maceio", "AL", "Maceio"),
    ("Macapa", "AP", "Macapa"),
    ("Manaus", "AM", "Manaus"),
    ("Salvador", "BA", "Salvador"),
    ("Fortaleza", "CE", "Fortaleza"),
    ("Brasilia", "DF", "Brasilia"),
    ("Vitoria", "ES", "Vitoria"),
    ("Goiania", "GO", "Goiania"),
    ("Sao Luis", "MA", "Sao Luis"),
    ("Cuiaba", "MT", "Cuiaba"),
    ("Campo Grande", "MS", "Campo Grande"),
    ("Belo Horizonte", "MG", "Belo Horizonte"),
    ("Belem", "PA", "Belem"),
    ("Joao Pessoa", "PB", "Joao Pessoa"),
    ("Curitiba", "PR", "Curitiba"),
    ("Recife", "PE", "Recife"),
    ("Teresina", "PI", "Teresina"),
    ("Rio de Janeiro", "RJ", "Rio de Janeiro"),
    ("Natal", "RN", "Natal"),
    ("Porto Alegre", "RS", "Porto Alegre"),
    ("Porto Velho", "RO", "Porto Velho"),
    ("Boa Vista", "RR", "Boa Vista"),
    ("Florianopolis", "SC", "Florianopolis"),
    ("Aracaju", "SE", "Aracaju"),
    ("Sao Paulo", "SP", "Sao Paulo"),
    ("Palmas", "TO", "Palmas"),

    # ── GRANDES CIDADES (SP) ──
    ("Campinas", "SP", "Campinas"),
    ("Santos", "SP", "Santos"),
    ("Sao Bernardo do Campo", "SP", "Sao Bernardo do Campo"),
    ("Santo Andre", "SP", "Santo Andre"),
    ("Osasco", "SP", "Osasco"),
    ("Ribeirao Preto", "SP", "Ribeirao Preto"),
    ("Sorocaba", "SP", "Sorocaba"),
    ("Sao Jose dos Campos", "SP", "Sao Jose dos Campos"),
    ("Mogi das Cruzes", "SP", "Mogi das Cruzes"),
    ("Sao Jose do Rio Preto", "SP", "Sao Jose do Rio Preto"),
    ("Bauru", "SP", "Bauru"),
    ("Piracicaba", "SP", "Piracicaba"),
    ("Limeira", "SP", "Limeira"),
    ("Guarulhos", "SP", "Guarulhos"),

    # ── GRANDES CIDADES (RJ) ──
    ("Niteroi", "RJ", "Niteroi"),
    ("Nova Iguacu", "RJ", "Nova Iguacu"),
    ("Duque de Caxias", "RJ", "Duque de Caxias"),
    ("Volta Redonda", "RJ", "Volta Redonda"),
    ("Petropolis", "RJ", "Petropolis"),
    ("Macae", "RJ", "Macae"),

    # ── GRANDES CIDADES (MG) ──
    ("Uberlandia", "MG", "Uberlandia"),
    ("Contagem", "MG", "Contagem"),
    ("Juiz de Fora", "MG", "Juiz de Fora"),
    ("Betim", "MG", "Betim"),
    ("Montes Claros", "MG", "Montes Claros"),
    ("Ribeiro das Neves", "MG", "Ribeiro das Neves"),
    ("Uberaba", "MG", "Uberaba"),
    ("Governador Valadares", "MG", "Governador Valadares"),
    ("Ipatinga", "MG", "Ipatinga"),
    ("Ouro Preto", "MG", "Ouro Preto"),
    ("Diamantina", "MG", "Diamantina"),

    # ── GRANDES CIDADES (RS) ──
    ("Canoas", "RS", "Canoas"),
    ("Pelotas", "RS", "Pelotas"),
    ("Caxias do Sul", "RS", "Caxias do Sul"),
    ("Santa Maria", "RS", "Santa Maria"),
    ("Novo Hamburgo", "RS", "Novo Hamburgo"),
    ("Sao Leopoldo", "RS", "Sao Leopoldo"),
    ("Passo Fundo", "RS", "Passo Fundo"),

    # ── GRANDES CIDADES (PR) ──
    ("Londrina", "PR", "Londrina"),
    ("Maringa", "PR", "Maringa"),
    ("Ponta Grossa", "PR", "Ponta Grossa"),
    ("Cascavel", "PR", "Cascavel"),
    ("Foz do Iguacu", "PR", "Foz do Iguacu"),

    # ── GRANDES CIDADES (SC) ──
    ("Joinville", "SC", "Joinville"),
    ("Blumenau", "SC", "Blumenau"),
    ("Chapeco", "SC", "Chapeco"),
    ("Itajai", "SC", "Itajai"),
    ("Criciuma", "SC", "Criciuma"),

    # ── GRANDES CIDADES (BA) ──
    ("Feira de Santana", "BA", "Feira de Santana"),
    ("Vitoria da Conquista", "BA", "Vitoria da Conquista"),
    ("Camacari", "BA", "Camacari"),
    ("Ilheus", "BA", "Ilheus"),
    ("Itabuna", "BA", "Itabuna"),

    # ── GRANDES CIDADES (PE) ──
    ("Caruaru", "PE", "Caruaru"),
    ("Olinda", "PE", "Olinda"),
    ("Petrolina", "PE", "Petrolina"),
    ("Paulista", "PE", "Paulista"),
    ("Palmares", "PE", "Palmares"),

    # ── GRANDES CIDADES (CE) ──
    ("Caucaia", "CE", "Caucaia"),
    ("Juazeiro do Norte", "CE", "Juazeiro do Norte"),
    ("Sobral", "CE", "Sobral"),
    ("Crato", "CE", "Crato"),

    # ── GRANDES CIDADES (GO) ──
    ("Aparecida de Goiania", "GO", "Aparecida de Goiania"),
    ("Anapolis", "GO", "Anapolis"),
    ("Rio Verde", "GO", "Rio Verde"),

    # ── GRANDES CIDADES (PA) ──
    ("Ananindeua", "PA", "Ananindeua"),
    ("Santarem", "PA", "Santarem"),
    ("Maraba", "PA", "Maraba"),

    # ── GRANDES CIDADES (MA) ──
    ("Imperatriz", "MA", "Imperatriz"),
    ("Timon", "MA", "Timon"),
    ("Caxias", "MA", "Caxias"),

    # ── GRANDES CIDADES (AM) ──
    ("Parintins", "AM", "Parintins"),
    ("Itacoatiara", "AM", "Itacoatiara"),

    # ── GRANDES CIDADES (RN) ──
    ("Mossoro", "RN", "Mossoro"),
    ("Parnamirim", "RN", "Parnamirim"),

    # ── GRANDES CIDADES (AL) ──
    ("Arapiraca", "AL", "Arapiraca"),
    ("Palmeira dos Indios", "AL", "Palmeira dos Indios"),

    # ── GRANDES CIDADES (SE) ──
    ("Nossa Senhora do Socorro", "SE", "Nossa Senhora do Socorro"),
    ("Lagarto", "SE", "Lagarto"),

    # ── GRANDES CIDADES (PI) ──
    ("Parnaiba", "PI", "Parnaiba"),
    ("Picos", "PI", "Picos"),

    # ── GRANDES CIDADES (PB) ──
    ("Campina Grande", "PB", "Campina Grande"),
    ("Santa Rita", "PB", "Santa Rita"),

    # ── GRANDES CIDADES (MT) ──
    ("Rondonopolis", "MT", "Rondonopolis"),
    ("Sinop", "MT", "Sinop"),
    ("Varzea Grande", "MT", "Varzea Grande"),

    # ── GRANDES CIDADES (MS) ──
    ("Dourados", "MS", "Dourados"),
    ("Tres Lagoas", "MS", "Tres Lagoas"),
    ("Corumba", "MS", "Corumba"),

    # ── GRANDES CIDADES (ES) ──
    ("Vila Velha", "ES", "Vila Velha"),
    ("Serra", "ES", "Serra"),
    ("Cariacica", "ES", "Cariacica"),
    ("Cachoeiro de Itapemirim", "ES", "Cachoeiro de Itapemirim"),

    # ── GRANDES CIDADES (TO/RO/RR/AP/AC) ──
    ("Araguaina", "TO", "Araguaina"),
    ("Ji-Parana", "RO", "Ji-Parana"),
    ("Rorainopolis", "RR", "Rorainopolis"),
    ("Santana", "AP", "Santana"),
    ("Cruzeiro do Sul", "AC", "Cruzeiro do Sul"),
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
    print(f"=== Seed: {len(CIDADES)} Cidades Brasileiras ===\n")
    ok = 0
    erros = 0

    for i, (nome, estado, cidade) in enumerate(CIDADES, 1):
        try:
            r = post("/api/admin/institutions", {
                "name": nome,
                "type": "city",
                "state": estado,
                "city": cidade,
            }, HEADERS)
            print(f"[{i:03d}/{len(CIDADES)}] OK  {nome} | {estado}")
            ok += 1
        except Exception as e:
            print(f"[{i:03d}/{len(CIDADES)}] ERR {nome} => {e}")
            erros += 1
        time.sleep(0.03)

    print(f"\n{'='*60}")
    print(f"CONCLUIDO: {ok} cidades | {erros} erros")

    req = urllib.request.Request(BASE + "/api/institutions?type=city")
    total = len(json.loads(urllib.request.urlopen(req).read()))
    print(f"Total no banco: {total} cidades")


main()
