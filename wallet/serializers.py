from rest_framework import serializers
from .models import Wallet, Transaction


class WalletSerializer(serializers.ModelSerializer):
    account_email = serializers.EmailField(source='account.email', read_only=True)

    class Meta:
        model = Wallet
        fields = [
            'id',
            'account',
            'account_email',
            'address',
            'wallet_type',
            'balance',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = [
            'id',
            'transaction_id',
            'wallet',
            'amount',
            'fee',
            'final_amount',
            'transaction_type',
            'status',
            'description',
            'metadata',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
