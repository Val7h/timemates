"""
Script de seed — Universidades Federais do Brasil
69 IFES (Instituições Federais de Ensino Superior)
"""
import urllib.request, urllib.parse, json, time, sys

BASE = "http://localhost:8765"
EMAIL = "teste@email.com"
PASSWORD = "123456"

UNIVERSIDADES = [
    # ACRE
    ("Universidade Federal do Acre (UFAC)", "AC", "Rio Branco"),
    # ALAGOAS
    ("Universidade Federal de Alagoas (UFAL)", "AL", "Maceió"),
    # AMAPÁ
    ("Universidade Federal do Amapá (UNIFAP)", "AP", "Macapá"),
    # AMAZONAS
    ("Universidade Federal do Amazonas (UFAM)", "AM", "Manaus"),
    # BAHIA
    ("Universidade Federal da Bahia (UFBA)", "BA", "Salvador"),
    ("Universidade Federal do Recôncavo da Bahia (UFRB)", "BA", "Cruz das Almas"),
    ("Universidade Federal do Oeste da Bahia (UFOB)", "BA", "Barreiras"),
    ("Universidade Federal do Sul da Bahia (UFSB)", "BA", "Itabuna"),
    # CEARÁ
    ("Universidade Federal do Ceará (UFC)", "CE", "Fortaleza"),
    ("Universidade Federal do Cariri (UFCA)", "CE", "Juazeiro do Norte"),
    ("Universidade da Integração Internacional da Lusofonia Afro-Brasileira (UNILAB)", "CE", "Redenção"),
    # DISTRITO FEDERAL
    ("Universidade de Brasília (UnB)", "DF", "Brasília"),
    # ESPÍRITO SANTO
    ("Universidade Federal do Espírito Santo (UFES)", "ES", "Vitória"),
    # GOIÁS
    ("Universidade Federal de Goiás (UFG)", "GO", "Goiânia"),
    ("Universidade Federal de Catalão (UFCAT)", "GO", "Catalão"),
    ("Universidade Federal de Jataí (UFJ)", "GO", "Jataí"),
    # MARANHÃO
    ("Universidade Federal do Maranhão (UFMA)", "MA", "São Luís"),
    # MATO GROSSO
    ("Universidade Federal de Mato Grosso (UFMT)", "MT", "Cuiabá"),
    # MATO GROSSO DO SUL
    ("Universidade Federal de Mato Grosso do Sul (UFMS)", "MS", "Campo Grande"),
    ("Universidade Federal da Grande Dourados (UFGD)", "MS", "Dourados"),
    # MINAS GERAIS
    ("Universidade Federal de Minas Gerais (UFMG)", "MG", "Belo Horizonte"),
    ("Universidade Federal de Viçosa (UFV)", "MG", "Viçosa"),
    ("Universidade Federal de Juiz de Fora (UFJF)", "MG", "Juiz de Fora"),
    ("Universidade Federal de Ouro Preto (UFOP)", "MG", "Ouro Preto"),
    ("Universidade Federal de Lavras (UFLA)", "MG", "Lavras"),
    ("Universidade Federal de Alfenas (UNIFAL-MG)", "MG", "Alfenas"),
    ("Universidade Federal de Itajubá (UNIFEI)", "MG", "Itajubá"),
    ("Universidade Federal de São João del-Rei (UFSJ)", "MG", "São João del-Rei"),
    ("Universidade Federal do Triângulo Mineiro (UFTM)", "MG", "Uberaba"),
    ("Universidade Federal dos Vales do Jequitinhonha e Mucuri (UFVJM)", "MG", "Diamantina"),
    ("Universidade Federal de Uberlândia (UFU)", "MG", "Uberlândia"),
    # PARÁ
    ("Universidade Federal do Pará (UFPA)", "PA", "Belém"),
    ("Universidade Federal Rural da Amazônia (UFRA)", "PA", "Belém"),
    ("Universidade Federal do Oeste do Pará (UFOPA)", "PA", "Santarém"),
    ("Universidade Federal do Sul e Sudeste do Pará (UNIFESSPA)", "PA", "Marabá"),
    # PARAÍBA
    ("Universidade Federal da Paraíba (UFPB)", "PB", "João Pessoa"),
    ("Universidade Federal de Campina Grande (UFCG)", "PB", "Campina Grande"),
    # PARANÁ
    ("Universidade Federal do Paraná (UFPR)", "PR", "Curitiba"),
    ("Universidade Tecnológica Federal do Paraná (UTFPR)", "PR", "Curitiba"),
    ("Universidade Federal da Integração Latino-Americana (UNILA)", "PR", "Foz do Iguaçu"),
    # PERNAMBUCO
    ("Universidade Federal de Pernambuco (UFPE)", "PE", "Recife"),
    ("Universidade Federal Rural de Pernambuco (UFRPE)", "PE", "Recife"),
    ("Universidade Federal do Vale do São Francisco (UNIVASF)", "PE", "Petrolina"),
    ("Universidade Federal do Agreste de Pernambuco (UFAPE)", "PE", "Garanhuns"),
    # PIAUÍ
    ("Universidade Federal do Piauí (UFPI)", "PI", "Teresina"),
    ("Universidade Federal do Delta do Parnaíba (UFDPar)", "PI", "Parnaíba"),
    # RIO DE JANEIRO
    ("Universidade Federal do Rio de Janeiro (UFRJ)", "RJ", "Rio de Janeiro"),
    ("Universidade Federal Fluminense (UFF)", "RJ", "Niterói"),
    ("Universidade Federal do Estado do Rio de Janeiro (UNIRIO)", "RJ", "Rio de Janeiro"),
    ("Universidade Federal Rural do Rio de Janeiro (UFRRJ)", "RJ", "Seropédica"),
    # RIO GRANDE DO NORTE
    ("Universidade Federal do Rio Grande do Norte (UFRN)", "RN", "Natal"),
    ("Universidade Federal Rural do Semi-Árido (UFERSA)", "RN", "Mossoró"),
    # RIO GRANDE DO SUL
    ("Universidade Federal do Rio Grande do Sul (UFRGS)", "RS", "Porto Alegre"),
    ("Universidade Federal de Santa Maria (UFSM)", "RS", "Santa Maria"),
    ("Universidade Federal do Rio Grande (FURG)", "RS", "Rio Grande"),
    ("Universidade Federal de Pelotas (UFPEL)", "RS", "Pelotas"),
    ("Universidade Federal de Ciências da Saúde de Porto Alegre (UFCSPA)", "RS", "Porto Alegre"),
    ("Universidade Federal do Pampa (UNIPAMPA)", "RS", "Bagé"),
    # RONDÔNIA
    ("Fundação Universidade Federal de Rondônia (UNIR)", "RO", "Porto Velho"),
    # RORAIMA
    ("Universidade Federal de Roraima (UFRR)", "RR", "Boa Vista"),
    # SANTA CATARINA
    ("Universidade Federal de Santa Catarina (UFSC)", "SC", "Florianópolis"),
    ("Universidade Federal da Fronteira Sul (UFFS)", "SC", "Chapecó"),
    # SERGIPE
    ("Universidade Federal de Sergipe (UFS)", "SE", "São Cristóvão"),
    # SÃO PAULO
    ("Universidade Federal de São Carlos (UFSCar)", "SP", "São Carlos"),
    ("Universidade Federal de São Paulo (UNIFESP)", "SP", "São Paulo"),
    ("Universidade Federal do ABC (UFABC)", "SP", "Santo André"),
    # TOCANTINS
    ("Universidade Federal do Tocantins (UFT)", "TO", "Palmas"),
    ("Universidade Federal do Norte do Tocantins (UFNT)", "TO", "Araguaína"),
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
    print("=== Seed: Universidades Federais do Brasil ===\n")

    # Login
    print("Fazendo login como admin...")
    r = post("/api/auth/login", {"email": EMAIL, "password": PASSWORD})
    token = r["access_token"]
    user = r["user"]
    if not user["is_system_admin"]:
        print("ERRO: Usuário não é admin do sistema!")
        sys.exit(1)
    print(f"Logado como: {user['full_name']} (Admin: {user['is_system_admin']})\n")

    headers = {"Authorization": f"Bearer {token}"}
    ok = 0
    erros = 0

    for i, (nome, estado, cidade) in enumerate(UNIVERSIDADES, 1):
        try:
            r = post("/api/admin/institutions", {
                "name": nome,
                "type": "university",
                "state": estado,
                "city": cidade,
            }, headers)
            print(f"[{i:02d}/{len(UNIVERSIDADES)}] OK  {nome[:60]} - {cidade}/{estado}")
            ok += 1
        except Exception as e:
            print(f"[{i:02d}/{len(UNIVERSIDADES)}] ERR {nome[:50]} - {e}")
            erros += 1
        time.sleep(0.05)  # não sobrecarregar o servidor

    print(f"\n{'='*50}")
    print(f"Concluído: {ok} adicionadas | {erros} erros")
    print(f"Total de universidades federais cadastradas: {ok}")

if __name__ == "__main__":
    main()
