import logging
from typing import Optional

logger = logging.getLogger(__name__)

class CacheableMixin:
    """Mixin for adding cache support to views"""
    
    cache_timeout = 300  # 5 minutes default
    
    def get_cache_key(self, *args, **kwargs) -> str:
        """Generate cache key for the view"""
        view_name = self.__class__.__name__
        user_id = getattr(self.request.user, 'id', 'anonymous') if hasattr(self, 'request') else 'anonymous'
        
        key_parts = [view_name, str(user_id)]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
        
        return ":".join(key_parts)
