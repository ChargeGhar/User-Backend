from typing import Optional, List
from django.db.models import Max
from django.utils import timezone
from api.content.models import Banner

class BannerRepository:
    """Repository for Banner data operations"""
    
    @staticmethod
    def get_all() -> List[Banner]:
        """Get all banners ordered by display order"""
        return list(Banner.objects.all().order_by('display_order', '-created_at'))

    @staticmethod
    def get_active_banners() -> List[Banner]:
        """Get currently active banners"""
        now = timezone.now()
        return list(Banner.objects.filter(
            is_active=True,
            valid_from__lte=now,
            valid_until__gte=now
        ).order_by('display_order', '-created_at'))

    @staticmethod
    def get_by_id(banner_id: str) -> Optional[Banner]:
        """Get banner by ID"""
        try:
            return Banner.objects.get(id=banner_id)
        except Banner.DoesNotExist:
            return None

    @staticmethod
    def get_max_display_order() -> int:
        """Get current maximum display order"""
        return Banner.objects.aggregate(max_order=Max('display_order'))['max_order'] or 0

    @staticmethod
    def count_total() -> int:
        """Count total banners"""
        return Banner.objects.count()

    @staticmethod
    def count_active() -> int:
        """Count currently active banners"""
        now = timezone.now()
        return Banner.objects.filter(
            is_active=True,
            valid_from__lte=now,
            valid_until__gte=now
        ).count()

    @staticmethod
    def create(**kwargs) -> Banner:
        """Create a new banner"""
        return Banner.objects.create(**kwargs)

    @staticmethod
    def update(banner: Banner, **kwargs) -> Banner:
        """Update an existing banner"""
        for field, value in kwargs.items():
            setattr(banner, field, value)
        banner.save()
        return banner

    @staticmethod
    def delete(banner: Banner) -> None:
        """Delete a banner"""
        banner.delete()
