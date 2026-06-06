# Testes - TimeMates Chat

Guia completo para testar todas as funcionalidades do sistema de chat.

---

## Testes Unitários (Manual)

### 1. Online Users Widget

```javascript
// Abrir DevTools (F12) e executar:

// Teste 1: Inicialização
const widget = new window.TimeMatesChat.OnlineUsersWidget('online-users-widget', 'room-123');
console.assert(document.querySelector('.online-users-widget'), 'Widget criado');

// Teste 2: Carregamento de usuários
await widget.loadOnlineUsers();
const users = document.querySelectorAll('.online-user-item');
console.log('Usuários carregados:', users.length);

// Teste 3: Dinâmica de usuários
const mockUsers = [
  { id: 'user-1', name: 'João Silva' },
  { id: 'user-2', name: 'Maria Santos' }
];
widget.updateUsersList(mockUsers);
console.assert(document.querySelectorAll('.online-user-item').length === 2, 'Usuários adicionados');

// Teste 4: Remover usuário
widget.updateUsersList([mockUsers[0]]);
console.assert(document.querySelectorAll('.online-user-item').length === 1, 'Usuário removido');

// Teste 5: Cores
const colors = [widget.getColorFromUserId('user-1'), widget.getColorFromUserId('user-2')];
console.log('Cores atribuídas:', colors);
console.assert(colors[0] !== colors[1], 'Cores diferentes para usuários diferentes');

// Teste 6: Iniciais
console.assert(widget.getInitials('João Silva') === 'JS', 'Iniciais corretas');
console.assert(widget.getInitials('A') === 'A', 'Uma inicial');
```

### 2. User Joined Notifier

```javascript
// Simular WebSocket
const mockWs = new EventTarget();

// Teste 1: Inicialização
const notifier = new window.TimeMatesChat.UserJoinedNotifier(mockWs);
console.assert(document.getElementById('toast-container'), 'Toast container criado');

// Teste 2: Mostrar notificação
notifier.showJoinNotification({ userName: 'João Silva' });
const toast = document.querySelector('.toast');
console.assert(toast, 'Toast criado');
console.assert(toast.textContent.includes('João Silva'), 'Nome do usuário na notificação');

// Teste 3: Auto-desaparição
setTimeout(() => {
  const toastRemoved = !document.querySelector('.toast');
  console.assert(toastRemoved, 'Toast desapareceu após 3 segundos');
}, 3500);

// Teste 4: Múltiplas notificações
notifier.showJoinNotification({ userName: 'Maria' });
notifier.showJoinNotification({ userName: 'Pedro' });
const toasts = document.querySelectorAll('.toast');
console.assert(toasts.length === 2, 'Múltiplas notificações funcionam');

// Teste 5: Listener WebSocket
const event = new MessageEvent('message', {
  data: JSON.stringify({
    type: 'user_joined',
    data: { userName: 'Ana' }
  })
});
mockWs.dispatchEvent(event);
// Verificar se notificação foi mostrada
console.log('Listener WebSocket funcionando');
```

### 3. Reaction Handler

```javascript
// Teste 1: Inicialização
const mockWs = new EventTarget();
const reactionHandler = new window.TimeMatesChat.ReactionHandler(mockWs);
console.assert(reactionHandler, 'ReactionHandler criado');

// Criar mensagem de teste no DOM
const messageEl = document.createElement('div');
messageEl.className = 'message';
messageEl.setAttribute('data-message-id', 'msg-1');
messageEl.textContent = 'Mensagem de teste';
document.body.appendChild(messageEl);

// Teste 2: Adicionar reação
reactionHandler.handleReactionAdded({
  messageId: 'msg-1',
  emoji: '👍',
  userId: 'user-1',
  userName: 'João'
});

const reactionsContainer = messageEl.querySelector('.message-reactions');
console.assert(reactionsContainer, 'Container de reações criado');

const reaction = reactionsContainer.querySelector('[data-emoji="👍"]');
console.assert(reaction, 'Reação adicionada');
console.assert(reaction.textContent.includes('👍'), 'Emoji correto');

// Teste 3: Incrementar contador
const countBefore = parseInt(reaction.querySelector('.reaction-count').textContent);
reactionHandler.handleReactionAdded({
  messageId: 'msg-1',
  emoji: '👍',
  userId: 'user-2',
  userName: 'Maria'
});
const countAfter = parseInt(reaction.querySelector('.reaction-count').textContent);
console.assert(countAfter === countBefore + 1, 'Contador incrementado');

// Teste 4: Múltiplas reações
reactionHandler.handleReactionAdded({
  messageId: 'msg-1',
  emoji: '❤️',
  userId: 'user-3',
  userName: 'Pedro'
});
const reactions = reactionsContainer.querySelectorAll('.message-reaction');
console.assert(reactions.length === 2, 'Múltiplas reações diferentes');

// Teste 5: Tooltip
reaction.dispatchEvent(new MouseEvent('mouseenter'));
const tooltip = reaction.querySelector('.reaction-tooltip');
console.assert(tooltip, 'Tooltip criado ao hover');

// Limpeza
messageEl.remove();
```

### 4. Push Notification Manager

```javascript
// Teste 1: Inicialização
const pushManager = new window.TimeMatesChat.PushNotificationManager();
console.assert(pushManager, 'PushNotificationManager criado');
console.log('Permission:', pushManager.permission);

// Teste 2: Verificar Service Worker
navigator.serviceWorker.getRegistrations().then(registrations => {
  console.assert(registrations.length > 0, 'Service Worker registrado');
  console.log('SW Scopes:', registrations.map(r => r.scope));
});

// Teste 3: Permissão
if (Notification.permission === 'granted') {
  console.log('Push notifications já ativas');
} else if (Notification.permission === 'denied') {
  console.log('Push notifications negadas (pode ser solicitado novamente)');
} else {
  console.log('Permissão padrão (será solicitada ao usuário)');
}
```

---

## Testes de Integração

### Cenário 1: Full Flow com Mock Data

```html
<!DOCTYPE html>
<html>
<head>
  <link rel="stylesheet" href="/chat.css" />
</head>
<body>
  <div id="online-users-widget" data-timemates-chat data-room-id="room-123"></div>
  <div id="messages"></div>

  <script src="/chat.js"></script>
  <script>
    // Criar WebSocket mock
    class MockWebSocket extends EventTarget {
      constructor() {
        super();
        this.readyState = 1;
      }
      send(data) {
        console.log('Enviado:', data);
      }
      close() {
        this.readyState = 3;
      }
    }

    const ws = new MockWebSocket();

    // Inicializar
    const chat = window.TimeMatesChat.init({
      roomId: 'room-123',
      webSocket: ws
    });

    console.log('Sistema inicializado:', chat);

    // Simular eventos
    setTimeout(() => {
      console.log('Simulando entrada de usuário...');
      ws.dispatchEvent(new MessageEvent('message', {
        data: JSON.stringify({
          type: 'user_joined',
          data: { userName: 'João Silva' }
        })
      }));
    }, 1000);

    setTimeout(() => {
      console.log('Simulando reação...');

      // Criar mensagem
      const msg = document.createElement('div');
      msg.className = 'message';
      msg.setAttribute('data-message-id', 'msg-1');
      msg.innerHTML = '<div class="message-content">Olá!</div>';
      document.getElementById('messages').appendChild(msg);

      // Enviar reação
      ws.dispatchEvent(new MessageEvent('message', {
        data: JSON.stringify({
          type: 'reaction_added',
          data: {
            messageId: 'msg-1',
            emoji: '👍',
            userId: 'user-1',
            userName: 'Maria Santos'
          }
        })
      }));
    }, 3000);

    // Verificações
    setTimeout(() => {
      const toast = document.querySelector('.toast');
      const reaction = document.querySelector('.message-reaction');

      console.log('RESULTADOS:');
      console.log('✓ Toast exibido:', !!toast);
      console.log('✓ Reação adicionada:', !!reaction);
      console.log('✓ Widget online users:', !!document.querySelector('.online-users-widget'));
    }, 5000);
  </script>
</body>
</html>
```

---

## Testes de Performance

### Medir tempo de atualização

```javascript
// Teste com mock API
const startTime = performance.now();

const widget = new window.TimeMatesChat.OnlineUsersWidget('online-users-widget', 'room-123');
await widget.loadOnlineUsers();

const endTime = performance.now();
console.log(`Tempo de atualização: ${(endTime - startTime).toFixed(2)}ms`);
// Expected: < 100ms
```

### Medir memória

```javascript
if (performance.memory) {
  console.log('Antes:', {
    usedJSHeapSize: (performance.memory.usedJSHeapSize / 1048576).toFixed(2) + ' MB'
  });

  // Criar muitos widgets
  for (let i = 0; i < 100; i++) {
    const div = document.createElement('div');
    div.id = `widget-${i}`;
    document.body.appendChild(div);
    // Não inicializar para evitar requisições
  }

  console.log('Depois:', {
    usedJSHeapSize: (performance.memory.usedJSHeapSize / 1048576).toFixed(2) + ' MB'
  });
}
```

### Teste de DOM updates

```javascript
// Medir atualizações de usuários
const widget = new window.TimeMatesChat.OnlineUsersWidget('online-users-widget', 'room-123');

const observer = new PerformanceObserver((list) => {
  for (const entry of list.getEntries()) {
    console.log('Interaction:', {
      name: entry.name,
      duration: entry.duration.toFixed(2) + 'ms'
    });
  }
});

observer.observe({ entryTypes: ['measure', 'navigation'] });

// Simular atualização
const testUsers = Array.from({ length: 50 }, (_, i) => ({
  id: `user-${i}`,
  name: `User ${i}`
}));

performance.mark('update-start');
widget.updateUsersList(testUsers);
performance.mark('update-end');
performance.measure('update', 'update-start', 'update-end');
```

---

## Testes no Navegador (Checklist)

### Desktop (Chrome/Firefox/Safari)

- [ ] Online users widget carrega com sucesso
- [ ] Avatares exibem com cores diferentes
- [ ] Contagem de usuários atualiza a cada 2s
- [ ] Toast de entrada aparece quando usuário entra
- [ ] Toast desaparece após 3 segundos
- [ ] Reações adicionadas sem refresh
- [ ] Contador de reações incrementa
- [ ] Tooltip mostra usuários ao hover em reação
- [ ] Push notification é solicitada
- [ ] Service Worker é registrado (DevTools > Application > Service Workers)

### Mobile (iPhone Safari / Android Chrome)

- [ ] Layout responsivo em tela pequena
- [ ] Scrollbar funciona em lista de usuários
- [ ] Toasts visíveis em mobile
- [ ] Reações renderizam corretamente
- [ ] Touch events funcionam
- [ ] Notificações push funcionam

### Offline

- [ ] Service Worker cacheou assets
- [ ] Página carrega sem conexão
- [ ] WebSocket desconecta gracefully
- [ ] Mensagens são enfileiradas para sincronização

---

## Testes de Segurança

### XSS Prevention

```javascript
// Teste 1: Nomes com HTML
const widget = new window.TimeMatesChat.OnlineUsersWidget('online-users-widget', 'room-123');
widget.updateUsersList([{
  id: 'user-1',
  name: '<img src=x onerror="alert(\'XSS\')">'
}]);

// Verificar se HTML foi escapado
const nameEl = document.querySelector('.online-user-name');
console.assert(!nameEl.innerHTML.includes('onerror'), 'XSS prevenido');

// Teste 2: Emoji malicioso
const reaction = widget.createReactionElement('<img src=x>', 'User');
console.log('Reaction HTML:', reaction.innerHTML);
```

### CSRF Prevention

```javascript
// O chat.js não faz mutations, apenas reads
// Todo envio de dados deve ser via WebSocket ou fetch com CSRF token
```

---

## Teste de Compatibilidade

```javascript
// Verificar suporte de features
const support = {
  webSocket: 'WebSocket' in window,
  serviceWorker: 'serviceWorker' in navigator,
  notification: 'Notification' in window,
  fetch: 'fetch' in window,
  eventSource: 'EventSource' in window,
  indexedDB: 'indexedDB' in window,
  localStorage: 'localStorage' in window
};

console.table(support);
// All should be true para navegadores modernos
```

---

## Log de Testes

Template para registrar resultados:

```markdown
# Teste: [Data] - [Navegador] [Versão]

## Ambiente
- Navegador: 
- SO: 
- URL: 
- HTTPS: Sim/Não

## Testes
- [ ] Online Users Widget
- [ ] User Joined Toast
- [ ] Reactions
- [ ] Push Notifications
- [ ] Service Worker
- [ ] Offline Mode
- [ ] Responsividade

## Bugs Encontrados
1. 
2. 

## Performance
- Carregamento: ms
- Atualização usuários: ms
- Memória: MB

## Notas
```

---

## Testes Automatizados (Exemplo com Puppeteer)

```javascript
// test.js
const puppeteer = require('puppeteer');

describe('TimeMates Chat', () => {
  let browser;
  let page;

  before(async () => {
    browser = await puppeteer.launch();
    page = await browser.newPage();
    await page.goto('http://localhost:3000');
  });

  after(async () => {
    await browser.close();
  });

  it('should load online users widget', async () => {
    const widget = await page.$('.online-users-widget');
    expect(widget).toBeTruthy();
  });

  it('should show toast on user joined', async () => {
    await page.evaluate(() => {
      const notifier = new window.TimeMatesChat.UserJoinedNotifier(null);
      notifier.showJoinNotification({ userName: 'Test User' });
    });

    await page.waitForSelector('.toast');
    const text = await page.$eval('.toast', el => el.textContent);
    expect(text).toContain('Test User');
  });

  it('should add reaction to message', async () => {
    // ... mais testes
  });
});
```

---

## Checklist Final

Antes de ir para produção:

- [ ] Todos os testes passaram
- [ ] Sem errors no console
- [ ] Sem memory leaks
- [ ] HTTPS ativo
- [ ] Service Worker funcionando
- [ ] Push Notifications ativas
- [ ] WebSocket estável
- [ ] Responsividade OK
- [ ] Performance < 100ms
- [ ] Compatibilidade com navegadores modernos
- [ ] Documentação atualizada

Pronto para deploy!
