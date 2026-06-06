# TimeMates Chat - Documentação Completa

Um sistema de chat em tempo real com vanilla JavaScript puro. Implementa:

1. **Widget de Usuários Online** - Atualiza a cada 2 segundos
2. **Notificações de Entrada** - Toast quando usuários entram
3. **Reações em Tempo Real** - Sem refresh necessário
4. **Push Notifications** - Com Service Worker

---

## Instalação

### 1. Incluir os arquivos no HTML

```html
<!DOCTYPE html>
<html>
<head>
  <link rel="stylesheet" href="/chat.css" />
</head>
<body>
  <!-- Seu HTML aqui -->
  
  <script src="/chat.js"></script>
  <script>
    // Inicializar (ver seções abaixo)
  </script>
</body>
</html>
```

### 2. Requisitos de Backend

Sua API deve implementar os seguintes endpoints:

```
GET /api/rooms/{room_id}/online-users
```

Resposta esperada:
```json
{
  "users": [
    {
      "id": "user-123",
      "name": "João Silva"
    },
    {
      "id": "user-456",
      "name": "Maria Santos"
    }
  ]
}
```

---

## Uso

### A. Online Users Widget

#### Inicialização automática

Adicione o atributo `data-timemates-chat` no container:

```html
<div id="online-users-widget" data-timemates-chat data-room-id="room-123"></div>
```

O widget será inicializado automaticamente ao carregar a página.

#### Inicialização manual

```javascript
const onlineUsers = new window.TimeMatesChat.OnlineUsersWidget(
  'container-id',  // ID do elemento
  'room-123'       // ID da sala
);

// Depois, para limpar:
onlineUsers.destroy();
```

#### Método: loadOnlineUsers()

Carrega manualmente os usuários online:

```javascript
onlineUsers.loadOnlineUsers();
```

#### Customizar cores

A classe `getColorFromUserId()` gera cores automaticamente baseadas no ID do usuário.
Para customizar, sobrescreva o método:

```javascript
onlineUsers.getColorFromUserId = function(userId) {
  const colors = ['#FF6B6B', '#4ECDC4', '#45B7D1'];
  return colors[Math.abs(userId.length % colors.length)];
};
```

---

### B. Notificações de Entrada (User Joined)

Requer WebSocket ativo. O servidor deve enviar mensagens com este formato:

```json
{
  "type": "user_joined",
  "data": {
    "userName": "João Silva"
  }
}
```

#### Inicialização

```javascript
const ws = new WebSocket('wss://seu-servidor.com/ws/room-123');

const notifier = new window.TimeMatesChat.UserJoinedNotifier(ws);
```

#### ou via factory function

```javascript
const chat = window.TimeMatesChat.init({
  roomId: 'room-123',
  webSocket: ws
});
```

#### Customizar mensagem

O método `showJoinNotification()` pode ser sobrescrito:

```javascript
notifier.showJoinNotification = function(data) {
  const { userName } = data;
  console.log(`${userName} chegou!`);
  // Sua lógica customizada
};
```

---

### C. Reações em Tempo Real

O servidor deve enviar mensagens com este formato:

```json
{
  "type": "reaction_added",
  "data": {
    "messageId": "msg-123",
    "emoji": "👍",
    "userId": "user-456",
    "userName": "Maria Santos"
  }
}
```

#### Inicialização

```javascript
const ws = new WebSocket('wss://seu-servidor.com/ws/room-123');

const reactions = new window.TimeMatesChat.ReactionHandler(ws);
```

#### Estrutura de mensagens no DOM

Suas mensagens devem ter `data-message-id`:

```html
<div class="message" data-message-id="msg-123">
  <div class="message-author">João Silva</div>
  <div class="message-content">Olá pessoal!</div>
  <!-- Container de reações será criado automaticamente -->
</div>
```

#### Método: handleReactionAdded()

Processa uma reação manualmente:

```javascript
reactions.handleReactionAdded({
  messageId: 'msg-123',
  emoji: '👍',
  userId: 'user-456',
  userName: 'Maria Santos'
});
```

#### Customizar aparência de reações

Sobrescreva `createReactionElement()`:

```javascript
reactions.createReactionElement = function(emoji, userName) {
  const div = document.createElement('div');
  div.className = 'custom-reaction';
  div.textContent = emoji;
  return div;
};
```

---

### D. Push Notifications

#### Requisitos

1. HTTPS obrigatório
2. Service Worker registrado em `/sw.js` ou customizado
3. Permissão do usuário

#### Inicialização automática

```javascript
const pushManager = new window.TimeMatesChat.PushNotificationManager();
```

O manager faz tudo automaticamente:
- ✅ Registra Service Worker se não existir
- ✅ Verifica permissão
- ✅ Pede permissão se necessário
- ✅ Mostra modal com contexto se foi negada

#### Verificar estado

```javascript
console.log(pushManager.permission); // 'granted', 'denied', 'default'
```

#### Customizar Service Worker

```javascript
const pushManager = new window.TimeMatesChat.PushNotificationManager();

// Após criação, modifique o escopo se necessário
navigator.serviceWorker.register('/meu-sw.js', {
  scope: '/chat/'
});
```

---

## Factory Function (Recomendado)

Use `window.TimeMatesChat.init()` para inicializar tudo de uma vez:

```javascript
const chat = window.TimeMatesChat.init({
  roomId: 'room-123',          // obrigatório
  containerId: 'online-users-widget',  // padrão: 'online-users-widget'
  webSocket: ws                 // opcional
});

// Acesso aos componentes
chat.onlineUsersWidget;      // OnlineUsersWidget instance
chat.userJoinedNotifier;     // UserJoinedNotifier instance
chat.reactionHandler;        // ReactionHandler instance
chat.pushManager;            // PushNotificationManager instance

// Limpeza
chat.destroy(); // Limpa timers e listeners
```

---

## Exemplo Completo

```html
<!DOCTYPE html>
<html>
<head>
  <link rel="stylesheet" href="/chat.css" />
</head>
<body>
  <div id="online-users-widget" data-timemates-chat data-room-id="room-123"></div>

  <div id="chat-messages"></div>

  <script src="/chat.js"></script>
  <script>
    // Conectar WebSocket
    const ws = new WebSocket('wss://seu-servidor.com/ws/room-123');

    // Inicializar todos os componentes
    const chat = window.TimeMatesChat.init({
      roomId: 'room-123',
      webSocket: ws
    });

    // Monitorar conexão
    ws.addEventListener('open', () => {
      console.log('WebSocket conectado');
    });

    ws.addEventListener('error', (error) => {
      console.error('Erro WebSocket:', error);
    });

    // Reconectar automaticamente
    ws.addEventListener('close', () => {
      setTimeout(() => {
        window.location.reload();
      }, 3000);
    });
  </script>
</body>
</html>
```

---

## API Customização

### Classe OnlineUsersWidget

```javascript
class OnlineUsersWidget {
  constructor(containerId, roomId)
  init()
  loadOnlineUsers()
  updateUsersList(users)
  createUserElement(user)
  updateCount(count)
  getInitials(name)
  getColorFromUserId(userId)
  destroy()
}
```

### Classe UserJoinedNotifier

```javascript
class UserJoinedNotifier {
  constructor(webSocket)
  createToastContainer()
  setupListener()
  showJoinNotification(data)
}
```

### Classe ReactionHandler

```javascript
class ReactionHandler {
  constructor(webSocket)
  setupListener()
  handleReactionAdded(data)
  createReactionElement(emoji, userName)
  incrementReactionCount(reactionElement, userName)
  showReactionTooltip(element, users)
}
```

### Classe PushNotificationManager

```javascript
class PushNotificationManager {
  constructor()
  init()
  registerServiceWorker()
  requestPermission()
  requestPermissionWithContext()
  showTestNotification()
}
```

---

## Estrutura de Estilos (CSS)

Todos os estilos estão em `chat.css`. Classes disponíveis:

### Online Users Widget
- `.online-users-widget` - Container principal
- `.online-users-header` - Header do widget
- `.online-users-list` - Lista de usuários
- `.online-user-item` - Item individual
- `.online-user-avatar` - Avatar do usuário
- `.online-user-name` - Nome do usuário
- `.online-status-dot` - Indicador de status

### Toasts
- `.toast-container` - Container de notificações
- `.toast` - Toast individual
- `.toast.show` - Estado visível
- `.toast-join` - Toast de entrada

### Reações
- `.message-reactions` - Container de reações
- `.message-reaction` - Reação individual
- `.reaction-emoji` - Emoji da reação
- `.reaction-count` - Contador
- `.reaction-tooltip` - Tooltip ao hover

### Modal
- `.notification-permission-modal` - Modal de permissão
- `.notification-permission-content` - Conteúdo
- `.notification-permission-buttons` - Botões

---

## Responsividade

O sistema é totalmente responsivo e funciona em:
- ✅ Desktop (1920px+)
- ✅ Tablet (768px - 1024px)
- ✅ Mobile (320px - 767px)

Breakpoints:
- `@media (max-width: 768px)` - Tablets
- `@media (max-width: 480px)` - Mobiles

---

## Debugging

### Habilitar logs

```javascript
// Todos os console.log() estão já no código
// Abra DevTools (F12) para ver logs em tempo real

// Customizar logger
window.TimeMatesChat.logger = {
  log: (msg) => console.log('[TimeMates]', msg),
  error: (msg) => console.error('[TimeMates Error]', msg)
};
```

### Monitorar atualizações de usuários

```javascript
const originalUpdate = chat.onlineUsersWidget.updateUsersList.bind(chat.onlineUsersWidget);
chat.onlineUsersWidget.updateUsersList = function(users) {
  console.log('Usuários online atualizados:', users);
  return originalUpdate(users);
};
```

---

## Performance

- ✅ Vanilla JavaScript (sem dependências)
- ✅ Atualização a cada 2s (configurável)
- ✅ DOM manipulation otimizado (delta updates)
- ✅ Memory efficient (Map para usuários)
- ✅ Animações com CSS (GPU accelerated)

### Otimizar requisições

Se o servidor está sobrecarregado, aumente o intervalo:

```javascript
onlineUsers.updateInterval = setInterval(
  () => onlineUsers.loadOnlineUsers(),
  5000  // 5 segundos em vez de 2
);
```

---

## Compatibilidade

- ✅ Chrome/Edge 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Mobile browsers (iOS Safari, Chrome Mobile)
- ✅ Service Workers (HTTPS necessário)

---

## Licença

Desenvolvido para TimeMates. Uso livre no projeto.
