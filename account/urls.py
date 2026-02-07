from django.urls import path
from . import views

app_name = "account"

urlpatterns = [
    path(
        "accounts/",
        views.AccountListCreateAPIView.as_view(),
        name="account-list-create"
    ),
    path(
        "accounts/<int:pk>/",
        views.AccountDetailAPIView.as_view(),
        name="account-detail"
    ),
    path(
        "account/exists/",
        views.AccountExistsView.as_view(),
        name="account-exists"
    ),
    path(
        "account/token/refresh/",
        views.TokenRefreshAPIView.as_view(),
        name="token-refresh"
    ),
    path(
        "account/me/",
        views.AccountMeAPIView.as_view(),
        name="account-me"
    ),
    path(
        "account-detail-by-email/",
        views.AccountDetailByEmailAPIView.as_view(),
        name="account-detail-by-email"
    ),
]
