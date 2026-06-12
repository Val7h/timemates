"""
Reconnect email — asymmetric-reveal invite.

Lives in its own module so we can force Reply-To = noreply on the outbound
message (the standard ``email_service._send`` helper doesn't expose headers),
and so the body template stays close to the route handler that uses it.

The send path reuses ``email_service``'s sendability filter, kill-switch,
SMTP config, and base HTML template — we only override the headers and
the body copy.
"""
import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import email_service as mail


def send_reconnect_invite(to_email: str, turma_name: str, request_id: int,
                          full_name: str | None = None) -> bool:
    """Notifies the target that *someone* from Turma X wants to reconnect.

    ASYMMETRIC REVEAL — the email must give away nothing about the requester:
      * No sender name, photo, or email anywhere in the body.
      * Subject mentions only the Turma, never the requester.
      * Reply-To = noreply: there is no email-side engagement path. The
        recipient must open the app to discover who it is.

    Returns True if the message was queued for delivery, False if filtered
    or kill-switched off.
    """
    accept_url = f"{mail.BASE_URL}/reconnect/accept/{request_id}"
    body = f"""
    <h2 style="color:#1E3A5F;margin:0 0 8px;">Alguém quer reconectar com você</h2>
    <p style="color:#6B7280;font-size:14px;margin:0 0 20px;">
      Da Turma <strong>{turma_name}</strong>.
    </p>
    <div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:8px;padding:20px;margin:0 0 20px;">
      <p style="margin:0 0 12px;color:#374151;font-size:16px;line-height:1.5;">
        Lembra da turma <strong>{turma_name}</strong>?
        Alguém de lá quer voltar a falar com você.
      </p>
      <p style="margin:0;color:#6B7280;font-size:14px;font-style:italic;">
        Você só descobre quem é se aceitar o convite.
      </p>
    </div>
    <p style="color:#374151;font-size:15px;">
      Pode ser um amigo de infância, um colega que você perdeu o contato,
      alguém que estava na sua vida e sumiu. Só clicando você descobre.
    </p>
    {mail._btn(accept_url, 'Ver convite', '#1E3A5F')}
    <p style="color:#9CA3AF;font-size:12px;margin-top:24px;">
      Não responda a este e-mail. Para decidir, abra o app.
    </p>"""

    subject = f"Alguém da Turma {turma_name} quer reconectar com você"
    html = mail._base_template("Convite para reconectar", body)

    # Reuse the standard sendability and kill-switch guards.
    if not mail._is_sendable(to_email, full_name=full_name):
        return False
    if not mail.EMAIL_ENABLED:
        print(f"[EMAIL DISABLED] EMAIL_ENABLED=false — skipping reconnect to {to_email}")
        return False

    def _do_send():
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"]  = f"[TimeMates] {subject}"
            msg["From"]     = f"{mail.FROM_NAME} <{mail.FROM_ADDR}>"
            msg["To"]       = to_email
            # No-engagement-back-via-email: critical for the asymmetric reveal.
            msg["Reply-To"] = "noreply@timemates.app"
            msg.attach(MIMEText(html, "html", "utf-8"))
            with smtplib.SMTP(mail.SMTP_HOST, mail.SMTP_PORT) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.login(mail.SMTP_USER, mail.SMTP_PASS)
                smtp.sendmail(mail.FROM_ADDR, to_email, msg.as_string())
            print(f"[EMAIL OK] reconnect -> {to_email}")
        except Exception as e:
            print(f"[EMAIL ERR] reconnect -> {to_email} | {e}")

    threading.Thread(target=_do_send, daemon=True).start()
    return True
