"""
Service for synchronizing station data from IoT system
Handles station, slot, and powerbank updates following project patterns
"""
from __future__ import annotations

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.db import transaction
from django.db.models import Q
from typing import Dict, Any, Optional
from decimal import Decimal

from api.common.services.base import CRUDService, ServiceException
from api.common.utils.helpers import paginate_queryset
from api.user.stations.models import Station, StationSlot, PowerBank


class StationSyncService(CRUDService):
    """
    Service for processing station data from IoT system
    Following project CRUD service patterns with comprehensive error handling
    """
    model = Station
    
    # Status mapping from IoT system to Django models
    SLOT_STATUS_MAP = {
        'AVAILABLE': 'AVAILABLE',
        'OCCUPIED': 'OCCUPIED', 
        'ERROR': 'ERROR',
        'MAINTENANCE': 'MAINTENANCE'
    }
    
    POWERBANK_STATUS_MAP = {
        'AVAILABLE': 'AVAILABLE',
        'RENTED': 'RENTED',
        'MAINTENANCE': 'MAINTENANCE',
        'DAMAGED': 'DAMAGED'
    }
    
    STATION_STATUS_MAP = {
        'ONLINE': 'ONLINE',
        'OFFLINE': 'OFFLINE',
        'MAINTENANCE': 'MAINTENANCE'
    }
    
    @transaction.atomic
    def sync_station_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sync complete station data (full sync)
        
        Args:
            data: Full data payload from IoT system
            
        Returns:
            Summary of sync operation
            
        Raises:
            ServiceException: If validation or sync fails
        """
        try:
            # Validate input data
            self._validate_sync_data(data)
            
            device_data = data.get('device', {})
            station_data = data.get('station', {})
            slots_data = data.get('slots', [])
            powerbanks_data = data.get('power_banks', [])
            
            serial_number = device_data.get('serial_number')
            
            # Update or create Station
            station = self._sync_station(device_data, station_data)
            
            # Update StationSlots
            slots_updated = self._sync_slots(station, slots_data)
            
            # Update PowerBanks
            powerbanks_updated = self._sync_powerbanks(station, powerbanks_data)
            
            result = {
                'station_id': str(station.id),
                'station_serial': station.serial_number,
                'slots_updated': slots_updated,
                'powerbanks_updated': powerbanks_updated,
                'timestamp': timezone.now().isoformat()
            }
            
            self.log_info(f"Station sync completed for {serial_number}: {slots_updated} slots, {powerbanks_updated} powerbanks")
            return result
            
        except ServiceException:
            # Re-raise service exceptions
            raise
        except Exception as e:
            self.handle_service_error(e, "Failed to sync station data")
    
    def _validate_sync_data(self, data: Dict[str, Any]) -> None:
        """Validate sync data structure"""
        if not isinstance(data, dict):
            raise ServiceException(
                detail="Data must be a dictionary",
                code="invalid_data_format"
            )
        
        device_data = data.get('device', {})
        if not device_data.get('serial_number'):
            raise ServiceException(
                detail="Missing device serial_number",
                code="missing_serial_number"
            )
        
        # Validate slots data if present
        slots_data = data.get('slots', [])
        if slots_data and not isinstance(slots_data, list):
            raise ServiceException(
                detail="Slots data must be a list",
                code="invalid_slots_format"
            )
        
        # Validate powerbanks data if present
        powerbanks_data = data.get('power_banks', [])
        if powerbanks_data and not isinstance(powerbanks_data, list):
            raise ServiceException(
                detail="PowerBanks data must be a list",
                code="invalid_powerbanks_format"
            )
    
    def _sync_station(self, device_data: Dict, station_data: Dict) -> Station:
        """
        Update or create Station record
        
        Args:
            device_data: Device information from IoT system
            station_data: Station configuration data
            
        Returns:
            Updated or created Station instance
        """
        try:
            serial_number = device_data.get('serial_number')
            imei = device_data.get('imei', serial_number)
            
            # Parse last_heartbeat
            last_heartbeat_str = device_data.get('last_heartbeat')
            last_heartbeat = None
            if last_heartbeat_str:
                try:
                    last_heartbeat = parse_datetime(last_heartbeat_str)
                except ValueError:
                    self.log_warning(f"Invalid heartbeat format: {last_heartbeat_str}")
            
            # Get or create station
            station, created = Station.objects.get_or_create(
                serial_number=serial_number,
                defaults={
                    'imei': imei,
                    'station_name': f'Station {serial_number[-4:]}',  # Default name
                    'latitude': Decimal('0.0'),  # Will be set manually in admin
                    'longitude': Decimal('0.0'),
                    'address': 'Pending Configuration',
                    'total_slots': station_data.get('total_slots', 0),
                    'status': self.STATION_STATUS_MAP.get(device_data.get('status', 'OFFLINE'), 'OFFLINE'),
                    'hardware_info': device_data.get('hardware_info', {}),
                    'last_heartbeat': last_heartbeat or timezone.now()
                }
            )
            
            if not created:
                # Update existing station
                station.imei = imei
                station.total_slots = station_data.get('total_slots', station.total_slots)
                station.status = self.STATION_STATUS_MAP.get(device_data.get('status', 'OFFLINE'), 'OFFLINE')
                station.hardware_info = device_data.get('hardware_info', {})
                station.last_heartbeat = last_heartbeat or timezone.now()
                
                # Update signal strength and wifi info if available
                if device_data.get('signal_strength'):
                    signal_str = str(device_data['signal_strength'])
                    try:
                        # Handle various formats: "CSQ:28", "RSSI:-65", "28", etc.
                        if ':' in signal_str:
                            signal_value = int(signal_str.split(':')[1].strip())
                        else:
                            signal_value = int(signal_str)
                        station.hardware_info['signal_strength'] = signal_value
                    except (ValueError, IndexError) as e:
                        self.log_warning(f"Invalid signal_strength format: '{signal_str}', error: {e}")
                        station.hardware_info['signal_strength'] = 0
                
                if device_data.get('wifi_ssid'):
                    station.hardware_info['wifi_ssid'] = device_data['wifi_ssid']
                
                station.save()
                self.log_info(f"Updated station {serial_number}")
            else:
                self.log_info(f"Created new station {serial_number}")
            
            return station
            
        except Exception as e:
            self.log_error(f"Error syncing station {serial_number}: {str(e)}")
            raise ServiceException(
                detail=f"Failed to sync station: {str(e)}",
                code="station_sync_error"
            )
    
    def _sync_slots(self, station: Station, slots_data: list) -> int:
        """
        Update or create StationSlot records
        
        Args:
            station: Station instance
            slots_data: List of slot data from IoT system
            
        Returns:
            Number of slots updated
        """
        try:
            slots_updated = 0
            
            for slot_info in slots_data:
                slot_number = slot_info.get('slot_number')
                if not slot_number:
                    self.log_warning(f"Slot data missing slot_number: {slot_info}")
                    continue
                
                slot_status = self.SLOT_STATUS_MAP.get(
                    slot_info.get('status', 'AVAILABLE'),
                    'AVAILABLE'
                )
                
                battery_level = slot_info.get('battery_level', 0)
                slot_metadata = slot_info.get('slot_metadata', {})
                power_bank_serial = slot_info.get('power_bank_serial')
                
                # Get or create slot
                slot, created = StationSlot.objects.get_or_create(
                    station=station,
                    slot_number=slot_number,
                    defaults={
                        'status': slot_status,
                        'battery_level': battery_level,
                        'slot_metadata': slot_metadata
                    }
                )
                
                if not created:
                    # Update existing slot
                    slot.status = slot_status
                    slot.battery_level = battery_level
                    slot.slot_metadata = slot_metadata
                    slot.save()
                
                slots_updated += 1
            
            self.log_info(f"Updated {slots_updated} slots for station {station.serial_number}")
            return slots_updated
            
        except Exception as e:
            self.log_error(f"Error syncing slots for station {station.serial_number}: {str(e)}")
            raise ServiceException(
                detail=f"Failed to sync slots: {str(e)}",
                code="slots_sync_error"
            )
    
    def _sync_powerbanks(self, station: Station, powerbanks_data: list) -> int:
        """
        Update or create PowerBank records
        
        Args:
            station: Station instance
            powerbanks_data: List of powerbank data from IoT system
            
        Returns:
            Number of powerbanks updated
        """
        try:
            powerbanks_updated = 0
            
            for pb_info in powerbanks_data:
                pb_serial = pb_info.get('serial_number')
                if not pb_serial:
                    self.log_warning(f"PowerBank data missing serial_number: {pb_info}")
                    continue
                
                pb_status = self.POWERBANK_STATUS_MAP.get(
                    pb_info.get('status', 'AVAILABLE'),
                    'AVAILABLE'
                )
                
                battery_level = pb_info.get('battery_level', 0)
                current_slot_number = pb_info.get('current_slot')
                hardware_info = pb_info.get('hardware_info', {})
                
                # Find current slot
                current_slot = None
                if current_slot_number:
                    try:
                        current_slot = StationSlot.objects.get(
                            station=station,
                            slot_number=current_slot_number
                        )
                    except StationSlot.DoesNotExist:
                        self.log_warning(f"Slot {current_slot_number} not found for station {station.serial_number}")
                
                # Get or create powerbank
                powerbank, created = PowerBank.objects.get_or_create(
                    serial_number=pb_serial,
                    defaults={
                        'model': 'Standard',  # Will be set based on capacity mapping
                        'capacity_mah': 10000,  # Default, should be mapped from SN
                        'status': pb_status,
                        'battery_level': battery_level,
                        'hardware_info': hardware_info,
                        'current_station': station,
                        'current_slot': current_slot
                    }
                )
                
                if not created:
                    # Update existing powerbank
                    powerbank.status = pb_status
                    powerbank.battery_level = battery_level
                    powerbank.hardware_info = hardware_info
                    powerbank.current_station = station
                    powerbank.current_slot = current_slot
                    powerbank.save()
                
                powerbanks_updated += 1
            
            self.log_info(f"Updated {powerbanks_updated} powerbanks for station {station.serial_number}")
            return powerbanks_updated
            
        except Exception as e:
            self.log_error(f"Error syncing powerbanks for station {station.serial_number}: {str(e)}")
            raise ServiceException(
                detail=f"Failed to sync powerbanks: {str(e)}",
                code="powerbanks_sync_error"
            )
    
    @transaction.atomic
    def process_return_event(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process PowerBank return event
        
        Args:
            data: Return event payload from IoT system
            
        Returns:
            Summary of return processing
            
        Raises:
            ServiceException: If validation or processing fails
        """
        try:
            # Validate return event data
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
                raise ServiceException(
                    detail=f"Station {station_serial} not found",
                    code="station_not_found"
                )
            
            # Find powerbank
            try:
                powerbank = PowerBank.objects.get(serial_number=pb_serial)
            except PowerBank.DoesNotExist:
                raise ServiceException(
                    detail=f"PowerBank {pb_serial} not found",
                    code="powerbank_not_found"
                )
            
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
            active_rental = Rental.objects.filter(
                power_bank=powerbank,
                status='ACTIVE'
            ).first()
            
            if not active_rental:
                self.log_warning(f"No active rental found for powerbank {pb_serial}")
                # Still update powerbank location
                self._update_powerbank_location(powerbank, station, slot, battery_level)
                return {
                    'message': 'PowerBank location updated, no active rental found',
                    'power_bank_serial': pb_serial,
                    'station_serial': station_serial,
                    'slot_number': slot_number
                }
            
            # Process rental return
            result = self._process_rental_return(active_rental, station, slot, powerbank, battery_level)
            
            self.log_info(f"Return event processed successfully for rental {active_rental.rental_code}")
            return result
            
        except ServiceException:
            # Re-raise service exceptions
            raise
        except Exception as e:
            self.handle_service_error(e, "Failed to process return event")
    
    def _validate_return_data(self, data: Dict[str, Any]) -> None:
        """Validate return event data structure"""
        device_data = data.get('device', {})
        return_event = data.get('return_event', {})
        
        required_fields = {
            'device.serial_number': device_data.get('serial_number'),
            'return_event.power_bank_serial': return_event.get('power_bank_serial'),
            'return_event.slot_number': return_event.get('slot_number')
        }
        
        missing_fields = [field for field, value in required_fields.items() if not value]
        if missing_fields:
            raise ServiceException(
                detail=f"Missing required fields: {', '.join(missing_fields)}",
                code="missing_return_fields"
            )
    
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
            # CRITICAL FIX: Call RentalService to handle complete return logic
            # This triggers: charge calculation, auto-collection, bonus points, notifications
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
            raise ServiceException(
                detail=f"Failed to process rental return: {str(e)}",
                code="rental_return_error"
            )
    
    @transaction.atomic
    def update_station_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update station status (online/offline/maintenance)
        
        Args:
            data: Status update payload from IoT system
            
        Returns:
            Summary of status update
            
        Raises:
            ServiceException: If validation or update fails
        """
        try:
            # Validate input data
            self._validate_status_data(data)
            
            device_data = data.get('device', {})
            serial_number = device_data.get('serial_number')
            imei = device_data.get('imei')
            new_status = device_data.get('status')
            
            # Find station by serial_number (could be IMEI or actual serial)
            identifier = imei or serial_number
            if not identifier:
                raise ServiceException(
                    detail="Missing device identifier (imei or serial_number)",
                    code="missing_device_identifier"
                )
            
            # Check if identifier matches IMEI or serial_number field
            station = Station.objects.filter(
                Q(imei=identifier) | Q(serial_number=identifier)
            ).first()
            
            if not station:
                raise ServiceException(
                    detail=f"Station with identifier {identifier} not found",
                    code="station_not_found"
                )
            
            # Validate status value
            if new_status not in self.STATION_STATUS_MAP:
                raise ServiceException(
                    detail=f"Invalid status '{new_status}'. Must be one of: {', '.join(self.STATION_STATUS_MAP.keys())}",
                    code="invalid_status"
                )
            
            # Update station status and heartbeat
            station.status = self.STATION_STATUS_MAP.get(new_status, 'OFFLINE')
            station.last_heartbeat = timezone.now()
            
            # Update hardware info if provided
            if device_data.get('hardware_info'):
                station.hardware_info.update(device_data['hardware_info'])
            
            station.save(update_fields=['status', 'last_heartbeat', 'hardware_info'])
            
            result = {
                'station_id': str(station.id),
                'serial_number': station.serial_number,
                'status': station.status,
                'last_heartbeat': station.last_heartbeat.isoformat(),
                'updated_at': timezone.now().isoformat()
            }
            
            identifier = imei or serial_number
            self.log_info(f"Station {identifier} status updated to {station.status}")
            return result
        
        except ServiceException:
            # Re-raise service exceptions
            raise
        except Exception as e:
            identifier = data.get('device', {}).get('imei') or data.get('device', {}).get('serial_number', 'unknown')
            self.handle_service_error(e, f"Failed to update station status for {identifier}")
    
    def _validate_status_data(self, data: Dict[str, Any]) -> None:
        """Validate status update data structure"""
        if not isinstance(data, dict):
            raise ServiceException(
                detail="Data must be a dictionary",
                code="invalid_data_format"
            )
        
        device_data = data.get('device', {})
        # Accept either IMEI or serial_number as device identifier
        if not device_data.get('imei') and not device_data.get('serial_number'):
            raise ServiceException(
                detail="Missing device imei or serial_number",
                code="missing_device_identifier"
            )
        
        if not device_data.get('status'):
            raise ServiceException(
                detail="Missing device status",
                code="missing_status"
            )