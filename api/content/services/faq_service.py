from __future__ import annotations

from typing import Dict, List
from django.db import transaction
from api.common.services.base import BaseService, ServiceException
from api.content.repositories.faq_repository import FAQRepository
from api.content.models import FAQ

class FAQService(BaseService):
    """Service for FAQ operations"""
    
    def get_all(self):
        """Get all FAQs for admin"""
        try:
            return FAQRepository.get_all()
        except Exception as e:
            self.handle_service_error(e, "Failed to get all FAQs")
    
    def get_by_id(self, faq_id: str):
        """Get FAQ by ID"""
        faq = FAQRepository.get_by_id(faq_id)
        if not faq:
            raise ServiceException(
                detail="FAQ not found",
                code="faq_not_found"
            )
        return faq
    
    def delete_by_id(self, faq_id: str):
        """Delete FAQ by ID"""
        try:
            faq = self.get_by_id(faq_id)
            FAQRepository.delete(faq)
            self.log_info(f"FAQ deleted: {faq_id}")
            return True
        except ServiceException:
            raise
        except Exception as e:
            self.handle_service_error(e, "Failed to delete FAQ")
    
    def get_faqs_by_category(self, serializer_class=None) -> List[Dict]:
        """Get FAQs grouped by category and formatted for response"""
        try:
            faqs = FAQRepository.get_active_faqs()
            
            # Group by category
            faqs_by_category = {}
            for faq in faqs:
                if faq.category not in faqs_by_category:
                    faqs_by_category[faq.category] = []
                faqs_by_category[faq.category].append(faq)
            
            # Format response
            categories_data = []
            for category, category_faqs in faqs_by_category.items():
                data = {
                    'category': category,
                    'faq_count': len(category_faqs),
                }
                
                if serializer_class:
                    data['faqs'] = serializer_class(category_faqs, many=True).data
                else:
                    data['faq_ids'] = [str(f.id) for f in category_faqs]
                    
                categories_data.append(data)
                
            return categories_data
            
        except Exception as e:
            self.handle_service_error(e, "Failed to get FAQs by category")
    
    def search_faqs(self, query: str) -> List:
        """Search FAQs by query"""
        try:
            return FAQRepository.search(query)
        except Exception as e:
            self.handle_service_error(e, "Failed to search FAQs")
    
    @transaction.atomic
    def create_faq(self, question: str, answer: str, category: str, admin_user) -> FAQ:
        """Create new FAQ"""
        try:
            max_order = FAQRepository.get_max_sort_order(category)
            
            faq = FAQRepository.create(
                question=question,
                answer=answer,
                category=category,
                sort_order=max_order + 1,
                created_by=admin_user,
                updated_by=admin_user
            )
            
            self.log_info(f"FAQ created: {question[:50]}...")
            return faq
            
        except Exception as e:
            self.handle_service_error(e, "Failed to create FAQ")
    
    @transaction.atomic
    def update_faq(self, faq_id: str, question: str, answer: str, category: str, admin_user) -> FAQ:
        """Update existing FAQ"""
        try:
            faq = self.get_by_id(faq_id)
            
            updated_faq = FAQRepository.update(
                faq,
                question=question,
                answer=answer,
                category=category,
                updated_by=admin_user
            )
            
            self.log_info(f"FAQ updated: {faq_id}")
            return updated_faq
            
        except ServiceException:
            raise
        except Exception as e:
            self.handle_service_error(e, "Failed to update FAQ")
