"""
Station sync mixin - handles full station synchronization
"""
from __future__ import annotations

from typing import Dict, Any
from decimal import Decimal
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.db import transaction
import time

from api.common.services.base import ServiceException
from api.user.stations.models import Station, StationSlot, PowerBank
from api.internal.services.iot_sync_log_service import IoTSyncLogService


class StationSyncMixin:
    """Mixin for full station synchronization operations"""
    
    @transaction.atomic
    def sync_station_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sync complete station data (full sync)
        
        Args:
            data: Full data payload from IoT system
            
        Returns:
            Summary of sync operation
        """
        start_time = time.time()
        station = None
        log_status = 'SUCCESS'
        error_message = None
        result = {}
        
        try:
            self._validate_sync_data(data)
            
            device_data = data.get('device', {})
            station_data = data.get('station', {})
            slots_data = data.get('slots', [])
            powerbanks_data = data.get('power_banks', [])
            
            station_identifier = self._resolve_station_imei(device_data)
            
            station = self._sync_station(device_data, station_data)
            slots_updated = self._sync_slots(station, slots_data)
            powerbanks_updated = self._sync_powerbanks(station, powerbanks_data)
            
            # Track status change
            new_status = self.STATION_STATUS_MAP.get(device_data.get('status', 'OFFLINE'), 'OFFLINE')
            IoTSyncLogService.track_status_change(station, new_status, 'SYNC')
            
            result = {
                'station_id': str(station.id),
                'station_serial': station.serial_number,
                'slots_updated': slots_updated,
                'powerbanks_updated': powerbanks_updated,
                'timestamp': timezone.now().isoformat()
            }
            
            self.log_info(
                f"Station sync completed for {station_identifier}: {slots_updated} slots, {powerbanks_updated} powerbanks"
            )
            return result
            
        except ServiceException as e:
            log_status = 'FAILED'
            error_message = str(e)
            raise
        except Exception as e:
            log_status = 'FAILED'
            error_message = str(e)
            self.handle_service_error(e, "Failed to sync station data")
        finally:
            # Log sync operation
            if station:
                duration_ms = int((time.time() - start_time) * 1000)
                device_data = data.get('device', {})
                IoTSyncLogService.log_sync(
                    station=station,
                    device_uuid=device_data.get('imei', device_data.get('serial_number', 'unknown')),
                    sync_type='FULL',
                    direction='INBOUND',
                    request_payload=data,
                    response_payload=result,
                    status=log_status,
                    error_message=error_message,
                    duration_ms=duration_ms
                )
    
    def _sync_station(self, device_data: Dict, station_data: Dict) -> Station:
        """Update or create Station record"""
        try:
            imei = self._resolve_station_imei(device_data)
            serial_number = device_data.get('serial_number') or imei
            
            last_heartbeat_str = device_data.get('last_heartbeat')
            last_heartbeat = None
            if last_heartbeat_str:
                try:
                    last_heartbeat = parse_datetime(last_heartbeat_str)
                except ValueError:
                    self.log_warning(f"Invalid heartbeat format: {last_heartbeat_str}")
            
            station, created = Station.objects.get_or_create(
                imei=imei,
                defaults={
                    'serial_number': serial_number,
                    'station_name': f'Station {serial_number[-4:]}',
                    'latitude': Decimal('0.0'),
                    'longitude': Decimal('0.0'),
                    'address': 'Pending Configuration',
                    'total_slots': station_data.get('total_slots', 0),
                    'status': self.STATION_STATUS_MAP.get(device_data.get('status', 'OFFLINE'), 'OFFLINE'),
                    'hardware_info': device_data.get('hardware_info', {}),
                    'last_heartbeat': last_heartbeat or timezone.now()
                }
            )
            
            if not created:
                self._update_existing_station(station, device_data, station_data, last_heartbeat)
            else:
                self.log_info(f"Created new station {serial_number} ({imei})")
            
            return station
            
        except Exception as e:
            self.log_error(f"Error syncing station {device_data.get('serial_number')}: {str(e)}")
            raise ServiceException(detail=f"Failed to sync station: {str(e)}", code="station_sync_error")
    
    def _update_existing_station(self, station: Station, device_data: Dict, station_data: Dict, last_heartbeat) -> None:
        """Update existing station with new data"""
        station.total_slots = station_data.get('total_slots', station.total_slots)
        station.status = self.STATION_STATUS_MAP.get(device_data.get('status', 'OFFLINE'), 'OFFLINE')
        station.hardware_info = device_data.get('hardware_info', {})
        station.last_heartbeat = last_heartbeat or timezone.now()
        
        if device_data.get('signal_strength'):
            signal_str = str(device_data['signal_strength'])
            try:
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
        self.log_info(f"Updated station {station.serial_number}")
    
    def _sync_slots(self, station: Station, slots_data: list) -> int:
        """Update or create StationSlot records"""
        try:
            slots_updated = 0
            
            for slot_info in slots_data:
                slot_number = slot_info.get('slot_number')
                if not slot_number:
                    self.log_warning(f"Slot data missing slot_number: {slot_info}")
                    continue
                
                slot_status = self.SLOT_STATUS_MAP.get(slot_info.get('status', 'AVAILABLE'), 'AVAILABLE')
                battery_level = slot_info.get('battery_level', 0)
                slot_metadata = slot_info.get('slot_metadata', {})
                
                slot, created = StationSlot.objects.get_or_create(
                    station=station,
                    slot_number=slot_number,
                    defaults={'status': slot_status, 'battery_level': battery_level, 'slot_metadata': slot_metadata}
                )
                
                if not created:
                    slot.status = slot_status
                    slot.battery_level = battery_level
                    slot.slot_metadata = slot_metadata
                    slot.save()
                
                slots_updated += 1
            
            self.log_info(f"Updated {slots_updated} slots for station {station.serial_number}")
            return slots_updated
            
        except Exception as e:
            self.log_error(f"Error syncing slots for station {station.serial_number}: {str(e)}")
            raise ServiceException(detail=f"Failed to sync slots: {str(e)}", code="slots_sync_error")
    
    def _sync_powerbanks(self, station: Station, powerbanks_data: list) -> int:
        """Update or create PowerBank records"""
        try:
            powerbanks_updated = 0
            
            for pb_info in powerbanks_data:
                pb_serial = pb_info.get('serial_number')
                if not pb_serial:
                    self.log_warning(f"PowerBank data missing serial_number: {pb_info}")
                    continue
                
                pb_status = self.POWERBANK_STATUS_MAP.get(pb_info.get('status', 'AVAILABLE'), 'AVAILABLE')
                battery_level = pb_info.get('battery_level', 0)
                current_slot_number = pb_info.get('current_slot')
                hardware_info = pb_info.get('hardware_info', {})
                
                current_slot = None
                if current_slot_number:
                    try:
                        current_slot = StationSlot.objects.get(station=station, slot_number=current_slot_number)
                    except StationSlot.DoesNotExist:
                        self.log_warning(f"Slot {current_slot_number} not found for station {station.serial_number}")
                
                powerbank, created = PowerBank.objects.get_or_create(
                    serial_number=pb_serial,
                    defaults={
                        'model': 'Standard',
                        'capacity_mah': 10000,
                        'status': pb_status,
                        'battery_level': battery_level,
                        'hardware_info': hardware_info,
                        'current_station': station,
                        'current_slot': current_slot
                    }
                )
                
                if not created:
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
            raise ServiceException(detail=f"Failed to sync powerbanks: {str(e)}", code="powerbanks_sync_error")
