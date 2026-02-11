import uuid
from decimal import Decimal

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from account.models import Account
from .models import Transaction, Wallet


def _get_account_from_request(request):
    """Get Account from request only if JWT auth set it (not AnonymousUser)."""
    user = getattr(request, "user", None)
    return user if isinstance(user, Account) else None


# OpenAPI request body schemas — account/wallet from token, not body
_WALLET_BODY_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["address"],
    properties={
        "address": openapi.Schema(type=openapi.TYPE_STRING, description="Wallet address (unique)"),
        "wallet_type": openapi.Schema(type=openapi.TYPE_STRING, description="e.g. metamask, trust"),
        "balance": openapi.Schema(type=openapi.TYPE_NUMBER, description="Initial balance", default=0),
    },
    description="Account is taken from your access token; do not send account_id.",
)
_TRANSACTION_BODY_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["transaction_id", "amount", "final_amount", "transaction_type"],
    properties={
        "transaction_id": openapi.Schema(type=openapi.TYPE_STRING, description="Unique transaction id"),
        "amount": openapi.Schema(type=openapi.TYPE_NUMBER),
        "fee": openapi.Schema(type=openapi.TYPE_NUMBER, default=0),
        "final_amount": openapi.Schema(type=openapi.TYPE_NUMBER),
        "transaction_type": openapi.Schema(type=openapi.TYPE_STRING, description="e.g. credit, debit, transfer"),
        "status": openapi.Schema(type=openapi.TYPE_STRING, description="e.g. pending, completed, failed", default="pending"),
        "description": openapi.Schema(type=openapi.TYPE_STRING),
        "metadata": openapi.Schema(type=openapi.TYPE_OBJECT, description="Optional JSON object"),
        "sender_name": openapi.Schema(type=openapi.TYPE_STRING, description="Sender name (plain text)"),
        "receiver_name": openapi.Schema(type=openapi.TYPE_STRING, description="Receiver name (plain text)"),
        "sender_email": openapi.Schema(type=openapi.TYPE_STRING, description="Sender email (plain text, not linked)"),
        "receiver_email": openapi.Schema(type=openapi.TYPE_STRING, description="Receiver email (plain text, not linked)"),
        "sender_type": openapi.Schema(type=openapi.TYPE_STRING, description="Sender type: send, receive, etc."),
        "wallet_address": openapi.Schema(type=openapi.TYPE_STRING, description="Wallet address (required for external users, optional if authenticated)"),
    },
    description="If authenticated, wallet is taken from your token. For external users, provide wallet_address.",
)

# No-auth API: save transaction by username; username = receiver (always)
# User sends their username, and that username becomes the receiver
_TRANSACTION_BY_USERNAME_BODY_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["username", "amount"],
    properties={
        "username": openapi.Schema(type=openapi.TYPE_STRING, description="Receiver's username (THIS USER WILL BE THE RECEIVER - wallet, receiver_name, receiver_email auto-filled from this user)"),
        "amount": openapi.Schema(type=openapi.TYPE_NUMBER, description="Transaction amount"),
        "fee": openapi.Schema(type=openapi.TYPE_NUMBER, default=0),
        "final_amount": openapi.Schema(type=openapi.TYPE_NUMBER, description="Optional; defaults to amount - fee"),
        "transaction_type": openapi.Schema(type=openapi.TYPE_STRING, description="e.g. credit, debit, transfer", default="credit"),
        "status": openapi.Schema(type=openapi.TYPE_STRING, default="pending"),
        "description": openapi.Schema(type=openapi.TYPE_STRING),
        "metadata": openapi.Schema(type=openapi.TYPE_OBJECT),
        "sender_name": openapi.Schema(type=openapi.TYPE_STRING, description="Sender's name"),
        "sender_email": openapi.Schema(type=openapi.TYPE_STRING, description="Sender's email"),
        "sender_type": openapi.Schema(type=openapi.TYPE_STRING, description="e.g. send, receive"),
        "transaction_id": openapi.Schema(type=openapi.TYPE_STRING, description="Optional; auto-generated if not sent"),
    },
    description="NO AUTH TOKEN REQUIRED. Username sent = RECEIVER (always). Wallet, receiver_name (username), receiver_email auto-filled from that user's account.",
)


def _wallet_to_dict(wallet):
    """Build response dict from Wallet. No serializer."""
    return {
        "id": wallet.id,
        "account": wallet.account_id,
        "account_email": wallet.account.email,
        "address": wallet.address,
        "wallet_type": wallet.wallet_type or "",
        "balance": str(wallet.balance),
        "created_at": wallet.created_at,
        "updated_at": wallet.updated_at,
    }


def _transaction_to_dict(txn):
    """Build response dict from Transaction. No serializer."""
    return {
        "id": txn.id,
        "transaction_id": txn.transaction_id,
        "wallet": txn.wallet_id,
        "amount": str(txn.amount),
        "fee": str(txn.fee),
        "final_amount": str(txn.final_amount),
        "transaction_type": txn.transaction_type,
        "status": txn.status,
        "description": txn.description or "",
        "metadata": txn.metadata or {},
        "sender_name": txn.sender_name or "",
        "receiver_name": txn.receiver_name or "",
        "sender_email": txn.sender_email or "",
        "receiver_email": txn.receiver_email or "",
        "sender_type": txn.sender_type or "",
        "created_at": txn.created_at,
        "updated_at": txn.updated_at,
    }


def _validate_wallet_create(data):
    """Validate wallet POST. Account comes from token, not body."""
    errors = {}
    address = (data.get("address") or "").strip()
    if not address:
        errors["address"] = ["This field is required."]
    if address and Wallet.objects.filter(address=address).exists():
        errors["address"] = ["Wallet with this address already exists."]
    if errors:
        return False, errors
    return True, data


def _validate_transaction_create(data):
    """Validate transaction POST data. Checks required fields and duplicate transaction_id."""
    errors = {}
    if not (data.get("transaction_id") or "").strip():
        errors["transaction_id"] = ["This field is required."]
    if data.get("amount") is None:
        errors["amount"] = ["This field is required."]
    if data.get("final_amount") is None:
        errors["final_amount"] = ["This field is required."]
    if not (data.get("transaction_type") or "").strip():
        errors["transaction_type"] = ["This field is required."]
    if errors:
        return False, errors
    tid = (data.get("transaction_id") or "").strip()
    if Transaction.objects.filter(transaction_id=tid).exists():
        errors["transaction_id"] = ["Transaction with this id already exists."]
        return False, errors
    return True, data


def _validate_transaction_by_username(data):
    """Validate save-transaction-by-username payload. Required: username, amount."""
    errors = {}
    if not (data.get("username") or "").strip():
        errors["username"] = ["This field is required."]
    if data.get("amount") is None:
        errors["amount"] = ["This field is required."]
    try:
        amount = Decimal(str(data["amount"]))
        if amount < 0:
            errors["amount"] = ["Amount must be non-negative."]
    except Exception:
        errors["amount"] = ["Enter a valid number."]
    if errors:
        return False, errors
    tid = (data.get("transaction_id") or "").strip()
    if tid and Transaction.objects.filter(transaction_id=tid).exists():
        errors["transaction_id"] = ["Transaction with this id already exists."]
        return False, errors
    return True, data


class WalletListCreateAPIView(APIView):
    """
    GET: List wallets. POST: Create wallet. All logic in view.
    """

    @swagger_auto_schema(tags=["Wallet"], operation_summary="List wallets (current user only)")
    def get(self, request):
        account = _get_account_from_request(request)
        if not account:
            return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)
        wallets = (
            Wallet.objects.filter(account=account, is_active=True)
            .select_related("account")
            .order_by("-created_at")
        )
        payload = [_wallet_to_dict(w) for w in wallets]
        return Response(payload)

    @swagger_auto_schema(
        tags=["Wallet"],
        operation_summary="Create wallet (Bearer token required)",
        operation_description="Requires **Authorization: Bearer &lt;access_token&gt;**. Account is taken from your token automatically; send only address, wallet_type, balance.",
        security=[{"Bearer": []}],
        request_body=_WALLET_BODY_SCHEMA,
        responses={
            201: openapi.Response(description="Wallet created"),
            401: openapi.Response(description="Missing or invalid access token"),
        },
    )
    def post(self, request):
        account = _get_account_from_request(request)
        if not account:
            return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)
        data = request.data
        is_valid, result = _validate_wallet_create(data)
        if not is_valid:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        data = result
        wallet = Wallet.objects.create(
            account=account,
            address=(data.get("address") or "").strip().replace(" ", ""),
            wallet_type=(data.get("wallet_type") or "").strip() or "",
            balance=Decimal(str(data.get("balance", 0))),
        )
        return Response(_wallet_to_dict(wallet), status=status.HTTP_201_CREATED)


class WalletDetailAPIView(APIView):
    """
    GET / PUT / PATCH / DELETE wallet. Only own wallet (token) allowed.
    """

    def get_object(self, request, pk):
        account = _get_account_from_request(request)
        if not account:
            return None
        try:
            return Wallet.objects.select_related("account").get(pk=pk, account=account, is_active=True)
        except Wallet.DoesNotExist:
            return None

    @swagger_auto_schema(tags=["Wallet"], operation_summary="Get wallet by ID (own only)")
    def get(self, request, pk):
        wallet = self.get_object(request, pk)
        if wallet is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(_wallet_to_dict(wallet))

    @swagger_auto_schema(
        tags=["Wallet"],
        operation_summary="Update wallet (full)",
        request_body=_WALLET_BODY_SCHEMA,
        responses={200: openapi.Response(description="Wallet updated")},
    )
    def put(self, request, pk):
        wallet = self.get_object(request, pk)
        if wallet is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        data = request.data
        addr = (data.get("address") or wallet.address or "").strip()
        if addr != wallet.address and Wallet.objects.filter(address=addr).exists():
            return Response(
                {"address": ["Wallet with this address already exists."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        wallet.address = addr
        wallet.wallet_type = (data.get("wallet_type") if "wallet_type" in data else wallet.wallet_type) or ""
        if "balance" in data:
            wallet.balance = Decimal(str(data["balance"]))
        wallet.save()
        return Response(_wallet_to_dict(wallet))

    @swagger_auto_schema(
        tags=["Wallet"],
        operation_summary="Update wallet (partial)",
        request_body=_WALLET_BODY_SCHEMA,
        responses={200: openapi.Response(description="Wallet updated")},
    )
    def patch(self, request, pk):
        wallet = self.get_object(request, pk)
        if wallet is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        data = request.data
        if "address" in data and data["address"] is not None:
            addr = str(data["address"]).strip()
            if addr != wallet.address and Wallet.objects.filter(address=addr).exists():
                return Response(
                    {"address": ["Wallet with this address already exists."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            wallet.address = addr
        if "wallet_type" in data:
            wallet.wallet_type = (data["wallet_type"] or "").strip() or ""
        if "balance" in data:
            wallet.balance = Decimal(str(data["balance"]))
        wallet.save()
        return Response(_wallet_to_dict(wallet))

    def delete(self, request, pk):
        wallet = self.get_object(request, pk)
        if wallet is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        wallet.is_active = False
        wallet.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class TransactionListCreateAPIView(APIView):
    """
    GET: List transactions. POST: Create transaction. Logic in view.
    """

    @swagger_auto_schema(tags=["Transaction"], operation_summary="List transactions (current user only)")
    def get(self, request):
        account = _get_account_from_request(request)
        if not account:
            return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)
        transactions = (
            Transaction.objects.filter(wallet__account=account, is_active=True)
            .select_related("wallet", "wallet__account")
            .order_by("-created_at")
        )
        payload = [_transaction_to_dict(t) for t in transactions]
        return Response(payload)

    @swagger_auto_schema(
        tags=["Transaction"],
        operation_summary="Create transaction",
        operation_description="If authenticated, wallet is taken from your token. For external users, provide wallet_address in request body.",
        request_body=_TRANSACTION_BODY_SCHEMA,
        responses={
            201: openapi.Response(description="Transaction created"),
            400: openapi.Response(description="Validation error or duplicate transaction"),
            404: openapi.Response(description="Wallet not found"),
        },
    )
    def post(self, request):
        account = _get_account_from_request(request)
        data = request.data
        
        # Get wallet - either from authenticated account or from wallet_address
        wallet = None
        if account:
            # Authenticated user - get wallet from account
            wallet = Wallet.objects.filter(account=account, is_active=True).first()
            if not wallet:
                return Response(
                    {"detail": "Create a wallet first. You have no wallet linked to your account."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            # External user - get wallet by address
            wallet_address = (data.get("wallet_address") or "").strip()
            if not wallet_address:
                return Response(
                    {"detail": "wallet_address is required for external users."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            wallet = Wallet.objects.filter(address=wallet_address, is_active=True).first()
            if not wallet:
                return Response(
                    {"detail": "Wallet not found with the provided address."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        
        # Validate transaction data
        is_valid, result = _validate_transaction_create(data)
        if not is_valid:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        data = result
        
        # Check for duplicate transaction_id before creating
        transaction_id = (data.get("transaction_id") or "").strip()
        if Transaction.objects.filter(transaction_id=transaction_id).exists():
            existing_txn = Transaction.objects.get(transaction_id=transaction_id)
            return Response(
                {"detail": "Transaction with this ID already exists.", "transaction": _transaction_to_dict(existing_txn)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Create transaction
        amount = Decimal(str(data["amount"]))
        fee = Decimal(str(data.get("fee", 0)))
        final_amount = Decimal(str(data["final_amount"]))
        txn = Transaction.objects.create(
            transaction_id=transaction_id,
            wallet=wallet,
            amount=amount,
            fee=fee,
            final_amount=final_amount,
            transaction_type=(data.get("transaction_type") or "").strip(),
            status=(data.get("status") or "pending").strip() or "pending",
            description=(data.get("description") or "").strip() or "",
            metadata=dict(data.get("metadata") or {}),
            sender_name=(data.get("sender_name") or "").strip(),
            receiver_name=(data.get("receiver_name") or "").strip(),
            sender_email=(data.get("sender_email") or "").strip(),
            receiver_email=(data.get("receiver_email") or "").strip(),
            sender_type=(data.get("sender_type") or "").strip(),
        )
        return Response(_transaction_to_dict(txn), status=status.HTTP_201_CREATED)


# class TransactionDetailAPIView(APIView):
#     """
#     GET / PUT / PATCH / DELETE transaction. Only own transactions (token) allowed.
#     """

#     def get_object(self, request, pk):
#         account = _get_account_from_request(request)
#         if not account:
#             return None
#         try:
#             return (
#                 Transaction.objects.filter(wallet__account=account, is_active=True)
#                 .select_related("wallet", "wallet__account")
#                 .get(pk=pk)
#             )
#         except Transaction.DoesNotExist:
#             return None

#     @swagger_auto_schema(tags=["Transaction"], operation_summary="Get transaction by ID (own only)")
#     def get(self, request, pk):
#         transaction = self.get_object(request, pk)
#         if transaction is None:
#             return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
#         return Response(_transaction_to_dict(transaction))

#     @swagger_auto_schema(
#         tags=["Transaction"],
#         operation_summary="Update transaction (full)",
#         request_body=_TRANSACTION_BODY_SCHEMA,
#         responses={200: openapi.Response(description="Transaction updated")},
#     )
#     def put(self, request, pk):
#         transaction = self.get_object(request, pk)
#         if transaction is None:
#             return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
#         data = request.data
#         transaction.amount = Decimal(str(data.get("amount", transaction.amount)))
#         transaction.fee = Decimal(str(data.get("fee", transaction.fee)))
#         transaction.final_amount = Decimal(str(data.get("final_amount", transaction.final_amount)))
#         transaction.transaction_type = (data.get("transaction_type") or transaction.transaction_type or "").strip()
#         transaction.status = (data.get("status") or transaction.status or "pending").strip() or "pending"
#         transaction.description = (data.get("description") if "description" in data else transaction.description) or ""
#         transaction.metadata = dict(data.get("metadata", transaction.metadata or {}))
#         transaction.save()
#         return Response(_transaction_to_dict(transaction))

#     @swagger_auto_schema(
#         tags=["Transaction"],
#         operation_summary="Update transaction (partial)",
#         request_body=_TRANSACTION_BODY_SCHEMA,
#         responses={200: openapi.Response(description="Transaction updated")},
#     )
#     def patch(self, request, pk):
#         transaction = self.get_object(request, pk)
#         if transaction is None:
#             return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
#         data = request.data
#         if "amount" in data:
#             transaction.amount = Decimal(str(data["amount"]))
#         if "fee" in data:
#             transaction.fee = Decimal(str(data["fee"]))
#         if "final_amount" in data:
#             transaction.final_amount = Decimal(str(data["final_amount"]))
#         if "transaction_type" in data and data["transaction_type"] is not None:
#             transaction.transaction_type = str(data["transaction_type"]).strip()
#         if "status" in data and data["status"] is not None:
#             transaction.status = str(data["status"]).strip() or "pending"
#         if "description" in data:
#             transaction.description = (data["description"] or "").strip() or ""
#         if "metadata" in data:
#             transaction.metadata = dict(data["metadata"] or {})
#         transaction.save()
#         return Response(_transaction_to_dict(transaction))

#     def delete(self, request, pk):
#         transaction = self.get_object(request, pk)
#         if transaction is None:
#             return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
#         transaction.is_active = False
#         transaction.save(update_fields=["is_active"])
#         return Response(status=status.HTTP_204_NO_CONTENT)




class TransactionDetailAPIView(APIView):
    """
    GET / PUT / PATCH / DELETE transaction.
    Only own account transactions allowed.
    """

    def get_object(self, request, pk):
        account = _get_account_from_request(request)
        if not account:
            return None

        try:
            return (
                Transaction.objects
                .select_related("wallet", "wallet__account")
                .get(
                    pk=pk,
                    wallet__account=account,
                    is_active=True
                )
            )
        except Transaction.DoesNotExist:
            return None

    # ===================== GET =====================

    @swagger_auto_schema(
        tags=["Transaction"],
        operation_summary="Get transaction by ID (own only)",
        responses={200: openapi.Response(description="Transaction detail")}
    )
    def get(self, request, pk):
        transaction = self.get_object(request, pk)
        if not transaction:
            return Response(
                {"detail": "Transaction not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(_transaction_to_dict(transaction))

    # ===================== PUT =====================

    @swagger_auto_schema(
        tags=["Transaction"],
        operation_summary="Update transaction (full update)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "amount": openapi.Schema(type=openapi.TYPE_STRING),
                "fee": openapi.Schema(type=openapi.TYPE_STRING),
                "final_amount": openapi.Schema(type=openapi.TYPE_STRING),
                "transaction_type": openapi.Schema(type=openapi.TYPE_STRING),
                "status": openapi.Schema(type=openapi.TYPE_STRING),
                "description": openapi.Schema(type=openapi.TYPE_STRING),
                "metadata": openapi.Schema(type=openapi.TYPE_OBJECT),
                "sender_name": openapi.Schema(type=openapi.TYPE_STRING),
                "receiver_name": openapi.Schema(type=openapi.TYPE_STRING),
                "sender_email": openapi.Schema(type=openapi.TYPE_STRING),
                "receiver_email": openapi.Schema(type=openapi.TYPE_STRING),
                "sender_type": openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=["amount", "final_amount"]
        ),
    )
    def put(self, request, pk):
        transaction = self.get_object(request, pk)
        if not transaction:
            return Response(
                {"detail": "Transaction not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        data = request.data

        transaction.amount = Decimal(str(data.get("amount", transaction.amount)))
        transaction.fee = Decimal(str(data.get("fee", transaction.fee)))
        transaction.final_amount = Decimal(str(data.get("final_amount", transaction.final_amount)))
        transaction.transaction_type = str(
            data.get("transaction_type", transaction.transaction_type)
        ).strip()
        transaction.status = str(
            data.get("status", transaction.status)
        ).strip() or "pending"
        transaction.description = data.get("description", transaction.description) or ""
        transaction.metadata = data.get("metadata", transaction.metadata or {})
        transaction.sender_name = (data.get("sender_name", transaction.sender_name) or "").strip()
        transaction.receiver_name = (data.get("receiver_name", transaction.receiver_name) or "").strip()
        transaction.sender_email = (data.get("sender_email", transaction.sender_email) or "").strip()
        transaction.receiver_email = (data.get("receiver_email", transaction.receiver_email) or "").strip()
        transaction.sender_type = (data.get("sender_type", transaction.sender_type) or "").strip()

        transaction.save()

        return Response(_transaction_to_dict(transaction))

    # ===================== PATCH =====================

    @swagger_auto_schema(
        tags=["Transaction"],
        operation_summary="Update transaction (partial update)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "amount": openapi.Schema(type=openapi.TYPE_STRING),
                "fee": openapi.Schema(type=openapi.TYPE_STRING),
                "final_amount": openapi.Schema(type=openapi.TYPE_STRING),
                "transaction_type": openapi.Schema(type=openapi.TYPE_STRING),
                "status": openapi.Schema(type=openapi.TYPE_STRING),
                "description": openapi.Schema(type=openapi.TYPE_STRING),
                "metadata": openapi.Schema(type=openapi.TYPE_OBJECT),
                "sender_name": openapi.Schema(type=openapi.TYPE_STRING),
                "receiver_name": openapi.Schema(type=openapi.TYPE_STRING),
                "sender_email": openapi.Schema(type=openapi.TYPE_STRING),
                "receiver_email": openapi.Schema(type=openapi.TYPE_STRING),
                "sender_type": openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
    )
    def patch(self, request, pk):
        transaction = self.get_object(request, pk)
        if not transaction:
            return Response(
                {"detail": "Transaction not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        data = request.data

        if "amount" in data:
            transaction.amount = Decimal(str(data["amount"]))

        if "fee" in data:
            transaction.fee = Decimal(str(data["fee"]))

        if "final_amount" in data:
            transaction.final_amount = Decimal(str(data["final_amount"]))

        if "transaction_type" in data:
            transaction.transaction_type = str(data["transaction_type"]).strip()

        if "status" in data:
            transaction.status = str(data["status"]).strip() or "pending"

        if "description" in data:
            transaction.description = data["description"] or ""

        if "metadata" in data:
            transaction.metadata = data["metadata"] or {}

        if "sender_name" in data:
            transaction.sender_name = (data["sender_name"] or "").strip()

        if "receiver_name" in data:
            transaction.receiver_name = (data["receiver_name"] or "").strip()

        if "sender_email" in data:
            transaction.sender_email = (data["sender_email"] or "").strip()

        if "receiver_email" in data:
            transaction.receiver_email = (data["receiver_email"] or "").strip()

        if "sender_type" in data:
            transaction.sender_type = (data["sender_type"] or "").strip()

        transaction.save()

        return Response(_transaction_to_dict(transaction))

    # ===================== DELETE =====================

    @swagger_auto_schema(
        tags=["Transaction"],
        operation_summary="Delete transaction (soft delete)"
    )
    def delete(self, request, pk):
        transaction = self.get_object(request, pk)
        if not transaction:
            return Response(
                {"detail": "Transaction not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        transaction.is_active = False
        transaction.save(update_fields=["is_active"])

        return Response(
            {"detail": "Transaction deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )
        
        
        
class WalletMyListAPIViewV1(APIView):
    """
    GET /api/v1/wallets/
    """

    def get(self, request):
        account = _get_account_from_request(request)
        if not account:
            return Response(
                {"detail": "Authentication required."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        wallets = Wallet.objects.filter(
            account=account,
            is_active=True
        ).order_by("-created_at")

        return Response([_wallet_to_dict(w) for w in wallets])



class WalletMyDetailAPIViewV1(APIView):
    """
    GET /api/v1/wallets/<wallet_id>/
    """

    def get(self, request, wallet_id):
        account = _get_account_from_request(request)
        if not account:
            return Response(
                {"detail": "Authentication required."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            wallet = Wallet.objects.get(
                id=wallet_id,
                account=account,
                is_active=True
            )
        except Wallet.DoesNotExist:
            return Response(
                {"detail": "Wallet not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(_wallet_to_dict(wallet))


class WalletAddressByUsernameAPIView(APIView):
    """
    GET: Get wallet address by username.
    Query parameter: ?username=<username>
    """

    @swagger_auto_schema(
        tags=["Wallet"],
        operation_summary="Get wallet address by username",
        manual_parameters=[
            openapi.Parameter(
                'username',
                openapi.IN_QUERY,
                description="Username to get wallet address for",
                type=openapi.TYPE_STRING,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description="Wallet address found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'username': openapi.Schema(type=openapi.TYPE_STRING),
                        'wallet_address': openapi.Schema(type=openapi.TYPE_STRING),
                        'wallet_type': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            404: openapi.Response(description="User or wallet not found"),
        },
    )
    def get(self, request):
        username = request.query_params.get('username', '').strip()
        
        if not username:
            return Response(
                {"detail": "Username parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            account = Account.objects.get(username=username, is_active=True)
        except Account.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            wallet = Wallet.objects.get(account=account, is_active=True)
        except Wallet.DoesNotExist:
            return Response(
                {"detail": "Wallet not found for this user."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response({
            "username": account.username,
            "wallet_address": wallet.address,
            "wallet_type": wallet.wallet_type or "",
            "balance": str(wallet.balance),
        })


class TransactionCreateByUsernameAPIView(APIView):
    """
    POST: Save transaction by username. NO AUTH TOKEN REQUIRED.
    Username sent = RECEIVER (always).
    Wallet, receiver_name (username), receiver_email auto-filled from that user's account.
    """

    @swagger_auto_schema(
        tags=["Transaction"],
        operation_summary="Create transaction by username (no auth - username = receiver)",
        operation_description="NO AUTH TOKEN REQUIRED. Send username (this user will be the RECEIVER) + amount + sender details. Wallet, receiver_name (username), receiver_email are auto-filled from that user's account.",
        request_body=_TRANSACTION_BY_USERNAME_BODY_SCHEMA,
        responses={
            201: openapi.Response(description="Transaction created"),
            400: openapi.Response(description="Validation error"),
            404: openapi.Response(description="User or wallet not found"),
        },
    )
    def post(self, request):
        data = request.data
        is_valid, result = _validate_transaction_by_username(data)
        if not is_valid:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        data = result

        username = (data.get("username") or "").strip()
        try:
            account = Account.objects.get(username=username, is_active=True)
        except Account.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            wallet = Wallet.objects.get(account=account, is_active=True)
        except Wallet.DoesNotExist:
            return Response(
                {"detail": "Wallet not found for this user."},
                status=status.HTTP_404_NOT_FOUND,
            )

        amount = Decimal(str(data["amount"]))
        fee = Decimal(str(data.get("fee", 0)))
        final_amount = data.get("final_amount")
        if final_amount is None:
            final_amount = amount - fee
        else:
            final_amount = Decimal(str(final_amount))

        transaction_id = (data.get("transaction_id") or "").strip()
        if not transaction_id:
            transaction_id = f"txn-{uuid.uuid4().hex[:16]}"

        if Transaction.objects.filter(transaction_id=transaction_id).exists():
            return Response(
                {"transaction_id": ["Transaction with this id already exists."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Username sent = RECEIVER (always)
        # Fill receiver details from the account
        receiver_name = account.username  # Receiver name = username
        receiver_email = account.email or ""  # Receiver email = account email

        txn = Transaction.objects.create(
            transaction_id=transaction_id,
            wallet=wallet,
            amount=amount,
            fee=fee,
            final_amount=final_amount,
            transaction_type=(data.get("transaction_type") or "credit").strip() or "credit",
            status=(data.get("status") or "pending").strip() or "pending",
            description=(data.get("description") or "").strip() or "",
            metadata=dict(data.get("metadata") or {}),
            sender_name=(data.get("sender_name") or "").strip(),
            receiver_name=receiver_name,
            sender_email=(data.get("sender_email") or "").strip(),
            receiver_email=receiver_email,
            sender_type=(data.get("sender_type") or "").strip(),
        )
        return Response(_transaction_to_dict(txn), status=status.HTTP_201_CREATED)
