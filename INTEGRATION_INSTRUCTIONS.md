# Instruções de Integração - TimeMates v2

Completo guia para integrar notificações, presença online, reações, navegação e tracking.

---

## PASSO 1: Preparar o Ambiente

### 1.1 Instalar dependências Python

```bash
pip install pywebpush apscheduler google-analytics-data requests
```

Adicionar ao `requirements.txt`:
```
pywebpush>=1.14
apscheduler>=3.10
google-analytics-data>=0.18
requests>=2.31
```

### 1.2 Variáveis de ambiente (.env)

```bash
# Web Push API (gerar em https://www.vapidkeys.com/)
VAPID_PUBLIC_KEY=BAw8wy-xJ7F...
VAPID_PRIVATE_KEY=...
VAPID_EMAIL=admin@timemates.com

# Email SMTP (Gmail recomendado)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu-email@gmail.com
SMTP_PASSWORD=sua-senha-app

# Google Analytics 4
GA4_MEASUREMENT_ID=G-XXXXXXXXXX
GA4_API_SECRET=seu_secret_key
GA4_PROPERTY_ID=123456789  # optional, para reports

# Google Credentials (opcional, para relatórios)
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account",...}
```

---

## PASSO 2: Atualizar Database

### 2.1 Adicionar modelos ao database.py

Copie os modelos de `models_extensions.py` para `database.py`:

```python
# Adicionar ao final de database.py:
class Event(Base):
    __tablename__ = "events"
    # ... (copiar de models_extensions.py)

class EventRSVP(Base):
    __tablename__ = "event_rsvps"
    # ...

class Notification(Base):
    __tablename__ = "notifications"
    # ...

# ... etc
```

### 2.2 Criar tabelas

```bash
python -c "from database import Base, engine; Base.metadata.create_all(bind=engine)"
```

---

## PASSO 3: Integrar Rotas no main.py

### 3.1 Importar novo router

```python
# No topo do main.py:
from notification_routes import router as notification_router

# Incluir router:
app.include_router(notification_router)
```

### 3.2 Inicializar scheduler de notificações

```python
# No startup do FastAPI (lifespan):
from notification_service import init_scheduler

@asynccontextmanager
async def lifespan(app):
    # ... código existente ...
    
    # Inicializa scheduler de tarefas
    db = SessionLocal()
    try:
        init_scheduler(db)
    finally:
        db.close()
    
    yield
    
    # cleanup
```

---

## PASSO 4: Frontend - HTML

### 4.1 Adicionar GA4 script no <head> do index.html

```html
<head>
    <!-- ... outros metas ... -->
    
    <!-- Google Analytics 4 -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){dataLayer.push(arguments);}
      gtag('js', new Date());
      gtag('config', 'G-XXXXXXXXXX', {
        'page_path': window.location.pathname,
        'page_title': document.title
      });
      window.trackEvent = function(eventName, params = {}) {
        gtag('event', eventName, params);
        console.log('[GA4]', eventName, params);
      };
      window.GA4_MEASUREMENT_ID = 'G-XXXXXXXXXX';
    </script>
</head>
```

### 4.2 Adicionar container para notificações in-app

```html
<body>
    <!-- No topo do <body> -->
    <div id="notifications-container" style="
      position: fixed;
      top: 70px;
      right: 16px;
      z-index: 1000;
      max-width: 400px;
      max-height: 80vh;
      overflow-y: auto;
    "></div>
    
    <!-- resto do conteúdo -->
</body>
```

### 4.3 Carregar scripts JavaScript

```html
</body>
    <!-- Scripts de integração (antes do closing </body>) -->
    <script src="/static/js/notifications.js"></script>
    <script src="/static/js/presence.js"></script>
    <script src="/static/js/reactions.js"></script>
    <script src="/static/js/tracking.js"></script>
    <script src="/static/js/nav.js"></script>
</body>
```

---

## PASSO 5: Testes de Integração

### 5.1 Testar Web Push

```javascript
// No console do browser:
await notificationManager.setupPushNotifications();
// Cria uma notificação de teste
window.notificationManager.showInAppNotification(
    'Teste', 
    'Isso é um teste de notificação'
);
```

### 5.2 Testar Presença Online

```javascript
// No console:
presenceManager.connectToRoom(1, 123); // room_id=1, user_id=123
// Carrega lista de presença
await presenceManager.loadPresence();
```

### 5.3 Testar Reações

```javascript
// Adiciona reação
await reactionsManager.addReaction(1, '👍'); // message_id=1, emoji='👍'
// Carrega reações
await reactionsManager.loadReactions(1);
```

### 5.4 Testar Tracking GA4

```javascript
// No console:
trackingService.trackNewsClick(5, 'Título da notícia');
trackingService.trackRsvpEvent(10, 2, 'going');
trackingService.trackReactionAdded(1, 2, '👍');
```

### 5.5 Testar Navegação

```javascript
// No console:
navigationManager.navigateToPage('news');
navigationManager.navigateToPage('events');
```

---

## PASSO 6: API Endpoints - Resumo

### Notificações
- `GET /api/notifications` - Lista notificações
- `PATCH /api/notifications/{id}/read` - Marca como lida
- `DELETE /api/notifications/{id}` - Deleta

### Push Subscriptions
- `POST /api/push/subscribe` - Registra subscription
- `POST /api/push/unsubscribe` - Remove subscription

### Eventos
- `POST /api/rooms/{room_id}/events` - Cria evento
- `GET /api/rooms/{room_id}/events` - Lista eventos
- `POST /api/events/{event_id}/rsvp` - Confirma RSVP
- `GET /api/events/{event_id}/rsvps` - Lista RSVPs

### Presença
- `POST /api/presence/update` - Atualiza status online
- `GET /api/rooms/{room_id}/presence` - Lista usuários online
- `WS /api/ws/room/{room_id}` - WebSocket em tempo real

### Reações
- `POST /api/messages/{message_id}/reactions` - Adiciona reação
- `DELETE /api/messages/{message_id}/reactions/{emoji}` - Remove
- `GET /api/messages/{message_id}/reactions` - Lista reações

---

## PASSO 7: Configuração de Email (Gmail)

### 7.1 Ativar "App Passwords"

1. Acesse Google Account: https://myaccount.google.com/
2. Security → 2-Step Verification → App Passwords
3. Selecione Mail e Device (Windows Computer)
4. Copie a senha gerada
5. Use em `SMTP_PASSWORD=`

### 7.2 Testar envio de email

```python
from notification_service import NotificationService
from database import SessionLocal

db = SessionLocal()
service = NotificationService(db)

# Envia email de teste
service.send_email(
    to_email='seu-email@gmail.com',
    subject='Teste TimeMates',
    html_content='<h1>Teste de email</h1>'
)
```

---

## PASSO 8: Configuração de GA4

### 8.1 Criar property no GA4

1. Acesse Google Analytics: https://analytics.google.com/
2. Crie uma Property
3. Copie o Measurement ID (G-XXXXX)
4. Crie um Secret (Admin > Property > Data Streams)

### 8.2 Ativar relatórios de eventos customizados

1. Admin > Events
2. Crie eventos customizados:
   - `click_news`
   - `rsvp_event`
   - `view_highlights`
   - `reaction_added`
   - `presence_online`

---

## PASSO 9: Checklist de Deploy

- [ ] Variáveis de ambiente configuradas
- [ ] Dependências Python instaladas
- [ ] Modelos de banco de dados criados
- [ ] Rotas incluídas em main.py
- [ ] Scheduler inicializado
- [ ] Scripts JS adicionados ao HTML
- [ ] GA4 snippet adicionado
- [ ] Service Worker registrado
- [ ] Email SMTP testado
- [ ] Web Push testado
- [ ] Presença online testado
- [ ] Reações em mensagens testado
- [ ] Navegação testada

---

## PASSO 10: Troubleshooting

### Notificações push não funcionam
- Verificar VAPID_PUBLIC_KEY e VAPID_PRIVATE_KEY
- Verificar se Service Worker registrou
- Verificar permissão de notificações do navegador

### Email não envia
- Verificar credenciais SMTP
- Ativar "Less secure app access" (se usar senha normal)
- Testar com senha de app (Gmail)

### WebSocket desconecta
- Verificar firewall/proxy
- Aumentar timeout em nginx/reverse proxy
- Verificar logs do servidor

### GA4 não registra eventos
- Verificar GA4_MEASUREMENT_ID
- Esperar 24-48h para ver dados (latência GA4)
- Usar GA4 Debugger (Chrome Extension)

---

## Arquivos Criados

```
timeMates/
├── INTEGRATION_PLAN.md                    # Este arquivo
├── INTEGRATION_INSTRUCTIONS.md            # Este arquivo
├── models_extensions.py                   # Modelos adicionais
├── notification_service.py                # Serviço de notificações
├── notification_routes.py                 # Rotas FastAPI
├── tracking_service.py                    # Serviço GA4
├── static/
│   ├── js/
│   │   ├── notifications.js               # Gerenciador de notificações
│   │   ├── presence.js                    # Gerenciador de presença
│   │   ├── reactions.js                   # Gerenciador de reações
│   │   ├── tracking.js                    # Tracking GA4
│   │   └── nav.js                         # Navegação com dropdowns
│   └── sw.js                              # Service Worker (atualizado)
```

---

## Próximas Fases (Future)

1. **Notícias em tempo real**: Feed de notícias com filtros
2. **Destaques automáticos**: Sistema que identifica melhores momentos
3. **Badges e achievements**: Gamificação
4. **Chat direto (DM)**: Mensagens privadas
5. **Integração com terceiros**: Slack, Discord, Telegram

---

**Desenvolvido em 2026 para TimeMates**
