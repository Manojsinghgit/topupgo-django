from rest_framework import serializers
from .models import Account


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = [
            'id',
            'email',
            'username',
            'phone_no',
            'profile_photo',
            'first_name',
            'last_name',
            'date_of_birth',
            'is_verified',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
