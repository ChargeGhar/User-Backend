from typing import Optional, List, Tuple
from django.utils import timezone
from api.content.models import ContentPage

class ContentPageRepository:
    """Repository for ContentPage data operations"""
    
    @staticmethod
    def get_by_type(page_type: str) -> Optional[ContentPage]:
        """Get active content page by type"""
        return ContentPage.objects.filter(page_type=page_type, is_active=True).first()

    @staticmethod
    def get_or_create(page_type: str, defaults: dict) -> Tuple[ContentPage, bool]:
        """Get or create content page"""
        return ContentPage.objects.get_or_create(page_type=page_type, defaults=defaults)

    @staticmethod
    def update(page: ContentPage, **kwargs) -> ContentPage:
        """Update content page"""
        for field, value in kwargs.items():
            setattr(page, field, value)
        page.save()
        return page

    @staticmethod
    def get_all_active() -> List[ContentPage]:
        """Get all active content pages"""
        return list(ContentPage.objects.filter(is_active=True))

    @staticmethod
    def count_active() -> int:
        """Count active content pages"""
        return ContentPage.objects.filter(is_active=True).count()

    @staticmethod
    def get_recently_updated(days: int = 7, limit: int = 5) -> List[ContentPage]:
        """Get recently updated content pages"""
        since = timezone.now() - timezone.timedelta(days=days)
        return list(ContentPage.objects.filter(updated_at__gte=since).order_by('-updated_at')[:limit])
