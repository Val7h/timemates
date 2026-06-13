"""Seed das 30 turmas iniciais - colégios brasileiros tradicionais.
Foco: cidades-mãe da Phase 1 estratégia (JF, Londrina, Caxias) + capitais
com forte identidade escolar (SP, RJ, BH, Salvador, Recife)."""

from datetime import datetime
from sqlalchemy.orm import Session
from database import SessionLocal, Turma

SEED_TURMAS = [
    # === SAO PAULO ===
    {"institution_name": "Colégio Bandeirantes", "city": "São Paulo", "state": "SP",
     "kind": "escola_medio", "cohort_year": 2003, "cohort_label": "Turma 2003"},
    {"institution_name": "Colégio Bandeirantes", "city": "São Paulo", "state": "SP",
     "kind": "escola_medio", "cohort_year": 2008, "cohort_label": "Turma 2008"},
    {"institution_name": "Colégio Etapa", "city": "São Paulo", "state": "SP",
     "kind": "escola_medio", "cohort_year": 2005, "cohort_label": "Turma 2005"},
    {"institution_name": "Colégio Dante Alighieri", "city": "São Paulo", "state": "SP",
     "kind": "escola_medio", "cohort_year": 2007, "cohort_label": "Turma 2007"},
    {"institution_name": "USP - Universidade de São Paulo", "city": "São Paulo", "state": "SP",
     "kind": "faculdade", "cohort_year": 2010, "cohort_label": "Direito Turma 2010"},

    # === RIO DE JANEIRO ===
    {"institution_name": "Colégio Pedro II", "city": "Rio de Janeiro", "state": "RJ",
     "kind": "escola_medio", "cohort_year": 2000, "cohort_label": "Turma 2000"},
    {"institution_name": "Colégio Pedro II", "city": "Rio de Janeiro", "state": "RJ",
     "kind": "escola_medio", "cohort_year": 2010, "cohort_label": "Turma 2010"},
    {"institution_name": "CAP-UFRJ", "city": "Rio de Janeiro", "state": "RJ",
     "kind": "escola_medio", "cohort_year": 2005, "cohort_label": "Turma 2005"},
    {"institution_name": "PUC-Rio", "city": "Rio de Janeiro", "state": "RJ",
     "kind": "faculdade", "cohort_year": 2012, "cohort_label": "Comunicação Turma 2012"},

    # === BELO HORIZONTE ===
    {"institution_name": "Colégio Loyola", "city": "Belo Horizonte", "state": "MG",
     "kind": "escola_medio", "cohort_year": 2002, "cohort_label": "Turma 2002"},
    {"institution_name": "Colégio Santo Agostinho", "city": "Belo Horizonte", "state": "MG",
     "kind": "escola_medio", "cohort_year": 2006, "cohort_label": "Turma 2006"},
    {"institution_name": "UFMG - Universidade Federal de Minas Gerais", "city": "Belo Horizonte", "state": "MG",
     "kind": "faculdade", "cohort_year": 2008, "cohort_label": "Medicina Turma 2008"},

    # === JUIZ DE FORA (cidade-mae) ===
    {"institution_name": "Colégio Stella Matutina", "city": "Juiz de Fora", "state": "MG",
     "kind": "escola_medio", "cohort_year": 2003, "cohort_label": "Turma 2003"},
    {"institution_name": "Academia de Comércio", "city": "Juiz de Fora", "state": "MG",
     "kind": "escola_medio", "cohort_year": 2000, "cohort_label": "Turma 2000"},
    {"institution_name": "UFJF - Universidade Federal de Juiz de Fora", "city": "Juiz de Fora", "state": "MG",
     "kind": "faculdade", "cohort_year": 2009, "cohort_label": "Engenharia Turma 2009"},

    # === LONDRINA (cidade-mae) ===
    {"institution_name": "Colégio Marista", "city": "Londrina", "state": "PR",
     "kind": "escola_medio", "cohort_year": 2004, "cohort_label": "Turma 2004"},
    {"institution_name": "Colégio Mãe de Deus", "city": "Londrina", "state": "PR",
     "kind": "escola_medio", "cohort_year": 2007, "cohort_label": "Turma 2007"},
    {"institution_name": "UEL - Universidade Estadual de Londrina", "city": "Londrina", "state": "PR",
     "kind": "faculdade", "cohort_year": 2011, "cohort_label": "Direito Turma 2011"},

    # === CAXIAS DO SUL (cidade-mae) ===
    {"institution_name": "Colégio La Salle Caxias", "city": "Caxias do Sul", "state": "RS",
     "kind": "escola_medio", "cohort_year": 2003, "cohort_label": "Turma 2003"},
    {"institution_name": "UCS - Universidade de Caxias do Sul", "city": "Caxias do Sul", "state": "RS",
     "kind": "faculdade", "cohort_year": 2010, "cohort_label": "Administração Turma 2010"},

    # === SALVADOR ===
    {"institution_name": "Colégio Antônio Vieira", "city": "Salvador", "state": "BA",
     "kind": "escola_medio", "cohort_year": 2005, "cohort_label": "Turma 2005"},
    {"institution_name": "UFBA - Universidade Federal da Bahia", "city": "Salvador", "state": "BA",
     "kind": "faculdade", "cohort_year": 2008, "cohort_label": "Arquitetura Turma 2008"},

    # === RECIFE ===
    {"institution_name": "Colégio Marista São Luís", "city": "Recife", "state": "PE",
     "kind": "escola_medio", "cohort_year": 2002, "cohort_label": "Turma 2002"},
    {"institution_name": "UFPE - Universidade Federal de Pernambuco", "city": "Recife", "state": "PE",
     "kind": "faculdade", "cohort_year": 2010, "cohort_label": "Ciência da Computação Turma 2010"},

    # === PORTO ALEGRE ===
    {"institution_name": "Colégio Anchieta", "city": "Porto Alegre", "state": "RS",
     "kind": "escola_medio", "cohort_year": 2001, "cohort_label": "Turma 2001"},
    {"institution_name": "Colégio Rosário", "city": "Porto Alegre", "state": "RS",
     "kind": "escola_medio", "cohort_year": 2006, "cohort_label": "Turma 2006"},
    {"institution_name": "UFRGS - Universidade Federal do Rio Grande do Sul", "city": "Porto Alegre", "state": "RS",
     "kind": "faculdade", "cohort_year": 2011, "cohort_label": "Engenharia Turma 2011"},

    # === CURITIBA ===
    {"institution_name": "Colégio Bom Jesus", "city": "Curitiba", "state": "PR",
     "kind": "escola_medio", "cohort_year": 2004, "cohort_label": "Turma 2004"},
    {"institution_name": "UFPR - Universidade Federal do Paraná", "city": "Curitiba", "state": "PR",
     "kind": "faculdade", "cohort_year": 2010, "cohort_label": "Medicina Turma 2010"},

    # === BRASILIA ===
    {"institution_name": "Colégio Sigma", "city": "Brasília", "state": "DF",
     "kind": "escola_medio", "cohort_year": 2005, "cohort_label": "Turma 2005"},
]


def slugify(institution_name, year, city):
    import re, unicodedata
    text = f"{institution_name}-{year}-{city}"
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[-\s]+', '-', text).strip('-')
    return text[:200]


def seed():
    db = SessionLocal()
    try:
        inserted = 0
        skipped = 0
        for t in SEED_TURMAS:
            slug = slugify(t['institution_name'], t['cohort_year'], t['city'])
            exists = db.query(Turma).filter(Turma.slug == slug).first()
            if exists:
                skipped += 1
                continue
            turma = Turma(
                institution_name=t['institution_name'],
                city=t['city'],
                state=t['state'],
                kind=t['kind'],
                cohort_year=t['cohort_year'],
                cohort_label=t.get('cohort_label'),
                slug=slug,
                total_members=0,
                total_verified=0,
                is_unlocked=False,
            )
            db.add(turma)
            inserted += 1
        db.commit()
        return {'inserted': inserted, 'skipped': skipped, 'total': len(SEED_TURMAS)}
    finally:
        db.close()


if __name__ == '__main__':
    result = seed()
    print(f"Seed complete: {result}")
