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
    },
    description="Wallet is taken from your access token (your account's wallet); do not send wallet_id.",
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
    """Validate transaction POST. Wallet comes from token (account's wallet), not body."""
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


# class WalletDetailAPIView(APIView):
#     """
#     GET / PUT / PATCH / DELETE wallet. Only own wallet (token) allowed.
#     """

#     def get_object(self, request, pk):
#         account = _get_account_from_request(request)
#         if not account:
#             return None
#         try:
#             return Wallet.objects.select_related("account").get(pk=pk, account=account, is_active=True)
#         except Wallet.DoesNotExist:
#             return None

#     @swagger_auto_schema(tags=["Wallet"], operation_summary="Get wallet by ID (own only)")
#     def get(self, request, pk):
#         wallet = self.get_object(request, pk)
#         if wallet is None:
#             return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
#         return Response(_wallet_to_dict(wallet))

#     @swagger_auto_schema(
#         tags=["Wallet"],
#         operation_summary="Update wallet (full)",
#         request_body=_WALLET_BODY_SCHEMA,
#         responses={200: openapi.Response(description="Wallet updated")},
#     )
#     def put(self, request, pk):
#         wallet = self.get_object(request, pk)
#         if wallet is None:
#             return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
#         data = request.data
#         addr = (data.get("address") or wallet.address or "").strip()
#         if addr != wallet.address and Wallet.objects.filter(address=addr).exists():
#             return Response(
#                 {"address": ["Wallet with this address already exists."]},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )
#         wallet.address = addr
#         wallet.wallet_type = (data.get("wallet_type") if "wallet_type" in data else wallet.wallet_type) or ""
#         if "balance" in data:
#             wallet.balance = Decimal(str(data["balance"]))
#         wallet.save()
#         return Response(_wallet_to_dict(wallet))

#     @swagger_auto_schema(
#         tags=["Wallet"],
#         operation_summary="Update wallet (partial)",
#         request_body=_WALLET_BODY_SCHEMA,
#         responses={200: openapi.Response(description="Wallet updated")},
#     )
#     def patch(self, request, pk):
#         wallet = self.get_object(request, pk)
#         if wallet is None:
#             return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
#         data = request.data
#         if "address" in data and data["address"] is not None:
#             addr = str(data["address"]).strip()
#             if addr != wallet.address and Wallet.objects.filter(address=addr).exists():
#                 return Response(
#                     {"address": ["Wallet with this address already exists."]},
#                     status=status.HTTP_400_BAD_REQUEST,
#                 )
#             wallet.address = addr
#         if "wallet_type" in data:
#             wallet.wallet_type = (data["wallet_type"] or "").strip() or ""
#         if "balance" in data:
#             wallet.balance = Decimal(str(data["balance"]))
#         wallet.save()
#         return Response(_wallet_to_dict(wallet))

#     def delete(self, request, pk):
#         wallet = self.get_object(request, pk)
#         if wallet is None:
#             return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
#         wallet.is_active = False
#         wallet.save(update_fields=["is_active"])
#         return Response(status=status.HTTP_204_NO_CONTENT)



class WalletDetailAPIView(APIView):
    """
    GET / PUT / PATCH / DELETE wallet.
    Only own wallet (token-based account) allowed.
    """
    def get_object(self, request, pk):
        account = _get_account_from_request(request)
        print("TOKEN ACCOUNT ID:", account.id if account else None)

        try:
            wallet = Wallet.objects.get(
                pk=pk,
                account=account,
                is_active=True
            )
            print("WALLET ACCOUNT ID:", wallet.account.id)
            return wallet
        except Wallet.DoesNotExist:
            print("WALLET NOT FOUND FOR THIS ACCOUNT")
            return None


    # ===================== GET =====================

    @swagger_auto_schema(
        tags=["Wallet"],
        operation_summary="Get wallet by ID (own only)",
    )
    def get(self, request, pk):
        wallet = self.get_object(request, pk)
        if not wallet:
            return Response(
                {"detail": "Wallet not found or access denied."},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(_wallet_to_dict(wallet))

    # ===================== PUT =====================

    @swagger_auto_schema(
        tags=["Wallet"],
        operation_summary="Update wallet (full)",
        request_body=_WALLET_BODY_SCHEMA,
    )
    def put(self, request, pk):
        wallet = self.get_object(request, pk)
        if not wallet:
            return Response(
                {"detail": "Wallet not found or access denied."},
                status=status.HTTP_404_NOT_FOUND
            )

        data = request.data

        # Address update (unique check)
        addr = (data.get("address") or "").strip()
        if addr and addr != wallet.address:
            if Wallet.objects.filter(address=addr).exclude(pk=wallet.pk).exists():
                return Response(
                    {"address": ["Wallet with this address already exists."]},
                    status=status.HTTP_400_BAD_REQUEST
                )
            wallet.address = addr

        # Wallet type
        wallet.wallet_type = (data.get("wallet_type") or "").strip()

        # ❌ balance update intentionally NOT allowed

        wallet.save()
        return Response(_wallet_to_dict(wallet))

    # ===================== PATCH =====================

    @swagger_auto_schema(
        tags=["Wallet"],
        operation_summary="Update wallet (partial)",
        request_body=_WALLET_BODY_SCHEMA,
    )
    def patch(self, request, pk):
        wallet = self.get_object(request, pk)
        if not wallet:
            return Response(
                {"detail": "Wallet not found or access denied."},
                status=status.HTTP_404_NOT_FOUND
            )

        data = request.data

        if "address" in data and data["address"] is not None:
            addr = str(data["address"]).strip()
            if addr != wallet.address:
                if Wallet.objects.filter(address=addr).exclude(pk=wallet.pk).exists():
                    return Response(
                        {"address": ["Wallet with this address already exists."]},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                wallet.address = addr

        if "wallet_type" in data:
            wallet.wallet_type = (data["wallet_type"] or "").strip()

        # ❌ balance update intentionally NOT allowed

        wallet.save()
        return Response(_wallet_to_dict(wallet))

    # ===================== DELETE =====================

    @swagger_auto_schema(
        tags=["Wallet"],
        operation_summary="Delete wallet (soft delete)",
    )
    def delete(self, request, pk):
        wallet = self.get_object(request, pk)
        if not wallet:
            return Response(
                {"detail": "Wallet not found or access denied."},
                status=status.HTTP_404_NOT_FOUND
            )

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
        operation_summary="Create transaction (Bearer token required)",
        operation_description="Requires **Authorization: Bearer &lt;access_token&gt;**. Wallet is taken from your token (your account's wallet) automatically; do not send wallet_id.",
        security=[{"Bearer": []}],
        request_body=_TRANSACTION_BODY_SCHEMA,
        responses={
            201: openapi.Response(description="Transaction created"),
            401: openapi.Response(description="Missing or invalid access token"),
            400: openapi.Response(description="Create a wallet first if you have none"),
        },
    )
    def post(self, request):
        account = _get_account_from_request(request)
        if not account:
            return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)
        wallet = Wallet.objects.filter(account=account, is_active=True).first()
        if not wallet:
            return Response(
                {"detail": "Create a wallet first. You have no wallet linked to your account."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = request.data
        is_valid, result = _validate_transaction_create(data)
        if not is_valid:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        data = result
        amount = Decimal(str(data["amount"]))
        fee = Decimal(str(data.get("fee", 0)))
        final_amount = Decimal(str(data["final_amount"]))
        txn = Transaction.objects.create(
            transaction_id=(data.get("transaction_id") or "").strip(),
            wallet=wallet,
            amount=amount,
            fee=fee,
            final_amount=final_amount,
            transaction_type=(data.get("transaction_type") or "").strip(),
            status=(data.get("status") or "pending").strip() or "pending",
            description=(data.get("description") or "").strip() or "",
            metadata=dict(data.get("metadata") or {}),
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