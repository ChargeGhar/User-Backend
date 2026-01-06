from rest_framework import serializers
from api.users.models import UserKYC

class UserKYCSerializer(serializers.ModelSerializer):
    """Serializer for user KYC"""
    class Meta:
        model = UserKYC
        fields = [
            'id', 'document_type', 'document_number', 'document_front_url',
            'document_back_url', 'status', 'verified_at', 'rejection_reason',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'status', 'verified_at', 'rejection_reason', 
            'created_at', 'updated_at'
        ]
    
    def validate_document_number(self, value):
        if not value or len(value.strip()) < 5:
            raise serializers.ValidationError("Document number must be at least 5 characters")
        return value.strip()
