/**
 * notifications.js
 * Gerencia Web Push API, in-app notifications e service workers
 */

class NotificationManager {
  constructor() {
    this.serviceWorkerReady = false;
    this.subscriptionReady = false;
    this.unreadCount = 0;
    this.init();
  }

  async init() {
    try {
      // Registra service worker
      if ('serviceWorker' in navigator) {
        const registration = await navigator.serviceWorker.register('/static/sw.js');
        this.serviceWorkerReady = true;
        console.log('[Notifications] Service Worker registrado:', registration.scope);
      }

      // Verifica suporte a Push
      if ('PushManager' in window) {
        await this.setupPushNotifications();
      }

      // Carrega notificações do servidor
      await this.loadNotifications();

      // Verifica a cada 30s se há novas notificações
      setInterval(() => this.loadNotifications(), 30000);
    } catch (error) {
      console.error('[Notifications] Erro ao inicializar:', error);
    }
  }

  /**
   * Configura Web Push API
   */
  async setupPushNotifications() {
    try {
      const registration = await navigator.serviceWorker.ready;
      const permission = Notification.permission;

      console.log('[Notifications] Permissão:', permission);

      // Se permissão já foi negada, não tenta novamente
      if (permission === 'denied') {
        return;
      }

      // Se já está inscrito, não tenta novamente
      const subscription = await registration.pushManager.getSubscription();
      if (subscription) {
        this.subscriptionReady = true;
        await this.sendSubscriptionToServer(subscription);
        return;
      }

      // Se permissão é 'prompt', pede ao usuário
      if (permission === 'default') {
        const result = await Notification.requestPermission();
        if (result !== 'granted') {
          console.log('[Notifications] Usuário negou permissão');
          return;
        }
      }

      // Inscreve no push
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: this.urlBase64ToUint8Array(
          window.VAPID_PUBLIC_KEY || 'BAw8wy-xJ7F...' // Substituir com chave real
        )
      });

      this.subscriptionReady = true;
      await this.sendSubscriptionToServer(subscription);

      console.log('[Notifications] Inscrito no push com sucesso');
    } catch (error) {
      console.error('[Notifications] Erro ao configurar push:', error);
    }
  }

  /**
   * Envia subscription para o servidor
   */
  async sendSubscriptionToServer(subscription) {
    try {
      const response = await fetch('/api/push/subscribe', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(subscription)
      });

      if (response.ok) {
        console.log('[Notifications] Subscription enviada ao servidor');
      }
    } catch (error) {
      console.error('[Notifications] Erro ao enviar subscription:', error);
    }
  }

  /**
   * Carrega notificações do servidor
   */
  async loadNotifications() {
    try {
      const response = await fetch('/api/notifications?limit=20');
      if (!response.ok) return;

      const notifications = await response.json();
      this.unreadCount = notifications.filter(n => !n.is_read).length;
      this.updateBadge();

      // Dispara evento customizado
      window.dispatchEvent(new CustomEvent('notificationsLoaded', {
        detail: { notifications, unreadCount: this.unreadCount }
      }));
    } catch (error) {
      console.error('[Notifications] Erro ao carregar:', error);
    }
  }

  /**
   * Mostra notificação in-app
   */
  showInAppNotification(title, body, options = {}) {
    const container = document.getElementById('notifications-container');
    if (!container) return;

    const notification = document.createElement('div');
    notification.className = 'in-app-notification';
    notification.style.cssText = `
      background: white;
      border-left: 4px solid var(--primary);
      padding: 16px;
      margin-bottom: 12px;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      animation: slideIn 0.3s ease;
    `;

    notification.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: start; gap: 12px;">
        <div>
          <strong style="color: var(--primary);">${title}</strong>
          <p style="color: var(--muted); margin: 4px 0; font-size: 0.9rem;">${body}</p>
        </div>
        <button style="background: none; border: none; color: var(--muted); cursor: pointer; font-size: 1.2rem;">×</button>
      </div>
    `;

    const closeBtn = notification.querySelector('button');
    closeBtn.onclick = () => notification.remove();

    container.appendChild(notification);

    // Auto-remove após 5 segundos (ou customizável)
    setTimeout(() => {
      notification.style.animation = 'slideOut 0.3s ease';
      setTimeout(() => notification.remove(), 300);
    }, options.duration || 5000);
  }

  /**
   * Marca notificação como lida
   */
  async markAsRead(notificationId) {
    try {
      await fetch(`/api/notifications/${notificationId}/read`, {
        method: 'PATCH'
      });
      await this.loadNotifications();
    } catch (error) {
      console.error('[Notifications] Erro ao marcar como lida:', error);
    }
  }

  /**
   * Deleta notificação
   */
  async deleteNotification(notificationId) {
    try {
      await fetch(`/api/notifications/${notificationId}`, {
        method: 'DELETE'
      });
      await this.loadNotifications();
    } catch (error) {
      console.error('[Notifications] Erro ao deletar:', error);
    }
  }

  /**
   * Atualiza badge de notificações (ícone de sino)
   */
  updateBadge() {
    const badge = document.querySelector('.badge');
    if (!badge) return;

    if (this.unreadCount > 0) {
      badge.textContent = this.unreadCount > 99 ? '99+' : this.unreadCount;
      badge.classList.remove('hidden');
    } else {
      badge.classList.add('hidden');
    }
  }

  /**
   * Converte VAPID public key de string para Uint8Array
   */
  urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
      .replace(/\-/g, '+')
      .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }
}

// Inicializa globalmente
window.notificationManager = new NotificationManager();

// CSS para animações
const style = document.createElement('style');
style.textContent = `
  @keyframes slideIn {
    from {
      transform: translateX(-100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }

  @keyframes slideOut {
    from {
      transform: translateX(0);
      opacity: 1;
    }
    to {
      transform: translateX(-100%);
      opacity: 0;
    }
  }
`;
document.head.appendChild(style);
