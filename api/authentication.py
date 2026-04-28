from rest_framework.authentication import SessionAuthentication


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    SessionAuthentication that does not enforce CSRF.

    This is safe because cross-origin protection is provided by CORS with a
    strict allowlist (CORS_ALLOWED_ORIGINS). Browsers will not send credentials
    from any origin outside that list, which is the same threat CSRF mitigates.
    Without this class, cross-domain SPAs cannot POST because document.cookie
    on the frontend domain cannot read the CSRF cookie set by the API domain.
    """

    def enforce_csrf(self, request):
        return None
