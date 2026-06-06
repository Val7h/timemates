# Plano de Integração - TimeMates v2

Integração de:
1. **Notificações** (push, email, digest)
2. **Online Status** (presença em tempo real)
3. **Reações em Tempo Real** (emojis nas mensagens)
4. **Navegação** (Abas, Dropdown)
5. **Tracking** (GA4)

---

## 1. NOTIFICAÇÕES

### Tipos
- **Breaking News Alert**: Alerta push quando há notícia importante
- **Event Reminder**: Notificação 24h antes do evento
- **Weekly Digest**: Resume semanal (segunda 10am)

### Implementação
- Backend: `/notification-routes.py` (FastAPI)
- Database: Modelos `Notification`, `PushSubscription`, `EmailLog`
- Frontend: Service Worker + Notification API
- Task scheduler: APScheduler para digests

---

## 2. ONLINE STATUS

### Features
- "5 pessoas indo" no evento
- Avatares de RSVPs
- Indicador de presença em tempo real

### Implementação
- WebSocket `/ws/event/{event_id}` para presença
- Modelo `UserPresence` (room_id, user_id, online_at)
- Frontend: Cache de avatares dos RSVPs

---

## 3. REAÇÕES EM TEMPO REAL

### Features
- Emojis nas mensagens (👍, ❤️, 🔥, etc)
- Top messages baseado em reactions

### Implementação
- Modelo `MessageReaction` (message_id, user_id, emoji)
- WebSocket broadcast de reações
- Ranking por count de reactions

---

## 4. NAVEGAÇÃO

### Estrutura
```
Nav:
├─ [Logo] [Notícias] [Eventos ▼] [Perfil]
   └─ Dropdown Eventos:
      ├─ Próximos eventos
      ├─ Meus eventos
      └─ Criar evento
```

### Implementação
- Tab "Notícias" no nav
- Dropdown para "Eventos"
- Active state baseado em rota

---

## 5. TRACKING (GA4)

### Eventos
- `click_news`: Clique em notícia
- `rsvp_event`: RSVP confirmado
- `view_highlights`: Visualização de destaques
- `reaction_added`: Reação adicionada
- `presence_online`: Usuário online

### Implementação
- Google Analytics 4 script no HTML
- Função `trackEvent(name, params)` em JS
- Custom user_id em GA4

---

## Estrutura de Arquivos

```
timeMates/
├── main.py                    (existente)
├── database.py                (existente + novos modelos)
├── notification_routes.py     (NOVO)
├── notification_service.py    (NOVO)
├── tracking_service.py        (NOVO)
├── static/
│   ├── index.html             (existente + GA4 + nav)
│   ├── js/
│   │   ├── notifications.js   (NOVO)
│   │   ├── presence.js        (NOVO)
│   │   ├── reactions.js       (NOVO)
│   │   ├── tracking.js        (NOVO)
│   │   └── nav.js             (NOVO)
│   ├── sw.js                  (Service Worker, NOVO)
│   └── manifest.json          (existente + push)
└── requirements.txt           (adicionar: APScheduler, google-analytics-python)
```

---

## Timeline de Integração

1. **Fase 1**: Modelos DB + Backend routes (3h)
2. **Fase 2**: Notificações push + email (4h)
3. **Fase 3**: Presença online + WebSocket (3h)
4. **Fase 4**: Reações em tempo real (2h)
5. **Fase 5**: Navegação + UI (2h)
6. **Fase 6**: Tracking GA4 (1h)
7. **Testes**: Integração completa (2h)

**Total: ~17h de desenvolvimento**

---

Arquivos detalhados nos próximos blocos de código.
