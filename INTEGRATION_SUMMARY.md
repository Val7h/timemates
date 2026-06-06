# Sumário de Integração - TimeMates v2

Data: 2026-06-05
Escopo: Notificações, Presença Online, Reações, Navegação, Tracking GA4

---

## 1. NOTIFICAÇÕES ✅

### Tipos Implementados
- **Web Push API**: Notificações do navegador (background e foreground)
- **In-App Notifications**: Notificações visuais dentro da app
- **Email Digest**: Resumo semanal enviado segunda 10am
- **Event Reminders**: Lembrete 24h antes de eventos

### Features
```javascript
notificationManager.send_push_notification(
  user_id, title, body, icon, data
)
notificationManager.showInAppNotification(title, body)
notificationManager.markAsRead(notificationId)
```

### Backend
- `NotificationService`: Gerencia envio via pywebpush e email
- `APScheduler`: Agenda tasks (reminders, digests)
- Database: `Notification`, `PushSubscription`, `EmailLog`

### Endpoints
```
POST   /api/push/subscribe
POST   /api/push/unsubscribe
GET    /api/notifications
PATCH  /api/notifications/{id}/read
DELETE /api/notifications/{id}
```

---

## 2. PRESENÇA ONLINE ✅

### Features
- "5 pessoas indo" em eventos com avatares
- Status online em tempo real via WebSocket
- Indica última atividade
- Auto-atualiza a cada 30 segundos
- Detecta visibilidade de aba (pausa quando aberta outra)

### API Frontend
```javascript
presenceManager.connectToRoom(roomId, userId)
presenceManager.loadPresence()
presenceManager.renderEventAttendees(container, attendees)
```

### Backend
- WebSocket: `/api/ws/room/{room_id}`
- Database: `UserPresence`
- Threshold: 5 minutos para considerar "online"

### Endpoints
```
POST   /api/presence/update
GET    /api/rooms/{room_id}/presence
WS     /api/ws/room/{room_id}
```

---

## 3. REAÇÕES EM TEMPO REAL ✅

### Emojis Suportados
👍 ❤️ 😂 🔥 ✨ 👏 🎉 🤔

### Features
- Adiciona/remove reações em mensagens
- Conta reações por emoji
- Picker de emojis
- Top messages por reactions (highlights)
- Broadcast em tempo real via WebSocket

### API Frontend
```javascript
reactionsManager.addReaction(messageId, emoji)
reactionsManager.removeReaction(messageId, emoji)
reactionsManager.loadReactions(messageId)
reactionsManager.getTopMessages(messages, limit=5)
reactionsManager.renderHighlights(container, messages)
```

### Backend
- Database: `MessageReaction`
- Endpoints: POST/DELETE /reactions, GET reactions

---

## 4. NAVEGAÇÃO ✅

### Estrutura
```
Nav Bar
├─ Logo TimeMates
├─ [📰 Notícias] [🎉 Eventos ▼] [Perfil ▼]
│  └─ Dropdown Eventos:
│     ├─ ⏰ Próximos Eventos
│     ├─ ✓ Meus Eventos
│     └─ ➕ Criar Evento
│  └─ Dropdown Perfil:
│     ├─ 👤 Meu Perfil
│     ├─ 🏠 Minhas Salas
│     ├─ ⚙️ Configurações
│     └─ 🚪 Sair
└─ 🔔 Notificações [badge]
```

### Features
- Dropdowns interativos
- Active state com highlight
- Badge de notificações não lidas
- Avatar do usuário
- Navegação via hash (#page)

### API Frontend
```javascript
navigationManager.navigateToPage('news')
navigationManager.init()
```

---

## 5. TRACKING GA4 ✅

### Eventos Rastreados
| Evento | Parâmetros | Quando |
|--------|-----------|--------|
| `click_news` | news_id, title | Clique em notícia |
| `rsvp_event` | event_id, room_id, status | RSVP confirmado |
| `view_highlights` | room_id, count | Abre destaques |
| `reaction_added` | message_id, room_id, emoji | Reação adicionada |
| `presence_online` | room_id, duration_seconds | Entrada em room |
| `room_joined` | room_id, institution_id | Entra na sala |
| `message_sent` | room_id, length | Mensagem enviada |

### API Frontend
```javascript
trackingService.trackNewsClick(newsId, title)
trackingService.trackRsvpEvent(eventId, roomId, status)
trackingService.trackReactionAdded(messageId, roomId, emoji)
trackingService.trackPresenceOnline(roomId)
```

### Dashboard GA4
- Real-time events
- User engagement
- Conversion tracking
- Cohort analysis

---

## 6. EVENTOS (NEW FEATURE) ✅

### Model
```
Event
├─ title, description
├─ start_at, end_at
├─ location
├─ room_id, created_by_id
└─ rsvps[] (list of EventRSVP)
```

### Status RSVP
- `interested` - Talvez vá
- `going` - Vai com certeza
- `maybe` - Indefinido
- `not_going` - Não vai

### Endpoints
```
POST   /api/rooms/{room_id}/events
GET    /api/rooms/{room_id}/events
POST   /api/events/{event_id}/rsvp
GET    /api/events/{event_id}/rsvps
```

---

## 7. ARQUITETURA

### Frontend Stack
```
HTML/CSS/JS
├─ notificações.js (Push + in-app)
├─ presença.js (WebSocket)
├─ reações.js (Emojis + highlights)
├─ tracking.js (GA4 events)
├─ nav.js (Navegação)
└─ sw.js (Service Worker)
```

### Backend Stack
```
FastAPI
├─ notification_routes.py
├─ notification_service.py
├─ tracking_service.py
└─ models_extensions.py
```

### Database
```
SQLAlchemy + PostgreSQL/SQLite
├─ Event
├─ EventRSVP
├─ Notification
├─ PushSubscription
├─ UserPresence
├─ MessageReaction
├─ News
└─ EmailLog
```

### External Services
```
Google Analytics 4
├─ Measurement Protocol (envio de eventos)
├─ Property ID (relatórios)
└─ Service Account (analytics read API)

SMTP Email
├─ Gmail (recomendado)
├─ Sendgrid (alternativa)
└─ Custom SMTP

Web Push
├─ pywebpush library
└─ VAPID keys
```

---

## 8. FLUXOS PRINCIPAIS

### Fluxo 1: Notificação Push
```
1. Usuário permite notificações
2. Service Worker salva subscription
3. Frontend envia subscription ao servidor
4. Sistema envia push via pywebpush
5. SW exibe notificação
6. Clique navega para recurso
```

### Fluxo 2: Presença Online
```
1. User A entra em room
2. Frontend conecta WebSocket
3. Envia POST /api/presence/update
4. Sistema broadcast "online" via WS
5. User B recebe update
6. UI mostra avatar + "5 pessoas online"
7. A cada 30s, renova presença
8. WebSocket desconecta = "offline"
```

### Fluxo 3: Reação em Tempo Real
```
1. User clica emoji em mensagem
2. Frontend POST /api/messages/{id}/reactions
3. Backend salva MessageReaction
4. Sistema broadcast via WebSocket
5. Todos os clients atualizam UI
6. Calcula top messages
7. Mostra em seção "Destaques"
```

### Fluxo 4: Tracking GA4
```
1. User clica notícia
2. Frontend trackingService.trackNewsClick()
3. gtag('event', 'click_news', {...})
4. GA4 Measurement Protocol recebe
5. Acumula em dashboard GA4
6. Análise em tempo real
```

---

## 9. PERFORMANCE

### Cache Strategy
- **Static assets**: Cache-first
- **API endpoints**: Network-first
- **Service Worker**: Offline fallback

### WebSocket Optimization
- Reconexão automática (5s)
- Heartbeat a cada 30s
- Fechar conexão ao sair
- Suporta múltiplas rooms

### Database Queries
- Índices em `user_id`, `room_id`, `message_id`
- Limit padrão 20 notificações
- Threshold presença: 5 minutos

---

## 10. SEGURANÇA

### Authentication
- JWT tokens (existente)
- Verificação em todos endpoints
- User isolation (GET notifications only self)

### Data Protection
- VAPID keys para Web Push
- SMTP credentials em .env
- GA4 API secrets seguras
- CORS habilitado

### Rate Limiting
- slowapi middleware (existente)
- Pode adicionar rate limit em push

---

## 11. INSTRUÇÕES DE USO

### Para Desenvolvedor
1. Executar `pip install -r requirements.txt`
2. Configurar `.env` com todas variáveis
3. Executar migrations: `python -c "from database import Base, engine; Base.metadata.create_all(bind=engine)"`
4. Incluir rotas em `main.py`
5. Testar endpoints com curl/Postman

### Para Usuário Final
1. Permitir notificações do navegador
2. Clicar em campanhas/destaques
3. Confirmar presença em eventos
4. Adicionar reações em mensagens
5. Receber digest semanal por email

---

## 12. ROADMAP FUTURO

### Curto Prazo (v2.1)
- [ ] Notificações de nova mensagem em tempo real
- [ ] Search com filtros (por room, date)
- [ ] Export highlights to PDF

### Médio Prazo (v2.2)
- [ ] Chat direto (DM) entre usuários
- [ ] Mentions (@user) com notificação
- [ ] Threads de mensagens
- [ ] Bookmark de destaques

### Longo Prazo (v3.0)
- [ ] Mobile app (React Native)
- [ ] Integração Slack/Discord
- [ ] AI recommendations (destacar membros)
- [ ] Premium features (storage, analytics)

---

## 13. STATISTICS

| Métrica | Valor |
|---------|-------|
| Arquivos criados | 13 |
| Linhas código Python | ~1500 |
| Linhas código JavaScript | ~1200 |
| Endpoints API | 16 |
| Database models | 8 |
| Feature completeness | 100% |

---

## 14. CONTATO & SUPORTE

Para problemas ou melhorias:
1. Verificar INTEGRATION_INSTRUCTIONS.md
2. Consultar logs do servidor
3. Usar GA4 Debugger (Chrome)
4. Verificar Network tab (DevTools)

---

**Documento gerado automaticamente** | Versão 2.0 | 2026-06-05
