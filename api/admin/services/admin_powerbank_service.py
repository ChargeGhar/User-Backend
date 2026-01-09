"""
Service for admin powerbank management
============================================================

This module contains service classes for powerbank tracking and management.
"""
from __future__ import annotations
from typing import Dict, Any
from django.db import transaction
from django.db.models import Q, Count, Avg, Sum, F
from django.utils import timezone
from api.common.services.base import CRUDService, ServiceException
from api.common.utils.helpers import paginate_queryset
from api.admin.models import AdminActionLog
from api.user.stations.models import PowerBank, Station, StationSlot
from api.user.rentals.models import Rental


class AdminPowerBankService(CRUDService):
    """Service for admin powerbank management"""
    model = PowerBank
    
    def get_powerbanks_list(self, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get paginated list of powerbanks with filters"""
        try:
            queryset = PowerBank.objects.select_related(
                'current_station', 'current_slot'
            ).annotate(
                rental_count=Count('rental', filter=Q(rental__status__in=['ACTIVE', 'COMPLETED']))
            )
            
            # Apply filters
            if filters:
                if filters.get('status'):
                    queryset = queryset.filter(status=filters['status'])
                
                if filters.get('station_id'):
                    queryset = queryset.filter(current_station_id=filters['station_id'])
                
                if filters.get('search'):
                    search_term = filters['search']
                    queryset = queryset.filter(
                        Q(serial_number__icontains=search_term) |
                        Q(model__icontains=search_term)
                    )
                
                if filters.get('min_battery'):
                    queryset = queryset.filter(battery_level__gte=filters['min_battery'])
                
                if filters.get('max_battery'):
                    queryset = queryset.filter(battery_level__lte=filters['max_battery'])
            
            # Order by status priority and then by serial number
            from django.db.models import Case, When, IntegerField
            queryset = queryset.annotate(
                status_priority=Case(
                    When(status='RENTED', then=0),
                    When(status='MAINTENANCE', then=1),
                    When(status='DAMAGED', then=2),
                    When(status='AVAILABLE', then=3),
                    default=4,
                    output_field=IntegerField()
                )
            ).order_by('status_priority', 'serial_number')
            
            # Pagination
            page = filters.get('page', 1) if filters else 1
            page_size = filters.get('page_size', 20) if filters else 20
            
            paginated_result = paginate_queryset(queryset, page, page_size)
            
            # Format powerbanks data
            powerbanks_data = []
            for powerbank in paginated_result['results']:
                powerbanks_data.append(self._format_powerbank_list_item(powerbank))
            
            paginated_result['results'] = powerbanks_data
            return paginated_result
            
        except Exception as e:
            self.handle_service_error(e, "Failed to get powerbanks list")
    
    def _format_powerbank_list_item(self, powerbank: PowerBank) -> Dict[str, Any]:
        """Format powerbank object for list response"""
        # Get current rental if rented
        current_rental = None
        if powerbank.status == 'RENTED':
            try:
                rental = Rental.objects.filter(
                    power_bank=powerbank,
                    status__in=['PENDING', 'ACTIVE', 'OVERDUE']
                ).select_related('user', 'station', 'return_station').first()
                
                if rental:
                    current_rental = {
                        'rental_code': rental.rental_code,
                        'user_id': str(rental.user.id),
                        'username': rental.user.username,
                        'started_at': rental.started_at,
                        'due_at': rental.due_at,
                        'status': rental.status
                    }
            except Exception:
                pass
        
        return {
            'id': str(powerbank.id),
            'serial_number': powerbank.serial_number,
            'model': powerbank.model,
            'capacity_mah': powerbank.capacity_mah,
            'status': powerbank.status,
            'battery_level': powerbank.battery_level,
            'rental_count': powerbank.rental_count,
            'current_station': {
                'id': str(powerbank.current_station.id),
                'name': powerbank.current_station.station_name,
                'serial_number': powerbank.current_station.serial_number
            } if powerbank.current_station else None,
            'current_slot': {
                'id': str(powerbank.current_slot.id),
                'slot_number': powerbank.current_slot.slot_number
            } if powerbank.current_slot else None,
            'current_rental': current_rental,
            'last_updated': powerbank.last_updated
        }
    
    def get_powerbank_detail(self, powerbank_id: str) -> Dict[str, Any]:
        """Get detailed powerbank information"""
        try:
            powerbank = PowerBank.objects.select_related(
                'current_station', 'current_slot'
            ).annotate(
                total_rentals=Count('rental'),
                completed_rentals=Count('rental', filter=Q(rental__status='COMPLETED')),
                total_revenue=Sum('rental__amount_paid', filter=Q(rental__status='COMPLETED'))
            ).get(id=powerbank_id)
            
            # Get current rental details if rented
            current_rental = None
            if powerbank.status == 'RENTED':
                try:
                    rental = Rental.objects.filter(
                        power_bank=powerbank,
                        status__in=['PENDING', 'ACTIVE', 'OVERDUE']
                    ).select_related('user', 'station', 'return_station', 'package').first()
                    
                    if rental:
                        current_rental = {
                            'rental_code': rental.rental_code,
                            'user': {
                                'id': str(rental.user.id),
                                'username': rental.user.username,
                                'email': rental.user.email
                            },
                            'pickup_station': {
                                'id': str(rental.station.id),
                                'name': rental.station.station_name
                            },
                            'package': {
                                'name': rental.package.name,
                                'duration_minutes': rental.package.duration_minutes,
                                'price': str(rental.package.price)
                            },
                            'started_at': rental.started_at,
                            'due_at': rental.due_at,
                            'status': rental.status,
                            'payment_status': rental.payment_status
                        }
                except Exception:
                    pass
            
            # Get recent rental history (last 10)
            recent_rentals = Rental.objects.filter(
                power_bank=powerbank
            ).select_related('user', 'station', 'return_station').order_by('-created_at')[:10]
            
            rental_history = []
            for rental in recent_rentals:
                rental_history.append({
                    'rental_code': rental.rental_code,
                    'user': rental.user.username,
                    'pickup_station': rental.station.station_name,
                    'return_station': rental.return_station.station_name if rental.return_station else None,
                    'started_at': rental.started_at,
                    'ended_at': rental.ended_at,
                    'status': rental.status,
                    'amount_paid': str(rental.amount_paid)
                })
            
            return {
                'id': str(powerbank.id),
                'serial_number': powerbank.serial_number,
                'model': powerbank.model,
                'capacity_mah': powerbank.capacity_mah,
                'status': powerbank.status,
                'battery_level': powerbank.battery_level,
                'hardware_info': powerbank.hardware_info,
                'current_station': {
                    'id': str(powerbank.current_station.id),
                    'name': powerbank.current_station.station_name,
                    'serial_number': powerbank.current_station.serial_number,
                    'address': powerbank.current_station.address
                } if powerbank.current_station else None,
                'current_slot': {
                    'id': str(powerbank.current_slot.id),
                    'slot_number': powerbank.current_slot.slot_number,
                    'status': powerbank.current_slot.status
                } if powerbank.current_slot else None,
                'current_rental': current_rental,
                'statistics': {
                    'total_rentals': powerbank.total_rentals,
                    'completed_rentals': powerbank.completed_rentals,
                    'total_revenue': str(powerbank.total_revenue or 0)
                },
                'recent_history': rental_history,
                'last_updated': powerbank.last_updated,
                'created_at': powerbank.created_at
            }
            
        except PowerBank.DoesNotExist:
            raise ServiceException(
                detail="PowerBank not found",
                code="powerbank_not_found"
            )
        except Exception as e:
            self.handle_service_error(e, "Failed to get powerbank detail")
    
    def get_powerbank_history(self, powerbank_id: str, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get complete rental history for a powerbank"""
        try:
            # Verify powerbank exists
            powerbank = PowerBank.objects.get(id=powerbank_id)
            
            queryset = Rental.objects.filter(
                power_bank=powerbank
            ).select_related('user', 'station', 'return_station', 'package')
            
            # Apply filters
            if filters:
                if filters.get('status'):
                    queryset = queryset.filter(status=filters['status'])
                
                if filters.get('start_date'):
                    queryset = queryset.filter(started_at__gte=filters['start_date'])
                
                if filters.get('end_date'):
                    queryset = queryset.filter(started_at__lte=filters['end_date'])
            
            queryset = queryset.order_by('-started_at')
            
            # Pagination
            page = filters.get('page', 1) if filters else 1
            page_size = filters.get('page_size', 20) if filters else 20
            
            paginated_result = paginate_queryset(queryset, page, page_size)
            
            # Format history data
            history_data = []
            for rental in paginated_result['results']:
                history_data.append({
                    'rental_code': rental.rental_code,
                    'user': {
                        'id': str(rental.user.id),
                        'username': rental.user.username,
                        'email': rental.user.email
                    },
                    'pickup_station': {
                        'id': str(rental.station.id),
                        'name': rental.station.station_name
                    },
                    'return_station': {
                        'id': str(rental.return_station.id),
                        'name': rental.return_station.station_name
                    } if rental.return_station else None,
                    'package': {
                        'name': rental.package.name,
                        'duration_minutes': rental.package.duration_minutes
                    },
                    'started_at': rental.started_at,
                    'ended_at': rental.ended_at,
                    'due_at': rental.due_at,
                    'status': rental.status,
                    'payment_status': rental.payment_status,
                    'amount_paid': str(rental.amount_paid),
                    'overdue_amount': str(rental.overdue_amount),
                    'is_returned_on_time': rental.is_returned_on_time
                })
            
            paginated_result['results'] = history_data
            paginated_result['powerbank'] = {
                'serial_number': powerbank.serial_number,
                'model': powerbank.model
            }
            
            return paginated_result
            
        except PowerBank.DoesNotExist:
            raise ServiceException(
                detail="PowerBank not found",
                code="powerbank_not_found"
            )
        except Exception as e:
            self.handle_service_error(e, "Failed to get powerbank history")
    
    def get_powerbank_analytics(self) -> Dict[str, Any]:
        """Get powerbank fleet analytics"""
        try:
            # Overall statistics
            total_powerbanks = PowerBank.objects.count()
            
            status_breakdown = PowerBank.objects.values('status').annotate(
                count=Count('id')
            )
            
            # Convert to dict
            status_stats = {item['status']: item['count'] for item in status_breakdown}
            
            # Utilization metrics
            utilization = PowerBank.objects.aggregate(
                avg_battery=Avg('battery_level'),
                total_rentals=Count('rental'),
                active_rentals=Count('rental', filter=Q(rental__status='ACTIVE')),
                completed_rentals=Count('rental', filter=Q(rental__status='COMPLETED')),
                total_revenue=Sum('rental__amount_paid', filter=Q(rental__status='COMPLETED'))
            )
            
            # Top performing powerbanks (by rental count)
            top_performers = PowerBank.objects.annotate(
                rental_count=Count('rental', filter=Q(rental__status='COMPLETED')),
                revenue=Sum('rental__amount_paid', filter=Q(rental__status='COMPLETED'))
            ).order_by('-rental_count')[:10]
            
            top_performers_data = []
            for pb in top_performers:
                top_performers_data.append({
                    'serial_number': pb.serial_number,
                    'model': pb.model,
                    'status': pb.status,
                    'rental_count': pb.rental_count,
                    'revenue': str(pb.revenue or 0)
                })
            
            # Powerbanks needing attention (damaged, maintenance, low battery)
            needs_attention = PowerBank.objects.filter(
                Q(status__in=['DAMAGED', 'MAINTENANCE']) |
                Q(battery_level__lt=20)
            ).select_related('current_station').count()
            
            # Station distribution
            station_distribution = PowerBank.objects.filter(
                current_station__isnull=False
            ).values(
                'current_station__station_name'
            ).annotate(
                count=Count('id')
            ).order_by('-count')[:10]
            
            return {
                'overview': {
                    'total_powerbanks': total_powerbanks,
                    'status_breakdown': {
                        'available': status_stats.get('AVAILABLE', 0),
                        'rented': status_stats.get('RENTED', 0),
                        'maintenance': status_stats.get('MAINTENANCE', 0),
                        'damaged': status_stats.get('DAMAGED', 0)
                    },
                    'needs_attention': needs_attention,
                    'avg_battery_level': round(utilization['avg_battery'] or 0, 2)
                },
                'utilization': {
                    'total_rentals': utilization['total_rentals'],
                    'active_rentals': utilization['active_rentals'],
                    'completed_rentals': utilization['completed_rentals'],
                    'total_revenue': str(utilization['total_revenue'] or 0),
                    'utilization_rate': round(
                        (status_stats.get('RENTED', 0) / total_powerbanks * 100) if total_powerbanks > 0 else 0,
                        2
                    )
                },
                'top_performers': top_performers_data,
                'station_distribution': [
                    {
                        'station': item['current_station__station_name'],
                        'count': item['count']
                    }
                    for item in station_distribution
                ]
            }
            
        except Exception as e:
            self.handle_service_error(e, "Failed to get powerbank analytics")
    
    @transaction.atomic
    def update_powerbank_status(self, powerbank_id: str, status: str, reason: str, admin_user) -> Dict[str, Any]:
        """Update powerbank status"""
        try:
            powerbank = PowerBank.objects.get(id=powerbank_id)
            old_status = powerbank.status
            
            # Validate status change
            if status == 'AVAILABLE' and powerbank.current_station is None:
                raise ServiceException(
                    detail="Cannot set powerbank to AVAILABLE without a station location",
                    code="invalid_status_change"
                )
            
            powerbank.status = status
            powerbank.save(update_fields=['status', 'last_updated'])
            
            # Log admin action
            self._log_admin_action(
                admin_user=admin_user,
                action_type='UPDATE_POWERBANK_STATUS',
                target_model='PowerBank',
                target_id=str(powerbank.id),
                changes={
                    'old_status': old_status,
                    'new_status': status,
                    'reason': reason,
                    'serial_number': powerbank.serial_number
                },
                description=f"Updated powerbank {powerbank.serial_number} status from {old_status} to {status}"
            )
            
            self.log_info(f"PowerBank status updated: {powerbank.serial_number} -> {status}")
            
            return {
                'id': str(powerbank.id),
                'serial_number': powerbank.serial_number,
                'status': powerbank.status
            }
            
        except PowerBank.DoesNotExist:
            raise ServiceException(
                detail="PowerBank not found",
                code="powerbank_not_found"
            )
        except Exception as e:
            self.handle_service_error(e, "Failed to update powerbank status")
    
    def _log_admin_action(self, admin_user, action_type: str, target_model: str, 
                         target_id: str, changes: Dict[str, Any], description: str = "") -> None:
        """Log admin action for audit trail"""
        try:
            AdminActionLog.objects.create(
                admin_user=admin_user,
                action_type=action_type,
                target_model=target_model,
                target_id=target_id,
                changes=changes,
                description=description,
                ip_address="127.0.0.1",
                user_agent="Admin Panel"
            )
        except Exception as e:
            self.log_error(f"Failed to log admin action: {str(e)}")
