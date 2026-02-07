"""
JWT access and refresh tokens for Account (not Django User).
Use Authorization: Bearer <access_token> for protected endpoints.
"""
import jwt
from datetime import datetime, timedelta
from django.conf import settings

JWT_ALGORITHM = "HS256"
ACCESS_TYPE = "access"
REFRESH_TYPE = "refresh"


def _now():
    return datetime.utcnow()


def generate_tokens_for_account(account):
    """
    Return dict with access_token and refresh_token for the given Account.
    """
    secret = getattr(settings, "JWT_SECRET_KEY", settings.SECRET_KEY)
    access_minutes = getattr(settings, "JWT_ACCESS_TOKEN_LIFETIME_MINUTES", 60)
    refresh_days = getattr(settings, "JWT_REFRESH_TOKEN_LIFETIME_DAYS", 7)

    now = _now()
    access_exp = now + timedelta(minutes=access_minutes)
    refresh_exp = now + timedelta(days=refresh_days)

    access_payload = {
        "account_id": account.id,
        "email": account.email,
        "type": ACCESS_TYPE,
        "exp": access_exp,
        "iat": now,
    }
    refresh_payload = {
        "account_id": account.id,
        "type": REFRESH_TYPE,
        "exp": refresh_exp,
        "iat": now,
    }

    access_token = jwt.encode(access_payload, secret, algorithm=JWT_ALGORITHM)
    refresh_token = jwt.encode(refresh_payload, secret, algorithm=JWT_ALGORITHM)

    # PyJWT 2.x returns str; 1.x returns bytes
    if hasattr(access_token, "decode"):
        access_token = access_token.decode("utf-8")
    if hasattr(refresh_token, "decode"):
        refresh_token = refresh_token.decode("utf-8")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


def decode_access_token(token):
    """
    Validate access token and return account_id or None.
    """
    try:
        secret = getattr(settings, "JWT_SECRET_KEY", settings.SECRET_KEY)
        payload = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != ACCESS_TYPE:
            return None
        return payload.get("account_id")
    except Exception:
        return None


def decode_refresh_token(token):
    """
    Validate refresh token and return account_id or None.
    """
    try:
        secret = getattr(settings, "JWT_SECRET_KEY", settings.SECRET_KEY)
        payload = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != REFRESH_TYPE:
            return None
        return payload.get("account_id")
    except Exception:
        return None
