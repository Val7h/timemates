# Guia de Integração - TimeMates Chat

Passo a passo para integrar o sistema de chat em tempo real em seu projeto.

---

## Pré-requisitos

- Node.js com Express ou FastAPI (backend)
- WebSocket configurado para comunicação em tempo real
- HTTPS ativo (obrigatório para Service Worker/Push Notifications)
- Navegadores modernos (Chrome 90+, Firefox 88+, Safari 14+)

---

## Passo 1: Copiar arquivos

Copie para seu projeto `public/`:

```
public/
├── chat.js              ← Main script
├── chat.css             ← Estilos
├── sw.js                ← Service Worker
├── chat-example.html    ← Exemplo de uso
└── CHAT_README.md       ← Documentação
```

---

## Passo 2: Configurar HTML

Adicione no seu HTML (ex: `index.html`):

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <!-- ... outros meta tags ... -->
  
  <!-- Incluir CSS do Chat -->
  <link rel="stylesheet" href="/chat.css" />
</head>
<body>
  <!-- Seu layout -->
  <div class="app-container">
    <!-- Sidebar com usuários online -->
    <aside class="sidebar">
      <div 
        id="online-users-widget" 
        data-timemates-chat 
        data-room-id="room-123"
      ></div>
    </aside>

    <!-- Chat area -->
    <main class="chat-area">
      <div id="messages"></div>
      <input type="text" id="message-input" placeholder="Sua mensagem..." />
      <button id="send-btn">Enviar</button>
    </main>
  </div>

  <!-- Incluir Script do Chat (antes do seu script) -->
  <script src="/chat.js"></script>
  
  <!-- Seu script customizado -->
  <script src="/js/app.js"></script>
</body>
</html>
```

---

## Passo 3: Configurar WebSocket (Backend)

### FastAPI Example

```python
# main.py
from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
import json

app = FastAPI()

# Armazenar conexões ativas
connections = {}

@app.get("/api/rooms/{room_id}/online-users")
async def get_online_users(room_id: str):
    """Endpoint para obter usuários online"""
    users = connections.get(room_id, [])
    return {
        "users": [
            {"id": u["id"], "name": u["name"]}
            for u in users
        ]
    }

@app.websocket("/ws/room/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await websocket.accept()
    
    # Registrar usuário
    user_id = f"user-{len(connections)}"
    user_name = "Usuário" + str(len(connections))
    
    if room_id not in connections:
        connections[room_id] = []
    
    user = {"id": user_id, "name": user_name}
    connections[room_id].append(user)
    
    # Notificar que novo usuário entrou
    await broadcast_to_room(room_id, {
        "type": "user_joined",
        "data": {"userName": user_name}
    })
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "reaction_added":
                # Broadcast reação para todos
                await broadcast_to_room(room_id, message)
            elif message["type"] == "message":
                # Processar mensagem
                await broadcast_to_room(room_id, {
                    "type": "message",
                    "data": {
                        "messageId": message.get("id"),
                        "userId": user_id,
                        "userName": user_name,
                        "content": message.get("content")
                    }
                })
    except:
        pass
    finally:
        # Remover usuário
        connections[room_id].remove(user)

async def broadcast_to_room(room_id: str, message: dict):
    """Enviar mensagem para todos na sala"""
    for conn in connections.get(room_id, []):
        try:
            await conn.send(json.dumps(message))
        except:
            pass
```

### Express Example

```javascript
// server.js
const express = require('express');
const http = require('http');
const WebSocket = require('ws');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

const connections = {};

// Endpoint para usuários online
app.get('/api/rooms/:roomId/online-users', (req, res) => {
  const { roomId } = req.params;
  const users = connections[roomId] || [];
  res.json({
    users: users.map(u => ({ id: u.id, name: u.name }))
  });
});

// WebSocket
wss.on('connection', (ws, req) => {
  const roomId = req.url.split('/').pop();
  
  if (!connections[roomId]) {
    connections[roomId] = [];
  }

  const user = {
    id: `user-${Math.random()}`,
    name: `User ${connections[roomId].length}`,
    ws
  };

  connections[roomId].push(user);

  // Notificar entrada
  broadcastToRoom(roomId, {
    type: 'user_joined',
    data: { userName: user.name }
  });

  ws.on('message', (message) => {
    const data = JSON.parse(message);
    
    if (data.type === 'reaction_added') {
      broadcastToRoom(roomId, data);
    }
  });

  ws.on('close', () => {
    connections[roomId] = connections[roomId].filter(u => u !== user);
  });
});

function broadcastToRoom(roomId, message) {
  connections[roomId]?.forEach(user => {
    user.ws.send(JSON.stringify(message));
  });
}

server.listen(3000);
```

---

## Passo 4: Inicializar em JavaScript

### Opção A: Auto-init (Recomendado)

```javascript
// Adicione data-timemates-chat no HTML e deixe o chat.js auto-inicializar

// Conectar WebSocket
const ws = new WebSocket(`wss://${window.location.host}/ws/room/room-123`);

ws.addEventListener('error', (error) => {
  console.error('WebSocket error:', error);
});

// O chat.js irá inicializar automaticamente quando encontrar
// o elemento com data-timemates-chat
```

### Opção B: Inicialização Manual

```javascript
// app.js
const ws = new WebSocket(`wss://${window.location.host}/ws/room/room-123`);

const chat = window.TimeMatesChat.init({
  roomId: 'room-123',
  containerId: 'online-users-widget',
  webSocket: ws
});

// Acessar componentes
console.log(chat.onlineUsersWidget);  // OnlineUsersWidget
console.log(chat.userJoinedNotifier); // UserJoinedNotifier
console.log(chat.reactionHandler);    // ReactionHandler
console.log(chat.pushManager);        // PushNotificationManager
```

---

## Passo 5: Enviar Reações (Do Cliente)

```javascript
// Quando usuário clicar em um emoji de reação
document.addEventListener('click', (e) => {
  if (e.target.classList.contains('reaction-btn')) {
    const emoji = e.target.getAttribute('data-emoji');
    const messageId = e.target.closest('.message').getAttribute('data-message-id');

    // Enviar via WebSocket
    ws.send(JSON.stringify({
      type: 'reaction_added',
      data: {
        messageId,
        emoji,
        userId: getUserId(),
        userName: getUserName()
      }
    }));
  }
});
```

---

## Passo 6: Renderizar Mensagens

```javascript
// Adicionar mensagens ao DOM com estrutura correta
function addMessage(messageData) {
  const messageEl = document.createElement('div');
  messageEl.className = 'message';
  messageEl.setAttribute('data-message-id', messageData.id);
  messageEl.innerHTML = `
    <div class="message-author">${messageData.userName}</div>
    <div class="message-content">${messageData.content}</div>
    <div class="message-time">${new Date().toLocaleTimeString()}</div>
    <!-- Container de reações será criado automaticamente pelo ReactionHandler -->
  `;

  document.getElementById('messages').appendChild(messageEl);
}

// Listener no WebSocket para novas mensagens
ws.addEventListener('message', (event) => {
  const message = JSON.parse(event.data);

  if (message.type === 'message') {
    addMessage(message.data);
  }
  // reaction_added e user_joined são processados automaticamente pelo chat.js
});
```

---

## Passo 7: Testar Push Notifications

```javascript
// Forçar teste manual
chat.pushManager.showTestNotification();

// Ou enviar do servidor
POST /api/rooms/room-123/notify
{
  "title": "Teste",
  "body": "Notificação de teste",
  "userId": "user-123"
}
```

---

## Passo 8: Deploy com HTTPS

### Para produção:

```bash
# Gerar certificado SSL (Let's Encrypt recomendado)
certbot certonly --standalone -d seu-dominio.com

# Configurar Express
const https = require('https');
const fs = require('fs');

const options = {
  key: fs.readFileSync('/etc/letsencrypt/live/seu-dominio/privkey.pem'),
  cert: fs.readFileSync('/etc/letsencrypt/live/seu-dominio/cert.pem')
};

https.createServer(options, app).listen(443);

# Ou com FastAPI
uvicorn main:app --ssl-keyfile=/etc/letsencrypt/live/seu-dominio/privkey.pem \
                 --ssl-certfile=/etc/letsencrypt/live/seu-dominio/cert.pem
```

---

## Checklist de Integração

- [ ] Arquivos copiados para `public/`
- [ ] HTML atualizado com links para CSS e JS
- [ ] Backend implementado (FastAPI ou Express)
- [ ] WebSocket configurado e testado
- [ ] Endpoint `/api/rooms/{room_id}/online-users` ativo
- [ ] Broadcast de eventos `user_joined` e `reaction_added` funcionando
- [ ] HTTPS ativo (para Push Notifications)
- [ ] Service Worker em `/sw.js`
- [ ] Mensagens renderizadas com `data-message-id`
- [ ] Testes manuais em navegadores modernos

---

## Troubleshooting

### "Online users widget não carrega"

```javascript
// Verificar se container existe
console.log(document.getElementById('online-users-widget'));

// Verificar endpoint
fetch('/api/rooms/room-123/online-users')
  .then(r => r.json())
  .then(data => console.log('Users:', data));
```

### "WebSocket connection failed"

```javascript
// Verificar URL
console.log(`Tentando conectar em: wss://${window.location.host}/ws/room/room-123`);

// Verificar CORS headers no servidor
```

### "Reações não aparecem"

```javascript
// Verificar se mensagem tem data-message-id
document.querySelectorAll('.message').forEach(msg => {
  console.log('Message ID:', msg.getAttribute('data-message-id'));
});

// Verificar se reactionHandler está inicializado
console.log(chat.reactionHandler);
```

### "Push notifications não funcionam"

```javascript
// Verificar permissão
console.log('Notification permission:', Notification.permission);

// Verificar Service Worker
navigator.serviceWorker.getRegistrations()
  .then(registrations => console.log('SW Registrations:', registrations));

// Testar manualmente
Notification.requestPermission().then(perm => {
  console.log('Permission:', perm);
});
```

---

## Performance Tips

1. **Aumentar intervalo de atualização de usuários:**
   ```javascript
   // Default: 2000ms
   // Para reduzir carga, aumentar para 5000ms
   clearInterval(chat.onlineUsersWidget.updateInterval);
   chat.onlineUsersWidget.updateInterval = setInterval(
     () => chat.onlineUsersWidget.loadOnlineUsers(),
     5000
   );
   ```

2. **Limitar número de reações visíveis:**
   ```javascript
   // Adicionar limite antes de renderizar
   if (reactionsContainer.children.length > 10) {
     reactionsContainer.innerHTML += `
       <div class="more-reactions">+${extra}</div>
     `;
   }
   ```

3. **Usar debounce para atualizações:**
   ```javascript
   const debounce = (fn, delay) => {
     let timer;
     return (...args) => {
       clearTimeout(timer);
       timer = setTimeout(() => fn(...args), delay);
     };
   };
   ```

---

## Suporte

Para problemas ou dúvidas, consulte:
- `CHAT_README.md` - Documentação completa
- `chat-example.html` - Exemplo funcional
- Console do navegador (F12) para logs

Bom desenvolvimento!
