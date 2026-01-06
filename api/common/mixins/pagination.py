from typing import Dict
from rest_framework.request import Request

class PaginationMixin:
    """Mixin for consistent pagination handling"""
    
    default_page_size = 20
    max_page_size = 100
    
    def get_pagination_params(self, request: Request) -> Dict[str, int]:
        """Extract pagination parameters from request"""
        try:
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', self.default_page_size))
            
            page = max(1, page)
            page_size = min(max(1, page_size), self.max_page_size)
            
            return {'page': page, 'page_size': page_size}
        except (ValueError, TypeError):
            return {'page': 1, 'page_size': self.default_page_size}
    
    def paginate_response(self, queryset, request: Request, serializer_class=None):
        """Paginate queryset and return response"""
        from api.common.utils.helpers import paginate_queryset
        
        pagination_params = self.get_pagination_params(request)
        result = paginate_queryset(
            queryset, 
            page=pagination_params['page'],
            page_size=pagination_params['page_size']
        )
        
        if serializer_class:
            serializer = serializer_class(result['results'], many=True, context={'request': request})
            result['results'] = serializer.data
        
        return result
