from decimal import Decimal

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from account.models import Account
from .models import Transaction, Wallet


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
    """Validate wallet POST in view."""
    errors = {}
    account_id = data.get("account")
    address = (data.get("address") or "").strip()
    if not account_id:
        errors["account"] = ["This field is required."]
    else:
        if not Account.objects.filter(pk=account_id, is_active=True).exists():
            errors["account"] = ["Valid account id required."]
    if not address:
        errors["address"] = ["This field is required."]
    if address and Wallet.objects.filter(address=address).exists():
        errors["address"] = ["Wallet with this address already exists."]
    if errors:
        return False, errors
    return True, data


def _validate_transaction_create(data):
    """Validate transaction POST in view."""
    errors = {}
    if not (data.get("transaction_id") or "").strip():
        errors["transaction_id"] = ["This field is required."]
    if data.get("wallet") is None:
        errors["wallet"] = ["This field is required."]
    else:
        if not Wallet.objects.filter(pk=data["wallet"], is_active=True).exists():
            errors["wallet"] = ["Valid wallet id required."]
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

    def get(self, request):
        wallets = (
            Wallet.objects.filter(is_active=True)
            .select_related("account")
            .order_by("-created_at")
        )
        payload = [_wallet_to_dict(w) for w in wallets]
        return Response(payload)

    def post(self, request):
        data = request.data
        is_valid, result = _validate_wallet_create(data)
        if not is_valid:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        data = result
        account = Account.objects.get(pk=data["account"])
        wallet = Wallet.objects.create(
            account=account,
            address=(data.get("address") or "").strip(),
            wallet_type=(data.get("wallet_type") or "").strip() or "",
            balance=Decimal(str(data.get("balance", 0))),
        )
        return Response(_wallet_to_dict(wallet), status=status.HTTP_201_CREATED)


class WalletDetailAPIView(APIView):
    """
    GET / PUT / PATCH / DELETE wallet. Logic in view.
    """

    def get_object(self, pk):
        try:
            return Wallet.objects.select_related("account").get(pk=pk, is_active=True)
        except Wallet.DoesNotExist:
            return None

    def get(self, request, pk):
        wallet = self.get_object(pk)
        if wallet is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(_wallet_to_dict(wallet))

    def put(self, request, pk):
        wallet = self.get_object(pk)
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

    def patch(self, request, pk):
        wallet = self.get_object(pk)
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
        wallet = self.get_object(pk)
        if wallet is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        wallet.is_active = False
        wallet.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class TransactionListCreateAPIView(APIView):
    """
    GET: List transactions. POST: Create transaction. Logic in view.
    """

    def get(self, request):
        transactions = (
            Transaction.objects.filter(is_active=True)
            .select_related("wallet", "wallet__account")
            .order_by("-created_at")
        )
        payload = [_transaction_to_dict(t) for t in transactions]
        return Response(payload)

    def post(self, request):
        data = request.data
        is_valid, result = _validate_transaction_create(data)
        if not is_valid:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        data = result
        wallet = Wallet.objects.get(pk=data["wallet"])
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


class TransactionDetailAPIView(APIView):
    """
    GET / PUT / PATCH / DELETE transaction. Logic in view.
    """

    def get_object(self, pk):
        try:
            return (
                Transaction.objects.filter(is_active=True)
                .select_related("wallet", "wallet__account")
                .get(pk=pk)
            )
        except Transaction.DoesNotExist:
            return None

    def get(self, request, pk):
        transaction = self.get_object(pk)
        if transaction is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(_transaction_to_dict(transaction))

    def put(self, request, pk):
        transaction = self.get_object(pk)
        if transaction is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        data = request.data
        transaction.amount = Decimal(str(data.get("amount", transaction.amount)))
        transaction.fee = Decimal(str(data.get("fee", transaction.fee)))
        transaction.final_amount = Decimal(str(data.get("final_amount", transaction.final_amount)))
        transaction.transaction_type = (data.get("transaction_type") or transaction.transaction_type or "").strip()
        transaction.status = (data.get("status") or transaction.status or "pending").strip() or "pending"
        transaction.description = (data.get("description") if "description" in data else transaction.description) or ""
        transaction.metadata = dict(data.get("metadata", transaction.metadata or {}))
        transaction.save()
        return Response(_transaction_to_dict(transaction))

    def patch(self, request, pk):
        transaction = self.get_object(pk)
        if transaction is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        data = request.data
        if "amount" in data:
            transaction.amount = Decimal(str(data["amount"]))
        if "fee" in data:
            transaction.fee = Decimal(str(data["fee"]))
        if "final_amount" in data:
            transaction.final_amount = Decimal(str(data["final_amount"]))
        if "transaction_type" in data and data["transaction_type"] is not None:
            transaction.transaction_type = str(data["transaction_type"]).strip()
        if "status" in data and data["status"] is not None:
            transaction.status = str(data["status"]).strip() or "pending"
        if "description" in data:
            transaction.description = (data["description"] or "").strip() or ""
        if "metadata" in data:
            transaction.metadata = dict(data["metadata"] or {})
        transaction.save()
        return Response(_transaction_to_dict(transaction))

    def delete(self, request, pk):
        transaction = self.get_object(pk)
        if transaction is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        transaction.is_active = False
        transaction.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)
