/**
 * TimeMates Service Worker
 * Gerencia Push Notifications e caching offline
 */

const CACHE_NAME = 'timemates-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/chat.js',
  '/chat.css',
  '/index.html'
];

// ============================================
// INSTALLATION
// ============================================

self.addEventListener('install', (event) => {
  console.log('[SW] Installing Service Worker...');

  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Caching assets');
      return cache.addAll(ASSETS_TO_CACHE).catch((error) => {
        console.warn('[SW] Some assets failed to cache:', error);
        // Não falhar completamente se um asset falhar
      });
    })
  );

  // Forçar ativação imediata
  self.skipWaiting();
});

// ============================================
// ACTIVATION
// ============================================

self.addEventListener('activate', (event) => {
  console.log('[SW] Activating Service Worker...');

  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('[SW] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );

  // Reclamar todos os clientes
  self.clients.claim();
});

// ============================================
// FETCH - Cache Strategy
// ============================================

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Ignorar requests não-GET
  if (request.method !== 'GET') {
    return;
  }

  // Ignorar requests para APIs (vão para network)
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request).catch(() => {
        // Offline - retornar erro ou cache
        return caches.match(request);
      })
    );
    return;
  }

  // Cache-first para assets estáticos
  event.respondWith(
    caches.match(request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }

      return fetch(request).then((networkResponse) => {
        if (!networkResponse || networkResponse.status !== 200 || networkResponse.type === 'error') {
          return networkResponse;
        }

        // Clonar response antes de cachear
        const responseToCache = networkResponse.clone();

        caches.open(CACHE_NAME).then((cache) => {
          cache.put(request, responseToCache);
        });

        return networkResponse;
      });
    }).catch(() => {
      // Offline fallback
      return new Response('Offline - conteúdo não disponível', {
        status: 503,
        statusText: 'Service Unavailable',
        headers: new Headers({
          'Content-Type': 'text/plain'
        })
      });
    })
  );
});

// ============================================
// PUSH NOTIFICATIONS
// ============================================

self.addEventListener('push', (event) => {
  console.log('[SW] Push notification received');

  if (!event.data) {
    console.warn('[SW] Push notification sem dados');
    return;
  }

  let notificationData = {};

  try {
    notificationData = event.data.json();
  } catch (error) {
    // Se não for JSON, tratar como texto
    notificationData = {
      title: 'TimeMates',
      body: event.data.text()
    };
  }

  const {
    title = 'TimeMates',
    body = 'Nova notificação',
    icon = '/assets/icon.png',
    badge = '/assets/badge.png',
    tag = 'timemates-notification',
    requireInteraction = false,
    actions = [],
    data = {}
  } = notificationData;

  const options = {
    body,
    icon,
    badge,
    tag,
    requireInteraction,
    actions,
    data,
    // Vibração
    vibrate: [200, 100, 200],
    // Som
    silent: false
  };

  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

// ============================================
// NOTIFICATION CLICK
// ============================================

self.addEventListener('notificationclick', (event) => {
  const { notification, action } = event;

  console.log('[SW] Notification clicked:', {
    title: notification.title,
    action: action
  });

  notification.close();

  // Extrair URL dos dados da notificação
  const urlToOpen = notification.data.url || '/timeMates/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      // Procurar janela aberta
      for (let client of clientList) {
        if (client.url === urlToOpen && 'focus' in client) {
          return client.focus();
        }
      }

      // Se nenhuma aberta, abrir nova
      if (clients.openWindow) {
        return clients.openWindow(urlToOpen);
      }
    })
  );
});

// ============================================
// NOTIFICATION CLOSE
// ============================================

self.addEventListener('notificationclose', (event) => {
  console.log('[SW] Notification closed:', event.notification.title);
  // Log para analytics, se necessário
});

// ============================================
// MESSAGE FROM CLIENT
// ============================================

self.addEventListener('message', (event) => {
  const { type, data } = event.data;

  console.log('[SW] Message received:', type);

  switch (type) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;

    case 'GET_VERSION':
      event.ports[0].postMessage({
        version: CACHE_NAME
      });
      break;

    case 'CLEAR_CACHE':
      caches.delete(CACHE_NAME).then(() => {
        event.ports[0].postMessage({
          success: true,
          message: 'Cache limpo'
        });
      });
      break;

    case 'SEND_NOTIFICATION':
      // Receber dados de notificação do cliente
      const {
        title = 'TimeMates',
        options = {}
      } = data;

      self.registration.showNotification(title, options).then(() => {
        event.ports[0].postMessage({
          success: true,
          message: 'Notificação enviada'
        });
      }).catch((error) => {
        event.ports[0].postMessage({
          success: false,
          error: error.message
        });
      });
      break;

    default:
      console.warn('[SW] Unknown message type:', type);
  }
});

// ============================================
// SYNC (Background Sync)
// ============================================

self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync triggered:', event.tag);

  if (event.tag === 'sync-messages') {
    event.waitUntil(
      // Sincronizar mensagens pendentes
      syncPendingMessages()
    );
  }
});

async function syncPendingMessages() {
  try {
    const db = await openIndexedDB();
    const pendingMessages = await getPendingMessages(db);

    console.log('[SW] Sincronizando', pendingMessages.length, 'mensagens');

    // Enviar para servidor
    for (const message of pendingMessages) {
      try {
        const response = await fetch('/api/messages', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(message)
        });

        if (response.ok) {
          await deletePendingMessage(db, message.id);
        }
      } catch (error) {
        console.error('[SW] Erro ao sincronizar mensagem:', error);
      }
    }
  } catch (error) {
    console.error('[SW] Erro ao sincronizar:', error);
  }
}

function openIndexedDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('TimeMates', 1);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains('pending-messages')) {
        db.createObjectStore('pending-messages', { keyPath: 'id' });
      }
    };
  });
}

function getPendingMessages(db) {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(['pending-messages'], 'readonly');
    const store = transaction.objectStore('pending-messages');
    const request = store.getAll();

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
  });
}

function deletePendingMessage(db, id) {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(['pending-messages'], 'readwrite');
    const store = transaction.objectStore('pending-messages');
    const request = store.delete(id);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve();
  });
}

// ============================================
// PERIODIC BACKGROUND SYNC
// ============================================

self.addEventListener('periodicsync', (event) => {
  if (event.tag === 'check-online-users') {
    event.waitUntil(
      checkOnlineUsersAndNotify()
    );
  }
});

async function checkOnlineUsersAndNotify() {
  try {
    const roomId = 'room-123'; // Será enviado do cliente
    const response = await fetch(`/api/rooms/${roomId}/online-users`);
    const data = await response.json();

    if (data.users && data.users.length > 0) {
      console.log('[SW] Usuários online:', data.users.length);
    }
  } catch (error) {
    console.error('[SW] Erro ao verificar usuários online:', error);
  }
}

// ============================================
// HEARTBEAT
// ============================================

// Manter Service Worker vivo
setInterval(() => {
  console.log('[SW] Heartbeat');
}, 60000); // A cada 60 segundos
