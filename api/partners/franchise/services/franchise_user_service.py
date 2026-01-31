"""
Franchise User Service

Service for searching users for vendor creation.
"""

from typing import Dict, Any
from django.db.models import Q

from api.common.services.base import BaseService
from api.common.utils.helpers import paginate_queryset
from api.user.auth.models import User


class FranchiseUserService(BaseService):
    """Service for franchise user operations"""
    
    def search_users_for_vendor(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search users for vendor creation
        
        Args:
            filters: Dict with search, exclude_partners, page, page_size
            
        Returns:
            Paginated user list with profile data
        """
        try:
            # Base query - active users with profile
            queryset = User.objects.select_related('profile').filter(is_active=True)
            
            # Search filter
            if filters.get('search'):
                search_term = filters['search']
                queryset = queryset.filter(
                    Q(username__icontains=search_term) |
                    Q(email__icontains=search_term) |
                    Q(phone_number__icontains=search_term)
                )
            
            # Exclude partners filter
            if filters.get('exclude_partners', True):
                queryset = queryset.filter(is_partner=False)
            
            # Order by latest
            queryset = queryset.order_by('-date_joined')
            
            # Paginate
            page = int(filters.get('page', 1))
            page_size = int(filters.get('page_size', 20))
            
            paginated_data = paginate_queryset(queryset, page, page_size)
            
            # Format results
            results = []
            for user in paginated_data['results']:
                user_data = {
                    'id': user.id,
                    'email': user.email,
                    'phone_number': user.phone_number,
                    'username': user.username,
                    'profile_picture': user.profile_picture,
                    'status': user.status,
                    'is_partner': user.is_partner,
                    'profile': None
                }
                
                # Add profile data if exists
                if hasattr(user, 'profile') and user.profile:
                    user_data['profile'] = {
                        'full_name': user.profile.full_name,
                        'date_of_birth': user.profile.date_of_birth,
                        'address': user.profile.address,
                        'avatar_url': user.profile.avatar_url,
                        'is_profile_complete': user.profile.is_profile_complete,
                    }
                
                results.append(user_data)
            
            return {
                'results': results,
                'count': paginated_data['pagination']['total_count'],
                'page': paginated_data['pagination']['current_page'],
                'page_size': page_size,
                'total_pages': paginated_data['pagination']['total_pages'],
            }
            
        except Exception as e:
            self.handle_service_error(e, "Failed to search users")
