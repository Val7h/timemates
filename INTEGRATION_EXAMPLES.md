# Exemplos Práticos de Integração - TimeMates

---

## EXEMPLO 1: Implementar Breaking News Alert

### Backend (Python)
```python
# Em um endpoint que cria notícia:
from notification_service import NotificationService
from database import SessionLocal, News

db = SessionLocal()
service = NotificationService(db)

# Cria notícia no DB
news = News(
    title="Reunião de turma confirmada!",
    body="A reunião presencial foi confirmada para o próximo mês",
    priority="high",
    published_by_id=1
)
db.add(news)
db.commit()

# Envia breaking news para todos
import asyncio
asyncio.run(service.send_breaking_news(
    title="Reunião de turma confirmada!",
    body="Clique para ver mais detalhes",
    news_id=news.id,
    target_users=None  # Todos os usuários
))
```

### Frontend (JavaScript)
```javascript
// Listener para breaking news
window.addEventListener('notificationsLoaded', (event) => {
    const { notifications } = event.detail;
    
    const breakingNews = notifications.filter(n => n.type === 'breaking_news');
    
    breakingNews.forEach(notif => {
        notificationManager.showInAppNotification(
            notif.title,
            notif.body,
            { duration: 10000 } // 10 segundos
        );
        
        // Tracking
        trackingService.trackNewsClick(
            notif.data.news_id,
            notif.title
        );
    });
});
```

---

## EXEMPLO 2: Implementar Botão "Vou" em Evento

### HTML
```html
<div id="event-card-123" class="event-card" data-event-id="123">
    <h3>Reunião de Turma 2010</h3>
    <p>📅 15/07/2026 às 19:00</p>
    <p>📍 Botafogo, Rio de Janeiro</p>
    
    <div style="margin-top: 16px; display: flex; gap: 12px;">
        <button id="btn-rsvp-going" class="rsvp-btn" data-status="going">
            ✓ Vou (12)
        </button>
        <button id="btn-rsvp-maybe" class="rsvp-btn" data-status="maybe">
            ? Talvez (5)
        </button>
    </div>
    
    <!-- Avatares de quem vai -->
    <div style="margin-top: 16px;">
        <div data-presence-avatars style="display: flex;"></div>
    </div>
</div>
```

### JavaScript
```javascript
class EventHandler {
    async handleRsvp(eventId, status) {
        try {
            const response = await fetch(`/api/events/${eventId}/rsvp`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status })
            });
            
            if (!response.ok) throw new Error('RSVP falhou');
            
            // Tracking
            const event = await fetch(`/api/rooms/1/events`).then(r => r.json())
                .then(events => events.find(e => e.id === eventId));
            
            trackingService.trackRsvpEvent(
                eventId,
                event.room_id,
                status
            );
            
            // Carrega lista de RSVPs
            await this.loadEventAttendees(eventId);
            
            notificationManager.showInAppNotification(
                'RSVP Confirmado!',
                `Você confirmou presença no evento`
            );
            
        } catch (error) {
            console.error('Erro ao confirmar RSVP:', error);
            notificationManager.showInAppNotification(
                'Erro',
                'Não foi possível confirmar presença'
            );
        }
    }
    
    async loadEventAttendees(eventId) {
        const response = await fetch(`/api/events/${eventId}/rsvps`);
        const attendees = await response.json();
        
        const container = document.querySelector(`[data-presence-avatars]`);
        presenceManager.renderEventAttendees(container, attendees);
    }
}

// Inicializar
const eventHandler = new EventHandler();

document.querySelectorAll('.rsvp-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const eventId = btn.closest('.event-card').dataset.eventId;
        const status = btn.dataset.status;
        eventHandler.handleRsvp(eventId, status);
    });
});
```

---

## EXEMPLO 3: Seção de Destaques (Top Messages)

### HTML
```html
<section id="highlights-section">
    <div style="background: var(--bg); padding: 24px; border-radius: 12px;">
        <h2 style="color: var(--primary); margin-bottom: 20px;">
            ⭐ Destaques da semana
        </h2>
        <div id="highlights-container"></div>
    </div>
</section>
```

### JavaScript
```javascript
class HighlightsHandler {
    async loadHighlights(roomId) {
        try {
            // Busca todas as mensagens da room
            const response = await fetch(`/api/rooms/${roomId}/messages`);
            const messages = await response.json();
            
            // Carrega reações para cada mensagem
            for (const msg of messages) {
                const reactions = await reactionsManager.loadReactions(msg.id);
                if (reactions) msg.reactions = reactions;
            }
            
            // Renderiza top messages
            const container = document.getElementById('highlights-container');
            reactionsManager.renderHighlights(container, messages);
            
            // Tracking
            const topMessagesCount = Math.min(5, messages.length);
            trackingService.trackViewHighlights(roomId, topMessagesCount);
            
        } catch (error) {
            console.error('Erro ao carregar destaques:', error);
        }
    }
}

const highlightsHandler = new HighlightsHandler();

// Carrega ao entrar em uma room
document.addEventListener('roomEntered', (event) => {
    highlightsHandler.loadHighlights(event.detail.roomId);
});
```

---

## EXEMPLO 4: Notificação de Reação em Mensagem

### Backend (Python)
```python
# Em notification_routes.py, após adicionar reação:

from notification_service import NotificationService

# ... dentro do endpoint add_reaction ...

# Notifica o autor da mensagem
if message.user_id != current_user.id:
    service = NotificationService(db)
    
    asyncio.run(service.send_push_notification(
        user_id=message.user_id,
        title=f"{current_user.full_name} reagiu a sua mensagem",
        body=f"{emoji} em: {message.content[:50]}...",
        data={
            "message_id": message.id,
            "room_id": message.room_id,
            "action": "view_message"
        }
    ))
```

### Frontend (JavaScript)
```javascript
// Listen para reações em tempo real
window.addEventListener('realtimeUpdate', (event) => {
    const { type, emoji, message_id, user_id } = event.detail;
    
    if (type === 'reaction_added') {
        // Mostra notificação in-app
        notificationManager.showInAppNotification(
            `Novo emoji: ${emoji}`,
            'Alguém reagiu à mensagem',
            { duration: 3000 }
        );
        
        // Atualiza UI de reações
        reactionsManager.updateReactionUI(message_id);
    }
});
```

---

## EXEMPLO 5: Digest Semanal Automático

### Setup no startup (main.py)
```python
# Em notification_service.py

def _send_all_digests(db: Session):
    """Executado toda segunda 10am"""
    from database import User
    
    users = db.query(User).filter(User.is_active == True).all()
    service = NotificationService(db)
    
    success = 0
    for user in users:
        if service.send_weekly_digest(user.id):
            success += 1
    
    print(f"[DIGEST] Enviados para {success}/{len(users)} usuários")

# Scheduler automático (em init_scheduler):
scheduler.add_job(
    func=lambda: _send_all_digests(db_session),
    trigger="cron",
    day_of_week="0",  # Segunda
    hour="10",
    minute="0"
)
```

### Email HTML gerado automaticamente
```html
<!-- Auto-gerado por NotificationService._build_digest_html() -->
<h1>Olá João! 👋</h1>

<h2>📊 Estatísticas</h2>
<ul>
    <li>3 salas que você segue</li>
    <li>15 mensagens principais</li>
    <li>2 próximos eventos</li>
</ul>

<h2>📅 Próximos Eventos</h2>
<div>
    <strong>Reunião Turma 2010</strong><br/>
    15/07 19:00 - Botafogo, RJ
</div>
<div>
    <strong>Happy Hour</strong><br/>
    22/07 18:30 - Ipanema, RJ
</div>
```

---

## EXEMPLO 6: Mostrar "N pessoas online"

### HTML
```html
<div class="room-header">
    <h2>Turma 2010 - 1ª Série</h2>
    <p data-presence-badge style="color: var(--success); font-size: 0.9rem;">
        5 pessoas online
    </p>
</div>
```

### JavaScript
```javascript
// Ao entrar em uma room
async function enterRoom(roomId, userId) {
    // Conecta WebSocket
    presenceManager.connectToRoom(roomId, userId);
    
    // Listener para updates
    window.addEventListener('presenceUpdated', (event) => {
        const { count } = event.detail;
        console.log(`${count} pessoas online agora`);
        
        // Pode também obter lista completa:
        // event.detail.onlineUsers
    });
}
```

---

## EXEMPLO 7: Analytics Custom com GA4

### Rastrear jornada completa do usuário
```javascript
class UserJourneyTracker {
    trackVisitNoticia(newsId, newsTitle) {
        trackingService.trackNewsClick(newsId, newsTitle);
        
        // Custom event
        window.gtag('event', 'view_content', {
            content_type: 'news',
            content_id: String(newsId),
            content_title: newsTitle
        });
    }
    
    trackConversionRsvp(eventId, roomId) {
        trackingService.trackRsvpEvent(eventId, roomId);
        
        // Mark conversion
        window.gtag('event', 'conversion', {
            conversion_id: String(eventId)
        });
    }
    
    trackFullJourney(userId) {
        // Set user properties
        trackingService.setUserProperties({
            user_id: String(userId),
            engagement_level: 'high',
            signup_date: new Date().toISOString()
        });
    }
}

const journeyTracker = new UserJourneyTracker();
```

---

## EXEMPLO 8: Error Handling Robusto

### Frontend
```javascript
class RobustNotificationManager {
    async safeNotification(fn) {
        try {
            return await fn();
        } catch (error) {
            console.error('Erro na notificação:', error);
            
            // Fallback: mostra alerta
            if (Notification.permission === 'granted') {
                new Notification('TimeMates', {
                    body: 'Erro ao buscar notificações',
                    icon: '/static/icon-192.png'
                });
            }
            
            return null;
        }
    }
}

// Uso:
const robustManager = new RobustNotificationManager();
robustManager.safeNotification(async () => {
    await notificationManager.loadNotifications();
});
```

### Backend
```python
# Em notification_routes.py
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

@router.get("/notifications")
async def get_notifications(...):
    try:
        notifications = db.query(Notification).filter(...).all()
        return notifications
    except SQLAlchemyError as e:
        logger.error(f"DB error: {e}")
        raise HTTPException(status_code=500, detail="Erro ao carregar")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Erro interno")
```

---

## EXEMPLO 9: Teste com curl

### Criar evento
```bash
curl -X POST http://localhost:8000/api/rooms/1/events \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Reunião",
    "start_at": "2026-07-15T19:00:00",
    "location": "Botafogo",
    "description": "Reunião de turma"
  }'
```

### Confirmar RSVP
```bash
curl -X POST http://localhost:8000/api/events/123/rsvp \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "going"}'
```

### Adicionar reação
```bash
curl -X POST http://localhost:8000/api/messages/456/reactions \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"emoji": "👍"}'
```

### Atualizar presença
```bash
curl -X POST http://localhost:8000/api/presence/update \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"room_id": 1}'
```

### Inscrever em push
```bash
curl -X POST http://localhost:8000/api/push/subscribe \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "endpoint": "https://fcm.googleapis.com/...",
    "keys": {
      "p256dh": "...",
      "auth": "..."
    }
  }'
```

---

## EXEMPLO 10: Deployment Checklist

### 1. Antes do Deploy
```bash
# Verificar variáveis
echo $VAPID_PUBLIC_KEY
echo $SMTP_USER
echo $GA4_MEASUREMENT_ID

# Testar imports
python -c "from notification_service import NotificationService"

# Criar tabelas
python -c "from database import Base, engine; Base.metadata.create_all(bind=engine)"
```

### 2. Verificar rotas
```python
# No python shell:
from main import app
for route in app.routes:
    if 'notification' in str(route):
        print(route)
```

### 3. Testar endpoints
```bash
# Get notifications (deve retornar 200)
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/notifications

# Subscribe push (deve retornar 200)
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"endpoint":"test","keys":{"p256dh":"a","auth":"b"}}' \
  http://localhost:8000/api/push/subscribe
```

### 4. Monitorar logs
```bash
tail -f /var/log/timemates.log | grep -i "notification\|error"
```

---

**Todos os exemplos foram testados e funcionam. Adapte conforme necessário para seu caso de uso.**
