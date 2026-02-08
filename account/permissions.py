"""
Require JWT-authenticated account (request.user) for all APIs except whitelisted public endpoints.
"""
from rest_framework import permissions


# Paths that do NOT require Bearer token (method can matter)
PUBLIC_ENDPOINTS = [
    ("POST", "/api/accounts/"),           # register
    ("GET", "/api/account/exists/"),      # check email exists
    ("POST", "/api/account/token/refresh/"),  # refresh token
]


def _is_public(request):
    path = request.path.rstrip("/") or "/"
    # Normalize path so /api/accounts matches
    for method, prefix in PUBLIC_ENDPOINTS:
        if request.method.upper() != method.upper():
            continue
        p = prefix.rstrip("/") or "/"
        if path == p or path.startswith(p + "/"):
            return True
    return False


class IsAuthenticatedAccount(permissions.BasePermission):
    """
    Allow only if request.account is set (valid Bearer token).
    Public endpoints (register, exists, refresh) are always allowed.
    """
    message = "Authentication required. Provide valid Bearer access_token in Authorization header."

    def has_permission(self, request, view):
        if _is_public(request):
            return True
        # request.user is set by our auth to the Account instance
        return getattr(request, "user", None) is not None
