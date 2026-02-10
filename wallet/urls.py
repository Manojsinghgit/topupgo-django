from django.urls import path

from .views import (
    TransactionDetailAPIView,
    TransactionListCreateAPIView,
    WalletDetailAPIView,
    WalletListCreateAPIView,
    WalletMyListAPIViewV1,
    WalletMyDetailAPIViewV1,
    WalletAddressByUsernameAPIView
)

app_name = "wallet"

urlpatterns = [
    path("wallets/", WalletListCreateAPIView.as_view(), name="wallet-list-create"),
    path("wallets/<int:pk>/", WalletDetailAPIView.as_view(), name="wallet-detail"),
    path("transactions/", TransactionListCreateAPIView.as_view(), name="transaction-list-create"),
    path("transactions/<int:pk>/", TransactionDetailAPIView.as_view(), name="transaction-detail"),
    path("v1/wallets/", WalletMyListAPIViewV1.as_view(),name="get-wallet"),
    path("v1/wallets/<int:wallet_id>/", WalletMyDetailAPIViewV1.as_view(), name="get-wallet-detail"),
    path("wallet-address-by-username/", WalletAddressByUsernameAPIView.as_view(), name="wallet-address-by-username"),
]
