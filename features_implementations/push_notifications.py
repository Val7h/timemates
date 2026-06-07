# 📢 PUSH NOTIFICATIONS SETUP
# Web Push para breaking news e event reminders

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import Session
from datetime import datetime
import json

# DATABASE MODEL
class PushSubscription(Column):
    """Armazena device tokens para push notifications"""
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=True)
    device_token = Column(String(500), unique=True)
    endpoint = Column(String(500))
    auth = Column(String(500))
    p256dh = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# BACKEND ENDPOINTS
def setup_push_notifications(app: FastAPI):
    """Setup push notification endpoints"""

    @app.post("/api/subscribe")
    def subscribe_to_push(
        subscription: dict,
        current_user = Depends(get_current_user_optional),
        db: Session = Depends(get_db)
    ):
        """
        Subscribe device para push notifications

        Request body:
        {
            "endpoint": "https://fcm.googleapis.com/...",
            "keys": {
                "auth": "...",
                "p256dh": "..."
            }
        }
        """
        try:
            # Salvar subscription no banco
            push_sub = PushSubscription(
                user_id=current_user.id if current_user else None,
                endpoint=subscription.get("endpoint"),
                auth=subscription.get("keys", {}).get("auth"),
                p256dh=subscription.get("keys", {}).get("p256dh")
            )
            db.add(push_sub)
            db.commit()

            return {
                "success": True,
                "message": "Subscribed to push notifications"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    @app.post("/api/notifications/send")
    def send_notification(
        title: str,
        body: str,
        city: str = None,
        event_id: int = None,
        db: Session = Depends(get_db)
    ):
        """
        Enviar push notification (admin only)

        Tipos:
        - Breaking News: title="Breaking News", city="São Paulo"
        - Event Reminder: title="Event Soon", event_id=123
        """

        # Buscar subscriptions ativas
        subscriptions = db.query(PushSubscription).filter(
            PushSubscription.is_active == True
        ).all()

        # Enviar para todas as subscriptions
        for sub in subscriptions:
            try:
                # Aqui você usaria Firebase Cloud Messaging (FCM)
                # ou Web Push API para enviar notificação
                payload = {
                    "notification": {
                        "title": title,
                        "body": body,
                        "icon": "/icon-192.png",
                        "badge": "/icon-192.png"
                    },
                    "data": {
                        "city": city or "",
                        "event_id": str(event_id) if event_id else ""
                    }
                }

                # Implementar envio via Firebase
                # await send_web_push(sub.endpoint, payload)

            except Exception as e:
                print(f"Failed to send to {sub.endpoint}: {e}")

        return {
            "success": True,
            "notified": len(subscriptions),
            "message": f"Notification sent to {len(subscriptions)} devices"
        }

    @app.post("/api/notifications/unsubscribe")
    def unsubscribe(
        endpoint: str,
        db: Session = Depends(get_db)
    ):
        """Unsubscribe de push notifications"""
        sub = db.query(PushSubscription).filter(
            PushSubscription.endpoint == endpoint
        ).first()

        if sub:
            sub.is_active = False
            db.commit()

        return {
            "success": True,
            "message": "Unsubscribed from push notifications"
        }


# FRONTEND JAVASCRIPT
"""
// Registrar service worker e pedir permissão
async function setupPushNotifications() {
    if ('serviceWorker' in navigator && 'PushManager' in window) {
        try {
            // Registrar service worker
            const registration = await navigator.serviceWorker.register('/sw.js');

            // Pedir permissão
            const permission = await Notification.requestPermission();

            if (permission === 'granted') {
                // Subscribe
                const subscription = await registration.pushManager.subscribe({
                    userVisibleOnly: true,
                    applicationServerKey: 'YOUR_VAPID_KEY'
                });

                // Enviar subscription para backend
                await fetch('/api/subscribe', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(subscription)
                });
            }
        } catch (error) {
            console.error('Push setup failed:', error);
        }
    }
}

// Chamar ao carregar página
setupPushNotifications();
"""

# SERVICE WORKER
"""
// public/sw.js - Service Worker para push notifications

self.addEventListener('push', event => {
    const data = event.data.json();

    const options = {
        body: data.notification.body,
        icon: data.notification.icon,
        badge: data.notification.badge,
        data: data.data
    };

    event.waitUntil(
        self.registration.showNotification(
            data.notification.title,
            options
        )
    );
});

self.addEventListener('notificationclick', event => {
    event.notification.close();

    const urlToOpen = '/';
    if (event.notification.data.city) {
        urlToOpen += `?city=${event.notification.data.city}`;
    }

    event.waitUntil(
        clients.matchAll({type: 'window'}).then(windowClients => {
            for (let i = 0; i < windowClients.length; i++) {
                if (windowClients[i].url === urlToOpen) {
                    return windowClients[i].focus();
                }
            }
            return clients.openWindow(urlToOpen);
        })
    );
});
"""

# AUTOMAÇÃO - ENVIAR BREAKING NEWS AUTOMATICAMENTE
"""
# Quando houver breaking news, enviar push automaticamente

@app.post("/api/news")
def create_news(
    city: str,
    title: str,
    content: str,
    category: str,
    db: Session = Depends(get_db)
):
    # Criar notícia
    news = LocalNews(...)
    db.add(news)
    db.commit()

    # Se for breaking news, enviar push
    if category == "breaking_news":
        await send_notification(
            title=f"Breaking News: {title}",
            body=f"Nova notícia em {city}",
            city=city
        )

    return news
"""
