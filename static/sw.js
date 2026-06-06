/**
 * Service Worker para TimeMates
 * - Cache de assets
 * - Web Push notifications
 * - Offline fallback
 */

const CACHE_NAME = 'timemates-v3';
const urlsToCache = [
  '/',
  '/static/index.html',
  '/static/manifest.json',
  '/static/icon-192.png',
  '/static/icon-512.png',
];

// ─────────────────────────────────────────
// INSTALL: Cache assets básicos
// ─────────────────────────────────────────

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Cacheando assets básicos');
      return cache.addAll(urlsToCache);
    })
  );
  self.skipWaiting();
});

// ─────────────────────────────────────────
// ACTIVATE: Limpa caches antigos
// ─────────────────────────────────────────

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('[SW] Deletando cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// ─────────────────────────────────────────
// FETCH: Cache-first strategy
// ─────────────────────────────────────────

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Ignora requisições não-GET
  if (request.method !== 'GET') {
    return;
  }

  // Ignora requisições para API (usam network-first)
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(request));
    return;
  }

  // Cache-first para assets estáticos
  event.respondWith(cacheFirst(request));
});

async function cacheFirst(request) {
  try {
    const cached = await caches.match(request);
    if (cached) {
      return cached;
    }

    const response = await fetch(request);

    // Cache resposta bem-sucedida
    if (response.status === 200 && response.type !== 'error') {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }

    return response;
  } catch (error) {
    console.error('[SW] Fetch error:', error);
    // Retorna offline page se disponível
    return caches.match('/static/index.html');
  }
}

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    return response;
  } catch (error) {
    console.error('[SW] Network error:', error);
    const cached = await caches.match(request);
    return cached || new Response('Offline', { status: 503 });
  }
}

// ─────────────────────────────────────────
// PUSH NOTIFICATIONS
// ─────────────────────────────────────────

self.addEventListener('push', (event) => {
  console.log('[SW] Push notificação recebida');

  let notificationData = {
    title: 'TimeMates',
    body: 'Você tem uma nova notificação',
    icon: '/static/icon-192.png',
    badge: '/static/icon-96.png',
    tag: 'timemates-notification',
    requireInteraction: false,
  };

  if (event.data) {
    try {
      const data = event.data.json();
      notificationData = { ...notificationData, ...data };
    } catch (e) {
      notificationData.body = event.data.text();
    }
  }

  event.waitUntil(
    self.registration.showNotification(
      notificationData.title,
      {
        body: notificationData.body,
        icon: notificationData.icon,
        badge: notificationData.badge,
        tag: notificationData.tag,
        requireInteraction: notificationData.requireInteraction,
        data: notificationData.data || {},
        actions: [
          {
            action: 'open',
            title: 'Abrir',
            icon: '/static/icon-96.png',
          },
          {
            action: 'close',
            title: 'Fechar',
          },
        ],
      }
    )
  );
});

// ─────────────────────────────────────────
// NOTIFICATION CLICK
// ─────────────────────────────────────────

self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notificação clicada:', event.action);

  event.notification.close();

  if (event.action === 'close') {
    return;
  }

  const data = event.notification.data || {};
  let url = '/';

  // Navega baseado no tipo de notificação
  if (data.action === 'view_event' && data.event_id) {
    url = `/#event/${data.event_id}`;
  } else if (data.action === 'view_news' && data.news_id) {
    url = `/#news/${data.news_id}`;
  } else if (data.room_id) {
    url = `/#room/${data.room_id}`;
  }

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(
      (clientList) => {
        // Procura por uma janela aberta
        for (let i = 0; i < clientList.length; i++) {
          const client = clientList[i];
          if (client.url === url && 'focus' in client) {
            return client.focus();
          }
        }

        // Se não encontrar, abre nova janela
        if (clients.openWindow) {
          return clients.openWindow(url);
        }
      }
    )
  );
});

// ─────────────────────────────────────────
// NOTIFICATION CLOSE (analytics)
// ─────────────────────────────────────────

self.addEventListener('notificationclose', (event) => {
  console.log('[SW] Notificação fechada:', event.notification.tag);
});

console.log('[SW] Service Worker iniciado');

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/ws')) return;
  e.respondWith(
    fetch(e.request)
      .then(res => {
        if (res && res.status === 200 && e.request.method === 'GET') {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return res;
      })
      .catch(() => caches.match(e.request))
  );
});

// ── Push Notifications ────────────────────────────────────────────────────────
self.addEventListener('push', e => {
  let data = { title: 'TimeMates', body: 'Nova notificação', url: '/' };
  try { data = { ...data, ...e.data.json() }; } catch(_) {}
  e.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: '/static/icon-192.png',
      badge: '/static/icon-192.png',
      data: { url: data.url },
      vibrate: [200, 100, 200],
    })
  );
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  const url = e.notification.data?.url || '/';
  e.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(cs => {
      const existing = cs.find(c => c.url.includes(self.location.origin));
      if (existing) { existing.focus(); existing.navigate(url); }
      else clients.openWindow(url);
    })
  );
});
