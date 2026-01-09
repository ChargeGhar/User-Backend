from typing import Optional, List, Tuple
from api.user.content.models import ContactInfo

class ContactInfoRepository:
    """Repository for ContactInfo data operations"""
    
    @staticmethod
    def get_all() -> List[ContactInfo]:
        """Get all contact info entries ordered by info_type"""
        return list(ContactInfo.objects.all().order_by('info_type'))

    @staticmethod
    def get_all_active() -> List[ContactInfo]:
        """Get all active contact info entries"""
        return list(ContactInfo.objects.filter(is_active=True).order_by('info_type'))

    @staticmethod
    def get_by_type(info_type: str) -> Optional[ContactInfo]:
        """Get contact info by type (e.g., 'PHONE', 'EMAIL')"""
        return ContactInfo.objects.filter(info_type=info_type, is_active=True).first()

    @staticmethod
    def get_by_id(contact_id: str) -> Optional[ContactInfo]:
        """Get contact info by ID"""
        try:
            return ContactInfo.objects.get(id=contact_id)
        except ContactInfo.DoesNotExist:
            return None

    @staticmethod
    def get_or_create(info_type: str, defaults: dict) -> Tuple[ContactInfo, bool]:
        """Get or create contact info"""
        return ContactInfo.objects.get_or_create(info_type=info_type, defaults=defaults)

    @staticmethod
    def create(**kwargs) -> ContactInfo:
        """Create a new contact info"""
        return ContactInfo.objects.create(**kwargs)

    @staticmethod
    def update(contact: ContactInfo, **kwargs) -> ContactInfo:
        """Update existing contact info"""
        for field, value in kwargs.items():
            setattr(contact, field, value)
        contact.save()
        return contact

    @staticmethod
    def delete(contact: ContactInfo) -> None:
        """Delete contact info"""
        contact.delete()
