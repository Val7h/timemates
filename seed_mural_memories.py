"""Seed 5 memorias sensoriais por cada uma das 30 turmas.

Templates por tipo (memory_type):
- smell (cheiro): cantina, mimeografo, giz molhado, cafe da prof, livro velho
- sound (som): sinal do recreio, cadeira arrastando, professor batendo na mesa
- place (lugar): bebedouro, patio, biblioteca, quadra, escadaria
- person (pessoa): inspetor, diretor lendario, professora marcante
- event (evento): festa junina, gincana, formatura, excursao
- taste (sabor): salgadinho da cantina, sucao de saquinho, sanduiche
- gesture (gesto): toque de sirene, apito de educacao fisica

Para cada turma, gera 5 memorias variadas usando context da escola.
Sistema autor: 'TimeMates Anchor' (user fake id 1 = founder Valth)."""

import time
import random
from database import SessionLocal, Turma, MuralMemory


# ─────────────────────────────────────────────────────────────────────
# Templates genericos (com placeholders {year} e {city} quando relevante)
# ─────────────────────────────────────────────────────────────────────

SMELL_TEMPLATES = [
    "O cheiro do mimeografo na prova de historia — a folha sempre saia umida e azul",
    "O cheiro da cantina no recreio: pao na chapa, cafe queimado e oleo do salgado",
    "O cheiro do giz molhado depois que a faxineira passava o pano na lousa",
    "O cheiro de livro velho da biblioteca, aquele perfume de pagina amarelada",
    "O cheiro do cafe da sala dos professores escapando pela porta entreaberta",
    "O cheiro de borracha nova no comeco do ano, junto com caderno aberto pela primeira vez",
    "O cheiro de sabao rosa do banheiro da escola, marca registrada de toda turma {year}",
]

SOUND_TEMPLATES = [
    "O sinal do recreio as 15h15 — a corrida pra pegar fila no salgado antes de acabar",
    "O barulho de cadeira arrastando quando o professor saia da sala",
    "O professor batendo a chave na mesa pra todo mundo calar a boca",
    "O som do apagador batendo na lousa antes da chamada",
    "O eco do nosso grito no patio coberto na hora do intervalo",
    "O som da chuva no telhado de zinco do galpao da quadra, em dia de prova",
    "A risada da turma {year} ecoando no corredor depois que alguem caiu",
]

PLACE_TEMPLATES = [
    "O bebedouro do fundo do patio, sempre com a aguinha mais gelada da escola",
    "A escadaria do patio onde a turma {year} toda fotografava no ultimo dia de aula",
    "A biblioteca silenciosa que viramos ponto de encontro pra colar trabalho de grupo",
    "A quadra coberta onde rolava o futsal da quinta-feira que parou o colegio inteiro",
    "O cantinho atras do refeitorio onde a galera ia esconder durante a chamada",
    "A sala 7 do segundo andar, com aquela janela enorme dando pra rua de {city}",
    "O muro do fundo, riscado com declaracao de amor de cada turma desde os anos 90",
]

PERSON_TEMPLATES = [
    "O inspetor que ja sabia o nome de toda a turma {year} de cor — chegava antes da gente",
    "A Dona Marlene, professora de matematica que ninguem entendia mas todos amavam",
    "O diretor lendario que parava no corredor pra contar piada antes da prova final",
    "A tia da cantina que separava o salgado pra galera da turma {year} antes de abrir a fila",
    "O professor de historia que tirava o sapato pra dar aula sentado na mesa",
    "A coordenadora que sempre sabia exatamente quem foi o autor do bilhete",
    "O porteiro de {city} que abria o portao 10 minutos antes pra galera que vinha de longe",
]

EVENT_TEMPLATES = [
    "A festa junina de {year}, quadrilha no patio e bandeirinha presa com fita crepe",
    "A gincana da turma {year} que virou madrugada — ninguem queria ir pra casa",
    "A formatura no auditorio: cadeira branca, discurso emocionado e abraco apertado",
    "A excursao pra Brotas em {year} — chuva no rafting e ninguem saiu da agua",
    "O ultimo dia de aula com farinha, ovo e o uniforme que nunca mais voltou ao normal",
    "O intercolegial em {city}: a torcida da turma {year} mais alta que a do time",
    "O trote do primeiro ano: a turma {year} marcada com batom roxo no rosto",
]

TASTE_TEMPLATES = [
    "O salgadinho da cantina — coxinha pequena por 50 centavos e suco de saquinho gelado",
    "O sucao de saquinho roxo que pintava a lingua inteira ate o fim da tarde",
    "O sanduiche da merenda escolar com aquele queijo derretido grudando no papel",
    "O biscoito de polvilho seco da cantina, vendido em pacote de papel pardo",
    "A pipoca doce da quermesse da escola, queimada na borda do tacho",
    "O bolo de fuba que a Dona da cantina fazia toda sexta — desaparecia em 10 minutos",
    "A bala juquinha trocada em moeda secreta no fundo da sala de {city}",
]

GESTURE_TEMPLATES = [
    "O toque de sirene tres vezes seguidas no fim da prova — todo mundo levantava junto",
    "O apito do professor de educacao fisica chamando pra formar duas filas no patio",
    "O bater de palmas da diretora chamando atencao no patio da escola",
    "O gesto da professora de portugues fechando o livro: sinal que ia cair na prova",
    "O movimento da turma {year} se levantando junto quando o professor entrava",
    "O aceno do porteiro de {city} no portao, despedida diaria as 17h30",
    "A mao do colega passando a cola dobrada em quatro por baixo da carteira",
]

TEMPLATE_BANK = [
    ("smell", SMELL_TEMPLATES),
    ("sound", SOUND_TEMPLATES),
    ("place", PLACE_TEMPLATES),
    ("person", PERSON_TEMPLATES),
    ("event", EVENT_TEMPLATES),
    ("taste", TASTE_TEMPLATES),
    ("gesture", GESTURE_TEMPLATES),
]


# ─────────────────────────────────────────────────────────────────────
# Contextualizacoes por cidade/escola (sutil — so adiciona sabor local)
# ─────────────────────────────────────────────────────────────────────

CITY_FLAVOR = {
    "São Paulo": [
        "O cinza da Av. Paulista vista da janela da sala de aula",
        "O bandejao do RU enchendo o saguao de cheiro de arroz com feijao",
    ],
    "Rio de Janeiro": [
        "O calor de fevereiro entrando pela janela e o ventilador de teto que nao dava conta",
        "O som do mar batendo longe quando o silencio caia no patio",
    ],
    "Belo Horizonte": [
        "O pao de queijo quentinho da cantina, marca de toda manha de BH",
        "A neblina cobrindo a Serra do Curral vista do patio do colegio",
    ],
    "Juiz de Fora": [
        "O frio do mineirinho no inverno entrando pela porta dos fundos",
        "O bonde apitando la fora enquanto a aula de matematica nao terminava",
    ],
    "Londrina": [
        "O por do sol vermelho de Londrina pintando a janela da sala no inverno",
        "O cheiro de cafe da fazenda chegando ate o portao da escola",
    ],
    "Caxias do Sul": [
        "O frio cortante do inverno gaucho secando a chuva na janela",
        "O cheiro de erva-mate vindo do chimarrao do servente",
    ],
    "Salvador": [
        "O sol de Salvador entrando pela janela e o ventilador girando sem parar",
        "O som do berimbau ensaiando a quadra ao lado em dia de festa",
    ],
    "Recife": [
        "O calor umido de Recife colando o uniforme no corpo logo de manha",
        "O frevo tocando no radio da cantina na semana do Sao Joao",
    ],
    "Porto Alegre": [
        "O minuano gelado entrando pelo patio descoberto no inverno",
        "O chimarrao do porteiro circulando entre os professores no recreio",
    ],
    "Curitiba": [
        "A garoa fina e constante que nao parava nem na hora do recreio",
        "O cheiro de pinhao cozinhando na cantina em junho",
    ],
    "Brasília": [
        "O ceu azul absurdo de Brasilia visto do patio sem parede",
        "O por do sol vermelho de Brasilia atravessando a sala da ultima aula",
    ],
}


def fill_template(text, turma):
    """Substitui placeholders {year} e {city}."""
    return text.replace("{year}", str(turma.cohort_year)).replace("{city}", turma.city or "")


def generate_memories_for_turma(turma):
    """Gera 5 memorias variadas, uma de cada tipo + 1 com flavor da cidade."""
    rng = random.Random(turma.id)  # determinista por turma (re-rodar nao bagunca)

    # 1) Escolhe 4 tipos distintos pra ter variedade
    chosen_types = rng.sample(TEMPLATE_BANK, k=4)
    memories = []
    for mtype, pool in chosen_types:
        tpl = rng.choice(pool)
        memories.append({
            "memory_type": mtype,
            "content": fill_template(tpl, turma),
            "tags": [mtype, str(turma.cohort_year), (turma.city or "").lower().replace(" ", "-")],
        })

    # 2) Quinta memoria: flavor local (sempre que tiver), senao pega +1 generica
    city_pool = CITY_FLAVOR.get(turma.city)
    if city_pool:
        flavor_text = rng.choice(city_pool)
        # tipo "place" por padrao pra flavor local
        memories.append({
            "memory_type": "place",
            "content": fill_template(flavor_text, turma),
            "tags": ["place", str(turma.cohort_year), (turma.city or "").lower().replace(" ", "-"), "local"],
        })
    else:
        # fallback: outra memoria generica
        mtype, pool = rng.choice(TEMPLATE_BANK)
        memories.append({
            "memory_type": mtype,
            "content": fill_template(rng.choice(pool), turma),
            "tags": [mtype, str(turma.cohort_year)],
        })

    return memories


def seed():
    db = SessionLocal()
    t0 = time.time()
    try:
        turmas = db.query(Turma).all()
        inserted = 0
        turmas_touched = 0
        for t in turmas:
            existing = db.query(MuralMemory).filter(MuralMemory.turma_id == t.id).count()
            if existing >= 3:
                continue
            memories = generate_memories_for_turma(t)
            # Author: founder se existir, senao user 1 (anchor system author)
            author_id = t.founder_id or 1
            for m in memories:
                db.add(MuralMemory(
                    turma_id=t.id,
                    user_id=author_id,
                    memory_type=m["memory_type"],
                    content=m["content"],
                    tags=m.get("tags", []),
                    in_memoriam=False,
                ))
                inserted += 1
            turmas_touched += 1
        db.commit()
        elapsed = round(time.time() - t0, 2)
        return {
            "inserted": inserted,
            "turmas_touched": turmas_touched,
            "elapsed_seconds": elapsed,
        }
    finally:
        db.close()


if __name__ == "__main__":
    result = seed()
    print(result)
