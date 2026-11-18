from .models import UserNotification, UserNotificationPreference


def notify_user(user, message, url):
    if user is None:
        return None
    preferences = UserNotificationPreference.objects.filter(user=user).first()
    if preferences and not preferences.in_app_enabled:
        return None
    return UserNotification.objects.create(user=user, message=message, url=url)
