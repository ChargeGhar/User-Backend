"""
Return event mixin - handles PowerBank return event processing
"""
from __future__ import annotations

from typing import Dict, Any
from django.db import transaction

from api.common.services.base import ServiceException
from api.user.stations.models import Station, StationSlot, PowerBank


class ReturnEventMixin:
    """Mixin for processing PowerBank return events"""
    
    @transaction.atomic
    def process_return_event(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process PowerBank return event
        
        Args:
            data: Return event payload from IoT system
            
        Returns:
            Summary of return processing
        """
        try:
            self._validate_return_data(data)
            
            device_data = data.get('device', {})
            return_event = data.get('return_event', {})
            
            station_serial = device_data.get('serial_number')
            pb_serial = return_event.get('power_bank_serial')
            slot_number = return_event.get('slot_number')
            battery_level = return_event.get('battery_level', 0)
            
            # Find station
            try:
                station = Station.objects.get(serial_number=station_serial)
            except Station.DoesNotExist:
                raise ServiceException(detail=f"Station {station_serial} not found", code="station_not_found")
            
            # Find powerbank
            try:
                powerbank = PowerBank.objects.get(serial_number=pb_serial)
            except PowerBank.DoesNotExist:
                raise ServiceException(detail=f"PowerBank {pb_serial} not found", code="powerbank_not_found")
            
            # Find slot
            try:
                slot = StationSlot.objects.get(station=station, slot_number=slot_number)
            except StationSlot.DoesNotExist:
                raise ServiceException(
                    detail=f"Slot {slot_number} not found at station {station_serial}",
                    code="slot_not_found"
                )
            
            # Find active rental for this powerbank
            from api.user.rentals.models import Rental
            active_rental = Rental.objects.filter(power_bank=powerbank, status='ACTIVE').first()
            
            if not active_rental:
                self.log_warning(f"No active rental found for powerbank {pb_serial}")
                self._update_powerbank_location(powerbank, station, slot, battery_level)
                return {
                    'message': 'PowerBank location updated, no active rental found',
                    'power_bank_serial': pb_serial,
                    'station_serial': station_serial,
                    'slot_number': slot_number
                }
            
            result = self._process_rental_return(active_rental, station, slot, powerbank, battery_level)
            
            self.log_info(f"Return event processed successfully for rental {active_rental.rental_code}")
            return result
            
        except ServiceException:
            raise
        except Exception as e:
            self.handle_service_error(e, "Failed to process return event")
    
    def _update_powerbank_location(self, powerbank: PowerBank, station: Station, slot: StationSlot, battery_level: int) -> None:
        """Update powerbank location and status"""
        powerbank.current_station = station
        powerbank.current_slot = slot
        powerbank.battery_level = battery_level
        powerbank.status = 'AVAILABLE'
        powerbank.save()
        
        slot.status = 'OCCUPIED'
        slot.battery_level = battery_level
        slot.save()
    
    def _process_rental_return(self, rental, station: Station, slot: StationSlot, powerbank: PowerBank, battery_level: int) -> Dict[str, Any]:
        """
        Process the actual rental return by delegating to RentalService
        This ensures all payment logic, auto-collection, and bonus points are handled
        """
        try:
            from api.user.rentals.services import RentalService
            
            rental_service = RentalService()
            completed_rental = rental_service.return_power_bank(
                rental_id=str(rental.id),
                return_station_sn=station.serial_number,
                return_slot_number=slot.slot_number,
                battery_level=battery_level
            )
            
            return {
                'rental_id': str(completed_rental.id),
                'rental_code': completed_rental.rental_code,
                'rental_status': completed_rental.status,
                'returned_on_time': completed_rental.is_returned_on_time,
                'power_bank_status': powerbank.status,
                'station_serial': station.serial_number,
                'slot_number': slot.slot_number,
                'payment_status': completed_rental.payment_status,
                'amount_paid': float(completed_rental.amount_paid),
                'overdue_amount': float(completed_rental.overdue_amount)
            }
            
        except Exception as e:
            self.log_error(f"Error processing rental return: {str(e)}")
            raise ServiceException(detail=f"Failed to process rental return: {str(e)}", code="rental_return_error")
