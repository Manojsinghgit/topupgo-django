"""
JWT Bearer authentication for Account. Sets request.account from Authorization header.
"""
from rest_framework import authentication

from .models import Account
from .tokens import decode_access_token


class AccountJWTAuthentication(authentication.BaseAuthentication):
    """
    Expects header: Authorization: Bearer <access_token>
    Sets request.account to the Account instance or None if missing/invalid.
    """
    keyword = "Bearer"

    def authenticate(self, request):
        auth = request.META.get("HTTP_AUTHORIZATION") or ""
        if not auth.startswith(self.keyword + " "):
            return None
        token = auth[len(self.keyword) + 1 :].strip()
        if not token:
            return None
        account_id = decode_access_token(token)
        if not account_id:
            return None
        try:
            account = Account.objects.get(pk=account_id, is_active=True)
        except Account.DoesNotExist:
            return None
        return (account, token)
