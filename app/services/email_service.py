import logging
from celery import Celery
from app.core.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "backendforge",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_password_reset_email(self, email: str, full_name: str, token: str) -> None:
    """Send a password reset email. Retries up to 3 times on failure."""
    try:
        reset_url = f"https://app.backendforge.dev/reset-password?token={token}"
        logger.info(f"[EMAIL] Sending password reset to {email} — {reset_url}")

        # In production, replace this block with a real SMTP/SES call:
        # import emails
        # message = emails.html(
        #     subject="Reset your BackendForge password",
        #     html=f"<p>Hi {full_name},</p><p><a href='{reset_url}'>Reset password</a></p>",
        #     mail_from=(settings.EMAILS_FROM_NAME, settings.EMAILS_FROM_EMAIL),
        # )
        # r = message.send(
        #     to=email,
        #     smtp={"host": settings.SMTP_HOST, "port": settings.SMTP_PORT,
        #           "user": settings.SMTP_USER, "password": settings.SMTP_PASSWORD, "tls": True},
        # )
        # assert r.status_code == 250

        logger.info(f"[EMAIL] Password reset email queued for {email}")

    except Exception as exc:
        logger.exception(f"[EMAIL] Failed to send reset email to {email}")
        raise self.retry(exc=exc)


@celery_app.task
def send_welcome_email(email: str, full_name: str) -> None:
    """Send a welcome email after registration."""
    logger.info(f"[EMAIL] Welcome email sent to {email} ({full_name})")
