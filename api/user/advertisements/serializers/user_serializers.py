"""
User Advertisement Serializers
==============================
Request/response serializers for user ad endpoints
"""
from rest_framework import serializers
from decimal import Decimal

from api.user.advertisements.models import AdRequest, AdContent, AdDistribution
from api.user.media.models import MediaUpload


class MediaUploadSerializer(serializers.Serializer):
    """Serializer for media upload details"""
    id = serializers.UUIDField(read_only=True)
    file_url = serializers.URLField(read_only=True)
    file_type = serializers.CharField(read_only=True)
    original_name = serializers.CharField(read_only=True)
    file_size = serializers.IntegerField(read_only=True)


class AdContentSerializer(serializers.Serializer):
    """Serializer for ad content details"""
    id = serializers.UUIDField(read_only=True)
    content_type = serializers.CharField(read_only=True)
    duration_seconds = serializers.IntegerField(read_only=True)
    display_order = serializers.IntegerField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    media_upload = MediaUploadSerializer(read_only=True)


class StationMinimalSerializer(serializers.Serializer):
    """Minimal station info for ad distribution"""
    id = serializers.UUIDField(read_only=True)
    station_name = serializers.CharField(read_only=True)
    address = serializers.CharField(read_only=True)


class TransactionSerializer(serializers.Serializer):
    """Serializer for transaction details"""
    id = serializers.UUIDField(read_only=True)
    transaction_id = serializers.CharField(read_only=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    currency = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    payment_method_type = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class AdRequestCreateSerializer(serializers.Serializer):
    """
    Request serializer for creating ad request
    Used in: POST /api/user/ads/request
    """
    full_name = serializers.CharField(
        max_length=255,
        help_text="Advertiser's full name"
    )
    contact_number = serializers.CharField(
        max_length=20,
        help_text="Contact phone number"
    )
    media_upload_id = serializers.UUIDField(
        help_text="Media upload ID (IMAGE or VIDEO only)"
    )
    
    def validate_full_name(self, value):
        """Validate full name"""
        if len(value.strip()) < 3:
            raise serializers.ValidationError(
                "Full name must be at least 3 characters"
            )
        return value.strip()
    
    def validate_contact_number(self, value):
        """Validate contact number format"""
        # Basic validation - adjust based on your requirements
        cleaned = value.strip().replace(' ', '').replace('-', '')
        if len(cleaned) < 10:
            raise serializers.ValidationError(
                "Contact number must be at least 10 digits"
            )
        return value.strip()
    
    def validate_media_upload_id(self, value):
        """Validate media upload exists and belongs to user"""
        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError("Request context required")
        
        try:
            media = MediaUpload.objects.get(id=value, uploaded_by=request.user)
            
            # Validate media type
            if media.file_type not in ['IMAGE', 'VIDEO']:
                raise serializers.ValidationError(
                    "Only IMAGE or VIDEO files are allowed for advertisements"
                )
            
            return value
        except MediaUpload.DoesNotExist:
            raise serializers.ValidationError(
                "Media upload not found or access denied"
            )


class AdRequestListSerializer(serializers.Serializer):
    """
    Response serializer for listing user's ad requests
    Used in: GET /api/user/ads/my-ads
    """
    id = serializers.UUIDField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    contact_number = serializers.CharField(read_only=True)
    title = serializers.CharField(read_only=True, allow_null=True)
    description = serializers.CharField(read_only=True, allow_null=True)
    status = serializers.CharField(read_only=True)
    duration_days = serializers.IntegerField(read_only=True, allow_null=True)
    admin_price = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True, 
        allow_null=True
    )
    
    # Timestamps
    submitted_at = serializers.DateTimeField(read_only=True)
    reviewed_at = serializers.DateTimeField(read_only=True, allow_null=True)
    approved_at = serializers.DateTimeField(read_only=True, allow_null=True)
    paid_at = serializers.DateTimeField(read_only=True, allow_null=True)
    completed_at = serializers.DateTimeField(read_only=True, allow_null=True)
    
    # Dates
    start_date = serializers.DateField(read_only=True, allow_null=True)
    end_date = serializers.DateField(read_only=True, allow_null=True)
    
    # Notes
    rejection_reason = serializers.CharField(read_only=True, allow_null=True)
    admin_notes = serializers.CharField(read_only=True, allow_null=True)
    
    # Related data
    ad_content = serializers.SerializerMethodField()
    stations = serializers.SerializerMethodField()
    transaction = TransactionSerializer(read_only=True, allow_null=True)
    
    def get_ad_content(self, obj):
        """Get ad content with media"""
        content = obj.ad_contents.select_related('media_upload').first()
        if content:
            return AdContentSerializer(content).data
        return None
    
    def get_stations(self, obj):
        """Get stations where ad is distributed"""
        content = obj.ad_contents.first()
        if content:
            distributions = content.ad_distributions.select_related('station').all()
            return [
                StationMinimalSerializer(d.station).data 
                for d in distributions
            ]
        return []


class AdRequestDetailSerializer(AdRequestListSerializer):
    """
    Detailed response serializer for single ad request
    Used in: POST /api/user/ads/request (response)
    Inherits from AdRequestListSerializer with same fields
    """
    pass


class AdPaymentSerializer(serializers.Serializer):
    """
    Request serializer for ad payment
    Used in: POST /api/user/ads/{id}/pay
    
    No request body needed - payment is processed automatically
    """
    pass
