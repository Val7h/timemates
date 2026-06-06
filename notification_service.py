"""
Serviço centralizado de notificações:
- Push notifications (Web Push API)
- Email (digest semanal, event reminders)
- In-app notifications
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from sqlalchemy.orm import Session

# Web Push
try:
    from pywebpush import webpush, WebPushException
except ImportError:
    webpush = None
    WebPushException = Exception

# Email
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Scheduler
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()


class NotificationService:
    """Gerencia todas as notificações do sistema"""

    def __init__(self, db: Session):
        self.db = db
        self.vapid_private_key = os.getenv("VAPID_PRIVATE_KEY")
        self.vapid_public_key = os.getenv("VAPID_PUBLIC_KEY")
        self.vapid_email = os.getenv("VAPID_EMAIL", "admin@timemates.com")
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")

    # ─────────────────────────────────────────
    # NOTIFICAÇÕES PUSH (Web Push API)
    # ─────────────────────────────────────────

    async def send_push_notification(
        self,
        user_id: int,
        title: str,
        body: str,
        icon: str = "/static/icon-192.png",
        badge: str = "/static/icon-96.png",
        data: Dict = None
    ) -> bool:
        """
        Envia notificação push para um usuário
        Precisa de valid PushSubscription no DB
        """
        from database import PushSubscription, Notification

        if not webpush:
            print("[PUSH] pywebpush não instalado, ignorando...")
            return False

        try:
            subscriptions = self.db.query(PushSubscription).filter(
                PushSubscription.user_id == user_id
            ).all()

            if not subscriptions:
                print(f"[PUSH] Nenhuma subscription para user {user_id}")
                return False

            payload = {
                "title": title,
                "body": body,
                "icon": icon,
                "badge": badge,
                "data": data or {}
            }

            success_count = 0
            for sub in subscriptions:
                try:
                    webpush(
                        subscription_info={
                            "endpoint": sub.endpoint,
                            "keys": {
                                "p256dh": sub.p256dh,
                                "auth": sub.auth
                            }
                        },
                        data=json.dumps(payload),
                        vapid_private_key=self.vapid_private_key,
                        vapid_claims={
                            "sub": self.vapid_email,
                            "aud": sub.endpoint.split("/")[2]
                        }
                    )
                    success_count += 1
                except WebPushException as e:
                    print(f"[PUSH] Erro enviando para {sub.endpoint}: {e}")

            # Registra notificação in-app
            notification = Notification(
                user_id=user_id,
                type="push",
                title=title,
                body=body,
                data=data or {}
            )
            self.db.add(notification)
            self.db.commit()

            return success_count > 0

        except Exception as e:
            print(f"[PUSH] Erro geral: {e}")
            return False

    # ─────────────────────────────────────────
    # NOTIFICAÇÕES EMAIL
    # ─────────────────────────────────────────

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        email_type: str = "transactional"
    ) -> bool:
        """Envia email via SMTP"""
        from database import EmailLog

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.smtp_user
            msg["To"] = to_email

            part = MIMEText(html_content, "html")
            msg.attach(part)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            # Log de sucesso
            log = EmailLog(
                recipient_email=to_email,
                type=email_type,
                status="sent",
                sent_at=datetime.utcnow()
            )
            self.db.add(log)
            self.db.commit()

            print(f"[EMAIL] Enviado para {to_email}")
            return True

        except Exception as e:
            print(f"[EMAIL] Erro: {e}")
            log = EmailLog(
                recipient_email=to_email,
                type=email_type,
                status="failed",
                error=str(e)
            )
            self.db.add(log)
            self.db.commit()
            return False

    # ─────────────────────────────────────────
    # EVENT REMINDER (24h antes)
    # ─────────────────────────────────────────

    def schedule_event_reminders(self):
        """
        Background task: verifica eventos com início em ~24h
        Envia reminder para todos os RSVPs
        """
        from database import Event, EventRSVP, User

        try:
            # Eventos que começam entre 23h30 e 24h30
            now = datetime.utcnow()
            window_start = now + timedelta(hours=23.5)
            window_end = now + timedelta(hours=24.5)

            events = self.db.query(Event).filter(
                (Event.start_at >= window_start) &
                (Event.start_at <= window_end)
            ).all()

            for event in events:
                rsvps = self.db.query(EventRSVP).filter(
                    (EventRSVP.event_id == event.id) &
                    (EventRSVP.status.in_(["going", "interested"]))
                ).all()

                for rsvp in rsvps:
                    user = self.db.query(User).get(rsvp.user_id)
                    if user:
                        title = f"Lembrete: {event.title}"
                        body = f"Seu evento começa em 24h em {event.location or 'local a definir'}"

                        asyncio.run(self.send_push_notification(
                            user_id=user.id,
                            title=title,
                            body=body,
                            data={
                                "event_id": event.id,
                                "room_id": event.room_id,
                                "action": "view_event"
                            }
                        ))

            print(f"[REMINDER] Enviados reminders de {len(events)} eventos")

        except Exception as e:
            print(f"[REMINDER] Erro: {e}")

    # ─────────────────────────────────────────
    # WEEKLY DIGEST (Segunda 10am)
    # ─────────────────────────────────────────

    def send_weekly_digest(self, user_id: int) -> bool:
        """
        Envia resumo semanal para o usuário
        - Novos membros nas rooms
        - Mensagens principais (top reactions)
        - Próximos eventos
        """
        from database import User, RoomMembership, Message, MessageReaction, Event

        try:
            user = self.db.query(User).get(user_id)
            if not user or not user.email:
                return False

            # Busca memberships do usuário
            memberships = self.db.query(RoomMembership).filter(
                RoomMembership.user_id == user_id
            ).all()

            if not memberships:
                return False

            room_ids = [m.room_id for m in memberships]

            # Top messages da semana (por reactions)
            week_ago = datetime.utcnow() - timedelta(days=7)
            top_messages = self.db.query(Message).filter(
                (Message.room_id.in_(room_ids)) &
                (Message.created_at >= week_ago)
            ).all()

            # Próximos eventos (próximos 30 dias)
            upcoming_events = self.db.query(Event).filter(
                (Event.room_id.in_(room_ids)) &
                (Event.start_at >= datetime.utcnow()) &
                (Event.start_at <= datetime.utcnow() + timedelta(days=30))
            ).order_by(Event.start_at).limit(5).all()

            # Monta HTML do digest
            html_content = self._build_digest_html(
                user.full_name,
                len(memberships),
                len(top_messages),
                upcoming_events
            )

            return self.send_email(
                to_email=user.email,
                subject=f"Seu resumo semanal - TimeMates",
                html_content=html_content,
                email_type="weekly_digest"
            )

        except Exception as e:
            print(f"[DIGEST] Erro para user {user_id}: {e}")
            return False

    def _build_digest_html(
        self,
        user_name: str,
        room_count: int,
        message_count: int,
        events: List
    ) -> str:
        """Constrói HTML do digest semanal"""
        events_html = "".join([
            f"""
            <div style="margin-bottom: 12px;">
                <strong>{event.title}</strong><br/>
                <small>{event.start_at.strftime('%d/%m %H:%M')} - {event.location}</small>
            </div>
            """
            for event in events
        ])

        return f"""
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: Inter, sans-serif; background: #f7f5f2; padding: 24px;">
            <div style="background: white; border-radius: 12px; padding: 32px; max-width: 600px; margin: 0 auto;">
                <h1 style="color: #1e3a5f; font-size: 24px; margin-bottom: 16px;">
                    Olá {user_name}! 👋
                </h1>
                <p style="color: #6b7280; margin-bottom: 24px;">
                    Aqui está seu resumo da semana no TimeMates
                </p>

                <h2 style="color: #1e3a5f; font-size: 16px; margin-top: 24px; margin-bottom: 12px;">
                    📊 Estatísticas
                </h2>
                <ul style="color: #1a1a2e; line-height: 1.8;">
                    <li>{room_count} salas que você segue</li>
                    <li>{message_count} mensagens principais</li>
                    <li>{len(events)} próximos eventos</li>
                </ul>

                <h2 style="color: #1e3a5f; font-size: 16px; margin-top: 24px; margin-bottom: 12px;">
                    📅 Próximos Eventos
                </h2>
                {events_html or '<p style="color: #6b7280;">Nenhum evento previsto</p>'}

                <div style="margin-top: 32px; padding-top: 24px; border-top: 1px solid #e5e0d6;">
                    <a href="https://timemates.onrender.com"
                       style="background: #d4a853; color: #1e3a5f; padding: 10px 20px;
                              border-radius: 8px; text-decoration: none; font-weight: 700;">
                        Abrir TimeMates
                    </a>
                </div>
            </div>
        </body>
        </html>
        """

    # ─────────────────────────────────────────
    # BREAKING NEWS ALERT
    # ─────────────────────────────────────────

    async def send_breaking_news(
        self,
        title: str,
        body: str,
        news_id: int,
        target_users: List[int] = None
    ):
        """
        Envia alerta de breaking news para usuários
        target_users: se None, envia para todos
        """
        from database import User

        try:
            if target_users is None:
                # Envia para todos os usuários ativos
                users = self.db.query(User).filter(User.is_active == True).all()
                target_users = [u.id for u in users]

            print(f"[NEWS] Breaking news para {len(target_users)} usuários")

            for user_id in target_users:
                await self.send_push_notification(
                    user_id=user_id,
                    title=title,
                    body=body,
                    data={
                        "news_id": news_id,
                        "action": "view_news"
                    }
                )

        except Exception as e:
            print(f"[NEWS] Erro: {e}")


def init_scheduler(db_session):
    """Inicializa scheduler de tarefas em background"""
    try:
        scheduler.add_job(
            func=lambda: NotificationService(db_session).schedule_event_reminders(),
            trigger="cron",
            hour="*",  # a cada hora
            minute="30"
        )

        scheduler.add_job(
            func=lambda: _send_all_digests(db_session),
            trigger="cron",
            day_of_week="0",  # segunda (0 = segunda, 6 = domingo)
            hour="10",
            minute="0"
        )

        scheduler.start()
        print("[SCHEDULER] Tasks agendadas com sucesso")

    except Exception as e:
        print(f"[SCHEDULER] Erro ao inicializar: {e}")


def _send_all_digests(db: Session):
    """Envia digest para todos os usuários"""
    from database import User

    try:
        users = db.query(User).filter(User.is_active == True).all()
        service = NotificationService(db)

        for user in users:
            service.send_weekly_digest(user.id)

        print(f"[DIGEST] Enviados para {len(users)} usuários")

    except Exception as e:
        print(f"[DIGEST] Erro ao enviar em massa: {e}")
