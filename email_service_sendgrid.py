"""SendGrid HTTP API email backend.
Replaces Gmail SMTP backend which was locked after bombardment crisis.

Configuration:
- SENDGRID_API_KEY (Render env var) - required to enable
- EMAIL_SENDER (Render env var) - default: noreply@timemates.app or sender verified in SendGrid
- EMAIL_ENABLED (Render env var) - master kill switch, stays false until tested

Safety:
- Same _is_sendable() allowlist from email_service.py (blocks .local/.test/seed domains)
- Same suppression of fake users
- Same EMAIL_ENABLED kill switch
- SendGrid has its own bounce handling (no risk to founder's gmail)
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "noreply@timemates.app")
EMAIL_SENDER_NAME = os.getenv("EMAIL_SENDER_NAME", "TimeMates")
EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
BLOCK_INVALID_DOMAINS = os.getenv("BLOCK_INVALID_DOMAINS", "true").lower() == "true"

# Bad domains (reuse from email_service.py)
BAD_TLDS = {'.local', '.test', '.invalid', '.example', '.localhost'}
BAD_DOMAIN_SUFFIXES = {'campinagrandeseed.local', 'demo.timemates', 'seed.timemates', 'example.com', 'example.org', 'test.com'}


def _is_sendable(email: str, full_name: str = "") -> bool:
    """Same defense-in-depth filter as legacy email_service.py."""
    if not email or '@' not in email:
        return False
    elower = email.lower()
    if '@seed' in elower:
        return False
    for tld in BAD_TLDS:
        if elower.endswith(tld):
            return False
    for suffix in BAD_DOMAIN_SUFFIXES:
        if suffix in elower:
            return False
    fname_lower = (full_name or '').lower()
    if any(marker in fname_lower for marker in ['seed', 'fake', 'test user', 'demo']):
        return False
    return True


def _send_via_sendgrid(
    to_email: str,
    to_name: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
) -> dict:
    """Send 1 email via SendGrid HTTP API. Returns dict with status."""
    if not EMAIL_ENABLED:
        logger.info(f"[EMAIL_DISABLED] Skip send to {to_email}")
        return {"sent": False, "reason": "EMAIL_ENABLED=false"}
    if BLOCK_INVALID_DOMAINS and not _is_sendable(to_email, to_name):
        logger.warning(f"[EMAIL_BLOCKED] Invalid domain/seed: {to_email}")
        return {"sent": False, "reason": "invalid_domain"}
    if not SENDGRID_API_KEY:
        logger.error("[SENDGRID] SENDGRID_API_KEY not configured")
        return {"sent": False, "reason": "no_api_key"}

    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Email, To

        message = Mail(
            from_email=Email(EMAIL_SENDER, EMAIL_SENDER_NAME),
            to_emails=To(to_email, to_name),
            subject=subject,
            html_content=html_content,
        )
        if text_content:
            message.plain_text_content = text_content

        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)

        if response.status_code in (200, 201, 202):
            logger.info(f"[SENDGRID] Sent to {to_email} (status {response.status_code})")
            return {
                "sent": True,
                "status_code": response.status_code,
                "message_id": response.headers.get('X-Message-Id', ''),
            }
        else:
            logger.error(f"[SENDGRID] Failed: status={response.status_code}, body={response.body[:200]}")
            return {"sent": False, "reason": f"sendgrid_status_{response.status_code}"}
    except Exception as e:
        logger.exception(f"[SENDGRID] Exception sending to {to_email}")
        return {"sent": False, "reason": "exception", "error": str(e)}


# ===== PUBLIC API (compatible with legacy email_service.py) =====

def send_welcome(email: str, full_name: str) -> dict:
    """Welcome email apos signup."""
    first = (full_name or 'Voce').split()[0]
    subject = f"Bem-vindo ao TimeMates, {first}"
    html = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 480px; margin: 0 auto; padding: 24px;">
        <h1 style="color: #d4a853;">Bem-vindo, {first}.</h1>
        <p>Que bom que voce chegou ao TimeMates.</p>
        <p>Aqui, a gente ajuda voce a reencontrar quem fez parte da sua historia - turma da escola, faculdade, bairro, empresa.</p>
        <p><strong>Proximo passo:</strong> encontre sua turma e comece a matar saudade.</p>
        <a href="https://timemates.onrender.com" style="display:inline-block; background:#d4a853; color:#000; padding:12px 24px; text-decoration:none; border-radius:8px; margin-top:16px;">Procurar minha turma</a>
        <p style="margin-top:32px; font-size:13px; color:#888;">Voce esta invisivel por padrao. Ninguem te encontra sem sua permissao.</p>
    </div>
    """
    return _send_via_sendgrid(email, full_name, subject, html)


def send_reconnect_request_email(
    target_email: str,
    target_name: str,
    turma_label: str,
    accept_url: str,
) -> dict:
    """Asymmetric reveal: target NAO sabe quem e o requester."""
    first = (target_name or 'Voce').split()[0]
    subject = f"Alguem da {turma_label} quer reconectar com voce"
    html = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 480px; margin: 0 auto; padding: 24px;">
        <h1 style="color: #d4a853;">{first}, alguem da sua turma quer matar saudade.</h1>
        <p>Lembra da <strong>{turma_label}</strong>?</p>
        <p>Alguem de la quer voltar a falar com voce.</p>
        <p>Voce so descobre quem e se aceitar.</p>
        <a href="{accept_url}" style="display:inline-block; background:#d4a853; color:#000; padding:12px 24px; text-decoration:none; border-radius:8px; margin-top:16px;">Ver convite</a>
        <p style="margin-top:32px; font-size:13px; color:#888;">Se preferir nao receber esses convites, mude em /api/me/visibility no app.</p>
    </div>
    """
    return _send_via_sendgrid(target_email, target_name, subject, html)


def send_password_reset(email: str, full_name: str, reset_url: str) -> dict:
    first = (full_name or 'Voce').split()[0]
    subject = f"Recuperar acesso, {first}"
    html = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 480px; margin: 0 auto; padding: 24px;">
        <h1>Recuperar sua conta TimeMates</h1>
        <p>Voce pediu pra recuperar acesso.</p>
        <a href="{reset_url}" style="display:inline-block; background:#d4a853; color:#000; padding:12px 24px; text-decoration:none; border-radius:8px; margin-top:16px;">Definir nova senha</a>
        <p style="margin-top:32px; font-size:13px; color:#888;">Se nao foi voce, ignore esse email - sua conta segue segura.</p>
    </div>
    """
    return _send_via_sendgrid(email, full_name, subject, html)


def is_email_configured() -> dict:
    """Diagnostic helper. Returns config status (no secrets exposed)."""
    return {
        "email_enabled": EMAIL_ENABLED,
        "sendgrid_api_key_set": bool(SENDGRID_API_KEY),
        "sender_configured": bool(EMAIL_SENDER),
        "backend": "sendgrid_api",
        "block_invalid_domains": BLOCK_INVALID_DOMAINS,
    }
