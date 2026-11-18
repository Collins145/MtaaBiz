from django.conf import settings


def oauth_settings(request):
    return {
        "google_oauth_enabled": settings.GOOGLE_OAUTH_ENABLED,
    }
