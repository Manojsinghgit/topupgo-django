from django.contrib import admin
from .models import Wallet, Transaction


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('account', 'address', 'wallet_type', 'balance', 'created_at')
    search_fields = ('address', 'account__email')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'wallet', 'amount', 'fee', 'final_amount', 'transaction_type', 'status', 'sender_name', 'receiver_name', 'sender_type', 'created_at')
    search_fields = ('transaction_id', 'sender_name', 'receiver_name', 'sender_type')
