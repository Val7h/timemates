# Instruções de Deployment - timeMates

## Pré-requisitos

- Python 3.8+
- Git
- Conta Render.com (para hospedagem)
- Banco de dados PostgreSQL (Render fornece)

---

## 1. Preparação Local

### Ambiente Virtual
```bash
# Criar e ativar ambiente virtual
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt
```

### Variáveis de Ambiente
Criar arquivo `.env` na raiz do projeto:
```
DATABASE_URL=sqlite:///./timeMates.db
SECRET_KEY=sua-chave-secreta-super-segura-aqui
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
SMTP_USERNAME=seu-email@gmail.com
SMTP_PASSWORD=sua-senha-de-app
```

---

## 2. Testes Locais

### Rodar aplicação
```bash
python main.py
```
Acesse: http://localhost:8000

### Verificar estrutura do banco
```bash
# SQLite (desenvolvimento)
sqlite3 timeMates.db ".tables"

# PostgreSQL (produção)
psql $DATABASE_URL -c "\dt"
```

---

## 3. Popular Database

### Opção A: Apenas 27 Cidades (Mínimo)
```bash
python seed_cities.py
```

### Opção B: Dados Completos (Recomendado)
```bash
python seed_deployment_data.py
```

**O que é populado:**
- 27 capitais brasileiras (todas com coordenadas, fotos, etc)
- 25 notícias (por cidade selecionada)
- 15 eventos (por cidade selecionada)
- 15 dicas locais (por cidade selecionada)
- 15 desafios (por cidade selecionada)
- 16 POIs - Pontos de Interesse (por cidade selecionada)
- 9 badges de exemplo

**Cidades com dados completos:**
- Rio de Janeiro
- São Paulo
- Belo Horizonte
- Salvador
- Fortaleza

---

## 4. Git Commit - Antes do Deploy

```bash
# Adicionar arquivos modificados
git add database.py requirements.txt seed_deployment_data.py

# Verificar status
git status

# Criar commit
git commit -m "Deploy: Adicionar modelos de News/Events e script de seed completo

- Adicionar modelos CityNews e CityEvent em database.py
- Criar seed_deployment_data.py com dados para 27 cidades
- Atualizar requirements.txt com dependências
- Suportar seed de notícias, eventos, dicas, desafios e POIs

Co-Authored-By: Deployment Agent <noreply@timeMates.com>"
```

---

## 5. Push para GitHub

```bash
# Fazer push para origin/master
git push origin master

# Verificar status remoto
git status
```

**Esperado:**
```
Your branch is up to date with 'origin/master'.
nothing to commit, working tree clean
```

---

## 6. Deploy no Render

### Step 1: Conectar Repositório
1. Ir para https://render.com
2. Novo serviço → "New Web Service"
3. Conectar repositório GitHub
4. Selecionar branch: `master`

### Step 2: Configurar Build
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn main:app --workers 3 --worker-class uvicorn.workers.UvicornWorker`

### Step 3: Variáveis de Ambiente
Adicionar em Render:
```
DATABASE_URL = postgresql://user:pass@host/db
SECRET_KEY = sua-chave-secreta
STRIPE_SECRET_KEY = sk_live_...
STRIPE_PUBLISHABLE_KEY = pk_live_...
```

### Step 4: Deploy Automático
```bash
git push origin master  # Trigger automático de build no Render
```

---

## 7. Verificar Deploy

### Aguardar Build
```
Render Dashboard → Seu Web Service → Logs
```

**Sinais de sucesso:**
```
[1/4] Building application...
[2/4] Installing dependencies...
[3/4] Starting server...
[4/4] Ready to receive requests
```

### Testar Aplicação
```
https://seu-app.onrender.com
https://seu-app.onrender.com/api/docs (Swagger)
https://seu-app.onrender.com/api/cities (Listar cidades)
```

---

## 8. Popular Database em Produção

### Opção A: Via UI Dashboard
1. Ir em seu serviço no Render
2. "Shell" → Conectar
3. Executar:
```bash
python seed_deployment_data.py
```

### Opção B: Via PostgreSQL Shell
```bash
# Conectar ao banco direto
psql $DATABASE_URL

# Executar SQL para criar tabelas
\dt  # listar tabelas

# Sair
\q
```

---

## 9. Checklist Final

- [ ] Código commitado com `git push origin master`
- [ ] Variáveis de ambiente configuradas no Render
- [ ] Build passou (Render Logs mostram sucesso)
- [ ] Database criado no Render PostgreSQL
- [ ] Seed de dados executado (`seed_deployment_data.py`)
- [ ] `/api/cities` retorna 27 cidades
- [ ] `/api/docs` acessível (documentação Swagger)
- [ ] Testes manuais OK

---

## 10. Troubleshooting

### Erro: `DATABASE_URL not configured`
```
Solução: Adicionar DATABASE_URL nas variáveis de ambiente do Render
```

### Erro: `Module not found`
```
Solução: pip install -r requirements.txt (adicionar dependência em requirements.txt)
```

### Erro: `Port already in use`
```
Solução: Render usa PORT=10000 por padrão (verificar em Logs)
```

### Database vazio
```
Solução: Executar seed_deployment_data.py novamente
```

---

## 11. Dados Populados

Após executar `seed_deployment_data.py`, você terá:

### Cidades (27 capitais)
```json
{
  "slug": "rio-de-janeiro",
  "name": "Rio de Janeiro",
  "state": "RJ",
  "population": 6775561,
  "coordinates": {"latitude": -22.9, "longitude": -43.1}
}
```

### Notícias (25+)
```json
{
  "city_id": 20,
  "title": "Cristo Redentor recebe 2 milhões de visitantes",
  "source": "O Globo",
  "views": 3500,
  "engagement_count": 245
}
```

### Eventos (15+)
```json
{
  "city_id": 20,
  "title": "Maratona do Rio 2026",
  "location": "Avenida Atlântica",
  "category": "esporte",
  "date": "2026-06-20T10:00:00",
  "attendees": 5000
}
```

### Desafios (15+)
```json
{
  "city_id": 20,
  "title": "Tire Foto no Cristo Redentor",
  "difficulty": "facil",
  "reward_points": 50,
  "active": true
}
```

### POIs (16+)
```json
{
  "city_id": 20,
  "name": "Cristo Redentor",
  "type": "landmark",
  "latitude": -22.9519,
  "longitude": -43.2105,
  "rating": 4.9
}
```

### Badges (9+)
```json
{
  "user_id": 1,
  "city_id": 20,
  "badge_type": "explorador_do_rio"
}
```

---

## 12. Endpoints Importantes

### Cidades
```
GET  /api/cities           # Listar todas
GET  /api/cities/{slug}    # Detalhes de uma cidade
```

### News
```
GET  /api/cities/{slug}/news      # Notícias de uma cidade
POST /api/cities/{slug}/news      # Criar notícia (admin)
```

### Events
```
GET  /api/cities/{slug}/events    # Eventos de uma cidade
POST /api/cities/{slug}/events    # Criar evento (admin)
```

### Challenges
```
GET  /api/cities/{slug}/challenges  # Desafios de uma cidade
POST /api/cities/{slug}/challenges  # Criar desafio (admin)
```

### POIs
```
GET  /api/cities/{slug}/pois      # POIs de uma cidade
```

### Documentation
```
GET  /api/docs            # Swagger UI
GET  /api/redoc           # ReDoc
```

---

## 13. Próximos Passos

### Desenvolvimento
1. Testar endpoints em `/api/docs`
2. Criar frontend dashboard com dados de cidades
3. Implementar feed de notícias e eventos
4. Sistema de challenges com submissão de fotos
5. Leaderboard por cidade

### Monitoramento
1. Configurar alertas no Render
2. Monitorar usage do banco PostgreSQL
3. Logs em tempo real

---

## 14. Suporte

Para questões:
1. Verificar logs no Render Dashboard
2. Testar localmente com sqlite
3. Verificar variáveis de ambiente

---

**Última atualização:** 2026-06-05  
**Status:** Pronto para deployment ✓
