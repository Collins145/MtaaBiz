from django.conf import settings as django_settings
from django.core.mail import send_mail

from .models import UserNotification, UserNotificationPreference


def send_notification_email(user, subject, message):
    """Best-effort transactional email. Never raises: email failures must not
    break the request that triggered the notification. Uses the configured
    EMAIL_BACKEND (console in development, SMTP in production)."""
    if not user or not getattr(user, "email", ""):
        return False
    try:
        send_mail(
            subject=f"MtaaBiz — {subject}",
            message=message,
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
        return True
    except Exception:
        return False


def notify_user(user, message, url, email_subject=None):
    if user is None:
        return None

    notification = None
    preferences = UserNotificationPreference.objects.filter(user=user).first()
    if preferences is None or preferences.in_app_enabled:
        notification = UserNotification.objects.create(user=user, message=message, url=url)

    # Also send an email when SMTP is configured (console backend in dev just prints).
    email_backend = django_settings.EMAIL_BACKEND
    if email_subject and "console" not in email_backend:
        link = f"{django_settings.SITE_BASE_URL}{url}" if url else ""
        body = f"{message}\n\n{link}".strip()
        send_notification_email(user, email_subject, body)

    return notification
