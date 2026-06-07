# 📅 CALENDAR INTEGRATION
# Google Calendar + Microsoft Outlook Integration

from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import requests

# Placeholder dependencies (must be wired by host app)
def get_db():
    raise NotImplementedError("get_db must be provided by host app")

def get_current_user_required():
    raise NotImplementedError("get_current_user_required must be provided by host app")

def setup_calendar_integration(app: FastAPI):
    """Setup calendar export endpoints"""

    @app.post("/api/events/{event_id}/export-google")
    async def export_to_google(
        event_id: int,
        current_user = Depends(get_current_user_required),
        db: Session = Depends(get_db)
    ):
        """
        Exportar evento para Google Calendar

        Precisa:
        1. OAuth2 token do usuário para Google
        2. Permissão 'calendar' do Google

        Fluxo:
        1. User clica "Add to Google Calendar"
        2. Redireciona para Google OAuth
        3. Retorna com token
        4. Criar evento no Google Calendar
        """

        # Buscar evento
        event = db.query(LocalEvent).filter(
            LocalEvent.id == event_id
        ).first()

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        # Verificar se user tem Google token
        user_tokens = db.query(UserToken).filter(
            UserToken.user_id == current_user.id,
            UserToken.provider == "google"
        ).first()

        if not user_tokens:
            # Redirecionar para OAuth
            return {
                "requires_auth": True,
                "auth_url": f"/auth/google?redirect=/events/{event_id}"
            }

        # Criar evento no Google Calendar
        headers = {
            "Authorization": f"Bearer {user_tokens.access_token}"
        }

        event_data = {
            "summary": event.title,
            "description": event.description,
            "start": {
                "dateTime": f"{event.date}T{event.time}:00",
                "timeZone": "America/Sao_Paulo"
            },
            "end": {
                "dateTime": f"{event.date}T{event.time}:00",
                "timeZone": "America/Sao_Paulo"
            },
            "location": event.location,
            "reminders": {
                "useDefault": True
            }
        }

        response = requests.post(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            json=event_data,
            headers=headers
        )

        if response.status_code == 200:
            return {
                "success": True,
                "message": "Event added to Google Calendar",
                "event_id": response.json()["id"]
            }
        else:
            raise HTTPException(status_code=response.status_code)

    @app.post("/api/events/{event_id}/export-outlook")
    async def export_to_outlook(
        event_id: int,
        current_user = Depends(get_current_user_required),
        db: Session = Depends(get_db)
    ):
        """
        Exportar evento para Microsoft Outlook

        Precisa:
        1. OAuth2 token do usuário para Microsoft
        2. Permissão 'Calendars.ReadWrite'
        """

        # Buscar evento
        event = db.query(LocalEvent).filter(
            LocalEvent.id == event_id
        ).first()

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        # Verificar se user tem Outlook token
        user_tokens = db.query(UserToken).filter(
            UserToken.user_id == current_user.id,
            UserToken.provider == "microsoft"
        ).first()

        if not user_tokens:
            return {
                "requires_auth": True,
                "auth_url": f"/auth/microsoft?redirect=/events/{event_id}"
            }

        # Criar evento no Outlook
        headers = {
            "Authorization": f"Bearer {user_tokens.access_token}",
            "Content-Type": "application/json"
        }

        event_data = {
            "subject": event.title,
            "bodyPreview": event.description,
            "start": {
                "dateTime": f"{event.date}T{event.time}:00",
                "timeZone": "America/Sao_Paulo"
            },
            "end": {
                "dateTime": f"{event.date}T{event.time}:00",
                "timeZone": "America/Sao_Paulo"
            },
            "location": {
                "displayName": event.location
            },
            "isReminderOn": True
        }

        response = requests.post(
            "https://graph.microsoft.com/v1.0/me/events",
            json=event_data,
            headers=headers
        )

        if response.status_code == 201:
            return {
                "success": True,
                "message": "Event added to Outlook Calendar",
                "event_id": response.json()["id"]
            }
        else:
            raise HTTPException(status_code=response.status_code)


# FRONTEND - BOTÕES DE EXPORTAÇÃO
"""
<!-- Em public/events-dashboard.html, adicionar buttons em cada evento: -->

<div class="event-actions">
    <button class="btn btn-google" onclick="exportToGoogle(eventId)">
        📅 Add to Google Calendar
    </button>
    <button class="btn btn-outlook" onclick="exportToOutlook(eventId)">
        📅 Add to Outlook
    </button>
</div>

<script>
async function exportToGoogle(eventId) {
    const response = await fetch(`/api/events/${eventId}/export-google`, {
        method: 'POST',
        headers: {'Authorization': `Bearer ${getToken()}`}
    });

    const data = await response.json();

    if (data.requires_auth) {
        // Redirecionar para Google OAuth
        window.location.href = data.auth_url;
    } else if (data.success) {
        alert('✅ Event added to Google Calendar!');
    }
}

async function exportToOutlook(eventId) {
    const response = await fetch(`/api/events/${eventId}/export-outlook`, {
        method: 'POST',
        headers: {'Authorization': `Bearer ${getToken()}`}
    });

    const data = await response.json();

    if (data.requires_auth) {
        window.location.href = data.auth_url;
    } else if (data.success) {
        alert('✅ Event added to Outlook Calendar!');
    }
}
</script>
"""
