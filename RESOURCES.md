# 🚀 Recursos do TimeMates - IBGE & Mapa Interativo

## 📍 Novos Endpoints da API

### 1. **Top 10 Cidades com Regiões Metropolitanas**
```
GET /api/cities/top10/with-regions
```

Retorna as 10 maiores cidades do Brasil com informações sobre:
- Ranking (1º ao 10º)
- População
- Coordenadas geográficas
- Regiões metropolitanas
- Estatísticas de notícias e eventos

**Exemplo de resposta:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "slug": "sao-paulo",
      "name": "São Paulo",
      "state": "SP",
      "population": 11975881,
      "rank": 1,
      "coordinates": {"lat": -23.5505, "lng": -46.6333},
      "metropolitan_region": {
        "name": "Região Metropolitana de São Paulo",
        "population": 22183000,
        "cities": ["São Paulo", "Guarulhos", "São Bernardo do Campo", "Santo André"],
        "radius_km": 45
      },
      "nickname": "Megalópole",
      "stats": {
        "news": 5,
        "events": 5
      }
    }
  ],
  "total": 10,
  "center": {"lat": -14.2350, "lng": -51.9253},
  "zoom": 4
}
```

### 2. **IBGE - Informações de Cidade**
```
GET /api/city/{slug}/info-ibge
```

Retorna dados em tempo real do IBGE:
- Informações da cidade
- Código IBGE
- População verificada
- Status da integração

**Exemplo:**
```
GET /api/city/sao-paulo/info-ibge
```

---

## 🗺️ Novos Dashboards Web

### 1. **Mapa Interativo**
```
GET /map
```

**Recursos:**
- ✅ Mapa interativo com Leaflet.js
- ✅ Visualização das 10 maiores cidades
- ✅ Regiões metropolitanas em tempo real
- ✅ Clique em cidades para ver detalhes
- ✅ Controles de zoom e navegação
- ✅ Modo responsivo (desktop/mobile)

**Funcionalidades:**
- **Clicar em uma cidade**: Centraliza o mapa e mostra detalhes
- **Mostrar Regiões Metropolitanas**: Toggle que exibe os raios de regiões
- **Focar Top 5**: Ajusta a visualização para as 5 maiores cidades
- **Resetar Mapa**: Retorna à visão padrão do Brasil

### 2. **Dashboard de Notícias**
```
GET /news
```

**Recursos:**
- 📰 Notícias locais por cidade
- 🏷️ Filtros por categoria (15 categorias)
- 🔍 Busca em tempo real
- 📊 Estatísticas de notícias

**Categorias:**
- breaking_news
- events
- economy
- education
- culture
- religion
- business
- tourism
- urban_planning
- technology
- gastronomy
- politics
- science
- environment
- news

### 3. **Dashboard de Eventos**
```
GET /events
```

**Recursos:**
- 🎪 Eventos locais por cidade
- 📅 Visualização em calendário
- 🔍 Busca por cidade
- 📍 Localização e horário dos eventos
- 👥 RSVP interativo (Vou/Talvez/Não vou)

---

## 🌍 IBGE Integration

### Serviço IBGE (ibge_service.py)

**Métodos disponíveis:**

#### `IBGEService.get_city_info(ibge_code: int)`
Busca informações básicas de uma cidade

#### `IBGEService.get_population_estimate(ibge_code: int, year: int = 2023)`
Busca estimativa de população para um ano específico

#### `IBGEService.get_state_cities(state_code: str)`
Busca todas as cidades de um estado (ex: "SP", "RJ")

#### `IBGEService.get_gdp_data(ibge_code: int)`
Busca dados de PIB municipal

---

## 📊 Regiões Metropolitanas Incluídas

| Ranking | Cidade | Região Metropolitana | População | Raio |
|---------|--------|----------------------|-----------|------|
| 1º | São Paulo | RM de São Paulo | 22.183.000 | 45km |
| 2º | Rio de Janeiro | RM do Rio de Janeiro | 13.000.000 | 40km |
| 3º | Brasília | RIDE | 4.000.000 | 30km |
| 4º | Fortaleza | RM de Fortaleza | 4.000.000 | 35km |
| 5º | Salvador | RM de Salvador | 4.000.000 | 25km |
| 6º | Belo Horizonte | RM de Belo Horizonte | 6.000.000 | 35km |
| 7º | Curitiba | RM de Curitiba | 3.600.000 | 30km |
| 8º | Manaus | RM de Manaus | 2.200.000 | 25km |
| 9º | Recife | RM de Recife | 4.000.000 | 30km |
| 10º | Goiânia | RM de Goiânia | Não definida | - |

---

## 🔧 Como Usar no Código

### JavaScript/Frontend

```javascript
// Buscar Top 10 cidades
fetch('/api/cities/top10/with-regions')
  .then(r => r.json())
  .then(data => {
    console.log(data.data); // Array com 10 cidades
    data.data.forEach(city => {
      console.log(`${city.rank}º - ${city.name}`);
      console.log(`População: ${city.population.toLocaleString('pt-BR')}`);
      console.log(`Região: ${city.metropolitan_region.name}`);
    });
  });
```

### Python/Backend

```python
from ibge_service import IBGEService

# Buscar info de São Paulo
sp_info = IBGEService.get_city_info(3550308)

# Buscar população estimada
sp_pop = IBGEService.get_population_estimate(3550308, year=2023)

# Buscar cidades de SP
sp_cities = IBGEService.get_state_cities("SP")
```

---

## 📱 URLs de Acesso

| Recurso | URL |
|---------|-----|
| 🗺️ Mapa Interativo | `/map` |
| 📰 Notícias | `/news` |
| 🎪 Eventos | `/events` |
| 🏠 Home | `/` |
| 🔒 Privacidade | `/privacy` |
| 📋 Termos | `/terms` |

---

## 🔄 Cache de IBGE

O serviço IBGE utiliza cache de **1 hora** para economizar requisições:
- Primeira requisição: API do IBGE
- Próximas requisições (até 1h): Cache local
- Após 1h: Nova requisição ao IBGE

---

## 📈 Dados Coletados

**Total no banco:**
- 27 cidades (todas as capitais)
- 35 notícias locais
- 35 eventos locais
- 135 desafios (5 por cidade)
- 10 regiões metropolitanas

---

## ✅ Status da Implementação

| Feature | Status | Descrição |
|---------|--------|-----------|
| IBGE Integration | ✅ | API do IBGE integrada com cache |
| Top 10 Endpoint | ✅ | Retorna cidades com regiões metropolitanas |
| Mapa Interativo | ✅ | Leaflet.js com controles e popups |
| Acentuação UTF-8 | ✅ | Todas as cidades com acentos corretos |
| Busca NFD | ✅ | Busca funciona com ou sem acentos |
| Regiões Metropolitanas | ✅ | 10 principais regiões mapeadas |

---

## 🚀 Deploy

Para fazer deploy na Render:

```bash
# 1. Commit as mudanças
git add .
git commit -m "Feat: IBGE integration e mapa interativo"

# 2. Push para GitHub
git push origin main

# 3. Render detecta automaticamente e redeploy
# Acesse: https://timemates.onrender.com/map
```

---

## 🐛 Troubleshooting

### Mapa não carrega
- Verifique se Leaflet.js está carregando (console.log)
- Teste o endpoint `/api/cities/top10/with-regions` no Postman

### IBGE retorna erro
- Verifique conexão com internet
- Código IBGE pode estar incorreto
- Timeout após 5 segundos é esperado em conexões lentas

### Regiões não aparecem
- Clique em "Mostrar Regiões Metropolitanas" na sidebar
- Verifique se coordenadas das cidades estão salvas no banco

---

Desenvolvido com ❤️ por Claude AI Agents
