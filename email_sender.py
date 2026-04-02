"""
SNB Mission Hunter — Email sender via SMTP (Gmail).
Envoie les propositions directement par email.
Nécessite un App Password Google dans SMTP_PASSWORD.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import Config

logger = logging.getLogger("snb.email_sender")


def send_proposal_email(config: Config, to_email: str, subject: str, body_html: str, reply_to: str = None):
    """Envoie un email de proposition via SMTP Gmail."""
    if not config.smtp_password or config.smtp_password in ("xxxx", ""):
        logger.warning("SMTP_PASSWORD non configuré — email non envoyé")
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = f"Baptiste Thevenot <{config.smtp_user}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to

    # Plain text version
    plain = body_html.replace("<br>", "\n").replace("<p>", "").replace("</p>", "\n")
    plain = plain.replace("<strong>", "").replace("</strong>", "")
    plain = plain.replace("<ul>", "").replace("</ul>", "")
    plain = plain.replace("<li>", "• ").replace("</li>", "\n")

    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    try:
        with smtplib.SMTP(config.smtp_host, config.smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(config.smtp_user, config.smtp_password)
            server.sendmail(config.smtp_user, to_email, msg.as_string())
        logger.info(f"✅ Email envoyé à {to_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur envoi email à {to_email}: {e}")
        return False
