from .models import SiteSetting


def site_settings(request):
    """Makes institution branding available to every template."""
    try:
        settings_obj = SiteSetting.load()
    except Exception:  # database not migrated yet
        settings_obj = None
    return {"site": settings_obj}
