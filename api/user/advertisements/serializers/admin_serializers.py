"""
Admin Advertisement Serializers
===============================
Request/response serializers for admin ad endpoints
"""
from rest_framework import serializers
from datetime import date, timedelta
from decimal import Decimal

from api.user.advertisements.models import AdRequest
from api.user.stations.models import Station


class AdminAdRequestListSerializer(serializers.Serializer):
    """
    Response serializer for listing all ad requests (admin)
    Used in: GET /api/admin/ads/requests
    """
    id = serializers.UUIDField(read_only=True)
    
    # User info
    user_id = serializers.UUIDField(source='user.id', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    
    # Ad info
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
    
    # Admin fields
    reviewed_by_name = serializers.CharField(
        source='reviewed_by.username', 
        read_only=True, 
        allow_null=True
    )
    approved_by_name = serializers.CharField(
        source='approved_by.username', 
        read_only=True, 
        allow_null=True
    )
    
    # Summary
    station_count = serializers.SerializerMethodField()
    
    def get_station_count(self, obj):
        """Count stations where ad is distributed"""
        content = obj.ad_contents.first()
        if content:
            return content.ad_distributions.count()
        return 0


class AdminAdRequestDetailSerializer(serializers.Serializer):
    """
    Detailed response serializer for single ad request (admin)
    Used in: GET /api/admin/ads/requests/{id}
    """
    id = serializers.UUIDField(read_only=True)
    
    # User info
    user = serializers.SerializerMethodField()
    
    # Ad info
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
    
    # Admin fields
    reviewed_by = serializers.SerializerMethodField()
    approved_by = serializers.SerializerMethodField()
    
    # Related data
    ad_content = serializers.SerializerMethodField()
    stations = serializers.SerializerMethodField()
    transaction = serializers.SerializerMethodField()
    
    def get_user(self, obj):
        """Get user details"""
        return {
            'id': str(obj.user.id),
            'email': obj.user.email,
            'username': obj.user.username,
            'phone_number': obj.user.phone_number
        }
    
    def get_reviewed_by(self, obj):
        """Get reviewer details"""
        if obj.reviewed_by:
            return {
                'id': str(obj.reviewed_by.id),
                'username': obj.reviewed_by.username,
                'email': obj.reviewed_by.email
            }
        return None
    
    def get_approved_by(self, obj):
        """Get approver details"""
        if obj.approved_by:
            return {
                'id': str(obj.approved_by.id),
                'username': obj.approved_by.username,
                'email': obj.approved_by.email
            }
        return None
    
    def get_ad_content(self, obj):
        """Get ad content with media"""
        content = obj.ad_contents.select_related('media_upload').first()
        if content:
            return {
                'id': str(content.id),
                'content_type': content.content_type,
                'duration_seconds': content.duration_seconds,
                'display_order': content.display_order,
                'is_active': content.is_active,
                'media_upload': {
                    'id': str(content.media_upload.id),
                    'file_url': content.media_upload.file_url,
                    'file_type': content.media_upload.file_type,
                    'original_name': content.media_upload.original_name,
                    'file_size': content.media_upload.file_size
                }
            }
        return None
    
    def get_stations(self, obj):
        """Get stations where ad is distributed"""
        content = obj.ad_contents.first()
        if content:
            distributions = content.ad_distributions.select_related('station').all()
            return [
                {
                    'id': str(d.station.id),
                    'station_name': d.station.station_name,
                    'serial_number': d.station.serial_number,
                    'address': d.station.address,
                    'status': d.station.status
                }
                for d in distributions
            ]
        return []
    
    def get_transaction(self, obj):
        """Get transaction details"""
        if obj.transaction:
            return {
                'id': str(obj.transaction.id),
                'transaction_id': obj.transaction.transaction_id,
                'amount': str(obj.transaction.amount),
                'currency': obj.transaction.currency,
                'status': obj.transaction.status,
                'payment_method_type': obj.transaction.payment_method_type,
                'created_at': obj.transaction.created_at
            }
        return None


class AdminAdReviewSerializer(serializers.Serializer):
    """
    Request serializer for reviewing ad request
    Used in: PATCH /api/admin/ads/requests/{id}/review
    """
    title = serializers.CharField(
        max_length=255,
        help_text="Advertisement title"
    )
    description = serializers.CharField(
        help_text="Advertisement description"
    )
    duration_days = serializers.IntegerField(
        min_value=1,
        max_value=365,
        help_text="Duration in days (1-365)"
    )
    admin_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01'),
        help_text="Price in NPR"
    )
    admin_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Admin notes/comments"
    )
    station_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        help_text="List of station IDs where ad will be displayed"
    )
    start_date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Optional start date"
    )
    
    # AdContent settings
    duration_seconds = serializers.IntegerField(
        min_value=3,
        max_value=30,
        default=5,
        help_text="Display duration in seconds (3-30)"
    )
    display_order = serializers.IntegerField(
        min_value=0,
        default=0,
        help_text="Display order/priority (0=highest)"
    )
    
    def validate_title(self, value):
        """Validate title"""
        if len(value.strip()) < 5:
            raise serializers.ValidationError(
                "Title must be at least 5 characters"
            )
        return value.strip()
    
    def validate_description(self, value):
        """Validate description"""
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Description must be at least 10 characters"
            )
        return value.strip()
    
    def validate_station_ids(self, value):
        """Validate all stations exist"""
        existing_ids = set(
            Station.objects.filter(id__in=value).values_list('id', flat=True)
        )
        
        invalid_ids = set(value) - existing_ids
        if invalid_ids:
            raise serializers.ValidationError(
                f"Invalid station IDs: {', '.join(str(id) for id in invalid_ids)}"
            )
        
        return value
    
    def validate_start_date(self, value):
        """Validate start date is not in the past"""
        if value and value < date.today():
            raise serializers.ValidationError(
                "Start date cannot be in the past"
            )
        return value
    
    def validate(self, attrs):
        """Cross-field validation"""
        # Calculate end_date if start_date provided
        if attrs.get('start_date'):
            attrs['_calculated_end_date'] = attrs['start_date'] + timedelta(
                days=attrs['duration_days']
            )
        
        return attrs


class AdminAdActionSerializer(serializers.Serializer):
    """
    Request serializer for ad actions
    Used in: POST /api/admin/ads/requests/{id}/action
    """
    action = serializers.ChoiceField(
        choices=[
            'approve',
            'reject',
            'schedule',
            'pause',
            'resume',
            'cancel',
            'complete'
        ],
        help_text="Action to perform"
    )
    
    # Action-specific fields
    rejection_reason = serializers.CharField(
        required=False,
        allow_blank=False,
        help_text="Required for 'reject' action"
    )
    start_date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Required for 'schedule' action"
    )
    end_date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Optional for 'schedule' action (auto-calculated if not provided)"
    )
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional reason for 'cancel' action"
    )
    
    def validate_rejection_reason(self, value):
        """Validate rejection reason"""
        if value and len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Rejection reason must be at least 10 characters"
            )
        return value.strip() if value else None
    
    def validate_start_date(self, value):
        """Validate start date"""
        if value and value < date.today():
            raise serializers.ValidationError(
                "Start date cannot be in the past"
            )
        return value
    
    def validate_end_date(self, value):
        """Validate end date"""
        if value and value < date.today():
            raise serializers.ValidationError(
                "End date cannot be in the past"
            )
        return value
    
    def validate(self, attrs):
        """Validate action-specific requirements"""
        action = attrs.get('action')
        
        # REJECT requires rejection_reason
        if action == 'reject':
            if not attrs.get('rejection_reason'):
                raise serializers.ValidationError({
                    'rejection_reason': 'Rejection reason is required for reject action'
                })
        
        # SCHEDULE requires start_date
        if action == 'schedule':
            if not attrs.get('start_date'):
                raise serializers.ValidationError({
                    'start_date': 'Start date is required for schedule action'
                })
            
            # Validate end_date is after start_date if provided
            if attrs.get('end_date') and attrs.get('start_date'):
                if attrs['end_date'] <= attrs['start_date']:
                    raise serializers.ValidationError({
                        'end_date': 'End date must be after start date'
                    })
        
        return attrs


class AdminAdScheduleUpdateSerializer(serializers.Serializer):
    """
    Request serializer for updating ad schedule
    Used in: PATCH /api/admin/ads/requests/{id}/update-schedule
    """
    start_date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="New start date"
    )
    end_date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="New end date"
    )
    
    def validate_start_date(self, value):
        """Validate start date"""
        if value and value < date.today():
            raise serializers.ValidationError(
                "Start date cannot be in the past"
            )
        return value
    
    def validate_end_date(self, value):
        """Validate end date"""
        if value and value < date.today():
            raise serializers.ValidationError(
                "End date cannot be in the past"
            )
        return value
    
    def validate(self, attrs):
        """Validate at least one date is provided"""
        if not attrs.get('start_date') and not attrs.get('end_date'):
            raise serializers.ValidationError(
                "At least one of start_date or end_date must be provided"
            )
        
        # Validate end_date is after start_date if both provided
        if attrs.get('start_date') and attrs.get('end_date'):
            if attrs['end_date'] <= attrs['start_date']:
                raise serializers.ValidationError({
                    'end_date': 'End date must be after start date'
                })
        
        return attrs
