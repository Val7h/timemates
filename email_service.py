"""
TimeMates — Email Service
Usa Gmail SMTP (gratuito, sem bibliotecas extras).
Configure SMTP_USER e SMTP_PASS no .env ou diretamente aqui.
"""
import smtplib
import os
import threading
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

logger = logging.getLogger(__name__)

# ===== SENDGRID MIGRATION (2026-06-12) =====
# Try SendGrid first if SENDGRID_API_KEY is configured.
# Falls back to legacy SMTP code below (currently LOCKED).
_USE_SENDGRID = bool(os.getenv("SENDGRID_API_KEY"))
if _USE_SENDGRID:
    try:
        from email_service_sendgrid import (
            send_welcome as _sg_welcome,
            send_reconnect_request_email as _sg_reconnect,
            send_password_reset as _sg_password_reset,
        )
        logger.info("[EMAIL] Using SendGrid backend")
    except Exception as e:
        logger.exception("[EMAIL] SendGrid import failed, falling back to SMTP")
        _USE_SENDGRID = False

# ── Configuração ──────────────────────────────────────────────────────────────
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")      # ex: noreply.timemates@gmail.com
SMTP_PASS = os.getenv("SMTP_PASS", "")      # Senha de App do Google
FROM_NAME = "TimeMates"
FROM_ADDR = SMTP_USER or "noreply@timemates.app"
BASE_URL  = os.getenv("BASE_URL", "http://localhost:8765")

# EMERGENCY KILL-SWITCH: must be explicitly enabled via env var.
# Defaults to FALSE to prevent runaway bounce floods from seed/fake users.
EMAIL_ENABLED = (
    os.getenv("EMAIL_ENABLED", "false").lower() == "true"
    and bool(SMTP_USER and SMTP_PASS)
)

# TLDs that never resolve in DNS — sending to these guarantees a bounce.
_INVALID_TLDS = {"local", "test", "invalid", "example", "localhost"}
# Domains used by seed/demo data — never deliver to real SMTP.
_BLOCKED_DOMAIN_SUFFIXES = (
    "campinagrandeseed.local",
    "demo.timemates",
    "seed.timemates",
    "example.com",
    "example.org",
    "test.com",
)
# Substrings inside the address local-part / domain that indicate a fake/seed user.
_BLOCKED_EMAIL_SUBSTRINGS = ("@seed", ".seed.", "+seed@", "seeduser")
# Substrings in the user's full_name that indicate a seed/fake/test account.
_BLOCKED_NAME_SUBSTRINGS = ("seed", "fake", "[test]", "(test)", "test user")


def _is_sendable(to_email: str, full_name: str | None = None) -> bool:
    """Return False for fake/seed/invalid addresses we must never SMTP-send to.

    Defense-in-depth: validates address shape, TLD, domain suffix, address
    substrings, and (optionally) the user's display name for seed/fake markers.
    Every rejection is logged with the reason for post-mortem visibility.
    """
    if not to_email or "@" not in to_email:
        print(f"[EMAIL BLOCKED] Missing/invalid address: {to_email!r}")
        return False
    lower_email = to_email.lower().strip()
    domain = lower_email.split("@", 1)[-1]
    tld = domain.rsplit(".", 1)[-1] if "." in domain else domain
    if tld in _INVALID_TLDS:
        print(f"[EMAIL BLOCKED] Invalid TLD .{tld} for {to_email}")
        return False
    for bad in _BLOCKED_DOMAIN_SUFFIXES:
        if domain.endswith(bad):
            print(f"[EMAIL BLOCKED] Seed/demo domain {domain} for {to_email}")
            return False
    for marker in _BLOCKED_EMAIL_SUBSTRINGS:
        if marker in lower_email:
            print(f"[EMAIL BLOCKED] Seed marker {marker!r} in {to_email}")
            return False
    if full_name:
        lname = full_name.lower()
        for marker in _BLOCKED_NAME_SUBSTRINGS:
            if marker in lname:
                print(f"[EMAIL BLOCKED] Seed name marker {marker!r} in full_name={full_name!r} ({to_email})")
                return False
    return True


# ── Estilos base ──────────────────────────────────────────────────────────────
def _base_template(title: str, body_html: str) -> str:
    year = datetime.now().year
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{title}</title>
</head>
<body style="margin:0;padding:0;background:#F7F5F2;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#F7F5F2;padding:40px 20px;">
  <tr><td align="center">
    <table width="580" cellpadding="0" cellspacing="0" style="max-width:580px;width:100%;">

      <!-- Header -->
      <tr><td style="background:#1E3A5F;border-radius:12px 12px 0 0;padding:28px 40px;text-align:center;">
        <h1 style="margin:0;color:#fff;font-size:26px;font-weight:800;letter-spacing:-0.5px;">
          Time<span style="color:#D4A853;">Mates</span>
        </h1>
        <p style="margin:4px 0 0;color:rgba(255,255,255,0.7);font-size:13px;">
          Quem ainda lembra de você?
        </p>
      </td></tr>

      <!-- Body -->
      <tr><td style="background:#fff;padding:36px 40px;border-left:1px solid #E5E0D6;border-right:1px solid #E5E0D6;">
        {body_html}
      </td></tr>

      <!-- Footer -->
      <tr><td style="background:#F0EDE8;border-radius:0 0 12px 12px;border:1px solid #E5E0D6;border-top:none;
                     padding:20px 40px;text-align:center;">
        <p style="margin:0;color:#9CA3AF;font-size:12px;">
          © {year} TimeMates. Este e-mail foi enviado automaticamente, não responda.<br/>
          <a href="{BASE_URL}" style="color:#1E3A5F;">Acessar o TimeMates</a>
        </p>
      </td></tr>

    </table>
  </td></tr>
</table>
</body>
</html>"""


def _btn(url: str, label: str, color: str = "#1E3A5F") -> str:
    return f"""<div style="text-align:center;margin:28px 0;">
      <a href="{url}" style="background:{color};color:#fff;text-decoration:none;
         padding:14px 32px;border-radius:8px;font-weight:700;font-size:15px;display:inline-block;">
        {label}
      </a>
    </div>"""


def _send(to_email: str, subject: str, html: str, full_name: str | None = None):
    """Envia e-mail em thread separada para não bloquear a requisição.

    full_name is optional but if provided is passed to _is_sendable for an extra
    layer of seed/fake-user filtering (catches users with valid-looking domains
    but names like "Carlos Seed" or "[TEST] User").
    """
    # Hard guard #1: domain/TLD allowlist (blocks .local, seed domains, etc.)
    if not _is_sendable(to_email, full_name=full_name):
        return False
    # Hard guard #2: global kill-switch (EMAIL_ENABLED env var)
    if not EMAIL_ENABLED:
        print(f"[EMAIL DISABLED] EMAIL_ENABLED=false — skipping {to_email} | {subject}")
        return False

    def _do_send():
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[TimeMates] {subject}"
            msg["From"]    = f"{FROM_NAME} <{FROM_ADDR}>"
            msg["To"]      = to_email
            msg.attach(MIMEText(html, "html", "utf-8"))

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.login(SMTP_USER, SMTP_PASS)
                smtp.sendmail(FROM_ADDR, to_email, msg.as_string())
            print(f"[EMAIL OK] {to_email} | {subject}")
        except Exception as e:
            print(f"[EMAIL ERR] {to_email} | {e}")

    threading.Thread(target=_do_send, daemon=True).start()


# ── Templates de e-mail ───────────────────────────────────────────────────────

def send_welcome(to_email: str, name: str):
    """Boas-vindas após cadastro — tom saudoso/brotherly (Copy V2)."""
    if _USE_SENDGRID:
        return _sg_welcome(to_email, name)
    first = name.split()[0]
    body = f"""
    <h2 style="color:#1E3A5F;margin:0 0 8px;">Que bom que você chegou, {first}.</h2>
    <p style="color:#6B7280;font-size:14px;margin:0 0 20px;">
      A gente guardou seu lugar.
    </p>
    <p style="color:#374151;font-size:15px;line-height:1.6;">
      O TimeMates é o lugar de <strong>matar saudade da sua turma</strong> —
      gente da escola, da faculdade, da empresa, da rua onde você cresceu.
      Bora achar quem te conhecia?
    </p>
    {_btn(BASE_URL + '/index.html', 'Achar minha galera', '#D4A853')}
    <hr style="border:none;border-top:1px solid #E5E0D6;margin:24px 0;"/>
    <p style="color:#9CA3AF;font-size:12px;text-align:center;">
      Você é descobrível só por quem você escolher. Por padrão, você é invisível.
    </p>"""
    _send(to_email, f"{first}, a gente guardou seu lugar", _base_template("Bem-vindo ao TimeMates", body), full_name=name)


def send_join_request_to_admin(admin_email: str, admin_name: str,
                                requester_name: str, room_name: str,
                                inst_name: str, room_id: int):
    """Avisa ADM da sala que alguém pediu para entrar — tom Copy V2."""
    first = admin_name.split()[0]
    body = f"""
    <h2 style="color:#1E3A5F;margin:0 0 8px;">Ô {first}, olha quem apareceu.</h2>
    <p style="color:#6B7280;font-size:14px;margin:0 0 20px;">
      Tem gente querendo entrar na sua turma.
    </p>
    <div style="background:#F7F5F2;border-radius:8px;padding:20px;margin:0 0 20px;">
      <p style="margin:0 0 8px;color:#374151;"><strong>Quem:</strong> {requester_name}</p>
      <p style="margin:0 0 8px;color:#374151;"><strong>Sala:</strong> {room_name}</p>
      <p style="margin:0;color:#374151;"><strong>Onde:</strong> {inst_name}</p>
    </div>
    <p style="color:#374151;font-size:15px;">
      Você que decide. Lembra dessa pessoa? Bora abrir a porta.
    </p>
    {_btn(BASE_URL, 'Ver quem é')}"""
    _send(admin_email, f"{requester_name} quer matar saudade com a turma", _base_template("Nova solicitação", body))


def send_approved(to_email: str, name: str, room_name: str, inst_name: str):
    """Avisa usuário que foi aprovado em uma sala — tom Copy V2."""
    first = name.split()[0]
    body = f"""
    <h2 style="color:#22C55E;margin:0 0 8px;">Tá dentro, {first}.</h2>
    <p style="color:#6B7280;font-size:14px;margin:0 0 20px;">
      A turma te abriu a porta.
    </p>
    <div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:8px;padding:20px;margin:0 0 20px;">
      <p style="margin:0 0 8px;color:#374151;"><strong>Sala:</strong> {room_name}</p>
      <p style="margin:0;color:#374151;"><strong>Onde:</strong> {inst_name}</p>
    </div>
    <p style="color:#374151;font-size:15px;">
      Bora matar saudade. Manda um oi, posta uma foto antiga, conta o que ficou.
      A galera tá esperando.
    </p>
    {_btn(BASE_URL, 'Entrar no rolê', '#22C55E')}"""
    _send(to_email, f"Tá dentro de {room_name}, {first}", _base_template("Aprovado!", body))


def send_rejected(to_email: str, name: str, room_name: str, inst_name: str):
    """Avisa usuário que foi rejeitado — tom Copy V2 (humano, sem ferir)."""
    first = name.split()[0]
    body = f"""
    <h2 style="color:#1E3A5F;margin:0 0 8px;">{first}, dessa vez não rolou.</h2>
    <p style="color:#6B7280;font-size:14px;margin:0 0 20px;">
      A porta dessa sala ficou fechada.
    </p>
    <div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:8px;padding:20px;margin:0 0 20px;">
      <p style="margin:0 0 8px;color:#374151;"><strong>Sala:</strong> {room_name}</p>
      <p style="margin:0;color:#374151;"><strong>Onde:</strong> {inst_name}</p>
    </div>
    <p style="color:#374151;font-size:15px;">
      Acontece. Pode ter sido engano da turma — você pode tentar de novo, ou procurar
      outra sala da sua época. Tem muita gente que ainda lembra de você por aí.
    </p>
    {_btn(BASE_URL, 'Achar outra turma')}"""
    _send(to_email, f"Sobre a sala {room_name}, {first}", _base_template("Resposta da turma", body))


def send_password_reset(to_email: str, name: str, reset_token: str):
    """Link de recuperação de senha — tom Copy V2."""
    first = name.split()[0]
    reset_url = f"{BASE_URL}/resetar-senha?token={reset_token}"
    if _USE_SENDGRID:
        return _sg_password_reset(to_email, name, reset_url)
    body = f"""
    <h2 style="color:#1E3A5F;margin:0 0 8px;">Bora trocar essa senha, {first}.</h2>
    <p style="color:#6B7280;font-size:14px;margin:0 0 20px;">
      A gente recebeu o pedido. Aqui é o caminho.
    </p>
    <p style="color:#374151;font-size:15px;line-height:1.6;">
      Clica no botão e cria uma senha nova. O link vale por <strong>1 hora</strong> —
      depois disso ele expira e você pede outro de boa.
    </p>
    {_btn(reset_url, 'Criar senha nova', '#D4A853')}
    <div style="background:#FEF3C7;border-radius:8px;padding:16px;margin:20px 0 0;">
      <p style="margin:0;color:#92400E;font-size:13px;">
        Não foi você que pediu? Ignora esse e-mail — sua senha continua a mesma.
      </p>
    </div>"""
    _send(to_email, f"Sua senha nova tá a um clique, {first}", _base_template("Trocar senha", body))


def send_you_were_remembered(to_email: str, name: str, room_name: str, inst_name: str,
                              allow_reconnect_requests: bool = False):
    """Avisa o usuário que alguém na sala lembra dele — Copy V2.

    GATE DE PRIVACIDADE: este e-mail só é enviado se o destinatário tiver
    explicitamente habilitado `user.allow_reconnect_requests = TRUE`. Por padrão
    todo mundo é invisível e não recebe esse tipo de toque — opt-in puro.
    """
    if not allow_reconnect_requests:
        print(f"[EMAIL OPT-OUT] {to_email} não autorizou pedidos de reencontro — pulando 'remembered'")
        return False
    first = name.split()[0]
    body = f"""
    <h2 style="color:#1E3A5F;margin:0 0 8px;">{first}, alguém lembrou de você hoje.</h2>
    <p style="color:#6B7280;font-size:14px;margin:0 0 20px;">
      Que saudade boa, hein?
    </p>
    <div style="background:#FFF7ED;border:1px solid #FED7AA;border-radius:8px;padding:20px;margin:0 0 20px;">
      <p style="margin:0;color:#374151;font-size:16px;line-height:1.6;">
        Tem gente da sala <strong>{room_name}</strong> ({inst_name}) que ainda
        guarda lembrança de você.<br/><br/>
        Você fez parte da história de alguém. E isso não é pouco. ❤️
      </p>
    </div>
    <p style="color:#374151;font-size:15px;">
      Bora ver quem é? Pode ser hora de matar essa saudade.
    </p>
    {_btn(BASE_URL, 'Quem lembra de mim?', '#D4A853')}
    <hr style="border:none;border-top:1px solid #E5E0D6;margin:24px 0;"/>
    <p style="color:#9CA3AF;font-size:11px;text-align:center;line-height:1.5;">
      Você tá recebendo isso porque autorizou pedidos de reencontro nas suas configurações.
      Quer parar? <a href="{BASE_URL}/configuracoes" style="color:#1E3A5F;">É um clique aqui</a>.
    </p>"""
    _send(to_email, f"{first}, alguém lembrou de você hoje", _base_template("Você foi lembrado", body))


def send_followup_day3(to_email: str, name: str, allow_reconnect_requests: bool = False):
    """Dia 3: convida o usuário a voltar e procurar a turma — Copy V2.

    Reescrito 2026-06-12 (Copy V2): retorna ao posicionamento de saudade/reencontro
    com tom saudoso/brotherly. Substitui o antigo "Seus ex-colegas estão esperando"
    com linguagem mais humana e menos agressiva.

    GATE: só dispara se o usuário tiver `allow_reconnect_requests=TRUE`. Os
    filtros _is_sendable + EMAIL_ENABLED continuam aplicados a jusante.
    """
    if not allow_reconnect_requests:
        print(f"[EMAIL OPT-OUT] {to_email} não autorizou toques de reencontro — pulando day3")
        return False
    first = name.split()[0] if name else "amigo(a)"
    body = f"""
    <h2 style="color:#1E3A5F;margin:0 0 8px;">{first}, faz 3 dias que você passou por aqui.</h2>
    <p style="color:#6B7280;font-size:14px;margin:0 0 20px;">
      A turma cresce todo dia. Bora dar uma olhada?
    </p>
    <p style="color:#374151;font-size:15px;line-height:1.6;">
      Talvez aquele nome que você esqueceu apareça. Talvez alguém lembre de você.
      Saudade tem disso — chega sem avisar, mas vai embora bem mais leve quando a gente
      mata ela junto.
    </p>
    {_btn(BASE_URL + '/index.html', 'Achar minha galera', '#D4A853')}
    <hr style="border:none;border-top:1px solid #E5E0D6;margin:24px 0;"/>
    <p style="color:#9CA3AF;font-size:11px;text-align:center;line-height:1.5;">
      Você tá recebendo isso porque autorizou pedidos de reencontro.
      Não quer mais? <a href="{BASE_URL}/configuracoes" style="color:#1E3A5F;">Desativa aqui</a>.
    </p>"""
    _send(to_email, f"{first}, sua turma cresceu essa semana",
          _base_template("Bora matar saudade", body), full_name=name)


def send_followup_day7(to_email: str, name: str, allow_reconnect_requests: bool = False):
    """Dia 7: chama a galera — Copy V2 (saudoso/brotherly + opt-in)."""
    if not allow_reconnect_requests:
        print(f"[EMAIL OPT-OUT] {to_email} não autorizou — pulando day7")
        return False
    first = name.split()[0]
    body = f"""
    <h2 style="color:#1E3A5F;margin:0 0 8px;">{first}, ninguém mata saudade sozinho.</h2>
    <p style="color:#6B7280;font-size:14px;margin:0 0 20px;">
      Uma semana aqui, e a sua sala ainda tá meio vazia.
    </p>
    <p style="color:#374151;font-size:15px;line-height:1.6;">
      Chama a galera. Manda o link no grupo do zap antigo, naquele que ninguém manda
      mensagem mas todo mundo lê. Você vai ver — quando um volta, o resto vem junto.
    </p>
    <div style="background:#F7F5F2;border-radius:8px;padding:20px;margin:20px 0;text-align:center;">
      <p style="margin:0 0 8px;color:#6B7280;font-size:13px;">Cola isso no grupo:</p>
      <p style="margin:0;color:#374151;font-size:14px;font-style:italic;">
        "Galera, lembra da gente? Tô no TimeMates matando saudade da nossa turma.<br/>
        Bora? {BASE_URL}"
      </p>
    </div>
    {_btn(BASE_URL + '/index.html', 'Chamar a galera', '#1E3A5F')}
    <hr style="border:none;border-top:1px solid #E5E0D6;margin:24px 0;"/>
    <p style="color:#9CA3AF;font-size:11px;text-align:center;line-height:1.5;">
      Recebendo porque autorizou pedidos de reencontro. <a href="{BASE_URL}/configuracoes" style="color:#1E3A5F;">Desativar</a>.
    </p>"""
    _send(to_email, f"{first}, chama a galera pra cá",
          _base_template("Chama a turma", body), full_name=name)


def send_remembered_found(to_email: str, name: str, found_name: str, room_name: str,
                           allow_reconnect_requests: bool = False):
    """Avisa que alguém que a pessoa lembrava entrou na sala — Copy V2.

    GATE: só envia se o destinatário autorizou pedidos de reencontro.
    """
    if not allow_reconnect_requests:
        print(f"[EMAIL OPT-OUT] {to_email} não autorizou — pulando remembered_found")
        return False
    first = name.split()[0]
    body = f"""
    <h2 style="color:#1E3A5F;margin:0 0 8px;">{first}, olha quem reapareceu.</h2>
    <p style="color:#6B7280;font-size:14px;margin:0 0 20px;">
      Aquela pessoa que você guardou na memória... voltou.
    </p>
    <div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:8px;padding:20px;margin:0 0 20px;">
      <p style="margin:0 0 8px;color:#374151;font-size:16px;line-height:1.6;">
        <strong>{found_name}</strong> acabou de chegar na sala <strong>{room_name}</strong>.
      </p>
    </div>
    <p style="color:#374151;font-size:15px;">
      Você tinha guardado essa pessoa na sua lista de lembrados. Agora ela tá ali.
      Bora dizer oi? Pode ser uma frase só. Às vezes é o que faltava.
    </p>
    {_btn(BASE_URL, 'Dizer oi')}
    <hr style="border:none;border-top:1px solid #E5E0D6;margin:24px 0;"/>
    <p style="color:#9CA3AF;font-size:11px;text-align:center;">
      Recebendo porque autorizou pedidos de reencontro. <a href="{BASE_URL}/configuracoes" style="color:#1E3A5F;">Desativar</a>.
    </p>"""
    _send(to_email, f"{found_name} reapareceu, {first}", _base_template("Reencontro", body))
