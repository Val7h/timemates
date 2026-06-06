# Teste de Integração - TimeMates v2

Guia rápido para testar todos os features sem sair do browser.

---

## SETUP INICIAL

Abra o console do browser (F12 → Console) e execute:

```javascript
// Verifica se todos os managers foram carregados
console.log('notificationManager:', !!window.notificationManager);
console.log('presenceManager:', !!window.presenceManager);
console.log('reactionsManager:', !!window.reactionsManager);
console.log('trackingService:', !!window.trackingService);
console.log('navigationManager:', !!window.navigationManager);
```

Esperado: todos devem retornar `true`

---

## TESTE 1: Web Push Notifications

### Setup
```javascript
// Solicita permissão
await notificationManager.setupPushNotifications();
// Você verá um popup do navegador
// Clique "Permitir"
```

### Testar notificação in-app
```javascript
notificationManager.showInAppNotification(
    'Teste de Notificação',
    'Esta é uma notificação de teste do TimeMates!',
    { duration: 5000 }
);
```

Esperado: Notificação aparece no topo direito e desaparece após 5s

### Testar carregamento de notificações
```javascript
await notificationManager.loadNotifications();
console.log('Notificações carregadas');
```

---

## TESTE 2: Presença Online

### Conectar a uma room
```javascript
presenceManager.connectToRoom(1, 123); // room_id=1, user_id=123
```

Esperado: Console log "[Presence] WebSocket conectado à room 1"

### Carregar usuários online
```javascript
await presenceManager.loadPresence();
console.log('Usuários online:', presenceManager.onlineUsers);
```

Esperado: Array com usuários atualmente online

### Testar evento de presença
```javascript
window.addEventListener('presenceUpdated', (event) => {
    console.log('Presença atualizada:', event.detail.count, 'pessoas online');
});
```

---

## TESTE 3: Reações em Mensagens

### Setup (em uma mensagem existente)
```javascript
const messageId = 1; // Use um ID real de mensagem

// Carregar reações
await reactionsManager.loadReactions(messageId);
console.log('Reações:', reactionsManager.messageReactions[messageId]);
```

Esperado: Array com reações (se houver)

### Adicionar reação
```javascript
await reactionsManager.addReaction(messageId, '👍');
console.log('Reação adicionada');
```

Esperado: Chamada bem-sucedida ao endpoint

### Testar picker de emojis
```javascript
// Cria um botão fake para testar
const fakeBtn = document.createElement('button');
fakeBtn.textContent = '+';
reactionsManager.showEmojiPicker({ target: fakeBtn }, messageId);
```

Esperado: Picker aparece com emojis disponíveis

### Carregar top messages
```javascript
const messages = [
    { id: 1, content: 'Oi', user: { full_name: 'João' } },
    { id: 2, content: 'Olá', user: { full_name: 'Maria' } }
];

const topMessages = reactionsManager.getTopMessages(messages, 5);
console.log('Top messages:', topMessages);
```

---

## TESTE 4: Navegação com Dropdowns

### Testar navegação
```javascript
navigationManager.navigateToPage('news');
// URL deve mudar para /#news
console.log('Página atual:', navigationManager.currentPage);
```

### Testar dropdowns (manual)
```javascript
// Clique no dropdown de "Eventos" no navbar
// Ou teste via JavaScript:
const dropdownBtn = document.getElementById('events-dropdown-btn');
dropdownBtn.click();
// Menu deve aparecer
```

### Verificar active state
```javascript
const newsBtn = document.querySelector('[data-page="news"]');
console.log('Classe active?', newsBtn.classList.contains('active'));
```

---

## TESTE 5: Google Analytics Tracking

### Verificar se GA4 está carregado
```javascript
console.log('gtag disponível?', !!window.gtag);
console.log('GA4 ID:', window.GA4_MEASUREMENT_ID);
```

Esperado: `true` e um ID do tipo `G-XXXXXXXXXX`

### Rastrear evento de teste
```javascript
trackingService.trackNewsClick(123, 'Notícia de Teste');
// Verá log no console: [GA4] click_news...
```

### Rastrear RSVP
```javascript
trackingService.trackRsvpEvent(456, 789, 'going');
// Log: [GA4] rsvp_event...
```

### Rastrear reação
```javascript
trackingService.trackReactionAdded(1, 2, '👍');
// Log: [GA4] reaction_added...
```

### Testar properties do usuário
```javascript
trackingService.setUserProperties({
    user_city: 'Rio de Janeiro',
    user_level: 'premium'
});
```

### Ver no GA4 Debugger
1. Instalar extensão "Google Analytics Debugger" no Chrome
2. Abrir DevTools → Google Analytics
3. Será exibido em tempo real o que está sendo rastreado

---

## TESTE 6: Integrações Combinadas

### Cenário 1: Usuário entra em room
```javascript
// Simula entrada em room
presenceManager.connectToRoom(1, 123);
trackingService.trackPresenceOnline(1);
navigationManager.navigateToPage('room');
```

### Cenário 2: Vê notícia e confirma RSVP
```javascript
trackingService.trackNewsClick(1, 'Reunião confirmada');
notificationManager.showInAppNotification(
    'Reunião confirmada',
    'Clique para confirmar presença'
);

setTimeout(() => {
    trackingService.trackRsvpEvent(1, 2, 'going');
    notificationManager.showInAppNotification(
        'RSVP Confirmado',
        'Você confirmou presença no evento'
    );
}, 2000);
```

### Cenário 3: Mensagem recebe reações
```javascript
await reactionsManager.addReaction(1, '👍');
await reactionsManager.addReaction(1, '❤️');
await reactionsManager.addReaction(1, '🔥');

// Simula top message
reactionsManager.renderHighlights(
    document.body,
    [{ id: 1, content: 'Ótima mensagem!', user: { full_name: 'João' } }]
);

trackingService.trackViewHighlights(2, 1);
```

---

## TESTE 7: Event Listeners

### Verificar eventos customizados
```javascript
// Listen para notificações carregadas
window.addEventListener('notificationsLoaded', (e) => {
    console.log('Notificações:', e.detail.notifications.length);
});

// Listen para presença atualizada
window.addEventListener('presenceUpdated', (e) => {
    console.log('Presença atualizada:', e.detail.count);
});

// Listen para navegação
window.addEventListener('navigationChange', (e) => {
    console.log('Página mudou para:', e.detail.page);
});

// Trigger manual
window.dispatchEvent(new CustomEvent('notificationsLoaded', {
    detail: { notifications: [], unreadCount: 5 }
}));
```

---

## TESTE 8: Service Worker

### Verificar registração
```javascript
navigator.serviceWorker.getRegistrations()
    .then(regs => {
        console.log('Service Workers registrados:', regs.length);
        regs.forEach(reg => console.log(reg.scope));
    });
```

Esperado: Um registro com scope `/`

### Testar push notification (browser)
```javascript
// Requer push subscription válida primeiro
navigator.serviceWorker.ready.then(reg => {
    reg.pushManager.getSubscription().then(sub => {
        if (sub) {
            console.log('Subscription ativa:', sub.endpoint.substring(0, 50) + '...');
        } else {
            console.log('Nenhuma subscription ativa');
        }
    });
});
```

---

## TESTE 9: Armazenamento Local

### Verificar dados salvos
```javascript
console.log('User data:', JSON.parse(localStorage.getItem('user_data')));
console.log('Access token:', localStorage.getItem('access_token')?.substring(0, 20) + '...');
```

### Simular logout
```javascript
localStorage.removeItem('access_token');
localStorage.removeItem('user_data');
window.location.href = '/';
```

---

## TESTE 10: Performance

### Medir tempo de carregamento
```javascript
console.time('notificações');
await notificationManager.loadNotifications();
console.timeEnd('notificações');
```

Esperado: < 500ms

### Verificar tamanho do bundle
```javascript
console.log('JS files loaded:');
document.querySelectorAll('script[src]').forEach(s => {
    console.log('  -', s.src);
});
```

---

## CHECKLIST FINAL

Marque cada teste conforme completa:

```
TESTES BÁSICOS
[ ] Web Push funciona
[ ] In-app notifications aparecem
[ ] Presença online carrega
[ ] Reações adicionam/removem
[ ] Navegação muda páginas
[ ] GA4 rastreia eventos

TESTES AVANÇADOS
[ ] WebSocket conecta e reconecta
[ ] Top messages renderizam
[ ] Dropdowns abrem/fecham
[ ] Event listeners disparam
[ ] Service Worker registra
[ ] Dados salvos em localStorage

TESTES DE INTEGRAÇÃO
[ ] Fluxo completo: entrar → reação → RSVP
[ ] GA4 mostra eventos em tempo real
[ ] Presença atualiza em tempo real
[ ] Notificações push entregam
[ ] Email digest envia (segunda 10am)

TESTES DE PERFORMANCE
[ ] Carregamento < 500ms
[ ] Reações respondem < 200ms
[ ] WebSocket latência < 100ms
[ ] Sem memory leaks após 1h uso
```

---

## COMANDOS ÚTEIS

### Limpar tudo
```javascript
localStorage.clear();
navigator.serviceWorker.getRegistrations().then(regs => {
    regs.forEach(r => r.unregister());
});
```

### Recarregar e testar
```javascript
location.reload(); // Recarrega página
```

### Logs estruturados
```javascript
const test = (name, fn) => {
    try {
        fn();
        console.log(`✅ ${name}`);
    } catch (e) {
        console.error(`❌ ${name}:`, e.message);
    }
};

test('Notificações', () => {
    if (!window.notificationManager) throw new Error('Manager não carregado');
});
```

---

**Testes completos = Integração pronta para produção!**
