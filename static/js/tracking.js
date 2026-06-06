/**
 * tracking.js
 * Google Analytics 4 integration e rastreamento de eventos customizados
 */

class TrackingService {
  constructor() {
    this.enabled = !!window.trackEvent;
  }

  // ─────────────────────────────────────────
  // News tracking
  // ─────────────────────────────────────────

  trackNewsClick(newsId, title = '') {
    if (!this.enabled) return;
    window.trackEvent('click_news', {
      news_id: String(newsId),
      title: title,
      timestamp: new Date().toISOString()
    });
    console.log('[GA4] click_news:', newsId);
  }

  // ─────────────────────────────────────────
  // Event tracking
  // ─────────────────────────────────────────

  trackRsvpEvent(eventId, roomId, status = 'going') {
    if (!this.enabled) return;
    window.trackEvent('rsvp_event', {
      event_id: String(eventId),
      room_id: String(roomId),
      status: status,
      timestamp: new Date().toISOString()
    });
    console.log('[GA4] rsvp_event:', eventId, status);
  }

  // ─────────────────────────────────────────
  // Highlights tracking
  // ─────────────────────────────────────────

  trackViewHighlights(roomId, highlightCount = 1) {
    if (!this.enabled) return;
    window.trackEvent('view_highlights', {
      room_id: String(roomId),
      highlight_count: String(highlightCount),
      timestamp: new Date().toISOString()
    });
    console.log('[GA4] view_highlights:', roomId);
  }

  // ─────────────────────────────────────────
  // Reaction tracking
  // ─────────────────────────────────────────

  trackReactionAdded(messageId, roomId, emoji) {
    if (!this.enabled) return;
    window.trackEvent('reaction_added', {
      message_id: String(messageId),
      room_id: String(roomId),
      emoji: emoji,
      timestamp: new Date().toISOString()
    });
    console.log('[GA4] reaction_added:', emoji, messageId);
  }

  // ─────────────────────────────────────────
  // Presence tracking
  // ─────────────────────────────────────────

  trackPresenceOnline(roomId = null, durationSeconds = 0) {
    if (!this.enabled) return;
    window.trackEvent('presence_online', {
      room_id: roomId ? String(roomId) : 'general',
      duration_seconds: String(durationSeconds),
      timestamp: new Date().toISOString()
    });
    console.log('[GA4] presence_online:', roomId);
  }

  // ─────────────────────────────────────────
  // Room tracking
  // ─────────────────────────────────────────

  trackRoomJoined(roomId, institutionId) {
    if (!this.enabled) return;
    window.trackEvent('room_joined', {
      room_id: String(roomId),
      institution_id: String(institutionId),
      timestamp: new Date().toISOString()
    });
    console.log('[GA4] room_joined:', roomId);
  }

  // ─────────────────────────────────────────
  // Message tracking
  // ─────────────────────────────────────────

  trackMessageSent(roomId, messageLength = 0) {
    if (!this.enabled) return;
    window.trackEvent('message_sent', {
      room_id: String(roomId),
      message_length: String(messageLength),
      timestamp: new Date().toISOString()
    });
    console.log('[GA4] message_sent:', roomId, messageLength);
  }

  // ─────────────────────────────────────────
  // Page view tracking (automático via GA4, mas podemos customizar)
  // ─────────────────────────────────────────

  trackPageView(pagePath, pageTitle) {
    if (!this.enabled) return;
    window.gtag('config', window.GA4_MEASUREMENT_ID, {
      page_path: pagePath,
      page_title: pageTitle
    });
    console.log('[GA4] page_view:', pagePath);
  }

  // ─────────────────────────────────────────
  // User properties (para segmentação)
  // ─────────────────────────────────────────

  setUserProperties(properties) {
    if (!window.gtag) return;

    const formattedProps = {};
    for (const [key, value] of Object.entries(properties)) {
      // GA4 nomes de propriedades devem ser prefixados com "user_"
      formattedProps[`user_${key}`] = value;
    }

    window.gtag('config', window.GA4_MEASUREMENT_ID, formattedProps);
    console.log('[GA4] set user properties:', formattedProps);
  }

  // ─────────────────────────────────────────
  // Track page engagement (tempo na página)
  // ─────────────────────────────────────────

  trackPageEngagement(pageName) {
    if (!this.enabled) return;

    let startTime = Date.now();
    let isActive = true;

    window.addEventListener('beforeunload', () => {
      const engagementTime = Math.round((Date.now() - startTime) / 1000);
      window.trackEvent('page_engagement', {
        page_name: pageName,
        engagement_time_seconds: String(engagementTime)
      });
    });

    // Considera inativo após 1 minuto sem atividade
    document.addEventListener('mousemove', () => {
      startTime = Date.now();
    });

    document.addEventListener('keydown', () => {
      startTime = Date.now();
    });
  }

  // ─────────────────────────────────────────
  // Batch tracking (para múltiplos eventos)
  // ─────────────────────────────────────────

  trackBatch(events) {
    events.forEach(event => {
      if (window.trackEvent) {
        window.trackEvent(event.name, event.params);
      }
    });
    console.log('[GA4] batch tracked:', events.length, 'events');
  }
}

// Inicializa globalmente
window.trackingService = new TrackingService();

// Auto-track page engagement
document.addEventListener('DOMContentLoaded', () => {
  const pageName = document.title || 'Unknown Page';
  window.trackingService.trackPageEngagement(pageName);
});

// Listener para eventos de real-time
window.addEventListener('realtimeUpdate', (event) => {
  const { type, emoji, message_id, room_id } = event.detail;

  if (type === 'reaction_added') {
    window.trackingService.trackReactionAdded(message_id, room_id, emoji);
  }
});
