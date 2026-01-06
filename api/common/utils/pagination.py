from __future__ import annotations

from typing import Any, Dict
from django.core.paginator import Paginator


def paginate_queryset(queryset, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    """Paginate queryset and return pagination info"""
    if not queryset.ordered:
        queryset = queryset.order_by('-created_at')
    
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    
    return {
        'results': list(page_obj.object_list),
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
            'page_size': page_size,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
            'previous_page': page_obj.previous_page_number() if page_obj.has_previous() else None,
        }
    }
