from typing import Optional, Dict, Any
from api.system.models.audit import AuditLog
from api.common.utils.helpers import get_client_ip

class AuditRepository:
    """Repository for AuditLog data operations"""
    
    @staticmethod
    def create_log(
        user=None, 
        admin=None, 
        action: str = 'UPDATE', 
        entity_type: str = 'USER', 
        entity_id: str = '',
        old_values: Dict = None,
        new_values: Dict = None,
        request=None
    ) -> AuditLog:
        ip_address = '0.0.0.0'
        user_agent = 'unknown'
        session_id = None
        
        if request:
            ip_address = get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', 'unknown')
            session_id = getattr(request.session, 'session_key', None)
            
        return AuditLog.objects.create(
            user=user,
            admin=admin,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values or {},
            new_values=new_values or {},
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id
        )
