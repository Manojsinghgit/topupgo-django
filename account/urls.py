from django.urls import path

from .views import AccountDetailAPIView, AccountListCreateAPIView

app_name = "account"

urlpatterns = [
    path("accounts/", AccountListCreateAPIView.as_view(), name="account-list-create"),
    path("accounts/<int:pk>/", AccountDetailAPIView.as_view(), name="account-detail"),
]
