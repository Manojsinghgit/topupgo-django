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
]
