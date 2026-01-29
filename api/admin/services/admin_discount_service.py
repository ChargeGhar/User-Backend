"""
Admin Discount Service
"""
from typing import Dict, Any
from django.db import transaction

from api.common.services.base import BaseService, ServiceException
from api.user.promotions.models import StationPackageDiscount
from api.user.rentals.models import RentalPackage
from api.user.stations.models import Station


class AdminDiscountService(BaseService):
    """Admin service for managing station package discounts"""
    
    @transaction.atomic
    def create_discount(self, data: Dict[str, Any], admin_user) -> StationPackageDiscount:
        """Create new discount"""
        try:
            station = Station.objects.get(id=data['station_id'])
            package = RentalPackage.objects.get(id=data['package_id'])
            
            if StationPackageDiscount.objects.filter(station=station, package=package).exists():
                raise ServiceException(
                    detail="Discount already exists for this station-package combination",
                    code="discount_exists"
                )
            
            discount = StationPackageDiscount.objects.create(
                station=station,
                package=package,
                discount_percent=data['discount_percent'],
                max_total_uses=data.get('max_total_uses'),
                max_uses_per_user=data.get('max_uses_per_user', 1),
                valid_from=data['valid_from'],
                valid_until=data['valid_until'],
                status=data.get('status', 'ACTIVE'),
                created_by=admin_user
            )
            
            return discount
            
        except (Station.DoesNotExist, RentalPackage.DoesNotExist) as e:
            raise ServiceException(detail=str(e), code="not_found")
    
    def get_discounts(self, filters: Dict[str, Any]):
        """Get discounts with filters"""
        queryset = StationPackageDiscount.objects.select_related(
            'station', 'package', 'created_by'
        ).all()
        
        if 'station_id' in filters:
            queryset = queryset.filter(station_id=filters['station_id'])
        
        if 'package_id' in filters:
            queryset = queryset.filter(package_id=filters['package_id'])
        
        if 'status' in filters:
            queryset = queryset.filter(status=filters['status'])
        
        return queryset.order_by('-created_at')
    
    def get_discount(self, discount_id: str) -> StationPackageDiscount:
        """Get single discount"""
        try:
            return StationPackageDiscount.objects.select_related(
                'station', 'package', 'created_by'
            ).get(id=discount_id)
        except StationPackageDiscount.DoesNotExist:
            raise ServiceException(detail="Discount not found", code="not_found")
    
    @transaction.atomic
    def update_discount(self, discount_id: str, data: Dict[str, Any]) -> StationPackageDiscount:
        """Update discount"""
        discount = self.get_discount(discount_id)
        
        for field in ['discount_percent', 'max_total_uses', 'max_uses_per_user', 
                      'valid_from', 'valid_until', 'status']:
            if field in data:
                setattr(discount, field, data[field])
        
        discount.save()
        return discount
    
    @transaction.atomic
    def delete_discount(self, discount_id: str):
        """Delete discount"""
        discount = self.get_discount(discount_id)
        discount.delete()
