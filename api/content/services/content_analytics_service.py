from __future__ import annotations

from typing import Dict, Any, List
from django.utils import timezone
from api.common.services.base import BaseService
from api.content.repositories import ContentPageRepository, FAQRepository, BannerRepository

class ContentAnalyticsService(BaseService):
    """Service for content analytics"""
    
    def get_content_analytics(self) -> Dict[str, Any]:
        """Get content analytics data"""
        try:
            # Basic counts
            total_pages = ContentPageRepository.count_active()
            total_faqs = FAQRepository.count_active()
            total_banners = BannerRepository.count_total()
            active_banners = BannerRepository.count_active()
            
            # Popular content (mock data - would need view tracking)
            popular_pages = [
                {'page_type': 'terms-of-service', 'views': 1250},
                {'page_type': 'privacy-policy', 'views': 980},
                {'page_type': 'faq', 'views': 2100}
            ]
            
            popular_faqs = [
                {'question': 'How do I rent a power bank?', 'views': 450},
                {'question': 'What are the rental charges?', 'views': 380},
                {'question': 'How do I return a power bank?', 'views': 320}
            ]
            
            # Recent updates
            recent_updates = []
            
            recent_pages = ContentPageRepository.get_recently_updated(days=7, limit=5)
            for page in recent_pages:
                recent_updates.append({
                    'type': 'page',
                    'title': page.title,
                    'updated_at': page.updated_at
                })
            
            recent_faqs = FAQRepository.get_recently_updated(days=7, limit=5)
            for faq in recent_faqs:
                recent_updates.append({
                    'type': 'faq',
                    'title': faq.question[:50] + '...' if len(faq.question) > 50 else faq.question,
                    'updated_at': faq.updated_at
                })
            
            # Sort recent updates by date
            recent_updates.sort(key=lambda x: x['updated_at'], reverse=True)
            
            return {
                'total_pages': total_pages,
                'total_faqs': total_faqs,
                'total_banners': total_banners,
                'active_banners': active_banners,
                'popular_pages': popular_pages,
                'popular_faqs': popular_faqs,
                'recent_updates': recent_updates[:10],
                'last_updated': timezone.now()
            }
            
        except Exception as e:
            self.handle_service_error(e, "Failed to get content analytics")
