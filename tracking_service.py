"""
Serviço de tracking com Google Analytics 4
Eventos:
- click_news
- rsvp_event
- view_highlights
- reaction_added
- presence_online
- room_joined
- message_sent
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

try:
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        RunReportRequest,
        Dimension,
        Metric,
    )
    HAS_GA4_LIBRARY = True
except ImportError:
    HAS_GA4_LIBRARY = False


class TrackingService:
    """Gerencia tracking de eventos com GA4"""

    def __init__(self, db: Session = None):
        self.db = db
        self.ga4_measurement_id = os.getenv("GA4_MEASUREMENT_ID")
        self.ga4_api_secret = os.getenv("GA4_API_SECRET")
        self.has_ga4 = bool(self.ga4_measurement_id and self.ga4_api_secret)

    # ─────────────────────────────────────────
    # EVENTOS PRINCIPAIS
    # ─────────────────────────────────────────

    def track_news_click(
        self,
        user_id: int,
        news_id: int,
        user_properties: Dict[str, str] = None
    ) -> bool:
        """Rastreia clique em notícia"""
        return self._send_event(
            event_name="click_news",
            user_id=user_id,
            params={
                "news_id": str(news_id),
                "timestamp": datetime.utcnow().isoformat(),
            },
            user_properties=user_properties
        )

    def track_rsvp_event(
        self,
        user_id: int,
        event_id: int,
        room_id: int,
        status: str = "going",
        user_properties: Dict[str, str] = None
    ) -> bool:
        """Rastreia RSVP em evento"""
        return self._send_event(
            event_name="rsvp_event",
            user_id=user_id,
            params={
                "event_id": str(event_id),
                "room_id": str(room_id),
                "status": status,
                "timestamp": datetime.utcnow().isoformat(),
            },
            user_properties=user_properties
        )

    def track_view_highlights(
        self,
        user_id: int,
        room_id: int,
        highlight_count: int = 1,
        user_properties: Dict[str, str] = None
    ) -> bool:
        """Rastreia visualização de destaques"""
        return self._send_event(
            event_name="view_highlights",
            user_id=user_id,
            params={
                "room_id": str(room_id),
                "highlight_count": str(highlight_count),
                "timestamp": datetime.utcnow().isoformat(),
            },
            user_properties=user_properties
        )

    def track_reaction_added(
        self,
        user_id: int,
        message_id: int,
        room_id: int,
        emoji: str,
        user_properties: Dict[str, str] = None
    ) -> bool:
        """Rastreia reação adicionada a mensagem"""
        return self._send_event(
            event_name="reaction_added",
            user_id=user_id,
            params={
                "message_id": str(message_id),
                "room_id": str(room_id),
                "emoji": emoji,
                "timestamp": datetime.utcnow().isoformat(),
            },
            user_properties=user_properties
        )

    def track_presence_online(
        self,
        user_id: int,
        room_id: Optional[int] = None,
        duration_seconds: int = 0,
        user_properties: Dict[str, str] = None
    ) -> bool:
        """Rastreia presença online"""
        return self._send_event(
            event_name="presence_online",
            user_id=user_id,
            params={
                "room_id": str(room_id) if room_id else "general",
                "duration_seconds": str(duration_seconds),
                "timestamp": datetime.utcnow().isoformat(),
            },
            user_properties=user_properties
        )

    def track_room_joined(
        self,
        user_id: int,
        room_id: int,
        institution_id: int,
        user_properties: Dict[str, str] = None
    ) -> bool:
        """Rastreia entrada em uma sala"""
        return self._send_event(
            event_name="room_joined",
            user_id=user_id,
            params={
                "room_id": str(room_id),
                "institution_id": str(institution_id),
                "timestamp": datetime.utcnow().isoformat(),
            },
            user_properties=user_properties
        )

    def track_message_sent(
        self,
        user_id: int,
        room_id: int,
        message_length: int = 0,
        user_properties: Dict[str, str] = None
    ) -> bool:
        """Rastreia mensagem enviada"""
        return self._send_event(
            event_name="message_sent",
            user_id=user_id,
            params={
                "room_id": str(room_id),
                "message_length": str(message_length),
                "timestamp": datetime.utcnow().isoformat(),
            },
            user_properties=user_properties
        )

    # ─────────────────────────────────────────
    # INTERNAL: Envio de eventos
    # ─────────────────────────────────────────

    def _send_event(
        self,
        event_name: str,
        user_id: int,
        params: Dict[str, str],
        user_properties: Dict[str, str] = None
    ) -> bool:
        """
        Envia evento para GA4 via Measurement Protocol
        https://developers.google.com/analytics/devguides/collection/protocol/ga4
        """
        if not self.has_ga4:
            print(f"[GA4] GA4_MEASUREMENT_ID não configurado, ignorando evento {event_name}")
            return False

        try:
            import requests

            # Payload do Measurement Protocol
            payload = {
                "client_id": str(user_id),
                "user_id": str(user_id),
                "timestamp_micros": str(int(datetime.utcnow().timestamp() * 1_000_000)),
                "events": [
                    {
                        "name": event_name,
                        "params": params
                    }
                ]
            }

            # Adiciona user properties se fornecidas
            if user_properties:
                payload["user_properties"] = {
                    key: {"value": value}
                    for key, value in user_properties.items()
                }

            # Envia para GA4
            url = (
                f"https://www.google-analytics.com/mp/collect?"
                f"measurement_id={self.ga4_measurement_id}&"
                f"api_secret={self.ga4_api_secret}"
            )

            response = requests.post(url, json=payload, timeout=5)

            if response.status_code == 204:
                print(f"[GA4] Evento '{event_name}' rastreado com sucesso")
                return True
            else:
                print(f"[GA4] Erro ao rastrear '{event_name}': {response.status_code}")
                return False

        except Exception as e:
            print(f"[GA4] Erro ao enviar evento '{event_name}': {e}")
            return False

    # ─────────────────────────────────────────
    # RELATÓRIOS (read-only, requer setup GA4)
    # ─────────────────────────────────────────

    def get_event_stats(
        self,
        event_name: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Busca estatísticas de um evento nos últimos N dias
        Requer credenciais de serviço do GA4
        """
        if not HAS_GA4_LIBRARY:
            print("[GA4] google-analytics-data não instalado")
            return {}

        try:
            from google.oauth2.service_account import Credentials

            # Requer GOOGLE_APPLICATION_CREDENTIALS
            property_id = os.getenv("GA4_PROPERTY_ID")
            if not property_id:
                print("[GA4] GA4_PROPERTY_ID não configurado")
                return {}

            client = BetaAnalyticsDataClient()
            credentials = Credentials.from_service_account_info(
                json.loads(os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON", "{}"))
            )

            request = RunReportRequest(
                property=f"properties/{property_id}",
                data_range={"start_date": f"{days}daysAgo", "end_date": "today"},
                dimensions=[Dimension(name="eventName")],
                metrics=[
                    Metric(name="eventCount"),
                    Metric(name="totalUsers"),
                ]
            )

            response = client.run_report(request)

            stats = {}
            for row in response.rows:
                event = row.dimension_values[0].value
                count = int(row.metric_values[0].value)
                users = int(row.metric_values[1].value)

                if event == event_name:
                    stats = {
                        "event": event,
                        "count": count,
                        "users": users,
                        "avg_per_user": count / users if users > 0 else 0
                    }

            return stats

        except Exception as e:
            print(f"[GA4] Erro ao buscar stats de '{event_name}': {e}")
            return {}


# ─────────────────────────────────────────
# JAVASCRIPT GTAG (para frontend)
# ─────────────────────────────────────────

def get_ga4_script(measurement_id: str) -> str:
    """
    Retorna snippet de GA4 para colocar no HTML <head>
    """
    return f"""
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id={measurement_id}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());

  gtag('config', '{measurement_id}', {{
    'page_path': window.location.pathname,
    'page_title': document.title
  }});

  // Função auxiliar para trackear eventos customizados
  window.trackEvent = function(eventName, params = {{}}) {{
    gtag('event', eventName, params);
    console.log('[GA4]', eventName, params);
  }};
</script>
"""
