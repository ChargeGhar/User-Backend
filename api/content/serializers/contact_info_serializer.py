from __future__ import annotations

from rest_framework import serializers
from api.content.models import ContactInfo


class ContactInfoSerializer(serializers.ModelSerializer):
    """Serializer for contact information"""
    updated_by_username = serializers.CharField(source='updated_by.username', read_only=True)
    
    class Meta:
        model = ContactInfo
        fields = [
            'id', 'info_type', 'label', 'value', 'description', 
            'is_active', 'updated_at', 'updated_by_username'
        ]
        read_only_fields = ['id', 'updated_at']
    
    def validate_value(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Value must be at least 3 characters")
        return value.strip()


class ContactInfoPublicSerializer(serializers.ModelSerializer):
    """Public serializer for contact information"""
    
    class Meta:
        model = ContactInfo
        fields = ['info_type', 'label', 'value', 'description']
