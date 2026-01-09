from typing import Optional, List
from django.db.models import Q, Max
from django.utils import timezone
from api.user.content.models import FAQ

class FAQRepository:
    """Repository for FAQ data operations"""
    
    @staticmethod
    def get_all() -> List[FAQ]:
        """Get all FAQs ordered by category and sort order"""
        return list(FAQ.objects.all().order_by('category', 'sort_order'))

    @staticmethod
    def get_active_faqs() -> List[FAQ]:
        """Get all active FAQs ordered by category and sort order"""
        return list(FAQ.objects.filter(is_active=True).order_by('category', 'sort_order'))

    @staticmethod
    def get_by_category(category: str) -> List[FAQ]:
        """Get active FAQs by category"""
        return list(FAQ.objects.filter(category=category, is_active=True).order_by('sort_order'))

    @staticmethod
    def get_by_id(faq_id: str) -> Optional[FAQ]:
        """Get FAQ by ID"""
        try:
            return FAQ.objects.get(id=faq_id)
        except FAQ.DoesNotExist:
            return None

    @staticmethod
    def search(query: str) -> List[FAQ]:
        """Search active FAQs by question or answer"""
        return list(FAQ.objects.filter(
            Q(question__icontains=query) | Q(answer__icontains=query),
            is_active=True
        ).order_by('category', 'sort_order'))

    @staticmethod
    def get_max_sort_order(category: str) -> int:
        """Get current maximum sort order for a category"""
        return FAQ.objects.filter(category=category).aggregate(max_order=Max('sort_order'))['max_order'] or 0

    @staticmethod
    def count_active() -> int:
        """Count active FAQs"""
        return FAQ.objects.filter(is_active=True).count()

    @staticmethod
    def get_recently_updated(days: int = 7, limit: int = 5) -> List[FAQ]:
        """Get recently updated FAQs"""
        since = timezone.now() - timezone.timedelta(days=days)
        return list(FAQ.objects.filter(updated_at__gte=since).order_by('-updated_at')[:limit])

    @staticmethod
    def create(**kwargs) -> FAQ:
        """Create a new FAQ"""
        return FAQ.objects.create(**kwargs)

    @staticmethod
    def update(faq: FAQ, **kwargs) -> FAQ:
        """Update existing FAQ"""
        for field, value in kwargs.items():
            setattr(faq, field, value)
        faq.save()
        return faq

    @staticmethod
    def delete(faq: FAQ) -> None:
        """Delete FAQ"""
        faq.delete()
