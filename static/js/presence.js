/**
 * presence.js
 * Gerencia presença online em tempo real via WebSocket
 */

class PresenceManager {
  constructor() {
    this.roomId = null;
    this.userId = null;
    this.websocket = null;
    this.onlineUsers = [];
    this.updateInterval = null;

    // Listener para mudanças de visibilidade
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        this.setOffline();
      } else {
        this.setOnline();
      }
    });

    // Listener para saída da página
    window.addEventListener('beforeunload', () => {
      this.disconnect();
    });
  }

  /**
   * Conecta a uma room e estabelece WebSocket
   */
  async connectToRoom(roomId, userId) {
    this.roomId = roomId;
    this.userId = userId;

    try {
      // Conecta WebSocket
      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
      const wsUrl = `${protocol}://${window.location.host}/api/ws/room/${roomId}?user_id=${userId}`;

      this.websocket = new WebSocket(wsUrl);

      this.websocket.onopen = () => {
        console.log('[Presence] WebSocket conectado à room', roomId);
        this.setOnline();
      };

      this.websocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        this.handleMessage(data);
      };

      this.websocket.onerror = (error) => {
        console.error('[Presence] Erro WebSocket:', error);
      };

      this.websocket.onclose = () => {
        console.log('[Presence] WebSocket desconectado');
        // Tenta reconectar após 5 segundos
        setTimeout(() => this.connectToRoom(roomId, userId), 5000);
      };

      // Carrega lista de presença inicial
      await this.loadPresence();

      // Atualiza presença a cada 30 segundos
      this.updateInterval = setInterval(() => this.setOnline(), 30000);
    } catch (error) {
      console.error('[Presence] Erro ao conectar:', error);
    }
  }

  /**
   * Marca usuário como online
   */
  async setOnline() {
    if (!this.roomId) return;

    try {
      const response = await fetch('/api/presence/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ room_id: this.roomId })
      });

      if (!response.ok) {
        console.error('[Presence] Erro ao atualizar presença');
        return;
      }

      // Broadcast via WebSocket
      if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
        this.websocket.send(JSON.stringify({
          type: 'presence_update',
          action: 'online'
        }));
      }
    } catch (error) {
      console.error('[Presence] Erro ao atualizar:', error);
    }
  }

  /**
   * Marca usuário como offline
   */
  setOffline() {
    if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
      return;
    }

    this.websocket.send(JSON.stringify({
      type: 'presence_update',
      action: 'offline'
    }));
  }

  /**
   * Carrega lista de usuários online
   */
  async loadPresence() {
    if (!this.roomId) return;

    try {
      const response = await fetch(`/api/rooms/${this.roomId}/presence`);
      if (!response.ok) return;

      const data = await response.json();
      this.onlineUsers = data;
      this.updatePresenceUI();

      // Dispara evento customizado
      window.dispatchEvent(new CustomEvent('presenceUpdated', {
        detail: { onlineUsers: data, count: data.length }
      }));
    } catch (error) {
      console.error('[Presence] Erro ao carregar presença:', error);
    }
  }

  /**
   * Trata mensagens WebSocket
   */
  handleMessage(data) {
    if (data.type === 'presence_update') {
      if (data.action === 'online') {
        // Adiciona/atualiza usuário
        const index = this.onlineUsers.findIndex(u => u.user_id === data.user_id);
        if (index === -1) {
          this.onlineUsers.push({
            user_id: data.user_id,
            full_name: data.full_name || 'Usuário'
          });
        }
      } else if (data.action === 'offline') {
        // Remove usuário
        this.onlineUsers = this.onlineUsers.filter(u => u.user_id !== data.user_id);
      }
      this.updatePresenceUI();
    } else if (data.type === 'reaction_added' || data.type === 'message') {
      // Delegado para outros managers
      window.dispatchEvent(new CustomEvent('realtimeUpdate', { detail: data }));
    }
  }

  /**
   * Atualiza UI de presença
   */
  updatePresenceUI() {
    // Atualiza badge de "N pessoas online"
    const badge = document.querySelector('[data-presence-badge]');
    if (badge) {
      badge.textContent = `${this.onlineUsers.length} pessoa${this.onlineUsers.length !== 1 ? 's' : ''} online`;
    }

    // Atualiza lista de avatares
    const avatarList = document.querySelector('[data-presence-avatars]');
    if (avatarList) {
      avatarList.innerHTML = this.onlineUsers.slice(0, 5).map(user => `
        <img
          src="${user.profile_photo || '/static/default-avatar.png'}"
          alt="${user.full_name}"
          title="${user.full_name}"
          style="
            width: 32px;
            height: 32px;
            border-radius: 50%;
            border: 2px solid white;
            margin-left: -8px;
            object-fit: cover;
            cursor: pointer;
          "
        />
      `).join('');

      // Mostra "+N" se houver mais
      if (this.onlineUsers.length > 5) {
        const extra = document.createElement('div');
        extra.style.cssText = `
          width: 32px;
          height: 32px;
          border-radius: 50%;
          background: var(--primary);
          color: white;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 0.7rem;
          font-weight: 700;
          margin-left: -8px;
        `;
        extra.textContent = `+${this.onlineUsers.length - 5}`;
        avatarList.appendChild(extra);
      }
    }
  }

  /**
   * Renderiza seção de "pessoas indo" em um evento
   */
  renderEventAttendees(container, attendees) {
    if (!attendees || attendees.length === 0) {
      container.innerHTML = '<p style="color: var(--muted); text-align: center;">Ninguém confirmou presença ainda</p>';
      return;
    }

    const html = `
      <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 16px;">
        <div style="display: flex; margin-right: 8px;">
          ${attendees.slice(0, 4).map((person, i) => `
            <img
              src="${person.profile_photo || '/static/default-avatar.png'}"
              alt="${person.full_name}"
              style="
                width: 40px;
                height: 40px;
                border-radius: 50%;
                border: 3px solid white;
                margin-left: ${i > 0 ? '-16px' : '0'};
                object-fit: cover;
              "
              title="${person.full_name}"
            />
          `).join('')}
          ${attendees.length > 4 ? `
            <div style="
              width: 40px;
              height: 40px;
              border-radius: 50%;
              background: var(--primary);
              color: white;
              display: flex;
              align-items: center;
              justify-content: center;
              font-weight: 700;
              margin-left: -16px;
              border: 3px solid white;
            ">+${attendees.length - 4}</div>
          ` : ''}
        </div>
        <div>
          <strong style="color: var(--primary);">${attendees.length} pessoas vão</strong>
          <p style="color: var(--muted); font-size: 0.85rem; margin: 2px 0;">
            ${attendees.slice(0, 3).map(p => p.full_name).join(', ')}${attendees.length > 3 ? '...' : ''}
          </p>
        </div>
      </div>
    `;

    container.innerHTML = html;
  }

  /**
   * Desconecta e limpa
   */
  disconnect() {
    if (this.websocket) {
      this.websocket.close();
    }

    if (this.updateInterval) {
      clearInterval(this.updateInterval);
    }

    this.roomId = null;
    this.userId = null;
    this.onlineUsers = [];
  }
}

window.presenceManager = new PresenceManager();
