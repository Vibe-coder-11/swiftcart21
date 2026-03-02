from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.http import HttpResponse


class DynamicCSRFMiddleware(MiddlewareMixin):
    """
    Optional middleware to add localhost preview origins in debug mode.
    Disabled by default via ALLOW_DYNAMIC_CSRF_ORIGINS=False.
    """
    
    def process_request(self, request):
        """Add dynamic CSRF trusted origins for localhost previews only."""
        if not (settings.DEBUG and getattr(settings, 'ALLOW_DYNAMIC_CSRF_ORIGINS', False)):
            return None

        host = request.get_host()
        if host.startswith(('localhost:', '127.0.0.1:')):
            if not hasattr(settings, '_dynamic_csrf_origins'):
                settings._dynamic_csrf_origins = set()

            origin = f"http://{host}"
            settings._dynamic_csrf_origins.add(origin)
            current_origins = set(settings.CSRF_TRUSTED_ORIGINS)
            current_origins.update(settings._dynamic_csrf_origins)
            settings.CSRF_TRUSTED_ORIGINS = list(current_origins)
        return None
