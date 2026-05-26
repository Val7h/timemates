"""
TimeMates — Email Service
Usa Gmail SMTP (gratuito, sem bibliotecas extras).
Configure SMTP_USER e SMTP_PASS no .env ou diretamente aqui.
"""
import smtplib
import os
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# ── Configuração ──────────────────────────────────────────────────────────────
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")      # ex: noreply.timemates@gmail.com
SMTP_PASS = os.getenv("SMTP_PASS", "")      # Senha de App do Google
FROM_NAME = "TimeMates"
FROM_ADDR = SMTP_USER or "noreply@timemates.app"
BASE_URL  = os.getenv("BASE_URL", "http://localhost:8765")

EMAIL_ENABLED = bool(SMTP_USER and SMTP_PASS)


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
          Reconecte com quem fez parte da sua história
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


def _send(to_email: str, subject: str, html: str):
    """Envia e-mail em thread separada para não bloquear a requisição."""
    if not EMAIL_ENABLED:
        print(f"[EMAIL MOCK] Para: {to_email} | Assunto: {subject}")
        return

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
    """Boas-vindas após cadastro."""
    first = name.split()[0]
    body = f"""
    <h2 style="color:#1E3A5F;margin:0 0 8px;">Olá, {first}! 👋</h2>
    <p style="color:#6B7280;font-size:14px;margin:0 0 20px;">
      Bem-vindo(a) ao TimeMates! Sua conta foi criada com sucesso.
    </p>
    <p style="color:#374151;font-size:15px;line-height:1.6;">
      Agora você pode <strong>explorar instituições</strong>, entrar em salas de ex-colegas
      e reconectar com pessoas que fizeram parte da sua história. 🎓
    </p>
    {_btn(BASE_URL + '/index.html', 'Explorar agora', '#D4A853')}
    <hr style="border:none;border-top:1px solid #E5E0D6;margin:24px 0;"/>
    <p style="color:#9CA3AF;font-size:12px;text-align:center;">
      💡 Dica: Busque sua escola, faculdade ou empresa e veja se alguém da sua turma já está lá!
    </p>"""
    _send(to_email, f"Bem-vindo(a) ao TimeMates, {first}!", _base_template("Bem-vindo ao TimeMates", body))


def send_join_request_to_admin(admin_email: str, admin_name: str,
                                requester_name: str, room_name: str,
                                inst_name: str, room_id: int):
    """Avisa ADM da sala que alguém pediu para entrar."""
    first = admin_name.split()[0]
    body = f"""
    <h2 style="color:#1E3A5F;margin:0 0 8px;">Nova solicitação de acesso 🔔</h2>
    <p style="color:#6B7280;font-size:14px;margin:0 0 20px;">
      Olá, {first}! Alguém quer entrar na sua sala.
    </p>
    <div style="background:#F7F5F2;border-radius:8px;padding:20px;margin:0 0 20px;">
      <p style="margin:0 0 8px;color:#374151;"><strong>Solicitante:</strong> {requester_name}</p>
      <p style="margin:0 0 8px;color:#374151;"><strong>Sala:</strong> {room_name}</p>
      <p style="margin:0;color:#374151;"><strong>Instituição:</strong> {inst_name}</p>
    </div>
    <p style="color:#374151;font-size:15px;">
      Acesse o TimeMates para <strong>aprovar ou rejeitar</strong> a entrada.
    </p>
    {_btn(BASE_URL, 'Ver solicitação')}"""
    _send(admin_email, f"{requester_name} quer entrar na sala", _base_template("Nova solicitação", body))


def send_approved(to_email: str, name: str, room_name: str, inst_name: str):
    """Avisa usuário que foi aprovado em uma sala."""
    first = name.split()[0]
    body = f"""
    <h2 style="color:#22C55E;margin:0 0 8px;">✅ Você foi aprovado(a)!</h2>
    <p style="color:#6B7280;font-size:14px;margin:0 0 20px;">
      Boa notícia, {first}!
    </p>
    <div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:8px;padding:20px;margin:0 0 20px;">
      <p style="margin:0 0 8px;color:#374151;"><strong>Sala:</strong> {room_name}</p>
      <p style="margin:0;color:#374151;"><strong>Instituição:</strong> {inst_name}</p>
    </div>
    <p style="color:#374151;font-size:15px;">
      Sua solicitação foi <strong>aprovada</strong>! Agora você pode participar do chat,
      ver fotos e reconectar com sua turma. 🎉
    </p>
    {_btn(BASE_URL, 'Entrar na sala agora', '#22C55E')}"""
    _send(to_email, f"Você foi aprovado(a) em {room_name}", _base_template("Aprovado!", body))


def send_rejected(to_email: str, name: str, room_name: str, inst_name: str):
    """Avisa usuário que foi rejeitado."""
    first = name.split()[0]
    body = f"""
    <h2 style="color:#EF4444;margin:0 0 8px;">Solicitação não aprovada</h2>
    <p style="color:#6B7280;font-size:14px;margin:0 0 20px;">
      Olá, {first}.
    </p>
    <div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:8px;padding:20px;margin:0 0 20px;">
      <p style="margin:0 0 8px;color:#374151;"><strong>Sala:</strong> {room_name}</p>
      <p style="margin:0;color:#374151;"><strong>Instituição:</strong> {inst_name}</p>
    </div>
    <p style="color:#374151;font-size:15px;">
      Infelizmente sua solicitação de entrada não foi aprovada pelo administrador da sala.
      Caso acredite que houve um engano, você pode tentar novamente ou entrar em contato
      com quem criou a sala.
    </p>
    {_btn(BASE_URL, 'Explorar outras salas')}"""
    _send(to_email, f"Atualização sobre {room_name}", _base_template("Solicitação não aprovada", body))


def send_password_reset(to_email: str, name: str, reset_token: str):
    """Link de recuperação de senha."""
    first = name.split()[0]
    reset_url = f"{BASE_URL}/resetar-senha?token={reset_token}"
    body = f"""
    <h2 style="color:#1E3A5F;margin:0 0 8px;">Recuperação de senha 🔐</h2>
    <p style="color:#6B7280;font-size:14px;margin:0 0 20px;">
      Olá, {first}!
    </p>
    <p style="color:#374151;font-size:15px;line-height:1.6;">
      Recebemos uma solicitação para redefinir a senha da sua conta no TimeMates.
      Clique no botão abaixo para criar uma nova senha. O link é válido por <strong>1 hora</strong>.
    </p>
    {_btn(reset_url, 'Redefinir minha senha', '#D4A853')}
    <div style="background:#FEF3C7;border-radius:8px;padding:16px;margin:20px 0 0;">
      <p style="margin:0;color:#92400E;font-size:13px;">
        ⚠️ Se você não solicitou isso, ignore este e-mail. Sua senha permanece a mesma.
      </p>
    </div>"""
    _send(to_email, "Redefinição de senha", _base_template("Recuperação de senha", body))


def send_you_were_remembered(to_email: str, name: str, room_name: str, inst_name: str):
    """Avisa o usuário que alguém na sala lembra dele — ele foi 'lembrado'."""
    first = name.split()[0]
    body = f"""
    <h2 style="color:#1E3A5F;margin:0 0 8px;">🥹 Alguém lembra de você!</h2>
    <p style="color:#6B7280;font-size:14px;margin:0 0 20px;">
      Que saudade boa, {first}!
    </p>
    <div style="background:#FFF7ED;border:1px solid #FED7AA;border-radius:8px;padding:20px;margin:0 0 20px;">
      <p style="margin:0;color:#374151;font-size:16px;line-height:1.6;">
        Um colega da sala <strong>{room_name}</strong> ({inst_name}) te adicionou
        na lista de <em>"pessoas que eu lembro"</em>.<br/><br/>
        Você fez parte da história de alguém. ❤️
      </p>
    </div>
    <p style="color:#374151;font-size:15px;">
      Entre no TimeMates para ver quem lembra de você e dizer oi!
    </p>
    {_btn(BASE_URL, 'Ver quem lembra de mim', '#D4A853')}"""
    _send(to_email, "Alguém lembra de você no TimeMates!", _base_template("Você foi lembrado!", body))


def send_remembered_found(to_email: str, name: str, found_name: str, room_name: str):
    """Avisa que alguém que a pessoa lembrava entrou na sala."""
    first = name.split()[0]
    body = f"""
    <h2 style="color:#1E3A5F;margin:0 0 8px;">🎉 Alguém que você lembrava apareceu!</h2>
    <p style="color:#6B7280;font-size:14px;margin:0 0 20px;">
      Que surpresa boa, {first}!
    </p>
    <div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:8px;padding:20px;margin:0 0 20px;">
      <p style="margin:0 0 8px;color:#374151;font-size:16px;">
        <strong>{found_name}</strong> acabou de entrar na sala <strong>{room_name}</strong>!
      </p>
    </div>
    <p style="color:#374151;font-size:15px;">
      Você havia lembrado desta pessoa na lista "Lembrados". Agora ela está lá — vai dizer oi? 😊
    </p>
    {_btn(BASE_URL, 'Abrir a sala')}"""
    _send(to_email, f"{found_name} entrou na sala!", _base_template("Pessoa lembrada encontrada", body))
