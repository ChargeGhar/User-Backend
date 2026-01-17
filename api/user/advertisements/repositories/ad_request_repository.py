"""
AdRequest Repository
====================
Data access layer for AdRequest model.
"""
from typing import Optional, List
from django.db.models import QuerySet, Q
from api.user.advertisements.models import AdRequest


class AdRequestRepository:
    """Repository for AdRequest data operations"""
    
    @staticmethod
    def get_by_id(ad_id: str) -> Optional[AdRequest]:
        """Get ad request by ID with all related data"""
        try:
            return AdRequest.objects.select_related(
                'user',
                'transaction',
                'reviewed_by',
                'approved_by'
            ).prefetch_related(
                'ad_contents__media_upload',
                'ad_contents__ad_distributions__station'
            ).get(id=ad_id)
        except AdRequest.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_id_for_user(ad_id: str, user) -> Optional[AdRequest]:
        """Get ad request by ID for specific user"""
        try:
            return AdRequest.objects.select_related(
                'user',
                'transaction',
                'reviewed_by',
                'approved_by'
            ).prefetch_related(
                'ad_contents__media_upload',
                'ad_contents__ad_distributions__station'
            ).get(id=ad_id, user=user)
        except AdRequest.DoesNotExist:
            return None
    
    @staticmethod
    def get_user_ad_requests(user, status: Optional[str] = None) -> QuerySet:
        """Get user's ad requests with optional status filter"""
        queryset = AdRequest.objects.filter(user=user).select_related(
            'transaction',
            'reviewed_by',
            'approved_by'
        ).prefetch_related(
            'ad_contents__media_upload',
            'ad_contents__ad_distributions__station'
        ).order_by('-created_at')
        
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset
    
    @staticmethod
    def get_all_ad_requests(filters: Optional[dict] = None) -> QuerySet:
        """Get all ad requests with optional filters (for admin)"""
        queryset = AdRequest.objects.select_related(
            'user',
            'transaction',
            'reviewed_by',
            'approved_by'
        ).prefetch_related(
            'ad_contents__media_upload',
            'ad_contents__ad_distributions__station'
        ).order_by('-created_at')
        
        if not filters:
            return queryset
        
        # Apply status filter
        if filters.get('status'):
            queryset = queryset.filter(status=filters['status'])
        
        # Apply user filter
        if filters.get('user_id'):
            queryset = queryset.filter(user_id=filters['user_id'])
        
        # Apply search filter
        if filters.get('search'):
            search = filters['search']
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(full_name__icontains=search) |
                Q(user__username__icontains=search) |
                Q(user__email__icontains=search)
            )
        
        return queryset
    
    @staticmethod
    def get_scheduled_ads_to_start(today) -> QuerySet:
        """Get scheduled ads that should start today"""
        return AdRequest.objects.filter(
            status='SCHEDULED',
            start_date__lte=today
        )
    
    @staticmethod
    def get_running_ads_to_complete(today) -> QuerySet:
        """Get running ads that should be completed"""
        return AdRequest.objects.filter(
            status='RUNNING',
            end_date__lt=today
        )
    
    @staticmethod
    def create(user, **kwargs) -> AdRequest:
        """Create new ad request"""
        return AdRequest.objects.create(user=user, **kwargs)
    
    @staticmethod
    def update(ad_request: AdRequest, **kwargs) -> AdRequest:
        """Update existing ad request"""
        for field, value in kwargs.items():
            setattr(ad_request, field, value)
        ad_request.save()
        return ad_request
    
    @staticmethod
    def count_by_status(status: str) -> int:
        """Count ad requests by status"""
        return AdRequest.objects.filter(status=status).count()
    
    @staticmethod
    def count_by_user(user) -> int:
        """Count ad requests by user"""
        return AdRequest.objects.filter(user=user).count()
    
    @staticmethod
    def get_active_ads_for_user(user) -> List[AdRequest]:
        """Get user's active ads (RUNNING or SCHEDULED)"""
        return list(AdRequest.objects.filter(
            user=user,
            status__in=['RUNNING', 'SCHEDULED']
        ).order_by('-created_at'))
