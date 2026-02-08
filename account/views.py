from decimal import Decimal
from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Account
from .tokens import generate_tokens_for_account, decode_refresh_token
from wallet.models import Wallet
from wallet.views import _wallet_to_dict, _transaction_to_dict


def _account_to_dict(account):
    """Build response dict from Account instance. No serializer."""
    return {
        "id": account.id,
        "email": account.email,
        "username": account.username,
        "phone_no": account.phone_no or "",
        "profile_photo": account.profile_photo.url if account.profile_photo else None,
        "first_name": account.first_name or "",
        "last_name": account.last_name or "",
        "date_of_birth": str(account.date_of_birth) if account.date_of_birth else None,
        "is_verified": account.is_verified,
        "created_at": account.created_at,
        "updated_at": account.updated_at,
    }


def _validate_account_create(data):
    """Validate POST data in view. Returns (is_valid, data_or_errors)."""
    errors = {}
    email = (data.get("email") or "").strip()
    username = (data.get("username") or "").strip()
    if not email:
        errors["email"] = ["This field is required."]
    if not username:
        errors["username"] = ["This field is required."]
    if errors:
        return False, errors
    if Account.objects.filter(email=email).exists():
        errors["email"] = ["Account with this email already exists."]
    if Account.objects.filter(username=username).exists():
        errors["username"] = ["Account with this username already exists."]
    if errors:
        return False, errors
    return True, data


def _validate_account_update(data, instance):
    """Validate PATCH/PUT data. Check unique only if field is changing."""
    errors = {}
    email = (data.get("email") or "").strip() or instance.email
    username = (data.get("username") or "").strip() or instance.username
    if email != instance.email and Account.objects.filter(email=email).exists():
        errors["email"] = ["Account with this email already exists."]
    if username != instance.username and Account.objects.filter(username=username).exists():
        errors["username"] = ["Account with this username already exists."]
    if errors:
        return False, errors
    return True, data


# OpenAPI request body schema for account create/update (Swagger UI body field)
_ACCOUNT_BODY_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["email", "username"],
    properties={
        "email": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL, description="Account email"),
        "username": openapi.Schema(type=openapi.TYPE_STRING, description="Unique username"),
        "phone_no": openapi.Schema(type=openapi.TYPE_STRING, description="Phone number"),
        "first_name": openapi.Schema(type=openapi.TYPE_STRING),
        "last_name": openapi.Schema(type=openapi.TYPE_STRING),
        "date_of_birth": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE, description="YYYY-MM-DD"),
        "is_verified": openapi.Schema(type=openapi.TYPE_BOOLEAN, default=False),
    },
)

class AccountListCreateAPIView(APIView):
    """
    GET: List all active accounts.
    POST: Create account. Validation and create done in view.
    """

    @swagger_auto_schema(tags=["Account"], operation_summary="List accounts (current user only)")
    def get(self, request):
        # Token required; return only current account
        account = getattr(request, "user", None)
        if not account:
            return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)
        payload = [_account_to_dict(account)]
        return Response(payload)

    @swagger_auto_schema(
        tags=["Account"],
        operation_summary="Create account",
        operation_description="Creates a new account. Response includes **access_token** and **refresh_token**.",
        request_body=_ACCOUNT_BODY_SCHEMA,
        responses={201: openapi.Response(description="Account created; includes access_token and refresh_token")},
    )
    def post(self, request):
        data = request.data
        is_valid, result = _validate_account_create(data)
        if not is_valid:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        data = result
        try:
            account = Account.objects.create(
                email=(data.get("email") or "").strip(),
                username=(data.get("username") or "").strip(),
                phone_no=(data.get("phone_no") or "").strip() or "",
                first_name=(data.get("first_name") or "").strip() or "",
                last_name=(data.get("last_name") or "").strip() or "",
                date_of_birth=data.get("date_of_birth") or None,
                is_verified=bool(data.get("is_verified", False)),
            )
        except IntegrityError:
            return Response(
                {"detail": "Account with this email or username already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if data.get("profile_photo"):
            account.profile_photo = data["profile_photo"]
            account.save(update_fields=["profile_photo"])
        payload = _account_to_dict(account)
        tokens = generate_tokens_for_account(account)
        payload["access_token"] = tokens["access_token"]
        payload["refresh_token"] = tokens["refresh_token"]
        return Response(payload, status=status.HTTP_201_CREATED)


class AccountDetailAPIView(APIView):
    """
    GET / PUT / PATCH / DELETE account. Only own account (token) allowed.
    """

    def get_object(self, request, pk):
        account = getattr(request, "user", None)
        if not account or account.pk != pk:
            return None
        return account

    @swagger_auto_schema(tags=["Account"], operation_summary="Get account by ID (own only)")
    def get(self, request, pk):
        account = self.get_object(request, pk)
        if account is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(_account_to_dict(account))

    @swagger_auto_schema(
        tags=["Account"],
        operation_summary="Update account (full)",
        request_body=_ACCOUNT_BODY_SCHEMA,
        responses={200: openapi.Response(description="Account updated")},
    )
    def put(self, request, pk):
        account = self.get_object(request, pk)
        if account is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        is_valid, result = _validate_account_update(request.data, account)
        if not is_valid:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        data = result
        account.email = (data.get("email") or account.email or "").strip()
        account.username = (data.get("username") or account.username or "").strip()
        account.phone_no = (data.get("phone_no") if "phone_no" in data else account.phone_no) or ""
        account.first_name = (data.get("first_name") if "first_name" in data else account.first_name) or ""
        account.last_name = (data.get("last_name") if "last_name" in data else account.last_name) or ""
        account.date_of_birth = data.get("date_of_birth") if "date_of_birth" in data else account.date_of_birth
        account.is_verified = data.get("is_verified", account.is_verified)
        if data.get("profile_photo") is not None:
            account.profile_photo = data["profile_photo"]
        account.save()
        return Response(_account_to_dict(account))

    @swagger_auto_schema(
        tags=["Account"],
        operation_summary="Update account (partial)",
        request_body=_ACCOUNT_BODY_SCHEMA,
        responses={200: openapi.Response(description="Account updated")},
    )
    def patch(self, request, pk):
        account = self.get_object(request, pk)
        if account is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        is_valid, result = _validate_account_update(request.data, account)
        if not is_valid:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        data = result
        if "email" in data and data["email"] is not None:
            account.email = str(data["email"]).strip()
        if "username" in data and data["username"] is not None:
            account.username = str(data["username"]).strip()
        if "phone_no" in data:
            account.phone_no = (data["phone_no"] or "").strip() or ""
        if "first_name" in data:
            account.first_name = (data["first_name"] or "").strip() or ""
        if "last_name" in data:
            account.last_name = (data["last_name"] or "").strip() or ""
        if "date_of_birth" in data:
            account.date_of_birth = data["date_of_birth"] or None
        if "is_verified" in data:
            account.is_verified = bool(data["is_verified"])
        if "profile_photo" in data:
            account.profile_photo = data["profile_photo"] or None
        account.save()
        return Response(_account_to_dict(account))

    def delete(self, request, pk):
        account = self.get_object(request, pk)
        if account is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        account.is_active = False
        account.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class AccountExistsView(APIView):
    """
    GET ?email=... — Returns exists (true/false). When exists=true, also returns access_token and refresh_token.
    """

    @swagger_auto_schema(
        tags=["Account"],
        operation_summary="Check if account exists by email",
        operation_description="Returns **exists** (true/false). When **exists=true**, also returns **access_token** and **refresh_token**.",
        manual_parameters=[
            openapi.Parameter("email", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True, description="Account email"),
        ],
        responses={
            200: openapi.Response(
                description="exists=true returns access_token and refresh_token; exists=false does not",
            ),
        },
    )
    def get(self, request):
        email = (request.query_params.get("email") or "").strip()

        if not email:
            return Response(
                {"detail": "email is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        account = Account.objects.filter(email=email, is_active=True).first()
        exists = account is not None

        payload = {"exists": exists}
        if exists:
            tokens = generate_tokens_for_account(account)
            payload["access_token"] = tokens["access_token"]
            payload["refresh_token"] = tokens["refresh_token"]

        return Response(payload, status=status.HTTP_200_OK)


class TokenRefreshAPIView(APIView):
    """
    POST with body {"refresh_token": "..."}. Returns new access_token and refresh_token.
    """

    @swagger_auto_schema(
        tags=["Account"],
        operation_summary="Refresh tokens",
        operation_description="Send **refresh_token** in body. Returns new **access_token** and **refresh_token**.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["refresh_token"],
            properties={"refresh_token": openapi.Schema(type=openapi.TYPE_STRING, description="Your refresh token")},
        ),
        responses={
            200: openapi.Response(description="New access_token and refresh_token"),
            401: openapi.Response(description="Invalid or expired refresh token"),
        },
    )
    def post(self, request):
        refresh_token = (request.data.get("refresh_token") or "").strip()
        if not refresh_token:
            return Response(
                {"detail": "refresh_token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        account_id = decode_refresh_token(refresh_token)
        if not account_id:
            return Response(
                {"detail": "Invalid or expired refresh token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            account = Account.objects.get(pk=account_id, is_active=True)
        except Account.DoesNotExist:
            return Response(
                {"detail": "Invalid or expired refresh token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        tokens = generate_tokens_for_account(account)
        return Response(tokens, status=status.HTTP_200_OK)


class AccountDetailByEmailAPIView(APIView):
    """
    GET: Pass email as query param (?email=user@example.com).
    Returns that account's detail, wallet detail (if any), and all transactions for that wallet.
    """

    @swagger_auto_schema(
        tags=["Account"],
        operation_summary="Get account details by email",
        operation_description="Pass **email** as query param. Returns account, wallet and transactions for that email.",
        manual_parameters=[
            openapi.Parameter("email", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True, description="Account email"),
        ],
        responses={
            200: openapi.Response(
                description="Account with wallet and transactions",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "account": openapi.Schema(type=openapi.TYPE_OBJECT),
                        "wallet": openapi.Schema(type=openapi.TYPE_OBJECT, nullable=True),
                        "transactions": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                    },
                ),
            ),
            404: openapi.Response(description="Account not found"),
        },
    )
    def get(self, request):
        email = (request.query_params.get("email") or "").strip()
        if not email:
            return Response(
                {"detail": "email is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Only allow own account (token)
        account = getattr(request, "user", None)
        if not account or account.email != email:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        wallet = Wallet.objects.filter(account=account, is_active=True).first()

        transactions = []
        if wallet:
            transactions = list(
                wallet.transactions.filter(is_active=True).order_by("-created_at")
            )
            transactions = [_transaction_to_dict(t) for t in transactions]

        payload = {
            "account": _account_to_dict(account),
            "wallet": _wallet_to_dict(wallet) if wallet else None,
            "transactions": transactions,
        }
        return Response(payload)


class AccountMeAPIView(APIView):
    """
    GET: Returns full details for the logged-in account (token): account, wallet, transactions.
    """

    @swagger_auto_schema(
        tags=["Account"],
        operation_summary="Get my details (requires Bearer token)",
        operation_description="Returns full account, wallet and transactions for the logged-in account.",
        security=[{"Bearer": []}],
        responses={
            200: openapi.Response(
                description="Account with wallet and transactions",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "account": openapi.Schema(type=openapi.TYPE_OBJECT),
                        "wallet": openapi.Schema(type=openapi.TYPE_OBJECT, nullable=True),
                        "transactions": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                    },
                ),
            ),
            401: openapi.Response(description="Missing or invalid access token"),
        },
    )
    def get(self, request):
        account = getattr(request, "user", None)
        if not account:
            return Response(
                {"detail": "Authentication required."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        wallet = Wallet.objects.filter(account=account, is_active=True).first()
        transactions = []
        if wallet:
            transactions = list(
                wallet.transactions.filter(is_active=True).order_by("-created_at")
            )
            transactions = [_transaction_to_dict(t) for t in transactions]

        payload = {
            "account": _account_to_dict(account),
            "wallet": _wallet_to_dict(wallet) if wallet else None,
            "transactions": transactions,
        }
        return Response(payload)
