from django.db import models
from common.models import BaseModel
from account.models import Account


class Wallet(BaseModel):
    """Wallet details - address and linked account."""
    account = models.OneToOneField(Account, on_delete=models.CASCADE, related_name='wallet')
    address = models.CharField(max_length=255, unique=True)
    wallet_type = models.CharField(max_length=50, blank=True)  # e.g. metamask, trust
    balance = models.DecimalField(max_digits=20, decimal_places=8, default=0)

    class Meta:
        db_table = 'wallet_wallet'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.account.email} - {self.address[:16]}..."


class Transaction(BaseModel):
    """Transaction record - amount, fee, final amount, etc."""
    transaction_id = models.CharField(max_length=100, unique=True, db_index=True)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    fee = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    final_amount = models.DecimalField(max_digits=20, decimal_places=8)
    transaction_type = models.CharField(max_length=50)  # credit, debit, transfer
    status = models.CharField(max_length=50, default='pending')  # pending, completed, failed
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    sender_name = models.CharField(max_length=255, blank=True)  # Sender name (plain text, not linked)
    receiver_name = models.CharField(max_length=255, blank=True)  # Receiver name (plain text, not linked)
    sender_type = models.CharField(max_length=50, blank=True)  # send, receive, etc.

    class Meta:
        db_table = 'wallet_transaction'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_id} - {self.final_amount}"
