from rest_framework.request import Request

class FilterMixin:
    """Mixin for common filtering operations"""
    
    def apply_date_filters(self, queryset, request: Request, date_field: str = 'created_at'):
        """Apply date range filters to queryset"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            try:
                from django.utils.dateparse import parse_datetime
                start_dt = parse_datetime(start_date)
                if start_dt:
                    queryset = queryset.filter(**{f"{date_field}__gte": start_dt})
            except (ValueError, TypeError):
                pass
        
        if end_date:
            try:
                from django.utils.dateparse import parse_datetime
                end_dt = parse_datetime(end_date)
                if end_dt:
                    queryset = queryset.filter(**{f"{date_field}__lte": end_dt})
            except (ValueError, TypeError):
                pass
        
        return queryset
    
    def apply_status_filter(self, queryset, request: Request, status_field: str = 'status'):
        """Apply status filter to queryset"""
        status_value = request.query_params.get('status')
        if status_value:
            queryset = queryset.filter(**{status_field: status_value})
        return queryset
