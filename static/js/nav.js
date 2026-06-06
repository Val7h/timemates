/**
 * nav.js
 * Gerencia navegação principal com dropdown de eventos
 */

class NavigationManager {
  constructor() {
    this.currentPage = 'home';
    this.currentUser = null;
    this.eventDropdownOpen = false;
  }

  init() {
    this.renderNavigation();
    this.attachEventListeners();
    this.loadUserProfile();
  }

  renderNavigation() {
    const nav = document.querySelector('nav');
    if (!nav) return;

    nav.innerHTML = `
      <div class="nav-logo">
        Time<span>Mates</span>
      </div>

      <div style="display: flex; gap: 24px; align-items: center; flex: 1; margin-left: 48px;">
        <!-- News Tab -->
        <button
          class="nav-item"
          data-page="news"
          style="
            background: none;
            border: none;
            color: #fff;
            font-size: 0.95rem;
            font-weight: 500;
            cursor: pointer;
            padding: 4px 0;
            border-bottom: 3px solid transparent;
            transition: all 0.2s;
          "
        >
          📰 Notícias
        </button>

        <!-- Events Dropdown -->
        <div style="position: relative;">
          <button
            id="events-dropdown-btn"
            style="
              background: none;
              border: none;
              color: #fff;
              font-size: 0.95rem;
              font-weight: 500;
              cursor: pointer;
              padding: 4px 0;
              display: flex;
              align-items: center;
              gap: 6px;
              transition: all 0.2s;
            "
          >
            🎉 Eventos
            <span style="font-size: 0.7rem;">▼</span>
          </button>

          <div
            id="events-dropdown-menu"
            style="
              position: absolute;
              top: 100%;
              left: 0;
              background: white;
              border-radius: 8px;
              box-shadow: var(--shadow-lg);
              min-width: 220px;
              margin-top: 12px;
              padding: 8px 0;
              display: none;
              z-index: 200;
            "
          >
            <button class="dropdown-item" data-action="upcoming-events">
              ⏰ Próximos Eventos
            </button>
            <button class="dropdown-item" data-action="my-events">
              ✓ Meus Eventos
            </button>
            <div style="height: 1px; background: var(--border); margin: 8px 0;"></div>
            <button class="dropdown-item" data-action="create-event">
              ➕ Criar Evento
            </button>
          </div>
        </div>
      </div>

      <div class="nav-right">
        <!-- Notifications Bell -->
        <button
          id="notifications-bell"
          class="nav-bell"
          style="position: relative;"
        >
          🔔
          <span class="badge hidden" style="
            position: absolute;
            top: 0;
            right: 0;
            background: var(--error);
            color: white;
            border-radius: 50%;
            width: 18px;
            height: 18px;
            font-size: 0.65rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            justify-content: center;
          "></span>
        </button>

        <!-- User Profile Dropdown -->
        <div style="position: relative;">
          <button
            id="user-dropdown-btn"
            style="
              background: transparent;
              border: 1.5px solid rgba(255,255,255,0.4);
              color: #fff;
              padding: 6px 14px;
              border-radius: 8px;
              font-size: 0.85rem;
              font-weight: 500;
              cursor: pointer;
              display: flex;
              align-items: center;
              gap: 8px;
              transition: all 0.2s;
            "
          >
            <img
              id="user-avatar"
              src="/static/default-avatar.png"
              alt="Você"
              style="
                width: 24px;
                height: 24px;
                border-radius: 50%;
                object-fit: cover;
              "
            />
            <span id="user-name">Perfil</span>
            <span style="font-size: 0.7rem;">▼</span>
          </button>

          <div
            id="user-dropdown-menu"
            style="
              position: absolute;
              top: 100%;
              right: 0;
              background: white;
              border-radius: 8px;
              box-shadow: var(--shadow-lg);
              min-width: 200px;
              margin-top: 12px;
              padding: 8px 0;
              display: none;
              z-index: 200;
            "
          >
            <button class="dropdown-item" data-action="view-profile">
              👤 Meu Perfil
            </button>
            <button class="dropdown-item" data-action="my-rooms">
              🏠 Minhas Salas
            </button>
            <button class="dropdown-item" data-action="settings">
              ⚙️ Configurações
            </button>
            <div style="height: 1px; background: var(--border); margin: 8px 0;"></div>
            <button class="dropdown-item" data-action="logout">
              🚪 Sair
            </button>
          </div>
        </div>
      </div>
    `;

    // Estilos para itens dropdown
    const style = document.createElement('style');
    style.textContent = `
      .nav-item {
        padding: 4px 0 !important;
        border-bottom: 3px solid transparent !important;
      }

      .nav-item:hover,
      .nav-item.active {
        border-bottom-color: var(--accent) !important;
        color: var(--accent) !important;
      }

      .dropdown-item {
        background: none;
        border: none;
        color: var(--text);
        padding: 10px 20px;
        width: 100%;
        text-align: left;
        cursor: pointer;
        font-size: 0.9rem;
        transition: all 0.2s;
        display: block;
      }

      .dropdown-item:hover {
        background: var(--bg);
        color: var(--primary);
      }

      #user-dropdown-btn:hover {
        background: rgba(255,255,255,0.15) !important;
        border-color: rgba(255,255,255,0.7) !important;
      }

      #events-dropdown-btn:hover {
        color: var(--accent);
      }
    `;
    document.head.appendChild(style);
  }

  attachEventListeners() {
    // News tab
    document.querySelectorAll('[data-page]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const page = btn.getAttribute('data-page');
        this.navigateToPage(page);
      });
    });

    // Events dropdown
    const eventsDropdownBtn = document.getElementById('events-dropdown-btn');
    const eventsDropdownMenu = document.getElementById('events-dropdown-menu');

    if (eventsDropdownBtn) {
      eventsDropdownBtn.addEventListener('click', () => {
        this.eventDropdownOpen = !this.eventDropdownOpen;
        eventsDropdownMenu.style.display = this.eventDropdownOpen ? 'block' : 'none';
      });

      // Fecha ao clicar em um item
      eventsDropdownMenu.querySelectorAll('.dropdown-item').forEach(item => {
        item.addEventListener('click', (e) => {
          const action = item.getAttribute('data-action');
          this.handleEventDropdownAction(action);
          this.eventDropdownOpen = false;
          eventsDropdownMenu.style.display = 'none';
        });
      });
    }

    // User dropdown
    const userDropdownBtn = document.getElementById('user-dropdown-btn');
    const userDropdownMenu = document.getElementById('user-dropdown-menu');

    if (userDropdownBtn) {
      userDropdownBtn.addEventListener('click', () => {
        userDropdownMenu.style.display =
          userDropdownMenu.style.display === 'none' ? 'block' : 'none';
      });

      userDropdownMenu.querySelectorAll('.dropdown-item').forEach(item => {
        item.addEventListener('click', (e) => {
          const action = item.getAttribute('data-action');
          this.handleUserDropdownAction(action);
          userDropdownMenu.style.display = 'none';
        });
      });
    }

    // Notifications bell
    document.getElementById('notifications-bell').addEventListener('click', () => {
      window.dispatchEvent(new CustomEvent('openNotifications'));
    });

    // Fecha dropdowns ao clicar fora
    document.addEventListener('click', (e) => {
      if (!e.target.closest('nav')) return;

      if (!e.target.closest('#events-dropdown-btn')) {
        eventsDropdownMenu.style.display = 'none';
        this.eventDropdownOpen = false;
      }

      if (!e.target.closest('#user-dropdown-btn')) {
        userDropdownMenu.style.display = 'none';
      }
    });

    // Listener para notificações
    window.addEventListener('notificationsLoaded', (event) => {
      const { unreadCount } = event.detail;
      const badge = document.querySelector('.badge');
      if (badge && unreadCount > 0) {
        badge.textContent = unreadCount > 99 ? '99+' : unreadCount;
        badge.classList.remove('hidden');
      }
    });
  }

  loadUserProfile() {
    // Busca dados do usuário para mostrar no avatar
    const userData = JSON.parse(localStorage.getItem('user_data') || '{}');
    if (userData.full_name) {
      document.getElementById('user-name').textContent =
        userData.full_name.split(' ')[0];
    }
    if (userData.profile_photo) {
      document.getElementById('user-avatar').src = userData.profile_photo;
    }
  }

  navigateToPage(page) {
    this.currentPage = page;

    // Atualiza active state
    document.querySelectorAll('[data-page]').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-page') === page);
    });

    // Dispara evento de navegação
    window.dispatchEvent(new CustomEvent('navigationChange', {
      detail: { page }
    }));

    // Navega para a página
    window.location.hash = `#${page}`;
  }

  handleEventDropdownAction(action) {
    switch (action) {
      case 'upcoming-events':
        this.navigateToPage('events');
        window.dispatchEvent(new CustomEvent('showUpcomingEvents'));
        break;

      case 'my-events':
        this.navigateToPage('events');
        window.dispatchEvent(new CustomEvent('showMyEvents'));
        break;

      case 'create-event':
        window.dispatchEvent(new CustomEvent('openCreateEventModal'));
        break;
    }
  }

  handleUserDropdownAction(action) {
    switch (action) {
      case 'view-profile':
        this.navigateToPage('profile');
        break;

      case 'my-rooms':
        this.navigateToPage('rooms');
        break;

      case 'settings':
        this.navigateToPage('settings');
        break;

      case 'logout':
        localStorage.removeItem('access_token');
        localStorage.removeItem('user_data');
        window.location.href = '/';
        break;
    }
  }
}

window.navigationManager = new NavigationManager();

// Inicializa ao carregar DOM
document.addEventListener('DOMContentLoaded', () => {
  window.navigationManager.init();
});
