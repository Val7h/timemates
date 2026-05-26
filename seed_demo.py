"""
TimeMates — Seed de dados demonstração
Cria escolas fictícias, alunos, salas e mensagens para simular vida na plataforma.
Completamente idempotente: não duplica se já existir.
"""
import hashlib, uuid
from datetime import datetime, timedelta
import random

DEMO_TAG = "DEMO_SEED_V3"   # marca no e-mail para identificar registros demo

# ── Instituições fictícias ────────────────────────────────────────────────────
SCHOOLS = [
    {"name": "Escola Estadual João Pessoa",       "state": "SP", "city": "São Paulo"},
    {"name": "Colégio Municipal Tiradentes",       "state": "MG", "city": "Belo Horizonte"},
    {"name": "Escola Estadual Getúlio Vargas",     "state": "RJ", "city": "Rio de Janeiro"},
    {"name": "Colégio Estadual Dom Pedro II",      "state": "PR", "city": "Curitiba"},
    {"name": "Instituto Estadual de Educação",     "state": "RS", "city": "Porto Alegre"},
    {"name": "Escola Municipal Santos Dumont",     "state": "BA", "city": "Salvador"},
]

# ── Universidades fictícias ───────────────────────────────────────────────────
UNIVERSITIES = [
    {"name": "Universidade Federal de Minas Gerais — UFMG", "state": "MG", "city": "Belo Horizonte"},
    {"name": "Universidade de São Paulo — USP",              "state": "SP", "city": "São Paulo"},
    {"name": "PUC-Rio",                                      "state": "RJ", "city": "Rio de Janeiro"},
    {"name": "Universidade Federal do Paraná — UFPR",        "state": "PR", "city": "Curitiba"},
    {"name": "UFRGS — Universidade Federal do Rio Grande do Sul", "state": "RS", "city": "Porto Alegre"},
    {"name": "Universidade Federal da Bahia — UFBA",         "state": "BA", "city": "Salvador"},
    {"name": "UNICAMP — Universidade Estadual de Campinas",  "state": "SP", "city": "Campinas"},
    {"name": "Universidade de Brasília — UnB",               "state": "DF", "city": "Brasília"},
]

UNIVERSITY_ROOM_TEMPLATES = [
    (2005, "Engenharia Civil — Turma 2005"),
    (2008, "Medicina — Turma 2008"),
    (2010, "Ciência da Computação — Turma 2010"),
    (2012, "Direito — Turma 2012"),
    (2015, "Administração — Turma 2015"),
    (2018, "Psicologia — Turma 2018"),
    (2007, "Arquitetura e Urbanismo — 2007"),
    (2011, "Engenharia Elétrica — 2011"),
]

UNIVERSITY_MESSAGES = [
    "Alguém lembra do RU? A fila era enorme mas valia! 😂",
    "A semana de calouros foi o melhor começo de vida que eu poderia ter.",
    "Que saudade das madrugadas de TCC na biblioteca...",
    "Ainda tenho a caneca do CA guardada aqui em casa 🙏",
    "A república da galera ainda existe? Alguém sabe?",
    "Quem lembra do professor que dormia na própria aula? 😂",
    "Esse curso mudou minha vida completamente.",
    "Quem foi pra semana acadêmica de 2013?",
    "Saudade do xis da cantina por R$2,00 haha",
    "A greve de 2011 foi difícil mas fortaleceu muito a turma.",
    "Pessoal, tem reunião de ex-alunos esse ano?",
    "Não acredito que encontrei vocês aqui! Que plataforma incrível!",
    "Formamos juntos e a vida nos separou... mas nunca esqueci ninguém ❤️",
    "Quem ainda fala com o Zé Carlos da sala B?",
    "Minha melhor época foi a graduação, sem dúvida.",
]

# ── Empresas fictícias ───────────────────────────────────────────────────────
COMPANIES = [
    {"name": "Construtora Horizonte",         "state": "SP", "city": "São Paulo",        "sector": "Construção Civil"},
    {"name": "TechSul Sistemas",              "state": "RS", "city": "Porto Alegre",     "sector": "Tecnologia"},
    {"name": "Banco Meridional",              "state": "RJ", "city": "Rio de Janeiro",   "sector": "Financeiro"},
    {"name": "Supermercados Bom Preço",       "state": "MG", "city": "Belo Horizonte",   "sector": "Varejo"},
    {"name": "Clínica São Lucas",             "state": "PR", "city": "Curitiba",         "sector": "Saúde"},
    {"name": "Agência Criativa NordBrand",    "state": "BA", "city": "Salvador",         "sector": "Marketing"},
    {"name": "Transportadora Rota Sul",       "state": "SC", "city": "Florianópolis",    "sector": "Logística"},
    {"name": "Escola de Idiomas GlobalTalk",  "state": "GO", "city": "Goiânia",          "sector": "Educação"},
]

# ── Turmas de empresa (por período de trabalho) ───────────────────────────────
COMPANY_ROOM_TEMPLATES = [
    (2008, "Turno da Manhã — Setor Administrativo"),
    (2010, "Equipe de Vendas"),
    (2013, "TI & Suporte"),
    (2015, "Recursos Humanos"),
    (2018, "Operações"),
    (2020, "Equipe Remota"),
]

# ── Mensagens de empresa ──────────────────────────────────────────────────────
COMPANY_MESSAGES = [
    "Saudade da galera do escritório! 🥹",
    "Quem lembra do cafezinho das 10h? ☕",
    "Aquele happy hour de sexta-feira era imperdível!",
    "Oi pessoal! Que surpresa boa te encontrar aqui!",
    "Os melhores anos da minha carreira foram lá.",
    "Ainda guardo aquela caneca da empresa hahaha",
    "O RH era tão animado naquela época!",
    "Alguém sabe onde está o pessoal do setor 3?",
    "Que time incrível a gente formou! Saudades 💙",
    "Ainda me lembro do treinamento de integração...",
    "A festa de fim de ano de 2015 foi épica!",
    "Alguém ainda fala com a gerente Maria José?",
    "Quantas histórias naquele lugar...",
    "Trabalhei lá por 5 anos, os melhores da vida.",
    "Vamos marcar um almoço de ex-funcionários!",
]

# ── Alunos fictícios ──────────────────────────────────────────────────────────
STUDENTS = [
    ("Ana Clara Silva",       "anaclara",   "SP", "Professora"),
    ("Pedro Henrique Santos", "pedrohs",    "MG", "Engenheiro"),
    ("Mariana Oliveira",      "mariana.o",  "RJ", "Designer"),
    ("Lucas Ferreira",        "lucasf",     "PR", "Desenvolvedor"),
    ("Fernanda Costa",        "fercosta",   "RS", "Médica"),
    ("Rafael Souza",          "rafaels",    "BA", "Advogado"),
    ("Juliana Alves",         "julianaa",   "SP", "Enfermeira"),
    ("Rodrigo Lima",          "rodlima",    "MG", "Contador"),
    ("Camila Pereira",        "camipereira","RJ", "Arquiteta"),
    ("Bruno Martins",         "brunomartins","PR","Veterinário"),
    ("Letícia Rodrigues",     "leticiar",   "RS", "Psicóloga"),
    ("Gabriel Carvalho",      "gabrielc",   "BA", "Jornalista"),
    ("Amanda Nascimento",     "amandn",     "SP", "Fisioterapeuta"),
    ("Thiago Barbosa",        "thiagob",    "MG", "Administrador"),
    ("Isabella Gomes",        "isabgomes",  "RJ", "Nutricionista"),
    ("Felipe Araújo",         "felipear",   "PR", "Mecânico"),
    ("Natália Duarte",        "nataliad",   "RS", "Bióloga"),
    ("Vinícius Rocha",        "vinirochat", "BA", "Economista"),
    ("Beatriz Mendes",        "beamendes",  "SP", "Farmacêutica"),
    ("Diego Castro",          "diegoc",     "MG", "Professor"),
    # Funcionários de empresa
    ("Carlos Eduardo Pinto",  "carlosedu",  "SP", "Analista Financeiro"),
    ("Priscila Mota",         "priscilam",  "RS", "Gerente de Projetos"),
    ("Henrique Tavares",      "henriquet",  "RJ", "Desenvolvedor Sênior"),
    ("Sabrina Leal",          "sabrinal",   "MG", "Coordenadora de RH"),
    ("Fábio Nunes",           "fabionunes", "PR", "Supervisor de Vendas"),
    ("Denise Queiroz",        "denisequei", "BA", "Analista de Marketing"),
    ("Maurício Freitas",      "mauriciof",  "SC", "Gerente Operacional"),
    ("Renata Borges",         "renatab",    "GO", "Assistente Administrativo"),
    ("Leandro Campos",        "leandrocam", "SP", "Técnico de TI"),
    ("Tatiana Assis",         "tatianaa",   "RS", "Consultora de Negócios"),
    ("Marcelo Fontes",        "marcelof",   "RJ", "Diretor Comercial"),
    ("Viviane Correia",       "vivianec",   "MG", "Especialista em Logística"),
]

# ── Turmas por escola ─────────────────────────────────────────────────────────
ROOM_TEMPLATES = [
    (2000, "Turma A"),
    (2003, "Turma B"),
    (2006, "Sala do Fundão"),
    (2010, "Turma C"),
    (2014, "Última Turma"),
]

# ── Mensagens de exemplo ──────────────────────────────────────────────────────
MESSAGES_POOL = [
    "Gente, que saudade dessa época! 🥹",
    "Lembro de tudo como se fosse ontem...",
    "Quem lembra do recreio? A melhor parte do dia!",
    "Oi pessoal! Não acredito que achei vocês aqui!",
    "Esses anos foram os melhores da minha vida 🙏",
    "Alguém ainda fala com o professor de matemática?",
    "A cantina tinha o melhor pastel do mundo 😂",
    "Que saudade das viagens de intercâmbio!",
    "Quem vai à reunião de ex-alunos esse ano?",
    "Finalmente um lugar pra nos reunirmos de novo!",
    "Alguém tem foto daquela festa junina de 2005?",
    "Eu morava do lado da escola, lembram?",
    "Que época boa... crescemos muito juntos ❤️",
    "Todo mundo sumiu depois que formou haha",
    "Precisamos marcar um almoço galera!",
]


def _hash_pw(password: str) -> str:
    from passlib.context import CryptContext
    return CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto").hash(password)


def seed_demo(db):
    from database import User, Institution, Room, RoomMembership, Message

    already_universities = db.query(Institution).filter(
        Institution.name == "PUC-Rio", Institution.type == "university"
    ).first()

    already_companies = db.query(Institution).filter(
        Institution.name == "Construtora Horizonte", Institution.type == "company"
    ).first()

    # Verifica se demo de escolas já foi criado
    already_schools = db.query(User).filter(User.email.like("%@demo.timemates%")).count()
    if already_schools > 0 and already_companies and already_universities:
        print("[DEMO] Seed demo completo já existe, pulando.")
        return

    print("[DEMO] Criando dados de demonstração...")

    pw_hash = _hash_pw("demo123456")

    # 1. Cria escolas
    school_objs = []
    for s in SCHOOLS:
        existing = db.query(Institution).filter(
            Institution.name == s["name"], Institution.type == "school"
        ).first()
        if not existing:
            inst = Institution(
                name=s["name"], type="school",
                state=s["state"], city=s["city"],
                approved=True,
            )
            db.add(inst)
            db.flush()
            school_objs.append(inst)
        else:
            school_objs.append(existing)
    db.commit()
    print(f"[DEMO] {len(school_objs)} escolas OK")

    # 2. Cria usuários demo
    user_objs = []
    for i, (name, handle, state, prof) in enumerate(STUDENTS):
        email = f"{handle}@demo.timemates"
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            user_objs.append(existing)
            continue
        cpf_hash = hashlib.sha256(f"demo-{uuid.uuid4()}".encode()).hexdigest()
        u = User(
            full_name=name,
            email=email,
            password_hash=pw_hash,
            cpf_hash=cpf_hash,
            city=state,
            profession=prof,
            show_city=True,
            show_profession=True,
            is_active=True,
        )
        db.add(u)
        db.flush()
        user_objs.append(u)
    db.commit()
    print(f"[DEMO] {len(user_objs)} alunos OK")

    # 3. Cria salas e popula com alunos + mensagens
    rng = random.Random(42)  # seed fixo = resultado determinístico

    for school in school_objs:
        # 2-4 turmas por escola
        templates = rng.sample(ROOM_TEMPLATES, k=rng.randint(2, 4))
        for year, group_name in templates:
            # Verifica se a sala já existe
            existing_room = db.query(Room).filter(
                Room.institution_id == school.id,
                Room.year == year,
                Room.group_name == group_name,
            ).first()
            if existing_room:
                continue

            # Escolhe ADM da sala (primeiro aluno sorteado)
            members_sample = rng.sample(user_objs, k=rng.randint(5, 12))
            admin_user = members_sample[0]

            room = Room(
                institution_id=school.id,
                year=year,
                group_name=group_name,
                created_by_id=admin_user.id,
                created_at=datetime.utcnow() - timedelta(days=rng.randint(1, 120)),
            )
            db.add(room)
            db.flush()

            # Adiciona membros
            for j, u in enumerate(members_sample):
                role = "admin" if j == 0 else "member"
                membership = RoomMembership(
                    room_id=room.id,
                    user_id=u.id,
                    role=role,
                    status="approved",
                    approved_at=datetime.utcnow() - timedelta(days=rng.randint(0, 90)),
                )
                db.add(membership)

            db.flush()

            # Adiciona mensagens
            msgs = rng.sample(MESSAGES_POOL, k=rng.randint(4, 8))
            base_time = datetime.utcnow() - timedelta(days=rng.randint(0, 30))
            for k, content in enumerate(msgs):
                author = rng.choice(members_sample)
                msg = Message(
                    room_id=room.id,
                    user_id=author.id,
                    content=content,
                    created_at=base_time + timedelta(hours=k * rng.randint(1, 6)),
                )
                db.add(msg)

    db.commit()
    print("[DEMO] Escolas: salas, membros e mensagens OK")

    # ── 4. Universidades ──────────────────────────────────────────────────────
    if not already_universities:
        univ_objs = []
        for u_data in UNIVERSITIES:
            existing = db.query(Institution).filter(
                Institution.name == u_data["name"], Institution.type == "university"
            ).first()
            if not existing:
                inst = Institution(
                    name=u_data["name"], type="university",
                    state=u_data["state"], city=u_data["city"],
                    approved=True,
                )
                db.add(inst)
                db.flush()
                univ_objs.append(inst)
            else:
                univ_objs.append(existing)
        db.commit()
        print(f"[DEMO] {len(univ_objs)} universidades criadas")

        for univ in univ_objs:
            templates = rng.sample(UNIVERSITY_ROOM_TEMPLATES, k=rng.randint(3, 5))
            for year, group_name in templates:
                existing_room = db.query(Room).filter(
                    Room.institution_id == univ.id,
                    Room.year == year, Room.group_name == group_name,
                ).first()
                if existing_room:
                    continue
                members_sample = rng.sample(user_objs, k=rng.randint(8, 16))
                room = Room(
                    institution_id=univ.id, year=year, group_name=group_name,
                    created_by_id=members_sample[0].id,
                    created_at=datetime.utcnow() - timedelta(days=rng.randint(1, 200)),
                )
                db.add(room)
                db.flush()
                for j, u in enumerate(members_sample):
                    db.add(RoomMembership(
                        room_id=room.id, user_id=u.id,
                        role="admin" if j == 0 else "member",
                        status="approved",
                        approved_at=datetime.utcnow() - timedelta(days=rng.randint(0, 150)),
                    ))
                msgs = rng.sample(UNIVERSITY_MESSAGES, k=rng.randint(6, 12))
                base_time = datetime.utcnow() - timedelta(days=rng.randint(0, 45))
                for k, content in enumerate(msgs):
                    db.add(Message(
                        room_id=room.id,
                        user_id=rng.choice(members_sample).id,
                        content=content,
                        created_at=base_time + timedelta(hours=k * rng.randint(1, 10)),
                    ))
        db.commit()
        print("[DEMO] Salas de universidade OK")

    # ── 5. Empresas ───────────────────────────────────────────────────────────
    if not already_companies:
        company_objs = []
        for c in COMPANIES:
            existing = db.query(Institution).filter(
                Institution.name == c["name"], Institution.type == "company"
            ).first()
            if not existing:
                inst = Institution(
                    name=c["name"], type="company",
                    state=c["state"], city=c["city"],
                    sector=c.get("sector"),
                    approved=True,
                )
                db.add(inst)
                db.flush()
                company_objs.append(inst)
            else:
                company_objs.append(existing)
        db.commit()
        print(f"[DEMO] {len(company_objs)} empresas criadas")

        # Adiciona funcionários extras que ainda não existem
        all_users = db.query(User).filter(User.email.like("%@demo.timemates%")).all()
        for name, handle, state, prof in STUDENTS[20:]:  # pega os funcionários novos
            email = f"{handle}@demo.timemates"
            if not any(u.email == email for u in all_users):
                cpf_hash = hashlib.sha256(f"demo-{uuid.uuid4()}".encode()).hexdigest()
                u = User(
                    full_name=name, email=email,
                    password_hash=pw_hash, cpf_hash=cpf_hash,
                    city=state, profession=prof,
                    show_city=True, show_profession=True, is_active=True,
                )
                db.add(u)
                db.flush()
                all_users.append(u)
        db.commit()

        # Cria salas de empresa com funcionários e mensagens
        for company in company_objs:
            templates = rng.sample(COMPANY_ROOM_TEMPLATES, k=rng.randint(2, 4))
            for year, group_name in templates:
                existing_room = db.query(Room).filter(
                    Room.institution_id == company.id,
                    Room.year == year,
                    Room.group_name == group_name,
                ).first()
                if existing_room:
                    continue

                members_sample = rng.sample(all_users, k=rng.randint(6, 14))
                admin_user = members_sample[0]

                room = Room(
                    institution_id=company.id,
                    year=year, group_name=group_name,
                    created_by_id=admin_user.id,
                    created_at=datetime.utcnow() - timedelta(days=rng.randint(1, 180)),
                )
                db.add(room)
                db.flush()

                for j, u in enumerate(members_sample):
                    db.add(RoomMembership(
                        room_id=room.id, user_id=u.id,
                        role="admin" if j == 0 else "member",
                        status="approved",
                        approved_at=datetime.utcnow() - timedelta(days=rng.randint(0, 120)),
                    ))

                msgs = rng.sample(COMPANY_MESSAGES, k=rng.randint(5, 10))
                base_time = datetime.utcnow() - timedelta(days=rng.randint(0, 60))
                for k, content in enumerate(msgs):
                    db.add(Message(
                        room_id=room.id,
                        user_id=rng.choice(members_sample).id,
                        content=content,
                        created_at=base_time + timedelta(hours=k * rng.randint(1, 8)),
                    ))

        db.commit()
        print("[DEMO] Salas de empresa, membros e mensagens OK")

    print("[DEMO] Seed demo concluído ✅")
