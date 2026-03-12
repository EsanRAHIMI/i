import smtplib
from email.message import EmailMessage
import ssl

from ..config import settings


class EmailService:
    def __init__(self) -> None:
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.username = settings.SMTP_USERNAME
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL
        self.use_tls = settings.SMTP_USE_TLS
        self.use_ssl = settings.SMTP_USE_SSL

    def _validate(self) -> None:
        if not self.host:
            raise RuntimeError("SMTP_HOST is not set")
        if not self.from_email:
            raise RuntimeError("SMTP_FROM_EMAIL is not set")
        if self.use_ssl and self.use_tls:
            raise RuntimeError("Only one of SMTP_USE_SSL or SMTP_USE_TLS can be enabled")

    def send(self, to_email: str, subject: str, html_body: str) -> None:
        self._validate()

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = to_email
        msg.set_content(html_body, subtype="html")

        if self.use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(self.host, self.port, context=context) as server:
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.send_message(msg)
            return

        with smtplib.SMTP(self.host, self.port) as server:
            if self.use_tls:
                context = ssl.create_default_context()
                server.starttls(context=context)
            if self.username and self.password:
                server.login(self.username, self.password)
            server.send_message(msg)

    def send_password_reset_email(self, to_email: str, reset_url: str) -> None:
        subject = "Reset your password"
        html_body = (
            "<p>You requested a password reset.</p>"
            f"<p><a href=\"{reset_url}\">Click here to reset your password</a></p>"
            "<p>If you didn't request this, you can ignore this email.</p>"
        )
        self.send(to_email=to_email, subject=subject, html_body=html_body)


email_service = EmailService()
