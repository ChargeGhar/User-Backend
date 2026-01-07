from __future__ import annotations

from rest_framework import serializers
from api.content.models import FAQ


class FAQSerializer(serializers.ModelSerializer):
    """Serializer for FAQs"""
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    updated_by_username = serializers.CharField(source='updated_by.username', read_only=True)
    
    class Meta:
        model = FAQ
        fields = [
            'id', 'question', 'answer', 'category', 'sort_order', 
            'is_active', 'created_at', 'updated_at', 'created_by_username', 
            'updated_by_username'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_question(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Question must be at least 10 characters")
        return value.strip()
    
    def validate_answer(self, value):
        if len(value.strip()) < 20:
            raise serializers.ValidationError("Answer must be at least 20 characters")
        return value.strip()


class FAQPublicSerializer(serializers.ModelSerializer):
    """Public serializer for FAQs"""
    
    class Meta:
        model = FAQ
        fields = ['id', 'question', 'answer', 'category', 'sort_order']


class FAQCategorySerializer(serializers.Serializer):
    """Serializer for FAQ categories"""
    category = serializers.CharField()
    faq_count = serializers.IntegerField()
    faqs = FAQPublicSerializer(many=True)
