/**
 * TimeMates Chat - Vanilla JavaScript
 * Funcionalidades:
 * 1. Online Users Widget com atualização em tempo real
 * 2. Notificações de entrada de usuários
 * 3. Reações em tempo real nas mensagens
 * 4. Push Notifications com Service Worker
 */

// ============================================
// 1. ONLINE USERS WIDGET
// ============================================

class OnlineUsersWidget {
  constructor(containerId, roomId) {
    this.container = document.getElementById(containerId);
    this.roomId = roomId;
    this.onlineUsers = new Map();
    this.updateInterval = null;

    if (!this.container) {
      console.error(`Container with id "${containerId}" not found`);
      return;
    }

    this.init();
  }

  init() {
    this.container.innerHTML = `
      <div class="online-users-widget">
        <div class="online-users-header">
          <h3>Usuários Online</h3>
          <span class="online-count">0</span>
        </div>
        <div class="online-users-list"></div>
      </div>
    `;

    // Inicia carregamento a cada 2 segundos
    this.loadOnlineUsers();
    this.updateInterval = setInterval(() => this.loadOnlineUsers(), 2000);
  }

  async loadOnlineUsers() {
    try {
      const response = await fetch(`/api/rooms/${this.roomId}/online-users`);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      const users = data.users || [];

      // Atualizar lista de usuários online
      this.updateUsersList(users);
      this.updateCount(users.length);
    } catch (error) {
      console.error('Erro ao carregar usuários online:', error);
    }
  }

  updateUsersList(users) {
    const usersList = this.container.querySelector('.online-users-list');
    const newUserIds = new Set(users.map(u => u.id));
    const currentUserIds = new Set(this.onlineUsers.keys());

    // Remover usuários que foram embora
    for (const userId of currentUserIds) {
      if (!newUserIds.has(userId)) {
        const userElement = usersList.querySelector(`[data-user-id="${userId}"]`);
        if (userElement) {
          userElement.classList.add('removing');
          setTimeout(() => {
            userElement.remove();
          }, 300);
        }
        this.onlineUsers.delete(userId);
      }
    }

    // Adicionar ou atualizar usuários
    for (const user of users) {
      if (!this.onlineUsers.has(user.id)) {
        // Novo usuário
        const userElement = this.createUserElement(user);
        usersList.appendChild(userElement);
        this.onlineUsers.set(user.id, user);

        // Trigger animation
        setTimeout(() => {
          userElement.classList.add('added');
        }, 10);
      }
    }
  }

  createUserElement(user) {
    const div = document.createElement('div');
    div.className = 'online-user-item';
    div.setAttribute('data-user-id', user.id);
    div.title = user.name;

    const avatar = document.createElement('div');
    avatar.className = 'online-user-avatar';
    avatar.style.backgroundColor = this.getColorFromUserId(user.id);
    avatar.textContent = this.getInitials(user.name);

    const nameSpan = document.createElement('span');
    nameSpan.className = 'online-user-name';
    nameSpan.textContent = user.name;

    const statusDot = document.createElement('div');
    statusDot.className = 'online-status-dot';

    avatar.appendChild(statusDot);
    div.appendChild(avatar);
    div.appendChild(nameSpan);

    return div;
  }

  updateCount(count) {
    const countElement = this.container.querySelector('.online-count');
    if (countElement) {
      countElement.textContent = count;
    }
  }

  getInitials(name) {
    return name
      .split(' ')
      .map(part => part[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  }

  getColorFromUserId(userId) {
    const colors = [
      '#FF6B6B',
      '#4ECDC4',
      '#45B7D1',
      '#FFA07A',
      '#98D8C8',
      '#F7DC6F',
      '#BB8FCE',
      '#85C1E2'
    ];
    const hashCode = userId.split('').reduce((acc, char) => {
      return ((acc << 5) - acc) + char.charCodeAt(0);
    }, 0);
    return colors[Math.abs(hashCode) % colors.length];
  }

  destroy() {
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
    }
  }
}

// ============================================
// 2. NOTIFICAÇÃO DE ENTRADA
// ============================================

class UserJoinedNotifier {
  constructor(webSocket) {
    this.ws = webSocket;
    this.toastContainer = this.createToastContainer();
    this.setupListener();
  }

  createToastContainer() {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }
    return container;
  }

  setupListener() {
    if (this.ws) {
      this.ws.addEventListener('message', (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === 'user_joined') {
            this.showJoinNotification(message.data);
          }
        } catch (error) {
          console.error('Erro ao processar mensagem WebSocket:', error);
        }
      });
    }
  }

  showJoinNotification(data) {
    const { userName } = data;

    const toast = document.createElement('div');
    toast.className = 'toast toast-join';
    toast.innerHTML = `
      <span class="toast-icon">🟢</span>
      <span class="toast-message">${userName} entrou na sala</span>
    `;

    this.toastContainer.appendChild(toast);

    // Trigger animation
    setTimeout(() => {
      toast.classList.add('show');
    }, 10);

    // Remove após 3 segundos
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => {
        toast.remove();
      }, 300);
    }, 3000);
  }
}

// ============================================
// 3. REAÇÕES EM TEMPO REAL
// ============================================

class ReactionHandler {
  constructor(webSocket) {
    this.ws = webSocket;
    this.setupListener();
  }

  setupListener() {
    if (this.ws) {
      this.ws.addEventListener('message', (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === 'reaction_added') {
            this.handleReactionAdded(message.data);
          }
        } catch (error) {
          console.error('Erro ao processar reação:', error);
        }
      });
    }
  }

  handleReactionAdded(data) {
    const { messageId, emoji, userId, userName } = data;

    // Encontrar elemento da mensagem no DOM
    const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
    if (!messageElement) {
      console.warn(`Mensagem com ID ${messageId} não encontrada no DOM`);
      return;
    }

    // Encontrar ou criar container de reações
    let reactionsContainer = messageElement.querySelector('.message-reactions');
    if (!reactionsContainer) {
      reactionsContainer = document.createElement('div');
      reactionsContainer.className = 'message-reactions';
      messageElement.appendChild(reactionsContainer);
    }

    // Procurar reação existente
    let reactionElement = reactionsContainer.querySelector(
      `[data-emoji="${emoji}"]`
    );

    if (reactionElement) {
      // Aumentar contador
      this.incrementReactionCount(reactionElement, userName);
    } else {
      // Criar nova reação
      reactionElement = this.createReactionElement(emoji, userName);
      reactionsContainer.appendChild(reactionElement);

      // Trigger animation
      setTimeout(() => {
        reactionElement.classList.add('added');
      }, 10);
    }
  }

  createReactionElement(emoji, userName) {
    const div = document.createElement('div');
    div.className = 'message-reaction';
    div.setAttribute('data-emoji', emoji);
    div.innerHTML = `
      <span class="reaction-emoji">${emoji}</span>
      <span class="reaction-count">1</span>
    `;

    // Tooltip ao passar mouse
    div.title = userName;
    div.addEventListener('mouseenter', (e) => {
      this.showReactionTooltip(e.target, [userName]);
    });

    return div;
  }

  incrementReactionCount(reactionElement, userName) {
    const countSpan = reactionElement.querySelector('.reaction-count');
    if (countSpan) {
      let count = parseInt(countSpan.textContent) || 1;
      count++;
      countSpan.textContent = count;

      // Atualizar lista de usuários no tooltip
      const users = reactionElement.getAttribute('data-users')
        ? JSON.parse(reactionElement.getAttribute('data-users'))
        : [];

      if (!users.includes(userName)) {
        users.push(userName);
        reactionElement.setAttribute('data-users', JSON.stringify(users));
      }
    }
  }

  showReactionTooltip(element, users) {
    let tooltip = element.querySelector('.reaction-tooltip');

    if (!tooltip) {
      tooltip = document.createElement('div');
      tooltip.className = 'reaction-tooltip';
      element.appendChild(tooltip);
    }

    const userList = element.getAttribute('data-users')
      ? JSON.parse(element.getAttribute('data-users'))
      : users;

    tooltip.textContent = userList.join(', ');
    tooltip.style.display = 'block';

    element.addEventListener('mouseleave', () => {
      if (tooltip) {
        tooltip.style.display = 'none';
      }
    });
  }
}

// ============================================
// 4. PUSH NOTIFICATIONS
// ============================================

class PushNotificationManager {
  constructor() {
    this.permission = Notification.permission;
    this.init();
  }

  async init() {
    // Registrar Service Worker
    await this.registerServiceWorker();

    // Verificar permissão
    if (this.permission === 'granted') {
      console.log('Push notifications já estão ativas');
      return;
    }

    if (this.permission === 'denied') {
      this.requestPermissionWithContext();
      return;
    }

    // Default: 'default' - pedir permissão
    this.requestPermission();
  }

  async registerServiceWorker() {
    if ('serviceWorker' in navigator) {
      try {
        // Verificar se Service Worker já está registrado
        const registrations = await navigator.serviceWorker.getRegistrations();
        const alreadyRegistered = registrations.some(reg =>
          reg.scope.includes('/timeMates/')
        );

        if (!alreadyRegistered) {
          const registration = await navigator.serviceWorker.register('/sw.js', {
            scope: '/timeMates/'
          });
          console.log('Service Worker registrado:', registration);
        }
      } catch (error) {
        console.error('Erro ao registrar Service Worker:', error);
      }
    }
  }

  async requestPermission() {
    try {
      const permission = await Notification.requestPermission();
      this.permission = permission;

      if (permission === 'granted') {
        console.log('Permissão de notificações concedida');
        this.showTestNotification();
      }
    } catch (error) {
      console.error('Erro ao solicitar permissão:', error);
    }
  }

  requestPermissionWithContext() {
    // Mostrar modal com contexto de por que precisamos de notificações
    const modal = document.createElement('div');
    modal.className = 'notification-permission-modal';
    modal.innerHTML = `
      <div class="notification-permission-content">
        <h3>Habilitar Notificações?</h3>
        <p>Receba notificações quando novos usuários entrarem na sala e não perca mensagens importantes.</p>
        <div class="notification-permission-buttons">
          <button class="btn btn-primary" id="enable-notifications">
            Habilitar
          </button>
          <button class="btn btn-secondary" id="skip-notifications">
            Agora não
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    document.getElementById('enable-notifications').addEventListener('click', () => {
      this.requestPermission();
      modal.remove();
    });

    document.getElementById('skip-notifications').addEventListener('click', () => {
      modal.remove();
    });
  }

  showTestNotification() {
    if (this.permission === 'granted') {
      if ('serviceWorker' in navigator && 'ready' in navigator.serviceWorker) {
        navigator.serviceWorker.ready.then(registration => {
          registration.showNotification('TimeMates', {
            body: 'Notificações ativadas com sucesso!',
            icon: '/assets/icon.png',
            tag: 'timemates-test',
            requireInteraction: false
          });
        });
      }
    }
  }
}

// ============================================
// API PUBLICA
// ============================================

window.TimeMatesChat = {
  OnlineUsersWidget,
  UserJoinedNotifier,
  ReactionHandler,
  PushNotificationManager,

  // Factory function para inicializar tudo
  init(config = {}) {
    const {
      containerId = 'online-users-widget',
      roomId = null,
      webSocket = null
    } = config;

    if (!roomId) {
      console.error('roomId é obrigatório para inicializar TimeMatesChat');
      return;
    }

    // Inicializar Online Users Widget
    const onlineUsersWidget = new OnlineUsersWidget(containerId, roomId);

    // Inicializar WebSocket listeners se houver conexão
    let userJoinedNotifier = null;
    let reactionHandler = null;

    if (webSocket) {
      userJoinedNotifier = new UserJoinedNotifier(webSocket);
      reactionHandler = new ReactionHandler(webSocket);
    }

    // Inicializar Push Notifications
    const pushManager = new PushNotificationManager();

    return {
      onlineUsersWidget,
      userJoinedNotifier,
      reactionHandler,
      pushManager,
      destroy() {
        if (onlineUsersWidget) onlineUsersWidget.destroy();
      }
    };
  }
};

// Auto-init se houver elemento com id 'online-users-widget'
document.addEventListener('DOMContentLoaded', () => {
  // Apenas inicializa automaticamente se houver um data-attribute indicando
  const chatContainer = document.querySelector('[data-timemates-chat]');
  if (chatContainer) {
    const roomId = chatContainer.getAttribute('data-room-id');
    if (roomId) {
      window.TimeMatesChat.init({
        roomId: roomId,
        containerId: 'online-users-widget'
      });
    }
  }
});
