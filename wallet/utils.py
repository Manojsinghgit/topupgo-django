def transaction_to_dict(transaction):
    return {
        "id": transaction.id,
        "amount": transaction.amount,
        "transaction_type": transaction.transaction_type,
        "wallet_type": transaction.wallet.wallet_type,
        "username": transaction.wallet.account.username,
        "address": transaction.wallet.address,
        "created_at": transaction.created_at,
    }
