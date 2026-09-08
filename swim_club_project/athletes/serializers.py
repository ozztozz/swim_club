# athletes/serializers.py
from rest_framework import serializers
from .models import Athlete

class AthleteSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent', read_only=True)
    class Meta:
        model = Athlete
        fields = (
            'id', 'parent', 'parent_name', 'parent_phone', 'parent_email', 'first_name', 'last_name', 'phone_number',
            'tc_identity', 'birth_date', 'gender', 'school', 
            'license_number', 'joined_date', 'photo', 
            'is_active', 'created_at'
        )
        read_only_fields = ('is_active',)
        extra_kwargs = {
            'parent': {'required': False, 'allow_blank': True},
        }