# athletes/serializers.py
from rest_framework import serializers
from .models import Athlete

class AthleteSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Athlete
        fields = (
            'id', 'parent', 'parent_name', 'first_name', 'last_name', 
            'tc_identity', 'birth_date', 'gender', 'school', 
            'license_number', 'joined_date', 'photo', 
            'status', 'status_display', 'is_active', 'created_at'
        )
        read_only_fields = ('status', 'is_active', 'parent')