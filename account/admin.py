from django.contrib import admin
from .models import Account


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'phone_no', 'is_verified', 'created_at')
    search_fields = ('email', 'username', 'phone_no')
