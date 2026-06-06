# Quick Start - Integração TimeMates em 30 minutos

## Para os apressados 🚀

### PASSO 1: Copiar arquivos (5 min)

```bash
# Copiar arquivos Python
cp models_extensions.py ↓ database.py (merge os modelos)
cp notification_service.py timeMates/
cp notification_routes.py timeMates/
cp tracking_service.py timeMates/

# Copiar arquivos JS
cp static/js/*.js timeMates/static/js/
cp static/sw.js timeMates/static/sw.js (replace)
```

### PASSO 2: Configurar .env (5 min)

```bash
# Gerar VAPID keys em https://www.vapidkeys.com/
export VAPID_PUBLIC_KEY=BAw8wy-xJ7F...
export VAPID_PRIVATE_KEY=...
export VAPID_EMAIL=admin@timemates.com

# Gmail app password
export SMTP_USER=seu-email@gmail.com
export SMTP_PASSWORD=senha-app-google

# GA4 ID (obter em https://analytics.google.com/)
export GA4_MEASUREMENT_ID=G-XXXXXXXXXX
export GA4_API_SECRET=seu_secret_here
```

### PASSO 3: Instalar dependências (5 min)

```bash
pip install pywebpush apscheduler google-analytics-data requests
```

### PASSO 4: Integrar no main.py (10 min)

```python
# No topo:
from notification_routes import router as notification_router
from notification_service import init_scheduler

# Depois de app = FastAPI(...):
app.include_router(notification_router)

# Na função lifespan (startup):
init_scheduler(SessionLocal())
```

### PASSO 5: Adicionar GA4 no HTML (5 min)

```html
<!-- No <head> de index.html -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX');
  window.trackEvent = function(eventName, params = {}) {
    gtag('event', eventName, params);
  };
  window.GA4_MEASUREMENT_ID = 'G-XXXXXXXXXX';
</script>

<!-- Antes de </body> -->
<script src="/static/js/notifications.js"></script>
<script src="/static/js/presence.js"></script>
<script src="/static/js/reactions.js"></script>
<script src="/static/js/tracking.js"></script>
<script src="/static/js/nav.js"></script>
```

---

## Testes Rápidos

Abra console (F12) e execute:

```javascript
// Test 1: Notificações
notificationManager.showInAppNotification('Teste', 'Funciona!');

// Test 2: Presença
presenceManager.connectToRoom(1, 123);

// Test 3: Reações
reactionsManager.addReaction(1, '👍');

// Test 4: Tracking
trackingService.trackNewsClick(1, 'Test');

// Test 5: Navegação
navigationManager.navigateToPage('news');
```

---

## Endpoints Principais

```bash
# Notificações
GET  /api/notifications
POST /api/push/subscribe
POST /api/events/{id}/rsvp

# Presença
POST /api/presence/update
GET  /api/rooms/{id}/presence

# Reações
POST /api/messages/{id}/reactions
GET  /api/messages/{id}/reactions

# WebSocket
WS   /api/ws/room/{id}
```

---

## Troubleshooting 5 Segundo

| Problema | Solução |
|----------|---------|
| "notificationManager undefined" | Incluir `/static/js/notifications.js` |
| Push não funciona | Verificar VAPID keys em .env |
| Email não envia | Ativar "App Passwords" no Gmail |
| GA4 não registra | Usar GA4 Debugger, esperar 24h |
| WebSocket desconecta | Aumentar timeout no servidor |

---

## Próximas 24h

1. ✅ Setup (30 min)
2. ✅ Testes no console (30 min)
3. 📝 Testar em produção
4. 📊 Verificar GA4
5. 🎉 Celebrate!

---

**Pronto? Comece!** 🚀

Documentação completa em:
- INTEGRATION_INSTRUCTIONS.md (passo a passo detalhado)
- INTEGRATION_EXAMPLES.md (10 exemplos prontos)
- TEST_INTEGRATION.md (teste tudo)
